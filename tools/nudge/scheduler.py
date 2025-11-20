"""
Nudge scheduling tools for autonomous reminders.

This module provides tools for determining when and what type of nudges
should be sent to users based on their activity patterns and time of day.
"""

import logging
from datetime import datetime, time, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from tools.base import BaseTool, ToolResult
from database.models import get_db, UserProfile, MealLog, WorkoutLog, WellnessLog, NudgeEvent
from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class NudgeSchedule:
    """Schedule information for a nudge."""
    nudge_type: str
    scheduled_time: datetime
    reason: str
    priority: int  # 1-10, higher = more important


class NudgeSchedulerTool(BaseTool):
    """
    Tool for determining when and what nudges to schedule for users.

    Analyzes user activity patterns and schedules appropriate nudges
    at optimal times for maintaining consistent logging habits.
    """

    def __init__(self):
        super().__init__(
            name="schedule_user_nudges",
            description="Analyze user activity and schedule appropriate autonomous nudges",
            parameters={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to schedule nudges for"
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
        Determine nudge schedule for a user based on their activity patterns.

        Args:
            user_id: User ID to analyze
            current_time: Current time (optional, defaults to now)
            tool_context: ADK tool context

        Returns:
            ToolResult with nudge schedule recommendations
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

                # Analyze user activity patterns
                activity_analysis = await self._analyze_user_activity(db, user, now)

                # Determine nudge schedule
                nudge_schedule = self._calculate_nudge_schedule(user, activity_analysis, now)

                # Filter to relevant nudges (next 24 hours)
                relevant_nudges = [
                    nudge for nudge in nudge_schedule
                    if nudge.scheduled_time <= now + timedelta(hours=24)
                ]

                return ToolResult(
                    success=True,
                    data={
                        "user_id": user_id,
                        "current_time": now.isoformat(),
                        "nudges_to_schedule": [
                            {
                                "nudge_type": nudge.nudge_type,
                                "scheduled_time": nudge.scheduled_time.isoformat(),
                                "reason": nudge.reason,
                                "priority": nudge.priority
                            }
                            for nudge in relevant_nudges
                        ],
                        "activity_summary": activity_analysis
                    }
                )

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Nudge scheduling failed: {e}")
            return ToolResult(
                success=False,
                error=f"Nudge scheduling failed: {str(e)}"
            )

    async def _analyze_user_activity(self, db, user: UserProfile, current_time: datetime) -> Dict[str, Any]:
        """
        Analyze user's recent activity patterns.

        Args:
            db: Database session
            user: User profile
            current_time: Current time

        Returns:
            Dict with activity analysis
        """
        # Get activity from last 7 days
        week_ago = current_time - timedelta(days=7)
        yesterday = current_time - timedelta(days=1)

        # Count recent logs
        meal_count = db.query(MealLog).filter(
            MealLog.user_id == user.user_id,
            MealLog.log_date >= week_ago.date()
        ).count()

        workout_count = db.query(WorkoutLog).filter(
            WorkoutLog.user_id == user.user_id,
            WorkoutLog.log_date >= week_ago.date()
        ).count()

        wellness_count = db.query(WellnessLog).filter(
            WellnessLog.user_id == user.user_id,
            WellnessLog.log_date >= week_ago.date()
        ).count()

        # Check yesterday's activity
        yesterday_meals = db.query(MealLog).filter(
            MealLog.user_id == user.user_id,
            MealLog.log_date == yesterday.date()
        ).count()

        yesterday_workouts = db.query(WorkoutLog).filter(
            WorkoutLog.user_id == user.user_id,
            WorkoutLog.log_date == yesterday.date()
        ).count()

        yesterday_wellness = db.query(WellnessLog).filter(
            WellnessLog.user_id == user.user_id,
            WellnessLog.log_date == yesterday.date()
        ).count()

        # Calculate streak (consecutive days with at least one log)
        streak_days = self._calculate_current_streak(db, user, current_time)

        # Calculate logging consistency (days with logs / total days)
        total_days = 7
        active_days = 0
        for i in range(7):
            check_date = (current_time - timedelta(days=i)).date()
            day_logs = db.query(MealLog).filter(
                MealLog.user_id == user.user_id,
                MealLog.log_date == check_date
            ).count()
            day_logs += db.query(WorkoutLog).filter(
                WorkoutLog.user_id == user.user_id,
                WorkoutLog.log_date == check_date
            ).count()
            day_logs += db.query(WellnessLog).filter(
                WellnessLog.user_id == user.user_id,
                WellnessLog.log_date == check_date
            ).count()
            if day_logs > 0:
                active_days += 1

        consistency = active_days / total_days if total_days > 0 else 0

        return {
            "week_meal_count": meal_count,
            "week_workout_count": workout_count,
            "week_wellness_count": wellness_count,
            "yesterday_had_meals": yesterday_meals > 0,
            "yesterday_had_workouts": yesterday_workouts > 0,
            "yesterday_had_wellness": yesterday_wellness > 0,
            "current_streak_days": streak_days,
            "consistency_ratio": consistency,
            "total_active_days": active_days
        }

    def _calculate_current_streak(self, db, user: UserProfile, current_time: datetime) -> int:
        """
        Calculate current logging streak in days.

        Args:
            db: Database session
            user: User profile
            current_time: Current time

        Returns:
            Number of consecutive days with activity
        """
        streak = 0
        check_date = current_time.date()

        # Check up to 30 days back
        for i in range(30):
            day_logs = db.query(MealLog).filter(
                MealLog.user_id == user.user_id,
                MealLog.log_date == check_date
            ).count()
            day_logs += db.query(WorkoutLog).filter(
                WorkoutLog.user_id == user.user_id,
                WorkoutLog.log_date == check_date
            ).count()
            day_logs += db.query(WellnessLog).filter(
                WellnessLog.user_id == user.user_id,
                WellnessLog.log_date == check_date
            ).count()

            if day_logs > 0:
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break

        return streak

    def _calculate_nudge_schedule(
        self,
        user: UserProfile,
        activity: Dict[str, Any],
        current_time: datetime
    ) -> List[NudgeSchedule]:
        """
        Calculate optimal nudge schedule based on user activity.

        Args:
            user: User profile
            activity: Activity analysis
            current_time: Current time

        Returns:
            List of nudge schedules
        """
        nudges = []

        # Convert current time to user's timezone
        user_tz = user.timezone  # Assume timezone string
        # For simplicity, assume UTC for now - would need pytz for proper timezone handling

        # Morning nudge (7:00) - if no activity yesterday
        if not activity["yesterday_had_meals"] and not activity["yesterday_had_workouts"]:
            morning_time = current_time.replace(hour=7, minute=0, second=0, microsecond=0)
            if morning_time > current_time:
                nudges.append(NudgeSchedule(
                    nudge_type="morning",
                    scheduled_time=morning_time,
                    reason="No activity logged yesterday - encourage morning start",
                    priority=8
                ))

        # Midday positive reinforcement (12:00) - if good activity today
        midday_time = current_time.replace(hour=12, minute=0, second=0, microsecond=0)
        if midday_time > current_time:
            today_logs = activity.get("today_logs", 0)  # Would need to calculate
            if today_logs > 0:
                nudges.append(NudgeSchedule(
                    nudge_type="midday",
                    scheduled_time=midday_time,
                    reason="Positive reinforcement for today's activity",
                    priority=6
                ))

        # Evening check-in (19:00) - general reminder
        evening_time = current_time.replace(hour=19, minute=0, second=0, microsecond=0)
        if evening_time > current_time:
            nudges.append(NudgeSchedule(
                nudge_type="evening",
                scheduled_time=evening_time,
                reason="Evening check-in reminder",
                priority=7
            ))

        # Streak protection (23:55) - if streak at risk
        if activity["current_streak_days"] >= 2:  # Only for established streaks
            late_time = current_time.replace(hour=23, minute=55, second=0, microsecond=0)
            if late_time > current_time:
                today_logs = activity.get("today_logs", 0)
                if today_logs == 0:  # No activity today
                    nudges.append(NudgeSchedule(
                        nudge_type="streak_protection",
                        scheduled_time=late_time,
                        reason=f"Protect {activity['current_streak_days']}-day streak",
                        priority=9
                    ))

        # Weekly summary (Sunday 18:00)
        if current_time.weekday() == 6:  # Sunday
            weekly_time = current_time.replace(hour=18, minute=0, second=0, microsecond=0)
            if weekly_time > current_time:
                nudges.append(NudgeSchedule(
                    nudge_type="weekly",
                    scheduled_time=weekly_time,
                    reason="Weekly progress summary",
                    priority=5
                ))

        return nudges


# Create singleton instance
nudge_scheduler = NudgeSchedulerTool()


# Convenience function for direct use
async def schedule_user_nudges(
    user_id: str,
    current_time: Optional[str] = None,
    tool_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Schedule nudges for a user based on their activity patterns.

    Args:
        user_id: User ID to schedule for
        current_time: Current time in ISO format (optional)
        tool_context: Optional ADK tool context

    Returns:
        Dict with status, data, error
    """
    result = await nudge_scheduler.execute(
        user_id=user_id,
        current_time=current_time,
        tool_context=tool_context
    )

    return {
        "status": "success" if result.success else "error",
        "data": result.data,
        "error": result.error
    }


__all__ = ['NudgeSchedulerTool', 'nudge_scheduler', 'schedule_user_nudges']