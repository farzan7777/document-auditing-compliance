from app.documents.generator import generate_policy, REQUIRED_CLAUSES, CLAUSE_SEVERITY
from typing import Dict, Any, Tuple


TASK_ID = 3
TASK_NAME = "Regulatory Policy Compliance Audit"
TASK_DIFFICULTY = "hard"
MAX_STEPS = 30

INSTRUCTIONS = """You are auditing a company privacy policy for GDPR/regulatory compliance.
The policy must contain ALL 12 required clauses. Your job is to find which ones are missing.

Required clauses to check:
  1.  data_retention_period       - How long data is kept
  2.  user_consent_mechanism      - How consent is obtained
  3.  right_to_deletion           - User's right to erase data
  4.  breach_notification_timeline - How quickly breaches are reported
  5.  third_party_sharing         - Rules on sharing with third parties
  6.  data_minimization           - Only collecting necessary data
  7.  user_access_rights          - Right to access/export data
  8.  cookie_policy               - Cookie usage disclosure
  9.  childrens_data              - Protection of minors
  10. contact_information         - DPO contact details
  11. policy_update_notification  - How users are notified of changes
  12. data_transfer_safeguards    - Rules for international data transfer

For MISSING clauses:
  - flag_violation: field="<clause_name>", severity="critical|major|minor", reason="<explanation>"

For PRESENT clauses, you don't need to act — only flag what's MISSING.
Use submit when done.

Severity guide:
  - critical: consent, deletion rights, breach notification
  - major: retention, third party sharing, access rights, minimization, children, transfers
  - minor: cookies, contact info, update notification
"""

AVAILABLE_ACTIONS = ["flag_violation", "submit"]


def get_task_info() -> Dict[str, Any]:
    return {
        "id": TASK_ID,
        "name": TASK_NAME,
        "difficulty": TASK_DIFFICULTY,
        "description": "Audit a privacy policy for 12 required compliance clauses. Flag missing ones with correct severity.",
        "max_steps": MAX_STEPS,
        "required_clauses": REQUIRED_CLAUSES,
        "severity_map": CLAUSE_SEVERITY,
        "action_schema": {
            "flag_violation": {
                "field": "str (one of the 12 clause names)",
                "reason": "str",
                "severity": "critical | major | minor"
            },
            "submit": {}
        }
    }


def generate_episode(seed: int = 42) -> Tuple[str, Dict[str, Any]]:
    return generate_policy(seed=seed)
