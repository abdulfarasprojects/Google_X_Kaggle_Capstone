"""
Sentiment detection tool for Weight Loss Chat Agent.

This tool analyzes user messages to detect emotional state for empathetic responses.
"""

import logging
import re
from typing import Dict, Any, Optional

from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


async def detect_sentiment(query: str, context: Optional[Dict[str, Any]] = None, tool_context: Optional[ToolContext] = None) -> Dict[str, Any]:
    """
    Detect sentiment and emotional state in user message.

    Args:
        query: User message to analyze
        context: Additional context
        tool_context: Tool context containing session information

    Returns:
        Dict with sentiment analysis
    """
    try:
        try:
            user_id = tool_context._invocation_context.session.user_id if tool_context and hasattr(tool_context, '_invocation_context') else "unknown"
        except AttributeError:
            user_id = "unknown"
        message_lower = query.lower().strip()

        # Positive indicators
        positive_words = [
            'great', 'awesome', 'excellent', 'amazing', 'fantastic', 'wonderful',
            'good', 'nice', 'love', 'like', 'enjoy', 'happy', 'excited', 'proud',
            'success', 'achieved', 'crushed', 'nailed', 'killed', 'smashed'
        ]

        # Negative indicators
        negative_words = [
            'bad', 'terrible', 'awful', 'horrible', 'hate', 'dislike', 'sad',
            'frustrated', 'angry', 'upset', 'disappointed', 'failed', 'struggling',
            'hard', 'difficult', 'tough', 'stressed', 'worried', 'anxious'
        ]

        # Neutral/question indicators
        neutral_words = [
            'what', 'how', 'when', 'where', 'why', 'can', 'could', 'would',
            'should', 'help', 'question', 'confused', 'unsure'
        ]

        # Count sentiment indicators
        positive_count = sum(1 for word in positive_words if word in message_lower)
        negative_count = sum(1 for word in negative_words if word in message_lower)
        neutral_count = sum(1 for word in neutral_words if word in message_lower)

        # Determine dominant sentiment
        if positive_count > negative_count and positive_count > neutral_count:
            sentiment = "positive"
            confidence = min(0.9, positive_count * 0.2)
        elif negative_count > positive_count and negative_count > neutral_count:
            sentiment = "negative"
            confidence = min(0.9, negative_count * 0.2)
        elif neutral_count > 0:
            sentiment = "neutral"
            confidence = min(0.7, neutral_count * 0.15)
        else:
            sentiment = "neutral"
            confidence = 0.5

        # Check for exclamation marks (enthusiasm)
        exclamation_count = query.count('!')
        if exclamation_count > 0:
            confidence = min(1.0, confidence + 0.1 * exclamation_count)

        # Check for question marks (curiosity/uncertainty)
        question_count = query.count('?')
        if question_count > 0 and sentiment == "neutral":
            confidence = min(0.8, confidence + 0.1 * question_count)

        # Determine emotional state
        emotional_state = "neutral"
        if sentiment == "positive":
            if "proud" in message_lower or "achieved" in message_lower:
                emotional_state = "accomplished"
            elif "excited" in message_lower or "love" in message_lower:
                emotional_state = "enthusiastic"
            else:
                emotional_state = "positive"
        elif sentiment == "negative":
            if "frustrated" in message_lower or "struggling" in message_lower:
                emotional_state = "frustrated"
            elif "worried" in message_lower or "anxious" in message_lower:
                emotional_state = "concerned"
            else:
                emotional_state = "negative"

        return {
            "sentiment": sentiment,
            "emotional_state": emotional_state,
            "confidence": confidence,
            "indicators": {
                "positive_words": positive_count,
                "negative_words": negative_count,
                "neutral_words": neutral_count,
                "exclamation_marks": exclamation_count,
                "question_marks": question_count
            }
        }

    except Exception as e:
        logger.error(f"Sentiment detection failed: {e}")
        return {
            "sentiment": "neutral",
            "emotional_state": "neutral",
            "confidence": 0.1,
            "error": str(e)
        }


__all__ = ['detect_sentiment']