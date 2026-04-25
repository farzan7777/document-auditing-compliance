from typing import Dict, List, Any
from .score_transform import reward_to_score


def grade(
    ground_truth: Dict[str, bool],
    agent_present: List[str],
    agent_missing: List[str],
    false_positives: int = 0,
) -> Dict[str, Any]:
    """
    Grade task 1: required field detection.
    ground_truth: {field_name: True if present, False if missing}
    agent_present: fields the agent marked as present
    agent_missing: fields the agent marked as missing
    Returns score 0.0–1.0 with breakdown.
    """
    total_fields = len(ground_truth)
    correct = 0
    breakdown = {}

    for field, is_present in ground_truth.items():
        if is_present and field in agent_present:
            correct += 1
            breakdown[field] = "✅ correctly identified as present"
        elif not is_present and field in agent_missing:
            correct += 1
            breakdown[field] = "✅ correctly identified as missing"
        elif is_present and field in agent_missing:
            breakdown[field] = "❌ present but marked as missing (false negative)"
        elif not is_present and field in agent_present:
            breakdown[field] = "❌ missing but marked as present (false positive)"
        else:
            breakdown[field] = "⚠️ not evaluated by agent"

    raw_score = correct / total_fields
    # Penalize false positives
    fp_penalty = min(0.2, false_positives * 0.05)
    final_score = reward_to_score(raw_score - fp_penalty)

    violations_found = len([f for f, p in ground_truth.items() if not p and f in agent_missing])
    violations_missed = len([f for f, p in ground_truth.items() if not p and f not in agent_missing])

    feedback_parts = []
    if final_score >= 0.9:
        feedback_parts.append("Excellent audit — nearly all fields correctly identified.")
    elif final_score >= 0.6:
        feedback_parts.append("Good audit with some missed or incorrect field assessments.")
    else:
        feedback_parts.append("Poor audit — many fields were incorrectly assessed.")

    if false_positives > 0:
        feedback_parts.append(f"Penalized {false_positives} false positive(s).")

    return {
        "score": round(final_score, 4),
        "breakdown": breakdown,
        "feedback": " ".join(feedback_parts),
        "correct_fields": correct,
        "total_fields": total_fields,
        "violations_found": violations_found,
        "violations_missed": violations_missed,
        "false_positives": false_positives,
    }
