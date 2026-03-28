"""
Inference Script — OpenEnv Document Compliance Auditing
===================================
MANDATORY environment variables:
    API_BASE_URL   The API endpoint for the LLM (e.g. https://router.huggingface.co/v1)
    MODEL_NAME     The model identifier to use for inference (e.g. nvidia/Llama-3.1-Nemotron-70B-Instruct)
    HF_TOKEN       Your Hugging Face API key

Usage:
    export API_BASE_URL="https://router.huggingface.co/v1"
    export MODEL_NAME="nvidia/Llama-3.1-Nemotron-70B-Instruct"
    export HF_TOKEN="hf_..."
    export OPENENV_BASE_URL="https://aakama-openenv-compliance.hf.space"
    python inference.py
"""

import os
import json
import re
import requests
import textwrap
from typing import List, Dict, Any, Optional
from openai import OpenAI

# ─── Config ───────────────────────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
MODEL_NAME   = os.getenv("MODEL_NAME")
OPENENV_URL  = os.getenv("OPENENV_BASE_URL", "https://aakama-openenv-compliance.hf.space")

MAX_STEPS    = 30
TEMPERATURE  = 0.1
MAX_TOKENS   = 300
SEEDS        = {1: 42, 2: 42, 3: 42}
DEBUG        = True

# ─── Validate config ──────────────────────────────────────────────────────────
if not API_KEY:
    raise EnvironmentError("HF_TOKEN or API_KEY environment variable not set.")
if not MODEL_NAME:
    raise EnvironmentError("MODEL_NAME environment variable not set.")

# ─── OpenAI client pointing to HF router ─────────────────────────────────────
client = OpenAI(
    base_url=API_BASE_URL,
    api_key=API_KEY,
)

# ─── System prompts per task ──────────────────────────────────────────────────
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

# ─── Environment API helpers ──────────────────────────────────────────────────

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

# ─── Action parser ────────────────────────────────────────────────────────────

ACTION_PATTERN = re.compile(r'\{.*\}', re.DOTALL)

def parse_action(raw: str) -> Dict[str, Any]:
    """Extract JSON action from LLM response."""
    # Strip markdown fences
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("```").strip()

    # Try direct parse first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON object
    match = ACTION_PATTERN.search(raw)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    if DEBUG:
        print(f"  ⚠️  Could not parse action from: {raw[:100]}")

    # Fallback
    return {"action_type": "submit"}

# ─── LLM agent ────────────────────────────────────────────────────────────────

def get_next_action(
    task_id: int,
    observation: Dict[str, Any],
    history: List[Dict],
) -> Dict[str, Any]:
    """Call LLM to get next action given current observation."""

    messages = [{"role": "system", "content": SYSTEM_PROMPTS[task_id]}]

    # Include recent history (last 8 turns)
    messages.extend(history[-8:])

    # Build current user message
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

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )

    raw = response.choices[0].message.content.strip()
    action = parse_action(raw)

    # Add to history
    history.append({"role": "user", "content": user_content})
    history.append({"role": "assistant", "content": raw})

    return action

# ─── Run one task episode ─────────────────────────────────────────────────────

def run_task(task_id: int, seed: int) -> float:
    print(f"\n{'='*55}")
    print(f"  Task {task_id} | seed={seed}")
    print(f"{'='*55}")

    # Reset
    result = env_reset(task_id=task_id, seed=seed)
    session_id = result["session_id"]
    observation = result["observation"]

    print(f"  Task: {observation['task_name']}")
    print(f"  Document: {len(observation['document_text'])} chars")
    print(f"  Max steps: {observation['max_steps']}")

    history = []
    max_steps = min(observation["max_steps"], MAX_STEPS)

    for step_num in range(max_steps):
        # Get action from LLM
        action = get_next_action(task_id, observation, history)

        if DEBUG:
            print(f"  Step {step_num+1:02d}: {action.get('action_type')} | {action.get('field', '')}")

        # Send action to environment
        step_result = env_step(session_id=session_id, action=action)
        observation = step_result["observation"]
        reward = step_result["reward"]

        if DEBUG:
            print(f"           reward={reward['value']:+.3f} | {reward['reason'][:60]}")

        if step_result["done"]:
            print(f"  Episode complete at step {step_num+1}")
            break

    # Get final grade
    grade_result = env_grade(session_id=session_id)
    score = grade_result["score"]

    print(f"\n  ✅ FINAL SCORE: {score:.4f}")
    print(f"  Feedback: {grade_result['feedback']}")
    print(f"  Violations found:  {grade_result['violations_found']}")
    print(f"  Violations missed: {grade_result['violations_missed']}")
    print(f"  False positives:   {grade_result['false_positives']}")

    return score

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n🔍 OpenEnv Document Compliance Auditing — Inference Script")
    print(f"   Model:       {MODEL_NAME}")
    print(f"   API Base:    {API_BASE_URL}")
    print(f"   Environment: {OPENENV_URL}")

    # Verify environment is reachable
    try:
        r = requests.get(f"{OPENENV_URL}/health")
        r.raise_for_status()
        print("   Status:      ✅ environment reachable\n")
    except Exception as e:
        print(f"   Status:      ❌ environment not reachable — {e}")
        return

    # Run all 3 tasks
    scores = {}
    for task_id, seed in SEEDS.items():
        score = run_task(task_id=task_id, seed=seed)
        scores[f"task_{task_id}"] = score

    average = sum(scores.values()) / len(scores)

    # Print summary
    print(f"\n{'='*55}")
    print("  FINAL RESULTS")
    print(f"{'='*55}")
    difficulty = {1: "easy", 2: "medium", 3: "hard"}
    for task, score in scores.items():
        tid = int(task.split("_")[1])
        bar = "█" * int(score * 20)
        print(f"  {task} ({difficulty[tid]}): {score:.4f}  {bar}")
    print(f"\n  Average Score: {average:.4f}")
    print(f"{'='*55}\n")

    # Save results
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

    print("  ✅ Results saved to baseline_scores.json\n")
    return output


if __name__ == "__main__":
    main()