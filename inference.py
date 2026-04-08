"""
Inference Script — OpenEnv Document Compliance Auditing
===================================
MANDATORY environment variables:
    API_BASE_URL   The API endpoint for the LLM
    MODEL_NAME     The model identifier to use for inference
    HF_TOKEN       Your Hugging Face / API key

Optional:
    LOCAL_IMAGE_NAME  When using from_docker_image()
    OPENENV_BASE_URL  The OpenEnv environment URL (default: HF Space)
"""

import os
import json
import re
import requests
import textwrap
from typing import List, Dict, Any, Optional
from openai import OpenAI

# ─── Environment Variables ────────────────────────────────────────────────────
# Defaults set ONLY for API_BASE_URL and MODEL_NAME (not HF_TOKEN)
API_BASE_URL     = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME       = os.getenv("MODEL_NAME", "nvidia/Llama-3.1-Nemotron-70B-Instruct-FP8")
HF_TOKEN         = os.getenv("HF_TOKEN")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")
OPENENV_URL      = os.getenv("OPENENV_BASE_URL", "https://aakama-openenv-compliance.hf.space")

# API_KEY: prefer API_KEY env var (injected by validator), fallback to HF_TOKEN
API_KEY = os.getenv("API_KEY") or os.getenv("HF_TOKEN") or "dummy-key"

MAX_STEPS   = 30
TEMPERATURE = 0.1
MAX_TOKENS  = 300
SEEDS       = {1: 42, 2: 42, 3: 42}

# ─── OpenAI Client ────────────────────────────────────────────────────────────
# ALWAYS initialize with API_BASE_URL and API_KEY from environment
try:
    client = OpenAI(
        base_url=API_BASE_URL,
        api_key=API_KEY,
    )
    print(f"[INFO] OpenAI client initialized base_url={API_BASE_URL} model={MODEL_NAME}", flush=True)
except Exception as e:
    print(f"[ERROR] Failed to initialize OpenAI client: {e}", flush=True)
    raise

# ─── System Prompts ───────────────────────────────────────────────────────────
SYSTEM_PROMPTS = {
    1: textwrap.dedent("""
        You are an expert compliance auditor reviewing an employment contract.
        Your job is to check whether 6 required fields are present:
          party_a, party_b, effective_date, termination_clause, governing_law, signature_block

        Reply with exactly one JSON action object. No explanation, no markdown, just JSON.

        Available actions:
          {"action_type": "mark_field_present", "field": "<field_name>"}
          {"action_type": "mark_field_missing", "field": "<field_name>", "reason": "<why>"}
          {"action_type": "submit"}

        Rules:
        - Check each field one at a time
        - After checking all 6 fields, use submit
        - Only use field names from the list above
    """).strip(),

    2: textwrap.dedent("""
        You are an expert compliance auditor comparing an invoice against a purchase order.
        Your job is to find discrepancies between the two documents.

        Reply with exactly one JSON action object. No explanation, no markdown, just JSON.

        Available actions:
          {"action_type": "flag_violation", "field": "<violation>", "reason": "<why>", "severity": "critical|major|minor"}
          {"action_type": "submit"}

        Violation types to check:
          - qty_mismatch:<item_name>     (quantity differs)
          - price_mismatch:<item_name>   (unit price differs)
          - tax_rate_error               (tax rate wrong, should be 8%)
          - missing_po_reference         (invoice missing PO number)

        Rules:
        - Only flag real violations you can see in the documents
        - False positives are penalized
        - Use submit when you have flagged all violations
    """).strip(),

    3: textwrap.dedent("""
        You are an expert GDPR compliance auditor reviewing a company privacy policy.
        Your job is to find which required compliance clauses are MISSING.

        Reply with exactly one JSON action object. No explanation, no markdown, just JSON.

        Available actions:
          {"action_type": "flag_violation", "field": "<clause_name>", "reason": "<why>", "severity": "critical|major|minor"}
          {"action_type": "submit"}

        Required clauses to check (flag only MISSING ones):
          critical: user_consent_mechanism, right_to_deletion, breach_notification_timeline
          major: data_retention_period, third_party_sharing, data_minimization,
                 user_access_rights, childrens_data, data_transfer_safeguards
          minor: cookie_policy, contact_information, policy_update_notification

        Rules:
        - Only flag clauses that are genuinely absent from the document
        - Assign correct severity (critical/major/minor) as listed above
        - Use submit when done checking all clauses
    """).strip(),
}

# ─── Environment API Helpers ──────────────────────────────────────────────────

