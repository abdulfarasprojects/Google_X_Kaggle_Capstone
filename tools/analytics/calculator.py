"""
Progress calculation tools for analytics.

This module provides tools for calculating progress metrics, calorie budgets,
and performance indicators for weight loss tracking.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from tools.base import BaseTool, ToolResult
from database.models import get_db, UserProfile, MealLog, WorkoutLog, WellnessLog, ProgressSummary
from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class ProgressMetrics:
    """Progress metrics for a time period."""
    calories_logged: int
    calories_budget: int
    calories_remaining: int
    workouts_completed: int
    sleep_avg_hours: float
    water_avg_glasses: float
    steps_avg_count: int
    streak_days: int
    weight_change_kg: Optional[float]


class ProgressCalculatorTool(BaseTool):
    """
    Tool for calculating progress metrics and analytics.

    Analyzes user data to provide comprehensive progress summaries
    and performance indicators for weight loss tracking.
    """

    def __init__(self):
        super().__init__(
            name="calculate_progress_metrics",
            description="Calculate comprehensive progress metrics for a user over a specified time period",
            parameters={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to calculate progress for"
                    },
                    "period_type": {
                        "type": "string",
                        "enum": ["daily", "weekly", "monthly"],
                        "description": "Time period for calculation"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date for the period (ISO format, optional, defaults to today)"
                    }
                },
                "required": ["user_id", "period_type"]
            }
        )

    async def execute(
        self,
        user_id: str,
        period_type: str,
        end_date: Optional[str] = None,
        tool_context: Optional[Any] = None
    ) -> ToolResult:
        """
        Calculate progress metrics for a user.

        Args:
            user_id: User ID to analyze
            period_type: 'daily', 'weekly', or 'monthly'
            end_date: End date for period (optional, defaults to today)
            tool_context: ADK tool context

        Returns:
            ToolResult with progress metrics
        """
        try:
            # Parse end date
            if end_date:
                end = datetime.fromisoformat(end_date).date()
            else:
                end = date.today()

            # Calculate period start date
            if period_type == "daily":
                start = end
            elif period_type == "weekly":
                start = end - timedelta(days=6)  # 7 days total
            elif period_type == "monthly":
                # Start of month to end of month
                start = end.replace(day=1)
            else:
                return ToolResult(
                    success=False,
                    error=f"Invalid period_type: {period_type}"
                )

            db = get_db()
            try:
                # Get user profile
                user = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
                if not user:
                    return ToolResult(
                        success=False,
                        error=f"User not found: {user_id}"
                    )

                # Calculate metrics
                metrics = await self._calculate_metrics(db, user, start, end)

                return ToolResult(
                    success=True,
                    data={
                        "user_id": user_id,
                        "period_type": period_type,
                        "period_start": start.isoformat(),
                        "period_end": end.isoformat(),
                        "metrics": {
                            "calories_logged": metrics.calories_logged,
                            "calories_budget": metrics.calories_budget,
                            "calories_remaining": metrics.calories_remaining,
                            "workouts_completed": metrics.workouts_completed,
                            "sleep_avg_hours": round(metrics.sleep_avg_hours, 1),
                            "water_avg_glasses": round(metrics.water_avg_glasses, 1),
                            "steps_avg_count": metrics.steps_avg_count,
                            "streak_days": metrics.streak_days,
                            "weight_change_kg": metrics.weight_change_kg
                        }
                    }
                )

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Progress calculation failed: {e}")
            return ToolResult(
                success=False,
                error=f"Progress calculation failed: {str(e)}"
            )

    async def _calculate_metrics(
        self,
        db,
        user: UserProfile,
        start_date: date,
        end_date: date
    ) -> ProgressMetrics:
        """
        Calculate all progress metrics for the period.

        Args:
            db: Database session
            user: User profile
            start_date: Period start date
            end_date: Period end date

        Returns:
            ProgressMetrics object
        """
        # Calculate calories logged
        calories_logged = self._calculate_calories_logged(db, user, start_date, end_date)

        # Calculate calorie budget for the period
        days_in_period = (end_date - start_date).days + 1
        calories_budget = user.daily_calorie_goal * days_in_period

        # Calculate remaining calories
        calories_remaining = max(0, calories_budget - calories_logged)

        # Count workouts completed
        workouts_completed = db.query(WorkoutLog).filter(
            WorkoutLog.user_id == user.user_id,
            WorkoutLog.log_date >= start_date,
            WorkoutLog.log_date <= end_date
        ).count()

        # Calculate sleep average
        sleep_logs = db.query(WellnessLog.sleep_hours).filter(
            WellnessLog.user_id == user.user_id,
            WellnessLog.log_date >= start_date,
            WellnessLog.log_date <= end_date,
            WellnessLog.sleep_hours > 0
        ).all()

        sleep_avg_hours = sum(log[0] for log in sleep_logs) / len(sleep_logs) if sleep_logs else 0

        # Calculate water average
        water_logs = db.query(WellnessLog.water_glasses).filter(
            WellnessLog.user_id == user.user_id,
            WellnessLog.log_date >= start_date,
            WellnessLog.log_date <= end_date,
            WellnessLog.water_glasses > 0
        ).all()

        water_avg_glasses = sum(log[0] for log in water_logs) / len(water_logs) if water_logs else 0

        # Calculate steps average
        steps_logs = db.query(WellnessLog.steps_count).filter(
            WellnessLog.user_id == user.user_id,
            WellnessLog.log_date >= start_date,
            WellnessLog.log_date <= end_date,
            WellnessLog.steps_count > 0
        ).all()

        steps_avg_count = int(sum(log[0] for log in steps_logs) / len(steps_logs)) if steps_logs else 0

        # Calculate current streak
        streak_days = self._calculate_streak(db, user, end_date)

        # Calculate weight change (simplified - would need weight log model)
        weight_change_kg = None  # Placeholder for future weight tracking

        return ProgressMetrics(
            calories_logged=calories_logged,
            calories_budget=calories_budget,
            calories_remaining=calories_remaining,
            workouts_completed=workouts_completed,
            sleep_avg_hours=sleep_avg_hours,
            water_avg_glasses=water_avg_glasses,
            steps_avg_count=steps_avg_count,
            streak_days=streak_days,
            weight_change_kg=weight_change_kg
        )

    def _calculate_calories_logged(self, db, user: UserProfile, start_date: date, end_date: date) -> int:
        """
        Calculate total calories logged in the period.

        Args:
            db: Database session
            user: User profile
            start_date: Period start
            end_date: Period end

        Returns:
            Total calories logged
        """
        result = db.query(MealLog.total_calories).filter(
            MealLog.user_id == user.user_id,
            MealLog.log_date >= start_date,
            MealLog.log_date <= end_date
        ).all()

        return sum(calories[0] for calories in result)

    def _calculate_streak(self, db, user: UserProfile, current_date: date) -> int:
        """
        Calculate current logging streak.

        Args:
            db: Database session
            user: User profile
            current_date: Current date

        Returns:
            Streak length in days
        """
        streak = 0
        check_date = current_date

        for i in range(60):  # Check up to 60 days back
            # Count logs for this date
            meal_count = db.query(MealLog).filter(
                MealLog.user_id == user.user_id,
                MealLog.log_date == check_date
            ).count()

            workout_count = db.query(WorkoutLog).filter(
                WorkoutLog.user_id == user.user_id,
                WorkoutLog.log_date == check_date
            ).count()

            wellness_count = db.query(WellnessLog).filter(
                WellnessLog.user_id == user.user_id,
                WellnessLog.log_date == check_date
            ).count()

            total_logs = meal_count + workout_count + wellness_count

            if total_logs > 0:
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break

        return streak


# Create singleton instance
progress_calculator = ProgressCalculatorTool()


# Convenience function for direct use
async def calculate_progress_metrics(
    user_id: str,
    period_type: str,
    end_date: Optional[str] = None,
    tool_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Calculate progress metrics for a user.

    Args:
        user_id: User ID
        period_type: 'daily', 'weekly', or 'monthly'
        end_date: End date (optional)
        tool_context: Optional ADK tool context

    Returns:
        Dict with status, data, error
    """
    result = await progress_calculator.execute(
        user_id=user_id,
        period_type=period_type,
        end_date=end_date,
        tool_context=tool_context
    )

    return {
        "status": "success" if result.success else "error",
        "data": result.data,
        "error": result.error
    }


__all__ = ['ProgressCalculatorTool', 'progress_calculator', 'calculate_progress_metrics']