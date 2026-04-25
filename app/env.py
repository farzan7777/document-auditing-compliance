import random
import threading
from typing import Dict, Any, Optional, Tuple
from app.models import Action, ActionType, Observation, Reward, StepResponse, GraderResponse
from app.tasks import task1_fields, task2_invoice, task3_policy
from app.graders import grader1, grader2, grader3
from app.rewards import compute_step_reward

# ─── NEW IMPORTS (Theme 4 + Theme 1) ─────────────────────────────────────────
# These connect curriculum, verifier, and verifier_grader to env
from app.curriculum import curriculum
from app.agents.verifier import verifier
from app.graders.verifier_grader import grade_multi_agent

# ─── In-memory session store ──────────────────────────────────────────────────
# Key: session_id, Value: session dict
_sessions: Dict[str, Dict[str, Any]] = {}
# Serialize all session mutations (safe for parallel /baseline/llm worker threads).
_SESSION_LOCK = threading.RLock()


def _make_session_id() -> str:
    import uuid
    return str(uuid.uuid4())[:8]


def reset(task_id: int, seed: Optional[int] = None) -> Tuple[str, Observation]:
    """Start a new episode for the given task. Returns (session_id, observation)."""
    with _SESSION_LOCK:
        if seed is None:
            seed = random.randint(0, 9999)

        session_id = _make_session_id()

        # ─── NEW: Ask curriculum what difficulty to use (Theme 4) ─────────────────
        # curriculum watches scores and decides level 1-5
        difficulty = curriculum.get_difficulty()

        if task_id == 1:
            # ─── UPDATED: pass difficulty to generator ─────────────────────────────
            doc, ground_truth = task1_fields.generate_episode(seed=seed, difficulty=difficulty)
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
                "difficulty": difficulty,  # NEW: store difficulty in session
            }

        elif task_id == 2:
            # ─── UPDATED: pass difficulty to generator ─────────────────────────────
            po_doc, inv_doc, ground_truth = task2_invoice.generate_episode(seed=seed, difficulty=difficulty)
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
                "difficulty": difficulty,  # NEW: store difficulty in session
            }

        elif task_id == 3:
            # ─── UPDATED: pass difficulty to generator ─────────────────────────────
            doc, ground_truth = task3_policy.generate_episode(seed=seed, difficulty=difficulty)
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
                "difficulty": difficulty,  # NEW: store difficulty in session
            }
        else:
            raise ValueError(f"Invalid task_id: {task_id}. Must be 1, 2, or 3.")

        _sessions[session_id] = session
        obs = _build_observation(session)
        return session_id, obs


def step(session_id: str, action: Action) -> StepResponse:
    """Process one agent action and return observation + reward."""
    with _SESSION_LOCK:
        if session_id not in _sessions:
            raise KeyError(f"Session {session_id} not found. Call /reset first.")

        session = _sessions[session_id]

        if session["done"]:
            raise ValueError("Episode already done. Call /reset to start a new episode.")

        action_name = action.action_type.value
        allowed_actions = session.get("available_actions", [])
        if action_name not in allowed_actions:
            raise ValueError(
                f"Action '{action_name}' is not allowed for task {session['task_id']}. "
                f"Allowed actions: {allowed_actions}"
            )
        if action_name == ActionType.SUBMIT.value and session["task_id"] == 1:
            total_fields = len(session["ground_truth"])
            assessed_fields = len(session["confirmations"]) + len(session["missing_confirmed"])
            if assessed_fields < total_fields:
                raise ValueError(
                    f"Cannot submit task 1 yet: assessed {assessed_fields}/{total_fields} required fields. "
                    "Use mark_field_present/mark_field_missing for each field first."
                )

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
    with _SESSION_LOCK:
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
            "difficulty": session.get("difficulty", 1),  # NEW: show difficulty in state
        }


def grade(session_id: str, record_curriculum: bool = True) -> GraderResponse:
    """Run the grader on a completed episode."""
    with _SESSION_LOCK:
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

        # ─── NEW: Run verifier + multi-agent grading (Theme 1 + 4) ───────────────
        # Step 1: Call verifier to check auditor's work
        verifier_decisions = verifier.verify(
            task_id=task_id,
            document=session["document"],
            auditor_findings=session["flags_raised"],
            session=session,
        )

        # Step 2: Score both agents together
        multi_result = grade_multi_agent(
            task_id=task_id,
            session=session,
            verifier_decisions=verifier_decisions,
            ground_truth=ground_truth,
        )

        # Step 3: Tell curriculum this episode's score (Theme 4)
        # Use combined score so curriculum sees full picture
        if record_curriculum:
            curriculum.record_score(multi_result["combined_score"])

        # Step 4: Store multi-agent results in session for API access
        session["verifier_decisions"] = verifier_decisions
        session["multi_agent_result"] = multi_result

        # ─── RETURN ORIGINAL GraderResponse — UNCHANGED ──────────────────────────
        # We keep returning the same format judges expect
        # Multi-agent data available via /multi/grade endpoint
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


def grade_multi(session_id: str) -> Dict[str, Any]:
    """
    NEW FUNCTION — Returns full multi-agent grading results.
    Called by /multi/grade endpoint.
    Shows auditor score, verifier score, combined score,
    verifier decisions, and curriculum stats.
    """
    with _SESSION_LOCK:
        if session_id not in _sessions:
            raise KeyError(f"Session {session_id} not found.")

        session = _sessions[session_id]

        # If grade() hasn't been called yet, call it now
        if "multi_agent_result" not in session:
            grade(session_id)

        multi_result = session.get("multi_agent_result", {})
        verifier_decisions = session.get("verifier_decisions", [])
        verifier_summary = verifier.get_summary(verifier_decisions)

        return {
            "session_id": session_id,
            "task_id": session["task_id"],
            "task_name": session["task_name"],
            "difficulty_level": session.get("difficulty", 1),
            "auditor_score": multi_result.get("auditor_score", 0.0),
            "verifier_score": multi_result.get("verifier_score", 0.0),
            "combined_score": multi_result.get("combined_score", 0.0),
            "feedback": multi_result.get("feedback", ""),
            "verifier_decisions": verifier_decisions,
            "verifier_summary": verifier_summary,
            "auditor_breakdown": multi_result.get("auditor_breakdown", []),
            "verifier_breakdown": multi_result.get("verifier_breakdown", []),
            "curriculum": curriculum.get_stats(),
        }


def _build_observation(session: Dict[str, Any]) -> Observation:
    # ─── THIS FUNCTION IS COMPLETELY UNCHANGED ────────────────────────────────
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
