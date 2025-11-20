"""
Trend analysis tools for progress tracking.

This module provides tools for analyzing trends in user data over time,
identifying patterns, and providing insights for weight loss progress.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from statistics import mean, stdev

from tools.base import BaseTool, ToolResult
from database.models import get_db, UserProfile, MealLog, WorkoutLog, WellnessLog
from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class TrendAnalysis:
    """Trend analysis results."""
    trend_direction: str  # 'improving', 'declining', 'stable', 'insufficient_data'
    confidence_level: float  # 0.0 to 1.0
    key_insights: List[str]
    recommendations: List[str]
    data_points: int


class TrendAnalyzerTool(BaseTool):
    """
    Tool for analyzing trends in user progress data.

    Provides statistical analysis of user metrics over time to identify
    patterns, improvements, and areas needing attention.
    """

    def __init__(self):
        super().__init__(
            name="analyze_progress_trends",
            description="Analyze trends in user progress data over time",
            parameters={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to analyze trends for"
                    },
                    "metric": {
                        "type": "string",
                        "enum": ["calories", "workouts", "sleep", "water", "steps", "streak"],
                        "description": "Metric to analyze trends for"
                    },
                    "days": {
                        "type": "integer",
                        "minimum": 7,
                        "maximum": 90,
                        "description": "Number of days to analyze (7-90)"
                    }
                },
                "required": ["user_id", "metric", "days"]
            }
        )

    async def execute(
        self,
        user_id: str,
        metric: str,
        days: int,
        tool_context: Optional[Any] = None
    ) -> ToolResult:
        """
        Analyze trends for a specific metric.

        Args:
            user_id: User ID to analyze
            metric: Metric to analyze ('calories', 'workouts', 'sleep', 'water', 'steps', 'streak')
            days: Number of days to analyze
            tool_context: ADK tool context

        Returns:
            ToolResult with trend analysis
        """
        try:
            if days < 7 or days > 90:
                return ToolResult(
                    success=False,
                    error="Days must be between 7 and 90"
                )

            db = get_db()
            try:
                # Get user profile
                user = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
                if not user:
                    return ToolResult(
                        success=False,
                        error=f"User not found: {user_id}"
                    )

                # Analyze trend for the metric
                analysis = await self._analyze_metric_trend(db, user, metric, days)

                return ToolResult(
                    success=True,
                    data={
                        "user_id": user_id,
                        "metric": metric,
                        "analysis_period_days": days,
                        "trend_direction": analysis.trend_direction,
                        "confidence_level": round(analysis.confidence_level, 2),
                        "key_insights": analysis.key_insights,
                        "recommendations": analysis.recommendations,
                        "data_points": analysis.data_points
                    }
                )

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            return ToolResult(
                success=False,
                error=f"Trend analysis failed: {str(e)}"
            )

    async def _analyze_metric_trend(
        self,
        db,
        user: UserProfile,
        metric: str,
        days: int
    ) -> TrendAnalysis:
        """
        Analyze trend for a specific metric.

        Args:
            db: Database session
            user: User profile
            metric: Metric name
            days: Analysis period

        Returns:
            TrendAnalysis object
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days-1)

        # Get data points for the metric
        data_points = self._get_metric_data(db, user, metric, start_date, end_date)

        if len(data_points) < 3:
            return TrendAnalysis(
                trend_direction="insufficient_data",
                confidence_level=0.0,
                key_insights=["Not enough data points for trend analysis"],
                recommendations=["Continue logging consistently for better insights"],
                data_points=len(data_points)
            )

        # Calculate trend
        trend_direction, confidence = self._calculate_trend(data_points)

        # Generate insights and recommendations
        insights = self._generate_insights(metric, trend_direction, data_points)
        recommendations = self._generate_recommendations(metric, trend_direction, data_points)

        return TrendAnalysis(
            trend_direction=trend_direction,
            confidence_level=confidence,
            key_insights=insights,
            recommendations=recommendations,
            data_points=len(data_points)
        )

    def _get_metric_data(self, db, user: UserProfile, metric: str, start_date: date, end_date: date) -> List[float]:
        """
        Get data points for a metric over the date range.

        Args:
            db: Database session
            user: User profile
            metric: Metric name
            start_date: Start of analysis period
            end_date: End of analysis period

        Returns:
            List of metric values (one per day)
        """
        data_points = []

        for current_date in [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]:
            if metric == "calories":
                # Sum calories for the day
                calories = db.query(MealLog.total_calories).filter(
                    MealLog.user_id == user.user_id,
                    MealLog.log_date == current_date
                ).all()
                value = sum(cal[0] for cal in calories)

            elif metric == "workouts":
                # Count workouts for the day
                value = db.query(WorkoutLog).filter(
                    WorkoutLog.user_id == user.user_id,
                    WorkoutLog.log_date == current_date
                ).count()

            elif metric == "sleep":
                # Average sleep for the day
                sleep = db.query(WellnessLog.sleep_hours).filter(
                    WellnessLog.user_id == user.user_id,
                    WellnessLog.log_date == current_date,
                    WellnessLog.sleep_hours > 0
                ).first()
                value = sleep[0] if sleep else 0

            elif metric == "water":
                # Water glasses for the day
                water = db.query(WellnessLog.water_glasses).filter(
                    WellnessLog.user_id == user.user_id,
                    WellnessLog.log_date == current_date,
                    WellnessLog.water_glasses > 0
                ).first()
                value = water[0] if water else 0

            elif metric == "steps":
                # Steps for the day
                steps = db.query(WellnessLog.steps_count).filter(
                    WellnessLog.user_id == user.user_id,
                    WellnessLog.log_date == current_date,
                    WellnessLog.steps_count > 0
                ).first()
                value = steps[0] if steps else 0

            elif metric == "streak":
                # This is cumulative, not daily - calculate streak up to this date
                value = self._calculate_streak_up_to_date(db, user, current_date)

            else:
                value = 0

            data_points.append(float(value))

        return data_points

    def _calculate_streak_up_to_date(self, db, user: UserProfile, current_date: date) -> int:
        """Calculate streak length up to a specific date."""
        streak = 0
        check_date = current_date

        for i in range(60):
            logs = db.query(MealLog).filter(
                MealLog.user_id == user.user_id,
                MealLog.log_date == check_date
            ).count()
            logs += db.query(WorkoutLog).filter(
                WorkoutLog.user_id == user.user_id,
                WorkoutLog.log_date == check_date
            ).count()
            logs += db.query(WellnessLog).filter(
                WellnessLog.user_id == user.user_id,
                WellnessLog.log_date == check_date
            ).count()

            if logs > 0:
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break

        return streak

    def _calculate_trend(self, data_points: List[float]) -> tuple[str, float]:
        """
        Calculate trend direction and confidence from data points.

        Args:
            data_points: List of metric values

        Returns:
            Tuple of (direction, confidence)
        """
        if len(data_points) < 3:
            return "insufficient_data", 0.0

        # Simple linear trend calculation
        n = len(data_points)
        x = list(range(n))
        y = data_points

        # Calculate slope using linear regression
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_xx = sum(xi * xi for xi in x)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)

        # Calculate R-squared for confidence
        y_mean = mean(y)
        ss_tot = sum((yi - y_mean) ** 2 for yi in y)
        ss_res = sum((yi - (slope * xi + (sum_y - slope * sum_x) / n)) ** 2 for xi, yi in zip(x, y))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Determine direction
        if abs(slope) < 0.01:  # Very flat
            direction = "stable"
        elif slope > 0.01:
            direction = "improving"
        else:
            direction = "declining"

        # Adjust confidence based on data variability
        if len(y) > 1:
            try:
                variability = stdev(y)
                if variability > 0:
                    # Lower confidence if data is highly variable
                    r_squared = r_squared * (1 - min(variability / mean(y), 0.5))
            except:
                pass

        return direction, min(r_squared, 1.0)

    def _generate_insights(self, metric: str, trend: str, data_points: List[float]) -> List[str]:
        """Generate key insights based on trend analysis."""
        insights = []

        avg_value = mean(data_points) if data_points else 0
        max_value = max(data_points) if data_points else 0
        min_value = min(data_points) if data_points else 0

        if metric == "calories":
            if trend == "improving":
                insights.append(f"Calorie logging is trending up (avg: {avg_value:.0f} cal/day)")
            elif trend == "declining":
                insights.append(f"Calorie logging is trending down (avg: {avg_value:.0f} cal/day)")
            else:
                insights.append(f"Calorie logging is stable (avg: {avg_value:.0f} cal/day)")

        elif metric == "workouts":
            if trend == "improving":
                insights.append(f"Workout frequency is increasing (avg: {avg_value:.1f} sessions/day)")
            elif trend == "declining":
                insights.append(f"Workout frequency is decreasing (avg: {avg_value:.1f} sessions/day)")
            else:
                insights.append(f"Workout frequency is consistent (avg: {avg_value:.1f} sessions/day)")

        elif metric == "sleep":
            if trend == "improving":
                insights.append(f"Sleep quality is improving (avg: {avg_value:.1f} hours/night)")
            elif trend == "declining":
                insights.append(f"Sleep quality is declining (avg: {avg_value:.1f} hours/night)")
            else:
                insights.append(f"Sleep quality is stable (avg: {avg_value:.1f} hours/night)")

        elif metric == "water":
            if trend == "improving":
                insights.append(f"Water intake is increasing (avg: {avg_value:.1f} glasses/day)")
            elif trend == "declining":
                insights.append(f"Water intake is decreasing (avg: {avg_value:.1f} glasses/day)")
            else:
                insights.append(f"Water intake is consistent (avg: {avg_value:.1f} glasses/day)")

        elif metric == "steps":
            if trend == "improving":
                insights.append(f"Step count is trending up (avg: {avg_value:.0f} steps/day)")
            elif trend == "declining":
                insights.append(f"Step count is trending down (avg: {avg_value:.0f} steps/day)")
            else:
                insights.append(f"Step count is stable (avg: {avg_value:.0f} steps/day)")

        elif metric == "streak":
            insights.append(f"Current streak is {int(max_value)} days")

        return insights

    def _generate_recommendations(self, metric: str, trend: str, data_points: List[float]) -> List[str]:
        """Generate recommendations based on trend analysis."""
        recommendations = []

        if metric == "calories":
            if trend == "declining":
                recommendations.append("Consider logging meals more consistently to track progress")
            elif trend == "stable" and mean(data_points) < 1500:
                recommendations.append("Ensure you're meeting your daily calorie goals for weight loss")

        elif metric == "workouts":
            if trend == "declining":
                recommendations.append("Try to maintain or increase workout frequency for better results")
            elif trend == "stable" and mean(data_points) < 0.5:
                recommendations.append("Consider adding more workout days for optimal weight loss")

        elif metric == "sleep":
            if trend == "declining" or mean(data_points) < 7:
                recommendations.append("Aim for 7-9 hours of sleep nightly for weight loss success")

        elif metric == "water":
            if trend == "declining" or mean(data_points) < 6:
                recommendations.append("Try to drink at least 8 glasses of water daily")

        elif metric == "steps":
            if trend == "declining" or mean(data_points) < 8000:
                recommendations.append("Aim for 10,000 steps daily for better health outcomes")

        if not recommendations:
            recommendations.append("Keep up the great work with consistent logging!")

        return recommendations


# Create singleton instance
trend_analyzer = TrendAnalyzerTool()


# Convenience function for direct use
async def analyze_progress_trends(
    user_id: str,
    metric: str,
    days: int,
    tool_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Analyze trends in user progress data.

    Args:
        user_id: User ID
        metric: Metric to analyze
        days: Number of days to analyze
        tool_context: Optional ADK tool context

    Returns:
        Dict with status, data, error
    """
    result = await trend_analyzer.execute(
        user_id=user_id,
        metric=metric,
        days=days,
        tool_context=tool_context
    )

    return {
        "status": "success" if result.success else "error",
        "data": result.data,
        "error": result.error
    }


__all__ = ['TrendAnalyzerTool', 'trend_analyzer', 'analyze_progress_trends']