"""
Workout storage tools for Weight Loss Chat Agent.

This module provides tools for storing calculated workout data
in the database after processing.
"""

import logging
from typing import List, Dict, Any, Optional

from tools.base import BaseTool, ToolResult
from database.workout_manager import workout_manager

logger = logging.getLogger(__name__)


class WorkoutStorageTool(BaseTool):
    """
    Tool for storing calculated workout data in the database.

    Takes workout calculation results and stores them as workout logs.
    """

    def __init__(self):
        super().__init__(
            name="store_workout_log",
            description="Store a calculated workout with volume data in the database",
            parameters={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User identifier"
                    },
                    "exercises": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "sets": {"type": "integer"},
                                "reps": {"type": "integer"},
                                "weight": {"type": "number"},
                                "duration": {"type": "number"}
                            }
                        },
                        "description": "List of exercises performed"
                    },
                    "total_volume": {
                        "type": "integer",
                        "description": "Calculated total volume score"
                    },
                    "progression_suggestion": {
                        "type": "string",
                        "description": "AI-generated progression recommendation"
                    }
                },
                "required": ["user_id", "exercises", "total_volume"]
            }
        )

    async def execute(
        self,
        user_id: str,
        exercises: List[Dict[str, Any]],
        total_volume: int,
        progression_suggestion: Optional[str] = None,
        tool_context: Optional[Any] = None
    ) -> ToolResult:
        """
        Store a workout log in the database.

        Args:
            user_id: User identifier
            exercises: List of exercises performed
            total_volume: Calculated total volume score
            progression_suggestion: Optional progression recommendation
            tool_context: ADK tool context

        Returns:
            ToolResult with storage confirmation
        """
        try:
            # Store the workout
            log_id = workout_manager.create_workout_log(
                user_id=user_id,
                exercises=exercises,
                total_volume=total_volume,
                progression_suggestion=progression_suggestion
            )

            if log_id:
                logger.info(f"Successfully stored workout log: {log_id}")
                return ToolResult(
                    success=True,
                    data={
                        "log_id": log_id,
                        "total_volume": total_volume,
                        "exercises_count": len(exercises),
                        "progression_suggestion": progression_suggestion
                    }
                )
            else:
                logger.error("Failed to store workout log")
                return ToolResult(
                    success=False,
                    error="Failed to store workout log in database"
                )

        except Exception as e:
            logger.error(f"Workout storage failed: {e}")
            return ToolResult(
                success=False,
                error=f"Workout storage failed: {str(e)}"
            )


# Create singleton instance
workout_storage_tool = WorkoutStorageTool()


# Convenience function for direct use
async def store_workout_log(
    user_id: str,
    exercises: List[Dict[str, Any]],
    total_volume: int,
    progression_suggestion: Optional[str] = None,
    tool_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Store a workout log with calculated volume data.

    Args:
        user_id: User identifier
        exercises: List of exercises performed
        total_volume: Calculated total volume
        progression_suggestion: Optional progression suggestion
        tool_context: Optional ADK tool context

    Returns:
        Dict with status and data
    """
    result = await workout_storage_tool.execute(
        user_id=user_id,
        exercises=exercises,
        total_volume=total_volume,
        progression_suggestion=progression_suggestion,
        tool_context=tool_context
    )

    return {
        "status": "success" if result.success else "error",
        "data": result.data,
        "error": result.error
    }


__all__ = ['WorkoutStorageTool', 'workout_storage_tool', 'store_workout_log']