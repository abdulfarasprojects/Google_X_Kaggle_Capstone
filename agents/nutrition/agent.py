"""
Nutrition agent for Weight Loss Chat Agent using Google ADK.

This agent processes compleasync def logged_get_nutrition_summary(user_id: str, period: str = "today", tool_context: Optional[str] = None):using Google ADK LlmAgent.
"""

import sys
import os
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from config import settings as Config
from config.logging import get_logger
from tools.nutrition.batch_parser import parse_meal_batch
from tools.nutrition.calculator import calculate_meal_nutrition
from tools.nutrition.manual_entry import process_manual_calorie_entry
from tools.nutrition.meal_storage import store_meal_log
from tools.nutrition.usda_client import lookup_nutrition_usda
from database.meal_manager import meal_manager

# Observability imports
from observability.tracing import traced
from observability.metrics import record_request, record_response_time, record_error

# Import Google ADK
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools.google_search_tool import google_search
from config.gemini import PatchedGemini

logger = get_logger(__name__)

# Logging wrapper functions for tools
@traced("parse_meal_batch")
async def logged_parse_meal_batch(food_items: str, meal_type: str, user_id: str, tool_context: Optional[str] = None):
    """Wrapper for meal batch parsing with logging.
    
    Accepts food items as a comma-separated string (e.g., "eggs, toast, coffee").
    Parses them, calculates nutrition, and stores the meal in database.
    Returns complete nutrition data.
    """
    # Convert comma-separated string to list if needed
    if isinstance(food_items, str):
        food_list = [item.strip() for item in food_items.split(',') if item.strip()]
    else:
        food_list = food_items
    
    logger.info(f"🍽️ Parsing meal batch: {food_list}, meal_type: {meal_type}, user_id: {user_id}")
    
    try:
        # Step 1: Parse the meal items
        parse_result = await parse_meal_batch(food_list, meal_type, user_id, None)
        logger.info(f"📋 Meal batch parsing result: {parse_result}")
        
        if not parse_result.get('success'):
            return parse_result
        
        # Step 2: Calculate nutrition from parsed items
        parsed_items = parse_result.get('data', [])
        calc_result = await calculate_meal_nutrition(parsed_items, meal_type, user_id, None)
        logger.info(f"📊 Nutrition calculation result: {calc_result}")
        
        if not calc_result.get('success'):
            return calc_result
        
        # Step 3: Store the meal log
        total_calories = calc_result.get('total_calories', 0)
        total_protein = calc_result.get('total_protein_g', 0)
        
        store_result = await store_meal_log(
            user_id=user_id,
            meal_type=meal_type,
            food_items=parsed_items,
            total_calories=total_calories,
            total_protein_g=total_protein,
            confidence_score=calc_result.get('confidence', 0.8),
            tool_context=None
        )
        logger.info(f"💾 Meal storage result: {store_result}")
        
        # Return combined result
        return {
            "status": "success",
            "meal_logged": True,
            "meal_type": meal_type,
            "food_items": food_list,
            "total_calories": total_calories,
            "total_protein_g": total_protein,
            "macros": calc_result.get('macros', {}),
            "meal_id": store_result.get('meal_id') if store_result.get('success') else None
        }
    except TypeError as e:
        # Handle ADK schema validation comparison errors
        error_str = str(e)
        if "'<=' not supported" in error_str or "not supported between instances of" in error_str:
            logger.warning(f"ADK comparison error in meal parsing: {error_str}")
            return {"status": "error", "error": "Processing error, please try again"}
        logger.error(f"Error in meal logging pipeline: {e}")
        return {"status": "error", "error": str(e)}
    except Exception as e:
        logger.error(f"Error in meal logging pipeline: {e}")
        return {"status": "error", "error": str(e)}

@traced("lookup_nutrition_usda")
async def logged_lookup_nutrition_usda(food_name: str, portion_size: str = "100g", tool_context: Optional[str] = None):
    """Wrapper for USDA nutrition lookup with logging.
    
    Accepts food name and portion size as strings.
    Looks up nutrition data from USDA database.
    """
    logger.info(f"🔍 Looking up USDA nutrition: {food_name}, portion: {portion_size}")
    try:
        result = await lookup_nutrition_usda(food_name, portion_size)
        logger.info(f"📚 USDA lookup result: {result}")
        return result
    except TypeError as e:
        # Handle ADK schema validation comparison errors
        error_str = str(e)
        if "'<=' not supported" in error_str or "not supported between instances of" in error_str:
            logger.warning(f"ADK comparison error in USDA lookup: {error_str}")
            return {"status": "error", "error": "Processing error, please try again"}
        logger.error(f"USDA lookup error: {e}")
        return {"status": "error", "error": str(e)}
    except Exception as e:
        logger.error(f"USDA lookup error: {e}")
        return {"status": "error", "error": str(e)}

@traced("get_nutrition_summary")
async def logged_get_nutrition_summary(user_id: str, period: str = "today", tool_context: Optional[str] = None):
    """Wrapper for nutrition summary queries with logging.
    
    Accepts period as a string: "today", "week", "month", etc.
    Returns daily or weekly nutrition summaries.
    """
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
    except TypeError as e:
        # Handle ADK schema validation comparison errors
        error_str = str(e)
        if "'<=' not supported" in error_str or "not supported between instances of" in error_str:
            logger.warning(f"ADK comparison error in nutrition summary: {error_str}")
            return {"status": "error", "error": "Processing error, please try again"}
        logger.error(f"Failed to get nutrition summary: {e}")
        return {"status": "error", "error": str(e)}
    except Exception as e:
        logger.error(f"Failed to get nutrition summary: {e}")
        return {"status": "error", "error": str(e)}

