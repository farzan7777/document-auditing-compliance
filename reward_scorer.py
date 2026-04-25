"""
reward_scorer.py
----------------
Monotonic reward → score transformation layer.

MONOTONIC GUARANTEE:
    For any two rewards A and B:
        If reward_A > reward_B  →  score_A >= score_B   (ALWAYS)

    This is enforced by:
    1. Clamping reward to [min_reward, max_reward]   → no out-of-range inversion
    2. Linear min-max normalization with epsilon guard → no division instability
    3. Power scaling with alpha ∈ [0.8, 1.2]          → monotone-preserving transform
       (x^alpha is strictly monotone increasing for x >= 0, alpha > 0)
"""

from __future__ import annotations


# ── Configuration ────────────────────────────────────────────────────────────

MIN_REWARD: float = 0.0        # Lowest possible reward in the system
MAX_REWARD: float = 100.0      # Highest possible reward in the system
EPSILON:    float = 1e-8       # Prevents division-by-zero when min == max
ALPHA:      float = 1.0        # Power-scaling factor; 1.0 = linear (no curve)
                               # Use < 1.0 to boost mid-range, > 1.0 for sharper top


# ── Core Function ─────────────────────────────────────────────────────────────

def reward_to_score(
    reward: float | None,
    *,
    min_reward: float = MIN_REWARD,
    max_reward: float = MAX_REWARD,
    epsilon: float = EPSILON,
    alpha: float = ALPHA,
) -> float:
    """
    Convert a raw reward value into a normalized score in [0.0, 1.0].

    Args:
        reward:      Raw reward value from the evaluation system.
                     Pass None or a very negative value for missing/invalid rewards.
        min_reward:  The minimum possible reward (lower bound of the scale).
        max_reward:  The maximum possible reward (upper bound of the scale).
        epsilon:     Small constant to stabilize division when range is near-zero.
        alpha:       Power exponent for soft scaling (must be > 0).
                     alpha=1.0  → identity (linear)
                     alpha<1.0  → boosts lower scores (concave)
                     alpha>1.0  → suppresses lower scores (convex)

    Returns:
        A float in [0.0, 1.0].
        Returns 0.0 for missing, None, or extremely low rewards.

    Monotonic guarantee:
        reward_to_score is strictly non-decreasing:
        reward_A >= reward_B  →  score_A >= score_B
    """

    # ── EDGE CASE: missing or invalid reward ─────────────────────────────────
    if reward is None:
        return 0.0

    # Coerce to float defensively
    try:
        reward = float(reward)
    except (TypeError, ValueError):
        return 0.0

    # ── STEP 1: Clamp reward to [min_reward, max_reward] ─────────────────────
    # Prevents out-of-range values from inverting or exceeding the scale.
    reward_clamped = max(min_reward, min(reward, max_reward))

    # ── STEP 2: Stable min-max normalization → score ∈ [0.0, 1.0] ────────────
    # epsilon prevents division-by-zero when min_reward == max_reward.
    # The division is always positive → direction is NEVER inverted.
    score = (reward_clamped - min_reward) / (max_reward - min_reward + epsilon)

    # Clamp to [0, 1] to absorb floating-point drift
    score = max(0.0, min(score, 1.0))

    # ── STEP 3: Soft power scaling (optional smoothing) ───────────────────────
    # x^alpha is strictly monotone increasing for x >= 0 and alpha > 0,
    # so monotonicity is fully preserved after this transform.
    if alpha != 1.0:
        score = score ** alpha

    # Final clamp — defensive guard against fp rounding at the boundary
    return max(0.0, min(score, 1.0))


# ── Batch Helper ──────────────────────────────────────────────────────────────

def batch_reward_to_score(
    rewards: list[float | None],
    **kwargs,
) -> list[float]:
    """
    Convert a list of raw rewards to scores.
    Preserves order; each position maps reward → score independently.
    """
    return [reward_to_score(r, **kwargs) for r in rewards]


# ── Validation ────────────────────────────────────────────────────────────────

def validate_monotonicity(rewards: list[float | None], **kwargs) -> bool:
    """
    Smoke-test: verify that the scored list is non-decreasing
    when rewards are sorted ascending.

    Returns True if monotonicity holds, raises AssertionError otherwise.
    """
    sorted_rewards = sorted((r for r in rewards if r is not None))
    scores = [reward_to_score(r, **kwargs) for r in sorted_rewards]

    for i in range(1, len(scores)):
        assert scores[i] >= scores[i - 1], (
            f"Monotonicity violation: "
            f"reward {sorted_rewards[i]} → score {scores[i]:.6f} "
            f"< reward {sorted_rewards[i-1]} → score {scores[i-1]:.6f}"
        )
    return True


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_cases = [
        # (label,          reward)
        ("missing",        None),
        ("zero",           0.0),
        ("low",            10.0),
        ("mid",            50.0),
        ("high",           90.0),
        ("max",            100.0),
        ("over-max",       150.0),   # should clamp to 1.0
        ("negative",       -10.0),   # should clamp to 0.0
        ("task_2 anomaly", 15.0),    # previously returned inflated score
    ]

    print(f"{'Label':<20} {'Reward':>10} {'Score':>10}")
    print("-" * 44)
    for label, reward in test_cases:
        score = reward_to_score(reward)
        print(f"{label:<20} {str(reward):>10} {score:>10.6f}")

    # Monotonicity check
    rewards = [r for _, r in test_cases if r is not None]
    passed = validate_monotonicity(rewards)
    print(f"\n[PASS] Monotonicity check: {'PASSED' if passed else 'FAILED'}")

    # Edge-case assertions
    assert reward_to_score(None)    == 0.0,  "None must return 0.0"
    assert reward_to_score(-999.0)  == 0.0,  "Extreme low must return 0.0"
    assert reward_to_score(100.0)   >= 0.999, "Max reward must return ~1.0"
    assert reward_to_score(0.0)     == 0.0,  "Zero reward must return 0.0"

    # Core bug regression: low reward must NOT produce high score
    score_low  = reward_to_score(10.0)
    score_high = reward_to_score(90.0)
    assert score_low < score_high, \
        f"BUG REGRESSION FAILED: score(10) {score_low} >= score(90) {score_high}"

    print("[PASS] All edge-case assertions passed.")
    print("[PASS] task_2 anomaly regression: FIXED.")
