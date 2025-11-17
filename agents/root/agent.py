"""
Root Agent for Weight Loss Chat Agent.

This is the main orchestrator agent that routes user messages to appropriate
sub-agents based on intent and user state. It handles:

- User onboarding state checking
- Intent analysis and routing
- Session management across agents
- Fallback responses for unrecognized inputs

The root agent ensures users complete onboarding before accessing other features.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from agents.base import BaseAgent, AgentResponse
from agents.onboarding_agent import onboarding_agent
from database.models import UserProfile
from database.init import get_db_session
from config.logging import get_logger

logger = get_logger(__name__)


class RootAgent(BaseAgent):
    """
    Main orchestrator agent for the weight loss chat system.

    Routes messages to appropriate sub-agents and manages overall conversation flow.
    """

    def __init__(self):
        super().__init__(
            name="root_agent",
            description="Main orchestrator for weight loss chat system"
        )

        # Register sub-agents (will be expanded as more agents are implemented)
        self.sub_agents = {
            "onboarding": onboarding_agent,
            # Future agents will be registered here:
            # "nutrition": nutrition_agent,
            # "fitness": fitness_agent,
            # "wellness": wellness_agent,
            # "analytics": analytics_agent,
            # "nudge": nudge_agent
        }

    async def process_message(self, user_id: str, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """
        Process user message and route to appropriate agent.

        Args:
            user_id: User identifier
            message: User message
            context: Additional context

        Returns:
            AgentResponse: Response from appropriate agent
        """
        try:
            # Check if user needs onboarding
            if await self._user_needs_onboarding(user_id):
                logger.info(f"Routing user {user_id} to onboarding")
                return await onboarding_agent.process_message(user_id, message, context)

            # Analyze message intent
            intent = await self._analyze_intent(user_id, message)

            # Route to appropriate sub-agent
            if intent in self.sub_agents:
                agent = self.sub_agents[intent]
                logger.info(f"Routing user {user_id} to {intent} agent")
                return await agent.process_message(user_id, message, context)

            # Handle general queries or unknown intents
            return await self._handle_general_query(user_id, message, context)

        except Exception as e:
            logger.error(f"Root agent processing failed for user {user_id}: {e}")
            return AgentResponse(
                text="I'm sorry, I encountered an error. Please try again or contact support if the problem persists.",
                completed=True
            )

    async def _user_needs_onboarding(self, user_id: str) -> bool:
        """
        Check if user needs to complete onboarding.

        Args:
            user_id: User identifier

        Returns:
            True if user needs onboarding, False otherwise
        """
        try:
            with get_db_session() as session:
                profile = session.query(UserProfile).filter_by(user_id=user_id).first()
                return profile is None
        except Exception as e:
            logger.error(f"Error checking onboarding status for user {user_id}: {e}")
            # Default to requiring onboarding on error
            return True

    async def _analyze_intent(self, user_id: str, message: str) -> str:
        """
        Analyze user message to determine intent.

        This is a simple keyword-based analysis. Could be enhanced with ML classification.

        Args:
            user_id: User identifier
            message: User message

        Returns:
            Intent string (e.g., 'nutrition', 'fitness', 'wellness', 'analytics')
        """
        message_lower = message.lower().strip()

        # Onboarding keywords (though this should be caught by needs_onboarding check)
        onboarding_keywords = ['start', 'begin', 'setup', 'onboard', 'profile', 'settings']
        if any(keyword in message_lower for keyword in onboarding_keywords):
            return "onboarding"

        # Nutrition keywords
        nutrition_keywords = [
            'eat', 'ate', 'food', 'meal', 'breakfast', 'lunch', 'dinner', 'snack',
            'calories', 'protein', 'nutrition', 'hungry', 'recipe', 'cook',
            'banana', 'apple', 'chicken', 'rice', 'bread', 'milk', 'eggs'  # Common foods
        ]
        if any(keyword in message_lower for keyword in nutrition_keywords):
            return "nutrition"

        # Fitness keywords
        fitness_keywords = [
            'workout', 'exercise', 'gym', 'lift', 'run', 'cardio', 'strength',
            'training', 'muscle', 'weight', 'sets', 'reps', 'push', 'pull',
            'squats', 'deadlift', 'bench', 'curls', 'pull-ups', 'burpees'
        ]
        if any(keyword in message_lower for keyword in fitness_keywords):
            return "fitness"

        # Wellness keywords
        wellness_keywords = [
            'sleep', 'water', 'steps', 'wellness', 'tired', 'rest', 'drink',
            'walk', 'bed', 'wake', 'stress', 'mood', 'energy', 'bathroom'
        ]
        if any(keyword in message_lower for keyword in wellness_keywords):
            return "wellness"

        # Progress/analytics keywords
        progress_keywords = [
            'progress', 'analytics', 'stats', 'summary', 'report', 'chart',
            'trend', 'weight', 'loss', 'gain', 'average', 'total', 'streak',
            'hero', 'best', 'summary', 'week', 'month'
        ]
        if any(keyword in message_lower for keyword in progress_keywords):
            return "analytics"

        # Help and general queries
        help_keywords = ['help', 'what', 'how', 'can you', 'commands', 'features']
        if any(keyword in message_lower for keyword in help_keywords):
            return "help"

        # Default to nutrition for food-related messages
        # This is a simple fallback - could be improved with better intent classification
        return "nutrition"

    async def _handle_general_query(self, user_id: str, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """
        Handle general queries that don't match specific intents.

        Args:
            user_id: User identifier
            message: User message
            context: Additional context

        Returns:
            General response
        """
        message_lower = message.lower().strip()

        # Greeting responses
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']):
            greeting = self._get_time_based_greeting()
            response_text = (
                f"{greeting} I'm your weight loss assistant! 👋\n\n"
                "I'm here to help you track your nutrition, fitness, and wellness. "
                "What would you like to do today?\n\n"
                "• Tell me about your meals (e.g., 'I ate scrambled eggs and toast')\n"
                "• Share your workouts (e.g., 'I did 3 sets of squats')\n"
                "• Log wellness data (e.g., 'I slept 8 hours and drank 6 glasses of water')\n"
                "• Check your progress (e.g., 'Show me my weekly summary')\n\n"
                "Just type what you want to track!"
            )
            return AgentResponse(text=response_text, completed=True)

        # Gratitude responses
        if any(word in message_lower for word in ['thank', 'thanks', 'appreciate', 'grateful']):
            return AgentResponse(
                text="You're welcome! I'm here to support your weight loss journey. Keep up the great work! 💪",
                completed=True
            )

        # Unknown intent - provide helpful guidance
        response_text = (
            "I'm not sure what you mean, but I'm here to help with your weight loss tracking! 🎯\n\n"
            "Try telling me about:\n\n"
            "• **Meals**: 'I ate chicken salad with rice'\n"
            "• **Workouts**: 'I did 45 minutes of cardio'\n"
            "• **Wellness**: 'I slept 7 hours and walked 8000 steps'\n"
            "• **Progress**: 'Show me my progress this week'\n\n"
            "What would you like to track?"
        )
        return AgentResponse(text=response_text, completed=True)

    def _get_time_based_greeting(self) -> str:
        """Get appropriate greeting based on current time."""
        current_hour = datetime.utcnow().hour

        if 5 <= current_hour < 12:
            return "Good morning! 🌅"
        elif 12 <= current_hour < 17:
            return "Good afternoon! ☀️"
        elif 17 <= current_hour < 22:
            return "Good evening! 🌆"
        else:
            return "Hello! 🌙"


# Create global instance
root_agent = RootAgent()

# Export for use in other modules
__all__ = ['RootAgent', 'root_agent']