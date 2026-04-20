"""
verifier.py — The Second Agent (Theme #1 Multi-Agent)
======================================================
This is the VERIFIER AGENT.

Its job is to CHECK the Auditor agent's work.
It reads the SAME document the Auditor read.
It looks at EVERY finding the Auditor made.
It decides: APPROVE or REJECT each finding.

This creates cooperation + competition between agents:
  - Cooperation:  Both working toward clean audit report
  - Competition:  Verifier challenges every Auditor finding
  - Oversight:    Verifier catches Auditor hallucinations

This directly covers:
  - Theme #1 Multi-Agent Interactions
  - Fleet AI Bonus: Scalable Oversight
  - Halluminate Bonus: Multi-Actor Environment
"""

from typing import Dict, Any, List
from app.documents.generator import (
    REQUIRED_FIELDS,        # Task 1 fields
    REQUIRED_CLAUSES,       # Task 3 clauses
    CLAUSE_SEVERITY,        # Task 3 severities
)


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFIER KEYWORD MAPS
# ═══════════════════════════════════════════════════════════════════════════════
# These are the keywords the Verifier uses to check each field/clause.
# If Auditor says "party_a is missing" but Verifier finds these keywords
# in the document → Verifier REJECTS the Auditor's finding.

# Task 1: Keywords for each required contract field
FIELD_KEYWORDS = {
    "party_a": [
        "Party A", "Employer", "Nexora", "employer",
        "Engaging Entity",          # Level 3-5 paraphrased version
    ],
    "party_b": [
        "Party B", "Employee", "employee",
        "Engaged Professional",     # Level 3-5 paraphrased version
    ],
    "effective_date": [
        "Effective Date", "effective as of", "EFFECTIVE DATE",
        "commencement of obligations",  # Level 3-5 paraphrased version
    ],
    "termination_clause": [
        "TERMINATION", "terminate", "Termination", "30 days",
        "dissolution", "Dissolution",   # Level 3-5 paraphrased version
    ],
    "governing_law": [
        "GOVERNING LAW", "governing law", "laws of the State",
        "Jurisdiction", "jurisdiction",  # Level 3-5 paraphrased version
    ],
    "signature_block": [
        "Signature", "WITNESS WHEREOF", "___",
        "EXECUTED", "Execution Date",   # Level 3-5 paraphrased version
    ],
}

