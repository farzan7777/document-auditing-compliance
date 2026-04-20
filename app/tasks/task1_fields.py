from app.documents.generator import generate_contract, REQUIRED_FIELDS
from typing import Dict, Any, Tuple


TASK_ID = 1
TASK_NAME = "Required Field Detection"
TASK_DIFFICULTY = "easy"
MAX_STEPS = 12

INSTRUCTIONS = """You are auditing an employment contract for completeness.
Your job is to check whether all 6 required fields are present:
  1. party_a         - Employer identification
  2. party_b         - Employee identification  
  3. effective_date  - When the contract starts
  4. termination_clause - How contract can be ended
  5. governing_law   - Which jurisdiction governs
  6. signature_block - Signature lines for both parties

For each field:
- If PRESENT: use action_type="mark_field_present", field="<field_name>"
- If MISSING:  use action_type="mark_field_missing", field="<field_name>", reason="<why it's missing>"
- When done with all fields: use action_type="submit"

Score higher by correctly identifying ALL present and missing fields.
"""

AVAILABLE_ACTIONS = ["mark_field_present", "mark_field_missing", "submit"]


def get_task_info() -> Dict[str, Any]:
    return {
        "id": TASK_ID,
        "name": TASK_NAME,
        "difficulty": TASK_DIFFICULTY,
        "description": "Check an employment contract for 6 required fields. Mark each as present or missing.",
        "max_steps": MAX_STEPS,
        "required_fields": REQUIRED_FIELDS,
        "action_schema": {
            "mark_field_present": {"field": "str (one of the 6 required fields)"},
            "mark_field_missing": {"field": "str", "reason": "str"},
            "submit": {},
        }
    }


def generate_episode(seed: int = 42, difficulty: int = 1) -> Tuple[str, Dict[str, bool]]:
    return generate_contract(seed=seed, difficulty=difficulty)