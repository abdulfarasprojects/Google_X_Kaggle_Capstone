"""
Nudge message generation tools for personalized reminders.

This module provides tools for generating contextual, encouraging nudge messages
based on user activity patterns and nudge types.
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from tools.base import BaseTool, ToolResult
from database.models import get_db, UserProfile, MealLog, WorkoutLog, WellnessLog
from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class NudgeMessage:
    """Generated nudge message with metadata."""
    message: str
    nudge_type: str
    tone: str  # 'encouraging', 'gentle', 'celebratory', 'urgent'
    personalization: Dict[str, Any]


class NudgeMessageGeneratorTool(BaseTool):
    """
    Tool for generating personalized nudge messages.

    Creates contextual, encouraging messages based on user activity patterns
    and the specific type of nudge being sent.
    """

    def __init__(self):
        super().__init__(
            name="generate_nudge_message",
            description="Generate personalized nudge message based on user context and nudge type",
            parameters={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to generate message for"
                    },
                    "nudge_type": {
                        "type": "string",
                        "enum": ["morning", "midday", "evening", "streak_protection", "weekly"],
                        "description": "Type of nudge to generate"
                    },
                    "context_data": {
                        "type": "object",
                        "description": "Additional context data for personalization"
                    }
                },
                "required": ["user_id", "nudge_type"]
            }
        )

    async def execute(
        self,
        user_id: str,
        nudge_type: str,
        context_data: Optional[Dict[str, Any]] = None,
        tool_context: Optional[Any] = None
    ) -> ToolResult:
        """
        Generate a personalized nudge message.

        Args:
            user_id: User ID for personalization
            nudge_type: Type of nudge ('morning', 'midday', 'evening', 'streak_protection', 'weekly')
            context_data: Additional context for message generation
            tool_context: ADK tool context

        Returns:
            ToolResult with generated message
        """
        try:
            context_data = context_data or {}

            db = get_db()
            try:
                # Get user profile for personalization
                user = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
                if not user:
                    return ToolResult(
                        success=False,
                        error=f"User not found: {user_id}"
                    )

                # Get recent activity for context
                activity_context = await self._get_activity_context(db, user)

                # Generate message based on type
                nudge_message = self._generate_message(nudge_type, user, activity_context, context_data)

                return ToolResult(
                    success=True,
                    data={
                        "user_id": user_id,
                        "nudge_type": nudge_type,
                        "message": nudge_message.message,
                        "tone": nudge_message.tone,
                        "personalization": nudge_message.personalization
                    }
                )

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Nudge message generation failed: {e}")
            return ToolResult(
                success=False,
                error=f"Nudge message generation failed: {str(e)}"
            )

    async def _get_activity_context(self, db, user: UserProfile) -> Dict[str, Any]:
        """
        Get recent activity context for message personalization.

        Args:
            db: Database session
            user: User profile

        Returns:
            Dict with activity context
        """
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)

        # Recent activity counts
        recent_meals = db.query(MealLog).filter(
            MealLog.user_id == user.user_id,
            MealLog.created_at >= week_ago
        ).count()

        recent_workouts = db.query(WorkoutLog).filter(
            WorkoutLog.user_id == user.user_id,
            WorkoutLog.created_at >= week_ago
        ).count()

        recent_wellness = db.query(WellnessLog).filter(
            WellnessLog.user_id == user.user_id,
            WellnessLog.created_at >= week_ago
        ).count()

        # Yesterday's activity
        yesterday_meals = db.query(MealLog).filter(
            MealLog.user_id == user.user_id,
            MealLog.log_date == yesterday.date()
        ).count()

        yesterday_workouts = db.query(WorkoutLog).filter(
            WorkoutLog.user_id == user.user_id,
            WorkoutLog.log_date == yesterday.date()
        ).count()

        # Calculate current streak
        streak = self._calculate_streak(db, user, now)

        return {
            "recent_meals": recent_meals,
            "recent_workouts": recent_workouts,
            "recent_wellness": recent_wellness,
            "yesterday_meals": yesterday_meals,
            "yesterday_workouts": yesterday_workouts,
            "current_streak": streak,
            "total_weekly_activity": recent_meals + recent_workouts + recent_wellness
        }

    def _calculate_streak(self, db, user: UserProfile, current_time: datetime) -> int:
        """Calculate current logging streak."""
        from datetime import timedelta

        streak = 0
        check_date = current_time.date()

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

    def _generate_message(
        self,
        nudge_type: str,
        user: UserProfile,
        activity: Dict[str, Any],
        context_data: Dict[str, Any]
    ) -> NudgeMessage:
        """
        Generate nudge message based on type and context.

        Args:
            nudge_type: Type of nudge
            user: User profile
            activity: Activity context
            context_data: Additional context

        Returns:
            NudgeMessage with generated content
        """
        personalization = {
            "user_name": f"there",  # Could be enhanced with actual name if available
            "streak_days": activity["current_streak"],
            "recent_activity": activity["total_weekly_activity"]
        }

        if nudge_type == "morning":
            return self._generate_morning_nudge(activity, personalization)

        elif nudge_type == "midday":
            return self._generate_midday_nudge(activity, personalization)

        elif nudge_type == "evening":
            return self._generate_evening_nudge(activity, personalization)

        elif nudge_type == "streak_protection":
            return self._generate_streak_protection_nudge(activity, personalization)

        elif nudge_type == "weekly":
            return self._generate_weekly_nudge(activity, personalization)

        else:
            # Fallback
            return NudgeMessage(
                message="Time to log your progress! Every step counts toward your goals. 💪",
                nudge_type=nudge_type,
                tone="encouraging",
                personalization=personalization
            )

    def _generate_morning_nudge(self, activity: Dict[str, Any], personalization: Dict[str, Any]) -> NudgeMessage:
        """Generate morning nudge for users who missed yesterday."""
        messages = [
            "Good morning! Yesterday was quiet - ready to start fresh today? Your body will thank you! 🌅",
            "Morning! Let's kickstart your day with some healthy choices. What's for breakfast? 🍳",
            "Good morning! A great day starts with great habits. Ready to log your first meal? 🌞",
            "Rise and shine! Your journey to better health continues today. What's your plan? 💪"
        ]

        if activity["current_streak"] > 0:
            messages.append(f"Good morning! Don't break your {activity['current_streak']}-day streak - let's keep it going! 🔥")

        message = random.choice(messages)

        return NudgeMessage(
            message=message,
            nudge_type="morning",
            tone="encouraging",
            personalization=personalization
        )

    def _generate_midday_nudge(self, activity: Dict[str, Any], personalization: Dict[str, Any]) -> NudgeMessage:
        """Generate midday positive reinforcement."""
        messages = [
            "Great job staying on track today! Keep up the excellent work! 🌟",
            "Midday check-in: You're doing amazing! How's your energy levels? 💪",
            "Halfway through the day and you're crushing it! What's next on your healthy agenda? 🎯",
            "You're making great progress today! Remember, consistency is key. Keep going! 🚀"
        ]

        if activity["recent_activity"] > 5:
            messages.append("Wow, you've been really active lately! That's fantastic progress! 🌟")

        message = random.choice(messages)

        return NudgeMessage(
            message=message,
            nudge_type="midday",
            tone="celebratory",
            personalization=personalization
        )

    def _generate_evening_nudge(self, activity: Dict[str, Any], personalization: Dict[str, Any]) -> NudgeMessage:
        """Generate evening check-in reminder."""
        messages = [
            "Evening check-in: How did your healthy choices go today? Let's wrap up strong! 🌆",
            "As the day winds down, let's make sure we've logged everything. Your future self will thank you! 📝",
            "Evening reminder: A quick log now saves time tomorrow. What's left to record? 🌙",
            "End of day check: You're doing great! Let's finish strong with a complete log. 💫"
        ]

        message = random.choice(messages)

        return NudgeMessage(
            message=message,
            nudge_type="evening",
            tone="gentle",
            personalization=personalization
        )

    def _generate_streak_protection_nudge(self, activity: Dict[str, Any], personalization: Dict[str, Any]) -> NudgeMessage:
        """Generate urgent streak protection reminder."""
        streak = activity["current_streak"]

        messages = [
            f"⏰ Last chance! Don't break your {streak}-day streak - log something quick before midnight! 🔥",
            f"⚠️ Streak alert! Your {streak} days of consistency are on the line. Quick log before it's too late! 💪",
            f"🚨 Streak protection mode! {streak} days strong - don't let it end tonight. Log now! 🛡️",
            f"⏳ Time is running out on your {streak}-day streak! A quick entry now keeps the momentum going! ⚡"
        ]

        message = random.choice(messages)

        return NudgeMessage(
            message=message,
            nudge_type="streak_protection",
            tone="urgent",
            personalization=personalization
        )

    def _generate_weekly_nudge(self, activity: Dict[str, Any], personalization: Dict[str, Any]) -> NudgeMessage:
        """Generate weekly progress summary."""
        total_activity = activity["total_weekly_activity"]

        if total_activity > 20:
            message = f"🌟 Amazing week! You logged {total_activity} activities - that's dedication! Here's to another great week! 🎉"
        elif total_activity > 10:
            message = f"👍 Solid week with {total_activity} logged activities! You're building great habits. Keep it up! 💪"
        else:
            message = f"📊 Weekly recap: {total_activity} activities logged. Every step counts - let's build on this momentum! 🌱"

        return NudgeMessage(
            message=message,
            nudge_type="weekly",
            tone="celebratory",
            personalization=personalization
        )


# Create singleton instance
nudge_generator = NudgeMessageGeneratorTool()


# Convenience function for direct use
async def generate_nudge_message(
    user_id: str,
    nudge_type: str,
    context_data: Optional[Dict[str, Any]] = None,
    tool_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Generate a personalized nudge message.

    Args:
        user_id: User ID for personalization
        nudge_type: Type of nudge to generate
        context_data: Additional context data
        tool_context: Optional ADK tool context

    Returns:
        Dict with status, data, error
    """
    result = await nudge_generator.execute(
        user_id=user_id,
        nudge_type=nudge_type,
        context_data=context_data,
        tool_context=tool_context
    )

    return {
        "status": "success" if result.success else "error",
        "data": result.data,
        "error": result.error
    }


__all__ = ['NudgeMessageGeneratorTool', 'nudge_generator', 'generate_nudge_message']