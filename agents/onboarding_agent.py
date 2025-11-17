"""
Onboarding Agent for Weight Loss Chat Agent.

This agent handles the complete user onboarding process including:
- Initial greeting and consent
- Profile data collection (age, height, weight, goals)
- Activity level assessment
- Calorie goal calculation and validation
- Profile creation and storage

The onboarding flow is conversational and guides users through
setting up their weight loss profile step by step.
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from agents.base import BaseAgent, AgentResponse, BaseTool
from database.models import UserProfile
from database.init import get_db_session
from tools.profile_validator import validate_user_input, suggest_calorie_goal
from config.logging import get_logger

logger = get_logger(__name__)


class OnboardingTool(BaseTool):
    """Tool for onboarding-specific operations."""

    def __init__(self):
        super().__init__(
            name="onboarding_assistance",
            description="Handle onboarding workflow steps and profile creation"
        )

    async def execute(self, action: str, **kwargs) -> Any:
        """Execute onboarding tool actions."""
        if action == "validate_profile":
            return await validate_user_input(
                kwargs.get("profile_data", {}),
                "profile",
                kwargs.get("existing_profile")
            )
        elif action == "suggest_calorie_goal":
            profile_data = kwargs.get("profile_data", {})
            return await suggest_calorie_goal(
                weight_kg=profile_data.get("weight_kg"),
                height_cm=profile_data.get("height_cm"),
                age=profile_data.get("age"),
                activity_level=profile_data.get("activity_level")
            )
        elif action == "create_profile":
            return await self._create_user_profile(kwargs.get("profile_data", {}))
        else:
            return {"error": f"Unknown action: {action}"}

    async def _create_user_profile(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create user profile in database."""
        try:
            with get_db_session() as session:
                # Check if profile already exists
                existing = session.query(UserProfile).filter_by(
                    user_id=profile_data["user_id"]
                ).first()

                if existing:
                    # Update existing profile
                    for key, value in profile_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                    session.commit()
                    return {"status": "updated", "user_id": profile_data["user_id"]}
                else:
                    # Create new profile
                    profile = UserProfile(**profile_data)
                    session.add(profile)
                    session.commit()
                    return {"status": "created", "user_id": profile_data["user_id"]}

        except Exception as e:
            logger.error(f"Profile creation failed: {e}")
            return {"error": str(e)}


