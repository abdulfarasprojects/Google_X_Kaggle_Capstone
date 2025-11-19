"""
Nutrition calculation tools for meal analysis.

This module provides tools for calculating nutrition information from parsed
food items. Uses web search to find accurate calorie and macronutrient data.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from tools.base import BaseTool, ToolResult
from config.settings import settings

from tools.nutrition.reference_data import nutrition_reference

logger = logging.getLogger(__name__)


@dataclass
class NutritionItem:
    """Nutrition data for a single food item."""
    food_name: str
    calories: float
    protein_g: float
    carbs_g: float = 0.0
    fat_g: float = 0.0
    confidence: float = 1.0
    source: str = "unknown"


class MealNutritionCalculatorTool(BaseTool):
    """
    Tool for calculating nutrition information for meal items.

    Uses web search to find accurate calorie and macronutrient calculations.
    Provides confidence scoring and validation.
    """

    def __init__(self):
        super().__init__(
            name="calculate_meal_nutrition",
            description="Calculate nutrition information for a batch of parsed food items using web search",
            parameters={
                "type": "object",
                "properties": {
                    "parsed_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "quantity": {"type": "number"},
                                "unit": {"type": "string"},
                                "parsed_food": {"type": "string"},
                                "confidence": {"type": "number"}
                            }
                        },
                        "maxItems": 10
                    },
                    "meal_type": {
                        "type": "string",
                        "enum": ["breakfast", "lunch", "dinner", "snack"]
                    },
                    "user_id": {
                        "type": "string"
                    }
                },
                "required": ["parsed_items", "meal_type", "user_id"]
            },
            timeout_seconds=30  # Allow time for web searches
        )

    async def execute(
        self,
        parsed_items: List[Dict[str, Any]],
        meal_type: str,
        user_id: str,
        tool_context: Optional[Any] = None
    ) -> ToolResult:
        """
        Calculate nutrition for parsed food items using web search.

        Args:
            parsed_items: List of parsed food items from batch parser
            meal_type: Type of meal
            user_id: User ID for context
            tool_context: ADK tool context

        Returns:
            ToolResult with nutrition calculations
        """
        try:
            if not parsed_items:
                return ToolResult(
                    success=False,
                    error="No parsed items provided"
                )

            if len(parsed_items) > 10:
                return ToolResult(
                    success=False,
                    error="Too many items (max 10)"
                )

            nutrition_items = []
            total_calories = 0.0
            total_protein = 0.0
            total_carbs = 0.0
            total_fat = 0.0
            confidences = []

            for item in parsed_items:
                nutrition = await self._calculate_item_nutrition(item, tool_context)
                if nutrition:
                    nutrition_items.append(nutrition)
                    total_calories += nutrition.calories
                    total_protein += nutrition.protein_g
                    total_carbs += nutrition.carbs_g
                    total_fat += nutrition.fat_g
                    confidences.append(nutrition.confidence)
                else:
                    # Fallback with zero nutrition but low confidence
                    nutrition_items.append(NutritionItem(
                        food_name=item.get('parsed_food', 'unknown'),
                        calories=0.0,
                        protein_g=0.0,
                        confidence=0.1,
                        source="failed"
                    ))
                    confidences.append(0.1)

            # Calculate overall confidence as average
            confidence_score = sum(confidences) / len(confidences) if confidences else 0.0

            return ToolResult(
                success=True,
                data={
                    "total_calories": round(total_calories, 1),
                    "total_protein_g": round(total_protein, 1),
                    "total_carbs_g": round(total_carbs, 1),
                    "total_fat_g": round(total_fat, 1),
                    "items": [
                        {
                            "food_name": item.food_name,
                            "calories": round(item.calories, 1),
                            "protein_g": round(item.protein_g, 1),
                            "confidence": item.confidence,
                            "source": item.source
                        }
                        for item in nutrition_items
                    ],
                    "confidence_score": round(confidence_score, 2)
                }
            )

        except Exception as e:
            logger.error(f"Nutrition calculation failed: {e}")
            return ToolResult(
                success=False,
                error=f"Nutrition calculation failed: {str(e)}"
            )

    async def _calculate_item_nutrition(self, parsed_item: Dict[str, Any], tool_context: Optional[Any]) -> Optional[NutritionItem]:
        """
        Calculate nutrition for a single parsed food item using web search.

        Args:
            parsed_item: Parsed food item data
            tool_context: ADK tool context for web search

        Returns:
            NutritionItem or None if search fails
        """
        try:
            food_description = parsed_item.get('parsed_food', '')
            quantity = parsed_item.get('quantity', 1.0)
            unit = parsed_item.get('unit', 'piece')
            parse_confidence = parsed_item.get('confidence', 0.5)

            if not food_description:
                return None

            # Use web search to find nutrition data
            search_query = f"nutrition facts for {food_description} calories protein carbs fat per serving"
            
            # Import google_search here to avoid circular imports
            from google.adk.tools.google_search_tool import google_search
            
            # Perform web search
            search_result = await google_search.run_async(
                args={"query": search_query},
                tool_context=tool_context
            )

            if not search_result or not search_result.success:
                logger.warning(f"Web search failed for: {food_description}")
                # Try reference data as fallback
                reference_result = nutrition_reference.calculate_nutrition_from_reference(
                    food_description, quantity, unit
                )
                if reference_result:
                    logger.info(f"Using reference data for: {food_description}")
                    return NutritionItem(
                        food_name=reference_result['food_name'],
                        calories=reference_result['calories'],
                        protein_g=reference_result['protein_g'],
                        carbs_g=reference_result['carbs_g'],
                        fat_g=reference_result['fat_g'],
                        confidence=reference_result['confidence'] * parse_confidence,
                        source="reference_db"
                    )
                return None

            # Parse search results to extract nutrition data
            nutrition_data = self._parse_search_results(search_result.data, food_description)
            
            if not nutrition_data:
                logger.warning(f"Could not parse nutrition data for: {food_description}")
                # Try reference data as fallback
                reference_result = nutrition_reference.calculate_nutrition_from_reference(
                    food_description, quantity, unit
                )
                if reference_result:
                    logger.info(f"Using reference data for: {food_description}")
                    return NutritionItem(
                        food_name=reference_result['food_name'],
                        calories=reference_result['calories'],
                        protein_g=reference_result['protein_g'],
                        carbs_g=reference_result['carbs_g'],
                        fat_g=reference_result['fat_g'],
                        confidence=reference_result['confidence'] * parse_confidence,
                        source="reference_db"
                    )
                return None

            base_calories = nutrition_data.get('calories_per_serving', 0)
            base_protein = nutrition_data.get('protein_g_per_serving', 0)
            base_carbs = nutrition_data.get('carbs_g_per_serving', 0)
            base_fat = nutrition_data.get('fat_g_per_serving', 0)
            serving_size_g = nutrition_data.get('serving_size_g', 100)
            search_confidence = nutrition_data.get('confidence', 0.7)

            # Convert quantity to grams for calculation
            quantity_g = self._convert_to_grams(quantity, unit, serving_size_g)

            # Scale nutrition by quantity
            scale_factor = quantity_g / serving_size_g
            calories = base_calories * scale_factor
            protein = base_protein * scale_factor
            carbs = base_carbs * scale_factor
            fat = base_fat * scale_factor

            # Overall confidence combines parsing and search confidence
            overall_confidence = min(parse_confidence * search_confidence, 1.0)

            return NutritionItem(
                food_name=nutrition_data.get('food_name', food_description),
                calories=calories,
                protein_g=protein,
                carbs_g=carbs,
                fat_g=fat,
                confidence=overall_confidence,
                source="web_search"
            )

        except Exception as e:
            logger.error(f"Item nutrition calculation failed: {e}")
            return None

    def _parse_search_results(self, search_data: Dict[str, Any], food_name: str) -> Optional[Dict[str, Any]]:
        """
        Parse web search results to extract nutrition information.

        Args:
            search_data: Raw search results
            food_name: Name of the food item

        Returns:
            Dict with parsed nutrition data or None
        """
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
            # Look for patterns like "Calories: 250", "Protein: 15g", etc.
            calories_match = re.search(r'calories?\s*:\s*(\d+)', search_text, re.IGNORECASE)
            protein_match = re.search(r'protein\s*:\s*(\d+(?:\.\d+)?)\s*g', search_text, re.IGNORECASE)
            carbs_match = re.search(r'(?:carbs?|carbohydrates?)\s*:\s*(\d+(?:\.\d+)?)\s*g', search_text, re.IGNORECASE)
            fat_match = re.search(r'fat\s*:\s*(\d+(?:\.\d+)?)\s*g', search_text, re.IGNORECASE)

            # Extract serving size if available
            serving_match = re.search(r'serving\s*size\s*:\s*(\d+(?:\.\d+)?)\s*g', search_text, re.IGNORECASE)
            serving_size_g = float(serving_match.group(1)) if serving_match else 100.0

            nutrition_data = {
                'food_name': food_name,
                'serving_size_g': serving_size_g,
                'calories_per_serving': float(calories_match.group(1)) if calories_match else 0,
                'protein_g_per_serving': float(protein_match.group(1)) if protein_match else 0,
                'carbs_g_per_serving': float(carbs_match.group(1)) if carbs_match else 0,
                'fat_g_per_serving': float(fat_match.group(1)) if fat_match else 0,
                'confidence': 0.6  # Lower confidence for web search
            }

            # If we found at least calories, consider it valid
            if nutrition_data['calories_per_serving'] > 0:
                return nutrition_data

            return None

        except Exception as e:
            logger.error(f"Failed to parse search results: {e}")
            return None

    def _convert_to_grams(self, quantity: float, unit: str, serving_size_g: float) -> float:
        """
        Convert quantity and unit to grams.

        Args:
            quantity: Parsed quantity
            unit: Parsed unit
            serving_size_g: Base serving size in grams

        Returns:
            Quantity in grams
        """
        # Unit conversion factors (approximate)
        conversions = {
            'cup': 240,  # 1 cup ≈ 240g for most foods
            'tablespoon': 15,
            'teaspoon': 5,
            'pound': 453.6,
            'ounce': 28.35,
            'gram': 1,
            'kilogram': 1000,
            'liter': 1000,
            'milliliter': 1,
            'piece': serving_size_g,  # Use serving size for pieces
            'slice': serving_size_g * 0.3,  # Assume slice is 30% of serving
            'whole': serving_size_g,
            'half': serving_size_g * 0.5,
            'quarter': serving_size_g * 0.25
        }

        unit_lower = unit.lower()
        if unit_lower in conversions:
            return quantity * conversions[unit_lower]
        else:
            # Unknown unit, assume it's equivalent to serving size
            logger.warning(f"Unknown unit '{unit}', using serving size")
            return quantity * serving_size_g


# Create singleton instance
nutrition_calculator = MealNutritionCalculatorTool()


# Convenience function for direct use
async def calculate_meal_nutrition(
    parsed_items: List[Dict[str, Any]],
    meal_type: str,
    user_id: str,
    tool_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Calculate nutrition information for a batch of parsed food items.

    This matches the contract specification for nutrition calculation.

    Args:
        parsed_items: Parsed food items from parse_meal_batch
        meal_type: Type of meal
        user_id: User ID
        tool_context: Optional ADK tool context

    Returns:
        Dict with status, data, error
    """
    result = await nutrition_calculator.execute(
        parsed_items=parsed_items,
        meal_type=meal_type,
        user_id=user_id,
        tool_context=tool_context
    )

    return {
        "status": "success" if result.success else "error",
        "data": result.data,
        "error": result.error
    }


__all__ = ['MealNutritionCalculatorTool', 'nutrition_calculator', 'calculate_meal_nutrition']