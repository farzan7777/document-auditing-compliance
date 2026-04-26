"""
Internal baseline agent.
Uses Groq when GROQ_API_KEY is set, otherwise falls back to heuristics.
"""

import hashlib
import json
import logging
import os
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import nullcontext
from functools import lru_cache
from typing import Any, Dict, List, Optional

from openai import OpenAI
from openai import AuthenticationError, RateLimitError, BadRequestError, APIError
from pydantic import ValidationError

from app import env
from app.models import Action, ActionType

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
# Default to small/fast model; override with GROQ_MODEL in env (e.g. on HF Space).
DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
DEFAULT_BASELINE_SEEDS = {1: 42, 2: 42, 3: 42}

logger = logging.getLogger(__name__)

# Optional LLM response cache (same JSON action output as live call). Off unless enabled.
_LLM_RESPONSE_CACHE: Dict[str, str] = {}
_LLM_CACHE_MAX_ENTRIES = 512

# Serialize Groq HTTP calls when enabled (avoids TPM spikes from parallel tasks on free tier).
_GROQ_RPC_LOCK = threading.Lock()


def _llm_cache_enabled() -> bool:
    return os.environ.get("GROQ_BASELINE_CACHE", "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _groq_baseline_serialize_requests() -> bool:
    """If true, only one Groq request happens at a time globally."""
    return os.environ.get("GROQ_BASELINE_SERIALIZE", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _groq_baseline_max_retries() -> int:
    raw = os.environ.get("GROQ_BASELINE_MAX_RETRIES", "8").strip()
    try:
        return max(1, min(20, int(raw)))
    except ValueError:
        return 8


def _groq_sampling_defaults() -> Dict[str, Any]:
    return {
        "temperature": 0.1,
        "top_p": 0.95,
        "response_format": {"type": "json_object"},
    }


def _retry_after_seconds_from_rate_limit(err: RateLimitError) -> Optional[float]:
    """Extends backoff logic if Groq explicitly tells us when to return."""
    msg = str(err).lower()
    if "retry-after" in msg or "try again in" in msg:
        try:
            # Simple heuristic for parsing Groq's error string
            parts = msg.split()
            for i, p in enumerate(parts):
                if p in ("in", "after") and i + 1 < len(parts):
                    val = parts[i + 1].replace("s", "").replace("ms", "")
                    return float(val)
        except (ValueError, IndexError):
            pass
    return None


def _stable_cache_key(model: str, system_text: str, user_text: str, seed: Optional[int]) -> str:
    payload = f"{model}\0{system_text}\0{user_text}\0{seed}".encode("utf-8", errors="replace")
    return hashlib.sha256(payload).hexdigest()


def _observability_prompt_hash(system_text: str, user_text: str, seed: Optional[int]) -> int:
    """Spec: hash(system_prompt + user_prompt + seed) for logs only."""
    return hash(system_text + user_text + str(seed if seed is not None else ""))


def _inject_system_seed(system_prompt: str, episode_seed: Optional[int]) -> str:
    if episode_seed is None:
        return system_prompt
    return f"{system_prompt}\n\nSYSTEM_SEED: {episode_seed}\n"


def _groq_chat_completion_with_repro_layer(
    client: OpenAI,
    *,
    model: str,
    messages: List[Dict[str, str]],
    base_system_prompt: str,
    user_prompt_text: str,
    episode_seed: Optional[int],
) -> str:
    """
    Thin wrapper: fixed sampling defaults + optional cache + observability hash.
    Does not alter messages/scoring outside this call path.
    """
    system_for_api = messages[0]["content"] if messages else ""
    prompt_hash = _observability_prompt_hash(base_system_prompt, user_prompt_text, episode_seed)
    logger.info(
        "groq_llm prompt_hash=%s model=%s seed=%s cache=%s",
        prompt_hash,
        model,
        episode_seed,
        _llm_cache_enabled(),
    )

    cache_key = _stable_cache_key(model, system_for_api, user_prompt_text, episode_seed)
    if _llm_cache_enabled():
        cached = _LLM_RESPONSE_CACHE.get(cache_key)
        if cached is not None:
            return cached

    create_kwargs: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": _active_max_tokens(),
        **_groq_sampling_defaults(),
    }

    lock_ctx = _GROQ_RPC_LOCK if _groq_baseline_serialize_requests() else nullcontext()
    max_retries = _groq_baseline_max_retries()
    for attempt in range(max_retries):
        try:
            with lock_ctx:
                response = client.chat.completions.create(**create_kwargs)
            content = response.choices[0].message.content or ""
            break
        except RateLimitError as e:
            if attempt >= max_retries - 1:
                raise
            wait = _retry_after_seconds_from_rate_limit(e)
            if wait is None:
                wait = min(45.0, 0.8 * (2**attempt))
            wait = min(90.0, wait + random.uniform(0.05, 0.35))
            logger.warning(
                "groq rate limit (attempt %s/%s), sleeping %.2fs: %s",
                attempt + 1,
                max_retries,
                wait,
                str(e)[:200],
            )
            time.sleep(wait)

    if _llm_cache_enabled():
        if len(_LLM_RESPONSE_CACHE) >= _LLM_CACHE_MAX_ENTRIES:
            _LLM_RESPONSE_CACHE.pop(next(iter(_LLM_RESPONSE_CACHE)))
        _LLM_RESPONSE_CACHE[cache_key] = content

    return content


def _safe_grade(session_id: str):
    """Grade without polluting curriculum; compatible with older env.grade()."""
    try:
        return env.grade(session_id=session_id, record_curriculum=False)
    except TypeError:
        return env.grade(session_id=session_id)


def _normalize_seeds(seeds: Optional[Dict[int, int]]) -> Dict[int, int]:
    """
    Normalize seed map for tasks 1-3.
    - If no seeds provided, use default 42s.
    - If seeds provided, preserve provided values and do not silently fall back
      to 42 for missing tasks; instead replicate the first provided seed.
    """
    if not seeds:
        return DEFAULT_BASELINE_SEEDS.copy()

    normalized = {int(k): int(v) for k, v in seeds.items() if k in (1, 2, 3)}
    if not normalized:
        return DEFAULT_BASELINE_SEEDS.copy()

    first_seed = next(iter(normalized.values()))
    return {
        1: normalized.get(1, first_seed),
        2: normalized.get(2, first_seed),
        3: normalized.get(3, first_seed),
    }


def _active_groq_model() -> str:
    return os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)


