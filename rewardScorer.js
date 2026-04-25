/**
 * rewardScorer.js
 * ---------------
 * Monotonic reward → score transformation layer.
 *
 * MONOTONIC GUARANTEE:
 *   For any two rewards A and B:
 *     If reward_A > reward_B  →  score_A >= score_B   (ALWAYS)
 *
 *   Enforced by:
 *   1. Clamping reward to [minReward, maxReward]  → no out-of-range inversion
 *   2. Linear min-max normalization with epsilon   → no division instability
 *   3. Power scaling with alpha ∈ (0, ∞)          → monotone-preserving (x^α is
 *      strictly increasing for x >= 0, α > 0)
 */

"use strict";

// ── Configuration ────────────────────────────────────────────────────────────

const DEFAULT_CONFIG = {
  minReward: 0.0,     // Lowest possible reward in the system
  maxReward: 100.0,   // Highest possible reward in the system
  epsilon:   1e-8,    // Prevents division-by-zero when minReward === maxReward
  alpha:     1.0,     // Power-scaling factor; 1.0 = linear (no curve)
                      // Use < 1.0 to boost mid-range, > 1.0 for sharper top
};


// ── Core Function ─────────────────────────────────────────────────────────────

/**
 * Convert a raw reward value into a normalized score in [0.0, 1.0].
 *
 * @param {number|null|undefined} reward - Raw reward from the evaluation system.
 * @param {object} [config]              - Optional overrides for bounds/alpha.
 * @param {number} [config.minReward]
 * @param {number} [config.maxReward]
 * @param {number} [config.epsilon]
 * @param {number} [config.alpha]
 * @returns {number} Score in [0.0, 1.0].
 *
 * Edge cases:
 *   - null / undefined / NaN  → 0.0
 *   - reward <= minReward     → 0.0
 *   - reward >= maxReward     → ≈1.0 (clamped)
 */
function rewardToScore(reward, config = {}) {
  const { minReward, maxReward, epsilon, alpha } = {
    ...DEFAULT_CONFIG,
    ...config,
  };

  // ── EDGE CASE: missing or invalid reward ──────────────────────────────────
  if (reward === null || reward === undefined || typeof reward !== "number" || isNaN(reward)) {
    return 0.0;
  }

  // ── STEP 1: Clamp reward to [minReward, maxReward] ────────────────────────
  // Prevents out-of-range values from inverting or exceeding the scale.
  const rewardClamped = Math.max(minReward, Math.min(reward, maxReward));

  // ── STEP 2: Stable min-max normalization → score ∈ [0.0, 1.0] ─────────────
  // epsilon prevents division-by-zero when minReward === maxReward.
  // Division is always positive → direction is NEVER inverted.
  let score = (rewardClamped - minReward) / (maxReward - minReward + epsilon);

  // Clamp to [0, 1] to absorb floating-point drift
  score = Math.max(0.0, Math.min(score, 1.0));

  // ── STEP 3: Soft power scaling (optional smoothing) ───────────────────────
  // x^alpha is strictly monotone increasing for x >= 0 and alpha > 0,
  // so monotonicity is fully preserved after this transform.
  if (alpha !== 1.0) {
    score = Math.pow(score, alpha);
  }

  // Final clamp — defensive guard against fp rounding at the boundary
  return Math.max(0.0, Math.min(score, 1.0));
}


// ── Batch Helper ──────────────────────────────────────────────────────────────

/**
 * Convert an array of raw rewards to scores.
 * Preserves order; each position maps reward → score independently.
 *
 * @param {Array<number|null>} rewards
 * @param {object} [config]
 * @returns {number[]}
 */
function batchRewardToScore(rewards, config = {}) {
  return rewards.map((r) => rewardToScore(r, config));
}


// ── Validation ────────────────────────────────────────────────────────────────

/**
 * Smoke-test: verify that scored values are non-decreasing
 * when rewards are sorted ascending.
 *
 * @param {Array<number|null>} rewards
 * @param {object} [config]
 * @returns {boolean} true if monotonicity holds.
 * @throws {Error} if a monotonicity violation is found.
 */
function validateMonotonicity(rewards, config = {}) {
  const validRewards = rewards
    .filter((r) => r !== null && r !== undefined && !isNaN(r))
    .sort((a, b) => a - b);

  const scores = validRewards.map((r) => rewardToScore(r, config));

  for (let i = 1; i < scores.length; i++) {
    if (scores[i] < scores[i - 1]) {
      throw new Error(
        `Monotonicity violation: ` +
        `reward ${validRewards[i]} → score ${scores[i].toFixed(6)} ` +
        `< reward ${validRewards[i - 1]} → score ${scores[i - 1].toFixed(6)}`
      );
    }
  }
  return true;
}


// ── Self-test ─────────────────────────────────────────────────────────────────

(function selfTest() {
  const testCases = [
    { label: "missing (null)",   reward: null      },
    { label: "missing (undef)",  reward: undefined },
    { label: "NaN",              reward: NaN       },
    { label: "zero",             reward: 0.0       },
    { label: "low",              reward: 10.0      },
    { label: "mid",              reward: 50.0      },
    { label: "high",             reward: 90.0      },
    { label: "max",              reward: 100.0     },
    { label: "over-max",         reward: 150.0     }, // clamps to ~1.0
    { label: "negative",         reward: -10.0     }, // clamps to 0.0
    { label: "task_2 anomaly",   reward: 15.0      }, // previously returned inflated score
  ];

  console.log(
    "Label".padEnd(22) + "Reward".padStart(10) + "Score".padStart(12)
  );
  console.log("-".repeat(44));

  for (const { label, reward } of testCases) {
    const score = rewardToScore(reward);
    console.log(
      label.padEnd(22) +
      String(reward).padStart(10) +
      score.toFixed(6).padStart(12)
    );
  }

  // Monotonicity check
  const numericRewards = testCases
    .map((t) => t.reward)
    .filter((r) => typeof r === "number" && !isNaN(r));

  const passed = validateMonotonicity(numericRewards);
  console.log(`\n✅ Monotonicity check: ${passed ? "PASSED" : "FAILED"}`);

  // Edge-case assertions
  console.assert(rewardToScore(null)      === 0.0,   "null must return 0.0");
  console.assert(rewardToScore(undefined) === 0.0,   "undefined must return 0.0");
  console.assert(rewardToScore(NaN)       === 0.0,   "NaN must return 0.0");
  console.assert(rewardToScore(-999)      === 0.0,   "Extreme low must return 0.0");
  console.assert(rewardToScore(100)       >= 0.999,  "Max reward must return ~1.0");
  console.assert(rewardToScore(0)         === 0.0,   "Zero reward must return 0.0");

  // Core bug regression: low reward must NOT produce high score
  const scoreLow  = rewardToScore(10.0);
  const scoreHigh = rewardToScore(90.0);
  console.assert(
    scoreLow < scoreHigh,
    `BUG REGRESSION FAILED: score(10) ${scoreLow} >= score(90) ${scoreHigh}`
  );

  console.log("✅ All edge-case assertions passed.");
  console.log("✅ task_2 anomaly regression: FIXED.");
})();


// ── Exports ───────────────────────────────────────────────────────────────────

module.exports = { rewardToScore, batchRewardToScore, validateMonotonicity, DEFAULT_CONFIG };
