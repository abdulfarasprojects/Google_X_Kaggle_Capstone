"""
Streak analysis tools for nudge logic.

This module provides tools for analyzing user logging streaks and determining
when streak protection nudges should be triggered.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from tools.base import BaseTool, ToolResult
from database.models import get_db, UserProfile, MealLog, WorkoutLog, WellnessLog
from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class StreakAnalysis:
    """Analysis of user's logging streak."""
    current_streak: int
    longest_streak: int
    streak_status: str  # 'active', 'broken', 'at_risk'
    days_since_last_log: int
    risk_level: str  # 'low', 'medium', 'high', 'critical'
    protection_needed: bool


class StreakAnalyzerTool(BaseTool):
    """
    Tool for analyzing user logging streaks and streak protection needs.

    Determines if a user is at risk of breaking their logging streak
    and when protection nudges should be sent.
    """

    def __init__(self):
        super().__init__(
            name="analyze_user_streak",
            description="Analyze user's logging streak and determine protection needs",
            parameters={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to analyze streak for"
                    },
                    "current_time": {
                        "type": "string",
                        "description": "Current time in ISO format (optional, defaults to now)"
                    }
                },
                "required": ["user_id"]
            }
        )

    async def execute(
        self,
        user_id: str,
        current_time: Optional[str] = None,
        tool_context: Optional[Any] = None
    ) -> ToolResult:
        """
        Analyze user's logging streak and protection needs.

        Args:
            user_id: User ID to analyze
            current_time: Current time (optional, defaults to now)
            tool_context: ADK tool context

        Returns:
            ToolResult with streak analysis
        """
        try:
            # Parse current time
            now = datetime.fromisoformat(current_time) if current_time else datetime.utcnow()

            db = get_db()
            try:
                # Get user profile
                user = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
                if not user:
                    return ToolResult(
                        success=False,
                        error=f"User not found: {user_id}"
                    )

                # Analyze streak
                streak_analysis = self._analyze_streak(db, user, now)

                return ToolResult(
                    success=True,
                    data={
                        "user_id": user_id,
                        "current_streak": streak_analysis.current_streak,
                        "longest_streak": streak_analysis.longest_streak,
                        "streak_status": streak_analysis.streak_status,
                        "days_since_last_log": streak_analysis.days_since_last_log,
                        "risk_level": streak_analysis.risk_level,
                        "protection_needed": streak_analysis.protection_needed,
                        "analysis_time": now.isoformat()
                    }
                )

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Streak analysis failed: {e}")
            return ToolResult(
                success=False,
                error=f"Streak analysis failed: {str(e)}"
            )

    def _analyze_streak(self, db, user: UserProfile, current_time: datetime) -> StreakAnalysis:
        """
        Perform comprehensive streak analysis.

        Args:
            db: Database session
            user: User profile
            current_time: Current time

        Returns:
            StreakAnalysis with detailed metrics
        """
        # Calculate current streak
        current_streak = self._calculate_current_streak(db, user, current_time)

        # Calculate longest streak (ever)
        longest_streak = self._calculate_longest_streak(db, user)

        # Days since last log
        days_since_last = self._days_since_last_log(db, user, current_time)

        # Determine streak status
        if current_streak == 0:
            if days_since_last <= 1:
                streak_status = "starting"
            else:
                streak_status = "broken"
        elif days_since_last == 0:
            streak_status = "active"
        elif days_since_last == 1:
            streak_status = "at_risk"
        else:
            streak_status = "broken"

        # Determine risk level and protection need
        risk_level, protection_needed = self._assess_risk(current_streak, days_since_last, current_time)

        return StreakAnalysis(
            current_streak=current_streak,
            longest_streak=longest_streak,
            streak_status=streak_status,
            days_since_last_log=days_since_last,
            risk_level=risk_level,
            protection_needed=protection_needed
        )

    def _calculate_current_streak(self, db, user: UserProfile, current_time: datetime) -> int:
        """
        Calculate current active streak.

        Args:
            db: Database session
            user: User profile
            current_time: Current time

        Returns:
            Current streak length in days
        """
        streak = 0
        check_date = current_time.date()

        # Check up to 60 days back for active streaks
        for i in range(60):
            day_logs = self._get_logs_for_date(db, user, check_date)

            if day_logs > 0:
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break

        return streak

    def _calculate_longest_streak(self, db, user: UserProfile) -> int:
        """
        Calculate the longest streak ever achieved.

        Args:
            db: Database session
            user: User profile

        Returns:
            Longest streak length in days
        """
        # Get all log dates in chronological order
        meal_dates = db.query(MealLog.log_date).filter(MealLog.user_id == user.user_id).all()
        workout_dates = db.query(WorkoutLog.log_date).filter(WorkoutLog.user_id == user.user_id).all()
        wellness_dates = db.query(WellnessLog.log_date).filter(WellnessLog.user_id == user.user_id).all()

        # Combine and deduplicate dates
        all_dates = set()
        for date_tuple in meal_dates + workout_dates + wellness_dates:
            all_dates.add(date_tuple[0])

        sorted_dates = sorted(all_dates)

        if not sorted_dates:
            return 0

        # Find longest consecutive streak
        longest_streak = 1
        current_streak = 1

        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i-1]).days == 1:
                current_streak += 1
                longest_streak = max(longest_streak, current_streak)
            else:
                current_streak = 1

        return longest_streak

    def _days_since_last_log(self, db, user: UserProfile, current_time: datetime) -> int:
        """
        Calculate days since user's last log entry.

        Args:
            db: Database session
            user: User profile
            current_time: Current time

        Returns:
            Days since last activity
        """
        # Find the most recent log date
        latest_meal = db.query(MealLog.log_date).filter(MealLog.user_id == user.user_id).order_by(MealLog.log_date.desc()).first()
        latest_workout = db.query(WorkoutLog.log_date).filter(WorkoutLog.user_id == user.user_id).order_by(WorkoutLog.log_date.desc()).first()
        latest_wellness = db.query(WellnessLog.log_date).filter(WellnessLog.user_id == user.user_id).order_by(WellnessLog.log_date.desc()).first()

        latest_dates = []
        if latest_meal:
            latest_dates.append(latest_meal[0])
        if latest_workout:
            latest_dates.append(latest_workout[0])
        if latest_wellness:
            latest_dates.append(latest_wellness[0])

        if not latest_dates:
            return 999  # No logs ever

        latest_date = max(latest_dates)
        days_diff = (current_time.date() - latest_date).days

        return max(0, days_diff)  # Don't return negative

    def _get_logs_for_date(self, db, user: UserProfile, date) -> int:
        """
        Count total logs for a specific date.

        Args:
            db: Database session
            user: User profile
            date: Date to check

        Returns:
            Number of log entries for the date
        """
        meal_count = db.query(MealLog).filter(
            MealLog.user_id == user.user_id,
            MealLog.log_date == date
        ).count()

        workout_count = db.query(WorkoutLog).filter(
            WorkoutLog.user_id == user.user_id,
            WorkoutLog.log_date == date
        ).count()

        wellness_count = db.query(WellnessLog).filter(
            WellnessLog.user_id == user.user_id,
            WellnessLog.log_date == date
        ).count()

        return meal_count + workout_count + wellness_count

    def _assess_risk(self, current_streak: int, days_since_last: int, current_time: datetime) -> tuple[str, bool]:
        """
        Assess streak risk level and protection need.

        Args:
            current_streak: Current streak length
            days_since_last: Days since last log
            current_time: Current time

        Returns:
            Tuple of (risk_level, protection_needed)
        """
        # No streak to protect
        if current_streak == 0:
            return "low", False

        # Active streak today
        if days_since_last == 0:
            return "low", False

        # Streak broken (more than 1 day gap)
        if days_since_last > 1:
            return "low", False  # Too late for protection

        # At risk (1 day gap) - assess based on time and streak length
        hour = current_time.hour

        # Critical: Late at night (11 PM - 12 AM) with established streak
        if hour >= 23 and current_streak >= 3:
            return "critical", True

        # High: Evening hours with good streak
        if hour >= 20 and current_streak >= 5:
            return "high", True

        # Medium: Afternoon/evening with any streak
        if hour >= 18 and current_streak >= 2:
            return "medium", True

        # Low: Earlier in day or short streak
        return "low", False


# Create singleton instance
streak_analyzer = StreakAnalyzerTool()


# Convenience function for direct use
async def analyze_user_streak(
    user_id: str,
    current_time: Optional[str] = None,
    tool_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Analyze a user's logging streak and protection needs.

    Args:
        user_id: User ID to analyze
        current_time: Current time in ISO format (optional)
        tool_context: Optional ADK tool context

    Returns:
        Dict with status, data, error
    """
    result = await streak_analyzer.execute(
        user_id=user_id,
        current_time=current_time,
        tool_context=tool_context
    )

    return {
        "status": "success" if result.success else "error",
        "data": result.data,
        "error": result.error
    }


__all__ = ['StreakAnalyzerTool', 'streak_analyzer', 'analyze_user_streak']