def _active_max_tokens() -> int:
    """Cap completion length for faster responses (single JSON action per call)."""
    raw = os.environ.get("GROQ_MAX_TOKENS", "96").strip()
    try:
        return max(32, min(512, int(raw)))
    except ValueError:
        return 96


def _groq_http_timeout() -> float:
    """Per-request timeout for Groq (read); avoids hanging try-it-out for minutes."""
    raw = os.environ.get("GROQ_HTTP_TIMEOUT_SEC", "45").strip()
    try:
        return max(5.0, min(180.0, float(raw)))
    except ValueError:
        return 45.0


@lru_cache(maxsize=8)
def _groq_client_for_key(api_key: str, timeout_s_key: str) -> OpenAI:
    return OpenAI(
        api_key=api_key,
        base_url=GROQ_BASE_URL,
        timeout=float(timeout_s_key),
    )


def _groq_client() -> Optional[OpenAI]:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    t = _groq_http_timeout()
    return _groq_client_for_key(api_key, f"{t:.6f}")


def _as_dict(observation: Any) -> Dict[str, Any]:
    if hasattr(observation, "model_dump"):
        return observation.model_dump()
    if isinstance(observation, dict):
        return observation
    raise TypeError(f"Unsupported observation type: {type(observation)!r}")


def _llm_doc_char_budget(task_id: int) -> int:
    """
    Max characters of document_text sent to Groq per step (input size dominates latency).
    0 = send full document. Set GROQ_BASELINE_DOC_CHAR_BUDGET=0 to disable.
    Optional per-task: GROQ_BASELINE_DOC_CHAR_BUDGET_1 / _2 / _3 (override global).
    """
    for key in (
        f"GROQ_BASELINE_DOC_CHAR_BUDGET_{task_id}",
        "GROQ_BASELINE_DOC_CHAR_BUDGET",
    ):
        raw = os.environ.get(key, "").strip()
        if not raw:
            continue
        if raw.lower() in ("0", "off", "none", "full"):
            return 0
        try:
            return max(2_000, min(120_000, int(raw)))
        except ValueError:
            continue
    # Task 3 prompts are largest; keep default budget lower to stay under on_demand TPM.
    return {1: 14_000, 2: 16_000, 3: 11_000}.get(task_id, 12_000)


