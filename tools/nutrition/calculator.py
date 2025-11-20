"""
Nutrition calculation tools for meal analysis.

This module provides tools for calculating nutrition information from parsed
food items. Uses web search to find accurate calorie and macronutrient data.
"""

import logging
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
            description="Calculate nutrition information for a batch of parsed food items using reference database",
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
            timeout_seconds=5  # Faster with reference data
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
        Calculate nutrition for a single parsed food item using reference data.

        Args:
            parsed_item: Parsed food item data
            tool_context: ADK tool context (not used for reference data)

        Returns:
            NutritionItem or None if lookup fails
        """
        try:
            food_description = parsed_item.get('parsed_food', '')
            quantity = parsed_item.get('quantity', 1.0)
            unit = parsed_item.get('unit', 'serving')
            parse_confidence = parsed_item.get('confidence', 0.5)

            if not food_description:
                return None

            # Use reference data for nutrition lookup
            reference_result = nutrition_reference.calculate_nutrition_from_reference(
                food_description, quantity, unit
            )

            if not reference_result:
                logger.warning(f"No reference data found for: {food_description}")
                return None

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

        except Exception as e:
            logger.error(f"Item nutrition calculation failed: {e}")
            return None


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