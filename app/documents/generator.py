"""
generator.py — Document Generator with 5 Difficulty Levels
============================================================
Theme #4: Self Improvement — Adaptive Curriculum

This file generates documents at 5 difficulty levels.
The curriculum.py decides WHICH level to use.
This file actually CREATES the document at that level.

Think of this as the EXAM PAPER PRINTER.
curriculum.py tells it "print Level 3 paper"
This file prints the Level 3 paper.

Difficulty Levels:
  Level 1 = Junior Clerk      (easiest)
  Level 2 = Analyst           (easy-medium)
  Level 3 = Senior Officer    (medium)
  Level 4 = Director          (hard)
  Level 5 = Regulatory Expert (hardest)
"""

import random
from typing import Dict, Any, List, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 1: EMPLOYMENT CONTRACT GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

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

# Level 3-5 use paraphrased versions to confuse the agent
CONTRACT_TEMPLATES_HARD = {
    "party_a": "Nexora Technologies Inc., a Delaware corporation (hereinafter the \"Engaging Entity\"), enters this instrument,",
    "party_b": "with {name}, an individual (hereinafter the \"Engaged Professional\"), together constituting the \"Contracting Parties\".",
    "effective_date": "The commencement of obligations under this instrument shall be {date}.",
    "termination_clause": "Dissolution of this arrangement may be initiated by either Contracting Party upon provision of thirty (30) calendar days advance written notification. Summary dissolution may occur upon material breach.",
    "governing_law": "Jurisdiction and venue for any disputes arising hereunder shall be exclusively in {state}, and its laws shall govern interpretation.",
    "signature_block": "EXECUTED as of the date indicated above by the duly authorized representatives:\n\n________________________        ________________________\nEngaging Entity Representative   Engaged Professional\nExecution Date: _________        Execution Date: _________",
}

# Level 5 fake clauses — look real but are NOT required fields
FAKE_CLAUSES = [
    "\n7. INTELLECTUAL PROPERTY ASSIGNMENT\n   All work product created during employment shall be property of Employer.",
    "\n8. NON-COMPETE AGREEMENT\n   Employee agrees not to compete within the industry for 12 months post-termination.",
    "\n9. DISPUTE RESOLUTION\n   Any disputes shall first be subject to mediation before arbitration proceedings.",
    "\n10. BENEFITS PACKAGE\n   Employee shall receive standard benefits including health, dental, and 401k matching.",
]

EMPLOYEE_NAMES = ["Jordan Mitchell", "Alex Rivera", "Sam Chen", "Morgan Taylor", "Casey Williams"]
STATES = ["California", "New York", "Texas", "Delaware", "Washington"]
DATES = ["January 15, 2025", "March 1, 2025", "April 10, 2025", "February 20, 2025"]


def generate_contract(seed: int = 42, difficulty: int = 1) -> Tuple[str, Dict[str, bool]]:
    """
    Generate a synthetic employment contract.

    Args:
        seed: Random seed for reproducibility
        difficulty: 1-5, controls how hard it is to audit

    Returns:
        (document_text, ground_truth)
        ground_truth = {"party_a": True, "party_b": False, ...}
        True = field IS present, False = field is MISSING
    """
    rng = random.Random(seed)
    name = rng.choice(EMPLOYEE_NAMES)
    state = rng.choice(STATES)
    date = rng.choice(DATES)

    # ── How many fields to remove based on difficulty ──────────────────────────
    # Level 1 → remove 1 field  (easy to find)
    # Level 2 → remove 2 fields (medium)
    # Level 3 → remove 2 fields (hard language)
    # Level 4 → remove 3 fields (buried in long text)
    # Level 5 → remove 3 fields + fake clauses added
    if difficulty == 1:
        num_missing = 1
    elif difficulty == 2:
        num_missing = 2
    elif difficulty == 3:
        num_missing = 2
    elif difficulty == 4:
        num_missing = 3
    else:  # difficulty == 5
        num_missing = 3

    missing_fields = rng.sample(REQUIRED_FIELDS, num_missing)
    ground_truth = {f: f not in missing_fields for f in REQUIRED_FIELDS}

    # ── Choose template style based on difficulty ──────────────────────────────
    # Level 1-2 → normal simple language
    # Level 3-5 → paraphrased confusing language
    templates = CONTRACT_TEMPLATES if difficulty <= 2 else CONTRACT_TEMPLATES_HARD

    # ── Build document sections ────────────────────────────────────────────────
    sections = []
    sections.append("=" * 60)
    sections.append("EMPLOYMENT AGREEMENT")
    sections.append("=" * 60)
    sections.append("")

    if "party_a" not in missing_fields:
        sections.append(templates["party_a"])
    if "party_b" not in missing_fields:
        sections.append(templates["party_b"].format(name=name))
    sections.append("")

    sections.append("1. POSITION AND DUTIES")
    sections.append(f"   Employee shall serve as Senior Software Engineer.")
    sections.append("")

    sections.append("2. COMPENSATION")
    sections.append(f"   Employee shall receive an annual salary of $120,000.")
    sections.append("")

    # Level 4-5: Add extra filler sections to bury the real content
    if difficulty >= 4:
        sections.append("3. PROBATIONARY PERIOD")
        sections.append("   Employee shall serve a 90-day probationary period during which performance will be evaluated against defined KPIs and departmental benchmarks.")
        sections.append("")
        sections.append("4. REMOTE WORK POLICY")
        sections.append("   Employee may work remotely up to three days per week subject to manager approval and departmental requirements as may change from time to time.")
        sections.append("")

    if "effective_date" not in missing_fields:
        sections.append("5. EFFECTIVE DATE" if difficulty >= 4 else "3. EFFECTIVE DATE")
        sections.append(f"   {templates['effective_date'].format(date=date)}")
        sections.append("")

    if "termination_clause" not in missing_fields:
        sections.append("6. TERMINATION" if difficulty >= 4 else "4. TERMINATION")
        sections.append(f"   {templates['termination_clause']}")
        sections.append("")

    sections.append("7. CONFIDENTIALITY" if difficulty >= 4 else "5. CONFIDENTIALITY")
    sections.append("   Employee agrees to maintain strict confidentiality of all proprietary information.")
    sections.append("")

    if "governing_law" not in missing_fields:
        sections.append("8. GOVERNING LAW" if difficulty >= 4 else "6. GOVERNING LAW")
        sections.append(f"   {templates['governing_law'].format(state=state)}")
        sections.append("")

    # Level 5: Add fake clauses to confuse agent
    if difficulty == 5:
        num_fakes = rng.randint(2, 3)
        fake_additions = rng.sample(FAKE_CLAUSES, num_fakes)
        for fake in fake_additions:
            sections.append(fake)
            sections.append("")

    if "signature_block" not in missing_fields:
        sections.append(templates["signature_block"])

    return "\n".join(sections), ground_truth


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 2: INVOICE VS PURCHASE ORDER GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

