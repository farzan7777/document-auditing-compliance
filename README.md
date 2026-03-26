---
title: OpenEnv Document Compliance Auditing
emoji: 📋
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
tags:
  - openenv
  - compliance
  - document-auditing
  - legal-ai
  - nlp
---

# 📋 OpenEnv: Document Compliance Auditing

An [OpenEnv](https://openenv.dev)-compliant environment where AI agents audit real-world business documents for compliance violations.

## 🎯 Environment Description

This environment simulates the work of a **compliance auditor** — a professional who reviews contracts, invoices, and policy documents to ensure they meet legal and regulatory standards. Unlike games or toy benchmarks, this environment reflects a genuine business task performed daily across legal, finance, and operations teams.

Agents interact with the environment through a standard HTTP API, receiving documents as observations, taking structured audit actions, and receiving per-step rewards that reflect audit quality.

---

## 📋 Tasks

### Task 1 — Required Field Detection *(Easy)*
**Objective:** Audit an employment contract for 6 required fields.

| Field | Description |
|---|---|
| `party_a` | Employer identification clause |
| `party_b` | Employee identification clause |
| `effective_date` | Contract start date |
| `termination_clause` | How the contract can be ended |
| `governing_law` | Jurisdiction that governs the contract |
| `signature_block` | Signature lines for both parties |

Documents are synthetically generated with 1–2 fields intentionally missing. The agent must correctly classify each field as **present** or **missing**.

**Scoring:** `correct_labels / total_fields` with false positive penalty.
**Max steps:** 12 | **Expected difficulty:** Easy

---

### Task 2 — Invoice vs Purchase Order Validation *(Medium)*
**Objective:** Compare an invoice against a purchase order and detect discrepancies.

| Violation Type | Description |
|---|---|
| `qty_mismatch:<item>` | Quantity differs between PO and invoice |
| `price_mismatch:<item>` | Unit price differs between PO and invoice |
| `tax_rate_error` | Tax rate is wrong (should be 8%) |
| `missing_po_reference` | Invoice doesn't reference the PO number |

The agent receives both documents side-by-side and must flag only real violations (false positives are penalized).

**Scoring:** Weighted F1 (recall-weighted) with precision penalty.
**Max steps:** 20 | **Expected difficulty:** Medium

---

### Task 3 — Regulatory Policy Compliance Audit *(Hard)*
**Objective:** Audit a company privacy policy for 12 required GDPR-style compliance clauses.

| Clause | Severity |
|---|---|
| `user_consent_mechanism` | Critical |
| `right_to_deletion` | Critical |
| `breach_notification_timeline` | Critical |
| `data_retention_period` | Major |
| `third_party_sharing` | Major |
| `data_minimization` | Major |
| `user_access_rights` | Major |
| `childrens_data` | Major |
| `data_transfer_safeguards` | Major |
| `cookie_policy` | Minor |
| `contact_information` | Minor |
| `policy_update_notification` | Minor |

Policies are generated with 3–5 missing clauses. Agents must find them and assign the correct severity. Critical violations are weighted 3x in scoring.

**Scoring:** Severity-weighted recall with false positive penalty and severity-correct bonus.
**Max steps:** 30 | **Expected difficulty:** Hard

---

## 🔌 API Reference

### Core OpenEnv Endpoints

```
POST /reset?task_id={1|2|3}&seed={int}
  → Returns: { session_id, observation }

POST /step?session_id={id}
  Body: Action object
  → Returns: { observation, reward, done, info }

GET  /state/{session_id}
  → Returns: Current session state
```

### Required Additional Endpoints

```
GET  /tasks
  → Returns: List of tasks with full action schemas

POST /grader?session_id={id}
  → Returns: Final score 0.0–1.0 with breakdown

POST /baseline
  → Returns: Baseline scores for all 3 tasks
```

### Health

```
GET  /health  → { status: "healthy" }
GET  /        → Environment info
GET  /docs    → Swagger UI (interactive)
```

---

## 🎮 Action Space

All actions use this schema:

```json
{
  "action_type": "flag_violation | mark_field_present | mark_field_missing | submit",
  "field": "string (field or violation name)",
  "reason": "string (optional explanation)",
  "severity": "critical | major | minor (optional)",
  "section": "string (optional document section)"
}
```

### Example Actions

```json
// Task 1: Mark a field as present
{ "action_type": "mark_field_present", "field": "governing_law" }

// Task 1: Mark a field as missing
{ "action_type": "mark_field_missing", "field": "signature_block", "reason": "No signature lines found" }

// Task 2 & 3: Flag a violation
{ "action_type": "flag_violation", "field": "tax_rate_error", "reason": "Invoice uses 10% tax, PO specifies 8%", "severity": "major" }

// End episode
{ "action_type": "submit" }
```

---

## 📊 Observation Space

```json
{
  "task_id": 1,
  "task_name": "Required Field Detection",
  "task_description": "...",
  "document_text": "...full document...",
  "current_flags": ["signature_block"],
  "current_confirmations": ["party_a", "party_b"],
  "steps_taken": 3,
  "max_steps": 12,
  "cumulative_reward": 0.22,
  "available_actions": ["mark_field_present", "mark_field_missing", "submit"],
  "instructions": "..."
}
```

---

## 💰 Reward Function

Per-step rewards provide dense learning signal throughout the episode:

| Event | Reward |
|---|---|
| Correct violation flag | +0.15 |
| Correct field confirmed present | +0.10 |
| Correct field identified as missing | +0.12 |
| False positive flag | -0.10 |
| Correct severity on flag | +0.05 bonus |
| Wrong severity | -0.02 |
| Redundant action (already done) | -0.05 |
| Clean submit (good coverage) | +0.10 bonus |
| Submit too early | -0.05 |

Cumulative reward is clamped to `[0.0, 1.0]`.

---

## 📈 Baseline Scores

Scores from a rule-based keyword-matching agent (no LLM):

| Task | Difficulty | Baseline Score |
|---|---|---|
| Task 1 | Easy | ~0.72 |
| Task 2 | Medium | ~0.45 |
| Task 3 | Hard | ~0.38 |
| **Average** | — | **~0.52** |

A strong LLM agent should score 0.75+ on Task 1, 0.65+ on Task 2, and 0.55+ on Task 3.

---

## 🚀 Setup & Usage

### Run Locally

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/openenv-compliance
cd openenv-compliance

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 7860 --reload

# Open Swagger UI
open http://localhost:7860/docs
```

### Run with Docker

```bash
# Build
docker build -t openenv-compliance .

# Run
docker run -p 7860:7860 openenv-compliance

# Test
curl http://localhost:7860/health
```

### Run Baseline Inference

```bash
export OPENAI_API_KEY=sk-...
export OPENENV_BASE_URL=http://localhost:7860

python baseline/run_baseline.py
# Results saved to baseline_scores.json
```

### Quick Test (no API key needed)

```bash
# Reset task 1
curl -X POST "http://localhost:7860/reset?task_id=1&seed=42"

# Step with an action (replace SESSION_ID)
curl -X POST "http://localhost:7860/step?session_id=SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"action_type": "mark_field_present", "field": "party_a"}'

# Get final score
curl -X POST "http://localhost:7860/grader?session_id=SESSION_ID"

# Run internal baseline (no API key needed)
curl -X POST "http://localhost:7860/baseline"
```

---

## 🏗️ Project Structure

```
openenv-compliance/
├── app/
│   ├── main.py          # FastAPI routes
│   ├── env.py           # Core step/reset/state/grade logic
│   ├── models.py        # Pydantic typed models
│   ├── rewards.py       # Per-step reward function
│   ├── baseline_agent.py # Internal rule-based agent
│   ├── tasks/
│   │   ├── task1_fields.py   # Easy: field detection
│   │   ├── task2_invoice.py  # Medium: invoice validation
│   │   └── task3_policy.py   # Hard: policy audit
│   ├── graders/
│   │   ├── grader1.py   # Task 1 scoring
│   │   ├── grader2.py   # Task 2 scoring
│   │   └── grader3.py   # Task 3 scoring
│   └── documents/
│       └── generator.py # Synthetic document generator
├── baseline/
│   └── run_baseline.py  # OpenAI API inference script
├── openenv.yaml         # OpenEnv spec metadata
├── Dockerfile           # Container definition
├── requirements.txt
└── README.md
```

---

## 🛠️ Tech Stack

- **Python 3.11** — Runtime
- **FastAPI** — HTTP framework
- **Pydantic v2** — Typed models & validation
- **Uvicorn** — ASGI server
- **Docker** — Containerization
- **Hugging Face Spaces** — Deployment

---

## 📝 License

MIT License
