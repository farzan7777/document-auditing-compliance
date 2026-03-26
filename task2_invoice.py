from app.documents.generator import generate_invoice_pair
from typing import Dict, Any, Tuple


TASK_ID = 2
TASK_NAME = "Invoice vs Purchase Order Validation"
TASK_DIFFICULTY = "medium"
MAX_STEPS = 20

INSTRUCTIONS = """You are validating an invoice against a purchase order for discrepancies.
You will receive TWO documents: a Purchase Order (PO) and an Invoice.

Check for these violation types:
  - qty_mismatch:<item_name>     - Quantity on invoice differs from PO
  - price_mismatch:<item_name>   - Unit price on invoice differs from PO
  - tax_rate_error               - Tax rate is wrong (should be 8%)
  - missing_po_reference         - Invoice doesn't reference the PO number

Actions available:
  - flag_violation: field="<violation_type>", reason="<explanation>", severity="critical|major|minor"
  - submit: when you have flagged all violations you found

Be precise: only flag real violations, false positives are penalized.
"""

AVAILABLE_ACTIONS = ["flag_violation", "submit"]


def get_task_info() -> Dict[str, Any]:
    return {
        "id": TASK_ID,
        "name": TASK_NAME,
        "difficulty": TASK_DIFFICULTY,
        "description": "Compare an invoice against a purchase order. Find quantity, price, tax, and reference errors.",
        "max_steps": MAX_STEPS,
        "violation_types": ["qty_mismatch", "price_mismatch", "tax_rate_error", "missing_po_reference"],
        "action_schema": {
            "flag_violation": {
                "field": "str (violation type, e.g. qty_mismatch:Cloud Server License)",
                "reason": "str",
                "severity": "critical | major | minor"
            },
            "submit": {}
        }
    }


def generate_episode(seed: int = 42) -> Tuple[str, str, Dict[str, Any]]:
    return generate_invoice_pair(seed=seed)
