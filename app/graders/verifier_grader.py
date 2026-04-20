"""
verifier_grader.py — Scores Both Agents (Theme #1 Multi-Agent)
===============================================================
This file scores BOTH the Auditor and Verifier agents.

It answers these questions:
  - Did Auditor find real violations? 
  - Did Verifier correctly approve real findings?
  - Did Verifier correctly reject fake findings?
  - What is the combined score?

Think of this as the JUDGE that scores both players
after a game is finished.

Auditor  → plays the game (finds violations)
Verifier → referees the game (checks findings)
Grader   → scores both after game ends
"""

from typing import Dict, Any, List


# ═══════════════════════════════════════════════════════════════════════════════
# SCORING CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
# These numbers decide how much reward each action gets.
# Positive = reward, Negative = penalty.

# ── Auditor Scores ─────────────────────────────────────────────────────────────
AUDITOR_REAL_APPROVED    =  1.0   # Found real violation + Verifier approved  (perfect)
AUDITOR_REAL_REJECTED    =  0.4   # Found real violation + Verifier rejected  (found but unclear)
AUDITOR_FAKE_APPROVED    = -1.0   # Hallucinated violation + Verifier approved (both fooled, very bad)
AUDITOR_FAKE_REJECTED    = -0.3   # Hallucinated violation + Verifier caught   (auditor wrong, verifier saved it)
AUDITOR_MISSED           = -0.5   # Real violation missed entirely             (auditor failed)

# ── Verifier Scores ────────────────────────────────────────────────────────────
VERIFIER_APPROVED_REAL   =  1.0   # Approved real violation    (correct approval)
VERIFIER_REJECTED_FAKE   =  1.0   # Rejected fake violation    (caught hallucination)
VERIFIER_APPROVED_FAKE   = -1.0   # Approved fake violation    (missed hallucination, bad)
VERIFIER_REJECTED_REAL   = -0.5   # Rejected real violation    (wrong rejection)

