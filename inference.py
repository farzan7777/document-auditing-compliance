"""
Inference Script — OpenEnv Document Compliance Auditing
===================================
MANDATORY environment variables (injected by hackathon):
    API_BASE_URL   The LiteLLM proxy endpoint
    API_KEY        The LiteLLM proxy key

Optional:
    MODEL_NAME       The model identifier (has default)
    OPENENV_BASE_URL The OpenEnv environment URL (has default)
"""

import os
import json
import re
import requests
import textwrap
from typing import List, Dict, Any

# ─── Environment Variables ────────────────────────────────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "").rstrip("/")
API_KEY      = os.environ.get("API_KEY", "")
MODEL_NAME   = os.environ.get("MODEL_NAME", "nvidia/Llama-3.1-Nemotron-70B-Instruct-FP8")
OPENENV_URL  = os.environ.get("OPENENV_BASE_URL", "https://aakama-openenv-compliance.hf.space").rstrip("/")

MAX_STEPS   = 30
TEMPERATURE = 0.1
MAX_TOKENS  = 300
SEEDS       = {1: 42, 2: 42, 3: 42}

# ─── Validate required env vars ──────────────────────────────────────────────
missing = []
if not API_BASE_URL:
    missing.append("API_BASE_URL")
if not API_KEY:
    missing.append("API_KEY")
if missing:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(missing)}\n"
        f"These are injected automatically by the hackathon platform.\n"
        f"Do NOT run this script locally without setting them first."
    )

print(f"[INFO] API_BASE_URL={API_BASE_URL}", flush=True)
print(f"[INFO] MODEL_NAME={MODEL_NAME}", flush=True)
print(f"[INFO] OPENENV_URL={OPENENV_URL}", flush=True)

