import random
from typing import Dict, Any, List, Tuple


# ─── Task 1: Employment Contract Generator ───────────────────────────────────

REQUIRED_FIELDS = [
    "party_a",
    "party_b",
    "effective_date",
    "termination_clause",
    "governing_law",
    "signature_block",
]

CONTRACT_TEMPLATES = {
    "party_a": "This Employment Agreement is entered into by and between Nexora Technologies Inc. (\"Employer\", \"Party A\"),",
    "party_b": "and {name} (\"Employee\", \"Party B\"), collectively referred to as the \"Parties\".",
    "effective_date": "This Agreement shall be effective as of {date} (\"Effective Date\").",
    "termination_clause": "Either party may terminate this Agreement with thirty (30) days written notice. Immediate termination may occur for cause including but not limited to gross misconduct, breach of confidentiality, or failure to perform duties.",
    "governing_law": "This Agreement shall be governed by and construed in accordance with the laws of the State of {state}, without regard to its conflict of law provisions.",
    "signature_block": "IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above.\n\n_______________________        _______________________\nEmployer Signature               Employee Signature\nDate: _______________           Date: _______________",
}

EMPLOYEE_NAMES = ["Jordan Mitchell", "Alex Rivera", "Sam Chen", "Morgan Taylor", "Casey Williams"]
STATES = ["California", "New York", "Texas", "Delaware", "Washington"]
DATES = ["January 15, 2025", "March 1, 2025", "April 10, 2025", "February 20, 2025"]


def generate_contract(seed: int = 42) -> Tuple[str, Dict[str, bool]]:
    """Generate a synthetic employment contract with 1-2 missing fields."""
    rng = random.Random(seed)
    name = rng.choice(EMPLOYEE_NAMES)
    state = rng.choice(STATES)
    date = rng.choice(DATES)

    # Randomly remove 1-2 fields
    num_missing = rng.randint(1, 2)
    missing_fields = rng.sample(REQUIRED_FIELDS, num_missing)
    ground_truth = {f: f not in missing_fields for f in REQUIRED_FIELDS}

    sections = []
    sections.append("=" * 60)
    sections.append("EMPLOYMENT AGREEMENT")
    sections.append("=" * 60)
    sections.append("")

    if "party_a" not in missing_fields:
        sections.append(CONTRACT_TEMPLATES["party_a"])
    if "party_b" not in missing_fields:
        sections.append(CONTRACT_TEMPLATES["party_b"].format(name=name))
    sections.append("")

    sections.append("1. POSITION AND DUTIES")
    sections.append(f"   Employee shall serve as Senior Software Engineer and shall perform duties as assigned by Employer.")
    sections.append("")

    sections.append("2. COMPENSATION")
    sections.append(f"   Employee shall receive an annual salary of $120,000, payable bi-weekly.")
    sections.append("")

    if "effective_date" not in missing_fields:
        sections.append("3. EFFECTIVE DATE")
        sections.append(f"   {CONTRACT_TEMPLATES['effective_date'].format(date=date)}")
        sections.append("")

    if "termination_clause" not in missing_fields:
        sections.append("4. TERMINATION")
        sections.append(f"   {CONTRACT_TEMPLATES['termination_clause']}")
        sections.append("")

    sections.append("5. CONFIDENTIALITY")
    sections.append("   Employee agrees to maintain strict confidentiality of all proprietary information.")
    sections.append("")

    if "governing_law" not in missing_fields:
        sections.append("6. GOVERNING LAW")
        sections.append(f"   {CONTRACT_TEMPLATES['governing_law'].format(state=state)}")
        sections.append("")

    if "signature_block" not in missing_fields:
        sections.append(CONTRACT_TEMPLATES["signature_block"])

    return "\n".join(sections), ground_truth


# ─── Task 2: Invoice vs Purchase Order Generator ─────────────────────────────

PRODUCTS = [
    {"name": "Cloud Server License", "unit_price": 299.99},
    {"name": "Developer Workstation", "unit_price": 1499.00},
    {"name": "Security Software Suite", "unit_price": 89.50},
    {"name": "Network Switch 24-Port", "unit_price": 349.00},
    {"name": "SSD Storage 2TB", "unit_price": 129.99},
]