# ── Combined Weight ────────────────────────────────────────────────────────────
# Auditor weighted more (0.6) because auditing is the primary job.
# Verifier weighted less (0.4) because it is the oversight role.
AUDITOR_WEIGHT   = 0.6
VERIFIER_WEIGHT  = 0.4


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN GRADER FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def grade_multi_agent(
    task_id: int,
    session: Dict[str, Any],
    verifier_decisions: List[Dict[str, Any]],
    ground_truth: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Score both Auditor and Verifier agents.

    Args:
        task_id: 1, 2, or 3
        session: current session state (has auditor findings)
        verifier_decisions: list of verifier APPROVE/REJECT decisions
        ground_truth: the real answers (what violations actually exist)

    Returns:
        Dictionary with:
          - auditor_score: 0.0 to 1.0
          - verifier_score: 0.0 to 1.0
          - combined_score: 0.0 to 1.0
          - breakdown: detailed scoring breakdown
          - feedback: human readable feedback
    """

    # Route to correct grader based on task
    if task_id == 1:
        return _grade_task1(session, verifier_decisions, ground_truth)
    elif task_id == 2:
        return _grade_task2(session, verifier_decisions, ground_truth)
    elif task_id == 3:
        return _grade_task3(session, verifier_decisions, ground_truth)
    else:
        return _empty_result()


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 1 GRADER — Employment Contract
# ═══════════════════════════════════════════════════════════════════════════════

def _grade_task1(
    session: Dict[str, Any],
    verifier_decisions: List[Dict[str, Any]],
    ground_truth: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Grade Task 1: Employment Contract field detection.

    Ground truth format:
      {"party_a": True, "party_b": False, ...}
      True = field IS present, False = field is MISSING
    """

    # Get what Auditor said
    auditor_missing = session.get("missing_confirmed", [])   # Auditor said these are missing
    auditor_present = session.get("confirmations", [])       # Auditor said these are present

    # Get real answers
    truly_missing = [f for f, present in ground_truth.items() if not present]
    truly_present = [f for f, present in ground_truth.items() if present]

    # Build lookup of verifier decisions
    # Key: "marked_missing:party_a" or "marked_present:party_a"
    verifier_lookup = {}
    for d in verifier_decisions:
        verifier_lookup[d["finding"]] = d["decision"]

    # ── Score Auditor ──────────────────────────────────────────────────────────
    auditor_points = []
    auditor_breakdown = []

    # Check fields Auditor marked as MISSING
    for field in auditor_missing:
        finding_key = f"marked_missing:{field}"
        verifier_decision = verifier_lookup.get(finding_key, "APPROVE")
        is_truly_missing = field in truly_missing

        if is_truly_missing and verifier_decision == "APPROVE":
            # Perfect: found real missing + verifier confirmed
            auditor_points.append(AUDITOR_REAL_APPROVED)
            auditor_breakdown.append(f"✅ {field}: correctly identified as missing (verified)")
        elif is_truly_missing and verifier_decision == "REJECT":
            # Found real missing but verifier disagreed
            auditor_points.append(AUDITOR_REAL_REJECTED)
            auditor_breakdown.append(f"⚠️ {field}: correctly missing but verifier rejected")
        elif not is_truly_missing and verifier_decision == "REJECT":
            # Field is present, auditor wrong, verifier caught it
            auditor_points.append(AUDITOR_FAKE_REJECTED)
            auditor_breakdown.append(f"❌ {field}: field is present — verifier caught error")
        else:
            # Field is present, auditor wrong, verifier also wrong
            auditor_points.append(AUDITOR_FAKE_APPROVED)
            auditor_breakdown.append(f"💥 {field}: field is present — both agents wrong")

    # Check fields Auditor marked as PRESENT
    for field in auditor_present:
        finding_key = f"marked_present:{field}"
        verifier_decision = verifier_lookup.get(finding_key, "APPROVE")
        is_truly_present = field in truly_present

        if is_truly_present and verifier_decision == "APPROVE":
            auditor_points.append(AUDITOR_REAL_APPROVED)
            auditor_breakdown.append(f"✅ {field}: correctly confirmed present (verified)")
        elif is_truly_present and verifier_decision == "REJECT":
            auditor_points.append(AUDITOR_REAL_REJECTED)
            auditor_breakdown.append(f"⚠️ {field}: correctly present but verifier rejected")
        elif not is_truly_present and verifier_decision == "REJECT":
            auditor_points.append(AUDITOR_FAKE_REJECTED)
            auditor_breakdown.append(f"❌ {field}: field is missing — verifier caught error")
        else:
            auditor_points.append(AUDITOR_FAKE_APPROVED)
            auditor_breakdown.append(f"💥 {field}: field is missing — both agents wrong")

    # Penalty for fields Auditor missed entirely
    all_checked = set(auditor_missing + auditor_present)
    all_fields = set(ground_truth.keys())
    missed_fields = all_fields - all_checked

    for field in missed_fields:
        auditor_points.append(AUDITOR_MISSED)
        auditor_breakdown.append(f"❌ {field}: auditor never checked this field")

    # ── Score Verifier ─────────────────────────────────────────────────────────
    verifier_points = []
    verifier_breakdown = []

    for decision in verifier_decisions:
        finding_type = decision.get("finding_type", "unknown")
        dec = decision["decision"]
        field = decision.get("field", "unknown")

        if finding_type == "true_missing" and dec == "APPROVE":
            verifier_points.append(VERIFIER_APPROVED_REAL)
            verifier_breakdown.append(f"✅ {field}: correctly approved real missing field")
        elif finding_type == "false_missing" and dec == "REJECT":
            verifier_points.append(VERIFIER_REJECTED_FAKE)
            verifier_breakdown.append(f"✅ {field}: correctly rejected false missing claim")
        elif finding_type == "false_missing" and dec == "APPROVE":
            verifier_points.append(VERIFIER_APPROVED_FAKE)
            verifier_breakdown.append(f"❌ {field}: missed auditor error — approved false claim")
        elif finding_type == "true_missing" and dec == "REJECT":
            verifier_points.append(VERIFIER_REJECTED_REAL)
            verifier_breakdown.append(f"⚠️ {field}: incorrectly rejected real missing field")
        elif finding_type == "true_present" and dec == "APPROVE":
            verifier_points.append(VERIFIER_APPROVED_REAL)
            verifier_breakdown.append(f"✅ {field}: correctly approved present field")
        elif finding_type == "false_present" and dec == "REJECT":
            verifier_points.append(VERIFIER_REJECTED_FAKE)
            verifier_breakdown.append(f"✅ {field}: correctly rejected false present claim")
        else:
            verifier_points.append(0.0)
            verifier_breakdown.append(f"➖ {field}: neutral decision")

    # ── Calculate Final Scores ─────────────────────────────────────────────────
    return _calculate_final_scores(
        auditor_points, auditor_breakdown,
        verifier_points, verifier_breakdown,
        task_id=1
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 2 GRADER — Invoice vs Purchase Order
# ═══════════════════════════════════════════════════════════════════════════════

def _grade_task2(
    session: Dict[str, Any],
    verifier_decisions: List[Dict[str, Any]],
    ground_truth: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Grade Task 2: Invoice validation.

    Ground truth format:
      {"violations": ["tax_rate_error", "qty_mismatch:item"], ...}
    """

    true_violations = set(ground_truth.get("violations", []))
    auditor_flags = set(session.get("flags_raised", []))

    # Build verifier lookup
    verifier_lookup = {d["finding"]: d["decision"] for d in verifier_decisions}

    # ── Score Auditor ──────────────────────────────────────────────────────────
    auditor_points = []
    auditor_breakdown = []

    for flag in auditor_flags:
        verifier_decision = verifier_lookup.get(flag, "APPROVE")
        is_real = flag in true_violations

        if is_real and verifier_decision == "APPROVE":
            auditor_points.append(AUDITOR_REAL_APPROVED)
            auditor_breakdown.append(f"✅ {flag}: real violation found and verified")
        elif is_real and verifier_decision == "REJECT":
            auditor_points.append(AUDITOR_REAL_REJECTED)
            auditor_breakdown.append(f"⚠️ {flag}: real violation but verifier rejected")
        elif not is_real and verifier_decision == "REJECT":
            auditor_points.append(AUDITOR_FAKE_REJECTED)
            auditor_breakdown.append(f"❌ {flag}: false violation — verifier caught it")
        else:
            auditor_points.append(AUDITOR_FAKE_APPROVED)
            auditor_breakdown.append(f"💥 {flag}: false violation — both agents wrong")

    # Penalty for missed violations
    missed = true_violations - auditor_flags
    for v in missed:
        auditor_points.append(AUDITOR_MISSED)
        auditor_breakdown.append(f"❌ {v}: auditor missed this real violation")

    # ── Score Verifier ─────────────────────────────────────────────────────────
    verifier_points = []
    verifier_breakdown = []

    for decision in verifier_decisions:
        finding = decision["finding"]
        dec = decision["decision"]
        finding_type = decision.get("finding_type", "unknown")

        if finding_type == "true_violation" and dec == "APPROVE":
            verifier_points.append(VERIFIER_APPROVED_REAL)
            verifier_breakdown.append(f"✅ {finding}: correctly approved real violation")
        elif finding_type == "false_violation" and dec == "REJECT":
            verifier_points.append(VERIFIER_REJECTED_FAKE)
            verifier_breakdown.append(f"✅ {finding}: correctly rejected false violation")
        elif finding_type == "false_violation" and dec == "APPROVE":
            verifier_points.append(VERIFIER_APPROVED_FAKE)
            verifier_breakdown.append(f"❌ {finding}: missed false violation")
        elif finding_type == "true_violation" and dec == "REJECT":
            verifier_points.append(VERIFIER_REJECTED_REAL)
            verifier_breakdown.append(f"⚠️ {finding}: incorrectly rejected real violation")
        else:
            verifier_points.append(0.0)
            verifier_breakdown.append(f"➖ {finding}: uncertain decision")

    return _calculate_final_scores(
        auditor_points, auditor_breakdown,
        verifier_points, verifier_breakdown,
        task_id=2
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 3 GRADER — Privacy Policy GDPR
# ═══════════════════════════════════════════════════════════════════════════════

def _grade_task3(
    session: Dict[str, Any],
    verifier_decisions: List[Dict[str, Any]],
    ground_truth: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Grade Task 3: GDPR Privacy Policy audit.

    Ground truth format:
      {"missing_clauses": [...], "severities": {...}}
    """

    true_missing = set(ground_truth.get("missing_clauses", []))
    auditor_flags = set(session.get("flags_raised", []))

    # Build verifier lookup
    verifier_lookup = {d["finding"]: d["decision"] for d in verifier_decisions}

    # ── Score Auditor ──────────────────────────────────────────────────────────
    auditor_points = []
    auditor_breakdown = []

    for flag in auditor_flags:
        verifier_decision = verifier_lookup.get(flag, "APPROVE")
        is_real = flag in true_missing

        if is_real and verifier_decision == "APPROVE":
            auditor_points.append(AUDITOR_REAL_APPROVED)
            auditor_breakdown.append(f"✅ {flag}: real missing clause found and verified")
        elif is_real and verifier_decision == "REJECT":
            auditor_points.append(AUDITOR_REAL_REJECTED)
            auditor_breakdown.append(f"⚠️ {flag}: real missing clause but verifier rejected")
        elif not is_real and verifier_decision == "REJECT":
            auditor_points.append(AUDITOR_FAKE_REJECTED)
            auditor_breakdown.append(f"❌ {flag}: clause present — verifier caught auditor error")
        else:
            auditor_points.append(AUDITOR_FAKE_APPROVED)
            auditor_breakdown.append(f"💥 {flag}: clause present — both agents wrong")

    # Penalty for missed clauses
    missed = true_missing - auditor_flags
    for clause in missed:
        auditor_points.append(AUDITOR_MISSED)
        auditor_breakdown.append(f"❌ {clause}: auditor missed this missing clause")

    # ── Score Verifier ─────────────────────────────────────────────────────────
    verifier_points = []
    verifier_breakdown = []

    for decision in verifier_decisions:
        finding = decision["finding"]
        dec = decision["decision"]
        finding_type = decision.get("finding_type", "unknown")

        if finding_type == "true_violation" and dec == "APPROVE":
            verifier_points.append(VERIFIER_APPROVED_REAL)
            verifier_breakdown.append(f"✅ {finding}: correctly approved real missing clause")
        elif finding_type == "false_violation" and dec == "REJECT":
            verifier_points.append(VERIFIER_REJECTED_FAKE)
            verifier_breakdown.append(f"✅ {finding}: correctly rejected false missing claim")
        elif finding_type == "false_violation" and dec == "APPROVE":
            verifier_points.append(VERIFIER_APPROVED_FAKE)
            verifier_breakdown.append(f"❌ {finding}: missed auditor hallucination")
        elif finding_type == "true_violation" and dec == "REJECT":
            verifier_points.append(VERIFIER_REJECTED_REAL)
            verifier_breakdown.append(f"⚠️ {finding}: incorrectly rejected real missing clause")
        else:
            verifier_points.append(0.0)
            verifier_breakdown.append(f"➖ {finding}: uncertain")

    return _calculate_final_scores(
        auditor_points, auditor_breakdown,
        verifier_points, verifier_breakdown,
        task_id=3
    )


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _calculate_final_scores(
    auditor_points: List[float],
    auditor_breakdown: List[str],
    verifier_points: List[float],
    verifier_breakdown: List[str],
    task_id: int,
) -> Dict[str, Any]:
    """
    Calculate final scores for both agents.
    Normalizes scores to 0.0-1.0 range.
    Combines into weighted final score.
    """

    # Calculate raw auditor score
    if auditor_points:
        # Sum all points
        raw_auditor = sum(auditor_points)
        # Max possible = all correct
        max_auditor = len(auditor_points) * AUDITOR_REAL_APPROVED
        # Normalize to 0-1
        auditor_score = max(0.0, min(1.0, raw_auditor / max_auditor if max_auditor > 0 else 0.0))
    else:
        auditor_score = 0.0

    # Calculate raw verifier score
    if verifier_points:
        raw_verifier = sum(verifier_points)
        max_verifier = len(verifier_points) * VERIFIER_APPROVED_REAL
        verifier_score = max(0.0, min(1.0, raw_verifier / max_verifier if max_verifier > 0 else 0.0))
    else:
        verifier_score = 0.0

    # Calculate combined weighted score
    combined_score = (auditor_score * AUDITOR_WEIGHT) + (verifier_score * VERIFIER_WEIGHT)
    combined_score = round(max(0.0, min(1.0, combined_score)), 4)

    # Generate human readable feedback
    feedback = _generate_feedback(auditor_score, verifier_score, combined_score)

    return {
        "auditor_score": round(auditor_score, 4),
        "verifier_score": round(verifier_score, 4),
        "combined_score": combined_score,
        "auditor_breakdown": auditor_breakdown,
        "verifier_breakdown": verifier_breakdown,
        "feedback": feedback,
        "weights": {
            "auditor": AUDITOR_WEIGHT,
            "verifier": VERIFIER_WEIGHT,
        }
    }


def _generate_feedback(
    auditor_score: float,
    verifier_score: float,
    combined_score: float,
) -> str:
    """Generate simple human readable feedback for judges."""

    if combined_score >= 0.85:
        quality = "Excellent"
        detail = "Both agents performing at expert level."
    elif combined_score >= 0.70:
        quality = "Good"
        detail = "Agents working well together with minor errors."
    elif combined_score >= 0.50:
        quality = "Developing"
        detail = "Agents learning — some errors still present."
    elif combined_score >= 0.30:
        quality = "Struggling"
        detail = "Agents need more training at this difficulty level."
    else:
        quality = "Poor"
        detail = "Agents significantly challenged by this document."

    return (
        f"{quality} multi-agent performance. "
        f"Auditor: {round(auditor_score*100)}%, "
        f"Verifier: {round(verifier_score*100)}%. "
        f"{detail}"
    )


def _empty_result() -> Dict[str, Any]:
    """Return empty result for invalid task."""
    return {
        "auditor_score": 0.0,
        "verifier_score": 0.0,
        "combined_score": 0.0,
        "auditor_breakdown": [],
        "verifier_breakdown": [],
        "feedback": "Invalid task ID",
        "weights": {"auditor": AUDITOR_WEIGHT, "verifier": VERIFIER_WEIGHT}
    }