PRODUCTS = [
    {"name": "Cloud Server License", "unit_price": 299.99},
    {"name": "Developer Workstation", "unit_price": 1499.00},
    {"name": "Security Software Suite", "unit_price": 89.50},
    {"name": "Network Switch 24-Port", "unit_price": 349.00},
    {"name": "SSD Storage 2TB", "unit_price": 129.99},
]

# Level 4-5: Similar sounding product names to confuse agent
SIMILAR_PRODUCTS = [
    {"name": "Cloud Server License Pro", "unit_price": 299.99},
    {"name": "Developer Workstation Plus", "unit_price": 1499.00},
    {"name": "Security Software Suite Lite", "unit_price": 89.50},
    {"name": "Network Switch 24-Port PoE", "unit_price": 349.00},
    {"name": "SSD Storage 2TB NVMe", "unit_price": 129.99},
]


def generate_invoice_pair(seed: int = 42, difficulty: int = 1) -> Tuple[str, str, Dict[str, Any]]:
    """
    Generate a PO and mismatched invoice.

    Args:
        seed: Random seed for reproducibility
        difficulty: 1-5, controls number of errors and complexity

    Returns:
        (po_text, invoice_text, ground_truth)
    """
    rng = random.Random(seed)

    # ── Choose products based on difficulty ────────────────────────────────────
    # Level 4-5 use similar sounding names to confuse agent
    product_pool = SIMILAR_PRODUCTS if difficulty >= 4 else PRODUCTS

    po_number = f"PO-{rng.randint(10000, 99999)}"
    inv_number = f"INV-{rng.randint(10000, 99999)}"

    items = rng.sample(product_pool, 3)

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

    # ── How many errors based on difficulty ────────────────────────────────────
    # Level 1 → 1 error
    # Level 2 → 2 errors
    # Level 3 → 2 errors + tax error
    # Level 4 → 3 errors
    # Level 5 → 3 errors + tax error + missing PO reference
    if difficulty == 1:
        num_errors = 1
        force_tax_error = False
        force_missing_po = False
    elif difficulty == 2:
        num_errors = 2
        force_tax_error = False
        force_missing_po = False
    elif difficulty == 3:
        num_errors = 2
        force_tax_error = True
        force_missing_po = False
    elif difficulty == 4:
        num_errors = 3
        force_tax_error = False
        force_missing_po = False
    else:  # difficulty == 5
        num_errors = 3
        force_tax_error = True
        force_missing_po = True

    error_indices = rng.sample(range(len(po_items)), min(num_errors, len(po_items)))
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

    # Tax error logic
    if force_tax_error:
        inv_tax = round(inv_subtotal * 0.10, 2)
        violations.append("tax_rate_error")
        tax_error = True
    else:
        tax_error = rng.random() > 0.5
        if tax_error:
            inv_tax = round(inv_subtotal * 0.10, 2)
            violations.append("tax_rate_error")
        else:
            inv_tax = round(inv_subtotal * 0.08, 2)

    # Missing PO reference logic
    if force_missing_po:
        include_po_ref = False
        violations.append("missing_po_reference")
    else:
        include_po_ref = rng.random() > 0.4
        if not include_po_ref:
            violations.append("missing_po_reference")

    inv_total = round(inv_subtotal + inv_tax, 2)

    # ── Build PO text ──────────────────────────────────────────────────────────
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

    # ── Build Invoice text ─────────────────────────────────────────────────────
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


