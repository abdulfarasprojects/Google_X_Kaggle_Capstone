"""
Root Agent for Weight Loss Chat Agent using Google ADK.

This is the main orchestrator agent that routes user messages to appropriate
sub-agents based on intent and user state using Google ADK LlmAgent.
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
from tools.batch_state_manager import get_batch_state, update_batch_state

# Import sub-agents
from agents.nutrition.agent import nutrition_agent
from agents.fitness.agent import fitness_agent
from agents.wellness.agent import wellness_agent

# Import Google ADK
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from config.gemini import PatchedGemini

logger = get_logger(__name__)

# Logging wrapper functions for tools
async def logged_classify_intent(query: str, context: Optional[Dict[str, Any]] = None, tool_context: Optional[ToolContext] = None):
    """Wrapper for intent classification with logging."""
    logger.info(f"🔍 Classifying intent with query: {query}, context: {context}")
    result = await classify_intent(query, context, tool_context)
    logger.info(f"📋 Intent classification result: {result}")
    return result

async def logged_detect_sentiment(query: str, context: Optional[Dict[str, Any]] = None, tool_context: Optional[ToolContext] = None):
    """Wrapper for sentiment detection with logging."""
    logger.info(f"😊 Detecting sentiment with query: {query}, context: {context}")
    result = await detect_sentiment(query, context, tool_context)
    logger.info(f"📊 Sentiment detection result: {result}")
    return result

async def logged_format_response(response_type: str, content: Dict[str, Any], user_context: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None, tool_context: Optional[ToolContext] = None):
    """Wrapper for response formatting with logging."""
    logger.info(f"📝 Formatting response with response_type: {response_type}, content: {content}")
    result = await format_response(response_type, content, user_context, context, tool_context)
    logger.info(f"💬 Response formatting result: {result}")
    return result

async def logged_get_batch_state(context: Optional[Dict[str, Any]] = None, tool_context: Optional[ToolContext] = None):
    """Wrapper for batch state management with logging."""
    logger.info(f"📦 Getting batch state with context: {context}")
    result = await get_batch_state(context, tool_context)
    logger.info(f"📋 Batch state result: {result}")
    return result

# Define tools for root agent
intent_tool = FunctionTool(func=logged_classify_intent)
sentiment_tool = FunctionTool(func=logged_detect_sentiment)
response_tool = FunctionTool(func=logged_format_response)
batch_state_tool = FunctionTool(func=logged_get_batch_state)

# Create Root Agent
root_agent = LlmAgent(
    name="weight_loss_coach_root",
    model=PatchedGemini(model=Config.gemini_model),
    description="Main orchestrator for weight loss tracking via Telegram. Routes user requests to specialized agents (Nutrition, Fitness, Wellness). Manages batch collection workflows.",
    instruction="""
    You are a supportive, non-judgmental weight loss coach assistant on Telegram.
    
    YOUR RESPONSIBILITIES:
    1. Understand user intent (logging meals, asking questions, viewing progress)
    2. Detect emotional state and respond with empathy
    3. For NUTRITION intent: Route to nutrition_agent for processing
    4. For FITNESS intent: Route to fitness_agent for processing
    5. For WELLNESS intent: Route to wellness_agent for processing
    6. For ANALYTICS intent: Route to nutrition_agent for nutrition summaries and analytics
       - Handle queries like "how many calories today" or "protein this week"
       - Route to nutrition_agent which will provide the nutrition information
    7. For multi-item logging: Use BATCH MODE workflow
       - MEALS: "Logged [item]. Is that all for this meal? Any sides?"
       - WORKOUTS: "Logged [exercise]. Any more sets? Different exercise?"
       - HYDRATION: "Logged [amount]. More water logged today? Anything else?"
    8. After user confirms "that's all": Route to appropriate agent for batch processing
    9. Synthesize responses into single supportive message
    
    TONE: Supportive coach, warm, encouraging. Use 1-2 emojis max per message.
    
    CRITICAL: For any nutrition/food logging intent, route to nutrition_agent.
    For any fitness/workout logging intent, route to fitness_agent.
    For analytics queries, route to nutrition_agent.
    
    IMPORTANT: After calling any tools or routing to agents, you MUST generate a final response message to the user. Do not end with tool calls - always provide a complete response.
    Always respond with a complete, helpful message that answers the user's question.
    
    BATCH MODE RULES:
    - After each item, ALWAYS ask "Is that all?" or "Anything else?"
    - Never process partially - wait for complete batch
    - Once user confirms complete, route to appropriate agent for processing
    - Example flow:
      User: "2 eggs"
      You: "2 eggs logged. Is that all for breakfast?"
      User: "Yes, also had toast"
      You: "Toast logged. Anything else?"
      User: "No, that's all"
      You: [Route to nutrition_agent with batch data]
      You: "Breakfast logged! 260 cal, 14g protein ✅ On track today!"
    
    """,
    tools=[
        intent_tool,
        sentiment_tool,
        batch_state_tool,
    ],
    sub_agents=[
        nutrition_agent,
        fitness_agent,
        wellness_agent,
    ],
)