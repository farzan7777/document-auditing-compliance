import random
from typing import Dict, Any, Optional, Tuple
from app.models import Action, ActionType, Observation, Reward, StepResponse, GraderResponse
from app.tasks import task1_fields, task2_invoice, task3_policy
from app.graders import grader1, grader2, grader3
from app.rewards import compute_step_reward

# ─── In-memory session store ──────────────────────────────────────────────────
# Key: session_id, Value: session dict
_sessions: Dict[str, Dict[str, Any]] = {}


def _make_session_id() -> str:
    import uuid
    return str(uuid.uuid4())[:8]


def reset(task_id: int, seed: Optional[int] = None) -> Tuple[str, Observation]:
    """Start a new episode for the given task. Returns (session_id, observation)."""
    if seed is None:
        seed = random.randint(0, 9999)

    session_id = _make_session_id()

    if task_id == 1:
        doc, ground_truth = task1_fields.generate_episode(seed=seed)
        session = {
            "task_id": 1,
            "task_name": task1_fields.TASK_NAME,
            "document": doc,
            "ground_truth": ground_truth,
            "instructions": task1_fields.INSTRUCTIONS,
            "available_actions": task1_fields.AVAILABLE_ACTIONS,
            "max_steps": task1_fields.MAX_STEPS,
            "flags_raised": [],
            "confirmations": [],
            "missing_confirmed": [],
            "steps_taken": 0,
            "cumulative_reward": 0.0,
            "done": False,
            "seed": seed,
        }

    elif task_id == 2:
        po_doc, inv_doc, ground_truth = task2_invoice.generate_episode(seed=seed)
        combined_doc = f"--- PURCHASE ORDER ---\n{po_doc}\n\n--- INVOICE ---\n{inv_doc}"
        session = {
            "task_id": 2,
            "task_name": task2_invoice.TASK_NAME,
            "document": combined_doc,
            "ground_truth": ground_truth,
            "instructions": task2_invoice.INSTRUCTIONS,
            "available_actions": task2_invoice.AVAILABLE_ACTIONS,
            "max_steps": task2_invoice.MAX_STEPS,
            "flags_raised": [],
            "confirmations": [],
            "missing_confirmed": [],
            "steps_taken": 0,
            "cumulative_reward": 0.0,
            "done": False,
            "seed": seed,
        }

    elif task_id == 3:
        doc, ground_truth = task3_policy.generate_episode(seed=seed)
        session = {
            "task_id": 3,
            "task_name": task3_policy.TASK_NAME,
            "document": doc,
            "ground_truth": ground_truth,
            "instructions": task3_policy.INSTRUCTIONS,
            "available_actions": task3_policy.AVAILABLE_ACTIONS,
            "max_steps": task3_policy.MAX_STEPS,
            "flags_raised": [],
            "confirmations": [],
            "missing_confirmed": [],
            "steps_taken": 0,
            "cumulative_reward": 0.0,
            "done": False,
            "seed": seed,
        }
    else:
        raise ValueError(f"Invalid task_id: {task_id}. Must be 1, 2, or 3.")

    _sessions[session_id] = session
    obs = _build_observation(session)
    return session_id, obs


def step(session_id: str, action: Action) -> StepResponse:
    """Process one agent action and return observation + reward."""
    if session_id not in _sessions:
        raise KeyError(f"Session {session_id} not found. Call /reset first.")

    session = _sessions[session_id]

    if session["done"]:
        raise ValueError("Episode already done. Call /reset to start a new episode.")

    session["steps_taken"] += 1

    # Compute step reward
    reward_value, reward_reason = compute_step_reward(action, session)

    # Update session state
    if action.action_type == ActionType.MARK_FIELD_PRESENT and action.field:
        if action.field not in session["confirmations"]:
            session["confirmations"].append(action.field)

    elif action.action_type == ActionType.MARK_FIELD_MISSING and action.field:
        if action.field not in session["missing_confirmed"]:
            session["missing_confirmed"].append(action.field)

    elif action.action_type == ActionType.FLAG_VIOLATION and action.field:
        if action.field not in session["flags_raised"]:
            session["flags_raised"].append(action.field)

    session["cumulative_reward"] = round(
        min(1.0, max(0.0, session["cumulative_reward"] + reward_value)), 4
    )

    # Check done conditions
    done = False
    if action.action_type == ActionType.SUBMIT:
        done = True
    elif session["steps_taken"] >= session["max_steps"]:
        done = True

    session["done"] = done

    reward = Reward(
        value=round(reward_value, 4),
        reason=reward_reason,
        cumulative=session["cumulative_reward"],
    )

    obs = _build_observation(session)

    info = {
        "steps_taken": session["steps_taken"],
        "max_steps": session["max_steps"],
        "flags_raised": session["flags_raised"],
        "confirmations": session["confirmations"],
        "missing_confirmed": session["missing_confirmed"],
    }

    return StepResponse(observation=obs, reward=reward, done=done, info=info)


def state(session_id: str) -> Dict[str, Any]:
    """Return current session state."""
    if session_id not in _sessions:
        raise KeyError(f"Session {session_id} not found.")
    session = _sessions[session_id]
    return {
        "session_id": session_id,
        "task_id": session["task_id"],
        "task_name": session["task_name"],
        "steps_taken": session["steps_taken"],
        "max_steps": session["max_steps"],
        "cumulative_reward": session["cumulative_reward"],
        "done": session["done"],
        "flags_raised": session["flags_raised"],
        "confirmations": session["confirmations"],
        "missing_confirmed": session["missing_confirmed"],
        "seed": session["seed"],
    }


def grade(session_id: str) -> GraderResponse:
    """Run the grader on a completed episode."""
    if session_id not in _sessions:
        raise KeyError(f"Session {session_id} not found.")

    session = _sessions[session_id]
    task_id = session["task_id"]
    ground_truth = session["ground_truth"]

    if task_id == 1:
        result = grader1.grade(
            ground_truth=ground_truth,
            agent_present=session["confirmations"],
            agent_missing=session["missing_confirmed"],
        )
    elif task_id == 2:
        result = grader2.grade(
            ground_truth=ground_truth,
            agent_flags=session["flags_raised"],
        )
    elif task_id == 3:
        agent_flags = [
            {"field": f, "severity": "major"}
            for f in session["flags_raised"]
        ]
        result = grader3.grade(
            ground_truth=ground_truth,
            agent_flags=agent_flags,
        )
    else:
        raise ValueError(f"Unknown task_id: {task_id}")

    return GraderResponse(
        task_id=task_id,
        task_name=session["task_name"],
        score=result["score"],
        breakdown=result["breakdown"],
        feedback=result["feedback"],
        total_steps=session["steps_taken"],
        violations_found=result.get("violations_found", 0),
        violations_missed=result.get("violations_missed", 0),
        false_positives=result.get("false_positives", 0),
    )


def _build_observation(session: Dict[str, Any]) -> Observation:
    return Observation(
        task_id=session["task_id"],
        task_name=session["task_name"],
        task_description=session.get("instructions", ""),
        document_text=session["document"],
        current_flags=session["flags_raised"],
        current_confirmations=session["confirmations"],
        steps_taken=session["steps_taken"],
        max_steps=session["max_steps"],
        cumulative_reward=session["cumulative_reward"],
        available_actions=session["available_actions"],
        instructions=session.get("instructions", ""),
    )