@traced("process_manual_calorie_entry")
async def logged_process_manual_calorie_entry(text: str, user_id: str = "", tool_context: Optional[str] = None):
    """Wrapper for manual calorie entry processing with logging.
    
    Accepts text description (e.g., "500 calories") and optional user ID.
    Returns parsed calorie information.
    """
    logger.info(f"📝 Processing manual calorie entry: {text}")
    try:
        result = process_manual_calorie_entry(text, {"user_id": user_id} if user_id else None)
        logger.info(f"✅ Manual entry processing result: {result}")
        return result
    except TypeError as e:
        # Handle ADK schema validation comparison errors
        error_str = str(e)
        if "'<=' not supported" in error_str or "not supported between instances of" in error_str:
            logger.warning(f"ADK comparison error in manual entry: {error_str}")
            return {"status": "error", "error": "Processing error, please try again"}
        logger.error(f"Error processing manual entry: {e}")
        return {"status": "error", "error": str(e)}
    except Exception as e:
        logger.error(f"Error processing manual entry: {e}")
        return {"status": "error", "error": str(e)}

@traced("store_meal_log")
async def logged_store_meal_log(user_id: str, meal_type: str, food_items_json: str, total_calories: float, total_protein_g: float, confidence_score: float = 1.0, tool_context: Optional[str] = None):
    """Wrapper for meal storage with logging.
    
    Accepts food_items as a JSON string and stores the meal in database.
    """
    try:
        # Parse JSON string back to list
        if isinstance(food_items_json, str):
            food_items = json.loads(food_items_json) if food_items_json.startswith('[') else [{"name": food_items_json}]
        else:
            food_items = food_items_json
        
        logger.info(f"💾 Storing meal log for user {user_id}: {meal_type}, {total_calories} cal, {len(food_items)} items")
        result = await store_meal_log(user_id, meal_type, food_items, total_calories, total_protein_g, confidence_score, None)
        logger.info(f"✅ Meal storage result: {result}")
        return result
    except TypeError as e:
        # Handle ADK schema validation comparison errors
        error_str = str(e)
        if "'<=' not supported" in error_str or "not supported between instances of" in error_str:
            logger.warning(f"ADK comparison error in meal storage: {error_str}")
            return {"status": "error", "error": "Processing error, please try again"}
        logger.error(f"Error storing meal log: {e}")
        return {"status": "error", "error": str(e)}
    except Exception as e:
        logger.error(f"Error storing meal log: {e}")
        return {"status": "error", "error": str(e)}

# Define tools for nutrition agent
batch_parser_tool = FunctionTool(func=logged_parse_meal_batch)
nutrition_summary_tool = FunctionTool(func=logged_get_nutrition_summary)
manual_entry_tool = FunctionTool(func=logged_process_manual_calorie_entry)
meal_storage_tool = FunctionTool(func=logged_store_meal_log)

nutrition_agent = LlmAgent(
    name="nutrition_agent_batch",
    model=PatchedGemini(model=Config.gemini_model),
    description="Nutrition specialist that processes meal logging and provides nutrition analytics. Receives food items from Root Agent via transfer_to_agent(), calculates nutrition data, and provides summaries and analytics.",
    instruction="""
    You are a nutrition specialist sub-agent that processes meal messages and provides nutrition analytics.
    
    CONTEXT: You are called from the Root Agent when the user's intent is classified as NUTRITION.
    The Root Agent will transfer the user's message to you using transfer_to_agent().
    Your job is to process the nutrition request and return results to the Root Agent.
    
    YOUR RESPONSIBILITIES:
    1. Parse food items from the user's message
    2. Calculate nutrition data (calories, protein, carbs, fat)
    3. Store the meal data in the database
    4. Provide friendly summary/response to user
    
    MEAL PROCESSING WORKFLOW:
    When receiving a meal message from Root Agent:
    1. Parse the food descriptions using logged_parse_meal_batch
    2. Calculate nutrition using logged_calculate_meal_nutrition
    3. Store the meal using logged_store_meal_log with the calculated data
    4. Provide a friendly summary of what was logged
    
    NUTRITION ANALYTICS QUERIES:
    - Handle requests like: "how many calories today", "protein this week", "nutrition summary"
    - For "today", "this day", "daily" → get daily nutrition summary using logged_get_nutrition_summary
    - For "week", "weekly", "this week" → get 7-day nutrition analytics
    - Provide nutrition totals in friendly, encouraging messages
    
    TOOLS AVAILABLE:
    - logged_parse_meal_batch: Parse food descriptions from text
    - logged_calculate_meal_nutrition: Calculate nutrition from parsed data
    - logged_get_nutrition_summary: Get daily/weekly nutrition summaries
    - logged_process_manual_calorie_entry: Handle manual calorie entries
    - logged_store_meal_log: Store calculated meal data in database
    
    RESPONSE GUIDELINES:
    - Always be encouraging and supportive
    - Provide specific calorie/protein totals when logging meals
    - For analytics: Include comparisons to goals/targets if available
    - Use 1-2 emojis max per response
    - Keep responses concise and actionable
    - End with positive reinforcement or next steps
    
    IMPORTANT: You are a SUB-AGENT. Do not try to handle non-nutrition requests.
    If the user's request is not about nutrition, clearly indicate that and the Root Agent 
    will reroute the request to the appropriate specialist.
    """,
    tools=[
        batch_parser_tool,
        nutrition_summary_tool,
        manual_entry_tool,
        meal_storage_tool,
    ],
)

# Alias for ADK web server framework compatibility
root_agent = nutrition_agent

__all__ = ["nutrition_agent", "root_agent"]