# ─── LLM call via raw requests ───────────────────────────────────────────────
def call_llm(messages: list) -> str:
    """
    Calls the LiteLLM proxy directly using requests.
    Tries /chat/completions, falls back to /v1/chat/completions if needed.
    """
    endpoints_to_try = [
        f"{API_BASE_URL}/chat/completions",
        f"{API_BASE_URL}/v1/chat/completions",
    ]

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
    }

    last_error = None
    for url in endpoints_to_try:
        try:
            print(f"[DEBUG] Trying LLM endpoint: {url}", flush=True)
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            print(f"[DEBUG] LLM response received ({len(content)} chars)", flush=True)
            return content
        except requests.exceptions.HTTPError as e:
            print(f"[DEBUG] HTTP error on {url}: {e} — {response.text[:200]}", flush=True)
            last_error = e
            continue
        except Exception as e:
            print(f"[DEBUG] Error on {url}: {e}", flush=True)
            last_error = e
            continue

    raise RuntimeError(f"All LLM endpoints failed. Last error: {last_error}")

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
    r = requests.post(
        f"{OPENENV_URL}/reset",
        params={"task_id": task_id, "seed": seed},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()

def env_step(session_id: str, action: Dict) -> Dict[str, Any]:
    r = requests.post(
        f"{OPENENV_URL}/step",
        params={"session_id": session_id},
        json=action,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()

def env_grade(session_id: str) -> Dict[str, Any]:
    r = requests.post(
        f"{OPENENV_URL}/grader",
        params={"session_id": session_id},
        timeout=30,
    )
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

    user_content = textwrap.dedent(f"""
        DOCUMENT:
        {observation['document_text'][:4000]}

        Current flags raised: {observation['current_flags']}
        Current confirmations: {observation['current_confirmations']}
        Steps taken: {observation['steps_taken']}/{observation['max_steps']}
        Cumulative reward so far: {observation['cumulative_reward']}

        What is your next action? Reply with JSON only.
    """).strip()

    messages.append({"role": "user", "content": user_content})

    try:
        raw = call_llm(messages)
    except Exception as e:
        print(f"[WARN] LLM call failed: {e} — defaulting to submit", flush=True)
        raw = '{"action_type": "submit"}'

    action = parse_action(raw)

    history.append({"role": "user", "content": user_content})
    history.append({"role": "assistant", "content": raw})

    return action

# ─── Run One Task Episode ─────────────────────────────────────────────────────

def run_task(task_id: int, seed: int) -> float:
    # ✅ Required [START] block
    print(f"[START] task=task_{task_id}", flush=True)

    result = env_reset(task_id=task_id, seed=seed)
    session_id = result["session_id"]
    observation = result["observation"]

    history = []
    max_steps = min(observation["max_steps"], MAX_STEPS)
    last_reward = 0.0

    for step_num in range(max_steps):
        action = get_next_action(task_id, observation, history)

        step_result = env_step(session_id=session_id, action=action)
        observation = step_result["observation"]
        last_reward = step_result["reward"]

        # ✅ Required [STEP] block
        print(f"[STEP] step={step_num + 1} reward={last_reward}", flush=True)

        if step_result["done"]:
            break

    grade_result = env_grade(session_id=session_id)
    score = grade_result["score"]
    total_steps = grade_result["total_steps"]

    # ✅ Required [END] block
    print(f"[END] task=task_{task_id} score={score} steps={total_steps}", flush=True)

    return score

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    # Verify OpenEnv environment is reachable
    try:
        r = requests.get(f"{OPENENV_URL}/health", timeout=15)
        r.raise_for_status()
        print("[INFO] OpenEnv health check passed.", flush=True)
    except Exception as e:
        print(f"[ERROR] OpenEnv not reachable: {e}", flush=True)
        raise

    scores = {}
    for task_id, seed in SEEDS.items():
        score = run_task(task_id=task_id, seed=seed)
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


# ═══════════════════════════════════════════════════════════════════════════════
# NEW MULTI-AGENT FUNCTIONS BELOW
# Everything above this line is 100% UNCHANGED from original
# These new functions show Theme #1 + #4 in action
# ═══════════════════════════════════════════════════════════════════════════════


# ─── New Multi-Agent API Helpers ──────────────────────────────────────────────

def env_multi_reset(task_id: int, seed: int) -> Dict[str, Any]:
    """
    NEW — Calls /multi/reset instead of /reset.
    Returns difficulty level + curriculum stats alongside observation.
    """
    r = requests.post(
        f"{OPENENV_URL}/multi/reset",
        params={"task_id": task_id, "seed": seed},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def env_multi_grade(session_id: str) -> Dict[str, Any]:
    """
    NEW — Calls /multi/grade instead of /grader.
    Returns both auditor + verifier scores and all decisions.
    """
    r = requests.post(
        f"{OPENENV_URL}/multi/grade",
        params={"session_id": session_id},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def env_curriculum_stats() -> Dict[str, Any]:
    """
    NEW — Gets current curriculum stats.
    Shows judges the difficulty progression.
    """
    r = requests.get(
        f"{OPENENV_URL}/curriculum/stats",
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


# ─── Multi-Agent Episode Runner ───────────────────────────────────────────────

def run_task_multi(task_id: int, seed: int) -> Dict[str, Any]:
    """
    NEW — Runs one episode with full multi-agent system.

    Shows:
    1. Curriculum decides difficulty level
    2. Auditor agent reads document and flags violations
    3. Verifier agent checks auditor findings
    4. Both agents get scored
    5. Curriculum records score for next episode

    This is the function judges run to see Theme #1 + #4 working.
    """

    # ✅ Required [START] block — same format as original
    print(f"[START] task=task_{task_id}", flush=True)

    # ── Step 1: Multi-agent reset (shows curriculum level) ────────────────────
    result = env_multi_reset(task_id=task_id, seed=seed)
    session_id = result["session_id"]
    observation = result["observation"]
    difficulty = result.get("difficulty_level", 1)
    level_name = result.get("level_name", "Level 1")

    print(f"[CURRICULUM] difficulty={difficulty} level={level_name}", flush=True)

    # ── Step 2: Auditor agent acts (same as original run_task) ────────────────
    history = []
    max_steps = min(observation["max_steps"], MAX_STEPS)
    last_reward = 0.0

    for step_num in range(max_steps):
        action = get_next_action(task_id, observation, history)

        step_result = env_step(session_id=session_id, action=action)
        observation = step_result["observation"]
        last_reward = step_result["reward"]

        # ✅ Required [STEP] block — same format as original
        print(f"[STEP] step={step_num + 1} reward={last_reward}", flush=True)

        if step_result["done"]:
            break

    # ── Step 3: Get multi-agent grade (verifier checks auditor) ───────────────
    try:
        multi_result = env_multi_grade(session_id=session_id)

        auditor_score  = multi_result.get("auditor_score", 0.0)
        verifier_score = multi_result.get("verifier_score", 0.0)
        combined_score = multi_result.get("combined_score", 0.0)
        decisions      = multi_result.get("verifier_decisions", [])
        summary        = multi_result.get("verifier_summary", {})
        feedback       = multi_result.get("feedback", "")

        # Print multi-agent results clearly for judges
        print(f"[AUDITOR]  score={auditor_score}", flush=True)
        print(f"[VERIFIER] score={verifier_score}", flush=True)
        print(f"[COMBINED] score={combined_score}", flush=True)
        print(f"[FEEDBACK] {feedback}", flush=True)

        # Print verifier decisions so judges see Theme #1 working
        print(f"[VERIFIER] checked={summary.get('total_checked', 0)} "
              f"approved={summary.get('approved', 0)} "
              f"rejected={summary.get('rejected', 0)} "
              f"hallucinations_caught={summary.get('hallucinations_caught', 0)}",
              flush=True)

        # Print each verifier decision
        for d in decisions:
            symbol = "✅" if d["decision"] == "APPROVE" else "❌"
            print(f"[VERIFIER] {symbol} {d['decision']} {d['finding']} — {d['reason']}", flush=True)

        total_steps = multi_result.get("total_steps", step_num + 1)

    except Exception as e:
        # If multi grade fails fall back to regular grade
        print(f"[WARN] Multi grade failed: {e} — using regular grade", flush=True)
        grade_result = env_grade(session_id=session_id)
        combined_score = grade_result["score"]
        total_steps = grade_result["total_steps"]
        multi_result = {"combined_score": combined_score}

    # ✅ Required [END] block — same format as original
    print(f"[END] task=task_{task_id} score={combined_score} steps={total_steps}", flush=True)

    return {
        "task_id": task_id,
        "seed": seed,
        "difficulty_level": difficulty,
        "combined_score": combined_score,
        "multi_result": multi_result,
    }


# ─── Multi-Agent Main ─────────────────────────────────────────────────────────

def main_multi():
    """
    NEW — Runs all 3 tasks with full multi-agent system.

    This is the multi-agent version of main().
    Shows Theme #1 (multi-agent) + Theme #4 (curriculum) working together.

    Judges run this to see:
    - Curriculum difficulty progression
    - Auditor + Verifier scores for each task
    - Verifier catching hallucinations
    - Combined reward curves
    """

    # Verify environment is reachable
    try:
        r = requests.get(f"{OPENENV_URL}/health", timeout=15)
        r.raise_for_status()
        print("[INFO] OpenEnv health check passed.", flush=True)
    except Exception as e:
        print(f"[ERROR] OpenEnv not reachable: {e}", flush=True)
        raise

    # Show curriculum stats before starting
    try:
        stats = env_curriculum_stats()
        print(f"[CURRICULUM] Starting at Level {stats['current_level']} "
              f"({stats['level_name']})", flush=True)
    except Exception as e:
        print(f"[WARN] Could not get curriculum stats: {e}", flush=True)

    # Run all 3 tasks with multi-agent system
    results = {}
    for task_id, seed in SEEDS.items():
        result = run_task_multi(task_id=task_id, seed=seed)
        results[f"task_{task_id}"] = result

    # Calculate average combined score
    scores = [r["combined_score"] for r in results.values()]
    average = round(sum(scores) / len(scores), 4)

    # Show final curriculum stats after all tasks
    try:
        final_stats = env_curriculum_stats()
        print(f"[CURRICULUM] Final Level: {final_stats['current_level']} "
              f"Rolling Average: {final_stats['rolling_average']}", flush=True)
    except Exception as e:
        print(f"[WARN] Could not get final curriculum stats: {e}", flush=True)

    # Build output
    output = {
        "model": MODEL_NAME,
        "api_base_url": API_BASE_URL,
        "environment": OPENENV_URL,
        "mode": "multi_agent",
        "themes": ["1_multi_agent", "3.1_professional", "4_self_improvement"],
        "seeds": SEEDS,
        "results": results,
        "average_combined_score": average,
    }

    # Save results
    with open("multi_agent_scores.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"[SUMMARY] average_combined_score={average} model={MODEL_NAME}", flush=True)

    return output