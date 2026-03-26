from typing import Dict, List, Any

SEVERITY_WEIGHTS = {
    "critical": 3.0,
    "major": 2.0,
    "minor": 1.0,
}


def grade(
    ground_truth: Dict[str, Any],
    agent_flags: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    Grade task 3: policy compliance audit.
    ground_truth: {missing_clauses: [...], severities: {clause: severity}}
    agent_flags: [{"field": clause_name, "severity": severity}, ...]
    Returns score 0.0–1.0 with breakdown.
    """
    missing_clauses = set(ground_truth["missing_clauses"])
    true_severities = ground_truth["severities"]

    agent_flagged = {f["field"]: f.get("severity", "minor") for f in agent_flags}
    agent_set = set(agent_flagged.keys())

    true_positives = missing_clauses & agent_set
    false_positives = agent_set - missing_clauses
    false_negatives = missing_clauses - agent_set

    # Weighted scoring: more points for finding critical violations
    total_weight = sum(SEVERITY_WEIGHTS.get(true_severities[c], 1.0) for c in missing_clauses)
    earned_weight = 0.0
    severity_bonus = 0.0

    breakdown = {}
    for clause in missing_clauses:
        true_sev = true_severities[clause]
        clause_weight = SEVERITY_WEIGHTS.get(true_sev, 1.0)
        if clause in agent_set:
            earned_weight += clause_weight
            agent_sev = agent_flagged[clause]
            if agent_sev == true_sev:
                severity_bonus += 0.05
                breakdown[clause] = f"✅ found + correct severity ({true_sev})"
            else:
                breakdown[clause] = f"✅ found but wrong severity (got {agent_sev}, expected {true_sev})"
        else:
            breakdown[clause] = f"❌ missed (severity: {true_sev}, weight: {clause_weight})"

    for clause in false_positives:
        breakdown[clause] = "⚠️ false positive — clause is actually present"

    base_score = (earned_weight / total_weight) if total_weight > 0 else 1.0
    fp_penalty = min(0.25, len(false_positives) * 0.05)
    final_score = max(0.0, min(1.0, base_score + severity_bonus - fp_penalty))

    feedback_parts = []
    if final_score >= 0.85:
        feedback_parts.append("Excellent policy audit — most violations found with correct severity.")
    elif final_score >= 0.55:
        feedback_parts.append("Partial audit — critical violations may have been missed.")
    else:
        feedback_parts.append("Poor audit — significant compliance violations were overlooked.")

    critical_missed = [c for c in false_negatives if true_severities.get(c) == "critical"]
    if critical_missed:
        feedback_parts.append(f"WARNING: {len(critical_missed)} CRITICAL clause(s) missed: {', '.join(critical_missed)}.")
    if false_positives:
        feedback_parts.append(f"{len(false_positives)} false positive(s) penalized.")

    return {
        "score": round(final_score, 4),
        "breakdown": breakdown,
        "feedback": " ".join(feedback_parts),
        "violations_found": len(true_positives),
        "violations_missed": len(false_negatives),
        "false_positives": len(false_positives),
        "severity_bonus": round(severity_bonus, 4),
    }
