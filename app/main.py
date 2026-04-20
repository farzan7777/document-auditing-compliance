from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
import os

from app.models import (
    Action, StepResponse, Observation, GraderResponse,
    TaskInfo, BaselineResponse
)
from app import env
from app.tasks import task1_fields, task2_invoice, task3_policy

app = FastAPI(
    title="OpenEnv: Document Compliance Auditing",
    description="""
## 📋 Document Compliance Auditing Environment

An OpenEnv-compliant environment where AI agents audit business documents
for compliance violations across contracts, invoices, and privacy policies.

### Tasks
- **Task 1** (Easy): Required field detection in employment contracts
- **Task 2** (Medium): Invoice vs Purchase Order validation
- **Task 3** (Hard): Regulatory privacy policy compliance audit

### Multi-Agent System (Theme #1 + #3.1 + #4)
- **Auditor Agent**: Reads documents and flags violations
- **Verifier Agent**: Checks auditor findings for hallucinations
- **Curriculum**: Auto-increases difficulty as agents improve

### How to use (Single Agent)
1. `POST /reset?task_id=1` — Start a new episode
2. `POST /step` — Send actions with your `session_id`
3. `GET /state/{session_id}` — Check current state
4. `POST /grader` — Get your final score

### How to use (Multi Agent)
1. `POST /multi/reset?task_id=1` — Start episode with curriculum difficulty
2. `POST /step` — Send auditor actions
3. `POST /multi/grade` — Get both agent scores + verifier decisions
4. `GET /curriculum/stats` — See difficulty progression
    """,
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health Check ─────────────────────────────────────────────────────────────
# UNCHANGED FROM ORIGINAL

@app.get("/", tags=["Health"])
def root():
    return {
        "status": "ok",
        "name": "openenv-document-compliance",
        "version": "2.0.0",
        "tasks": [1, 2, 3],
        "themes": ["3.1 Professional Tasks", "1 Multi-Agent", "4 Self-Improvement"],
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}


# ─── Core OpenEnv Endpoints ───────────────────────────────────────────────────
# ALL UNCHANGED FROM ORIGINAL

@app.post("/reset", response_model=dict, tags=["OpenEnv"])
def reset(
    task_id: int = Query(..., ge=1, le=3, description="Task ID: 1 (easy), 2 (medium), 3 (hard)"),
    seed: Optional[int] = Query(None, description="Random seed for reproducibility"),
):
    """
    Start a new episode. Returns session_id and initial observation.
    The agent must use session_id in all subsequent /step calls.
    """
    try:
        session_id, observation = env.reset(task_id=task_id, seed=seed)
        return {
            "session_id": session_id,
            "observation": observation.model_dump(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step", response_model=StepResponse, tags=["OpenEnv"])
def step(
    session_id: str = Query(..., description="Session ID from /reset"),
    action: Action = None,
):
    """
    Send one action. Returns new observation, reward, done flag, and info.
    """
    if action is None:
        raise HTTPException(status_code=422, detail="Action body required")
    try:
        return env.step(session_id=session_id, action=action)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state/{session_id}", tags=["OpenEnv"])
def state(session_id: str):
    """Return current state of a session without taking an action."""
    try:
        return env.state(session_id=session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── Grader Endpoint ──────────────────────────────────────────────────────────
# UNCHANGED FROM ORIGINAL

@app.post("/grader", response_model=GraderResponse, tags=["Grader"])
def grader(session_id: str = Query(..., description="Session ID to grade")):
    """
    Run the grader on a completed episode. Returns score 0.0-1.0 with breakdown.
    Can be called anytime (not just when done=True).
    """
    try:
        return env.grade(session_id=session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Tasks Endpoint ───────────────────────────────────────────────────────────
# UNCHANGED FROM ORIGINAL

@app.get("/tasks", tags=["Tasks"])
def tasks():
    """
    List all tasks with their action schemas.
    Required by OpenEnv spec for automated checkers.
    """
    return {
        "tasks": [
            task1_fields.get_task_info(),
            task2_invoice.get_task_info(),
            task3_policy.get_task_info(),
        ]
    }


# ─── Baseline Endpoint ────────────────────────────────────────────────────────
# UNCHANGED FROM ORIGINAL

@app.post("/baseline", response_model=BaselineResponse, tags=["Baseline"])
def baseline():
    """
    Trigger the baseline inference script server-side.
    Runs a rule-based agent against all 3 tasks and returns scores.
    This endpoint uses the internal baseline agent (no OpenAI API key required).
    """
    from app.baseline_agent import run_baseline_internal
    try:
        result = run_baseline_internal()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Baseline failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# NEW ENDPOINTS BELOW — Theme #1 + #4
# Everything above this line is UNCHANGED from original
# ═══════════════════════════════════════════════════════════════════════════════


# ─── Curriculum Stats Endpoint (Theme #4) ─────────────────────────────────────

@app.get("/curriculum/stats", tags=["Multi-Agent"])
def curriculum_stats():
    """
    NEW — Theme #4 Self Improvement.

    Shows the curriculum system status.
    Judges use this to see difficulty progression over time.

    Returns:
    - current_level: difficulty level 1-5
    - level_name: human readable level name
    - rolling_average: average score of recent episodes
    - total_episodes: how many episodes have run
    - trend: improving / stable / declining
    - level_history: when and why difficulty changed
    """
    from app.curriculum import curriculum
    try:
        return curriculum.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Multi-Agent Reset Endpoint (Theme #1 + #4) ───────────────────────────────

@app.post("/multi/reset", tags=["Multi-Agent"])
def multi_reset(
    task_id: int = Query(..., ge=1, le=3, description="Task ID: 1, 2, or 3"),
    seed: Optional[int] = Query(None, description="Random seed"),
):
    """
    NEW — Theme #1 + #4 Multi-Agent Reset.

    Same as /reset but also returns:
    - difficulty_level: current curriculum level (1-5)
    - level_name: human readable name
    - curriculum_stats: full curriculum information

    Use this instead of /reset to see the full multi-agent system.
    """
    try:
        from app.curriculum import curriculum
        session_id, observation = env.reset(task_id=task_id, seed=seed)
        return {
            "session_id": session_id,
            "observation": observation.model_dump(),
            "difficulty_level": curriculum.get_difficulty(),
            "level_name": curriculum._get_level_name(),
            "curriculum_stats": curriculum.get_stats(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Multi-Agent Grade Endpoint (Theme #1) ────────────────────────────────────

@app.post("/multi/grade", tags=["Multi-Agent"])
def multi_grade(session_id: str = Query(..., description="Session ID to grade")):
    """
    NEW — Theme #1 Multi-Agent Grading.

    Returns full multi-agent results including:
    - auditor_score: how well auditor found violations (0-1)
    - verifier_score: how well verifier checked findings (0-1)
    - combined_score: weighted combination (0-1)
    - verifier_decisions: every APPROVE/REJECT with reasons
    - verifier_summary: counts of approvals and rejections
    - auditor_breakdown: detailed auditor scoring
    - verifier_breakdown: detailed verifier scoring
    - curriculum: current difficulty stats

    This is the KEY endpoint for judges to see Theme #1 working.
    """
    try:
        return env.grade_multi(session_id=session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Curriculum Reset Endpoint (Theme #4 Demo) ────────────────────────────────

@app.post("/curriculum/reset", tags=["Multi-Agent"])
def curriculum_reset():
    """
    NEW — Reset curriculum back to Level 1.

    Use this to reset the difficulty system for a fresh demo.
    Useful for judges who want to watch the curriculum progress
    from the beginning.
    """
    from app.curriculum import curriculum
    try:
        curriculum.reset_for_demo()
        return {
            "message": "Curriculum reset to Level 1",
            "current_level": 1,
            "level_name": "Junior Compliance Clerk",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))