"""
Internal rule-based baseline agent.
Used by the /baseline endpoint — no OpenAI API key required.
This agent uses simple keyword matching to audit documents.
"""
from app import env
from app.models import Action, ActionType
from app.tasks import task1_fields, task2_invoice, task3_policy
from typing import Dict, Any
import re


def _run_task1_agent(session_id: str, document: str) -> float:
    """Rule-based agent for task 1: look for keywords in document."""
    keyword_map = {
        "party_a": ["Party A", "Employer", "Nexora", "employer"],
        "party_b": ["Party B", "Employee", "employee"],
        "effective_date": ["Effective Date", "effective as of", "EFFECTIVE DATE"],
        "termination_clause": ["TERMINATION", "terminate", "Termination", "30 days"],
        "governing_law": ["GOVERNING LAW", "governing law", "laws of the State"],
        "signature_block": ["Signature", "WITNESS WHEREOF", "___"],
    }

    for field, keywords in keyword_map.items():
        found = any(kw in document for kw in keywords)
        action = Action(
            action_type=ActionType.MARK_FIELD_PRESENT if found else ActionType.MARK_FIELD_MISSING,
            field=field,
            reason=f"{'Found' if found else 'Not found'} keyword indicators for {field}",
        )
        env.step(session_id=session_id, action=action)

    env.step(session_id=session_id, action=Action(action_type=ActionType.SUBMIT))
    result = env.grade(session_id=session_id)
    return result.score


def _run_task2_agent(session_id: str, document: str) -> float:
    """Rule-based agent for task 2: detect invoice vs PO mismatches."""
    violations_to_check = [
        ("missing_po_reference", "PO-", "Missing PO reference number in invoice"),
        ("tax_rate_error", "10%", "Incorrect tax rate found (10% instead of 8%)"),
    ]

    for field, keyword, reason in violations_to_check:
        if field == "missing_po_reference" and keyword not in document.split("--- INVOICE ---")[-1]:
            action = Action(
                action_type=ActionType.FLAG_VIOLATION,
                field=field,
                reason=reason,
                severity="minor",
            )
            env.step(session_id=session_id, action=action)
        elif field == "tax_rate_error" and keyword in document:
            action = Action(
                action_type=ActionType.FLAG_VIOLATION,
                field=field,
                reason=reason,
                severity="major",
            )
            env.step(session_id=session_id, action=action)

    env.step(session_id=session_id, action=Action(action_type=ActionType.SUBMIT))
    result = env.grade(session_id=session_id)
    return result.score


def _run_task3_agent(session_id: str, document: str) -> float:
    """Rule-based agent for task 3: check for missing policy clauses."""
    clause_keywords = {
        "data_retention_period": ["retain", "retention", "24 months", "deleted"],
        "user_consent_mechanism": ["consent", "explicit consent", "Consent"],
        "right_to_deletion": ["deletion", "erasure", "right to", "erase"],
        "breach_notification_timeline": ["breach", "72 hours", "notification", "Breach"],
        "third_party_sharing": ["third party", "third-party", "Third Party", "sell"],
        "data_minimization": ["minimization", "minimum", "necessary data"],
        "user_access_rights": ["access rights", "right to access", "export"],
        "cookie_policy": ["cookie", "Cookie", "cookies"],
        "childrens_data": ["children", "minor", "under 13"],
        "contact_information": ["contact", "privacy@", "DPO", "Data Protection Officer"],
        "policy_update_notification": ["update", "notify", "30 days", "changes"],
        "data_transfer_safeguards": ["transfer", "EEA", "Standard Contractual", "international"],
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
        found = any(kw in document for kw in keywords)
        if not found:
            action = Action(
                action_type=ActionType.FLAG_VIOLATION,
                field=clause,
                reason=f"No indicators found for {clause} in policy document",
                severity=severity_map.get(clause, "minor"),
            )
            env.step(session_id=session_id, action=action)

    env.step(session_id=session_id, action=Action(action_type=ActionType.SUBMIT))
    result = env.grade(session_id=session_id)
    return result.score


def run_baseline_internal() -> Dict[str, Any]:
    """Run rule-based baseline agent on all 3 tasks with fixed seeds."""
    SEEDS = {1: 42, 2: 42, 3: 42}
    scores = {}
    details = {}

    for task_id, seed in SEEDS.items():
        session_id, observation = env.reset(task_id=task_id, seed=seed)
        document = observation.document_text

        if task_id == 1:
            score = _run_task1_agent(session_id, document)
        elif task_id == 2:
            score = _run_task2_agent(session_id, document)
        elif task_id == 3:
            score = _run_task3_agent(session_id, document)

        scores[f"task_{task_id}"] = score
        state = env.state(session_id)
        details[f"task_{task_id}"] = {
            "seed": seed,
            "steps_taken": state["steps_taken"],
            "final_score": score,
            "agent_type": "rule_based_keyword_matching",
        }

    avg = round(sum(scores.values()) / len(scores), 4)
    return {
        "scores": scores,
        "details": details,
        "average_score": avg,
    }
