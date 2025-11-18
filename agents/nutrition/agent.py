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

# Define tools for nutrition agent
batch_parser_tool = FunctionTool(func=logged_parse_meal_batch)
batch_calculator_tool = FunctionTool(func=logged_calculate_meal_nutrition)
usda_tool = FunctionTool(func=logged_lookup_nutrition_usda)

nutrition_agent = LlmAgent(
    name="nutrition_agent_batch",
    model=PatchedGemini(model=Config.gemini_model),
    description="Processes complete meal batches (not individual items). Receives list of food items from Root Agent, calculates total calories and macros using web search for nutrition data.",
    instruction="""
    You are a nutrition specialist receiving COMPLETE MEAL BATCHES as text input.
    
    INPUT FORMAT: "Calculate nutrition for: food1, food2, ..." or similar descriptions
    
    YOUR TASK:
    - Parse the food items from the input text
    - Use web search to find accurate nutritional information for each food item
    - Calculate: Total calories, protein, carbs, fat for this meal
    - Include: Confidence levels for each food estimate
    - Return: Summarized meal data
    
    WEB SEARCH STRATEGY:
    - Search for reliable sources like USDA, nutrition websites, or established databases
    - Look for specific nutritional data per serving size
    - Use queries like "nutrition facts for [food item]" or "[food item] calories per serving"
    - Cross-reference multiple sources when possible for accuracy
    - If exact match not found, use closest equivalent food
    
    CONSTRAINTS:
    - Always provide realistic estimates based on web search results
    - Show confidence scores (e.g., "~260 cal, high confidence")
    - Flag if total seems high (>1000 cal single meal) or low (<200 cal)
    - Use standard serving sizes when not specified
    
    RETURN FORMAT:
    {
        "status": "success",
        "meal_type": "lunch",  # inferred from time or user
        "foods": [
            {"name": "tuna sandwich", "quantity": "1", "calories": 350, "protein": 25, "carbs": 30, "fat": 12},
            {"name": "soda can", "quantity": "1", "calories": 140, "protein": 0, "carbs": 39, "fat": 0}
        ],
        "totals": {"calories": 490, "protein": 25, "carbs": 69, "fat": 12},
        "confidence": 0.85,
        "notes": "Estimates based on USDA and nutrition database searches"
    }
    """,
    tools=[
        google_search,
    ],
)

__all__ = ["nutrition_agent"]