class OnboardingAgent(BaseAgent):
    """
    Agent responsible for user onboarding and profile setup.

    Manages the conversational flow for collecting user information
    and creating their weight loss profile.
    """

    def __init__(self):
        tools = [OnboardingTool()]
        super().__init__(
            name="onboarding_agent",
            description="Handle user onboarding and profile creation",
            tools=tools
        )

        # Onboarding conversation states
        self.states = {
            "greeting": self._handle_greeting,
            "consent": self._handle_consent,
            "age": self._handle_age,
            "height": self._handle_height,
            "weight": self._handle_weight,
            "target_weight": self._handle_target_weight,
            "activity_level": self._handle_activity_level,
            "review_profile": self._handle_review_profile,
            "complete": self._handle_complete
        }

    async def process_message(self, user_id: str, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """
        Process onboarding message based on current state.

        Args:
            user_id: User identifier
            message: User message
            context: Additional context

        Returns:
            AgentResponse: Formatted response
        """
        try:
            # Get current onboarding state
            state = await self._get_onboarding_state(user_id)

            # Handle message based on state
            handler = self.states.get(state, self._handle_greeting)
            response = await handler(user_id, message, context)

            return response

        except Exception as e:
            logger.error(f"Onboarding processing failed: {e}")
            return AgentResponse(
                text="I'm sorry, I encountered an error during onboarding. Let's start over. Type 'start' to begin.",
                completed=False
            )

    async def _get_onboarding_state(self, user_id: str) -> str:
        """Get current onboarding state for user."""
        # Check if user already has a complete profile
        with get_db_session() as session:
            profile = session.query(UserProfile).filter_by(user_id=user_id).first()
            if profile:
                return "complete"

        # Get session data for onboarding progress
        session_data = await self._get_session_data(user_id)
        if session_data and "onboarding_state" in session_data:
            return session_data["onboarding_state"]

        # Default to greeting for new users
        return "greeting"

    async def _set_onboarding_state(self, user_id: str, state: str, profile_data: Optional[Dict[str, Any]] = None) -> None:
        """Update onboarding state and profile data."""
        session_data = await self._get_session_data(user_id) or {}
        session_data["onboarding_state"] = state

        if profile_data:
            session_data["profile_data"] = profile_data

        await self._update_session_data(user_id, session_data)

    async def _handle_greeting(self, user_id: str, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Handle initial greeting and start onboarding."""
        greeting_text = (
            "👋 Welcome to your Weight Loss Assistant!\n\n"
            "I'm here to help you track your nutrition, fitness, and wellness "
            "to reach your weight loss goals.\n\n"
            "To get started, I'll need to learn a bit about you. This will help me "
            "provide personalized recommendations.\n\n"
            "Ready to begin? Reply with 'yes' or 'start' to continue."
        )

        # Initialize onboarding session
        await self._set_onboarding_state(user_id, "consent")

        return AgentResponse(
            text=greeting_text,
            completed=False
        )

    async def _handle_consent(self, user_id: str, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Handle user consent for data collection."""
        message_lower = message.lower().strip()

        if message_lower in ['yes', 'start', 'begin', 'ok', 'sure', 'y']:
            consent_text = (
                "Great! Let's get you set up. 📝\n\n"
                "First, I'll ask a few questions about your age, height, weight, and activity level. "
                "This information helps me calculate your daily calorie needs.\n\n"
                "All your data stays private and local to your device. I never share it with anyone.\n\n"
                "How old are you? (Please enter a number between 18-100)"
            )

            await self._set_onboarding_state(user_id, "age")
            return AgentResponse(text=consent_text, completed=False)

        elif message_lower in ['no', 'stop', 'cancel', 'quit', 'n']:
            return AgentResponse(
                text="No problem! When you're ready to start tracking, just type 'start' or 'begin'.",
                completed=True
            )

        else:
            return AgentResponse(
                text="Please reply with 'yes' to start onboarding, or 'no' if you'd like to skip for now.",
                completed=False
            )

    async def _handle_age(self, user_id: str, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Handle age input and validation."""
        try:
            age = int(message.strip())

            # Validate age
            validation = await validate_user_input({"age": age}, "profile")
            if not validation["data"]["is_valid"]:
                error_msg = "; ".join(validation["data"]["errors"])
                return AgentResponse(
                    text=f"Sorry, {error_msg}. Please enter your age as a number between 18-100.",
                    completed=False
                )

            # Store age and move to next step
            profile_data = {"user_id": user_id, "age": age}
            await self._set_onboarding_state(user_id, "height", profile_data)

            return AgentResponse(
                text="Thanks! Now, what's your height in centimeters? (e.g., 170)",
                completed=False
            )

        except ValueError:
            return AgentResponse(
                text="Please enter your age as a number (e.g., 25).",
                completed=False
            )

    async def _handle_height(self, user_id: str, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Handle height input and validation."""
        try:
            height = float(message.strip())

            # Get current profile data
            session_data = await self._get_session_data(user_id)
            profile_data = session_data.get("profile_data", {})
            profile_data["height_cm"] = height

            # Validate height
            validation = await validate_user_input({"height_cm": height}, "profile")
            if not validation["data"]["is_valid"]:
                error_msg = "; ".join(validation["data"]["errors"])
                return AgentResponse(
                    text=f"Sorry, {error_msg}. Please enter your height in centimeters (100-250).",
                    completed=False
                )

            # Store height and move to next step
            await self._set_onboarding_state(user_id, "weight", profile_data)

            return AgentResponse(
                text="Perfect! Now, what's your current weight in kilograms? (e.g., 75.5)",
                completed=False
            )

        except ValueError:
            return AgentResponse(
                text="Please enter your height as a number in centimeters (e.g., 170).",
                completed=False
            )

    async def _handle_weight(self, user_id: str, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Handle current weight input and validation."""
        try:
            weight = float(message.strip())

            # Get current profile data
            session_data = await self._get_session_data(user_id)
            profile_data = session_data.get("profile_data", {})
            profile_data["weight_kg"] = weight

            # Validate weight
            validation = await validate_user_input({"weight_kg": weight}, "profile")
            if not validation["data"]["is_valid"]:
                error_msg = "; ".join(validation["data"]["errors"])
                return AgentResponse(
                    text=f"Sorry, {error_msg}. Please enter your weight in kilograms (30-300).",
                    completed=False
                )

            # Store weight and move to next step
            await self._set_onboarding_state(user_id, "target_weight", profile_data)

            return AgentResponse(
                text="Great! Now, what's your target weight in kilograms? (This should be less than your current weight)",
                completed=False
            )

        except ValueError:
            return AgentResponse(
                text="Please enter your weight as a number in kilograms (e.g., 75.5).",
                completed=False
            )

    async def _handle_target_weight(self, user_id: str, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Handle target weight input and validation."""
        try:
            target_weight = float(message.strip())

            # Get current profile data
            session_data = await self._get_session_data(user_id)
            profile_data = session_data.get("profile_data", {})
            profile_data["target_weight_kg"] = target_weight

            # Validate target weight against current weight
            validation = await validate_user_input({
                "weight_kg": profile_data.get("weight_kg"),
                "target_weight_kg": target_weight
            }, "profile")

            if not validation["data"]["is_valid"]:
                error_msg = "; ".join(validation["data"]["errors"])
                return AgentResponse(
                    text=f"Sorry, {error_msg}. Your target weight must be less than your current weight.",
                    completed=False
                )

            # Store target weight and move to next step
            await self._set_onboarding_state(user_id, "activity_level", profile_data)

            activity_options = (
                "Finally, what's your typical activity level?\n\n"
                "Choose the option that best describes you:\n\n"
                "• **sedentary**: Little to no exercise, desk job\n"
                "• **light**: Light exercise 1-3 days/week\n"
                "• **moderate**: Moderate exercise 3-5 days/week\n"
                "• **active**: Hard exercise 6-7 days/week\n"
                "• **very_active**: Very hard exercise, physical job, or 2x training\n\n"
                "Reply with one of: sedentary, light, moderate, active, very_active"
            )

            return AgentResponse(text=activity_options, completed=False)

        except ValueError:
            return AgentResponse(
                text="Please enter your target weight as a number in kilograms (e.g., 70.0).",
                completed=False
            )

    async def _handle_activity_level(self, user_id: str, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Handle activity level selection."""
        valid_levels = ['sedentary', 'light', 'moderate', 'active', 'very_active']
        activity_input = message.lower().strip()

        if activity_input not in valid_levels:
            return AgentResponse(
                text=f"Please choose one of the valid options: {', '.join(valid_levels)}",
                completed=False
            )

        # Get current profile data
        session_data = await self._get_session_data(user_id)
        profile_data = session_data.get("profile_data", {})
        profile_data["activity_level"] = activity_input

        # Calculate suggested calorie goal
        suggestion = await suggest_calorie_goal(
            weight_kg=profile_data.get("weight_kg"),
            height_cm=profile_data.get("height_cm"),
            age=profile_data.get("age"),
            activity_level=activity_input
        )

        if suggestion["status"] == "success":
            suggested_calories = suggestion["data"]["suggested_calories"]
            profile_data["daily_calorie_goal"] = suggested_calories

            review_text = (
                f"Perfect! Based on your information, I suggest a daily calorie goal of **{suggested_calories} calories**.\n\n"
                "This creates a safe deficit for weight loss while considering your activity level.\n\n"
                "Here's a summary of your profile:\n\n"
                f"• Age: {profile_data.get('age')} years\n"
                f"• Height: {profile_data.get('height_cm')} cm\n"
                f"• Current Weight: {profile_data.get('weight_kg')} kg\n"
                f"• Target Weight: {profile_data.get('target_weight_kg')} kg\n"
                f"• Activity Level: {activity_input}\n"
                f"• Daily Calories: {suggested_calories}\n\n"
                "Does this look correct? Reply 'yes' to save your profile, or 'no' to make changes."
            )
        else:
            # Fallback if calculation fails
            profile_data["daily_calorie_goal"] = 1800  # Safe default
            review_text = (
                "I've set a default calorie goal of 1800 calories. We can adjust this later.\n\n"
                "Here's your profile summary:\n\n"
                f"• Age: {profile_data.get('age')} years\n"
                f"• Height: {profile_data.get('height_cm')} cm\n"
                f"• Current Weight: {profile_data.get('weight_kg')} kg\n"
                f"• Target Weight: {profile_data.get('target_weight_kg')} kg\n"
                f"• Activity Level: {activity_input}\n"
                f"• Daily Calories: 1800\n\n"
                "Does this look correct? Reply 'yes' to save your profile, or 'no' to make changes."
            )

        await self._set_onboarding_state(user_id, "review_profile", profile_data)

        return AgentResponse(text=review_text, completed=False)

    async def _handle_review_profile(self, user_id: str, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Handle profile review and confirmation."""
        message_lower = message.lower().strip()

        if message_lower in ['yes', 'correct', 'save', 'ok', 'y']:
            # Get profile data and create profile
            session_data = await self._get_session_data(user_id)
            profile_data = session_data.get("profile_data", {})

            # Add timezone (default to UTC, can be updated later)
            profile_data["timezone"] = "UTC"

            # Create profile using tool
            tool = self._get_tool_by_name("onboarding_assistance")
            result = await tool.execute_with_timeout(action="create_profile", profile_data=profile_data)

            if result.success and result.data.get("status") in ["created", "updated"]:
                # Mark onboarding as complete
                await self._set_onboarding_state(user_id, "complete")

                completion_text = (
                    "🎉 **Welcome aboard! Your profile has been created successfully.**\n\n"
                    "You're all set to start tracking your weight loss journey. Here's what you can do:\n\n"
                    "• **Log meals**: Tell me what you ate (e.g., 'I had scrambled eggs and toast')\n"
                    "• **Track workouts**: Share your exercise sessions\n"
                    "• **Log wellness**: Record sleep, water, and steps\n"
                    "• **View progress**: Ask for summaries and trends\n\n"
                    "Try starting with: 'I ate breakfast - 2 eggs, toast, and coffee'\n\n"
                    "Remember: I'm here to guide and track, but you control your journey. "
                    "Stay consistent and be patient with yourself! 💪"
                )

                return AgentResponse(text=completion_text, completed=True)
            else:
                return AgentResponse(
                    text="Sorry, I had trouble saving your profile. Please try again or contact support.",
                    completed=False
                )

        elif message_lower in ['no', 'change', 'edit', 'wrong', 'n']:
            # Restart onboarding
            await self._set_onboarding_state(user_id, "age")
            return AgentResponse(
                text="No problem! Let's update your information. How old are you?",
                completed=False
            )

        else:
            return AgentResponse(
                text="Please reply with 'yes' to save your profile, or 'no' to make changes.",
                completed=False
            )

    async def _handle_complete(self, user_id: str, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Handle messages when onboarding is already complete."""
        return AgentResponse(
            text="Your profile is already set up! Ready to log something? Try telling me about your meals, workouts, or wellness.",
            completed=True
        )


# Create global instance
onboarding_agent = OnboardingAgent()

# Export for use in other modules
__all__ = ['OnboardingAgent', 'onboarding_agent']