def _compress_document_for_llm(text: str, budget: int) -> tuple[str, bool]:
    if budget <= 0 or len(text) <= budget:
        return text, False
    marker = "\n\n...[middle omitted for API speed]...\n\n"
    cap = budget - len(marker)
    if cap < 800:
        return text[:budget], True
    head_n = int(cap * 0.72)
    tail_n = cap - head_n
    core = text[:head_n] + marker + text[-tail_n:]
    return core[:budget], True


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
    return text.strip()


def _parse_action(text: str) -> Dict[str, Any]:
    raw = _strip_json_fences(text)
    action = json.loads(raw)
    if not isinstance(action, dict):
        raise ValueError("LLM response must be a JSON object.")
    if "action_type" not in action:
        raise ValueError("LLM response missing action_type.")
    action["action_type"] = str(action["action_type"]).strip().lower()
    if "severity" in action and action["severity"] is not None:
        action["severity"] = str(action["severity"]).strip().lower()
    if "field" in action and action["field"] is not None:
        action["field"] = str(action["field"]).strip()
    if "reason" in action and action["reason"] is not None:
        action["reason"] = str(action["reason"]).strip()
    return action


def _history_tail_limit() -> int:
    raw = os.environ.get("GROQ_BASELINE_HISTORY_TAIL", "4").strip()
    try:
        return max(0, min(12, int(raw)))
    except ValueError:
        return 4


def _build_messages(
    system_prompt: str,
    observation: Dict[str, Any],
    history: List[Dict[str, Any]],
    task_id: int,
) -> List[Dict[str, str]]:
    budget = _llm_doc_char_budget(task_id)
    doc_text, truncated = _compress_document_for_llm(observation["document_text"], budget)
    messages = [{"role": "system", "content": system_prompt}]
    tail = _history_tail_limit()
    if history and tail > 0:
        messages.append(
            {
                "role": "assistant",
                "content": json.dumps(history[-tail:], separators=(",", ":")),
            }
        )
    payload: Dict[str, Any] = {
        "task_name": observation["task_name"],
        "task_description": observation.get("task_description", ""),
        "document_text": doc_text,
        "document_truncated": truncated,
        "current_flags": observation.get("current_flags", []),
        "current_confirmations": observation.get("current_confirmations", []),
        "steps_taken": observation.get("steps_taken", 0),
        "max_steps": observation.get("max_steps", 0),
        "cumulative_reward": observation.get("cumulative_reward", 0.0),
        "available_actions": observation.get("available_actions", []),
        "instructions": observation.get("instructions", ""),
    }
    messages.append(
        {
            "role": "user",
            "content": json.dumps(payload, separators=(",", ":")),
        }
    )
    return messages


