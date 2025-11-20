"""
Progression suggestion tools for fitness tracking.

This module provides AI-powered progression suggestions based on workout history,
current performance, and fitness best practices.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import date, timedelta

from tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class ProgressionSuggesterTool(BaseTool):
    """
    Tool for generating AI-powered progression suggestions.

    Analyzes workout history and current performance to suggest appropriate
    progression strategies for strength training and conditioning.
    """

    def __init__(self):
        super().__init__(
            name="suggest_workout_progression",
            description="Generate AI-powered progression suggestions based on workout history and performance",
            parameters={
                "type": "object",
                "properties": {
                    "current_exercises": {
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
                        "description": "Current workout exercises"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "Telegram user ID for personalization"
                    },
                    "workout_history": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "log_date": {"type": "string"},
                                "exercises": {"type": "array"}
                            }
                        },
                        "description": "Historical workout data for analysis"
                    },
                    "user_profile": {
                        "type": "object",
                        "properties": {
                            "activity_level": {"type": "string"},
                            "age": {"type": "integer"}
                        },
                        "description": "User profile for personalized suggestions"
                    }
                },
                "required": ["current_exercises", "user_id"]
            }
        )

        # Exercise categories for progression strategies
        self.EXERCISE_CATEGORIES = {
            # Compound lifts (focus on progressive overload)
            'compound': [
                'squats', 'deadlifts', 'bench press', 'overhead press',
                'pull-ups', 'rows', 'lunges', 'dips'
            ],
            # Isolation exercises (focus on rep progression)
            'isolation': [
                'bicep curls', 'tricep extensions', 'lateral raises',
                'leg extensions', 'calf raises', 'shoulder press'
            ],
            # Bodyweight exercises (focus on rep/difficulty progression)
            'bodyweight': [
                'push-ups', 'pull-ups', 'burpees', 'mountain climbers',
                'planks', 'jumping jacks'
            ]
        }

        # Progression strategies by category
        self.PROGRESSION_STRATEGIES = {
            'compound': [
                "Increase weight by 5-10 lbs when you can complete all sets/reps with good form",
                "Add 1-2 reps per set when weight increase isn't possible",
                "Increase sets from 3 to 4 when reps and weight are maxed",
                "Consider technique improvements before weight increases"
            ],
            'isolation': [
                "Increase reps by 2-3 per set when you reach the top of your rep range",
                "Add weight when you can complete 12+ reps with perfect form",
                "Increase sets from 3 to 4 for additional volume",
                "Focus on time under tension for muscle growth"
            ],
            'bodyweight': [
                "Increase reps by 2-5 per set when you reach current max",
                "Progress to more difficult variations (e.g., decline push-ups)",
                "Add pauses or slow eccentrics for increased difficulty",
                "Increase sets or add weight when bodyweight becomes too easy"
            ]
        }

    async def execute(
        self,
        current_exercises: List[Dict[str, Any]],
        user_id: str,
        workout_history: Optional[List[Dict[str, Any]]] = None,
        user_profile: Optional[Dict[str, Any]] = None,
        tool_context: Optional[Any] = None
    ) -> ToolResult:
        """
        Generate progression suggestions for the current workout.

        Args:
            current_exercises: Current workout exercises
            user_id: User ID for context
            workout_history: Optional historical workout data
            user_profile: Optional user profile data
            tool_context: ADK tool context

        Returns:
            ToolResult with progression suggestions
        """
        try:
            if not current_exercises:
                return ToolResult(
                    success=False,
                    error="No exercises provided for progression analysis"
                )

            suggestions = []

            for exercise in current_exercises:
                exercise_name = exercise.get("exercise_name", "").lower()
                sets = exercise.get("sets", 1)
                reps = exercise.get("reps", 1)
                weight = exercise.get("weight")

                # Analyze progression potential
                progression_analysis = self._analyze_exercise_progression(
                    exercise_name, sets, reps, weight, workout_history
                )

                # Generate suggestion
                suggestion = self._generate_exercise_suggestion(
                    exercise_name, sets, reps, weight, progression_analysis, user_profile
                )

                suggestions.append({
                    "exercise_name": exercise_name,
                    "current_performance": {
                        "sets": sets,
                        "reps": reps,
                        "weight": weight
                    },
                    "progression_analysis": progression_analysis,
                    "suggestion": suggestion
                })

            # Generate overall workout suggestion
            overall_suggestion = self._generate_overall_suggestion(
                current_exercises, workout_history
            )

            return ToolResult(
                success=True,
                data={
                    "exercise_suggestions": suggestions,
                    "overall_suggestion": overall_suggestion,
                    "progression_focus": self._determine_progression_focus(suggestions)
                }
            )

        except Exception as e:
            logger.error(f"Progression suggestion failed: {e}")
            return ToolResult(
                success=False,
                error=f"Progression suggestion failed: {str(e)}"
            )

    def _analyze_exercise_progression(
        self,
        exercise_name: str,
        current_sets: int,
        current_reps: int,
        current_weight: Optional[float],
        workout_history: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Analyze progression potential for an exercise.

        Args:
            exercise_name: Name of the exercise
            current_sets: Current number of sets
            current_reps: Current reps per set
            current_weight: Current weight (if applicable)
            workout_history: Historical workout data

        Returns:
            Dict with progression analysis
        """
        category = self._categorize_exercise(exercise_name)

        # Default analysis
        analysis = {
            "category": category,
            "progression_potential": "moderate",
            "recommended_action": "maintain",
            "reasoning": "Insufficient history for detailed analysis"
        }

        if not workout_history:
            return analysis

        # Find recent performances (last 30 days)
        recent_performances = []
        for workout in workout_history[-10:]:  # Last 10 workouts
            workout_date = workout.get("log_date")
            if workout_date:
                try:
                    workout_date_obj = date.fromisoformat(workout_date)
                    if (date.today() - workout_date_obj).days <= 30:
                        for ex in workout.get("exercises", []):
                            if ex.get("exercise_name", "").lower() == exercise_name.lower():
                                recent_performances.append({
                                    "date": workout_date,
                                    "sets": ex.get("sets", 1),
                                    "reps": ex.get("reps", 1),
                                    "weight": ex.get("weight")
                                })
                except ValueError:
                    continue

        if len(recent_performances) < 2:
            return analysis

        # Analyze trend
        trend = self._calculate_trend(recent_performances, current_sets, current_reps, current_weight)

        # Determine progression potential
        if trend == "improving":
            analysis.update({
                "progression_potential": "high",
                "recommended_action": "increase_load",
                "reasoning": "Consistent improvement over recent workouts"
            })
        elif trend == "plateau":
            analysis.update({
                "progression_potential": "moderate",
                "recommended_action": "deload_or_vary",
                "reasoning": "Performance has stabilized, consider deload or variation"
            })
        elif trend == "declining":
            analysis.update({
                "progression_potential": "low",
                "recommended_action": "recovery_focus",
                "reasoning": "Recent performance decline, focus on recovery"
            })

        return analysis

    def _generate_exercise_suggestion(
        self,
        exercise_name: str,
        sets: int,
        reps: int,
        weight: Optional[float],
        analysis: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]]
    ) -> str:
        """
        Generate a specific suggestion for an exercise.

        Args:
            exercise_name: Name of the exercise
            sets: Current sets
            reps: Current reps
            weight: Current weight
            analysis: Progression analysis
            user_profile: User profile data

        Returns:
            Suggestion string
        """
        category = analysis.get("category", "compound")
        action = analysis.get("recommended_action", "maintain")

        strategies = self.PROGRESSION_STRATEGIES.get(category, [])

        if not strategies:
            return f"Continue with current {exercise_name} routine and track progress."

        # Select appropriate strategy based on action
        if action == "increase_load":
            if weight and weight > 0:
                return f"Great progress on {exercise_name}! Next week, try increasing weight by 5-10 lbs while maintaining form."
            else:
                return f"Excellent work on {exercise_name}! Next session, aim to increase reps by 2-3 per set."
        elif action == "deload_or_vary":
            return f"You're at a good level with {exercise_name}. Consider a deload week or trying a variation next time."
        elif action == "recovery_focus":
            return f"Take it easy on {exercise_name} this week. Focus on recovery and proper form."
        else:
            return f"Keep up the good work with {exercise_name}! You're building consistency."

    def _generate_overall_suggestion(
        self,
        current_exercises: List[Dict[str, Any]],
        workout_history: Optional[List[Dict[str, Any]]]
    ) -> str:
        """
        Generate overall workout progression suggestion.

        Args:
            current_exercises: All exercises in current workout
            workout_history: Historical workout data

        Returns:
            Overall suggestion string
        """
        if not workout_history or len(workout_history) < 3:
            return "Keep tracking your workouts! After a few sessions, I'll be able to provide more personalized progression advice."

        # Analyze workout frequency
        recent_workouts = []
        for workout in workout_history[-10:]:
            workout_date = workout.get("log_date")
            if workout_date:
                try:
                    workout_date_obj = date.fromisoformat(workout_date)
                    if (date.today() - workout_date_obj).days <= 21:  # Last 3 weeks
                        recent_workouts.append(workout_date_obj)
                except ValueError:
                    continue

        workout_frequency = len(recent_workouts) / 3  # Workouts per week

        if workout_frequency >= 4:
            return "You're training frequently! Make sure to include deload weeks every 4-6 weeks to prevent overtraining."
        elif workout_frequency >= 2:
            return "Good training consistency! Focus on progressive overload by gradually increasing weight or reps."
        else:
            return "Consider increasing workout frequency to 2-3 times per week for better progress."

    def _determine_progression_focus(self, suggestions: List[Dict[str, Any]]) -> str:
        """
        Determine the main progression focus for this workout.

        Args:
            suggestions: List of exercise suggestions

        Returns:
            Focus area string
        """
        high_potential = sum(1 for s in suggestions
                           if s.get("progression_analysis", {}).get("progression_potential") == "high")

        if high_potential > len(suggestions) / 2:
            return "Focus on increasing load (weight/reps) where possible"
        else:
            return "Focus on consistency and form before increasing intensity"

    def _categorize_exercise(self, exercise_name: str) -> str:
        """Categorize an exercise into compound, isolation, or bodyweight."""
        exercise_lower = exercise_name.lower()

        for category, exercises in self.EXERCISE_CATEGORIES.items():
            if any(ex in exercise_lower for ex in exercises):
                return category

        return "compound"  # Default to compound

    def _calculate_trend(
        self,
        recent_performances: List[Dict[str, Any]],
        current_sets: int,
        current_reps: int,
        current_weight: Optional[float]
    ) -> str:
        """
        Calculate performance trend from recent workouts.

        Args:
            recent_performances: List of recent exercise performances
            current_sets: Current sets
            current_reps: Current reps
            current_weight: Current weight

        Returns:
            "improving", "plateau", or "declining"
        """
        if len(recent_performances) < 2:
            return "plateau"

        # Calculate volumes for comparison
        volumes = []
        for perf in recent_performances:
            vol = perf["sets"] * perf["reps"] * (perf["weight"] or 1)
            volumes.append(vol)

        current_volume = current_sets * current_reps * (current_weight or 1)
        volumes.append(current_volume)

        # Simple trend analysis
        if len(volumes) >= 3:
            recent_avg = sum(volumes[-3:]) / 3
            older_avg = sum(volumes[:-3]) / len(volumes[:-3]) if volumes[:-3] else recent_avg

            if recent_avg > older_avg * 1.05:  # 5% improvement
                return "improving"
            elif recent_avg < older_avg * 0.95:  # 5% decline
                return "declining"

        return "plateau"


# Create singleton instance
progression_suggester_tool = ProgressionSuggesterTool()


# Convenience function for direct use
async def suggest_workout_progression(
    current_exercises: List[Dict[str, Any]],
    user_id: str,
    workout_history: Optional[List[Dict[str, Any]]] = None,
    user_profile: Optional[Dict[str, Any]] = None,
    tool_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Generate AI-powered progression suggestions for workout.

    This is the main API function that matches the contract specification.

    Args:
        current_exercises: Current workout exercises
        user_id: Telegram user ID for context
        workout_history: Optional historical workout data
        user_profile: Optional user profile for personalization
        tool_context: Optional ADK tool context

    Returns:
        Dict with status, data, and error fields
    """
    result = await progression_suggester_tool.execute(
        current_exercises=current_exercises,
        user_id=user_id,
        workout_history=workout_history,
        user_profile=user_profile,
        tool_context=tool_context
    )

    return {
        "status": "success" if result.success else "error",
        "data": result.data,
        "error": result.error
    }


__all__ = ['ProgressionSuggesterTool', 'progression_suggester_tool', 'suggest_workout_progression']