import pytest

from app import env
from app.models import Action


def test_task1_rejects_flag_violation_action_type():
    session_id, _ = env.reset(task_id=1, seed=42)

    with pytest.raises(ValueError, match="not allowed for task 1"):
        env.step(
            session_id=session_id,
            action=Action(
                action_type="flag_violation",
                field="signature_block",
                reason="no signature block",
                severity="critical",
            ),
        )

    state = env.state(session_id)
    assert state["steps_taken"] == 0


def test_task1_rejects_submit_before_all_fields_assessed():
    session_id, _ = env.reset(task_id=1, seed=42)

    with pytest.raises(ValueError, match="Cannot submit task 1 yet"):
        env.step(session_id=session_id, action=Action(action_type="submit"))

    state = env.state(session_id)
    assert state["steps_taken"] == 0
