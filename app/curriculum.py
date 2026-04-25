"""
curriculum.py — Theme #4 Self Improvement
==========================================
This is the TEACHER of your environment.
 
It watches how well agents perform across episodes.
It decides when to make documents harder or keep same level.
It never lets agents get too comfortable.
 
This is what makes your environment "self-improving."
"""
 
# ─── How Difficulty Works ─────────────────────────────────────────────────────
#
# Level 1 = Junior Clerk      (easiest documents)
# Level 2 = Analyst           (slightly harder)
# Level 3 = Senior Officer    (medium difficulty)
# Level 4 = Director          (hard)
# Level 5 = Regulatory Expert (hardest documents)
#
# Agent starts at Level 1 always.
# Agent moves UP   when rolling average > 0.85
# Agent moves DOWN when rolling average < 0.40
# Agent stays SAME when rolling average is between 0.40 and 0.85
# ─────────────────────────────────────────────────────────────────────────────
 
 
class Curriculum:
    """
    The teacher class.
    One instance of this runs for the entire environment lifetime.
    It remembers ALL episode scores and decides difficulty.
    """
 
    def __init__(self):
        # Start at Level 1 always (easiest)
        self.current_level = 1
 
        # Remember last 10 episode scores
        # Example: [0.85, 0.82, 0.87, 0.84, 0.86]
        self.recent_scores = []
 
        # How many scores to look back at
        # 10 means "average of last 10 episodes"
        self.window_size = 10
 
        # Agent must score above this to move UP
        self.upgrade_threshold = 0.40
 
        # Agent must score below this to move DOWN
        self.downgrade_threshold = 0.20
 
        # Track total episodes seen
        self.total_episodes = 0
 
        # Track how many episodes at current level
        self.episodes_at_current_level = 0
 
        # Track history of level changes for judges to see
        self.level_history = []
 
    def record_score(self, score: float):
        """
        Call this after EVERY episode ends.
        Give it the final score (0.0 to 1.0).
        It will automatically decide if difficulty should change.
 
        Example:
            curriculum.record_score(0.87)
        """
        # Make sure score is between 0 and 1
        score = max(0.0, min(1.0, float(score)))
 
        # Add this score to our memory
        self.recent_scores.append(score)
 
        # Only remember last 10 scores (forget older ones)
        # This is the "rolling window"
        if len(self.recent_scores) > self.window_size:
            self.recent_scores.pop(0)  # remove oldest score
 
        # Count this episode
        self.total_episodes += 1
        self.episodes_at_current_level += 1
 
        # Now decide if difficulty should change
        self._update_difficulty()
 
    def _update_difficulty(self):
        """
        Internal method — called automatically after each score.
        Looks at rolling average and decides level.
        """
        # Need at least 5 scores before making decisions
        # Don't want to change level after just 1-2 episodes
        if len(self.recent_scores) < 5:
            return
 
        # Calculate rolling average
        average = sum(self.recent_scores) / len(self.recent_scores)
 
        old_level = int(self.current_level)
 
        if average > self.upgrade_threshold:
            new_level = min(old_level + 1, 5)
        elif average < self.downgrade_threshold:
            new_level = max(old_level - 1, 1)
        else:
            new_level = old_level
            
        if new_level != old_level:
            self.current_level = new_level
            self.episodes_at_current_level = 0
            self.recent_scores = []
            
            direction = "UP" if new_level > old_level else "DOWN"
            threshold = self.upgrade_threshold if direction == "UP" else self.downgrade_threshold
            word = "exceeded" if direction == "UP" else "below"
            
            self.level_history.append({
                "episode": self.total_episodes,
                "from_level": old_level,
                "to_level": self.current_level,
                "reason": f"Rolling average {round(average, 3)} {word} {threshold}",
                "direction": direction
            })
 
        # Otherwise stay at same level — agent still learning
 
    def get_difficulty(self) -> int:
        """
        Call this when starting a new episode.
        Returns current difficulty level (1 to 5).
 
        Example:
            level = curriculum.get_difficulty()
            # level = 3
            document = generator.generate_contract(seed=42, difficulty=level)
        """
        return self.current_level
 
    def get_stats(self) -> dict:
        """
        Returns all curriculum stats.
        Used by the /curriculum/stats API endpoint.
        Judges call this to see how the system is working.
 
        Returns a dictionary with:
        - current_level: what level we are at now
        - rolling_average: average of recent scores
        - total_episodes: how many episodes have run
        - trend: is agent improving or declining?
        - level_history: all level changes so far
        """
        # Calculate current rolling average
        if self.recent_scores:
            average = round(sum(self.recent_scores) / len(self.recent_scores), 4)
        else:
            average = 0.0
 
        # Determine trend
        # Compare first half of scores to second half
        if len(self.recent_scores) >= 4:
            half = len(self.recent_scores) // 2
            first_half = sum(self.recent_scores[:half]) / half
            second_half = sum(self.recent_scores[half:]) / (len(self.recent_scores) - half)
            if second_half > first_half + 0.05:
                trend = "improving"
            elif second_half < first_half - 0.05:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
 
        return {
            "current_level": self.current_level,
            "level_name": self._get_level_name(),
            "rolling_average": average,
            "recent_scores": self.recent_scores,
            "total_episodes": self.total_episodes,
            "episodes_at_current_level": self.episodes_at_current_level,
            "trend": trend,
            "upgrade_threshold": self.upgrade_threshold,
            "downgrade_threshold": self.downgrade_threshold,
            "level_history": self.level_history,
            "next_level_at": f"Score above {self.upgrade_threshold} average",
        }
 
    def _get_level_name(self) -> str:
        """Returns human readable name for current level."""
        names = {
            1: "Junior Compliance Clerk",
            2: "Compliance Analyst",
            3: "Senior Compliance Officer",
            4: "Compliance Director",
            5: "Regulatory Authority Auditor",
        }
        return names.get(self.current_level, "Unknown")
 
    def reset_for_demo(self):
        """
        Reset curriculum back to Level 1.
        Useful for demos and testing.
        """
        self.__init__()
 
 
# ─── Global Instance ──────────────────────────────────────────────────────────
# This single instance runs for the entire server lifetime.
# All episodes share the same curriculum.
# This is how it remembers scores across episodes.
 
curriculum = Curriculum()
 