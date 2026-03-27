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

> ✅ **Validator:** `openenv validate` passes 6/6 criteria
> 🚀 **Live API:** https://aakama-openenv-compliance.hf.space
> 📖 **Swagger UI:** https://aakama-openenv-compliance.hf.space/docs
> 💻 **GitHub:** https://github.com/aatif13/openenv-compliance

---

## 🎯 Environment Description

This environment simulates the work of a **compliance auditor** — a professional who reviews contracts, invoices, and policy documents to ensure they meet legal and regulatory standards. Unlike games or toy benchmarks, this environment reflects a genuine business task performed daily across legal, finance, and operations teams.

Agents interact through a standard HTTP API, receiving documents as observations, taking structured audit actions, and receiving per-step rewards that reflect audit quality.

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

**Scoring:** `correct_labels / total_fields` with false positive penalty
**Max steps:** 12 | **Difficulty:** Easy

---

### Task 2 — Invoice vs Purchase Order Validation *(Medium)*
**Objective:** Compare an invoice against a purchase order and detect discrepancies.

| Violation Type | Description |
|---|---|
| `qty_mismatch:<item>` | Quantity differs between PO and invoice |
| `price_mismatch:<item>` | Unit price differs between PO and invoice |
| `tax_rate_error` | Tax rate is wrong (should be 8%) |
| `missing_po_reference` | Invoice doesn't reference the PO number |

**Scoring:** Weighted F1 (recall-weighted) with precision penalty
**Max steps:** 20 | **Difficulty:** Medium

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

Critical violations are weighted 3x in scoring. Agents must find missing clauses and assign correct severity.

**Scoring:** Severity-weighted recall with false positive penalty and severity-correct bonus
**Max steps:** 30 | **Difficulty:** Hard

---

## 🔌 API Reference

### Base URL
```
https://aakama-openenv-compliance.hf.space
```

### Core OpenEnv Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/reset?task_id={1\|2\|3}&seed={int}` | Start new episode |
| `POST` | `/step?session_id={id}` | Send action, get reward |
| `GET` | `/state/{session_id}` | Get current state |
| `POST` | `/grader?session_id={id}` | Get final score 0.0–1.0 |
| `GET` | `/tasks` | List tasks + action schemas |
| `POST` | `/baseline` | Run baseline on all 3 tasks |
| `GET` | `/metadata` | Environment metadata |
| `GET` | `/schema` | Action/observation/state schemas |
| `POST` | `/mcp` | JSON-RPC 2.0 MCP endpoint |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Swagger UI |

---

## 🎮 Action Space

```json
{
  "action_type": "flag_violation | mark_field_present | mark_field_missing | submit",
  "field": "string (field or violation name)",
  "reason": "string (optional)",
  "severity": "critical | major | minor (optional)",
  "section": "string (optional)"
}
```

### Example Actions

```json
{ "action_type": "mark_field_present", "field": "governing_law" }

{ "action_type": "mark_field_missing", "field": "signature_block", "reason": "No signature lines found" }

{ "action_type": "flag_violation", "field": "tax_rate_error", "reason": "Invoice uses 10% tax, PO specifies 8%", "severity": "major" }

{ "action_type": "submit" }
```

---

## 📊 Observation Space

```json
{
  "task_id": 1,
  "task_name": "Required Field Detection",
  "document_text": "...full document text...",
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

Per-step rewards provide dense signal throughout the episode:

| Event | Reward |
|---|---|
| Correct violation flagged | +0.15 |
| Correct field confirmed present | +0.10 |
| Correct field identified as missing | +0.12 |
| False positive flag | -0.10 |
| Correct severity on flag | +0.05 bonus |
| Wrong severity | -0.02 |
| Redundant action | -0.05 |
| Clean submit (good coverage) | +0.10 bonus |
| Submit too early | -0.05 |

Cumulative reward is clamped to `[0.0, 1.0]`.

---

## 📈 Baseline Scores

Scores from the internal rule-based keyword-matching agent (no LLM):

| Task | Difficulty | Baseline Score |
|---|---|---|
| Task 1 | Easy | 0.8333 |
| Task 2 | Medium | 0.7500 |
| Task 3 | Hard | 0.9333 |
| **Average** | — | **0.8389** |

Run the baseline yourself (no API key needed):
```bash
curl -X POST "https://aakama-openenv-compliance.hf.space/baseline"
```

---

## 🚀 Setup & Usage

### Option 1 — Use the Live API (no setup needed)
The environment is already running. Just call the endpoints directly:

```bash
# Start episode
curl -X POST "https://aakama-openenv-compliance.hf.space/reset?task_id=1&seed=42"

# Send action (replace SESSION_ID)
curl -X POST "https://aakama-openenv-compliance.hf.space/step?session_id=SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"action_type": "mark_field_present", "field": "party_a"}'

# Get score
curl -X POST "https://aakama-openenv-compliance.hf.space/grader?session_id=SESSION_ID"
```

### Option 2 — Run Locally

```bash
git clone https://github.com/aatif13/openenv-compliance
cd openenv-compliance
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 7860 --reload
# Open http://localhost:7860/docs
```

### Option 3 — Run with Docker

```bash
git clone https://github.com/aatif13/openenv-compliance
cd openenv-compliance
docker build -t openenv-compliance .
docker run -p 7860:7860 openenv-compliance
curl http://localhost:7860/health
```

### Option 4 — Run OpenAI Baseline Inference

```bash
export OPENAI_API_KEY=sk-...
export OPENENV_BASE_URL=https://aakama-openenv-compliance.hf.space
python baseline/run_baseline.py
# Saves results to baseline_scores.json
```

### Option 5 — Validate with OpenEnv

```bash
pip install openenv-core
openenv validate https://aakama-openenv-compliance.hf.space
# passes: true, 6/6 criteria
```

---

## 🏗️ Project Structure

```
openenv-compliance/
├── app/
│   ├── main.py              # FastAPI routes (all endpoints)
│   ├── env.py               # Core step/reset/state/grade logic
│   ├── models.py            # Pydantic typed models
│   ├── rewards.py           # Per-step reward function
│   ├── baseline_agent.py    # Internal rule-based agent
│   ├── tasks/
│   │   ├── task1_fields.py  # Easy: field detection
│   │   ├── task2_invoice.py # Medium: invoice validation
│   │   └── task3_policy.py  # Hard: policy audit
│   ├── graders/
│   │   ├── grader1.py       # Task 1 scoring
│   │   ├── grader2.py       # Task 2 scoring
│   │   └── grader3.py       # Task 3 scoring
│   └── documents/
│       └── generator.py     # Synthetic document generator
├── baseline/
│   └── run_baseline.py      # OpenAI API inference script
├── openenv.yaml             # OpenEnv spec metadata
├── Dockerfile               # Container definition
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
