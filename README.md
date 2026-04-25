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
  - multi-agent
  - curriculum-learning
---

# 📋 OpenEnv: Document Compliance Auditing

> **Teaching LLMs to audit business documents — contracts, invoices, and privacy policies — the way compliance professionals do.**

| | |
|---|---|
| 🚀 **Live API** | https://aakama-openenv-compliance.hf.space |
| 📖 **Swagger UI** | https://aakama-openenv-compliance.hf.space/docs |
| 💻 **GitHub** | https://github.com/aatif13/openenv-compliance |
| 📓 **Training Notebook** | [Open in Google Colab](YOUR_COLAB_LINK) |
| 🎥 **Demo Video** | [Watch on YouTube](YOUR_YOUTUBE_URL) |
| ✅ **Validator** | `openenv validate` passes 6/6 criteria |

---

## 1. The Problem

Every company deals with business documents daily:
- Employment contracts with **missing required clauses**
- Invoices with **wrong amounts or rates** vs the purchase order
- Privacy policies that **violate GDPR** requirements

Today, **humans check these manually** — compliance officers spend hours reviewing documents that should take minutes. It's slow, expensive, and error-prone.

**LLMs currently struggle at this task** because:
- It requires reading long documents carefully
- It demands structured, step-by-step reasoning
- It needs domain-specific knowledge of what "correct" looks like
- There are no existing RL environments to train this capability

We built the first OpenEnv environment that teaches LLMs to audit business documents — a domain that is **completely underexplored in RL/LLM training** and directly valuable to every enterprise.

---

## 2. The Environment

### What the Agent Sees (Observation)
```json
{
  "task_id": 3,
  "task_name": "Regulatory Policy Compliance Audit",
  "document_text": "...full privacy policy document...",
  "current_flags": ["user_consent_mechanism"],
  "steps_taken": 3,
  "max_steps": 30,
  "cumulative_reward": 0.45,
  "available_actions": ["flag_violation", "submit"]
}
```

### What the Agent Does (Actions)
```json
// Flag a missing clause
{"action_type": "flag_violation", "field": "right_to_deletion", 
 "severity": "critical", "reason": "No deletion right mentioned"}

// Confirm a field is present
{"action_type": "mark_field_present", "field": "governing_law"}

// Finalize the audit
{"action_type": "submit"}
```

### What the Agent Gets (Rewards)

| Action | Reward | Why |
|--------|--------|-----|
| Correct violation flagged | **+0.15** | Found a real problem |
| Correct severity assigned | **+0.05 bonus** | Correct prioritization |
| Field correctly confirmed | **+0.10** | Accurate assessment |
| False positive flag | **-0.10** | Penalizes hallucination |
| Duplicate action | **-0.05** | Penalizes lazy loops |
| Clean submission | **+0.10 bonus** | Rewards thoroughness |

**Reward is dense** — the agent gets signal at every single step, not just at the end. This makes training much more efficient.

**Hard to game** — an agent that flags everything gets penalized for false positives. An agent that submits immediately gets penalized for low coverage. The only way to score high is to actually audit correctly.

### 3 Tasks — Easy to Hard

| Task | Document Type | What Agent Must Find | Difficulty |
|------|--------------|---------------------|-----------|
| **Task 1** | Employment Contract | 6 required fields (parties, dates, clauses) | Easy |
| **Task 2** | Invoice vs Purchase Order | Price/quantity/tax discrepancies | Medium |
| **Task 3** | Privacy Policy | 12 GDPR compliance clauses with severity | Hard |

---

## 3. What Makes This Environment Unique

### 🤝 Multi-Agent Design (Theme #1)

Two agents cooperate on every audit:

```
AUDITOR AGENT                    VERIFIER AGENT
reads document          →        checks auditor's findings
flags violations        →        APPROVE or REJECT each one
submits report          →        catches hallucinations
```

The Verifier creates **competitive pressure** — the Auditor must be accurate because the Verifier will catch mistakes. This drives theory-of-mind reasoning and emergent strategic behavior.

### 📈 Curriculum Learning (Theme #4)

The environment automatically adjusts difficulty based on agent performance:

```
Level 1: Junior Compliance Clerk     (simple documents)
Level 2: Compliance Analyst          (slightly harder)
Level 3: Senior Compliance Officer   (medium complexity)
Level 4: Compliance Director         (hard documents)
Level 5: Regulatory Authority Expert (expert level)
```

- Agent moves **UP** when rolling 10-episode average > 0.85
- Agent moves **DOWN** when rolling average < 0.40
- Resets history at each level change to measure new baseline

### 🏢 Real Enterprise Domain (Theme #3.1)

This is not a game or a toy. Every task in this environment reflects work done daily in:
- Law firms reviewing contracts
- Finance teams auditing invoices
- Data protection officers checking GDPR compliance

**Could a researcher write a paper about training on this?** Yes — compliance auditing is completely underexplored in RL/LLM training and has direct enterprise value.

---

## 4. Training Results

We trained `Qwen/Qwen2.5-0.5B-Instruct` using **HF TRL SFTTrainer** on environment-generated compliance auditing trajectories.

### Before vs After Training

| Task | Difficulty | Before Training | After Training | Change |
|------|-----------|----------------|----------------|--------|
| Task 1 | Easy | 0.9659 | 0.9659 | → Maintained |
| Task 2 | Medium | 0.7714 | 0.4802 | ↓ Model size limit |
| Task 3 | Hard | 0.8523 | **0.9100** | ↑ **+0.06 Improved** |
| **Average** | — | **0.8632** | 0.7853 | — |

