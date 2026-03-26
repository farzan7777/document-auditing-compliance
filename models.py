from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Any, Dict
from enum import Enum


# ─── Action Types ────────────────────────────────────────────────────────────

class ActionType(str, Enum):
    FLAG_VIOLATION = "flag_violation"
    MARK_FIELD_PRESENT = "mark_field_present"
    MARK_FIELD_MISSING = "mark_field_missing"
    SUBMIT = "submit"


class Severity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class Action(BaseModel):
    action_type: ActionType = Field(..., description="Type of action the agent takes")
    field: Optional[str] = Field(None, description="Field or clause name being acted on")
    reason: Optional[str] = Field(None, description="Agent's reason for this action")
    severity: Optional[Severity] = Field(None, description="Severity of the violation (for flag_violation)")
    section: Optional[str] = Field(None, description="Document section where issue was found")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "action_type": "flag_violation",
                    "field": "signature_block",
                    "reason": "No signature block found in document",
                    "severity": "critical",
                    "section": "footer"
                }
            ]
        }
    }


# ─── Observation ─────────────────────────────────────────────────────────────

class Observation(BaseModel):
    task_id: int = Field(..., description="Current task ID (1, 2, or 3)")
    task_name: str = Field(..., description="Human-readable task name")
    task_description: str = Field(..., description="What the agent must do")
    document_text: str = Field(..., description="The document to audit")
    current_flags: List[str] = Field(default_factory=list, description="Violations flagged so far")
    current_confirmations: List[str] = Field(default_factory=list, description="Fields confirmed present")
    steps_taken: int = Field(0, description="Number of steps taken so far")
    max_steps: int = Field(..., description="Maximum steps allowed")
    cumulative_reward: float = Field(0.0, description="Reward accumulated so far")
    available_actions: List[str] = Field(..., description="Actions available to the agent")
    instructions: str = Field(..., description="Specific instructions for this task")


# ─── Reward ──────────────────────────────────────────────────────────────────

class Reward(BaseModel):
    value: float = Field(..., description="Reward for this step (-1.0 to 1.0)")
    reason: str = Field(..., description="Why this reward was given")
    cumulative: float = Field(..., description="Total reward so far")


# ─── Step Response ───────────────────────────────────────────────────────────

class StepResponse(BaseModel):
    observation: Observation
    reward: Reward
    done: bool = Field(..., description="Whether the episode is complete")
    info: Dict[str, Any] = Field(default_factory=dict, description="Extra debug info")


# ─── Grader Response ─────────────────────────────────────────────────────────

class GraderResponse(BaseModel):
    task_id: int
    task_name: str
    score: float = Field(..., ge=0.0, le=1.0, description="Final score 0.0–1.0")
    breakdown: Dict[str, Any] = Field(..., description="Score breakdown by category")
    feedback: str = Field(..., description="Human-readable feedback")
    total_steps: int
    violations_found: int
    violations_missed: int
    false_positives: int


# ─── Task Info ───────────────────────────────────────────────────────────────

class TaskInfo(BaseModel):
    id: int
    name: str
    difficulty: Literal["easy", "medium", "hard"]
    description: str
    max_steps: int
    action_schema: Dict[str, Any]


# ─── Baseline Response ───────────────────────────────────────────────────────

class BaselineResponse(BaseModel):
    scores: Dict[str, float]
    details: Dict[str, Any]
    average_score: float
