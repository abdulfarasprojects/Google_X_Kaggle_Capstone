"""
Wellness logging database manager.

This module provides database operations for wellness logging, including
creation, retrieval, updates, and analytics for wellness data.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database.init import get_db_session
from database.models import WellnessLog, UserProfile

logger = logging.getLogger(__name__)


class WellnessManager:
    """
    Database manager for wellness logging operations.

    Provides CRUD operations and analytics for wellness logs.
    Note: Only one wellness log per user per day is allowed.
    """

    @staticmethod
    def create_wellness_log(
        user_id: str,
        sleep_hours: float,
        sleep_quality: int,
        water_glasses: float,
        steps_count: int,
        log_date: Optional[date] = None
    ) -> Optional[str]:
        """
        Create a new wellness log entry.

        Args:
            user_id: User identifier
            sleep_hours: Hours of sleep (0-24)
            sleep_quality: Self-reported quality (1-10 scale)
            water_glasses: Glasses of water consumed (0-20)
            steps_count: Daily step count (0-100,000)
            log_date: Date of the wellness tracking (defaults to today)

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
                wellness_date = log_date or date.today()

                # Check if log already exists for this date
                existing_log = session.query(WellnessLog).filter_by(
                    user_id=user_id,
                    log_date=wellness_date
                ).first()

                if existing_log:
                    logger.warning(f"Wellness log already exists for user {user_id} on {wellness_date}")
                    return None

                # Generate unique log ID
                log_id = f"{user_id}_wellness_{datetime.utcnow().timestamp()}"

                # Create wellness log
                wellness_log = WellnessLog(
                    log_id=log_id,
                    user_id=user_id,
                    sleep_hours=sleep_hours,
                    sleep_quality=sleep_quality,
                    water_glasses=water_glasses,
                    steps_count=steps_count,
                    log_date=wellness_date
                )

                session.add(wellness_log)
                session.commit()

                logger.info(f"Created wellness log: {log_id}")
                return log_id

        except IntegrityError:
            logger.warning(f"Duplicate wellness log for user {user_id} on {log_date or date.today()}")
            return None
        except Exception as e:
            logger.error(f"Failed to create wellness log: {e}")
            return None

    @staticmethod
    def get_wellness_logs(
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50
    ) -> List[WellnessLog]:
        """
        Retrieve wellness logs for a user.

        Args:
            user_id: User identifier
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum number of results

        Returns:
            List of WellnessLog objects
        """
        try:
            with get_db_session() as session:
                query = session.query(WellnessLog).filter_by(user_id=user_id)

                if start_date:
                    query = query.filter(WellnessLog.log_date >= start_date)
                if end_date:
                    query = query.filter(WellnessLog.log_date <= end_date)

                return query.order_by(WellnessLog.log_date.desc(), WellnessLog.created_at.desc()).limit(limit).all()

        except Exception as e:
            logger.error(f"Failed to retrieve wellness logs: {e}")
            return []

    @staticmethod
    def get_daily_wellness_summary(user_id: str, target_date: date) -> Dict[str, Any]:
        """
        Get wellness summary for a specific day.

        Args:
            user_id: User identifier
            target_date: Date to summarize

        Returns:
            Dictionary with daily wellness metrics
        """
        try:
            with get_db_session() as session:
                wellness = session.query(WellnessLog).filter_by(
                    user_id=user_id,
                    log_date=target_date
                ).first()

                if wellness:
                    return {
                        "date": target_date.isoformat(),
                        "logged": True,
                        "sleep_hours": wellness.sleep_hours,
                        "sleep_quality": wellness.sleep_quality,
                        "water_glasses": wellness.water_glasses,
                        "steps_count": wellness.steps_count,
                        "overall_score": (wellness.sleep_quality + min(wellness.water_glasses / 2, 5) + min(wellness.steps_count / 2000, 5)) / 3,
                        "created_at": wellness.created_at.isoformat()
                    }
                else:
                    return {
                        "date": target_date.isoformat(),
                        "logged": False,
                        "sleep_hours": 0.0,
                        "sleep_quality": 0,
                        "water_glasses": 0.0,
                        "steps_count": 0,
                        "overall_score": 0.0
                    }

        except Exception as e:
            logger.error(f"Failed to get daily wellness summary: {e}")
            return {
                "date": target_date.isoformat(),
                "logged": False,
                "sleep_hours": 0.0,
                "sleep_quality": 0,
                "water_glasses": 0.0,
                "steps_count": 0,
                "overall_score": 0.0
            }

    @staticmethod
    def get_wellness_analytics(
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get wellness analytics for recent period.

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

                # Get all wellness logs in period
                wellness_logs = session.query(WellnessLog).filter(
                    WellnessLog.user_id == user_id,
                    WellnessLog.log_date >= start_date,
                    WellnessLog.log_date <= end_date
                ).all()

                if not wellness_logs:
                    return {
                        "period_days": days,
                        "days_logged": 0,
                        "avg_sleep_hours": 0.0,
                        "avg_sleep_quality": 0.0,
                        "avg_water_glasses": 0.0,
                        "avg_steps": 0,
                        "consistency_score": 0.0
                    }

                # Calculate averages
                total_sleep = sum(log.sleep_hours for log in wellness_logs)
                total_quality = sum(log.sleep_quality for log in wellness_logs)
                total_water = sum(log.water_glasses for log in wellness_logs)
                total_steps = sum(log.steps_count for log in wellness_logs)
                days_logged = len(wellness_logs)

                return {
                    "period_days": days,
                    "days_logged": days_logged,
                    "avg_sleep_hours": round(total_sleep / days_logged, 1),
                    "avg_sleep_quality": round(total_quality / days_logged, 1),
                    "avg_water_glasses": round(total_water / days_logged, 1),
                    "avg_steps": round(total_steps / days_logged),
                    "consistency_score": round(days_logged / days, 2)
                }

        except Exception as e:
            logger.error(f"Failed to get wellness analytics: {e}")
            return {
                "period_days": days,
                "days_logged": 0,
                "avg_sleep_hours": 0.0,
                "avg_sleep_quality": 0.0,
                "avg_water_glasses": 0.0,
                "avg_steps": 0,
                "consistency_score": 0.0
            }

    @staticmethod
    def update_wellness_log(
        log_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update an existing wellness log.

        Args:
            log_id: Wellness log identifier
            updates: Fields to update

        Returns:
            True if successful, False otherwise
        """
        try:
            with get_db_session() as session:
                wellness = session.query(WellnessLog).filter_by(log_id=log_id).first()
                if not wellness:
                    logger.error(f"Wellness log not found: {log_id}")
                    return False

                # Update allowed fields
                allowed_fields = [
                    'sleep_hours', 'sleep_quality', 'water_glasses',
                    'steps_count', 'log_date'
                ]

                for field, value in updates.items():
                    if field in allowed_fields:
                        setattr(wellness, field, value)

                session.commit()

                logger.info(f"Updated wellness log: {log_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to update wellness log: {e}")
            return False

    @staticmethod
    def delete_wellness_log(log_id: str, user_id: str) -> bool:
        """
        Delete a wellness log.

        Args:
            log_id: Wellness log identifier
            user_id: User ID for ownership verification

        Returns:
            True if successful, False otherwise
        """
        try:
            with get_db_session() as session:
                wellness = session.query(WellnessLog).filter_by(
                    log_id=log_id,
                    user_id=user_id
                ).first()

                if not wellness:
                    logger.error(f"Wellness log not found: {log_id}")
                    return False

                session.delete(wellness)
                session.commit()

                logger.info(f"Deleted wellness log: {log_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to delete wellness log: {e}")
            return False

    @staticmethod
    def upsert_wellness_log(
        user_id: str,
        sleep_hours: float,
        sleep_quality: int,
        water_glasses: float,
        steps_count: int,
        log_date: Optional[date] = None
    ) -> Optional[str]:
        """
        Create or update wellness log for a specific date.

        If a log already exists for the date, it will be updated.
        Otherwise, a new log will be created.

        Args:
            user_id: User identifier
            sleep_hours: Hours of sleep (0-24)
            sleep_quality: Self-reported quality (1-10 scale)
            water_glasses: Glasses of water consumed (0-20)
            steps_count: Daily step count (0-100,000)
            log_date: Date of the wellness tracking (defaults to today)

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
                wellness_date = log_date or date.today()

                # Check if log already exists for this date
                existing_log = session.query(WellnessLog).filter_by(
                    user_id=user_id,
                    log_date=wellness_date
                ).first()

                if existing_log:
                    # Update existing log
                    existing_log.sleep_hours = sleep_hours
                    existing_log.sleep_quality = sleep_quality
                    existing_log.water_glasses = water_glasses
                    existing_log.steps_count = steps_count

                    session.commit()
                    logger.info(f"Updated existing wellness log: {existing_log.log_id}")
                    return existing_log.log_id
                else:
                    # Create new log
                    return WellnessManager.create_wellness_log(
                        user_id=user_id,
                        sleep_hours=sleep_hours,
                        sleep_quality=sleep_quality,
                        water_glasses=water_glasses,
                        steps_count=steps_count,
                        log_date=wellness_date
                    )

        except Exception as e:
            logger.error(f"Failed to upsert wellness log: {e}")
            return None


# Create singleton instance
wellness_manager = WellnessManager()

# Convenience functions
def log_wellness(
    user_id: str,
    sleep_hours: float,
    sleep_quality: int,
    water_glasses: float,
    steps_count: int
) -> Optional[str]:
    """Convenience function to log wellness metrics."""
    return wellness_manager.create_wellness_log(
        user_id=user_id,
        sleep_hours=sleep_hours,
        sleep_quality=sleep_quality,
        water_glasses=water_glasses,
        steps_count=steps_count
    )

def upsert_wellness(
    user_id: str,
    sleep_hours: float,
    sleep_quality: int,
    water_glasses: float,
    steps_count: int
) -> Optional[str]:
    """Convenience function to create or update wellness metrics."""
    return wellness_manager.upsert_wellness_log(
        user_id=user_id,
        sleep_hours=sleep_hours,
        sleep_quality=sleep_quality,
        water_glasses=water_glasses,
        steps_count=steps_count
    )

__all__ = ['WellnessManager', 'wellness_manager', 'log_wellness', 'upsert_wellness']