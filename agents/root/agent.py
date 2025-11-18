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

from database.meal_manager import meal_manager

# Import nutrition tools
from tools.nutrition.batch_parser import parse_meal_batch
from tools.nutrition.usda_client import lookup_nutrition_usda

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

# Nutrition tool wrappers
async def logged_parse_meal_batch(food_descriptions: List[str], meal_type: str, user_id: str, tool_context: Optional[ToolContext] = None):
    """Wrapper for meal batch parsing with logging."""
    logger.info(f"🍽️ Parsing meal batch: {food_descriptions}, type: {meal_type}, user: {user_id}")
    result = await parse_meal_batch(food_descriptions, meal_type, user_id)
    logger.info(f"📋 Meal batch parsing result: {result}")
    return result

async def logged_calculate_meal_nutrition(food_descriptions: List[str], meal_type: str, user_id: str, tool_context: Optional[ToolContext] = None):
    """Wrapper for nutrition calculation with logging using approximate values."""
    try:
        logger.info(f"🧮 Calculating nutrition for: {food_descriptions}, type: {meal_type}, user: {user_id}")

        # First parse the food descriptions
        parse_result = await parse_meal_batch(food_descriptions, meal_type, user_id)
        if parse_result["status"] == "error":
            logger.error(f"Failed to parse meal batch: {parse_result['error']}")
            return {"status": "error", "error": parse_result["error"]}

        parsed_items = parse_result["data"]["parsed_items"]

        # Calculate nutrition using approximate values for common foods
        total_calories = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0
        items = []
        overall_confidence = 1.0

        # Approximate nutrition data for common foods (per serving)
        nutrition_db = {
            # Breakfast Items
            'tuna sandwich': {'calories': 350, 'protein': 25, 'carbs': 30, 'fat': 12, 'serving': '1 sandwich'},
            'eggs': {'calories': 70, 'protein': 6, 'carbs': 0.5, 'fat': 5, 'serving': '1 large'},
            'toast': {'calories': 80, 'protein': 3, 'carbs': 15, 'fat': 1, 'serving': '1 slice'},
            'oatmeal': {'calories': 150, 'protein': 5, 'carbs': 27, 'fat': 2.5, 'serving': '1/2 cup dry'},
            'cereal': {'calories': 120, 'protein': 3, 'carbs': 24, 'fat': 1, 'serving': '1 cup'},
            'pancakes': {'calories': 227, 'protein': 6, 'carbs': 35, 'fat': 6, 'serving': '2 medium'},
            'waffles': {'calories': 218, 'protein': 6, 'carbs': 31, 'fat': 7, 'serving': '1 large'},
            'bacon': {'calories': 43, 'protein': 3, 'carbs': 0.1, 'fat': 3.3, 'serving': '1 slice'},
            'sausage': {'calories': 85, 'protein': 5, 'carbs': 0.5, 'fat': 7, 'serving': '1 link'},
            'bagel': {'calories': 250, 'protein': 9, 'carbs': 48, 'fat': 2, 'serving': '1 medium'},
            'muffin': {'calories': 340, 'protein': 6, 'carbs': 45, 'fat': 15, 'serving': '1 large'},
            'croissant': {'calories': 231, 'protein': 5, 'carbs': 26, 'fat': 12, 'serving': '1 medium'},
            'cinnamon roll': {'calories': 223, 'protein': 4, 'carbs': 32, 'fat': 9, 'serving': '1 medium'},
            
            # Fruits
            'apple': {'calories': 95, 'protein': 0.5, 'carbs': 25, 'fat': 0.3, 'serving': '1 medium'},
            'banana': {'calories': 105, 'protein': 1.3, 'carbs': 27, 'fat': 0.4, 'serving': '1 medium'},
            'orange': {'calories': 62, 'protein': 1.2, 'carbs': 15, 'fat': 0.2, 'serving': '1 medium'},
            'grapes': {'calories': 62, 'protein': 0.6, 'carbs': 16, 'fat': 0.3, 'serving': '1 cup'},
            'strawberries': {'calories': 49, 'protein': 1, 'carbs': 12, 'fat': 0.5, 'serving': '1 cup'},
            'blueberries': {'calories': 84, 'protein': 1.1, 'carbs': 21, 'fat': 0.5, 'serving': '1 cup'},
            'pineapple': {'calories': 82, 'protein': 1, 'carbs': 22, 'fat': 0.2, 'serving': '1 cup'},
            'watermelon': {'calories': 30, 'protein': 0.6, 'carbs': 8, 'fat': 0.2, 'serving': '1 cup'},
            'peach': {'calories': 59, 'protein': 1.4, 'carbs': 14, 'fat': 0.4, 'serving': '1 medium'},
            'pear': {'calories': 101, 'protein': 0.7, 'carbs': 27, 'fat': 0.2, 'serving': '1 medium'},
            
            # Vegetables
            'broccoli': {'calories': 55, 'protein': 3.7, 'carbs': 11, 'fat': 0.6, 'serving': '1 cup'},
            'carrots': {'calories': 25, 'protein': 0.6, 'carbs': 6, 'fat': 0.1, 'serving': '1 medium'},
            'potatoes': {'calories': 77, 'protein': 2, 'carbs': 17, 'fat': 0.1, 'serving': '1 medium'},
            'sweet potato': {'calories': 112, 'protein': 2, 'carbs': 26, 'fat': 0.1, 'serving': '1 medium'},
            'spinach': {'calories': 7, 'protein': 0.9, 'carbs': 1.1, 'fat': 0.1, 'serving': '1 cup'},
            'lettuce': {'calories': 5, 'protein': 0.5, 'carbs': 1, 'fat': 0.1, 'serving': '1 cup'},
            'tomatoes': {'calories': 22, 'protein': 1.1, 'carbs': 5, 'fat': 0.2, 'serving': '1 medium'},
            'cucumber': {'calories': 16, 'protein': 0.7, 'carbs': 3.6, 'fat': 0.1, 'serving': '1 medium'},
            'bell pepper': {'calories': 24, 'protein': 1, 'carbs': 6, 'fat': 0.3, 'serving': '1 medium'},
            'onion': {'calories': 44, 'protein': 1.2, 'carbs': 10, 'fat': 0.1, 'serving': '1 medium'},
            'garlic': {'calories': 4, 'protein': 0.2, 'carbs': 1, 'fat': 0, 'serving': '1 clove'},
            'zucchini': {'calories': 33, 'protein': 2.4, 'carbs': 6, 'fat': 0.6, 'serving': '1 cup'},
            'mushrooms': {'calories': 22, 'protein': 3.1, 'carbs': 3.3, 'fat': 0.3, 'serving': '1 cup'},
            'avocado': {'calories': 234, 'protein': 2.9, 'carbs': 12, 'fat': 21, 'serving': '1/2 medium'},
            
            # Proteins
            'chicken breast': {'calories': 165, 'protein': 31, 'carbs': 0, 'fat': 3.6, 'serving': '100g'},
            'chicken thigh': {'calories': 209, 'protein': 26, 'carbs': 0, 'fat': 10, 'serving': '100g'},
            'ground beef': {'calories': 152, 'protein': 20, 'carbs': 0, 'fat': 8, 'serving': '100g'},
            'steak': {'calories': 250, 'protein': 26, 'carbs': 0, 'fat': 15, 'serving': '100g'},
            'pork chop': {'calories': 231, 'protein': 29, 'carbs': 0, 'fat': 11, 'serving': '100g'},
            'salmon': {'calories': 206, 'protein': 22, 'carbs': 0, 'fat': 12, 'serving': '100g'},
            'tuna': {'calories': 144, 'protein': 25, 'carbs': 0, 'fat': 4.9, 'serving': '100g'},
            'shrimp': {'calories': 99, 'protein': 24, 'carbs': 0.3, 'fat': 0.3, 'serving': '100g'},
            'turkey': {'calories': 135, 'protein': 30, 'carbs': 0, 'fat': 1, 'serving': '100g'},
            'tofu': {'calories': 76, 'protein': 8, 'carbs': 2, 'fat': 4.8, 'serving': '100g'},
            'lentils': {'calories': 116, 'protein': 9, 'carbs': 20, 'fat': 0.4, 'serving': '1/2 cup'},
            'black beans': {'calories': 132, 'protein': 9, 'carbs': 24, 'fat': 0.5, 'serving': '1/2 cup'},
            'chickpeas': {'calories': 143, 'protein': 7.5, 'carbs': 25, 'fat': 2.6, 'serving': '1/2 cup'},
            'peanut butter': {'calories': 190, 'protein': 7, 'carbs': 6, 'fat': 16, 'serving': '2 tbsp'},
            'peanuts': {'calories': 567, 'protein': 26, 'carbs': 16, 'fat': 49, 'serving': '100g'},
            'almonds': {'calories': 164, 'protein': 6, 'carbs': 6, 'fat': 14, 'serving': '1 oz'},
            'walnuts': {'calories': 185, 'protein': 4, 'carbs': 4, 'fat': 18, 'serving': '1 oz'},
            'cashews': {'calories': 157, 'protein': 5, 'carbs': 9, 'fat': 12, 'serving': '1 oz'},
            
            # Dairy
            'milk': {'calories': 103, 'protein': 8, 'carbs': 12, 'fat': 2.4, 'serving': '1 cup'},
            'cheese': {'calories': 113, 'protein': 7, 'carbs': 1, 'fat': 9, 'serving': '1 oz'},
            'yogurt': {'calories': 150, 'protein': 12, 'carbs': 12, 'fat': 5, 'serving': '1 cup'},
            'cottage cheese': {'calories': 163, 'protein': 28, 'carbs': 6, 'fat': 2.3, 'serving': '1 cup'},
            'ice cream': {'calories': 137, 'protein': 2.3, 'carbs': 16, 'fat': 7.3, 'serving': '1/2 cup'},
            'butter': {'calories': 102, 'protein': 0.1, 'carbs': 0, 'fat': 11.5, 'serving': '1 tbsp'},
            
            # Grains & Carbs
            'rice': {'calories': 130, 'protein': 2.7, 'carbs': 28, 'fat': 0.3, 'serving': '1/2 cup cooked'},
            'pasta': {'calories': 157, 'protein': 6, 'carbs': 31, 'fat': 0.9, 'serving': '1 cup cooked'},
            'bread': {'calories': 79, 'protein': 3, 'carbs': 15, 'fat': 1, 'serving': '1 slice'},
            'quinoa': {'calories': 111, 'protein': 4, 'carbs': 20, 'fat': 1.9, 'serving': '1/2 cup cooked'},
            'brown rice': {'calories': 109, 'protein': 2.6, 'carbs': 23, 'fat': 0.9, 'serving': '1/2 cup cooked'},
            'potato chips': {'calories': 152, 'protein': 2, 'carbs': 15, 'fat': 10, 'serving': '1 oz'},
            'pretzels': {'calories': 108, 'protein': 3, 'carbs': 22, 'fat': 1, 'serving': '1 oz'},
            
            # Fast Food & Prepared Meals
            'hamburger': {'calories': 354, 'protein': 20, 'carbs': 29, 'fat': 17, 'serving': '1 medium'},
            'cheeseburger': {'calories': 535, 'protein': 27, 'carbs': 31, 'fat': 29, 'serving': '1 medium'},
            'french fries': {'calories': 365, 'protein': 4, 'carbs': 46, 'fat': 17, 'serving': 'medium'},
            'pizza': {'calories': 285, 'protein': 12, 'carbs': 36, 'fat': 10, 'serving': '1 slice'},
            'taco': {'calories': 156, 'protein': 9, 'carbs': 13, 'fat': 7, 'serving': '1 medium'},
            'burrito': {'calories': 340, 'protein': 14, 'carbs': 45, 'fat': 12, 'serving': '1 medium'},
            'sandwich': {'calories': 250, 'protein': 15, 'carbs': 30, 'fat': 8, 'serving': '1 medium'},
            
            # Snacks & Sweets
            'chocolate bar': {'calories': 235, 'protein': 3, 'carbs': 27, 'fat': 13, 'serving': '1.5 oz'},
            'cookies': {'calories': 53, 'protein': 1, 'carbs': 7, 'fat': 2.5, 'serving': '1 medium'},
            'cake': {'calories': 257, 'protein': 3, 'carbs': 37, 'fat': 11, 'serving': '1 slice'},
            'pie': {'calories': 323, 'protein': 4, 'carbs': 44, 'fat': 15, 'serving': '1 slice'},
            'candy': {'calories': 103, 'protein': 0, 'carbs': 27, 'fat': 0, 'serving': '1.5 oz'},
            'popcorn': {'calories': 31, 'protein': 1, 'carbs': 6, 'fat': 0.4, 'serving': '1 cup'},
            'trail mix': {'calories': 175, 'protein': 5, 'carbs': 16, 'fat': 12, 'serving': '1/4 cup'},
            
            # Beverages
            'soda can': {'calories': 140, 'protein': 0, 'carbs': 39, 'fat': 0, 'serving': '1 can'},
            'coffee': {'calories': 2, 'protein': 0.1, 'carbs': 0, 'fat': 0, 'serving': '1 cup'},
            'tea': {'calories': 2, 'protein': 0, 'carbs': 0.4, 'fat': 0, 'serving': '1 cup'},
            'orange juice': {'calories': 112, 'protein': 2, 'carbs': 26, 'fat': 0.5, 'serving': '1 cup'},
            'apple juice': {'calories': 114, 'protein': 0.2, 'carbs': 28, 'fat': 0.3, 'serving': '1 cup'},
            'beer': {'calories': 153, 'protein': 1.6, 'carbs': 12.6, 'fat': 0, 'serving': '12 oz'},
            'wine': {'calories': 125, 'protein': 0.1, 'carbs': 3.8, 'fat': 0, 'serving': '5 oz'},
            'protein shake': {'calories': 120, 'protein': 25, 'carbs': 3, 'fat': 1, 'serving': '1 scoop'},
            'smoothie': {'calories': 200, 'protein': 10, 'carbs': 35, 'fat': 3, 'serving': '1 medium'},
            
            # Salads & Mixed Dishes
            'salad': {'calories': 50, 'protein': 2, 'carbs': 10, 'fat': 0.5, 'serving': '1 cup'},
            'caesar salad': {'calories': 184, 'protein': 7, 'carbs': 10, 'fat': 14, 'serving': '1 medium'},
            'pasta salad': {'calories': 157, 'protein': 5, 'carbs': 25, 'fat': 5, 'serving': '1 cup'},
            'soup': {'calories': 70, 'protein': 3, 'carbs': 10, 'fat': 2, 'serving': '1 cup'},
            'stir fry': {'calories': 150, 'protein': 15, 'carbs': 15, 'fat': 6, 'serving': '1 cup'},
            'curry': {'calories': 200, 'protein': 12, 'carbs': 20, 'fat': 8, 'serving': '1 cup'},
            
            # Miscellaneous
            'hummus': {'calories': 166, 'protein': 8, 'carbs': 14, 'fat': 10, 'serving': '1/2 cup'},
            'guacamole': {'calories': 160, 'protein': 2, 'carbs': 9, 'fat': 15, 'serving': '1/2 cup'},
            'salsa': {'calories': 20, 'protein': 1, 'carbs': 4, 'fat': 0.2, 'serving': '1/4 cup'},
            'olive oil': {'calories': 119, 'protein': 0, 'carbs': 0, 'fat': 13.5, 'serving': '1 tbsp'},
            'honey': {'calories': 64, 'protein': 0.1, 'carbs': 17, 'fat': 0, 'serving': '1 tbsp'},
            'sugar': {'calories': 49, 'protein': 0, 'carbs': 13, 'fat': 0, 'serving': '1 tbsp'},
            'salt': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'serving': '1 tsp'},
        }

        for item in parsed_items:
            food_name = item.get('parsed_food', item.get('description', '')).lower()
            quantity = item.get('quantity', 1.0)
            unit = item.get('unit', 'serving')
            confidence = item.get('confidence', 0.5)

            # Find the best match in our database
            best_match = None
            best_score = 0
            
            for db_food, data in nutrition_db.items():
                # Check for substring matches (more flexible than word overlap)
                if db_food in food_name or food_name in db_food:
                    # Calculate similarity score based on substring match quality
                    if food_name in db_food:
                        # food_name is substring of db_food (e.g., "burger" in "hamburger")
                        score = len(food_name) / len(db_food)  # How much of db_food matches
                    else:
                        # db_food is substring of food_name (e.g., "chips" in "potato chips")
                        score = len(db_food) / len(food_name)  # How much of food_name matches
                    
                    if score > best_score:
                        best_score = score
                        best_match = db_food

            if best_match and best_score > 0.3:  # Require some similarity
                data = nutrition_db[best_match]
                
                # Scale by quantity (simplified - assumes quantity refers to servings)
                scale_factor = quantity
                calories = data['calories'] * scale_factor
                protein = data['protein'] * scale_factor
                carbs = data['carbs'] * scale_factor
                fat = data['fat'] * scale_factor

                items.append({
                    'food_name': food_name,
                    'calories': round(calories, 1),
                    'protein_g': round(protein, 1),
                    'confidence': min(confidence * 0.8, 1.0),  # Slightly reduce confidence for approximations
                    'source': 'approximate_db'
                })

                total_calories += calories
                total_protein += protein
                total_carbs += carbs
                total_fat += fat
                overall_confidence = min(overall_confidence, confidence * 0.8)
            else:
                # No match found
                items.append({
                    'food_name': food_name,
                    'calories': 0.0,
                    'protein_g': 0.0,
                    'confidence': 0.1,
                    'source': 'unknown'
                })
                overall_confidence = min(overall_confidence, 0.1)

        result = {
            "status": "success",
            "data": {
                "total_calories": round(total_calories, 1),
                "total_protein_g": round(total_protein, 1),
                "total_carbs_g": round(total_carbs, 1),
                "total_fat_g": round(total_fat, 1),
                "items": items,
                "confidence_score": round(overall_confidence, 2)
            },
            "error": None
        }

        logger.info(f"📊 Nutrition calculation result: {result}")
        return result

    except Exception as e:
        logger.error(f"Nutrition calculation failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def _parse_nutrition_search_results(search_data: Dict[str, Any], food_name: str) -> Optional[Dict[str, Any]]:
    """Parse nutrition data from web search results."""
    try:
        # Extract text from search results
        search_text = ""
        if 'results' in search_data:
            for result in search_data['results'][:3]:  # Use top 3 results
                if 'content' in result:
                    search_text += result['content'] + " "
                elif 'snippet' in result:
                    search_text += result['snippet'] + " "

        if not search_text:
            return None

        # Use regex to extract nutrition facts
        import re
        calories_match = re.search(r'calories?\s*:\s*(\d+)', search_text, re.IGNORECASE)
        protein_match = re.search(r'protein\s*:\s*(\d+(?:\.\d+)?)\s*g', search_text, re.IGNORECASE)
        carbs_match = re.search(r'(?:carbs?|carbohydrates?)\s*:\s*(\d+(?:\.\d+)?)\s*g', search_text, re.IGNORECASE)
        fat_match = re.search(r'fat\s*:\s*(\d+(?:\.\d+)?)\s*g', search_text, re.IGNORECASE)
        serving_match = re.search(r'serving\s*size\s*:\s*(\d+(?:\.\d+)?)\s*g', search_text, re.IGNORECASE)

        serving_size_g = float(serving_match.group(1)) if serving_match else 100.0

        nutrition_data = {
            'food_name': food_name,
            'serving_size_g': serving_size_g,
            'calories_per_serving': float(calories_match.group(1)) if calories_match else 0,
            'protein_g_per_serving': float(protein_match.group(1)) if protein_match else 0,
            'carbs_g_per_serving': float(carbs_match.group(1)) if carbs_match else 0,
            'fat_g_per_serving': float(fat_match.group(1)) if fat_match else 0,
            'confidence': 0.6
        }

        # Return data if we found at least calories
        if nutrition_data['calories_per_serving'] > 0:
            return nutrition_data

        return None

    except Exception as e:
        logger.error(f"Failed to parse search results for {food_name}: {e}")
        return None


def _calculate_scale_factor(quantity: float, unit: str, serving_size_g: float) -> float:
    """Calculate scaling factor for nutrition values based on quantity and unit."""
    # Unit conversion factors (approximate)
    conversions = {
        'cup': 240,
        'tablespoon': 15,
        'teaspoon': 5,
        'pound': 453.6,
        'ounce': 28.35,
        'gram': 1,
        'kilogram': 1000,
        'liter': 1000,
        'milliliter': 1,
        'piece': serving_size_g,
        'slice': serving_size_g * 0.3,
        'whole': serving_size_g,
        'half': serving_size_g * 0.5,
        'quarter': serving_size_g * 0.25,
        'serving': serving_size_g,
        'scoop': serving_size_g,
        'bottle': serving_size_g,
        'can': serving_size_g
    }

    unit_lower = unit.lower()
    if unit_lower in conversions:
        grams = quantity * conversions[unit_lower]
    else:
        # Unknown unit, assume it's equivalent to serving size
        grams = quantity * serving_size_g

    return grams / serving_size_g


async def logged_lookup_nutrition_usda(food_name: str, quantity: str = "100g", tool_context: Optional[ToolContext] = None):
    """Wrapper for USDA nutrition lookup with logging."""
    logger.info(f"🔍 Looking up USDA nutrition for: {food_name}, quantity: {quantity}")
    result = lookup_nutrition_usda(food_name, quantity)
    logger.info(f"📚 USDA lookup result: {result}")
    return result

async def logged_get_nutrition_summary(user_id: str, period: str = "today", tool_context: Optional[ToolContext] = None):
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

# Define tools for root agent
intent_tool = FunctionTool(func=logged_classify_intent)
sentiment_tool = FunctionTool(func=logged_detect_sentiment)
response_tool = FunctionTool(func=logged_format_response)
batch_state_tool = FunctionTool(func=logged_get_batch_state)

# Nutrition tools with explicit schemas
parse_meal_tool = FunctionTool(func=logged_parse_meal_batch)

calculate_nutrition_tool = FunctionTool(func=logged_calculate_meal_nutrition)

usda_lookup_tool = FunctionTool(func=logged_lookup_nutrition_usda)

nutrition_summary_tool = FunctionTool(func=logged_get_nutrition_summary)

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
    3. For NUTRITION intent: ALWAYS call nutrition tools to process the food
       - Use parse_meal_batch to parse the food items
       - Use calculate_meal_nutrition to get nutritional info and log it
       - Use the result data to generate a response message with the nutrition summary
    4. For ANALYTICS intent: Get nutrition summaries by calling logged_get_nutrition_summary
       - Handle queries like "how many calories today" or "protein this week"
       - Call the tool with the appropriate period and user_id
       - Then provide a complete response with the nutrition information
    5. For multi-item logging: Use BATCH MODE workflow
       - MEALS: "Logged [item]. Is that all for this meal? Any sides?"
       - WORKOUTS: "Logged [exercise]. Any more sets? Different exercise?"
       - HYDRATION: "Logged [amount]. More water logged today? Anything else?"
    6. After user confirms "that's all": Process the batch using nutrition tools
    7. Route requests:
       - Food logs → Use nutrition tools directly
       - Progress queries → Use nutrition_summary_tool for analytics
       - Workouts → Handle with fitness logic (not implemented yet)
       - Water/Sleep/Steps → Handle with wellness logic (not implemented yet)
    8. Synthesize responses into single supportive message
    
    TONE: Supportive coach, warm, encouraging. Use 1-2 emojis max per message.
    
    CRITICAL: For any nutrition/food logging intent, you MUST call the nutrition tools (parse_meal_batch + calculate_meal_nutrition) before responding.
    For analytics queries, you MUST call nutrition_summary_tool to get the data.
    
    IMPORTANT: After calling any tools, you MUST generate a final response message to the user. Do not end with tool calls - always provide a complete response.
    Always respond with a complete, helpful message that answers the user's question.
    
    BATCH MODE RULES:
    - After each item, ALWAYS ask "Is that all?" or "Anything else?"
    - Never process partially - wait for complete batch
    - Once user confirms complete, use nutrition tools to process
    - Example flow:
      User: "2 eggs"
      You: "2 eggs logged. Is that all for breakfast?"
      User: "Yes, also had toast"
      You: "Toast logged. Anything else?"
      User: "No, that's all"
      You: [PARSE_MEAL_BATCH: ["eggs", "toast"], "breakfast", user_id]
      [CALCULATE_NUTRITION: parsed_data]
      You: "Breakfast logged! 260 cal, 14g protein ✅ On track today!"
    
    ANALYTICS RULES:
    - For "today", "this day", "daily" → call logged_get_nutrition_summary with period="today"
    - For "week", "weekly", "this week" → call logged_get_nutrition_summary with period="week"
    - Always include user_id in the call
    - After getting the data, respond with the nutrition totals in a friendly message
    """,
    tools=[
        intent_tool,
        sentiment_tool,
        batch_state_tool,
        parse_meal_tool,
        calculate_nutrition_tool,
        nutrition_summary_tool,
    ],
)