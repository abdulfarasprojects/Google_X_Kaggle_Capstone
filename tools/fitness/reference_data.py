"""
Fitness reference data for approximate calculations.

This module contains static reference data for fitness calculations,
including approximate exercise data for volume calculations. Used as
fallback when parsing is unavailable or for faster calculations.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class FitnessReferenceData:
    """
    Static reference data for fitness calculations.

    Contains approximate exercise data organized by category for easy lookup
    and volume calculation.
    """

    # Approximate exercise data (typical weights and RPE for different levels)
    EXERCISE_REFERENCE_DB = {
        # Compound Lower Body
        'squats': {
            'category': 'lower_body',
            'typical_sets': 3,
            'typical_reps': 10,
            'beginner_weight': 45,  # lbs
            'intermediate_weight': 135,
            'advanced_weight': 225,
            'bodyweight_multiplier': 1.0,
            'muscle_groups': ['quadriceps', 'glutes', 'hamstrings']
        },
        'deadlifts': {
            'category': 'lower_body',
            'typical_sets': 3,
            'typical_reps': 8,
            'beginner_weight': 95,
            'intermediate_weight': 185,
            'advanced_weight': 315,
            'bodyweight_multiplier': 1.0,
            'muscle_groups': ['hamstrings', 'glutes', 'back']
        },
        'lunges': {
            'category': 'lower_body',
            'typical_sets': 3,
            'typical_reps': 12,
            'beginner_weight': 25,
            'intermediate_weight': 45,
            'advanced_weight': 70,
            'bodyweight_multiplier': 0.5,
            'muscle_groups': ['quadriceps', 'glutes', 'hamstrings']
        },
        'leg press': {
            'category': 'lower_body',
            'typical_sets': 3,
            'typical_reps': 12,
            'beginner_weight': 180,
            'intermediate_weight': 270,
            'advanced_weight': 360,
            'bodyweight_multiplier': 0.0,
            'muscle_groups': ['quadriceps', 'glutes', 'hamstrings']
        },

        # Compound Upper Body Push
        'bench press': {
            'category': 'upper_body_push',
            'typical_sets': 3,
            'typical_reps': 10,
            'beginner_weight': 65,
            'intermediate_weight': 135,
            'advanced_weight': 225,
            'bodyweight_multiplier': 0.7,
            'muscle_groups': ['chest', 'triceps', 'shoulders']
        },
        'overhead press': {
            'category': 'upper_body_push',
            'typical_sets': 3,
            'typical_reps': 8,
            'beginner_weight': 45,
            'intermediate_weight': 95,
            'advanced_weight': 135,
            'bodyweight_multiplier': 0.5,
            'muscle_groups': ['shoulders', 'triceps', 'chest']
        },
        'push-ups': {
            'category': 'upper_body_push',
            'typical_sets': 3,
            'typical_reps': 15,
            'beginner_weight': 0,
            'intermediate_weight': 0,
            'advanced_weight': 0,
            'bodyweight_multiplier': 1.0,
            'muscle_groups': ['chest', 'triceps', 'shoulders']
        },
        'dips': {
            'category': 'upper_body_push',
            'typical_sets': 3,
            'typical_reps': 12,
            'beginner_weight': 0,
            'intermediate_weight': 0,
            'advanced_weight': 45,
            'bodyweight_multiplier': 1.0,
            'muscle_groups': ['triceps', 'chest', 'shoulders']
        },

        # Compound Upper Body Pull
        'pull-ups': {
            'category': 'upper_body_pull',
            'typical_sets': 3,
            'typical_reps': 8,
            'beginner_weight': 0,
            'intermediate_weight': 0,
            'advanced_weight': 0,
            'bodyweight_multiplier': 1.0,
            'muscle_groups': ['back', 'biceps', 'shoulders']
        },
        'rows': {
            'category': 'upper_body_pull',
            'typical_sets': 3,
            'typical_reps': 10,
            'beginner_weight': 65,
            'intermediate_weight': 135,
            'advanced_weight': 185,
            'bodyweight_multiplier': 0.0,
            'muscle_groups': ['back', 'biceps', 'shoulders']
        },
        'dead hang': {
            'category': 'upper_body_pull',
            'typical_sets': 3,
            'typical_reps': 1,
            'beginner_weight': 0,
            'intermediate_weight': 0,
            'advanced_weight': 0,
            'bodyweight_multiplier': 1.0,
            'muscle_groups': ['back', 'shoulders', 'forearms']
        },

        # Isolation Exercises
        'bicep curls': {
            'category': 'isolation',
            'typical_sets': 3,
            'typical_reps': 12,
            'beginner_weight': 20,
            'intermediate_weight': 35,
            'advanced_weight': 50,
            'bodyweight_multiplier': 0.0,
            'muscle_groups': ['biceps']
        },
        'tricep extensions': {
            'category': 'isolation',
            'typical_sets': 3,
            'typical_reps': 12,
            'beginner_weight': 25,
            'intermediate_weight': 45,
            'advanced_weight': 65,
            'bodyweight_multiplier': 0.0,
            'muscle_groups': ['triceps']
        },
        'lateral raises': {
            'category': 'isolation',
            'typical_sets': 3,
            'typical_reps': 15,
            'beginner_weight': 10,
            'intermediate_weight': 20,
            'advanced_weight': 30,
            'bodyweight_multiplier': 0.0,
            'muscle_groups': ['shoulders']
        },
        'leg curls': {
            'category': 'isolation',
            'typical_sets': 3,
            'typical_reps': 12,
            'beginner_weight': 50,
            'intermediate_weight': 80,
            'advanced_weight': 110,
            'bodyweight_multiplier': 0.0,
            'muscle_groups': ['hamstrings']
        },

        # Core Exercises
        'plank': {
            'category': 'core',
            'typical_sets': 3,
            'typical_reps': 1,
            'beginner_weight': 0,
            'intermediate_weight': 0,
            'advanced_weight': 0,
            'bodyweight_multiplier': 1.0,
            'muscle_groups': ['core', 'shoulders']
        },
        'crunches': {
            'category': 'core',
            'typical_sets': 3,
            'typical_reps': 20,
            'beginner_weight': 0,
            'intermediate_weight': 0,
            'advanced_weight': 0,
            'bodyweight_multiplier': 1.0,
            'muscle_groups': ['core']
        },
        'russian twists': {
            'category': 'core',
            'typical_sets': 3,
            'typical_reps': 20,
            'beginner_weight': 0,
            'intermediate_weight': 10,
            'advanced_weight': 20,
            'bodyweight_multiplier': 0.5,
            'muscle_groups': ['core', 'obliques']
        },

        # Cardio Exercises
        'burpees': {
            'category': 'cardio',
            'typical_sets': 3,
            'typical_reps': 10,
            'beginner_weight': 0,
            'intermediate_weight': 0,
            'advanced_weight': 0,
            'bodyweight_multiplier': 1.0,
            'muscle_groups': ['full_body']
        },
        'mountain climbers': {
            'category': 'cardio',
            'typical_sets': 3,
            'typical_reps': 30,
            'beginner_weight': 0,
            'intermediate_weight': 0,
            'advanced_weight': 0,
            'bodyweight_multiplier': 1.0,
            'muscle_groups': ['core', 'cardio']
        },
        'jumping jacks': {
            'category': 'cardio',
            'typical_sets': 3,
            'typical_reps': 50,
            'beginner_weight': 0,
            'intermediate_weight': 0,
            'advanced_weight': 0,
            'bodyweight_multiplier': 1.0,
            'muscle_groups': ['cardio', 'full_body']
        },

        # Olympic Lifts
        'clean and jerk': {
            'category': 'olympic',
            'typical_sets': 3,
            'typical_reps': 5,
            'beginner_weight': 65,
            'intermediate_weight': 135,
            'advanced_weight': 185,
            'bodyweight_multiplier': 0.8,
            'muscle_groups': ['full_body']
        },
        'snatch': {
            'category': 'olympic',
            'typical_sets': 3,
            'typical_reps': 3,
            'beginner_weight': 45,
            'intermediate_weight': 95,
            'advanced_weight': 135,
            'bodyweight_multiplier': 0.7,
            'muscle_groups': ['full_body']
        }
    }

    # Common exercise name variations and aliases
    EXERCISE_ALIASES = {
        # Squats variations
        'back squat': 'squats',
        'front squat': 'squats',
        'goblet squat': 'squats',
        'squat': 'squats',

        # Deadlift variations
        'conventional deadlift': 'deadlifts',
        'sumo deadlift': 'deadlifts',
        'romanian deadlift': 'deadlifts',
        'rdl': 'deadlifts',
        'dl': 'deadlifts',

        # Bench press variations
        'barbell bench press': 'bench press',
        'dumbbell bench press': 'bench press',
        'incline bench press': 'bench press',
        'decline bench press': 'bench press',
        'bench': 'bench press',

        # Pull-up variations
        'chin-ups': 'pull-ups',
        'chin up': 'pull-ups',
        'pull up': 'pull-ups',
        'pullup': 'pull-ups',
        'chinup': 'chin-ups',

        # Row variations
        'barbell row': 'rows',
        'dumbbell row': 'rows',
        't-bar row': 'rows',
        'cable row': 'rows',
        'seated row': 'rows',

        # Press variations
        'shoulder press': 'overhead press',
        'military press': 'overhead press',
        'ohp': 'overhead press',
        'strict press': 'overhead press',

        # Curl variations
        'barbell curl': 'bicep curls',
        'dumbbell curl': 'bicep curls',
        'hammer curl': 'bicep curls',
        'preacher curl': 'bicep curls',

        # Extension variations
        'skull crushers': 'tricep extensions',
        'overhead extension': 'tricep extensions',
        'cable extension': 'tricep extensions',

        # Raise variations
        'side raises': 'lateral raises',
        'dumbbell raises': 'lateral raises',

        # Core variations
        'sit-ups': 'crunches',
        'ab crunches': 'crunches',

        # Cardio variations
        'burpee': 'burpees',
        'mountain climber': 'mountain climbers',
        'jumping jack': 'jumping jacks'
    }

    @staticmethod
    def get_exercise_data(exercise_name: str) -> Optional[Dict[str, Any]]:
        """
        Get reference data for an exercise.

        Args:
            exercise_name: Name of the exercise to look up

        Returns:
            Dict with exercise data or None if not found
        """
        exercise_key = exercise_name.lower().strip()

        # Direct lookup
        if exercise_key in FitnessReferenceData.EXERCISE_REFERENCE_DB:
            return FitnessReferenceData.EXERCISE_REFERENCE_DB[exercise_key].copy()

        # Check aliases
        if exercise_key in FitnessReferenceData.EXERCISE_ALIASES:
            canonical_name = FitnessReferenceData.EXERCISE_ALIASES[exercise_key]
            if canonical_name in FitnessReferenceData.EXERCISE_REFERENCE_DB:
                return FitnessReferenceData.EXERCISE_REFERENCE_DB[canonical_name].copy()

        # Fuzzy matching
        for db_exercise in FitnessReferenceData.EXERCISE_REFERENCE_DB:
            if db_exercise in exercise_key or exercise_key in db_exercise:
                logger.info(f"Found approximate match: '{exercise_key}' -> '{db_exercise}'")
                return FitnessReferenceData.EXERCISE_REFERENCE_DB[db_exercise].copy()

        return None

    @staticmethod
    def get_typical_workout_volume(
        exercise_name: str,
        experience_level: str = 'intermediate'
    ) -> Optional[Dict[str, Any]]:
        """
        Get typical workout volume for an exercise.

        Args:
            exercise_name: Name of the exercise
            experience_level: 'beginner', 'intermediate', or 'advanced'

        Returns:
            Dict with typical sets, reps, and weight
        """
        exercise_data = FitnessReferenceData.get_exercise_data(exercise_name)
        if not exercise_data:
            return None

        level = experience_level.lower()
        if level not in ['beginner', 'intermediate', 'advanced']:
            level = 'intermediate'

        weight_key = f'{level}_weight'

        return {
            'exercise_name': exercise_name,
            'sets': exercise_data['typical_sets'],
            'reps': exercise_data['typical_reps'],
            'weight': exercise_data[weight_key],
            'weight_unit': 'lb',
            'category': exercise_data['category'],
            'muscle_groups': exercise_data['muscle_groups'],
            'confidence': 0.8
        }

    @staticmethod
    def calculate_volume_score(
        exercise_name: str,
        sets: int,
        reps: int,
        weight: float
    ) -> int:
        """
        Calculate a volume score for an exercise.

        Args:
            exercise_name: Name of the exercise
            sets: Number of sets
            reps: Reps per set
            weight: Weight used

        Returns:
            Volume score (sets * reps * weight)
        """
        return int(sets * reps * weight)


# Create singleton instance
fitness_reference = FitnessReferenceData()

__all__ = ['FitnessReferenceData', 'fitness_reference']