def generate_invoice_pair(seed: int = 42) -> Tuple[str, str, Dict[str, Any]]:
    """Generate a PO and mismatched invoice. Returns (po_text, invoice_text, ground_truth)."""
    rng = random.Random(seed)
    items = rng.sample(PRODUCTS, 3)
    po_number = f"PO-{rng.randint(10000, 99999)}"
    inv_number = f"INV-{rng.randint(10000, 99999)}"

    # Generate PO quantities
    po_items = []
    for item in items:
        qty = rng.randint(1, 5)
        po_items.append({
            "name": item["name"],
            "qty": qty,
            "unit_price": item["unit_price"],
            "total": round(qty * item["unit_price"], 2)
        })

    po_subtotal = round(sum(i["total"] for i in po_items), 2)
    po_tax = round(po_subtotal * 0.08, 2)
    po_total = round(po_subtotal + po_tax, 2)

    # Introduce errors in invoice
    num_errors = rng.randint(1, 2)
    error_indices = rng.sample(range(len(po_items)), num_errors)
    inv_items = []
    violations = []

    for idx, item in enumerate(po_items):
        if idx in error_indices:
            error_type = rng.choice(["qty", "price"])
            if error_type == "qty":
                wrong_qty = item["qty"] + rng.randint(1, 3)
                inv_items.append({
                    "name": item["name"],
                    "qty": wrong_qty,
                    "unit_price": item["unit_price"],
                    "total": round(wrong_qty * item["unit_price"], 2)
                })
                violations.append(f"qty_mismatch:{item['name']}")
            else:
                wrong_price = round(item["unit_price"] * rng.uniform(1.1, 1.3), 2)
                inv_items.append({
                    "name": item["name"],
                    "qty": item["qty"],
                    "unit_price": wrong_price,
                    "total": round(item["qty"] * wrong_price, 2)
                })
                violations.append(f"price_mismatch:{item['name']}")
        else:
            inv_items.append(item.copy())

    inv_subtotal = round(sum(i["total"] for i in inv_items), 2)
    # Introduce tax error sometimes
    tax_error = rng.random() > 0.5
    if tax_error:
        inv_tax = round(inv_subtotal * 0.10, 2)  # Wrong rate
        violations.append("tax_rate_error")
    else:
        inv_tax = round(inv_subtotal * 0.08, 2)

    # Sometimes omit PO reference
    include_po_ref = rng.random() > 0.4
    if not include_po_ref:
        violations.append("missing_po_reference")

    inv_total = round(inv_subtotal + inv_tax, 2)

    # Build PO text
    po_lines = [
        "=" * 60,
        "PURCHASE ORDER",
        "=" * 60,
        f"PO Number: {po_number}",
        f"Date: March 15, 2025",
        f"Vendor: TechSupply Corp",
        "",
        f"{'Item':<35} {'Qty':>5} {'Unit Price':>12} {'Total':>12}",
        "-" * 65,
    ]
    for item in po_items:
        po_lines.append(f"{item['name']:<35} {item['qty']:>5} ${item['unit_price']:>10.2f} ${item['total']:>10.2f}")
    po_lines += [
        "-" * 65,
        f"{'Subtotal:':<53} ${po_subtotal:>10.2f}",
        f"{'Tax (8%):':<53} ${po_tax:>10.2f}",
        f"{'TOTAL:':<53} ${po_total:>10.2f}",
    ]

    # Build Invoice text
    inv_lines = [
        "=" * 60,
        "INVOICE",
        "=" * 60,
        f"Invoice Number: {inv_number}",
        f"Date: March 20, 2025",
        f"From: TechSupply Corp",
    ]
    if include_po_ref:
        inv_lines.append(f"PO Reference: {po_number}")
    inv_lines += [
        "",
        f"{'Item':<35} {'Qty':>5} {'Unit Price':>12} {'Total':>12}",
        "-" * 65,
    ]
    for item in inv_items:
        inv_lines.append(f"{item['name']:<35} {item['qty']:>5} ${item['unit_price']:>10.2f} ${item['total']:>10.2f}")
    tax_label = "Tax (10%):" if tax_error else "Tax (8%):"
    inv_lines += [
        "-" * 65,
        f"{'Subtotal:':<53} ${inv_subtotal:>10.2f}",
        f"{tax_label:<53} ${inv_tax:>10.2f}",
        f"{'TOTAL:':<53} ${inv_total:>10.2f}",
    ]

    ground_truth = {
        "violations": violations,
        "po_number": po_number,
        "po_items": po_items,
        "inv_items": inv_items,
    }

    return "\n".join(po_lines), "\n".join(inv_lines), ground_truth


