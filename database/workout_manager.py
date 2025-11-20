"""
Workout logging database manager.

This module provides database operations for workout logging, including
creation, retrieval, updates, and analytics for fitness data.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session

from database.init import get_db_session
from database.models import WorkoutLog, UserProfile

logger = logging.getLogger(__name__)


class WorkoutManager:
    """
    Database manager for workout logging operations.

    Provides CRUD operations and analytics for workout logs.
    """

    @staticmethod
    def create_workout_log(
        user_id: str,
        exercises: List[Dict[str, Any]],
        total_volume: int,
        progression_suggestion: Optional[str] = None,
        log_date: Optional[date] = None
    ) -> Optional[str]:
        """
        Create a new workout log entry.

        Args:
            user_id: User identifier
            exercises: List of exercise dictionaries
            total_volume: Calculated total volume score
            progression_suggestion: AI-generated progression recommendation
            log_date: Date of the workout (defaults to today)

        Returns:
            Log ID if successful, None if failed
        """
        try:
            with get_db_session() as session:
                # Validate user exists
                user = session.query(UserProfile).filter_by(user_id=user_id).first()
                if not user:
                    logger.error(f"User not found: {user_id}")
                    return None

                # Use provided date or today
                workout_date = log_date or date.today()

                # Generate unique log ID
                log_id = f"{user_id}_workout_{datetime.utcnow().timestamp()}"

                # Create workout log
                workout_log = WorkoutLog(
                    log_id=log_id,
                    user_id=user_id,
                    total_volume=total_volume,
                    progression_suggestion=progression_suggestion,
                    log_date=workout_date
                )
                # Set exercises using the property setter which handles JSON conversion
                workout_log.exercises_list = exercises

                session.add(workout_log)
                session.commit()

                logger.info(f"Created workout log: {log_id}")
                return log_id

        except Exception as e:
            logger.error(f"Failed to create workout log: {e}")
            return None

    @staticmethod
    def get_workout_logs(
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50
    ) -> List[WorkoutLog]:
        """
        Retrieve workout logs for a user.

        Args:
            user_id: User identifier
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum number of results

        Returns:
            List of WorkoutLog objects
        """
        try:
            with get_db_session() as session:
                query = session.query(WorkoutLog).filter_by(user_id=user_id)

                if start_date:
                    query = query.filter(WorkoutLog.log_date >= start_date)
                if end_date:
                    query = query.filter(WorkoutLog.log_date <= end_date)

                return query.order_by(WorkoutLog.log_date.desc(), WorkoutLog.created_at.desc()).limit(limit).all()

        except Exception as e:
            logger.error(f"Failed to retrieve workout logs: {e}")
            return []

    @staticmethod
    def get_daily_workout_summary(user_id: str, target_date: date) -> Dict[str, Any]:
        """
        Get workout summary for a specific day.

        Args:
            user_id: User identifier
            target_date: Date to summarize

        Returns:
            Dictionary with daily workout totals
        """
        try:
            with get_db_session() as session:
                workouts = session.query(WorkoutLog).filter_by(
                    user_id=user_id,
                    log_date=target_date
                ).all()

                summary = {
                    "date": target_date.isoformat(),
                    "total_volume": 0,
                    "workouts_logged": len(workouts),
                    "exercises_completed": 0,
                    "workouts": []
                }

                for workout in workouts:
                    summary["total_volume"] += workout.total_volume
                    exercise_count = len(workout.exercises_list) if workout.exercises_list else 0
                    summary["exercises_completed"] += exercise_count

                    summary["workouts"].append({
                        "log_id": workout.log_id,
                        "exercises": exercise_count,
                        "volume": workout.total_volume,
                        "progression_suggestion": workout.progression_suggestion,
                        "created_at": workout.created_at.isoformat()
                    })

                return summary

        except Exception as e:
            logger.error(f"Failed to get daily workout summary: {e}")
            return {
                "date": target_date.isoformat(),
                "total_volume": 0,
                "workouts_logged": 0,
                "exercises_completed": 0,
                "workouts": []
            }

    @staticmethod
    def get_workout_analytics(
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get workout analytics for recent period.

        Args:
            user_id: User identifier
            days: Number of days to analyze

        Returns:
            Analytics dictionary
        """
        try:
            with get_db_session() as session:
                # Calculate date range
                end_date = date.today()
                start_date = end_date - timedelta(days=days-1)

                # Get all workouts in period
                workouts = session.query(WorkoutLog).filter(
                    WorkoutLog.user_id == user_id,
                    WorkoutLog.log_date >= start_date,
                    WorkoutLog.log_date <= end_date
                ).all()

                if not workouts:
                    return {
                        "period_days": days,
                        "total_workouts": 0,
                        "total_volume": 0,
                        "avg_daily_volume": 0.0,
                        "avg_workouts_per_week": 0.0,
                        "exercise_types": {}
                    }

                # Calculate totals
                total_volume = sum(workout.total_volume for workout in workouts)
                total_workouts = len(workouts)

                # Exercise type breakdown
                exercise_types = {}
                for workout in workouts:
                    if workout.exercises_list:
                        for exercise in workout.exercises_list:
                            exercise_name = exercise.get('name', 'unknown')
                            if exercise_name not in exercise_types:
                                exercise_types[exercise_name] = {"count": 0, "total_volume": 0}
                            exercise_types[exercise_name]["count"] += 1
                            # Add volume contribution (simplified)
                            sets = exercise.get('sets', 0)
                            reps = exercise.get('reps', 0)
                            weight = exercise.get('weight', 0)
                            exercise_types[exercise_name]["total_volume"] += sets * reps * weight

                return {
                    "period_days": days,
                    "total_workouts": total_workouts,
                    "total_volume": total_volume,
                    "avg_daily_volume": round(total_volume / days, 1),
                    "avg_workouts_per_week": round(total_workouts / (days / 7), 1),
                    "exercise_types": exercise_types
                }

        except Exception as e:
            logger.error(f"Failed to get workout analytics: {e}")
            return {
                "period_days": days,
                "total_workouts": 0,
                "total_volume": 0,
                "avg_daily_volume": 0.0,
                "avg_workouts_per_week": 0.0,
                "exercise_types": {}
            }

    @staticmethod
    def update_workout_log(
        log_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update an existing workout log.

        Args:
            log_id: Workout log identifier
            updates: Fields to update

        Returns:
            True if successful, False otherwise
        """
        try:
            with get_db_session() as session:
                workout = session.query(WorkoutLog).filter_by(log_id=log_id).first()
                if not workout:
                    logger.error(f"Workout log not found: {log_id}")
                    return False

                # Update allowed fields
                allowed_fields = [
                    'exercises', 'total_volume', 'progression_suggestion', 'log_date'
                ]

                for field, value in updates.items():
                    if field in allowed_fields:
                        setattr(workout, field, value)

                session.commit()

                logger.info(f"Updated workout log: {log_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to update workout log: {e}")
            return False

    @staticmethod
    def delete_workout_log(log_id: str, user_id: str) -> bool:
        """
        Delete a workout log.

        Args:
            log_id: Workout log identifier
            user_id: User ID for ownership verification

        Returns:
            True if successful, False otherwise
        """
        try:
            with get_db_session() as session:
                workout = session.query(WorkoutLog).filter_by(
                    log_id=log_id,
                    user_id=user_id
                ).first()

                if not workout:
                    logger.error(f"Workout log not found: {log_id}")
                    return False

                session.delete(workout)
                session.commit()

                logger.info(f"Deleted workout log: {log_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to delete workout log: {e}")
            return False


# Create singleton instance
workout_manager = WorkoutManager()

# Convenience functions
def log_workout(
    user_id: str,
    exercises: List[Dict[str, Any]],
    total_volume: int,
    progression_suggestion: Optional[str] = None
) -> Optional[str]:
    """Convenience function to log a workout."""
    return workout_manager.create_workout_log(
        user_id=user_id,
        exercises=exercises,
        total_volume=total_volume,
        progression_suggestion=progression_suggestion
    )

__all__ = ['WorkoutManager', 'workout_manager', 'log_workout']