def _llm_next_action(
    system_prompt: str,
    observation: Dict[str, Any],
    history: List[Dict[str, Any]],
    task_id: int,
    episode_seed: Optional[int] = None,
) -> Dict[str, Any]:
    client = _groq_client()
    if client is None:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    system_for_request = _inject_system_seed(system_prompt, episode_seed)
    messages = _build_messages(system_for_request, observation, history, task_id)
    user_prompt_text = messages[-1]["content"] if messages else ""
    content = _groq_chat_completion_with_repro_layer(
        client,
        model=_active_groq_model(),
        messages=messages,
        base_system_prompt=system_prompt,
        user_prompt_text=user_prompt_text,
        episode_seed=episode_seed,
    )
    return _parse_action(content)


def _coerce_action(action: Dict[str, Any], allowed: List[str], fallback: str) -> Dict[str, Any]:
    action_type = action.get("action_type", "").lower()
    if action_type not in allowed:
        return {"action_type": fallback}
    return action


def _llm_iteration_cap(task_id: int, env_max_steps: int) -> int:
    """
    Cap how many Groq calls we make per task in the live baseline.

    The env allows up to 12/20/30 steps, but each step is one full-document completion;
    worst-case sequential runs (~62 calls) exceed typical HF / browser timeouts (~260s).
    Override with GROQ_BASELINE_MAX_LLM_STEPS (single int cap for all tasks).
    """
    raw = os.environ.get("GROQ_BASELINE_MAX_LLM_STEPS", "").strip()
    if raw:
        try:
            cap = max(4, min(64, int(raw)))
            return min(env_max_steps, cap)
        except ValueError:
            pass
    # Tight caps: each step is one Groq round-trip; env still has full document for grading
    per_task = {1: 8, 2: 14, 3: 18}
    return min(env_max_steps, per_task.get(task_id, 14))


def _run_llm_episode(
    session_id: str,
    observation: Any,
    task_id: int,
    system_prompt: str,
    allowed_actions: List[str],
    fallback_runner,
) -> float:
    obs = _as_dict(observation)
    history: List[Dict[str, Any]] = []
    try:
        episode_seed = env.state(session_id).get("seed")
    except Exception:
        episode_seed = None

    env_max = int(obs.get("max_steps", 0))
    max_iter = _llm_iteration_cap(task_id, env_max)
    for _ in range(max_iter):
        try:
            next_action = _llm_next_action(
                system_prompt, obs, history, task_id, episode_seed=episode_seed
            )
            next_action = _coerce_action(next_action, allowed_actions, "submit")
        except (json.JSONDecodeError, ValueError, RuntimeError):
            return fallback_runner(session_id, obs["document_text"])

        try:
            step_result = env.step(session_id=session_id, action=Action(**next_action))
        except (ValidationError, KeyError, ValueError, TypeError):
            return fallback_runner(session_id, obs["document_text"])

        history.append(
            {
                "action": next_action,
                "reward": step_result.reward.value,
                "reason": step_result.reward.reason,
            }
        )
        obs = _as_dict(step_result.observation)

        if step_result.done or next_action["action_type"] == "submit":
            break

    # Budget exhausted without a clean terminal step — try submit once then grade
    try:
        st = env.state(session_id)
        if not st.get("done") and ActionType.SUBMIT.value in allowed_actions:
            env.step(
                session_id=session_id,
                action=Action(action_type=ActionType.SUBMIT),
            )
    except Exception:
        pass

    result = _safe_grade(session_id=session_id)
    return result.score


