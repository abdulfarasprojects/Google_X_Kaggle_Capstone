"""
ADK Integration Layer for Weight Loss Chat Agent.

This module provides the integration layer between the Telegram bot and
Google ADK agents. It uses the ADK Runner framework to properly execute
agents and handle their responses.

Key features:
- ADK Runner integration for agent execution
- Async message processing with proper event handling
- Session management for conversation continuity
- Error handling and logging
- Response formatting for Telegram
"""

import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime

from google.genai import types

from config.logging import get_logger
from config.settings import settings

logger = get_logger(__name__)

# Lazy-loaded globals
_InMemoryRunner = None
_InMemorySessionService = None
_root_agent = None
_nutrition_agent = None
_ADK_LOADED = False


def _lazy_load_adk() -> bool:
    """Lazy load ADK components to avoid import-time hangs."""
    global _InMemoryRunner, _InMemorySessionService, _root_agent, _nutrition_agent, _ADK_LOADED

    if _ADK_LOADED:
        return True

    try:
        logger.debug("Lazy-loading ADK components...")
        from google.adk.runners import InMemoryRunner
        from google.adk.sessions import InMemorySessionService
        from agents.root.agent import root_agent
        from agents.nutrition.agent import nutrition_agent

        _InMemoryRunner = InMemoryRunner
        _InMemorySessionService = InMemorySessionService
        _root_agent = root_agent
        _nutrition_agent = nutrition_agent
        _ADK_LOADED = True
        logger.debug("✅ ADK components loaded successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to lazy-load ADK components: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


class ADKAgentRunner:
    """
    ADK Agent Runner for executing agents with proper session management.

    This class manages the ADK Runner lifecycle and provides methods to
    execute agents asynchronously with proper event handling.
    """

    def __init__(self):
        """Initialize the ADK agent runner."""
        self.runner = None
        self.session_service = None
        self._initialized = False

    async def initialize(self):
        """Initialize the ADK runner with agents."""
        if self._initialized:
            return

        logger.info("Initializing ADK Runner...")

        if not _lazy_load_adk():
            raise ImportError("Failed to load ADK components")

        try:
            # Create runner with root agent
            self.session_service = _InMemorySessionService()
            self.runner = _InMemoryRunner(
                agent=_root_agent,
                app_name="agents"  # Match the agent's directory
            )

            logger.info("✅ ADK Runner initialized successfully")
            self._initialized = True

        except Exception as e:
            logger.error(f"❌ Failed to initialize ADK Runner: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def _classify_intent(self, message: str) -> str:
        """Classify user message intent based on keywords."""
        message_lower = message.lower()
        
        # Nutrition keywords
        if any(word in message_lower for word in ['ate', 'food', 'meal', 'breakfast', 'lunch', 'dinner', 'snack', 'calories', 'protein', 'hungry']):
            return 'nutrition'
        
        # Fitness keywords
        if any(word in message_lower for word in ['workout', 'exercise', 'gym', 'lift', 'run', 'cardio', 'sets', 'reps', 'weight', 'strength']):
            return 'fitness'
        
        # Wellness keywords
        if any(word in message_lower for word in ['sleep', 'water', 'steps', 'wellness', 'tired', 'rest', 'drink', 'walk']):
            return 'wellness'
        
        # Analytics keywords
        if any(word in message_lower for word in ['progress', 'stats', 'summary', 'report', 'trend', 'weekly', 'daily']):
            return 'analytics'
        
        # Default to root
        return 'root'
    
    def _get_agent_for_intent(self, intent: str):
        """Get the appropriate agent for the given intent."""
        if intent == 'nutrition':
            return _nutrition_agent
        elif intent == 'fitness':
            from agents.fitness.agent import fitness_agent
            return fitness_agent
        elif intent == 'wellness':
            from agents.wellness.agent import wellness_agent
            return wellness_agent
        elif intent == 'analytics':
            from agents.analytics.agent import analytics_agent
            return analytics_agent
        else:
            return _root_agent

    async def process_message(
        self,
        user_id: str,
        message: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a message using the ADK agent framework.

        Args:
            user_id: User identifier
            message: User message text
            session_id: Optional session ID (generated if not provided)
            context: Optional context data

        Returns:
            Dict with 'text' and optional 'keyboard' fields
        """
        if not self._initialized:
            await self.initialize()

        # Generate session ID if not provided
        if not session_id:
            session_id = f"session_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"Processing message for user {user_id}, session {session_id}: {message[:100]}...")
        
        # Classify intent and route to appropriate agent
        intent = self._classify_intent(message)
        logger.info(f"📌 Classified intent: {intent}")
        
        # Get agent for this intent
        target_agent = self._get_agent_for_intent(intent)
        logger.info(f"🎯 Using agent: {target_agent.name if hasattr(target_agent, 'name') else 'unknown'}")

        try:
            logger.info(f"📤 Sending message to agent: {message}")

            # Create a runner for the specific agent
            runner = _InMemoryRunner(
                agent=target_agent,
                app_name="agents"
            )
            
            # Use run_debug to execute the agent
            events = await runner.run_debug(
                user_messages=[message],
                user_id=user_id,
                session_id=session_id,
                verbose=True
            )

            logger.info(f"📊 Total events received: {len(events)}")

            # Process events to extract response
            response_text = ""
            keyboard = None

            for event in events:
                logger.debug(f"🔍 Processing event type: {type(event).__name__}")

                if hasattr(event, 'content') and event.content and event.content.parts:
                    # Extract text from content
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text is not None:
                            response_text += part.text
                            logger.info(f"💬 Extracted text: {part.text[:100]}...")

                # Handle tool calls and other events
                if hasattr(event, 'tool_call') and event.tool_call:
                    logger.info(f"🔧 Tool call detected: {event.tool_call}")

                # Handle function calls
                if hasattr(event, 'function_call') and event.function_call:
                    logger.info(f"⚙️ Function call detected: {event.function_call}")

            # If no response text, provide fallback
            if not response_text.strip():
                logger.warning("⚠️ No response text generated, using fallback")
                response_text = "I processed your message but don't have a specific response. How can I help you with your weight loss journey?"

            logger.info(f"✅ Response generated: {response_text[:200]}...")

            return {
                'text': response_text,
                'keyboard': keyboard,
                'session_id': session_id
            }

        except Exception as e:
            logger.error(f"❌ Error processing message: {e}", exc_info=True)
            return {
                'text': "❌ Sorry, I encountered an error. Please try again.",
                'session_id': session_id
            }

    async def get_session_history(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session history for debugging.

        Args:
            user_id: User identifier
            session_id: Session identifier

        Returns:
            Session data if found
        """
        try:
            # This would require access to session data
            # For now, return None as InMemorySessionService doesn't expose this easily
            return None
        except Exception as e:
            logger.error(f"Error getting session history: {e}")
            return None

    async def close(self):
        """Close the runner and cleanup resources."""
        if self.runner:
            await self.runner.close()
            self._initialized = False
            logger.info("ADK Runner closed")


# Global runner instance
agent_runner = ADKAgentRunner()


async def process_agent_message(
    user_id: str,
    message: str,
    session_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Process a message using the ADK agent framework.

    This is the main entry point for the Telegram bot integration.

    Args:
        user_id: User identifier
        message: User message text
        session_id: Optional session ID
        context: Optional context data

    Returns:
        Dict with response data
    """
    try:
        return await agent_runner.process_message(user_id, message, session_id, context)
    except Exception as e:
        logger.error(f"Error in process_agent_message: {e}", exc_info=True)
        return {
            'text': "❌ Sorry, I encountered an error. Please try again."
        }


async def initialize_agent_runner():
    """Initialize the global agent runner."""
    await agent_runner.initialize()


async def shutdown_agent_runner():
    """Shutdown the global agent runner."""
    await agent_runner.close()


# Export functions for easy import
__all__ = [
    'ADKAgentRunner',
    'agent_runner',
    'process_agent_message',
    'initialize_agent_runner',
    'shutdown_agent_runner'
]
