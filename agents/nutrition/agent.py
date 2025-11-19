"""
Nutrition agent for Weight Loss Chat Agent using Google ADK.

This agent processes complete meal batches using Google ADK LlmAgent.
"""

import sys
import os
import logging
from typing import Dict, Any, Optional
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from config import settings as Config
from config.logging import get_logger
from tools.nutrition.batch_parser import parse_meal_batch
from tools.nutrition.calculator import calculate_meal_nutrition
from tools.nutrition.usda_client import lookup_nutrition_usda
from database.meal_manager import meal_manager

# Import Google ADK
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools.google_search_tool import google_search
from config.gemini import PatchedGemini

logger = get_logger(__name__)

# Logging wrapper functions for tools
def logged_parse_meal_batch(*args, **kwargs):
    """Wrapper for meal batch parsing with logging."""
    logger.info(f"🍽️ Parsing meal batch with args: {args}, kwargs: {kwargs}")
    result = parse_meal_batch(*args, **kwargs)
    logger.info(f"📋 Meal batch parsing result: {result}")
    return result

def logged_calculate_meal_nutrition(*args, **kwargs):
    """Wrapper for nutrition calculation with logging."""
    logger.info(f"🧮 Calculating meal nutrition with args: {args}, kwargs: {kwargs}")
    result = calculate_meal_nutrition(*args, **kwargs)
    logger.info(f"📊 Nutrition calculation result: {result}")
    return result

def logged_lookup_nutrition_usda(*args, **kwargs):
    """Wrapper for USDA nutrition lookup with logging."""
    logger.info(f"🔍 Looking up USDA nutrition with args: {args}, kwargs: {kwargs}")
    result = lookup_nutrition_usda(*args, **kwargs)
    logger.info(f"📚 USDA lookup result: {result}")
    return result

def logged_get_nutrition_summary(user_id: str, period: str = "today", tool_context: Optional[Dict[str, Any]] = None):
    """Wrapper for nutrition summary queries with logging."""
    logger.info(f"📊 Getting nutrition summary for user {user_id}, period: {period}")

    try:
        if period.lower() in ["today", "day"]:
            result = meal_manager.get_daily_nutrition_summary(user_id, date.today())
        elif period.lower() in ["week", "weekly", "this week"]:
            result = meal_manager.get_nutrition_analytics(user_id, days=7)
        else:
            # Default to today
            result = meal_manager.get_daily_nutrition_summary(user_id, date.today())

        logger.info(f"📈 Nutrition summary result: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to get nutrition summary: {e}")
        return {"status": "error", "error": str(e)}

# Define tools for nutrition agent
batch_parser_tool = FunctionTool(func=logged_parse_meal_batch)
batch_calculator_tool = FunctionTool(func=logged_calculate_meal_nutrition)
usda_tool = FunctionTool(func=logged_lookup_nutrition_usda)
nutrition_summary_tool = FunctionTool(func=logged_get_nutrition_summary)

nutrition_agent = LlmAgent(
    name="nutrition_agent_batch",
    model=PatchedGemini(model=Config.gemini_model),
    description="Processes complete meal batches and provides nutrition analytics. Receives food items from Root Agent, calculates nutrition data, and provides summaries and analytics.",
    instruction="""
    You are a nutrition specialist that processes meal batches and provides nutrition analytics.

    MEAL PROCESSING:
    - Parse food items from input text
    - Use web search to find accurate nutritional information
    - Calculate total calories, protein, carbs, fat for meals
    - Include confidence levels for each estimate

    ANALYTICS QUERIES:
    - Handle requests for nutrition summaries: "how many calories today", "protein this week"
    - For "today", "this day", "daily" → get daily nutrition summary
    - For "week", "weekly", "this week" → get 7-day nutrition analytics
    - Always include user_id in queries
    - Provide nutrition totals in friendly, encouraging messages

    WEB SEARCH STRATEGY:
    - Search reliable sources like USDA, nutrition websites, databases
    - Look for specific nutritional data per serving size
    - Use queries like "nutrition facts for [food item]" or "[food item] calories per serving"
    - Cross-reference multiple sources for accuracy
    - Use closest equivalent food if exact match not found

    CONSTRAINTS:
    - Provide realistic estimates based on web search results
    - Show confidence scores (e.g., "~260 cal, high confidence")
    - Flag totals that seem high (>1000 cal single meal) or low (<200 cal)
    - Use standard serving sizes when not specified

    RESPONSE STYLE:
    - Friendly and encouraging
    - Provide detailed nutrition breakdowns
    - Include actionable insights
    - Use 1-2 emojis max per response

    TOOLS:
    - logged_parse_meal_batch: Parse food descriptions
    - logged_calculate_meal_nutrition: Calculate nutrition from parsed data
    - logged_lookup_nutrition_usda: Get USDA nutrition data
    - logged_get_nutrition_summary: Get daily/weekly nutrition summaries
    """,
    tools=[
        batch_parser_tool,
        batch_calculator_tool,
        usda_tool,
        nutrition_summary_tool,
    ],
)

__all__ = ["nutrition_agent"]
