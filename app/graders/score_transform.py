"""
score_transform.py
------------------
Centralised reward → final_score transformation.

MONOTONIC GUARANTEE
-------------------
reward_to_score() is strictly non-decreasing:
    For any reward_A, reward_B:
        reward_A >= reward_B  →  score_A >= score_B   (ALWAYS)

Achieved by:
  1. Clamping reward to [0.0, 1.0]  — no out-of-range inversion possible
  2. Identity mapping  score = reward  — linear, no curve that could invert

SCALE CONTRACT
--------------
  reward 0.0  → score 0.0    (no artificial floor)
  reward 0.5  → score 0.5    (proportional mid-range, no inflation)
  reward 1.0  → score 1.0    (no saturation at 0.999)

WHY THE OLD CODE WAS WRONG
--------------------------
  Old:  max(0.001, min(0.999, reward))
    ❌  floor 0.001  — terrible scores were inflated to non-zero
    ❌  ceiling 0.999 — all high rewards clumped near 0.999 (saturation)
    ❌  grader3 added severity_bonus on top, pushing 0.4–0.65 rewards
        into the 0.75–0.999 range — the reported "task_2 anomaly"

  New:  max(0.0, min(1.0, reward))
    ✔  true zero for zero/missing performance
    ✔  true one for perfect performance
    ✔  linear, monotone, no saturation
"""

from __future__ import annotations


def reward_to_score(reward: float | None) -> float:
    """
    Convert a raw intermediate reward into a final score in [0.0, 1.0].

    This is the ONLY place that maps reward → score.
    All graders must call this function instead of writing inline clamping.

    Args:
        reward: Pre-computed reward value from grader logic.
                Expected range [0.0, 1.0], but safe beyond that range.

    Returns:
        float in [0.0, 1.0], linearly proportional to reward.

    Properties:
        - Monotonic:   reward_A >= reward_B  → score_A >= score_B
        - Normalised:  output always in [0.0, 1.0]
        - Stable:      same reward always produces same score
        - No inflation: 0.5 reward → 0.5 score (not 0.8)
    """
    # Edge case: missing / unparseable reward → lowest possible score
    if reward is None:
        return 0.0
    try:
        reward = float(reward)
    except (TypeError, ValueError):
        return 0.0

    # Linear clamp — the only transformation needed.
    # x^1 is trivially monotone; clamp preserves ordering at the boundaries.
    return max(0.0, min(1.0, reward))
