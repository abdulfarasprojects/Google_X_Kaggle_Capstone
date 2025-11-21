"""
Root Agent (Coordinator) for Weight Loss Chat Agent using Google ADK.

This is the main orchestrator agent that routes user messages to appropriate
sub-agents based on intent using Google ADK's agent transfer capability.

PATTERN: Coordinator/Dispatcher Pattern with LLM-Driven Delegation
- Receives user messages
- Classifies intent
- Delegates to appropriate sub-agent using transfer_to_agent()
- Sub-agents handle domain-specific operations
- Root agent manages cross-domain operations (profile, sessions)
"""

import sys
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from config import settings as Config
from config.logging import get_logger
from tools.intent_classifier import classify_intent
from tools.sentiment_detector import detect_sentiment
from tools.response_formatter import format_response

# Observability imports
from observability.tracing import traced
from observability.metrics import record_request, record_response_time, record_error

# Note: Sub-agents are NOT imported here to avoid circular imports and initialization delays
# Routing is now done at the ADK integration layer instead of using agent transfers

# Import Google ADK
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from config.gemini import PatchedGemini

logger = get_logger(__name__)

# Logging wrapper functions for coordinator tools
async def logged_classify_intent(query: str, context: Optional[Dict[str, Any]] = None, tool_context: Optional[ToolContext] = None):
    """Wrapper for intent classification with logging."""
    logger.info(f"Classifying intent with query: {query}")
    result = await classify_intent(query, context, tool_context)
    logger.info(f"Intent classification result: {result}")
    return result

async def logged_detect_sentiment(query: str, context: Optional[Dict[str, Any]] = None, tool_context: Optional[ToolContext] = None):
    """Wrapper for sentiment detection with logging."""
    logger.info(f"Detecting sentiment with query: {query}")
    result = await detect_sentiment(query, context, tool_context)
    logger.info(f"Sentiment detection result: {result}")
    return result

async def logged_format_response(response_type: str, content: Dict[str, Any], user_context: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None, tool_context: Optional[ToolContext] = None):
    """Wrapper for response formatting with logging."""
    logger.info(f"Formatting response with response_type: {response_type}")
    result = await format_response(response_type, content, user_context, context, tool_context)
    logger.info(f"Response formatting result: {result}")
    return result

# Define tools for coordinator agent (MINIMAL)
intent_tool = FunctionTool(func=logged_classify_intent)
sentiment_tool = FunctionTool(func=logged_detect_sentiment)
response_tool = FunctionTool(func=logged_format_response)

# Create Root Agent (Coordinator/Orchestrator)
root_agent = LlmAgent(
    name="weight_loss_coach_root",
    model=PatchedGemini(model=Config.gemini_model),
    description="Coordinator for weight loss tracking via Telegram. Routes user requests to specialized agents (Nutrition, Fitness, Wellness, Analytics, Nudge).",
    instruction="""
    You are a supportive, non-judgmental weight loss coach assistant on Telegram serving as the main coordinator.
    
    YOUR ROLE: General Assistant & Fallback Handler
    - You handle general conversation with the user
    - You provide supportive, encouraging responses
    - You serve as fallback for ambiguous or non-domain-specific requests
    
    YOUR RESPONSIBILITIES:
    1. Provide supportive, warm responses to user messages
    2. Detect emotional state and respond with empathy
    3. For domain-specific requests (meals, workouts, sleep, etc.), acknowledge that
       the specialized agent will handle it
    4. Manage cross-domain concerns like sessions and user state
    
    AGENT ROUTING (Handled by system):
    This agent is called for:
    - Meal/food/calorie questions → nutrition_agent processes
    - Workout/exercise questions → fitness_agent processes
    - Water/sleep/steps → wellness_agent processes
    - Weekly/daily summaries → analytics_agent processes
    - General questions → root_agent (this agent)
    - Nudges/reminders → nudge_agent (future)
    
    INTENT CLASSIFICATION:
    - NUTRITION: "ate", "food", "meal", "breakfast", "lunch", "dinner", "snack", "calories", "protein", "hungry", "recipe"
    - FITNESS: "workout", "exercise", "gym", "lift", "run", "cardio", "strength", "training", "muscle", "sets", "reps"
    - WELLNESS: "sleep", "water", "steps", "wellness", "tired", "rest", "drink", "walk", "bed", "wake", "stress"
    - ANALYTICS: "progress", "stats", "summary", "report", "how am I doing", "trend", "weekly", "daily"
    
    EXAMPLE RESPONSES:
    User: "I had 2 eggs for breakfast"
    → Your response: "Great! That's being logged by our nutrition specialist. You're taking good care of yourself! 💪"
    
    User: "did 3 sets of squats at 185 pounds"
    → Your response: "Awesome strength work! That's impressive. Our fitness specialist is recording this. Keep it up! 🏋️"
    
    User: "how am I doing this week?"
    → Your response: "Let me get your weekly summary from our analytics specialist..."
    
    TOOLS YOU CAN USE DIRECTLY:
    - detect_sentiment: Understand user's emotional state
    - format_response: Format responses for Telegram
    - classify_intent: Analyze user message intent (informational only)
    
    CRITICAL RULES:
    - Be supportive and encouraging in all responses
    - DO NOT try to process meals, workouts, sleep, or analytics directly
    - Acknowledge that appropriate specialists will handle domain-specific requests
    - Keep responses concise and warm
    - Use 1-2 emojis max per message
    
    TONE: Supportive coach, warm, encouraging, empathetic.
    """,
    tools=[
        intent_tool,
        sentiment_tool,
        response_tool,
    ],
)
