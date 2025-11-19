"""
Wellness correlation tools for analyzing relationships between wellness metrics and outcomes.

This module provides tools for correlating sleep, water intake, and steps with
weight loss progress, workout performance, and overall health trends.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import date, timedelta

from tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class WellnessCorrelationTool(BaseTool):
    """
    Tool for analyzing correlations between wellness metrics and health outcomes.

    Correlates sleep quality, water intake, and steps with weight trends,
    workout performance, and provides actionable insights.
    """

    def __init__(self):
        super().__init__(
            name="analyze_wellness_correlations",
            description="Analyze correlations between wellness metrics and health outcomes",
            parameters={
                "type": "object",
                "properties": {
                    "wellness_data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "log_date": {"type": "string"},
                                "sleep_hours": {"type": ["number", "null"]},
                                "sleep_quality": {"type": ["integer", "null"]},
                                "water_glasses": {"type": ["number", "null"]},
                                "steps_count": {"type": ["integer", "null"]}
                            }
                        },
                        "description": "Historical wellness data for correlation analysis"
                    },
                    "weight_data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "log_date": {"type": "string"},
                                "weight_kg": {"type": "number"}
                            }
                        },
                        "description": "Weight tracking data for correlation with wellness"
                    },
                    "workout_data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "log_date": {"type": "string"},
                                "total_volume": {"type": "integer"}
                            }
                        },
                        "description": "Workout volume data for performance correlation"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "Telegram user ID for context"
                    }
                },
                "required": ["user_id"]
            }
        )

    async def execute(
        self,
        wellness_data: Optional[List[Dict[str, Any]]] = None,
        weight_data: Optional[List[Dict[str, Any]]] = None,
        workout_data: Optional[List[Dict[str, Any]]] = None,
        user_id: str = "",
        tool_context: Optional[Any] = None
    ) -> ToolResult:
        """
        Analyze wellness correlations with health outcomes.

        Args:
            wellness_data: Historical wellness metrics
            weight_data: Weight tracking data
            workout_data: Workout performance data
            user_id: User ID for context
            tool_context: ADK tool context

        Returns:
            ToolResult with correlation analysis and insights
        """
        try:
            correlations = {}

            # Sleep correlations
            if wellness_data:
                sleep_correlations = self._analyze_sleep_correlations(
                    wellness_data, weight_data, workout_data
                )
                correlations["sleep"] = sleep_correlations

            # Water correlations
            if wellness_data and weight_data:
                water_correlations = self._analyze_water_correlations(
                    wellness_data, weight_data
                )
                correlations["water"] = water_correlations

            # Steps correlations
            if wellness_data and weight_data:
                steps_correlations = self._analyze_steps_correlations(
                    wellness_data, weight_data
                )
                correlations["steps"] = steps_correlations

            # Generate insights
            insights = self._generate_correlation_insights(correlations)

            return ToolResult(
                success=True,
                data={
                    "correlations": correlations,
                    "insights": insights,
                    "data_quality": self._assess_data_quality(wellness_data, weight_data, workout_data)
                }
            )

        except Exception as e:
            logger.error(f"Wellness correlation analysis failed: {e}")
            return ToolResult(
                success=False,
                error=f"Wellness correlation analysis failed: {str(e)}"
            )

    def _analyze_sleep_correlations(
        self,
        wellness_data: List[Dict[str, Any]],
        weight_data: Optional[List[Dict[str, Any]]] = None,
        workout_data: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Analyze correlations between sleep and health outcomes.

        Args:
            wellness_data: Sleep data
            weight_data: Weight data for correlation
            workout_data: Workout data for correlation

        Returns:
            Dict with sleep correlation analysis
        """
        # Extract sleep data
        sleep_entries = []
        for entry in wellness_data:
            if entry.get("sleep_hours") is not None:
                sleep_entries.append({
                    "date": entry["log_date"],
                    "hours": entry["sleep_hours"],
                    "quality": entry.get("sleep_quality")
                })

        if len(sleep_entries) < 3:
            return {"available": False, "message": "Insufficient sleep data for correlation analysis"}

        # Calculate averages
        avg_sleep = sum(e["hours"] for e in sleep_entries) / len(sleep_entries)
        avg_quality = sum(e["quality"] for e in sleep_entries if e["quality"]) / len([e for e in sleep_entries if e["quality"]])

        correlations = {
            "available": True,
            "average_sleep_hours": round(avg_sleep, 1),
            "average_sleep_quality": round(avg_quality, 1) if avg_quality else None,
            "sleep_consistency": self._calculate_consistency([e["hours"] for e in sleep_entries]),
            "insights": []
        }

        # Sleep and weight correlation
        if weight_data and len(weight_data) >= 3:
            sleep_weight_corr = self._correlate_sleep_weight(sleep_entries, weight_data)
            correlations["weight_correlation"] = sleep_weight_corr

            if sleep_weight_corr["correlation"] > 0.3:
                correlations["insights"].append("Poor sleep appears linked to weight gain plateaus")
            elif sleep_weight_corr["correlation"] < -0.3:
                correlations["insights"].append("Good sleep patterns correlate with weight loss progress")

        # Sleep and workout correlation
        if workout_data and len(workout_data) >= 3:
            sleep_workout_corr = self._correlate_sleep_workout(sleep_entries, workout_data)
            correlations["workout_correlation"] = sleep_workout_corr

            if sleep_workout_corr["correlation"] < -0.3:
                correlations["insights"].append("Poor sleep may be impacting workout performance")

        # Sleep quality insights
        if avg_sleep < 7:
            correlations["insights"].append("Average sleep is below recommended 7-9 hours")
        if avg_quality and avg_quality < 6:
            correlations["insights"].append("Sleep quality could be improved - consider sleep hygiene")

        return correlations

    def _analyze_water_correlations(
        self,
        wellness_data: List[Dict[str, Any]],
        weight_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze correlations between water intake and weight.

        Args:
            wellness_data: Water intake data
            weight_data: Weight data

        Returns:
            Dict with water correlation analysis
        """
        # Extract water data
        water_entries = []
        for entry in wellness_data:
            if entry.get("water_glasses") is not None:
                water_entries.append({
                    "date": entry["log_date"],
                    "glasses": entry["water_glasses"]
                })

        if len(water_entries) < 3:
            return {"available": False, "message": "Insufficient water data for correlation analysis"}

        avg_water = sum(e["glasses"] for e in water_entries) / len(water_entries)

        correlations = {
            "available": True,
            "average_water_glasses": round(avg_water, 1),
            "water_consistency": self._calculate_consistency([e["glasses"] for e in water_entries]),
            "insights": []
        }

        # Water and weight correlation (hydration can affect weight measurements)
        if len(weight_data) >= 3:
            water_weight_corr = self._correlate_water_weight(water_entries, weight_data)
            correlations["weight_correlation"] = water_weight_corr

        # Hydration insights
        if avg_water < 6:
            correlations["insights"].append("Water intake is below recommended 6-8 glasses per day")
        elif avg_water > 12:
            correlations["insights"].append("Water intake is very high - ensure it's not excessive")

        return correlations

    def _analyze_steps_correlations(
        self,
        wellness_data: List[Dict[str, Any]],
        weight_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze correlations between steps and weight.

        Args:
            wellness_data: Steps data
            weight_data: Weight data

        Returns:
            Dict with steps correlation analysis
        """
        # Extract steps data
        steps_entries = []
        for entry in wellness_data:
            if entry.get("steps_count") is not None:
                steps_entries.append({
                    "date": entry["log_date"],
                    "steps": entry["steps_count"]
                })

        if len(steps_entries) < 3:
            return {"available": False, "message": "Insufficient steps data for correlation analysis"}

        avg_steps = sum(e["steps"] for e in steps_entries) / len(steps_entries)

        correlations = {
            "available": True,
            "average_steps": int(avg_steps),
            "steps_consistency": self._calculate_consistency([e["steps"] for e in steps_entries]),
            "insights": []
        }

        # Steps and weight correlation
        if len(weight_data) >= 3:
            steps_weight_corr = self._correlate_steps_weight(steps_entries, weight_data)
            correlations["weight_correlation"] = steps_weight_corr

            if steps_weight_corr["correlation"] < -0.2:
                correlations["insights"].append("Higher step counts correlate with weight loss progress")

        # Activity level insights
        if avg_steps < 5000:
            correlations["insights"].append("Step count suggests sedentary lifestyle - consider increasing daily activity")
        elif avg_steps > 10000:
            correlations["insights"].append("Excellent activity level! Keep up the good work")

        return correlations

    def _correlate_sleep_weight(self, sleep_entries: List[Dict[str, Any]], weight_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate correlation between sleep and weight changes."""
        # Simple correlation calculation
        paired_data = []
        for sleep in sleep_entries:
            for weight in weight_data:
                if sleep["date"] == weight.get("log_date"):
                    paired_data.append((sleep["hours"], weight["weight_kg"]))
                    break

        if len(paired_data) < 3:
            return {"correlation": 0, "sample_size": len(paired_data), "interpretation": "insufficient_data"}

        # Calculate Pearson correlation coefficient approximation
        correlation = self._calculate_correlation([p[0] for p in paired_data], [p[1] for p in paired_data])

        interpretation = "neutral"
        if correlation > 0.3:
            interpretation = "poor_sleep_linked_to_higher_weight"
        elif correlation < -0.3:
            interpretation = "good_sleep_linked_to_weight_loss"

        return {
            "correlation": round(correlation, 2),
            "sample_size": len(paired_data),
            "interpretation": interpretation
        }

    def _correlate_sleep_workout(self, sleep_entries: List[Dict[str, Any]], workout_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate correlation between sleep and workout performance."""
        paired_data = []
        for sleep in sleep_entries:
            for workout in workout_data:
                if sleep["date"] == workout.get("log_date"):
                    paired_data.append((sleep["hours"], workout["total_volume"]))
                    break

        if len(paired_data) < 3:
            return {"correlation": 0, "sample_size": len(paired_data), "interpretation": "insufficient_data"}

        correlation = self._calculate_correlation([p[0] for p in paired_data], [p[1] for p in paired_data])

        interpretation = "neutral"
        if correlation < -0.3:
            interpretation = "poor_sleep_impacts_performance"

        return {
            "correlation": round(correlation, 2),
            "sample_size": len(paired_data),
            "interpretation": interpretation
        }

    def _correlate_water_weight(self, water_entries: List[Dict[str, Any]], weight_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate correlation between water intake and weight."""
        paired_data = []
        for water in water_entries:
            for weight in weight_data:
                if water["date"] == weight.get("log_date"):
                    paired_data.append((water["glasses"], weight["weight_kg"]))
                    break

        if len(paired_data) < 3:
            return {"correlation": 0, "sample_size": len(paired_data), "interpretation": "insufficient_data"}

        correlation = self._calculate_correlation([p[0] for p in paired_data], [p[1] for p in paired_data])

        return {
            "correlation": round(correlation, 2),
            "sample_size": len(paired_data),
            "interpretation": "hydration_effects" if abs(correlation) > 0.2 else "neutral"
        }

    def _correlate_steps_weight(self, steps_entries: List[Dict[str, Any]], weight_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate correlation between steps and weight."""
        paired_data = []
        for steps in steps_entries:
            for weight in weight_data:
                if steps["date"] == weight.get("log_date"):
                    paired_data.append((steps["steps"], weight["weight_kg"]))
                    break

        if len(paired_data) < 3:
            return {"correlation": 0, "sample_size": len(paired_data), "interpretation": "insufficient_data"}

        correlation = self._calculate_correlation([p[0] for p in paired_data], [p[1] for p in paired_data])

        interpretation = "neutral"
        if correlation < -0.2:
            interpretation = "more_activity_linked_to_weight_loss"

        return {
            "correlation": round(correlation, 2),
            "sample_size": len(paired_data),
            "interpretation": interpretation
        }

    def _calculate_correlation(self, x_values: List[float], y_values: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0

        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        sum_y2 = sum(y * y for y in y_values)

        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y)) ** 0.5

        return numerator / denominator if denominator != 0 else 0

    def _calculate_consistency(self, values: List[float]) -> str:
        """Calculate consistency rating for a metric."""
        if len(values) < 3:
            return "unknown"

        avg = sum(values) / len(values)
        variance = sum((v - avg) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5

        cv = std_dev / avg if avg > 0 else 0  # Coefficient of variation

        if cv < 0.1:
            return "very_consistent"
        elif cv < 0.2:
            return "consistent"
        elif cv < 0.3:
            return "moderate"
        else:
            return "inconsistent"

    def _generate_correlation_insights(self, correlations: Dict[str, Any]) -> List[str]:
        """Generate actionable insights from correlation analysis."""
        insights = []

        # Sleep insights
        if "sleep" in correlations and correlations["sleep"]["available"]:
            sleep_data = correlations["sleep"]
            if sleep_data["average_sleep_hours"] < 7:
                insights.append("Consider prioritizing sleep - aim for 7-9 hours per night")
            if sleep_data.get("weight_correlation", {}).get("interpretation") == "poor_sleep_linked_to_higher_weight":
                insights.append("Poor sleep may be hindering weight loss progress")

        # Water insights
        if "water" in correlations and correlations["water"]["available"]:
            water_data = correlations["water"]
            if water_data["average_water_glasses"] < 6:
                insights.append("Increasing water intake may support weight loss efforts")

        # Steps insights
        if "steps" in correlations and correlations["steps"]["available"]:
            steps_data = correlations["steps"]
            if steps_data["average_steps"] < 5000:
                insights.append("Increasing daily steps could accelerate weight loss")

        return insights

    def _assess_data_quality(self, wellness_data, weight_data, workout_data) -> Dict[str, Any]:
        """Assess the quality and completeness of available data."""
        quality = {
            "wellness_entries": len(wellness_data) if wellness_data else 0,
            "weight_entries": len(weight_data) if weight_data else 0,
            "workout_entries": len(workout_data) if workout_data else 0,
            "data_completeness": "poor"
        }

        total_entries = quality["wellness_entries"] + quality["weight_entries"] + quality["workout_entries"]

        if total_entries > 20:
            quality["data_completeness"] = "good"
        elif total_entries > 10:
            quality["data_completeness"] = "moderate"

        return quality


# Create singleton instance
wellness_correlation_tool = WellnessCorrelationTool()


# Convenience function for direct use
async def analyze_wellness_correlations(
    wellness_data: Optional[List[Dict[str, Any]]] = None,
    weight_data: Optional[List[Dict[str, Any]]] = None,
    workout_data: Optional[List[Dict[str, Any]]] = None,
    user_id: str = "",
    tool_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Analyze correlations between wellness metrics and health outcomes.

    This is the main API function that matches the contract specification.

    Args:
        wellness_data: Historical wellness metrics
        weight_data: Weight tracking data
        workout_data: Workout performance data
        user_id: Telegram user ID for context
        tool_context: Optional ADK tool context

    Returns:
        Dict with status, data, and error fields
    """
    result = await wellness_correlation_tool.execute(
        wellness_data=wellness_data,
        weight_data=weight_data,
        workout_data=workout_data,
        user_id=user_id,
        tool_context=tool_context
    )

    return {
        "status": "success" if result.success else "error",
        "data": result.data,
        "error": result.error
    }


__all__ = ['WellnessCorrelationTool', 'wellness_correlation_tool', 'analyze_wellness_correlations']