def _run_task1_rule_based(session_id: str, document: str) -> float:
    doc_lower = document.lower()
    keyword_map = {
        "party_a": ["party a", "employer", "nexora", "engaging entity"],
        "party_b": ["party b", "employee", "engaged professional"],
        "effective_date": ["effective date", "effective as of", "commencement of obligations"],
        "termination_clause": ["termination", "terminate", "30 days", "dissolution"],
        "governing_law": ["governing law", "laws of the state", "jurisdiction and venue", "jurisdiction"],
        "signature_block": ["witness whereof", "employer signature", "employee signature", "executed", "execution date", "________________"],
    }

    for field, keywords in keyword_map.items():
        found = any(kw in doc_lower for kw in keywords)
        env.step(
            session_id=session_id,
            action=Action(
                action_type=ActionType.MARK_FIELD_PRESENT if found else ActionType.MARK_FIELD_MISSING,
                field=field,
                reason=f"{'Found' if found else 'Not found'} indicators for {field}",
            ),
        )

    env.step(session_id=session_id, action=Action(action_type=ActionType.SUBMIT))
    return _safe_grade(session_id=session_id).score


def _run_task2_rule_based(session_id: str, document: str) -> float:
    def _split_po_invoice(doc: str) -> tuple[str, str]:
        if "--- INVOICE ---" in doc:
            po_part, inv_part = doc.split("--- INVOICE ---", 1)
        else:
            po_part, inv_part = doc, doc
        if "--- PURCHASE ORDER ---" in po_part:
            po_part = po_part.split("--- PURCHASE ORDER ---", 1)[-1]
        return po_part, inv_part

    def _extract_table(section: str) -> list[str]:
        lines = section.splitlines()
        dash = "-" * 65
        try:
            start = next(i for i, l in enumerate(lines) if l.strip() == dash) + 1
            end = next(i for i in range(start, len(lines)) if lines[i].strip() == dash)
            return [l.rstrip("\n") for l in lines[start:end] if l.strip()]
        except StopIteration:
            return []

    def _parse_items(section: str) -> dict[str, dict[str, float]]:
        items: dict[str, dict[str, float]] = {}
        for line in _extract_table(section):
            name = line[:35].rstrip()
            rest = line[35:].strip()
            m = re.match(r"^(\d+)\s+\$([0-9]+(?:\.[0-9]+)?)\s+\$([0-9]+(?:\.[0-9]+)?)$", rest)
            if not name or not m:
                continue
            items[name] = {"qty": int(m.group(1)), "unit_price": float(m.group(2)), "total": float(m.group(3))}
        return items

    po_section, invoice_section = _split_po_invoice(document)
    po_items = _parse_items(po_section)
    inv_items = _parse_items(invoice_section)

    for name, po in po_items.items():
        inv = inv_items.get(name)
        if not inv:
            continue

        if int(inv["qty"]) != int(po["qty"]):
            env.step(
                session_id=session_id,
                action=Action(
                    action_type=ActionType.FLAG_VIOLATION,
                    field=f"qty_mismatch:{name}",
                    reason=f"Quantity differs for '{name}': PO {po['qty']} vs Invoice {inv['qty']}",
                    severity="major",
                ),
            )

        if abs(float(inv["unit_price"]) - float(po["unit_price"])) > 0.01:
            env.step(
                session_id=session_id,
                action=Action(
                    action_type=ActionType.FLAG_VIOLATION,
                    field=f"price_mismatch:{name}",
                    reason=f"Unit price differs for '{name}': PO ${po['unit_price']:.2f} vs Invoice ${inv['unit_price']:.2f}",
                    severity="major",
                ),
            )

    if "Tax (10%)" in invoice_section or "Tax (10%):" in invoice_section:
        env.step(
            session_id=session_id,
            action=Action(
                action_type=ActionType.FLAG_VIOLATION,
                field="tax_rate_error",
                reason="Invoice tax label shows 10% (expected 8%).",
                severity="major",
            ),
        )

    if "PO Reference:" not in invoice_section:
        env.step(
            session_id=session_id,
            action=Action(
                action_type=ActionType.FLAG_VIOLATION,
                field="missing_po_reference",
                reason="Invoice header does not include 'PO Reference: PO-xxxxx'.",
                severity="minor",
            ),
        )

    env.step(session_id=session_id, action=Action(action_type=ActionType.SUBMIT))
    return _safe_grade(session_id=session_id).score


