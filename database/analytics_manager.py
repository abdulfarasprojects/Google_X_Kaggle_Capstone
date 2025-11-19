"""
Analytics database manager.

This module provides database operations for progress summaries and analytics,
including generation, retrieval, and caching of progress data.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta

from database.init import get_db_session
from database.models import ProgressSummary, UserProfile, MealLog, WorkoutLog, WellnessLog

logger = logging.getLogger(__name__)


class AnalyticsManager:
    """
    Database manager for analytics operations.

    Provides CRUD operations and analytics generation for progress summaries.
    """

    @staticmethod
    def generate_progress_summary(
        user_id: str,
        period_type: str,
        period_start: date,
        period_end: date
    ) -> Optional[str]:
        """
        Generate and store a progress summary for a user.

        Args:
            user_id: User identifier
            period_type: 'daily', 'weekly', or 'monthly'
            period_start: Start date of period
            period_end: End date of period

        Returns:
            Summary ID if successful, None if failed
        """
        try:
            import uuid
            summary_id = str(uuid.uuid4())

            with get_db_session() as session:
                # Calculate metrics
                metrics = AnalyticsManager._calculate_period_metrics(session, user_id, period_start, period_end)

                # Get hero stat
                hero_stat = AnalyticsManager._generate_hero_stat(session, user_id, period_start, period_end)

                # Create summary
                summary = ProgressSummary(
                    summary_id=summary_id,
                    user_id=user_id,
                    period_type=period_type,
                    period_start=period_start,
                    period_end=period_end,
                    calories_logged=metrics['calories_logged'],
                    workouts_completed=metrics['workouts_completed'],
                    sleep_avg_hours=metrics['sleep_avg_hours'],
                    water_avg_glasses=metrics['water_avg_glasses'],
                    steps_avg_count=metrics['steps_avg_count'],
                    streak_days=metrics['streak_days'],
                    hero_stat=hero_stat
                )

                session.add(summary)
                session.commit()

                logger.info(f"Generated progress summary: {summary_id} for user {user_id}")
                return summary_id

        except Exception as e:
            logger.error(f"Failed to generate progress summary: {e}")
            return None

    @staticmethod
    def get_daily_progress_summary(user_id: str, target_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Get daily progress summary for a user.

        Args:
            user_id: User identifier
            target_date: Date to get summary for (defaults to today)

        Returns:
            Dict with summary data
        """
        try:
            if target_date is None:
                target_date = date.today()

            with get_db_session() as session:
                # Try to get existing summary first
                summary = session.query(ProgressSummary).filter_by(
                    user_id=user_id,
                    period_type='daily',
                    period_start=target_date,
                    period_end=target_date
                ).first()

                if summary:
                    return AnalyticsManager._format_summary(summary)

                # Generate new summary
                summary_id = AnalyticsManager.generate_progress_summary(
                    user_id, 'daily', target_date, target_date
                )

                if summary_id:
                    summary = session.query(ProgressSummary).filter_by(summary_id=summary_id).first()
                    if summary:
                        return AnalyticsManager._format_summary(summary)

                # Fallback to real-time calculation
                return AnalyticsManager._get_realtime_daily_summary(session, user_id, target_date)

        except Exception as e:
            logger.error(f"Failed to get daily progress summary: {e}")
            return {"status": "error", "error": str(e)}

    @staticmethod
    def get_weekly_progress_summary(user_id: str, week_end: Optional[date] = None) -> Dict[str, Any]:
        """
        Get weekly progress summary for a user.

        Args:
            user_id: User identifier
            week_end: End date of week (defaults to today)

        Returns:
            Dict with summary data
        """
        try:
            if week_end is None:
                week_end = date.today()

            # Calculate week start (Monday of the week)
            week_start = week_end - timedelta(days=week_end.weekday())

            with get_db_session() as session:
                # Try to get existing summary
                summary = session.query(ProgressSummary).filter_by(
                    user_id=user_id,
                    period_type='weekly',
                    period_start=week_start,
                    period_end=week_end
                ).first()

                if summary:
                    return AnalyticsManager._format_summary(summary)

                # Generate new summary
                summary_id = AnalyticsManager.generate_progress_summary(
                    user_id, 'weekly', week_start, week_end
                )

                if summary_id:
                    summary = session.query(ProgressSummary).filter_by(summary_id=summary_id).first()
                    if summary:
                        return AnalyticsManager._format_summary(summary)

                # Fallback to real-time calculation
                return AnalyticsManager._get_realtime_weekly_summary(session, user_id, week_start, week_end)

        except Exception as e:
            logger.error(f"Failed to get weekly progress summary: {e}")
            return {"status": "error", "error": str(e)}

    @staticmethod
    def get_monthly_progress_summary(user_id: str, month_end: Optional[date] = None) -> Dict[str, Any]:
        """
        Get monthly progress summary for a user.

        Args:
            user_id: User identifier
            month_end: End date of month (defaults to today)

        Returns:
            Dict with summary data
        """
        try:
            if month_end is None:
                month_end = date.today()

            # Calculate month start
            month_start = month_end.replace(day=1)

            with get_db_session() as session:
                # Try to get existing summary
                summary = session.query(ProgressSummary).filter_by(
                    user_id=user_id,
                    period_type='monthly',
                    period_start=month_start,
                    period_end=month_end
                ).first()

                if summary:
                    return AnalyticsManager._format_summary(summary)

                # Generate new summary
                summary_id = AnalyticsManager.generate_progress_summary(
                    user_id, 'monthly', month_start, month_end
                )

                if summary_id:
                    summary = session.query(ProgressSummary).filter_by(summary_id=summary_id).first()
                    if summary:
                        return AnalyticsManager._format_summary(summary)

                # Fallback to real-time calculation
                return AnalyticsManager._get_realtime_monthly_summary(session, user_id, month_start, month_end)

        except Exception as e:
            logger.error(f"Failed to get monthly progress summary: {e}")
            return {"status": "error", "error": str(e)}

    @staticmethod
    def _calculate_period_metrics(session, user_id: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Calculate metrics for a date period.

        Args:
            session: Database session
            user_id: User identifier
            start_date: Period start
            end_date: Period end

        Returns:
            Dict with calculated metrics
        """
        # Calories logged
        calories_result = session.query(MealLog.total_calories).filter(
            MealLog.user_id == user_id,
            MealLog.log_date >= start_date,
            MealLog.log_date <= end_date
        ).all()
        calories_logged = sum(cal[0] for cal in calories_result)

        # Workouts completed
        workouts_completed = session.query(WorkoutLog).filter(
            WorkoutLog.user_id == user_id,
            WorkoutLog.log_date >= start_date,
            WorkoutLog.log_date <= end_date
        ).count()

        # Sleep average
        sleep_logs = session.query(WellnessLog.sleep_hours).filter(
            WellnessLog.user_id == user_id,
            WellnessLog.log_date >= start_date,
            WellnessLog.log_date <= end_date,
            WellnessLog.sleep_hours > 0
        ).all()
        sleep_avg_hours = sum(log[0] for log in sleep_logs) / len(sleep_logs) if sleep_logs else 0

        # Water average
        water_logs = session.query(WellnessLog.water_glasses).filter(
            WellnessLog.user_id == user_id,
            WellnessLog.log_date >= start_date,
            WellnessLog.log_date <= end_date,
            WellnessLog.water_glasses > 0
        ).all()
        water_avg_glasses = sum(log[0] for log in water_logs) / len(water_logs) if water_logs else 0

        # Steps average
        steps_logs = session.query(WellnessLog.steps_count).filter(
            WellnessLog.user_id == user_id,
            WellnessLog.log_date >= start_date,
            WellnessLog.log_date <= end_date,
            WellnessLog.steps_count > 0
        ).all()
        steps_avg_count = int(sum(log[0] for log in steps_logs) / len(steps_logs)) if steps_logs else 0

        # Current streak (simplified)
        streak_days = AnalyticsManager._calculate_streak(session, user_id, end_date)

        return {
            'calories_logged': calories_logged,
            'workouts_completed': workouts_completed,
            'sleep_avg_hours': sleep_avg_hours,
            'water_avg_glasses': water_avg_glasses,
            'steps_avg_count': steps_avg_count,
            'streak_days': streak_days
        }

    @staticmethod
    def _calculate_streak(session, user_id: str, current_date: date) -> int:
        """Calculate current streak length."""
        streak = 0
        check_date = current_date

        for i in range(60):
            logs = session.query(MealLog).filter(
                MealLog.user_id == user_id,
                MealLog.log_date == check_date
            ).count()
            logs += session.query(WorkoutLog).filter(
                WorkoutLog.user_id == user_id,
                WorkoutLog.log_date == check_date
            ).count()
            logs += session.query(WellnessLog).filter(
                WellnessLog.user_id == user_id,
                WellnessLog.log_date == check_date
            ).count()

            if logs > 0:
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break

        return streak

    @staticmethod
    def _generate_hero_stat(session, user_id: str, start_date: date, end_date: date) -> str:
        """
        Generate a hero stat for the period.

        Args:
            session: Database session
            user_id: User identifier
            start_date: Period start
            end_date: Period end

        Returns:
            Hero stat string
        """
        # Simple hero stat generation - could be enhanced
        streak = AnalyticsManager._calculate_streak(session, user_id, end_date)

        if streak >= 7:
            return f"{streak}-day logging streak!"
        elif streak >= 3:
            return f"{streak} days of consistency!"
        else:
            workouts = session.query(WorkoutLog).filter(
                WorkoutLog.user_id == user_id,
                WorkoutLog.log_date >= start_date,
                WorkoutLog.log_date <= end_date
            ).count()

            if workouts > 0:
                return f"{workouts} workout sessions completed!"
            else:
                return "Keep up the great work!"

    @staticmethod
    def _format_summary(summary: ProgressSummary) -> Dict[str, Any]:
        """
        Format a progress summary for API response.

        Args:
            summary: ProgressSummary object

        Returns:
            Formatted dict
        """
        return {
            "status": "success",
            "summary_id": summary.summary_id,
            "period_type": summary.period_type,
            "period_start": summary.period_start.isoformat(),
            "period_end": summary.period_end.isoformat(),
            "metrics": {
                "calories_logged": summary.calories_logged,
                "workouts_completed": summary.workouts_completed,
                "sleep_avg_hours": round(summary.sleep_avg_hours or 0, 1),
                "water_avg_glasses": round(summary.water_avg_glasses or 0, 1),
                "steps_avg_count": summary.steps_avg_count or 0,
                "streak_days": summary.streak_days
            },
            "hero_stat": summary.hero_stat,
            "generated_at": summary.created_at.isoformat()
        }

    @staticmethod
    def _get_realtime_daily_summary(session, user_id: str, target_date: date) -> Dict[str, Any]:
        """Get real-time daily summary when no cached summary exists."""
        metrics = AnalyticsManager._calculate_period_metrics(session, user_id, target_date, target_date)
        hero_stat = AnalyticsManager._generate_hero_stat(session, user_id, target_date, target_date)

        return {
            "status": "success",
            "period_type": "daily",
            "period_start": target_date.isoformat(),
            "period_end": target_date.isoformat(),
            "metrics": metrics,
            "hero_stat": hero_stat,
            "generated_at": datetime.utcnow().isoformat(),
            "note": "Real-time calculation"
        }

    @staticmethod
    def _get_realtime_weekly_summary(session, user_id: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get real-time weekly summary when no cached summary exists."""
        metrics = AnalyticsManager._calculate_period_metrics(session, user_id, start_date, end_date)
        hero_stat = AnalyticsManager._generate_hero_stat(session, user_id, start_date, end_date)

        return {
            "status": "success",
            "period_type": "weekly",
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "metrics": metrics,
            "hero_stat": hero_stat,
            "generated_at": datetime.utcnow().isoformat(),
            "note": "Real-time calculation"
        }

    @staticmethod
    def _get_realtime_monthly_summary(session, user_id: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get real-time monthly summary when no cached summary exists."""
        metrics = AnalyticsManager._calculate_period_metrics(session, user_id, start_date, end_date)
        hero_stat = AnalyticsManager._generate_hero_stat(session, user_id, start_date, end_date)

        return {
            "status": "success",
            "period_type": "monthly",
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "metrics": metrics,
            "hero_stat": hero_stat,
            "generated_at": datetime.utcnow().isoformat(),
            "note": "Real-time calculation"
        }


# Create singleton instance
analytics_manager = AnalyticsManager()

# Convenience functions
def generate_progress_summary(
    user_id: str,
    period_type: str,
    period_start: date,
    period_end: date
) -> Optional[str]:
    """Convenience function to generate a progress summary."""
    return analytics_manager.generate_progress_summary(
        user_id=user_id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end
    )

__all__ = ['AnalyticsManager', 'analytics_manager', 'generate_progress_summary']