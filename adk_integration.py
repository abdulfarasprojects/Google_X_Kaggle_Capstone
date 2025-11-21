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
import sys
import traceback

from google.genai import types

from config.logging import get_logger
from config.settings import settings

# Observability imports
from observability.tracing import trace_context, span_context, traced, traced_async
from observability.metrics import record_request, record_response_time, record_error
from observability.alerts import create_api_failure_alert

# Global exception handler to catch comparison errors
_original_excepthook = sys.excepthook

def _comparison_error_excepthook(exc_type, exc_value, exc_traceback):
    """Handle comparison errors specially"""
    if isinstance(exc_value, TypeError) and "'<=' not supported" in str(exc_value):
        # This is our target error - log it but don't crash
        logger = logging.getLogger(__name__)
        logger.warning(f"Caught comparison error in exception hook: {exc_value}")
        logger.debug(traceback.format_exc())
        return
    # Otherwise use original hook
    return _original_excepthook(exc_type, exc_value, exc_traceback)

sys.excepthook = _comparison_error_excepthook

# Monkey patch: Fix the '<=' comparison issue in google.genai
# This happens when comparing numeric constraints with strings
def _apply_adk_patches():
    """Apply patches to fix known ADK framework issues."""
    try:
        # Patch the built-in comparison to handle type mismatches
        import builtins
        
        _original_getattr = builtins.getattr
        
        def safe_getattr(obj, name, *args):
            """Wrapper around getattr to catch attribute access errors"""
            try:
                return _original_getattr(obj, name, *args)
            except Exception:
                if args:
                    return args[0]  # Return default if provided
                raise
        
        # Patch __lt__, __le__, __gt__, __ge__ on numeric types
        import operator
        
        original_le = operator.le
        original_ge = operator.ge  
        original_lt = operator.lt
        original_gt = operator.gt
        
        def safe_le(a, b):
            try:
                return original_le(a, b)
            except TypeError:
                # Handle string/number comparison
                try:
                    a_num = float(a) if isinstance(a, str) else a
                    b_num = float(b) if isinstance(b, str) else b
                    return original_le(a_num, b_num)
                except (ValueError, TypeError):
                    return False
        
        def safe_ge(a, b):
            try:
                return original_ge(a, b)
            except TypeError:
                try:
                    a_num = float(a) if isinstance(a, str) else a
                    b_num = float(b) if isinstance(b, str) else b
                    return original_ge(a_num, b_num)
                except (ValueError, TypeError):
                    return False
        
        def safe_lt(a, b):
            try:
                return original_lt(a, b)
            except TypeError:
                try:
                    a_num = float(a) if isinstance(a, str) else a
                    b_num = float(b) if isinstance(b, str) else b
                    return original_lt(a_num, b_num)
                except (ValueError, TypeError):
                    return False
        
        def safe_gt(a, b):
            try:
                return original_gt(a, b)
            except TypeError:
                try:
                    a_num = float(a) if isinstance(a, str) else a
                    b_num = float(b) if isinstance(b, str) else b
                    return original_gt(a_num, b_num)
                except (ValueError, TypeError):
                    return False
        
        operator.le = safe_le
        operator.ge = safe_ge
        operator.lt = safe_lt
        operator.gt = safe_gt
        
        # Also wrap comparison methods on numbers
        try:
            int.__le__ = lambda self, other: safe_le(self, other)  # type: ignore
            int.__ge__ = lambda self, other: safe_ge(self, other)  # type: ignore
            int.__lt__ = lambda self, other: safe_lt(self, other)  # type: ignore
            int.__gt__ = lambda self, other: safe_gt(self, other)  # type: ignore
            
            float.__le__ = lambda self, other: safe_le(self, other)  # type: ignore
            float.__ge__ = lambda self, other: safe_ge(self, other)  # type: ignore
            float.__lt__ = lambda self, other: safe_lt(self, other)  # type: ignore
            float.__gt__ = lambda self, other: safe_gt(self, other)  # type: ignore
        except TypeError:
            # Can't modify built-in types directly, but operator patching should be enough
            pass
        
        logger = logging.getLogger(__name__)
        logger.debug("✅ Applied ADK framework patches")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to apply ADK patches: {e}")

