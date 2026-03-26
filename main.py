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

### How to use
1. `POST /reset?task_id=1` — Start a new episode
2. `POST /step` — Send actions with your `session_id`
3. `GET /state/{session_id}` — Check current state
4. `POST /grader` — Get your final score
    """,
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {
        "status": "ok",
        "name": "openenv-document-compliance",
        "version": "1.0.0",
        "tasks": [1, 2, 3],
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}


# ─── Core OpenEnv Endpoints ───────────────────────────────────────────────────

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

@app.post("/grader", response_model=GraderResponse, tags=["Grader"])
def grader(session_id: str = Query(..., description="Session ID to grade")):
    """
    Run the grader on a completed episode. Returns score 0.0–1.0 with breakdown.
    Can be called anytime (not just when done=True).
    """
    try:
        return env.grade(session_id=session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Tasks Endpoint ───────────────────────────────────────────────────────────

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
