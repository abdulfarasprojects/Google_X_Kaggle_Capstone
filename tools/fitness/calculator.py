"""
Volume calculation tools for fitness tracking.

This module provides tools for calculating workout volume, tracking progression,
and generating volume-based analytics for fitness logging.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import date, timedelta

from tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class VolumeCalculatorTool(BaseTool):
    """
    Tool for calculating workout volume and progression metrics.

    Calculates total volume from exercise sets, reps, and weights.
    Provides progression tracking and volume-based analytics.
    """

    def __init__(self):
        super().__init__(
            name="calculate_workout_volume",
            description="Calculate total workout volume and progression metrics from parsed exercises",
            parameters={
                "type": "object",
                "properties": {
                    "parsed_exercises": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "exercise_name": {"type": "string"},
                                "sets": {"type": "integer"},
                                "reps": {"type": "integer"},
                                "weight": {"type": ["number", "null"]},
                                "weight_unit": {"type": ["string", "null"]}
                            },
                            "required": ["exercise_name", "sets", "reps"]
                        },
                        "description": "List of parsed exercise objects"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "Telegram user ID for progression context"
                    },
                    "previous_workouts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "log_date": {"type": "string"},
                                "exercises": {"type": "array"}
                            }
                        },
                        "description": "Previous workout data for progression analysis"
                    }
                },
                "required": ["parsed_exercises", "user_id"]
            }
        )

    async def execute(
        self,
        parsed_exercises: List[Dict[str, Any]],
        user_id: str,
        previous_workouts: Optional[List[Dict[str, Any]]] = None,
        tool_context: Optional[Any] = None
    ) -> ToolResult:
        """
        Calculate workout volume and progression.

        Args:
            parsed_exercises: List of parsed exercise dictionaries
            user_id: User ID for context
            previous_workouts: Optional previous workout data for progression
            tool_context: ADK tool context

        Returns:
            ToolResult with volume calculations and progression
        """
        try:
            if not parsed_exercises:
                return ToolResult(
                    success=False,
                    error="No exercises provided for volume calculation"
                )

            # Calculate total volume
            total_volume = 0
            exercise_breakdown = []

            for exercise in parsed_exercises:
                exercise_name = exercise.get("exercise_name", "")
                sets = exercise.get("sets", 1)
                reps = exercise.get("reps", 1)
                weight = exercise.get("weight")

                # Calculate volume for this exercise
                if weight and weight > 0:
                    # Weighted exercise: sets × reps × weight
                    exercise_volume = sets * reps * weight
                else:
                    # Bodyweight exercise: sets × reps
                    exercise_volume = sets * reps

                total_volume += exercise_volume

                exercise_breakdown.append({
                    "exercise_name": exercise_name,
                    "sets": sets,
                    "reps": reps,
                    "weight": weight,
                    "volume": exercise_volume
                })

            # Calculate progression if previous data available
            progression_data = None
            if previous_workouts:
                progression_data = self._calculate_progression(
                    parsed_exercises, previous_workouts
                )

            return ToolResult(
                success=True,
                data={
                    "total_volume": total_volume,
                    "exercise_breakdown": exercise_breakdown,
                    "progression": progression_data,
                    "volume_category": self._categorize_volume(total_volume)
                }
            )

        except Exception as e:
            logger.error(f"Volume calculation failed: {e}")
            return ToolResult(
                success=False,
                error=f"Volume calculation failed: {str(e)}"
            )

    def _calculate_progression(
        self,
        current_exercises: List[Dict[str, Any]],
        previous_workouts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate progression metrics compared to previous workouts.

        Args:
            current_exercises: Current workout exercises
            previous_workouts: Previous workout data

        Returns:
            Dict with progression metrics
        """
        try:
            # Find the most recent similar workout (last 30 days)
            recent_workouts = []
            for workout in previous_workouts:
                workout_date = workout.get("log_date")
                if workout_date:
                    try:
                        workout_date_obj = date.fromisoformat(workout_date)
                        if (date.today() - workout_date_obj).days <= 30:
                            recent_workouts.append(workout)
                    except ValueError:
                        continue

            if not recent_workouts:
                return {"available": False, "message": "No recent workouts for comparison"}

            # Calculate progression for each exercise
            progression_exercises = []
            overall_trend = "stable"

            for current_ex in current_exercises:
                exercise_name = current_ex.get("exercise_name", "")
                current_sets = current_ex.get("sets", 1)
                current_reps = current_ex.get("reps", 1)
                current_weight = current_ex.get("weight")

                # Find previous performance for this exercise
                prev_performance = self._find_previous_exercise_performance(
                    exercise_name, recent_workouts
                )

                if prev_performance:
                    trend = self._compare_performance(
                        current_sets, current_reps, current_weight,
                        prev_performance
                    )
                    progression_exercises.append({
                        "exercise_name": exercise_name,
                        "trend": trend,
                        "previous": prev_performance,
                        "current": {
                            "sets": current_sets,
                            "reps": current_reps,
                            "weight": current_weight
                        }
                    })

                    # Update overall trend
                    if trend == "improved" and overall_trend == "stable":
                        overall_trend = "improved"
                    elif trend == "declined":
                        overall_trend = "declined"

            return {
                "available": True,
                "overall_trend": overall_trend,
                "exercise_progression": progression_exercises,
                "workouts_analyzed": len(recent_workouts)
            }

        except Exception as e:
            logger.error(f"Progression calculation failed: {e}")
            return {"available": False, "error": str(e)}

    def _find_previous_exercise_performance(
        self,
        exercise_name: str,
        previous_workouts: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Find the most recent performance data for an exercise.

        Args:
            exercise_name: Name of the exercise
            previous_workouts: Previous workout data

        Returns:
            Dict with previous performance or None
        """
        for workout in reversed(previous_workouts):  # Most recent first
            exercises = workout.get("exercises", [])
            for ex in exercises:
                if ex.get("exercise_name", "").lower() == exercise_name.lower():
                    return {
                        "sets": ex.get("sets", 1),
                        "reps": ex.get("reps", 1),
                        "weight": ex.get("weight"),
                        "log_date": workout.get("log_date")
                    }
        return None

    def _compare_performance(
        self,
        current_sets: int,
        current_reps: int,
        current_weight: Optional[float],
        previous: Dict[str, Any]
    ) -> str:
        """
        Compare current performance to previous.

        Args:
            current_sets: Current sets
            current_reps: Current reps
            current_weight: Current weight
            previous: Previous performance data

        Returns:
            "improved", "declined", or "stable"
        """
        prev_sets = previous.get("sets", 1)
        prev_reps = previous.get("reps", 1)
        prev_weight = previous.get("weight")

        # Calculate volume comparison
        current_volume = current_sets * current_reps * (current_weight or 1)
        prev_volume = prev_sets * prev_reps * (prev_weight or 1)

        # Significant improvement (>10% volume increase)
        if current_volume > prev_volume * 1.1:
            return "improved"
        # Significant decline (>10% volume decrease)
        elif current_volume < prev_volume * 0.9:
            return "declined"
        else:
            return "stable"

    def _categorize_volume(self, total_volume: int) -> str:
        """
        Categorize workout volume into descriptive categories.

        Args:
            total_volume: Total workout volume

        Returns:
            Volume category description
        """
        if total_volume < 100:
            return "light"
        elif total_volume < 500:
            return "moderate"
        elif total_volume < 1500:
            return "heavy"
        else:
            return "intense"


# Create singleton instance
volume_calculator_tool = VolumeCalculatorTool()


# Convenience function for direct use
async def calculate_workout_volume(
    parsed_exercises: List[Dict[str, Any]],
    user_id: str,
    previous_workouts: Optional[List[Dict[str, Any]]] = None,
    tool_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Calculate workout volume and progression metrics.

    This is the main API function that matches the contract specification.

    Args:
        parsed_exercises: List of parsed exercise dictionaries
        user_id: Telegram user ID for context
        previous_workouts: Optional previous workout data for progression
        tool_context: Optional ADK tool context

    Returns:
        Dict with status, data, and error fields
    """
    result = await volume_calculator_tool.execute(
        parsed_exercises=parsed_exercises,
        user_id=user_id,
        previous_workouts=previous_workouts,
        tool_context=tool_context
    )

    return {
        "status": "success" if result.success else "error",
        "data": result.data,
        "error": result.error
    }


__all__ = ['VolumeCalculatorTool', 'volume_calculator_tool', 'calculate_workout_volume']