def _run_task3_rule_based(session_id: str, document: str) -> float:
    doc_lower = document.lower()
    clause_keywords = {
        "data_retention_period": ["data retention:", "24 months", "permanently deleted"],
        "user_consent_mechanism": ["consent:", "explicit consent", "withdrawn"],
        "right_to_deletion": ["right to erasure:", "request deletion", "processed within 30 days"],
        "breach_notification_timeline": ["data breach notification:", "within 72 hours"],
        "third_party_sharing": ["third party sharing:", "do not sell", "service providers"],
        "data_minimization": ["data minimization:", "minimum personal data"],
        "user_access_rights": ["access rights:", "access, correct, and export"],
        "cookie_policy": ["cookies:", "analytics cookies", "opt out"],
        "childrens_data": ["children's privacy:", "under 13"],
        "contact_information": ["contact:", "data protection officer", "privacy@"],
        "policy_update_notification": ["policy updates:", "at least 30 days"],
        "data_transfer_safeguards": ["international transfers:", "outside the eea", "standard contractual clauses"],
    }

    severity_map = {
        "user_consent_mechanism": "critical",
        "right_to_deletion": "critical",
        "breach_notification_timeline": "critical",
        "data_retention_period": "major",
        "third_party_sharing": "major",
        "data_minimization": "major",
        "user_access_rights": "major",
        "childrens_data": "major",
        "data_transfer_safeguards": "major",
        "cookie_policy": "minor",
        "contact_information": "minor",
        "policy_update_notification": "minor",
    }

    for clause, keywords in clause_keywords.items():
        if not any(kw in doc_lower for kw in keywords):
            env.step(
                session_id=session_id,
                action=Action(
                    action_type=ActionType.FLAG_VIOLATION,
                    field=clause,
                    reason=f"No indicators found for {clause} in policy document",
                    severity=severity_map.get(clause, "minor"),
                ),
            )

    env.step(session_id=session_id, action=Action(action_type=ActionType.SUBMIT))
    return _safe_grade(session_id=session_id).score


def _task1_system_prompt() -> str:
    return """You are a document auditing agent for employment contracts.
Return ONLY one JSON object with the next action.

Allowed actions:
- {"_thought":"<your step-by-step reasoning>","action_type":"mark_field_present","field":"<one of: party_a, party_b, effective_date, termination_clause, governing_law, signature_block>"}
- {"_thought":"<your step-by-step reasoning>","action_type":"mark_field_missing","field":"<same field>","reason":"<short reason>"}
- {"_thought":"<your reasoning>","action_type":"submit"}

Rules:
- You MUST always output `_thought` first before `action_type`.
- Mark a field present only if it is clearly present in the document.
- Mark a field missing only if it is clearly absent.
- Do not repeat actions already reflected in current_confirmations/current_flags.
- Submit only after you have assessed all 6 fields."""


def _task2_system_prompt() -> str:
    return """You are a document auditing agent for invoice vs purchase order validation.
Return ONLY one JSON object with the next action.

Allowed actions:
- {"_thought":"<your step-by-step math comparison>","action_type":"flag_violation","field":"qty_mismatch:<exact item name>","severity":"major","reason":"<short reason>"}
- {"_thought":"<your step-by-step math comparison>","action_type":"flag_violation","field":"price_mismatch:<exact item name>","severity":"major","reason":"<short reason>"}
- {"_thought":"<your reasoning>","action_type":"flag_violation","field":"tax_rate_error","severity":"major","reason":"<short reason>"}
- {"_thought":"<your reasoning>","action_type":"flag_violation","field":"missing_po_reference","severity":"minor","reason":"<short reason>"}
- {"_thought":"<your reasoning>","action_type":"submit"}

Rules:
- You MUST always output `_thought` first before `action_type`. Physically compare quantities and prices.
- Use the exact item name from the document table after qty_mismatch: or price_mismatch:.
- Only flag real violations.
- Submit only after checking all item lines, tax, and PO reference."""


