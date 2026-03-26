from typing import Dict, List, Any


def grade(
    ground_truth: Dict[str, Any],
    agent_flags: List[str],
) -> Dict[str, Any]:
    """
    Grade task 2: invoice validation.
    ground_truth: {violations: [...], po_number: str, ...}
    agent_flags: list of violation strings flagged by agent
    Returns score 0.0–1.0 with breakdown.
    """
    true_violations = set(ground_truth["violations"])
    agent_set = set(agent_flags)

    true_positives = true_violations & agent_set
    false_positives = agent_set - true_violations
    false_negatives = true_violations - agent_set

    if not true_violations:
        # No violations — agent should not flag anything
        score = 1.0 if not agent_set else max(0.0, 1.0 - len(agent_set) * 0.2)
        return {
            "score": round(score, 4),
            "breakdown": {"no_violations": "Document was clean"},
            "feedback": "No violations present. Agent correctly found nothing." if not agent_set else "No violations present but agent raised false flags.",
            "violations_found": 0,
            "violations_missed": 0,
            "false_positives": len(agent_set),
        }

    # Precision and recall weighted scoring
    precision = len(true_positives) / len(agent_set) if agent_set else 0.0
    recall = len(true_positives) / len(true_violations) if true_violations else 1.0

    # F1-like score with recall weighted more (missing violations is worse)
    if precision + recall == 0:
        f_score = 0.0
    else:
        f_score = (1.5 * precision * recall) / (0.5 * precision + recall)

    final_score = max(0.0, min(1.0, f_score))

    breakdown = {}
    for v in true_violations:
        if v in agent_set:
            breakdown[v] = "✅ correctly flagged"
        else:
            breakdown[v] = "❌ missed"
    for v in false_positives:
        breakdown[v] = "⚠️ false positive — not a real violation"

    feedback_parts = []
    if final_score >= 0.85:
        feedback_parts.append("Excellent invoice audit.")
    elif final_score >= 0.5:
        feedback_parts.append("Partial audit — some violations missed or incorrectly flagged.")
    else:
        feedback_parts.append("Poor audit — most violations were missed or incorrectly flagged.")

    if false_positives:
        feedback_parts.append(f"{len(false_positives)} false positive(s) penalized.")
    if false_negatives:
        feedback_parts.append(f"{len(false_negatives)} violation(s) missed.")

    return {
        "score": round(final_score, 4),
        "breakdown": breakdown,
        "feedback": " ".join(feedback_parts),
        "violations_found": len(true_positives),
        "violations_missed": len(false_negatives),
        "false_positives": len(false_positives),
    }
