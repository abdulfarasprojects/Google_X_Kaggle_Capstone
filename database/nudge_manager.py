"""
Nudge event database manager.

This module provides database operations for nudge events, including
creation, retrieval, scheduling, and analytics for autonomous nudges.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session

from database.init import get_db_session
from database.models import NudgeEvent, UserProfile

logger = logging.getLogger(__name__)


class NudgeManager:
    """
    Database manager for nudge event operations.

    Provides CRUD operations and scheduling for autonomous nudges.
    """

    @staticmethod
    def create_nudge_event(
        user_id: str,
        nudge_type: str,
        message: str,
        scheduled_time: datetime,
        status: str = 'scheduled'
    ) -> Optional[str]:
        """
        Create a new nudge event.

        Args:
            user_id: User identifier
            nudge_type: Type of nudge (morning, midday, evening, etc.)
            message: Nudge message content
            scheduled_time: When to send the nudge
            status: Initial status (defaults to 'scheduled')

        Returns:
            Nudge ID if successful, None if failed
        """
        try:
            import uuid
            nudge_id = str(uuid.uuid4())

            with get_db_session() as session:
                nudge = NudgeEvent(
                    nudge_id=nudge_id,
                    user_id=user_id,
                    nudge_type=nudge_type,
                    message=message,
                    scheduled_time=scheduled_time,
                    status=status
                )

                session.add(nudge)
                session.commit()

                logger.info(f"Created nudge event: {nudge_id} for user {user_id}")
                return nudge_id

        except Exception as e:
            logger.error(f"Failed to create nudge event: {e}")
            return None

    @staticmethod
    def get_pending_nudges(current_time: Optional[datetime] = None) -> List[NudgeEvent]:
        """
        Get all pending nudges that should be sent.

        Args:
            current_time: Current time (defaults to now)

        Returns:
            List of pending nudge events
        """
        if current_time is None:
            current_time = datetime.utcnow()

        try:
            with get_db_session() as session:
                nudges = session.query(NudgeEvent).filter(
                    NudgeEvent.status == 'scheduled',
                    NudgeEvent.scheduled_time <= current_time
                ).all()

                logger.info(f"Found {len(nudges)} pending nudges")
                return nudges

        except Exception as e:
            logger.error(f"Failed to get pending nudges: {e}")
            return []

    @staticmethod
    def mark_nudge_delivered(nudge_id: str, delivered_at: Optional[datetime] = None) -> bool:
        """
        Mark a nudge as delivered.

        Args:
            nudge_id: Nudge event ID
            delivered_at: Time of delivery (defaults to now)

        Returns:
            True if successful, False otherwise
        """
        try:
            if delivered_at is None:
                delivered_at = datetime.utcnow()

            with get_db_session() as session:
                nudge = session.query(NudgeEvent).filter_by(nudge_id=nudge_id).first()

                if not nudge:
                    logger.error(f"Nudge not found: {nudge_id}")
                    return False

                nudge.status = 'delivered'
                nudge.delivered_at = delivered_at
                session.commit()

                logger.info(f"Marked nudge as delivered: {nudge_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to mark nudge delivered: {e}")
            return False

    @staticmethod
    def cancel_nudge(nudge_id: str) -> bool:
        """
        Cancel a scheduled nudge.

        Args:
            nudge_id: Nudge event ID

        Returns:
            True if successful, False otherwise
        """
        try:
            with get_db_session() as session:
                nudge = session.query(NudgeEvent).filter_by(nudge_id=nudge_id).first()

                if not nudge:
                    logger.error(f"Nudge not found: {nudge_id}")
                    return False

                nudge.status = 'cancelled'
                session.commit()

                logger.info(f"Cancelled nudge: {nudge_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to cancel nudge: {e}")
            return False

    @staticmethod
    def get_nudge_history(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get nudge history for a user.

        Args:
            user_id: User identifier
            limit: Maximum number of records to return

        Returns:
            List of nudge event dictionaries
        """
        try:
            with get_db_session() as session:
                nudges = session.query(NudgeEvent).filter_by(user_id=user_id)\
                    .order_by(NudgeEvent.scheduled_time.desc())\
                    .limit(limit)\
                    .all()

                result = []
                for nudge in nudges:
                    result.append({
                        'nudge_id': nudge.nudge_id,
                        'nudge_type': nudge.nudge_type,
                        'message': nudge.message,
                        'scheduled_time': nudge.scheduled_time.isoformat(),
                        'delivered_at': nudge.delivered_at.isoformat() if nudge.delivered_at else None,
                        'status': nudge.status
                    })

                logger.info(f"Retrieved {len(result)} nudge history records for user {user_id}")
                return result

        except Exception as e:
            logger.error(f"Failed to get nudge history: {e}")
            return []

    @staticmethod
    def schedule_protection_nudge(user_id: str) -> Dict[str, Any]:
        """
        Schedule an immediate streak protection nudge.

        Args:
            user_id: User identifier

        Returns:
            Dict with status and nudge info
        """
        try:
            # Schedule for 5 minutes from now for immediate protection
            scheduled_time = datetime.utcnow() + timedelta(minutes=5)

            nudge_id = NudgeManager.create_nudge_event(
                user_id=user_id,
                nudge_type='streak_protection',
                message="⏰ Don't break your streak! Log something quick before midnight! 🔥",
                scheduled_time=scheduled_time
            )

            if nudge_id:
                return {
                    'status': 'success',
                    'nudge_id': nudge_id,
                    'scheduled_time': scheduled_time.isoformat()
                }
            else:
                return {'status': 'error', 'error': 'Failed to create nudge'}

        except Exception as e:
            logger.error(f"Failed to schedule protection nudge: {e}")
            return {'status': 'error', 'error': str(e)}

    @staticmethod
    def get_user_nudge_stats(user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get nudge statistics for a user.

        Args:
            user_id: User identifier
            days: Number of days to look back

        Returns:
            Dict with nudge statistics
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            with get_db_session() as session:
                total_nudges = session.query(NudgeEvent).filter(
                    NudgeEvent.user_id == user_id,
                    NudgeEvent.scheduled_time >= cutoff_date
                ).count()

                delivered_nudges = session.query(NudgeEvent).filter(
                    NudgeEvent.user_id == user_id,
                    NudgeEvent.status == 'delivered',
                    NudgeEvent.scheduled_time >= cutoff_date
                ).count()

                nudge_types = session.query(
                    NudgeEvent.nudge_type,
                    NudgeEvent.status
                ).filter(
                    NudgeEvent.user_id == user_id,
                    NudgeEvent.scheduled_time >= cutoff_date
                ).all()

                type_counts = {}
                for nudge_type, status in nudge_types:
                    if nudge_type not in type_counts:
                        type_counts[nudge_type] = {'total': 0, 'delivered': 0}
                    type_counts[nudge_type]['total'] += 1
                    if status == 'delivered':
                        type_counts[nudge_type]['delivered'] += 1

                return {
                    'total_nudges': total_nudges,
                    'delivered_nudges': delivered_nudges,
                    'delivery_rate': delivered_nudges / total_nudges if total_nudges > 0 else 0,
                    'nudge_types': type_counts,
                    'period_days': days
                }

        except Exception as e:
            logger.error(f"Failed to get nudge stats: {e}")
            return {'error': str(e)}

    @staticmethod
    def cleanup_old_nudges(days_to_keep: int = 90) -> int:
        """
        Clean up old nudge events.

        Args:
            days_to_keep: Number of days of history to keep

        Returns:
            Number of records deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            with get_db_session() as session:
                deleted_count = session.query(NudgeEvent).filter(
                    NudgeEvent.scheduled_time < cutoff_date
                ).delete()

                session.commit()

                logger.info(f"Cleaned up {deleted_count} old nudge events")
                return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old nudges: {e}")
            return 0


# Create singleton instance
nudge_manager = NudgeManager()

# Convenience functions
def schedule_nudge(
    user_id: str,
    nudge_type: str,
    message: str,
    scheduled_time: datetime
) -> Optional[str]:
    """Convenience function to schedule a nudge."""
    return nudge_manager.create_nudge_event(
        user_id=user_id,
        nudge_type=nudge_type,
        message=message,
        scheduled_time=scheduled_time
    )

def get_pending_nudges() -> List[NudgeEvent]:
    """Convenience function to get pending nudges."""
    return nudge_manager.get_pending_nudges()

__all__ = ['NudgeManager', 'nudge_manager', 'schedule_nudge', 'get_pending_nudges']