def _task3_system_prompt() -> str:
    return """You are a document auditing agent for privacy policy compliance.
Return ONLY one JSON object with the next action.

Allowed actions:
- {"_thought":"<your step-by-step reasoning>","action_type":"flag_violation","field":"<one of the 12 clause names>","severity":"critical|major|minor","reason":"<short reason>"}
- {"_thought":"<your reasoning>","action_type":"submit"}

Rules:
- You MUST always output `_thought` first before `action_type`.
- Flag only missing clauses.
- Use the correct severity for each missing clause.
- Submit only after checking all 12 required clauses."""


def _run_groq_task(session_id: str, observation: Any, task_id: int) -> float:
    obs = _as_dict(observation)
    if task_id == 1:
        return _run_llm_episode(
            session_id=session_id,
            observation=obs,
            task_id=1,
            system_prompt=_task1_system_prompt(),
            allowed_actions=["mark_field_present", "mark_field_missing", "submit"],
            fallback_runner=_run_task1_rule_based,
        )
    if task_id == 2:
        return _run_llm_episode(
            session_id=session_id,
            observation=obs,
            task_id=2,
            system_prompt=_task2_system_prompt(),
            allowed_actions=["flag_violation", "submit"],
            fallback_runner=_run_task2_rule_based,
        )
    return _run_llm_episode(
        session_id=session_id,
        observation=obs,
        task_id=3,
        system_prompt=_task3_system_prompt(),
        allowed_actions=["flag_violation", "submit"],
        fallback_runner=_run_task3_rule_based,
    )


def run_baseline_internal(seeds: Optional[Dict[int, int]] = None) -> Dict[str, Any]:
    """Run pure rule-based baseline agent on all 3 tasks with configurable seeds."""
    seeds = _normalize_seeds(seeds)
    scores: Dict[str, float] = {}
    details: Dict[str, Any] = {}
    agent_type = "rule_based_keyword_matching"
    from app.curriculum import curriculum

    for task_id, seed in seeds.items():
        session_id, observation = env.reset(task_id=task_id, seed=seed)
        score = _run_rule_based_for_task(task_id, session_id, observation)

        scores[f"task_{task_id}"] = score
        state = env.state(session_id)
        details[f"task_{task_id}"] = {
            "seed": seed,
            "cumulative_reward": state["cumulative_reward"],
            "steps_taken": state["steps_taken"],
            "final_score": score,
            "agent_type": agent_type,
            "model": None,
        }

    average = round(sum(scores.values()) / len(scores), 4)
    curriculum.record_score(average)
    return {
        "scores": scores,
        "details": details,
        "average_score": average,
        "agent_type": agent_type,
        "groq_available": _groq_client() is not None,
        "model": None,
        "fallback_used": False,
        "curriculum": curriculum.get_stats(),
    }


def _baseline_parallel_llm_tasks_enabled() -> bool:
    # Default off: three parallel episodes triple TPM bursts on org on_demand limits.
    return os.environ.get("GROQ_BASELINE_PARALLEL", "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _llm_baseline_one_task(
    task_id: int,
    seed: int,
    client: Optional[OpenAI],
    model_name: str,
) -> Dict[str, Any]:
    """Run one task's LLM (or rule) episode. Safe to call from worker threads."""
    session_id, observation = env.reset(task_id=task_id, seed=seed)
    task_key = f"task_{task_id}"
    task_agent_type = "rule_based_keyword_matching"
    err: Optional[str] = None

    if client is not None:
        try:
            score = _run_groq_task(session_id, observation, task_id)
            task_agent_type = f"groq_llm_{model_name}"
        except (AuthenticationError, RateLimitError, BadRequestError, APIError) as exc:
            err = str(exc)
            score = _run_rule_based_for_task(task_id, session_id, observation)
        except Exception as exc:
            err = f"Unexpected LLM error: {exc}"
            score = _run_rule_based_for_task(task_id, session_id, observation)
    else:
        score = _run_rule_based_for_task(task_id, session_id, observation)

    state = env.state(session_id)
    details = {
        "seed": seed,
        "steps_taken": state["steps_taken"],
        "cumulative_reward": state["cumulative_reward"],
        "final_score": score,
        "agent_type": task_agent_type,
        "model": model_name if "groq_llm" in task_agent_type else None,
    }
    return {
        "task_id": task_id,
        "task_key": task_key,
        "score": score,
        "details": details,
        "error": err,
        "task_agent_type": task_agent_type,
    }