# ─── Task 3: Privacy Policy Generator ────────────────────────────────────────

REQUIRED_CLAUSES = [
    "data_retention_period",
    "user_consent_mechanism",
    "right_to_deletion",
    "breach_notification_timeline",
    "third_party_sharing",
    "data_minimization",
    "user_access_rights",
    "cookie_policy",
    "childrens_data",
    "contact_information",
    "policy_update_notification",
    "data_transfer_safeguards",
]

CLAUSE_TEXTS = {
    "data_retention_period": "DATA RETENTION: We retain personal data for no longer than 24 months from the date of last activity, after which data is permanently deleted from our systems.",
    "user_consent_mechanism": "CONSENT: Users must provide explicit consent before we collect any personal data. Consent may be withdrawn at any time through your account settings or by contacting us.",
    "right_to_deletion": "RIGHT TO ERASURE: Users have the right to request deletion of their personal data at any time. Requests will be processed within 30 days.",
    "breach_notification_timeline": "DATA BREACH NOTIFICATION: In the event of a data breach affecting your personal information, we will notify affected users and relevant authorities within 72 hours of discovery.",
    "third_party_sharing": "THIRD PARTY SHARING: We do not sell personal data to third parties. Data may be shared with service providers under strict contractual data processing agreements.",
    "data_minimization": "DATA MINIMIZATION: We collect only the minimum personal data necessary to provide our services. Unnecessary data is not collected or retained.",
    "user_access_rights": "ACCESS RIGHTS: Users have the right to access, correct, and export their personal data at any time through the account dashboard.",
    "cookie_policy": "COOKIES: We use essential cookies required for service operation and optional analytics cookies. Users may opt out of non-essential cookies at any time.",
    "childrens_data": "CHILDREN'S PRIVACY: Our services are not directed at children under 13. We do not knowingly collect data from minors.",
    "contact_information": "CONTACT: For privacy-related inquiries, contact our Data Protection Officer at privacy@company.com or via postal address at 123 Tech Street, San Francisco, CA 94102.",
    "policy_update_notification": "POLICY UPDATES: We will notify users of material changes to this policy via email at least 30 days before changes take effect.",
    "data_transfer_safeguards": "INTERNATIONAL TRANSFERS: Data transferred outside the EEA is protected by Standard Contractual Clauses approved by the European Commission.",
}

CLAUSE_SEVERITY = {
    "data_retention_period": "major",
    "user_consent_mechanism": "critical",
    "right_to_deletion": "critical",
    "breach_notification_timeline": "critical",
    "third_party_sharing": "major",
    "data_minimization": "major",
    "user_access_rights": "major",
    "cookie_policy": "minor",
    "childrens_data": "major",
    "contact_information": "minor",
    "policy_update_notification": "minor",
    "data_transfer_safeguards": "major",
}


def generate_policy(seed: int = 42) -> Tuple[str, Dict[str, Any]]:
    """Generate a privacy policy with 3-5 missing clauses."""
    rng = random.Random(seed)
    num_missing = rng.randint(3, 5)
    missing_clauses = rng.sample(REQUIRED_CLAUSES, num_missing)
    present_clauses = [c for c in REQUIRED_CLAUSES if c not in missing_clauses]
    ground_truth = {
        "missing_clauses": missing_clauses,
        "present_clauses": present_clauses,
        "severities": {c: CLAUSE_SEVERITY[c] for c in missing_clauses},
    }

    lines = [
        "=" * 60,
        "PRIVACY POLICY",
        "Company: Nexora Technologies Inc.",
        "Last Updated: March 1, 2025",
        "=" * 60,
        "",
        "This Privacy Policy describes how Nexora Technologies Inc. collects, uses, and protects your personal information.",
        "",
    ]

    section_num = 1
    for clause in present_clauses:
        lines.append(f"{section_num}. {CLAUSE_TEXTS[clause]}")
        lines.append("")
        section_num += 1

    lines.append("By using our services, you acknowledge that you have read and understood this Privacy Policy.")

    return "\n".join(lines), ground_truth
