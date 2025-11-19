"""
Fitness agent for Weight Loss Chat Agent using Google ADK.

This agent processes complete workout batches using Google ADK LlmAgent.
"""

import sys
import os
import logging
from typing import Dict, Any, Optional
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from config import settings as Config
from config.logging import get_logger
from tools.fitness.batch_parser import parse_workout_batch
from tools.fitness.calculator import calculate_workout_volume
from tools.fitness.progress import suggest_workout_progression
from database.workout_manager import workout_manager

# Import Google ADK
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from config.gemini import PatchedGemini

logger = get_logger(__name__)

# Logging wrapper functions for tools
def logged_parse_workout_batch(*args, **kwargs):
    """Wrapper for workout batch parsing with logging."""
    logger.info(f"🏋️ Parsing workout batch with args: {args}, kwargs: {kwargs}")
    result = parse_workout_batch(*args, **kwargs)
    logger.info(f"📋 Workout batch parsing result: {result}")
    return result

def logged_calculate_workout_volume(*args, **kwargs):
    """Wrapper for volume calculation with logging."""
    logger.info(f"📊 Calculating workout volume with args: {args}, kwargs: {kwargs}")
    result = calculate_workout_volume(*args, **kwargs)
    logger.info(f"💪 Volume calculation result: {result}")
    return result

def logged_suggest_workout_progression(*args, **kwargs):
    """Wrapper for progression suggestions with logging."""
    logger.info(f"📈 Generating progression suggestions with args: {args}, kwargs: {kwargs}")
    result = suggest_workout_progression(*args, **kwargs)
    logger.info(f"🎯 Progression suggestions result: {result}")
    return result

def logged_get_workout_summary(user_id: str, period: str = "today", tool_context: Optional[Dict[str, Any]] = None):
    """Wrapper for workout summary queries with logging."""
    logger.info(f"📊 Getting workout summary for user {user_id}, period: {period}")
    
    try:
        if period.lower() in ["today", "day"]:
            result = workout_manager.get_daily_workout_summary(user_id, date.today())
        elif period.lower() in ["week", "weekly", "this week"]:
            result = workout_manager.get_workout_analytics(user_id, days=7)
        else:
            # Default to today
            result = workout_manager.get_daily_workout_summary(user_id, date.today())
            
        logger.info(f"📈 Workout summary result: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to get workout summary: {e}")
        return {"status": "error", "error": str(e)}

# Define tools for fitness agent
batch_parser_tool = FunctionTool(func=logged_parse_workout_batch)
volume_calculator_tool = FunctionTool(func=logged_calculate_workout_volume)
progression_tool = FunctionTool(func=logged_suggest_workout_progression)
workout_summary_tool = FunctionTool(func=logged_get_workout_summary)

fitness_agent = LlmAgent(
    name="fitness_agent_batch",
    model=PatchedGemini(model=Config.gemini_model),
    description="Fitness coach that helps users log workouts and provides workout analytics. Collects exercise data in conversations, processes complete sessions, and provides workout summaries and progress tracking.",
    instruction="""
    You are a friendly fitness coach helping users track their workouts and view their progress.

    CONVERSATION FLOW:
    1. When user says "workout" or similar, acknowledge and start collecting: "Great! Let's log your workout. What exercises did you do?"
    2. Ask for exercise details in natural way: "What exercises did you do?"
    3. For each exercise mentioned, confirm and ask for more: "Got it! Any other exercises?"
    4. Continue until user says "done", "finished", "that's all", "no more", etc.
    5. Then process the complete workout using your tools

    IMPORTANT: "workout" by itself is NOT a complete workout. It just means they want to start logging.

    ANALYTICS QUERIES:
    - Handle requests for workout summaries: "how many workouts this week", "my exercise progress"
    - For "today", "this day", "daily" → get daily workout summary
    - For "week", "weekly", "this week" → get 7-day workout analytics
    - Always include user_id in queries
    - Provide workout summaries in friendly, encouraging messages

    EXERCISE PARSING:
    - Accept natural descriptions: "squats 3 sets of 10 reps at 185 pounds"
    - Parse automatically using parse_workout_batch tool
    - Handle multiple exercises in one message
    - Ask for clarification if needed

    BATCH PROCESSING:
    - Only call tools when you have a complete workout (user indicates they're done)
    - Call tools in sequence: parse → calculate volume → suggest progression
    - Provide encouraging summary with volume, feedback, and next suggestions

    TOOLS: Only call when ready to process complete workout or for analytics
    - parse_workout_batch: Convert exercise descriptions to structured data
    - calculate_workout_volume: Get total volume and metrics
    - suggest_workout_progression: Personalized improvement recommendations
    - logged_get_workout_summary: Get daily/weekly workout summaries and analytics

    RESPONSE STYLE:
    - Friendly and encouraging
    - Ask questions to continue collection
    - Provide detailed summary only when workout is complete
    - Use emojis sparingly (1-2 per response)

    COMPLETION SIGNALS: "done", "finished", "that's all", "no more", "complete", "finished workout"

    CRITICAL: Never call tools when user just says "workout". Always respond with questions to collect exercise data first.
    """,
    tools=[
        batch_parser_tool,
        volume_calculator_tool,
        progression_tool,
        workout_summary_tool,
    ],
)

__all__ = ["fitness_agent"]