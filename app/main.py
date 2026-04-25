from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from app.models import (
    Action, StepResponse, Observation, GraderResponse,
    TaskInfo, BaselineResponse,
)

# FastAPI instance must exist before importing `env` / tasks: their import graph is
# large; any indirect import of `app.main` must see `app` already (avoids uvicorn
# "Attribute app not found in module app.main" from a half-initialized module).
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
    """,
    version="2.0.0",
    docs_url=None,
    redoc_url=None,
)

# ── CRITICAL: Mount static BEFORE defining /docs route ────────────────────────
# If mounted after, FastAPI's own router intercepts first → "Not Found"
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from app import env
from app.tasks import task1_fields, task2_invoice, task3_policy


# ─── Custom Swagger UI ────────────────────────────────────────────────────────

@app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
async def custom_docs():
    with open("static/swagger-ui-custom.html", "r") as f:
        return HTMLResponse(content=f.read())


# ─── Dashboard UI ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    # Hackathon Demo Feature: Reset curriculum to Level 1 on page refresh
    from app.curriculum import curriculum
    curriculum.reset_for_demo()
    
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())


# ─── /info — used by dashboard status bar ─────────────────────────────────────
# The root / now returns HTML, so we expose /info for the status bar fetch

@app.get("/info", tags=["Health"])
def info():
    """
    Returns environment metadata for the UI dashboard.
    Called by index.html to populate the status bar (version, task count, etc.)
    """
    return {
        "status": "ok",
        "name": "openenv-document-compliance",
        "version": "2.0.0",
        "tasks": [1, 2, 3],
        "themes": ["3.1 Professional Tasks", "1 Multi-Agent", "4 Self-Improvement"],
    }


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}


# ─── Core OpenEnv Endpoints ───────────────────────────────────────────────────

@app.post("/reset", response_model=dict, tags=["OpenEnv"])
def reset(
    task_id: int = Query(..., ge=1, le=3, description="Task ID: 1 (easy), 2 (medium), 3 (hard)"),
    seed: Optional[int] = Query(None, description="Random seed for reproducibility"),
):
    """Start a new episode. Returns session_id and initial observation."""
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
    """Send one action. Returns new observation, reward, done flag, and info."""
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
    """Run the grader on a completed episode. Returns score 0.0-1.0 with breakdown."""
    try:
        return env.grade(session_id=session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Tasks Endpoint ───────────────────────────────────────────────────────────

@app.get("/tasks", tags=["Tasks"])
def tasks():
    """List all tasks with their action schemas. Required by OpenEnv spec."""
    return {
        "tasks": [
            task1_fields.get_task_info(),
            task2_invoice.get_task_info(),
            task3_policy.get_task_info(),
        ]
    }


# ─── Baseline Endpoint ────────────────────────────────────────────────────────

@app.post("/baseline", response_model=BaselineResponse, tags=["Baseline"])
def baseline(
    seed_1: Optional[int] = Query(42, description="Seed for Task 1"),
    seed_2: Optional[int] = Query(42, description="Seed for Task 2"),
    seed_3: Optional[int] = Query(42, description="Seed for Task 3"),
):
    """Run rule-based baseline agent on all 3 tasks. No API key required."""
    from app.baseline_agent import run_baseline_internal
    try:
        result = run_baseline_internal(seeds={1: seed_1, 2: seed_2, 3: seed_3})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Baseline failed: {str(e)}")


@app.post("/baseline/llm", tags=["Baseline"])
def baseline_llm(
    seed_1: Optional[int] = Query(42, description="Seed for Task 1"),
    seed_2: Optional[int] = Query(42, description="Seed for Task 2"),
    seed_3: Optional[int] = Query(42, description="Seed for Task 3"),
):
    """
    **Groq LLM agent** — uses `GROQ_MODEL` (default: fast 8B) to audit documents step-by-step.

    Requires GROQ_API_KEY environment variable set in HF Space secrets.
    Falls back to rule-based agent automatically if key is not set.

    This is the trained vs baseline comparison judges want to see:
    - Rule-based baseline: keyword matching (~0.85 avg)
    - LLM agent: semantic reasoning (scores higher, reasoning visible)

    Each call records 3 episode scores to the curriculum system (Theme #4).
    Set different seeds to get different documents and demonstrate generalisation.
    """
    from app.baseline_agent import run_llm_agent
    try:
        result = run_llm_agent(seeds={1: seed_1, 2: seed_2, 3: seed_3})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM agent failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-AGENT + CURRICULUM ENDPOINTS — Theme #1 + #4
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/curriculum/stats", tags=["Multi-Agent"])
def curriculum_stats():
    """
    Theme #4 Self Improvement — current curriculum state.
    Returns level 1-5, rolling average, trend, and full level history.
    Judges call this to watch difficulty progression in real-time.
    """
    from app.curriculum import curriculum
    try:
        return curriculum.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/multi/reset", tags=["Multi-Agent"])
def multi_reset(
    task_id: int = Query(..., ge=1, le=3, description="Task ID: 1, 2, or 3"),
    seed: Optional[int] = Query(None, description="Random seed"),
):
    """
    Theme #1 + #4 Multi-Agent Reset.
    Same as /reset but includes curriculum difficulty info.
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


@app.post("/multi/grade", tags=["Multi-Agent"])
def multi_grade(session_id: str = Query(..., description="Session ID to grade")):
    """
    Theme #1 Multi-Agent Grading.
    Returns auditor score, verifier score, combined score, and all APPROVE/REJECT decisions.
    """
    try:
        return env.grade_multi(session_id=session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/curriculum/reset", tags=["Multi-Agent"])
def curriculum_reset():
    """Reset curriculum back to Level 1 for demo purposes."""
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