# ═══════════════════════════════════════════════════════════════════════════════
# TASK 3: PRIVACY POLICY GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

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

# Level 4-5: Fake clauses that LOOK like real ones but are NOT required
# Agent must not flag these as missing — they are present but misleading
FAKE_CLAUSE_TEXTS = {
    "data_archival_policy": "DATA ARCHIVAL: Historical records may be archived for business continuity purposes in compliance with applicable record retention laws.",
    "marketing_preferences": "MARKETING COMMUNICATIONS: Users may opt in or out of marketing communications at any time via account preferences or unsubscribe links.",
    "platform_security": "SECURITY MEASURES: We implement industry-standard security measures including encryption, firewalls, and regular security audits to protect your data.",
    "user_feedback_data": "FEEDBACK DATA: Information provided through surveys or feedback forms is used solely to improve our services and is not shared with third parties.",
}


def generate_policy(seed: int = 42, difficulty: int = 1) -> Tuple[str, Dict[str, Any]]:
    """
    Generate a privacy policy with missing GDPR clauses.

    Args:
        seed: Random seed for reproducibility
        difficulty: 1-5, controls missing clauses and document complexity

    Returns:
        (document_text, ground_truth)
    """
    rng = random.Random(seed)

    # ── How many clauses to remove based on difficulty ─────────────────────────
    # Level 1 → 3 missing (easiest)
    # Level 2 → 4 missing
    # Level 3 → 5 missing
    # Level 4 → 5 missing + partial fake clauses
    # Level 5 → 6 missing + many fake clauses
    if difficulty == 1:
        num_missing = 3
    elif difficulty == 2:
        num_missing = 4
    elif difficulty == 3:
        num_missing = 5
    elif difficulty == 4:
        num_missing = 5
    else:  # difficulty == 5
        num_missing = 6

    missing_clauses = rng.sample(REQUIRED_CLAUSES, num_missing)
    present_clauses = [c for c in REQUIRED_CLAUSES if c not in missing_clauses]

    ground_truth = {
        "missing_clauses": missing_clauses,
        "present_clauses": present_clauses,
        "severities": {c: CLAUSE_SEVERITY[c] for c in missing_clauses},
    }

    # ── Build document ─────────────────────────────────────────────────────────
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

    # Level 4-5: Add intro paragraphs to make document longer and harder
    if difficulty >= 4:
        lines.append("We are committed to protecting your privacy and handling your personal data with transparency and integrity. This policy applies to all users of our services globally and reflects our commitment to compliance with applicable data protection regulations.")
        lines.append("")
        lines.append("By accessing or using our services, you acknowledge that you have read and understood this Privacy Policy and agree to the collection and use of your information as described herein.")
        lines.append("")

    section_num = 1
    for clause in present_clauses:
        lines.append(f"{section_num}. {CLAUSE_TEXTS[clause]}")
        lines.append("")
        section_num += 1

    # Level 4-5: Add fake clauses to confuse agent
    if difficulty >= 4:
        num_fakes = 2 if difficulty == 4 else 4
        fake_keys = rng.sample(list(FAKE_CLAUSE_TEXTS.keys()), min(num_fakes, len(FAKE_CLAUSE_TEXTS)))
        for fake_key in fake_keys:
            lines.append(f"{section_num}. {FAKE_CLAUSE_TEXTS[fake_key]}")
            lines.append("")
            section_num += 1

    lines.append("By using our services, you acknowledge that you have read and understood this Privacy Policy.")

    return "\n".join(lines), ground_truth


# ═══════════════════════════════════════════════════════════════════════════════
# BACKWARD COMPATIBLE WRAPPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════
# These functions keep the OLD names working.
# Your existing code calls generate_episode() — that still works.
# Now it just passes difficulty through.

def generate_episode(seed: int = 42, difficulty: int = 1):
    """Task 1 wrapper — keeps existing code working."""
    return generate_contract(seed=seed, difficulty=difficulty)


def generate_invoice_episode(seed: int = 42, difficulty: int = 1):
    """Task 2 wrapper — keeps existing code working."""
    return generate_invoice_pair(seed=seed, difficulty=difficulty)


def generate_policy_episode(seed: int = 42, difficulty: int = 1):
    """Task 3 wrapper — keeps existing code working."""
    return generate_policy(seed=seed, difficulty=difficulty)