def _run_rule_based_for_task(task_id: int, session_id: str, observation: Any) -> float:
    document = _as_dict(observation)["document_text"]
    if task_id == 1:
        return _run_task1_rule_based(session_id, document)
    if task_id == 2:
        return _run_task2_rule_based(session_id, document)
    return _run_task3_rule_based(session_id, document)


def run_llm_agent(seeds: Optional[Dict[int, int]] = None) -> Dict[str, Any]:
    """
    Run Groq-backed baseline with resilient per-task fallback.
    If Groq fails (invalid key, rate limit, bad model, API issues), we fall back
    to rule-based logic for that task and return the error in payload.
    """
    seeds = _normalize_seeds(seeds)
    scores: Dict[str, float] = {}
    details: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    fallback_used = False

    client = _groq_client()
    model_name = _active_groq_model()
    groq_available = client is not None
    from app.curriculum import curriculum

    t0 = time.perf_counter()
    parallel = _baseline_parallel_llm_tasks_enabled() and client is not None
    rows_by_tid: Dict[int, Dict[str, Any]] = {}

    if parallel:
        with ThreadPoolExecutor(max_workers=3) as pool:
            future_map = {
                pool.submit(_llm_baseline_one_task, tid, seeds[tid], client, model_name): tid
                for tid in (1, 2, 3)
            }
            for fut in as_completed(future_map):
                row = fut.result()
                rows_by_tid[row["task_id"]] = row
    else:
        for tid in (1, 2, 3):
            rows_by_tid[tid] = _llm_baseline_one_task(tid, seeds[tid], client, model_name)

    for tid in (1, 2, 3):
        row = rows_by_tid[tid]
        scores[row["task_key"]] = row["score"]
        details[row["task_key"]] = row["details"]
        if row.get("error"):
            fallback_used = True
            errors[row["task_key"]] = row["error"]

    average = round(sum(scores.values()) / len(scores), 4)
    curriculum.record_score(average)
    elapsed = round(time.perf_counter() - t0, 2)
    result = {
        "scores": scores,
        "details": details,
        "average_score": average,
        "agent_type": f"groq_llm_{model_name}" if groq_available else "rule_based_keyword_matching",
        "groq_available": groq_available,
        "fallback_used": fallback_used or (not groq_available),
        "meta": {
            "model": model_name,
            "elapsed_sec": elapsed,
            "parallel_tasks": parallel,
            "groq_speed": {
                "doc_char_budget_t1": _llm_doc_char_budget(1),
                "doc_char_budget_t2": _llm_doc_char_budget(2),
                "doc_char_budget_t3": _llm_doc_char_budget(3),
                "max_tokens": _active_max_tokens(),
                "history_tail": _history_tail_limit(),
                "serialize_groq_calls": _groq_baseline_serialize_requests(),
                "rate_limit_max_retries": _groq_baseline_max_retries(),
            },
        },
    }
    if errors:
        result["errors"] = errors
    try:
        from app.curriculum import curriculum
        result["curriculum"] = curriculum.get_stats()
    except Exception:
        # Non-fatal: keep baseline response available even if curriculum metadata fails.
        pass
    return result