# Task 3: Keywords for each required GDPR clause
CLAUSE_KEYWORDS = {
    "data_retention_period": [
        "retain", "retention", "24 months", "deleted", "DATA RETENTION"
    ],
    "user_consent_mechanism": [
        "consent", "explicit consent", "Consent", "CONSENT"
    ],
    "right_to_deletion": [
        "deletion", "erasure", "right to", "erase", "ERASURE"
    ],
    "breach_notification_timeline": [
        "breach", "72 hours", "notification", "Breach", "BREACH"
    ],
    "third_party_sharing": [
        "third party", "third-party", "Third Party", "sell", "THIRD PARTY"
    ],
    "data_minimization": [
        "minimization", "minimum", "necessary data", "MINIMIZATION"
    ],
    "user_access_rights": [
        "access rights", "right to access", "export", "ACCESS RIGHTS"
    ],
    "cookie_policy": [
        "cookie", "Cookie", "cookies", "COOKIES"
    ],
    "childrens_data": [
        "children", "minor", "under 13", "CHILDREN"
    ],
    "contact_information": [
        "contact", "privacy@", "DPO", "Data Protection Officer", "CONTACT"
    ],
    "policy_update_notification": [
        "update", "notify", "30 days", "changes", "POLICY UPDATES"
    ],
    "data_transfer_safeguards": [
        "transfer", "EEA", "Standard Contractual", "international", "TRANSFERS"
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFIER AGENT CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class VerifierAgent:
    """
    The Verifier Agent.

    This agent monitors, analyzes, and explains
    the behavior of the Auditor agent.

    It is the OVERSIGHT agent that Fleet AI bonus requires.
    """

    def verify(
        self,
        task_id: int,
        document: str,
        auditor_findings: List[str],
        session: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Main verification method.
        Called after Auditor finishes its work.

        Args:
            task_id: 1, 2, or 3 (which task)
            document: the full document text
            auditor_findings: list of what Auditor flagged
            session: current session state

        Returns:
            List of decisions, one per Auditor finding.
            Each decision has:
              - finding: what Auditor flagged
              - decision: "APPROVE" or "REJECT"
              - reason: why Verifier made this decision
              - confidence: how confident Verifier is (0.0-1.0)
        """

        # Route to correct verification method based on task
        if task_id == 1:
            return self._verify_task1(document, auditor_findings, session)
        elif task_id == 2:
            return self._verify_task2(document, auditor_findings, session)
        elif task_id == 3:
            return self._verify_task3(document, auditor_findings, session)
        else:
            return []

    def _verify_task1(
        self,
        document: str,
        auditor_findings: List[str],
        session: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Verify Task 1 findings (Employment Contract).

        Auditor flagged some fields as missing.
        Verifier checks if those fields are ACTUALLY missing.

        Logic:
          Search document for field keywords
          If keywords FOUND but Auditor said MISSING → REJECT
          If keywords NOT FOUND and Auditor said MISSING → APPROVE
        """
        decisions = []

        # Get what Auditor said is missing
        # missing_confirmed = fields Auditor marked as missing
        auditor_missing = session.get("missing_confirmed", [])
        auditor_present = session.get("confirmations", [])

        # Check each field Auditor said is MISSING
        for field in auditor_missing:
            keywords = FIELD_KEYWORDS.get(field, [])
            # Search for any keyword in document
            found_in_doc = any(kw in document for kw in keywords)

            if found_in_doc:
                # Auditor said missing BUT keywords found → Auditor is WRONG
                decisions.append({
                    "finding": f"marked_missing:{field}",
                    "decision": "REJECT",
                    "reason": f"Keywords for '{field}' found in document. Auditor incorrectly marked as missing.",
                    "confidence": 0.85,
                    "field": field,
                    "finding_type": "false_missing"
                })
            else:
                # Auditor said missing AND keywords not found → Auditor is CORRECT
                decisions.append({
                    "finding": f"marked_missing:{field}",
                    "decision": "APPROVE",
                    "reason": f"No keywords for '{field}' found in document. Auditor correctly identified as missing.",
                    "confidence": 0.90,
                    "field": field,
                    "finding_type": "true_missing"
                })

        # Check each field Auditor said is PRESENT
        for field in auditor_present:
            keywords = FIELD_KEYWORDS.get(field, [])
            found_in_doc = any(kw in document for kw in keywords)

            if found_in_doc:
                # Auditor said present AND keywords found → Auditor is CORRECT
                decisions.append({
                    "finding": f"marked_present:{field}",
                    "decision": "APPROVE",
                    "reason": f"Keywords for '{field}' confirmed in document.",
                    "confidence": 0.90,
                    "field": field,
                    "finding_type": "true_present"
                })
            else:
                # Auditor said present BUT keywords not found → Auditor is WRONG
                decisions.append({
                    "finding": f"marked_present:{field}",
                    "decision": "REJECT",
                    "reason": f"No keywords for '{field}' found. Field may actually be missing.",
                    "confidence": 0.75,
                    "field": field,
                    "finding_type": "false_present"
                })

        return decisions

    def _verify_task2(
        self,
        document: str,
        auditor_findings: List[str],
        session: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Verify Task 2 findings (Invoice vs PO).

        Auditor flagged some violations.
        Verifier checks if those violations are REAL.

        Logic:
          For tax_rate_error: check if "10%" appears in invoice section
          For missing_po_reference: check if PO number in invoice section
          For qty/price mismatch: check if numbers actually differ
        """
        decisions = []
        auditor_flags = session.get("flags_raised", [])

        # Split document into PO and Invoice sections
        parts = document.split("--- INVOICE ---")
        invoice_section = parts[-1] if len(parts) > 1 else document
        po_section = parts[0] if len(parts) > 1 else document

        for flag in auditor_flags:

            # ── Check tax rate error ───────────────────────────────────────────
            if flag == "tax_rate_error":
                if "10%" in invoice_section or "Tax (10%)" in invoice_section:
                    decisions.append({
                        "finding": flag,
                        "decision": "APPROVE",
                        "reason": "10% tax rate confirmed in invoice section. Should be 8%.",
                        "confidence": 0.95,
                        "field": flag,
                        "finding_type": "true_violation"
                    })
                else:
                    decisions.append({
                        "finding": flag,
                        "decision": "REJECT",
                        "reason": "No 10% tax rate found in invoice. Tax appears correct.",
                        "confidence": 0.90,
                        "field": flag,
                        "finding_type": "false_violation"
                    })

            # ── Check missing PO reference ─────────────────────────────────────
            elif flag == "missing_po_reference":
                if "PO-" in invoice_section or "PO Reference" in invoice_section:
                    decisions.append({
                        "finding": flag,
                        "decision": "REJECT",
                        "reason": "PO reference number found in invoice section.",
                        "confidence": 0.90,
                        "field": flag,
                        "finding_type": "false_violation"
                    })
                else:
                    decisions.append({
                        "finding": flag,
                        "decision": "APPROVE",
                        "reason": "No PO reference found in invoice section.",
                        "confidence": 0.90,
                        "field": flag,
                        "finding_type": "true_violation"
                    })

            # ── Check quantity or price mismatch ──────────────────────────────
            elif flag.startswith("qty_mismatch:") or flag.startswith("price_mismatch:"):
                # Extract item name from flag
                # Example: "qty_mismatch:Cloud Server License"
                item_name = flag.split(":", 1)[-1] if ":" in flag else ""

                if item_name and item_name in document:
                    # Item exists — likely a real mismatch
                    decisions.append({
                        "finding": flag,
                        "decision": "APPROVE",
                        "reason": f"Item '{item_name}' found in both documents. Mismatch plausible.",
                        "confidence": 0.75,
                        "field": flag,
                        "finding_type": "true_violation"
                    })
                else:
                    decisions.append({
                        "finding": flag,
                        "decision": "REJECT",
                        "reason": f"Item '{item_name}' not clearly identified in documents.",
                        "confidence": 0.65,
                        "field": flag,
                        "finding_type": "uncertain"
                    })

            # ── Unknown flag ───────────────────────────────────────────────────
            else:
                decisions.append({
                    "finding": flag,
                    "decision": "REJECT",
                    "reason": f"Unknown violation type '{flag}'. Not a recognized violation.",
                    "confidence": 0.80,
                    "field": flag,
                    "finding_type": "false_violation"
                })

        return decisions

    def _verify_task3(
        self,
        document: str,
        auditor_findings: List[str],
        session: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Verify Task 3 findings (Privacy Policy GDPR).

        Auditor flagged some clauses as missing.
        Verifier checks if those clauses are ACTUALLY missing.

        Logic:
          Search document for clause keywords
          If keywords FOUND but Auditor said MISSING → REJECT
          If keywords NOT FOUND and Auditor said MISSING → APPROVE
        """
        decisions = []
        auditor_flags = session.get("flags_raised", [])

        for flag in auditor_flags:
            # Check if this is a known GDPR clause
            if flag in CLAUSE_KEYWORDS:
                keywords = CLAUSE_KEYWORDS[flag]
                found_in_doc = any(kw in document for kw in keywords)

                if found_in_doc:
                    # Auditor said missing BUT clause found → Auditor WRONG
                    decisions.append({
                        "finding": flag,
                        "decision": "REJECT",
                        "reason": f"Keywords for '{flag}' found in policy document. Clause is present — auditor hallucinated.",
                        "confidence": 0.88,
                        "field": flag,
                        "finding_type": "false_violation"
                    })
                else:
                    # Auditor said missing AND clause not found → Auditor CORRECT
                    decisions.append({
                        "finding": flag,
                        "decision": "APPROVE",
                        "reason": f"No keywords for '{flag}' found in document. Clause genuinely missing.",
                        "confidence": 0.92,
                        "field": flag,
                        "finding_type": "true_violation"
                    })
            else:
                # Not a recognized clause name → definitely wrong
                decisions.append({
                    "finding": flag,
                    "decision": "REJECT",
                    "reason": f"'{flag}' is not a recognized GDPR compliance clause.",
                    "confidence": 0.95,
                    "field": flag,
                    "finding_type": "false_violation"
                })

        return decisions

    def get_summary(self, decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Summarize all verifier decisions.
        Used in API response so judges can see everything clearly.

        Returns counts of approvals, rejections, and confidence.
        """
        if not decisions:
            return {
                "total_checked": 0,
                "approved": 0,
                "rejected": 0,
                "average_confidence": 0.0,
                "hallucinations_caught": 0,
            }

        approved = [d for d in decisions if d["decision"] == "APPROVE"]
        rejected = [d for d in decisions if d["decision"] == "REJECT"]

        # Count hallucinations caught
        # (cases where Auditor was wrong and Verifier caught it)
        hallucinations = [
            d for d in decisions
            if d["decision"] == "REJECT"
            and d.get("finding_type") in ["false_violation", "false_missing", "false_present"]
        ]

        avg_confidence = sum(d["confidence"] for d in decisions) / len(decisions)

        return {
            "total_checked": len(decisions),
            "approved": len(approved),
            "rejected": len(rejected),
            "average_confidence": round(avg_confidence, 3),
            "hallucinations_caught": len(hallucinations),
        }


# ─── Global Verifier Instance ─────────────────────────────────────────────────
# One verifier runs for entire server lifetime.
# Stateless — no memory between calls.
# Each call is independent.

verifier = VerifierAgent()