from app.models import Action, ActionType, Severity
from typing import Dict, Any, Tuple


# ─── Reward Constants ─────────────────────────────────────────────────────────
CORRECT_FLAG = 0.15          # Flagged a real violation
CORRECT_CONFIRM = 0.10       # Correctly confirmed a field present
CORRECT_MISSING = 0.12       # Correctly identified a missing field
FALSE_POSITIVE = -0.10       # Flagged something that isn't a violation
WRONG_FIELD = -0.05          # Flagged correct type but wrong field name
REDUNDANT_ACTION = -0.05     # Same action taken twice
SEVERITY_BONUS = 0.05        # Correct severity on a flag
SEVERITY_WRONG = -0.02       # Wrong severity (partial credit still)
SUBMIT_BONUS = 0.10          # Clean submission with good coverage
SUBMIT_INCOMPLETE = -0.05    # Submitted too early (missed obvious violations)


def compute_step_reward(
    action: Action,
    session: Dict[str, Any],
) -> Tuple[float, str]:
    """
    Compute per-step reward based on action and current session state.
    Returns (reward_value, reason_string).
    """
    task_id = session["task_id"]
    ground_truth = session["ground_truth"]
    flags_raised = session.get("flags_raised", [])
    confirmations = session.get("confirmations", [])
    missing_confirmed = session.get("missing_confirmed", [])

    # ── SUBMIT action ─────────────────────────────────────────────────────────
    if action.action_type == ActionType.SUBMIT:
        if task_id == 1:
            total = len(ground_truth)
            assessed = len(confirmations) + len(missing_confirmed)
            coverage = assessed / total if total > 0 else 0
            if coverage >= 0.8:
                return SUBMIT_BONUS, "Clean submission with good field coverage"
            else:
                return SUBMIT_INCOMPLETE, f"Submitted early — only {assessed}/{total} fields assessed"

        elif task_id == 2:
            true_violations = set(ground_truth.get("violations", []))
            found = set(flags_raised) & true_violations
            coverage = len(found) / len(true_violations) if true_violations else 1.0
            if coverage >= 0.7:
                return SUBMIT_BONUS, "Good violation coverage on submit"
            else:
                return SUBMIT_INCOMPLETE, "Submitted with low violation coverage"

        elif task_id == 3:
            missing = set(ground_truth.get("missing_clauses", []))
            found = set(flags_raised) & missing
            coverage = len(found) / len(missing) if missing else 1.0
            if coverage >= 0.7:
                return SUBMIT_BONUS, "Good clause coverage on submit"
            else:
                return SUBMIT_INCOMPLETE, "Submitted with low clause coverage"

    # ── MARK FIELD PRESENT ────────────────────────────────────────────────────
    if action.action_type == ActionType.MARK_FIELD_PRESENT:
        field = action.field
        if not field:
            return -0.05, "No field specified"
        if field in confirmations:
            return REDUNDANT_ACTION, f"Already confirmed {field} as present"
        if task_id == 1:
            is_present = ground_truth.get(field)
            if is_present is True:
                return CORRECT_CONFIRM, f"Correctly confirmed {field} is present"
            elif is_present is False:
                return FALSE_POSITIVE, f"{field} is actually MISSING — incorrectly marked present"
            else:
                return -0.03, f"Unknown field: {field}"

    # ── MARK FIELD MISSING ────────────────────────────────────────────────────
    if action.action_type == ActionType.MARK_FIELD_MISSING:
        field = action.field
        if not field:
            return -0.05, "No field specified"
        if field in missing_confirmed:
            return REDUNDANT_ACTION, f"Already flagged {field} as missing"
        if task_id == 1:
            is_present = ground_truth.get(field)
            if is_present is False:
                return CORRECT_MISSING, f"Correctly identified {field} as missing"
            elif is_present is True:
                return FALSE_POSITIVE, f"{field} is actually PRESENT — incorrectly marked missing"
            else:
                return -0.03, f"Unknown field: {field}"

    # ── FLAG VIOLATION ────────────────────────────────────────────────────────
    if action.action_type == ActionType.FLAG_VIOLATION:
        field = action.field
        if not field:
            return -0.05, "No field specified for violation flag"

        if field in flags_raised:
            return REDUNDANT_ACTION, f"Already flagged {field}"

        if task_id == 2:
            true_violations = ground_truth.get("violations", [])
            if field in true_violations:
                reward = CORRECT_FLAG
                reason = f"Correctly flagged violation: {field}"
                # Check severity
                if action.severity:
                    sev = action.severity.value if hasattr(action.severity, 'value') else action.severity
                    expected = _get_task2_severity(field)
                    if sev == expected:
                        reward += SEVERITY_BONUS
                        reason += f" with correct severity ({sev})"
                    else:
                        reward += SEVERITY_WRONG
                        reason += f" but wrong severity (got {sev}, expected {expected})"
                return reward, reason
            else:
                return FALSE_POSITIVE, f"{field} is not a real violation"

        elif task_id == 3:
            missing_clauses = ground_truth.get("missing_clauses", [])
            severities = ground_truth.get("severities", {})
            if field in missing_clauses:
                reward = CORRECT_FLAG
                reason = f"Correctly flagged missing clause: {field}"
                if action.severity:
                    sev = action.severity.value if hasattr(action.severity, 'value') else action.severity
                    expected = severities.get(field, "minor")
                    if sev == expected:
                        reward += SEVERITY_BONUS
                        reason += f" with correct severity ({sev})"
                    else:
                        reward += SEVERITY_WRONG
                        reason += f" but wrong severity (got {sev}, expected {expected})"
                return reward, reason
            else:
                return FALSE_POSITIVE, f"{field} is not missing — false positive"

    return 0.0, "No reward for this action"


def _get_task2_severity(violation: str) -> str:
    if "qty_mismatch" in violation or "price_mismatch" in violation:
        return "major"
    if "tax_rate_error" in violation:
        return "major"
    if "missing_po_reference" in violation:
        return "minor"
    return "minor"
