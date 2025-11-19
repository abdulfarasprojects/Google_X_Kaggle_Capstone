"""
Nutrition agent for Weight Loss Chat Agent using Google ADK.

This agent processes complete meal batches using Google ADK LlmAgent.
"""

import sys
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from config import settings as Config
from config.logging import get_logger
from tools.nutrition.batch_parser import parse_meal_batch
from tools.nutrition.calculator import calculate_meal_nutrition
from tools.nutrition.usda_client import lookup_nutrition_usda
from tools.nutrition.manual_entry import process_manual_calorie_entry
from tools.nutrition.meal_storage import store_meal_log
from database.meal_manager import meal_manager

# Import Google ADK
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools.google_search_tool import google_search
from config.gemini import PatchedGemini

logger = get_logger(__name__)

# Logging wrapper functions for tools
async def logged_parse_meal_batch(food_items: str, meal_type: str, user_id: str, tool_context=None):
    """Wrapper for meal batch parsing with logging."""
    # Convert comma-separated string to list if needed
    if isinstance(food_items, str):
        food_items = [item.strip() for item in food_items.split(',') if item.strip()]
    
    logger.info(f"🍽️ Parsing meal batch: {food_items}, meal_type: {meal_type}, user_id: {user_id}")
    result = await parse_meal_batch(food_items, meal_type, user_id, tool_context)
    logger.info(f"📋 Meal batch parsing result: {result}")
    return result

async def logged_calculate_meal_nutrition(parsed_items, meal_type, user_id, tool_context=None):
    """Wrapper for nutrition calculation with logging."""
    logger.info(f"🧮 Calculating meal nutrition: {len(parsed_items)} items, meal_type: {meal_type}, user_id: {user_id}")
    result = await calculate_meal_nutrition(parsed_items, meal_type, user_id, tool_context)
    logger.info(f"📊 Nutrition calculation result: {result}")
    return result

async def logged_lookup_nutrition_usda(*args, **kwargs):
    """Wrapper for USDA nutrition lookup with logging."""
    logger.info(f"🔍 Looking up USDA nutrition with args: {args}, kwargs: {kwargs}")
    result = await lookup_nutrition_usda(*args, **kwargs)
    logger.info(f"📚 USDA lookup result: {result}")
    return result

async def logged_get_nutrition_summary(user_id: str, period: str = "today", tool_context: Optional[Dict[str, Any]] = None):
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

async def logged_process_manual_calorie_entry(text: str, context: Optional[Dict[str, Any]] = None, tool_context: Optional[Dict[str, Any]] = None):
    """Wrapper for manual calorie entry processing with logging."""
    logger.info(f"📝 Processing manual calorie entry with text: {text}, context: {context}")
    result = process_manual_calorie_entry(text, context)
    logger.info(f"✅ Manual entry processing result: {result}")
    return result

async def logged_store_meal_log(user_id: str, meal_type: str, food_items: List[Dict[str, Any]], total_calories: float, total_protein_g: float, confidence_score: float, tool_context: Optional[Dict[str, Any]] = None):
    """Wrapper for meal storage with logging."""
    logger.info(f"💾 Storing meal log for user {user_id}: {meal_type}, {total_calories} cal, {len(food_items)} items")
    result = await store_meal_log(user_id, meal_type, food_items, total_calories, total_protein_g, confidence_score, tool_context)
    logger.info(f"✅ Meal storage result: {result}")
    return result

# Define tools for nutrition agent
batch_parser_tool = FunctionTool(func=logged_parse_meal_batch)
batch_calculator_tool = FunctionTool(func=logged_calculate_meal_nutrition)
usda_tool = FunctionTool(func=logged_lookup_nutrition_usda)
nutrition_summary_tool = FunctionTool(func=logged_get_nutrition_summary)
manual_entry_tool = FunctionTool(func=logged_process_manual_calorie_entry)
meal_storage_tool = FunctionTool(func=logged_store_meal_log)

nutrition_agent = LlmAgent(
    name="nutrition_agent_batch",
    model=PatchedGemini(model=Config.gemini_model),
    description="Processes individual meal messages and provides nutrition analytics. Receives food items from Root Agent, calculates nutrition data, and provides summaries and analytics.",
    instruction="""
    You are a nutrition specialist that processes individual meal messages and provides nutrition analytics.

    MEAL PROCESSING:
    - Parse food items from input text
    - Use web search to find accurate nutritional information
    - Calculate total calories, protein, carbs, fat for meals
    - Store the calculated meal in the database using store_meal_log
    - Include confidence levels for each estimate

    MANUAL CALORIE ENTRY:
    - Handle direct calorie entries: "500 calories", "ate 300 cal", "manual entry 400 calories"
    - Validate entries and provide confidence scores
    - Estimate basic nutritional breakdown (protein, carbs, fat) from calories
    - Flag suspicious entries and provide recommendations
    - Store entries with confidence levels for future reference

    ANALYTICS QUERIES:
    - Handle requests for nutrition summaries: "how many calories today", "protein this week"
    - For "today", "this day", "daily" → get daily nutrition summary
    - For "week", "weekly", "this week" → get 7-day nutrition analytics
    - Always include user_id in queries
    - Provide nutrition totals in friendly, encouraging messages

    WORKFLOW FOR MEAL LOGGING:
    When receiving a meal message:
    1. Parse the food descriptions using parse_meal_batch
    2. Calculate nutrition using calculate_meal_nutrition
    3. Store the meal using store_meal_log with the calculated data
    4. Provide a summary of what was logged

    TOOLS:
    - logged_parse_meal_batch: Parse food descriptions
    - logged_calculate_meal_nutrition: Calculate nutrition from parsed data
    - logged_lookup_nutrition_usda: Get USDA nutrition data
    - logged_get_nutrition_summary: Get daily/weekly nutrition summaries
    - logged_process_manual_calorie_entry: Process manual calorie entries with validation
    - logged_store_meal_log: Store calculated meal data in database
    """,
    tools=[
        batch_parser_tool,
        batch_calculator_tool,
        usda_tool,
        nutrition_summary_tool,
        manual_entry_tool,
        meal_storage_tool,
    ],
)

__all__ = ["nutrition_agent"]
