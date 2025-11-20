"""
Meal storage tools for Weight Loss Chat Agent.

This module provides tools for storing calculated meal nutrition data
in the database after processing.
"""

import logging
from typing import List, Dict, Any, Optional

from tools.base import BaseTool, ToolResult
from database.meal_manager import meal_manager

logger = logging.getLogger(__name__)


class MealStorageTool(BaseTool):
    """
    Tool for storing calculated meal nutrition data in the database.

    Takes nutrition calculation results and stores them as meal logs.
    """

    def __init__(self):
        super().__init__(
            name="store_meal_log",
            description="Store a calculated meal with nutrition data in the database",
            parameters={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier"
                    },
                    "meal_type": {
                        "type": "string",
                        "enum": ["breakfast", "lunch", "dinner", "snack"],
                        "description": "Type of meal"
                    },
                    "food_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "food_name": {"type": "string"},
                                "calories": {"type": "number"},
                                "protein_g": {"type": "number"},
                                "confidence": {"type": "number"}
                            }
                        },
                        "description": "List of food items with nutrition data"
                    },
                    "total_calories": {
                        "type": "number",
                        "description": "Total calories for the meal"
                    },
                    "total_protein_g": {
                        "type": "number",
                        "description": "Total protein in grams"
                    },
                    "confidence_score": {
                        "type": "number",
                        "description": "Overall confidence score for the meal"
                    }
                },
                "required": ["user_id", "meal_type", "food_items", "total_calories", "total_protein_g", "confidence_score"]
            }
        )

    async def execute(
        self,
        user_id: str,
        meal_type: str,
        food_items: List[Dict[str, Any]],
        total_calories: float,
        total_protein_g: float,
        confidence_score: float,
        tool_context: Optional[Any] = None
    ) -> ToolResult:
        """
        Store a meal log in the database.

        Args:
            user_id: User identifier
            meal_type: Type of meal
            food_items: List of food items with nutrition data
            total_calories: Total calories for the meal
            total_protein_g: Total protein in grams
            confidence_score: Overall confidence score
            tool_context: ADK tool context

        Returns:
            ToolResult with storage confirmation
        """
        try:
            # Convert food items to the format expected by meal_manager
            formatted_items = []
            for item in food_items:
                formatted_items.append({
                    "name": item.get("food_name", "Unknown food"),
                    "calories": item.get("calories", 0),
                    "protein_g": item.get("protein_g", 0),
                    "confidence": item.get("confidence", 0.5),
                    "source": item.get("source", "calculated")
                })

            # Store the meal
            log_id = meal_manager.create_meal_log(
                user_id=user_id,
                meal_type=meal_type,
                food_items=formatted_items,
                total_calories=total_calories,
                total_protein_g=total_protein_g,
                confidence_score=confidence_score
            )

            if log_id:
                logger.info(f"Successfully stored meal log: {log_id}")
                return ToolResult(
                    success=True,
                    data={
                        "log_id": log_id,
                        "meal_type": meal_type,
                        "total_calories": total_calories,
                        "total_protein_g": total_protein_g,
                        "confidence_score": confidence_score,
                        "items_count": len(food_items)
                    }
                )
            else:
                logger.error("Failed to store meal log")
                return ToolResult(
                    success=False,
                    error="Failed to store meal log in database"
                )

        except Exception as e:
            logger.error(f"Meal storage failed: {e}")
            return ToolResult(
                success=False,
                error=f"Meal storage failed: {str(e)}"
            )


# Create singleton instance
meal_storage_tool = MealStorageTool()


# Convenience function for direct use
async def store_meal_log(
    user_id: str,
    meal_type: str,
    food_items: List[Dict[str, Any]],
    total_calories: float,
    total_protein_g: float,
    confidence_score: float,
    tool_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Store a meal log with calculated nutrition data.

    Args:
        user_id: User identifier
        meal_type: Type of meal
        food_items: Food items with nutrition data
        total_calories: Total calories
        total_protein_g: Total protein in grams
        confidence_score: Confidence score
        tool_context: Optional ADK tool context

    Returns:
        Dict with status and data
    """
    result = await meal_storage_tool.execute(
        user_id=user_id,
        meal_type=meal_type,
        food_items=food_items,
        total_calories=total_calories,
        total_protein_g=total_protein_g,
        confidence_score=confidence_score,
        tool_context=tool_context
    )

    return {
        "status": "success" if result.success else "error",
        "data": result.data,
        "error": result.error
    }


__all__ = ['MealStorageTool', 'meal_storage_tool', 'store_meal_log']