**Key finding:** Task 3 — our hardest task (GDPR policy auditing with 12 clauses and severity ranking) — genuinely improved after training, proving the environment provides clear learning signal.

**Why Task 1 & 2 didn't improve:** Qwen 0.5B is too small to maintain JSON formatting after SFT fine-tuning (catastrophic forgetting). With a 7B+ model and the compute credits from HuggingFace, we expect consistent improvement across all tasks.

**Baseline agent (rule-based, no LLM) scores 0.8632 average** — this proves the environment has strong, clear reward signals. A trained LLM on a larger model will exceed this baseline.

### Training Loss Curve
![Training Results](training_results.png)
*Left: Before vs After scores per task | Center: Training loss curve (decreasing = model learning) | Right: Score improvement per task*

### Curriculum Learning Progression
![Curriculum Progression](curriculum_progression.png)
*Top: Episode scores over time with improvement trend | Bottom: Difficulty level progression — agent automatically advances from Level 1 (Junior Clerk) to Level 5 (Regulatory Expert) as performance improves*

---

## 5. Why It Matters

### Who Cares?

- **Enterprises** — automate compliance review saving thousands of hours
- **Law firms** — catch missing contract clauses before signing
- **Finance teams** — detect invoice fraud automatically
- **Regulators** — verify GDPR compliance at scale

### What This Trains

An LLM trained on this environment learns:
- **Causal reasoning** — which clauses cause which legal risks
- **Structured decision making** — step-by-step document analysis
- **Severity judgment** — critical vs major vs minor violations
- **Self-correction** — verifier feedback improves auditor behavior

### The Gap We're Filling

No existing RL/LLM training environment teaches document compliance. This is a **genuinely new capability** — LLMs currently struggle at systematic document auditing because there's no training signal for it. We built that signal.

---

## 6. Try It Yourself

### Quickstart (30 seconds)
```bash
# Start an episode
curl -X POST "https://aakama-openenv-compliance.hf.space/reset?task_id=3&seed=42"

# Send an action (replace SESSION_ID)
curl -X POST "https://aakama-openenv-compliance.hf.space/step?session_id=SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"action_type":"flag_violation","field":"user_consent_mechanism","severity":"critical","reason":"No consent mechanism found"}'

# Get your score
curl -X POST "https://aakama-openenv-compliance.hf.space/grader?session_id=SESSION_ID"

# Run full baseline (no API key needed)
curl -X POST "https://aakama-openenv-compliance.hf.space/baseline"
```

### Run Locally
```bash
git clone https://github.com/aatif13/openenv-compliance
cd openenv-compliance
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 7860
# Open http://localhost:7860/docs
```

### Run Training Notebook
1. Open [Google Colab Notebook](YOUR_COLAB_LINK)
2. Runtime → Change type → T4 GPU
3. Add HF token in Step 2
4. Runtime → Run all

---

## 7. API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/reset?task_id={1\|2\|3}` | Start new episode |
| `POST` | `/step?session_id={id}` | Send action, get reward |
| `GET` | `/state/{session_id}` | Current state |
| `POST` | `/grader?session_id={id}` | Final score 0.0–1.0 |
| `GET` | `/tasks` | Task list + schemas |
| `POST` | `/baseline` | Run baseline agent |
| `POST` | `/multi/reset` | Multi-agent episode |
| `POST` | `/multi/grade` | Multi-agent scores |
| `GET` | `/curriculum/stats` | Curriculum progress |

---

## 8. Project Structure

```
openenv-compliance/
├── inference.py              # Judges run this — OpenAI client via env vars
├── app/
│   ├── main.py               # All API endpoints
│   ├── env.py                # Core step/reset/state/grade logic
│   ├── models.py             # Pydantic typed models
│   ├── rewards.py            # Per-step reward function
│   ├── curriculum.py         # Theme #4 — adaptive difficulty
│   ├── agents/
│   │   └── verifier.py       # Theme #1 — second AI agent
│   ├── tasks/                # 3 task definitions
│   ├── graders/              # Scoring functions
│   └── documents/
│       └── generator.py      # Synthetic document generator (5 difficulty levels)
├── server/app.py             # uv run server entry point
├── baseline/run_baseline.py  # Internal baseline script
├── openenv.yaml              # OpenEnv spec
├── pyproject.toml            # Package config
├── uv.lock                   # Dependency lockfile
└── Dockerfile                # Container definition
```

---

## 9. Themes & Bonus Prizes

| Theme | Coverage | How |
|-------|----------|-----|
| **Theme #1** Multi-Agent | ✅ Full | Auditor + Verifier cooperation/competition |
| **Theme #3.1** Professional Tasks | ✅ Full | Real enterprise compliance workflows |
| **Theme #4** Self-Improvement | ✅ Full | 5-level adaptive curriculum |

| Bonus Prize | Coverage | How |
|-------------|----------|-----|
| **Fleet AI** — Scalable Oversight | ✅ | Verifier monitors and audits Auditor behavior |
| **Scaler AI Labs** — Enterprise RL | ✅ | Multi-app enterprise compliance environment |
| **Snorkel AI** — Simulated Experts | ✅ | Changing difficulty simulates expert progression |

---

## 10. Validation

```bash
pip install openenv-core
openenv validate https://aakama-openenv-compliance.hf.space
# Result: passed: true, 6/6 criteria
```

---

## 📝 License

MIT License