def env_reset(task_id: int, seed: int) -> Dict[str, Any]:
    r = requests.post(f"{OPENENV_URL}/reset", params={"task_id": task_id, "seed": seed})
    r.raise_for_status()
    return r.json()

def env_step(session_id: str, action: Dict) -> Dict[str, Any]:
    r = requests.post(
        f"{OPENENV_URL}/step",
        params={"session_id": session_id},
        json=action,
    )
    r.raise_for_status()
    return r.json()

def env_grade(session_id: str) -> Dict[str, Any]:
    r = requests.post(f"{OPENENV_URL}/grader", params={"session_id": session_id})
    r.raise_for_status()
    return r.json()

# ─── Action Parser ────────────────────────────────────────────────────────────

ACTION_PATTERN = re.compile(r'\{.*\}', re.DOTALL)

def parse_action(raw: str) -> Dict[str, Any]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("```").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = ACTION_PATTERN.search(raw)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"action_type": "submit"}

# ─── LLM Agent ────────────────────────────────────────────────────────────────

def get_next_action(
    task_id: int,
    observation: Dict[str, Any],
    history: List[Dict],
) -> Dict[str, Any]:
    messages = [{"role": "system", "content": SYSTEM_PROMPTS[task_id]}]
    messages.extend(history[-8:])

    user_content = f"""
DOCUMENT:
{observation['document_text'][:4000]}

Current flags raised: {observation['current_flags']}
Current confirmations: {observation['current_confirmations']}
Steps taken: {observation['steps_taken']}/{observation['max_steps']}
Cumulative reward so far: {observation['cumulative_reward']}

What is your next action? Reply with JSON only.
""".strip()

    messages.append({"role": "user", "content": user_content})

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        raw = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[WARNING] LLM call failed: {e}, using submit fallback", flush=True)
        raw = '{"action_type": "submit"}'

    action = parse_action(raw)
    history.append({"role": "user", "content": user_content})
    history.append({"role": "assistant", "content": raw})

    return action

# ─── Run One Task Episode ─────────────────────────────────────────────────────

def run_task(task_id: int, seed: int) -> float:
    print(f"[START] task=task_{task_id}", flush=True)

    try:
        result = env_reset(task_id=task_id, seed=seed)
    except Exception as e:
        print(f"[ERROR] reset failed: {e}", flush=True)
        print(f"[END] task=task_{task_id} score=0.0 steps=0", flush=True)
        return 0.0

    session_id = result["session_id"]
    observation = result["observation"]

    history = []
    max_steps = min(observation["max_steps"], MAX_STEPS)
    last_reward = 0.0

    for step_num in range(max_steps):
        try:
            action = get_next_action(task_id, observation, history)
            step_result = env_step(session_id=session_id, action=action)
            observation = step_result["observation"]
            last_reward = step_result["reward"]
            print(f"[STEP] step={step_num + 1} reward={last_reward}", flush=True)
            if step_result["done"]:
                break
        except Exception as e:
            print(f"[WARNING] step {step_num+1} failed: {e}", flush=True)
            break

    try:
        grade_result = env_grade(session_id=session_id)
        score = grade_result["score"]
        total_steps = grade_result["total_steps"]
    except Exception as e:
        print(f"[WARNING] grading failed: {e}", flush=True)
        score = 0.0
        total_steps = step_num + 1

    print(f"[END] task=task_{task_id} score={score} steps={total_steps}", flush=True)
    return score

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    try:
        r = requests.get(f"{OPENENV_URL}/health", timeout=10)
        r.raise_for_status()
        print(f"[INFO] Environment reachable at {OPENENV_URL}", flush=True)
    except Exception as e:
        print(f"[ERROR] Environment not reachable: {e}", flush=True)
        return

    scores = {}
    for task_id, seed in SEEDS.items():
        try:
            score = run_task(task_id=task_id, seed=seed)
        except Exception as e:
            print(f"[ERROR] task_{task_id} failed: {e}", flush=True)
            score = 0.0
        scores[f"task_{task_id}"] = score

    average = sum(scores.values()) / len(scores)

    output = {
        "model": MODEL_NAME,
        "api_base_url": API_BASE_URL,
        "environment": OPENENV_URL,
        "seeds": SEEDS,
        "scores": scores,
        "average_score": round(average, 4),
    }

    with open("baseline_scores.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"[SUMMARY] average_score={round(average, 4)} model={MODEL_NAME}", flush=True)
    return output


if __name__ == "__main__":
    main()
