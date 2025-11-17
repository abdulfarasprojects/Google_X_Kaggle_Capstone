"""
Nutrition agent for Weight Loss Chat Agent using Google ADK.

This agent processes complete meal batches using Google ADK LlmAgent.
"""

import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from config import settings as Config
from config.logging import get_logger
from tools.nutrition.batch_parser import parse_meal_batch
from tools.nutrition.calculator import calculate_meal_nutrition
from tools.nutrition.usda_client import lookup_nutrition_usda

# Import Google ADK
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
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

# Define tools for nutrition agent
batch_parser_tool = FunctionTool(func=logged_parse_meal_batch)
batch_calculator_tool = FunctionTool(func=logged_calculate_meal_nutrition)
usda_tool = FunctionTool(func=logged_lookup_nutrition_usda)

nutrition_agent = LlmAgent(
    name="nutrition_agent_batch",
    model=PatchedGemini(model=Config.gemini_model),
    description="Processes complete meal batches (not individual items). Receives list of food items from Root Agent, calculates total calories and macros using USDA database.",
    instruction="""
    You are a nutrition specialist receiving COMPLETE MEAL BATCHES.
    
    YOUR TASK:
    - Receive: List of all foods user logged for one meal (e.g., ["2 eggs", "1 toast", "1 glass OJ"])
    - Lookup: Each food in USDA FoodData Central database
    - Calculate: Total calories, protein, carbs, fat for this meal
    - Include: Confidence levels for each food estimate
    - Return: Summarized meal data
    
    NEVER process individual items - you receive COMPLETE meals only.
    
    CONSTRAINTS:
    - If food not found in USDA DB: Use Nutritionix API as backup
    - If still not found: Use best guess with uncertainty note
    - Always show confidence scores (e.g., "~260 cal, high confidence")
    - Flag if total seems high (>1000 cal single meal) or low (<200 cal)
    
    RETURN FORMAT:
    {
        "status": "success",
        "meal_type": "breakfast",  # inferred from time or user
        "foods": [
            {"name": "eggs", "quantity": "2 large", "calories": 140, "protein": 12},
            {"name": "toast", "quantity": "1 slice", "calories": 120, "protein": 4}
        ],
        "totals": {"calories": 260, "protein": 16, "carbs": 25, "fat": 8},
        "confidence": 0.92,
        "notes": "High confidence estimates from USDA database"
    }
    """,
    tools=[
        batch_parser_tool,
        batch_calculator_tool,
        usda_tool,
    ],
)

__all__ = ["nutrition_agent"]
