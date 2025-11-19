"""
APScheduler integration for autonomous nudge delivery.

This module provides background scheduling for autonomous nudges using APScheduler.
It integrates with the nudge agent to send timely reminders and streak protection.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

from config.settings import settings
from config.logging import get_logger
from database.nudge_manager import nudge_manager
from agents.nudge.agent import nudge_agent
from telegram_bot.bot import send_message_to_user

logger = get_logger(__name__)


class NudgeScheduler:
    """
    APScheduler wrapper for autonomous nudge delivery.

    Manages background jobs for sending nudges at scheduled times
    and integrates with the nudge agent for intelligent scheduling.
    """

    def __init__(self):
        """Initialize the nudge scheduler."""
        self.scheduler = AsyncIOScheduler(
            jobstores={
                'default': MemoryJobStore()
            },
            executors={
                'default': AsyncIOExecutor()
            },
            job_defaults={
                'coalesce': True,
                'max_instances': 3,
                'misfire_grace_time': 30
            },
            timezone='UTC'
        )

        self._initialized = False
        logger.info("NudgeScheduler initialized")

    async def initialize(self) -> None:
        """
        Initialize the scheduler and add nudge jobs.

        This should be called once during application startup.
        """
        if self._initialized:
            logger.warning("NudgeScheduler already initialized")
            return

        try:
            # Add recurring nudge check job (runs every 15 minutes)
            self.scheduler.add_job(
                self._check_and_send_nudges,
                trigger=CronTrigger(minute='*/15'),  # Every 15 minutes
                id='nudge_check',
                name='Check and Send Pending Nudges',
                replace_existing=True
            )

            # Add daily nudge scheduling job (runs at 6:00 AM daily)
            self.scheduler.add_job(
                self._schedule_daily_nudges,
                trigger=CronTrigger(hour=6, minute=0),  # 6:00 AM daily
                id='daily_nudge_schedule',
                name='Schedule Daily Nudges',
                replace_existing=True
            )

            # Add weekly summary job (runs every Sunday at 6:00 PM)
            self.scheduler.add_job(
                self._send_weekly_summaries,
                trigger=CronTrigger(day_of_week=6, hour=18, minute=0),  # Sunday 6:00 PM
                id='weekly_summary',
                name='Send Weekly Progress Summaries',
                replace_existing=True
            )

            # Start the scheduler
            self.scheduler.start()
            self._initialized = True

            logger.info("NudgeScheduler started successfully")

        except Exception as e:
            logger.error(f"Failed to initialize NudgeScheduler: {e}")
            raise

    async def shutdown(self) -> None:
        """
        Shutdown the scheduler gracefully.

        This should be called during application shutdown.
        """
        if not self._initialized:
            return

        try:
            self.scheduler.shutdown(wait=True)
            self._initialized = False
            logger.info("NudgeScheduler shut down successfully")

        except Exception as e:
            logger.error(f"Error shutting down NudgeScheduler: {e}")

    async def _check_and_send_nudges(self) -> None:
        """
        Check for pending nudges and send them.

        This job runs every 15 minutes to deliver scheduled nudges.
        """
        try:
            logger.info("🔍 Checking for pending nudges...")

            # Get pending nudges from database
            pending_nudges = nudge_manager.get_pending_nudges()

            if not pending_nudges:
                logger.info("No pending nudges found")
                return

            logger.info(f"Found {len(pending_nudges)} pending nudges")

            # Send each pending nudge
            for nudge in pending_nudges:
                try:
                    await self._send_nudge(nudge)
                except Exception as e:
                    logger.error(f"Failed to send nudge {nudge.nudge_id}: {e}")
                    # Mark as failed but continue with others
                    nudge_manager.cancel_nudge(nudge.nudge_id)

        except Exception as e:
            logger.error(f"Error in nudge check job: {e}")

    async def _send_nudge(self, nudge) -> None:
        """
        Send a nudge to a user.

        Args:
            nudge: NudgeEvent object to send
        """
        try:
            logger.info(f"📤 Sending nudge {nudge.nudge_id} to user {nudge.user_id}")

            # Send message via Telegram bot
            success = await send_message_to_user(
                user_id=nudge.user_id,
                message=nudge.message,
                message_type='nudge'
            )

            if success:
                # Mark as delivered
                nudge_manager.mark_nudge_delivered(nudge.nudge_id)
                logger.info(f"✅ Nudge {nudge.nudge_id} delivered successfully")
            else:
                # Mark as failed
                nudge_manager.cancel_nudge(nudge.nudge_id)
                logger.warning(f"❌ Failed to deliver nudge {nudge.nudge_id}")

        except Exception as e:
            logger.error(f"Error sending nudge {nudge.nudge_id}: {e}")
            raise

    async def _schedule_daily_nudges(self) -> None:
        """
        Schedule daily nudges for all active users.

        This job runs daily at 6:00 AM to analyze user patterns
        and schedule personalized nudges for the day.
        """
        try:
            logger.info("📅 Scheduling daily nudges for all users...")

            # Get all active users (users with recent activity)
            from database.models import UserProfile, MealLog, WorkoutLog, WellnessLog
            from database.init import get_db_session

            cutoff_date = datetime.utcnow() - timedelta(days=30)  # Active in last 30 days

            with get_db_session() as session:
                # Find users with recent activity
                recent_meal_users = session.query(MealLog.user_id).filter(
                    MealLog.created_at >= cutoff_date
                ).distinct().all()

                recent_workout_users = session.query(WorkoutLog.user_id).filter(
                    WorkoutLog.created_at >= cutoff_date
                ).distinct().all()

                recent_wellness_users = session.query(WellnessLog.user_id).filter(
                    WellnessLog.created_at >= cutoff_date
                ).distinct().all()

                # Combine and deduplicate user IDs
                active_user_ids = set()
                for user_tuple in recent_meal_users + recent_workout_users + recent_wellness_users:
                    active_user_ids.add(user_tuple[0])

                logger.info(f"Found {len(active_user_ids)} active users for nudge scheduling")

                # Schedule nudges for each active user
                for user_id in active_user_ids:
                    try:
                        await self._schedule_user_nudges(user_id)
                    except Exception as e:
                        logger.error(f"Failed to schedule nudges for user {user_id}: {e}")

        except Exception as e:
            logger.error(f"Error in daily nudge scheduling: {e}")

    async def _schedule_user_nudges(self, user_id: str) -> None:
        """
        Schedule nudges for a specific user using the nudge agent.

        Args:
            user_id: User ID to schedule nudges for
        """
        try:
            # Use nudge agent to determine optimal nudge schedule
            from tools.nudge.scheduler import schedule_user_nudges

            result = await schedule_user_nudges(user_id=user_id)

            if result.get('status') != 'success':
                logger.warning(f"Failed to get nudge schedule for user {user_id}: {result.get('error')}")
                return

            nudges_to_schedule = result.get('nudges_to_schedule', [])

            # Create nudge events in database
            for nudge_info in nudges_to_schedule:
                try:
                    # Generate personalized message
                    from tools.nudge.generator import generate_nudge_message

                    msg_result = await generate_nudge_message(
                        user_id=user_id,
                        nudge_type=nudge_info['nudge_type']
                    )

                    if msg_result.get('status') == 'success':
                        message = msg_result['data']['message']
                    else:
                        # Fallback message
                        message = f"Time to log your progress! 💪"

                    # Schedule time from nudge info
                    scheduled_time = datetime.fromisoformat(nudge_info['scheduled_time'])

                    # Create nudge event
                    nudge_id = nudge_manager.create_nudge_event(
                        user_id=user_id,
                        nudge_type=nudge_info['nudge_type'],
                        message=message,
                        scheduled_time=scheduled_time
                    )

                    if nudge_id:
                        logger.info(f"Scheduled nudge {nudge_id} for user {user_id} at {scheduled_time}")
                    else:
                        logger.error(f"Failed to schedule nudge for user {user_id}")

                except Exception as e:
                    logger.error(f"Error scheduling individual nudge for user {user_id}: {e}")

        except Exception as e:
            logger.error(f"Error scheduling nudges for user {user_id}: {e}")

    async def _send_weekly_summaries(self) -> None:
        """
        Send weekly progress summaries to all active users.

        This job runs every Sunday at 6:00 PM.
        """
        try:
            logger.info("📊 Sending weekly progress summaries...")

            # Get active users (same logic as daily scheduling)
            from database.models import UserProfile, MealLog, WorkoutLog, WellnessLog
            from database.init import get_db_session

            cutoff_date = datetime.utcnow() - timedelta(days=7)

            with get_db_session() as session:
                recent_users = session.query(MealLog.user_id).filter(
                    MealLog.created_at >= cutoff_date
                ).distinct().all()

                active_user_ids = set(user[0] for user in recent_users)

                logger.info(f"Sending weekly summaries to {len(active_user_ids)} users")

                # Send weekly summary to each user
                for user_id in active_user_ids:
                    try:
                        await self._send_weekly_summary(user_id)
                    except Exception as e:
                        logger.error(f"Failed to send weekly summary to user {user_id}: {e}")

        except Exception as e:
            logger.error(f"Error sending weekly summaries: {e}")

    async def _send_weekly_summary(self, user_id: str) -> None:
        """
        Send a weekly progress summary to a user.

        Args:
            user_id: User ID to send summary to
        """
        try:
            # Generate weekly summary message
            from tools.nudge.generator import generate_nudge_message

            result = await generate_nudge_message(
                user_id=user_id,
                nudge_type='weekly'
            )

            if result.get('status') != 'success':
                logger.warning(f"Failed to generate weekly summary for user {user_id}")
                return

            message = result['data']['message']

            # Send via Telegram
            success = await send_message_to_user(
                user_id=user_id,
                message=message,
                message_type='weekly_summary'
            )

            if success:
                logger.info(f"Sent weekly summary to user {user_id}")
            else:
                logger.warning(f"Failed to send weekly summary to user {user_id}")

        except Exception as e:
            logger.error(f"Error sending weekly summary to user {user_id}: {e}")

    async def schedule_immediate_nudge(
        self,
        user_id: str,
        nudge_type: str,
        message: Optional[str] = None
    ) -> bool:
        """
        Schedule an immediate nudge for delivery.

        Args:
            user_id: User ID to send nudge to
            nudge_type: Type of nudge
            message: Custom message (optional)

        Returns:
            True if scheduled successfully
        """
        try:
            if not message:
                # Generate message if not provided
                from tools.nudge.generator import generate_nudge_message

                result = await generate_nudge_message(
                    user_id=user_id,
                    nudge_type=nudge_type
                )

                if result.get('status') == 'success':
                    message = result['data']['message']
                else:
                    message = "Time to log your progress! 💪"

            # Schedule for immediate delivery (1 minute from now)
            scheduled_time = datetime.utcnow() + timedelta(minutes=1)

            nudge_id = nudge_manager.create_nudge_event(
                user_id=user_id,
                nudge_type=nudge_type,
                message=message,
                scheduled_time=scheduled_time
            )

            if nudge_id:
                logger.info(f"Scheduled immediate nudge {nudge_id} for user {user_id}")
                return True
            else:
                logger.error(f"Failed to schedule immediate nudge for user {user_id}")
                return False

        except Exception as e:
            logger.error(f"Error scheduling immediate nudge: {e}")
            return False


# Create singleton instance
nudge_scheduler = NudgeScheduler()

# Convenience functions
async def initialize_nudge_scheduler() -> None:
    """Initialize the nudge scheduler."""
    await nudge_scheduler.initialize()

async def shutdown_nudge_scheduler() -> None:
    """Shutdown the nudge scheduler."""
    await nudge_scheduler.shutdown()

async def schedule_immediate_nudge(user_id: str, nudge_type: str, message: Optional[str] = None) -> bool:
    """Schedule an immediate nudge."""
    return await nudge_scheduler.schedule_immediate_nudge(user_id, nudge_type, message)

__all__ = [
    'NudgeScheduler', 'nudge_scheduler',
    'initialize_nudge_scheduler', 'shutdown_nudge_scheduler',
    'schedule_immediate_nudge'
]