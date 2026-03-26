"""
Baseline inference script using OpenAI API.
Reads OPENAI_API_KEY from environment variables.
Runs GPT model against all 3 tasks and produces reproducible scores.

Usage:
    export OPENAI_API_KEY=sk-...
    export OPENENV_BASE_URL=http://localhost:7860   # or your HF Space URL
    python baseline/run_baseline.py
"""
import os
import json
import requests
from openai import OpenAI

# ─── Config ───────────────────────────────────────────────────────────────────
BASE_URL = os.environ.get("OPENENV_BASE_URL", "http://localhost:7860")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
SEEDS = {1: 42, 2: 42, 3: 42}

if not OPENAI_API_KEY:
    raise EnvironmentError("OPENAI_API_KEY environment variable not set.")

client = OpenAI(api_key=OPENAI_API_KEY)


# ─── Helper: call environment endpoints ──────────────────────────────────────

def env_reset(task_id: int, seed: int) -> dict:
    r = requests.post(f"{BASE_URL}/reset", params={"task_id": task_id, "seed": seed})
    r.raise_for_status()
    return r.json()

def env_step(session_id: str, action: dict) -> dict:
    r = requests.post(
        f"{BASE_URL}/step",
        params={"session_id": session_id},
        json=action,
    )
    r.raise_for_status()
    return r.json()

def env_grade(session_id: str) -> dict:
    r = requests.post(f"{BASE_URL}/grader", params={"session_id": session_id})
    r.raise_for_status()
    return r.json()

def env_tasks() -> dict:
    r = requests.get(f"{BASE_URL}/tasks")
    r.raise_for_status()
    return r.json()


# ─── Agent: call OpenAI to pick next action ───────────────────────────────────

SYSTEM_PROMPT = """You are an expert document compliance auditor AI agent.
You will be given a document to audit and must take actions to identify compliance issues.

You must respond with a JSON object representing your next action. Available action types:
- mark_field_present: {"action_type": "mark_field_present", "field": "<field_name>"}
- mark_field_missing: {"action_type": "mark_field_missing", "field": "<field_name>", "reason": "<why>"}
- flag_violation: {"action_type": "flag_violation", "field": "<violation>", "reason": "<why>", "severity": "critical|major|minor"}
- submit: {"action_type": "submit"}

Respond with ONLY valid JSON. No explanation, no markdown, just the JSON object.
"""

def get_next_action(observation: dict, history: list) -> dict:
    """Ask OpenAI for the next action given current observation."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add history
    for h in history[-6:]:  # Keep last 6 turns to save tokens
        messages.append(h)

    # Current observation
    user_content = f"""
TASK: {observation['task_name']}
INSTRUCTIONS: {observation['instructions'][:500]}
DOCUMENT:
{observation['document_text'][:3000]}

Current flags raised: {observation['current_flags']}
Current confirmations: {observation['current_confirmations']}
Steps taken: {observation['steps_taken']}/{observation['max_steps']}
Cumulative reward: {observation['cumulative_reward']}

What is your next action? Respond with JSON only.
"""
    messages.append({"role": "user", "content": user_content})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.1,
        max_tokens=200,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        action = json.loads(raw)
    except json.JSONDecodeError:
        print(f"  ⚠️  Could not parse action: {raw[:100]}")
        action = {"action_type": "submit"}

    return action


# ─── Run one task episode ─────────────────────────────────────────────────────

def run_task(task_id: int, seed: int) -> float:
    print(f"\n{'='*50}")
    print(f"  Running Task {task_id} (seed={seed})")
    print(f"{'='*50}")

    result = env_reset(task_id=task_id, seed=seed)
    session_id = result["session_id"]
    observation = result["observation"]

    print(f"  Task: {observation['task_name']}")
    print(f"  Document length: {len(observation['document_text'])} chars")

    history = []
    max_steps = observation["max_steps"]

    for step_num in range(max_steps):
        action = get_next_action(observation, history)
        print(f"  Step {step_num+1}: {action.get('action_type')} | {action.get('field', '')}")

        history.append({"role": "assistant", "content": json.dumps(action)})

        step_result = env_step(session_id=session_id, action=action)
        observation = step_result["observation"]
        reward = step_result["reward"]

        print(f"           Reward: {reward['value']:.3f} ({reward['reason'][:60]})")

        if step_result["done"]:
            print(f"  Episode complete at step {step_num+1}")
            break

    # Final grade
    grade_result = env_grade(session_id=session_id)
    score = grade_result["score"]
    print(f"\n  FINAL SCORE: {score:.4f}")
    print(f"  Feedback: {grade_result['feedback']}")
    print(f"  Violations found: {grade_result['violations_found']}")
    print(f"  Violations missed: {grade_result['violations_missed']}")
    print(f"  False positives: {grade_result['false_positives']}")

    return score


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n🔍 OpenEnv Document Compliance Auditing — Baseline Inference")
    print(f"   Model: {MODEL}")
    print(f"   Environment: {BASE_URL}")

    # Verify environment is reachable
    try:
        r = requests.get(f"{BASE_URL}/health")
        r.raise_for_status()
        print("   Environment: ✅ reachable\n")
    except Exception as e:
        print(f"   Environment: ❌ not reachable — {e}")
        print(f"   Make sure the server is running at {BASE_URL}")
        return

    scores = {}
    for task_id, seed in SEEDS.items():
        score = run_task(task_id=task_id, seed=seed)
        scores[f"task_{task_id}"] = score

    average = sum(scores.values()) / len(scores)

    print(f"\n{'='*50}")
    print("  BASELINE RESULTS")
    print(f"{'='*50}")
    for task, score in scores.items():
        difficulty = {"task_1": "easy", "task_2": "medium", "task_3": "hard"}[task]
        bar = "█" * int(score * 20)
        print(f"  {task} ({difficulty}): {score:.4f}  {bar}")
    print(f"\n  Average Score: {average:.4f}")
    print(f"{'='*50}\n")

    # Save results
    output = {
        "model": MODEL,
        "environment": BASE_URL,
        "seeds": SEEDS,
        "scores": scores,
        "average_score": round(average, 4),
    }

    with open("baseline_scores.json", "w") as f:
        json.dump(output, f, indent=2)

    print("  ✅ Results saved to baseline_scores.json")
    return output


if __name__ == "__main__":
    main()