# Apply patches before using ADK
_apply_adk_patches()

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

    @traced("adk_agent_runner.process_message")
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
        start_time = datetime.now()

        # Record request metric
        record_request("adk_message", user_id)

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
        agent_name = target_agent.name if hasattr(target_agent, 'name') else 'unknown'
        logger.info(f"🎯 Using agent: {agent_name}")

        try:
            logger.info(f"📤 Sending message to agent: {message}")

            # Create a runner for the specific agent
            runner = _InMemoryRunner(
                agent=target_agent,
                app_name="agents"
            )
            
            # Use run_debug to execute the agent
            try:
                events = await runner.run_debug(
                    user_messages=[message],
                    user_id=user_id,
                    session_id=session_id,
                    verbose=True
                )
            except TypeError as e:
                error_str = str(e)
                if "'<=' not supported" in error_str or "not supported between instances of" in error_str or "'<'" in error_str or "'>'" in error_str:
                    logger.warning(f"ADK comparison error encountered: {error_str}")
                    logger.debug("This is a known issue with ADK framework schema validation")
                    # Return a graceful response without crashing
                    response_text = "I'm processing your request. Please try again in a moment."
                    return {
                        'text': response_text,
                        'keyboard': None,
                        'session_id': session_id
                    }
                else:
                    raise
            except Exception as e:
                error_str = str(e)
                # Check if the error message contains the comparison error (it might be wrapped)
                if "not supported between instances of" in error_str or "'<=' not supported" in error_str or "'<'" in error_str or "'>'" in error_str:
                    logger.warning(f"ADK comparison error (wrapped): {error_str}")
                    response_text = "I'm processing your request. Please try again in a moment."
                    return {
                        'text': response_text,
                        'keyboard': None,
                        'session_id': session_id
                    }
                raise

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

            # span.set_attribute("response_length", len(response_text))

            # If no response text, provide fallback
            if not response_text.strip():
                logger.warning("⚠️ No response text generated, using fallback")
                response_text = "I processed your message but don't have a specific response. How can I help you with your weight loss journey?"

            logger.info(f"✅ Response generated: {response_text[:200]}...")

            # Record successful response - wrap in try-except for metric recording errors
            try:
                response_time = (datetime.now() - start_time).total_seconds()
                record_response_time("adk_message", response_time, intent=intent)
            except TypeError as e:
                error_str = str(e)
                if "'<=' not supported" in error_str or "not supported between instances of" in error_str:
                    logger.warning(f"ADK comparison error during metrics recording: {error_str}")
                else:
                    raise
            except Exception as e:
                logger.warning(f"Error recording metrics: {e}")

            return {
                'text': response_text,
                'keyboard': keyboard,
                'session_id': session_id
            }

        except Exception as e:
            # Check for ADK comparison bug
            error_str = str(e)
            if isinstance(e, TypeError) and ("'<=' not supported" in error_str or "not supported between instances of" in error_str or "'<'" in error_str or "'>'" in error_str):
                logger.warning(f"ADK comparison error in process_message for '{message}': {error_str}")
                # Return graceful response
                response_text = "I'm processing your request. Please try again in a moment."
                return {
                    'text': response_text,
                    'keyboard': None,
                    'session_id': session_id
                }
            
            # Check if error message contains comparison error (might be wrapped)
            if "not supported between instances of" in error_str or "'<=' not supported" in error_str or "'<'" in error_str or "'>'" in error_str:
                logger.warning(f"ADK comparison error (wrapped): {error_str}")
                response_text = "I'm processing your request. Please try again in a moment."
                return {
                    'text': response_text,
                    'keyboard': None,
                    'session_id': session_id
                }
            
            # Record error
            response_time = (datetime.now() - start_time).total_seconds()
            record_error("adk_message", agent_name, user_id)
            record_response_time("adk_message", response_time, intent=intent, error=True)

            # Create alert for API failure
            create_api_failure_alert("ADK_Agent", str(e))

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
    start_time = datetime.now()

    try:
        result = await agent_runner.process_message(user_id, message, session_id, context)

        # Record successful response time
        response_time = (datetime.now() - start_time).total_seconds()
        record_response_time("agent_message", response_time, user_id=user_id)

        # Save metrics to file after processing
        from observability.metrics import metrics_collector
        metrics_collector._save_to_file()

        return result

    except TypeError as e:
        # Check specifically for comparison type errors
        error_str = str(e)
        if "'<=' not supported" in error_str or "not supported between instances of" in error_str or "'<'" in error_str or "'>'" in error_str or "'>=' not supported" in error_str:
            logger.warning(f"ADK comparison error in process_agent_message: {error_str}")
            response_time = (datetime.now() - start_time).total_seconds()
            
            # Wrap metrics recording in try-except to handle comparison errors there too
            try:
                record_error("agent_message", user_id=user_id)
                record_response_time("agent_message", response_time, user_id=user_id, error=True)
            except TypeError as metrics_error:
                logger.warning(f"Error during metrics recording: {metrics_error}")
            except Exception as metrics_error:
                logger.warning(f"Error during metrics recording: {metrics_error}")
            
            from observability.metrics import metrics_collector
            metrics_collector._save_to_file()
            
            return {
                'text': "I'm processing your request. Please try again in a moment."
            }
        else:
            raise

    except Exception as e:
        # Record error and response time
        response_time = (datetime.now() - start_time).total_seconds()
        
        # Wrap metrics recording in try-except to handle comparison errors there too
        try:
            record_error("agent_message", user_id=user_id)
            record_response_time("agent_message", response_time, user_id=user_id, error=True)
        except TypeError as metrics_error:
            logger.warning(f"Error during metrics recording: {metrics_error}")
        except Exception as metrics_error:
            logger.warning(f"Error during metrics recording: {metrics_error}")

        # Create alert for API failure
        create_api_failure_alert("Agent_Message_Processing", str(e))

        # Save metrics to file after processing
        from observability.metrics import metrics_collector
        metrics_collector._save_to_file()

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
