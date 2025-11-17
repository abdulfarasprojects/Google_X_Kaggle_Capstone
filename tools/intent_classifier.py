"""
Intent classification tool for Weight Loss Chat Agent.

This tool analyzes user messages to determine intent for routing to appropriate agents.
"""

import logging
from typing import Dict, Any, Optional

from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


async def classify_intent(query: str, context: Optional[Dict[str, Any]] = None, tool_context: Optional[ToolContext] = None) -> Dict[str, Any]:
    """
    Classify user message intent for agent routing.

    Args:
        query: User message to classify
        context: Additional context
        tool_context: Tool context containing session information

    Returns:
        Dict with intent classification
    """
    try:
        try:
            user_id = tool_context._invocation_context.session.user_id if tool_context and hasattr(tool_context, '_invocation_context') else "unknown"
        except AttributeError:
            user_id = "unknown"
        message_lower = query.lower().strip()

        # Onboarding keywords (though this should be caught by needs_onboarding check)
        onboarding_keywords = ['start', 'begin', 'setup', 'onboard', 'profile', 'settings']
        if any(keyword in message_lower for keyword in onboarding_keywords):
            return {
                "intent": "onboarding",
                "confidence": 0.9,
                "reasoning": "Contains onboarding-related keywords"
            }

        # Nutrition keywords
        nutrition_keywords = [
            'eat', 'ate', 'food', 'meal', 'breakfast', 'lunch', 'dinner', 'snack',
            'calories', 'protein', 'nutrition', 'hungry', 'recipe', 'cook',
            'banana', 'apple', 'chicken', 'rice', 'bread', 'milk', 'eggs'  # Common foods
        ]
        if any(keyword in message_lower for keyword in nutrition_keywords):
            return {
                "intent": "nutrition",
                "confidence": 0.8,
                "reasoning": "Contains food or nutrition-related keywords"
            }

        # Fitness keywords
        fitness_keywords = [
            'workout', 'exercise', 'gym', 'lift', 'run', 'cardio', 'strength',
            'training', 'muscle', 'weight', 'sets', 'reps', 'push', 'pull',
            'squats', 'deadlift', 'bench', 'curls', 'pull-ups', 'burpees'
        ]
        if any(keyword in message_lower for keyword in fitness_keywords):
            return {
                "intent": "fitness",
                "confidence": 0.8,
                "reasoning": "Contains fitness or exercise-related keywords"
            }

        # Wellness keywords
        wellness_keywords = [
            'sleep', 'water', 'steps', 'wellness', 'tired', 'rest', 'drink',
            'walk', 'bed', 'wake', 'stress', 'mood', 'energy', 'bathroom'
        ]
        if any(keyword in message_lower for keyword in wellness_keywords):
            return {
                "intent": "wellness",
                "confidence": 0.8,
                "reasoning": "Contains wellness or health-related keywords"
            }

        # Progress/analytics keywords
        progress_keywords = [
            'progress', 'analytics', 'stats', 'summary', 'report', 'chart',
            'trend', 'weight', 'loss', 'gain', 'average', 'total', 'streak',
            'hero', 'best', 'summary', 'week', 'month'
        ]
        if any(keyword in message_lower for keyword in progress_keywords):
            return {
                "intent": "analytics",
                "confidence": 0.8,
                "reasoning": "Contains progress or analytics-related keywords"
            }

        # Help and general queries
        help_keywords = ['help', 'what', 'how', 'can you', 'commands', 'features']
        if any(keyword in message_lower for keyword in help_keywords):
            return {
                "intent": "help",
                "confidence": 0.7,
                "reasoning": "Contains help or question-related keywords"
            }

        # Default to nutrition for food-related messages
        return {
            "intent": "nutrition",
            "confidence": 0.5,
            "reasoning": "Default fallback - no specific intent detected"
        }

    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        return {
            "intent": "nutrition",
            "confidence": 0.1,
            "reasoning": f"Classification error: {str(e)}"
        }


__all__ = ['classify_intent']