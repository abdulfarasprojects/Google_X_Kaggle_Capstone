"""
Batch workout parsing tools for fitness logging.

This module provides tools for parsing natural language workout descriptions
into structured data for volume calculation and progression tracking.
Supports batch processing of multiple exercises with validation.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


@dataclass
class ParsedExercise:
    """Structured representation of a parsed exercise."""
    description: str
    exercise_name: str
    sets: int
    reps: int
    weight: Optional[float]
    weight_unit: Optional[str]
    confidence: float


class BatchWorkoutParserTool(BaseTool):
    """
    Tool for parsing batch workout descriptions into structured format.

    Uses pattern matching to extract exercise name, sets, reps, and weight
    from natural language descriptions. Supports batch processing for workout logging.
    """

    def __init__(self):
        super().__init__(
            name="parse_workout_batch",
            description="Parse and validate a batch of exercise descriptions for workout logging",
            parameters={
                "type": "object",
                "properties": {
                    "exercise_descriptions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of exercise descriptions",
                        "maxItems": 10
                    },
                    "user_id": {
                        "type": "string",
                        "description": "Telegram user ID for context"
                    }
                },
                "required": ["exercise_descriptions", "user_id"]
            }
        )

        # Weight units and their normalizations
        self.WEIGHT_UNITS = {
            'lb': 'lb', 'lbs': 'lb', 'pound': 'lb', 'pounds': 'lb',
            'kg': 'kg', 'kilogram': 'kg', 'kilograms': 'kg',
            'g': 'g', 'gram': 'g', 'grams': 'g'
        }

        # Exercise patterns with confidence scores
        self.EXERCISE_PATTERNS = [
            # "Exercise: sets of reps at weight"
            (r'^(.+?):\s*(\d+)\s*(?:sets?|x)\s+of\s+(\d+)\s*(?:reps?|rep)\s+(?:at|@)\s+(\d+(?:\.\d+)?)\s*(lb|lbs|kg|kilogram|kilograms|g|gram|grams|pound|pounds)?$', 0.95),
            # "Exercise: sets x reps at weight"
            (r'^(.+?):\s*(\d+)\s*(?:sets?|x)\s*(\d+)\s*(?:reps?|rep)\s+(?:at|@)\s+(\d+(?:\.\d+)?)\s*(lb|lbs|kg|kilogram|kilograms|g|gram|grams|pound|pounds)?$', 0.95),
            # "sets x reps exercise at weight"
            (r'^(\d+)\s*(?:sets?|x)\s*(\d+)\s+(.+?)\s+(?:at|@)\s+(\d+(?:\.\d+)?)\s*(lb|lbs|kg|kilogram|kilograms|g|gram|grams|pound|pounds)?$', 0.95),
            # "sets x reps exercise weight unit"
            (r'^(\d+)\s*(?:sets?|x)\s*(\d+)\s+(.+?)\s+(\d+(?:\.\d+)?)\s*(lb|lbs|kg|kilogram|kilograms|g|gram|grams|pound|pounds)$', 0.95),
            # "reps exercise at weight"
            (r'^(\d+)\s*(?:reps?|rep)\s+(.+?)\s+(?:at|@)\s+(\d+(?:\.\d+)?)\s*(lb|lbs|kg|kilogram|kilograms|g|gram|grams|pound|pounds)?$', 0.9),
            # "reps exercise weight unit"
            (r'^(\d+)\s*(?:reps?|rep)\s+(.+?)\s+(\d+(?:\.\d+)?)\s*(lb|lbs|kg|kilogram|kilograms|g|gram|grams|pound|pounds)$', 0.9),
            # "sets x reps exercise" (bodyweight)
            (r'^(\d+)\s*(?:sets?|x)\s*(\d+)\s+(.+)$', 0.85),
            # "reps exercise" (bodyweight)
            (r'^(\d+)\s*(?:reps?|rep)\s+(.+)$', 0.8),
            # "exercise" (assume 1 set, ask for clarification)
            (r'^(.+)$', 0.6),
        ]

        # Common exercise name normalizations
        self.EXERCISE_NORMALIZATIONS = {
            'pullup': 'pull-ups', 'pullups': 'pull-ups', 'pull up': 'pull-ups', 'pull ups': 'pull-ups',
            'pushup': 'push-ups', 'pushups': 'push-ups', 'push up': 'push-ups', 'push ups': 'push-ups',
            'squat': 'squats', 'squatz': 'squats',
            'deadlift': 'deadlifts', 'dl': 'deadlifts',
            'benchpress': 'bench press', 'bench': 'bench press',
            'overheadpress': 'overhead press', 'ohp': 'overhead press',
            'bicep curl': 'bicep curls', 'bicep curls': 'bicep curls',
            'tricep extension': 'tricep extensions',
            'lateral raise': 'lateral raises',
            'shoulder press': 'shoulder press',
            'leg press': 'leg press',
            'lunges': 'lunges', 'lunge': 'lunges',
            'burpee': 'burpees', 'burpees': 'burpees',
            'plank': 'plank',
            'mountain climber': 'mountain climbers',
            'jumping jack': 'jumping jacks',
            'burpee': 'burpees'
        }

    async def execute(
        self,
        exercise_descriptions: List[str],
        user_id: str,
        tool_context: Optional[Any] = None
    ) -> ToolResult:
        """
        Parse batch of exercise descriptions.

        Args:
            exercise_descriptions: List of exercise descriptions (max 10)
            user_id: User ID for context
            tool_context: ADK tool context

        Returns:
            ToolResult with parsed exercises or error
        """
        try:
            # Validate batch size
            if len(exercise_descriptions) > 10:
                return ToolResult(
                    success=False,
                    error="Batch size exceeds maximum of 10 exercises"
                )

            if len(exercise_descriptions) == 0:
                return ToolResult(
                    success=False,
                    error="No exercise descriptions provided"
                )

            parsed_exercises = []
            validation_errors = []

            for i, description in enumerate(exercise_descriptions):
                try:
                    parsed = self._parse_exercise_description(description)
                    parsed_exercises.append(parsed)
                except Exception as e:
                    validation_errors.append(f"Exercise {i+1}: {str(e)}")
                    # Add with low confidence defaults
                    parsed_exercises.append(ParsedExercise(
                        description=description,
                        exercise_name=description,
                        sets=1,
                        reps=1,
                        weight=None,
                        weight_unit=None,
                        confidence=0.1
                    ))

            batch_complete = len(validation_errors) == 0

            return ToolResult(
                success=True,
                data={
                    "parsed_exercises": [
                        {
                            "description": ex.description,
                            "exercise_name": ex.exercise_name,
                            "sets": ex.sets,
                            "reps": ex.reps,
                            "weight": ex.weight,
                            "weight_unit": ex.weight_unit,
                            "confidence": ex.confidence
                        }
                        for ex in parsed_exercises
                    ],
                    "batch_complete": batch_complete,
                    "validation_errors": validation_errors
                }
            )

        except Exception as e:
            logger.error(f"Batch workout parsing failed: {e}")
            return ToolResult(
                success=False,
                error=f"Batch workout parsing failed: {str(e)}"
            )

    def _parse_exercise_description(self, description: str) -> ParsedExercise:
        """
        Parse a single exercise description into structured format.

        Args:
            description: Natural language exercise description

        Returns:
            ParsedExercise: Structured exercise data

        Raises:
            ValueError: If parsing fails
        """
        original_desc = description.strip()
        desc = original_desc.lower()

        # Try each pattern
        for pattern, base_confidence in self.EXERCISE_PATTERNS:
            match = re.match(pattern, desc)
            if match:
                return self._extract_from_exercise_match(match, original_desc, base_confidence)

        # Fallback: treat as unknown exercise
        raise ValueError(f"Could not parse exercise description: {original_desc}")

    def _extract_from_exercise_match(self, match: re.Match, original_desc: str, base_confidence: float) -> ParsedExercise:
        """Extract exercise details from regex match."""
        groups = match.groups()

        if len(groups) == 6:
            # "sets x reps exercise at weight unit" or "Exercise: sets x reps at weight unit"
            if ':' in original_desc[:20]:  # Colon pattern
                exercise = groups[0].strip()
                sets = int(groups[1])
                reps = int(groups[2])
                weight = float(groups[4])
                unit = groups[5] if groups[5] else None
                if unit:
                    unit = self._normalize_weight_unit(unit)
            else:
                # "sets x reps exercise at weight unit"
                sets = int(groups[0])
                reps = int(groups[1])
                exercise = groups[2].strip()
                weight = float(groups[3])
                unit = groups[4] if groups[4] else groups[5]
                if unit:
                    unit = self._normalize_weight_unit(unit)
        elif len(groups) == 5:
            if ':' in original_desc[:20]:  # Colon pattern
                if ' of ' in original_desc:
                    # "Exercise: sets of reps at weight unit"
                    exercise = groups[0].strip()
                    sets = int(groups[1])
                    reps = int(groups[2])
                    weight = float(groups[3])
                    unit = groups[4] if groups[4] else None
                    if unit:
                        unit = self._normalize_weight_unit(unit)
                else:
                    # "Exercise: sets x reps at weight unit"
                    exercise = groups[0].strip()
                    sets = int(groups[1])
                    reps = int(groups[2])
                    weight = float(groups[3])
                    unit = groups[4] if groups[4] else None
                    if unit:
                        unit = self._normalize_weight_unit(unit)
            else:
                # "sets x reps exercise weight unit" or "reps exercise at weight unit"
                if ' at ' in original_desc or ' @ ' in original_desc:
                    # "reps exercise at weight unit"
                    sets = 1  # Assume 1 set
                    reps = int(groups[0])
                    exercise = groups[1].strip()
                    weight = float(groups[2])
                    unit = groups[3] if groups[3] else groups[4]
                    if unit:
                        unit = self._normalize_weight_unit(unit)
                else:
                    # "sets x reps exercise weight unit"
                    sets = int(groups[0])
                    reps = int(groups[1])
                    exercise = groups[2].strip()
                    weight = float(groups[3])
                    unit = groups[4]
                    unit = self._normalize_weight_unit(unit)
        elif len(groups) == 4:
            # "reps exercise weight unit" (no 'at')
            sets = 1  # Assume 1 set
            reps = int(groups[0])
            exercise = groups[1].strip()
            weight = float(groups[2])
            unit = groups[3]
            unit = self._normalize_weight_unit(unit)
        elif len(groups) == 3:
            # "sets x reps exercise" (bodyweight)
            sets = int(groups[0])
            reps = int(groups[1])
            exercise = groups[2].strip()
            weight = None
            unit = None
        elif len(groups) == 2:
            # "reps exercise" (bodyweight)
            sets = 1  # Assume 1 set
            reps = int(groups[0])
            exercise = groups[1].strip()
            weight = None
            unit = None
        elif len(groups) == 1:
            # "exercise" only (very low confidence)
            sets = 1
            reps = 1
            exercise = groups[0].strip()
            weight = None
            unit = None
            base_confidence = 0.3  # Very low confidence
        else:
            raise ValueError(f"Unexpected match groups: {groups}")

        # Normalize exercise name
        exercise_name = self._normalize_exercise_name(exercise)

        # Validate ranges
        self._validate_exercise_data(sets, reps, weight, unit)

        return ParsedExercise(
            description=original_desc,
            exercise_name=exercise_name,
            sets=sets,
            reps=reps,
            weight=weight,
            weight_unit=unit,
            confidence=base_confidence
        )

    def _normalize_weight_unit(self, unit: str) -> str:
        """Normalize weight unit to standard form."""
        unit = unit.lower().strip()
        return self.WEIGHT_UNITS.get(unit, unit)

    def _normalize_exercise_name(self, exercise: str) -> str:
        """Normalize exercise name using common mappings."""
        exercise = exercise.lower().strip()
        return self.EXERCISE_NORMALIZATIONS.get(exercise, exercise)

    def _validate_exercise_data(self, sets: int, reps: int, weight: Optional[float], unit: Optional[str]) -> None:
        """Validate exercise data ranges."""
        if sets < 1 or sets > 10:
            raise ValueError(f"Sets must be between 1-10, got {sets}")
        if reps < 1 or reps > 500:
            raise ValueError(f"Reps must be between 1-500, got {reps}")
        if weight is not None and (weight < 0 or weight > 1000):
            raise ValueError(f"Weight must be between 0-1000, got {weight}")


# Create singleton instance
batch_workout_parser_tool = BatchWorkoutParserTool()


# Convenience function for direct use
async def parse_workout_batch(
    exercise_descriptions: List[str],
    user_id: str,
    tool_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Parse a batch of exercise descriptions for workout logging.

    This is the main API function that matches the contract specification.

    Args:
        exercise_descriptions: List of exercise descriptions (max 10 items)
        user_id: Telegram user ID for context
        tool_context: Optional ADK tool context

    Returns:
        Dict with status, data, and error fields
    """
    result = await batch_workout_parser_tool.execute(
        exercise_descriptions=exercise_descriptions,
        user_id=user_id,
        tool_context=tool_context
    )

    return {
        "status": "success" if result.success else "error",
        "data": result.data,
        "error": result.error
    }


__all__ = ['BatchWorkoutParserTool', 'batch_workout_parser_tool', 'parse_workout_batch']