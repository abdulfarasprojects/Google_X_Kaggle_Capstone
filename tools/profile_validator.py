"""
Profile validation tools for Weight Loss Chat Agent.

This module provides validation functions for user profile data including
age, height, weight, activity level, and calorie goal validation.
Implements the validate_user_input contract from general-tools-api.md.
"""

import asyncio
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime

from config.logging import get_logger
from database.models import UserProfile

logger = get_logger(__name__)


class ProfileValidationError(Exception):
    """Raised when profile validation fails."""
    pass


async def validate_user_input(
    input_data: Dict,
    validation_type: str,
    user_profile: Optional[Dict] = None,
    tool_context: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    General input validation against guardrails and safety rules.

    Args:
        input_data: Data to validate
        validation_type: Type of validation ('profile', 'meal', 'workout', 'wellness')
        user_profile: User profile for context
        tool_context: ADK tool context

    Returns:
        Validation result with status, validity, warnings, and errors
    """
    try:
        if validation_type == 'profile':
            return await _validate_profile_data(input_data, user_profile)
        elif validation_type == 'meal':
            return await _validate_meal_data(input_data, user_profile)
        elif validation_type == 'workout':
            return await _validate_workout_data(input_data, user_profile)
        elif validation_type == 'wellness':
            return await _validate_wellness_data(input_data, user_profile)
        else:
            return {
                "status": "error",
                "data": {
                    "is_valid": False,
                    "warnings": [],
                    "errors": [f"Unknown validation type: {validation_type}"],
                    "suggestions": [],
                    "guardrail_triggers": []
                },
                "error": f"Unknown validation type: {validation_type}"
            }
    except Exception as e:
        logger.error(f"Validation error for type {validation_type}: {e}")
        return {
            "status": "error",
            "data": {
                "is_valid": False,
                "warnings": [],
                "errors": [f"Validation failed: {str(e)}"],
                "suggestions": [],
                "guardrail_triggers": []
            },
            "error": str(e)
        }


async def _validate_profile_data(
    profile_data: Dict,
    existing_profile: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Validate user profile data against health and safety guidelines.

    Args:
        profile_data: Profile data to validate
        existing_profile: Existing profile for update validation

    Returns:
        Validation result
    """
    errors = []
    warnings = []
    guardrail_triggers = []

    # Extract fields
    age = profile_data.get('age')
    height_cm = profile_data.get('height_cm')
    weight_kg = profile_data.get('weight_kg')
    target_weight_kg = profile_data.get('target_weight_kg')
    activity_level = profile_data.get('activity_level')
    daily_calorie_goal = profile_data.get('daily_calorie_goal')

    # Age validation
    if age is not None:
        if not isinstance(age, int) or age < 18 or age > 100:
            errors.append("Age must be between 18 and 100 years")
            guardrail_triggers.append("age_out_of_range")
        elif age < 25 or age > 65:
            warnings.append("Age is outside typical weight loss range (25-65)")

    # Height validation
    if height_cm is not None:
        try:
            height = Decimal(str(height_cm))
            if height < 100 or height > 250:
                errors.append("Height must be between 100 and 250 cm")
                guardrail_triggers.append("height_out_of_range")
        except (ValueError, TypeError):
            errors.append("Height must be a valid number")

    # Weight validation
    if weight_kg is not None:
        try:
            weight = Decimal(str(weight_kg))
            if weight < 30 or weight > 300:
                errors.append("Weight must be between 30 and 300 kg")
                guardrail_triggers.append("weight_out_of_range")
        except (ValueError, TypeError):
            errors.append("Weight must be a valid number")

    # Target weight validation
    if target_weight_kg is not None and weight_kg is not None:
        try:
            target_weight = Decimal(str(target_weight_kg))
            current_weight = Decimal(str(weight_kg))
            if target_weight >= current_weight:
                errors.append("Target weight must be less than current weight for weight loss")
                guardrail_triggers.append("invalid_weight_loss_goal")
            elif (current_weight - target_weight) > 50:
                warnings.append("Large weight loss goal (>50kg) may be unrealistic")
        except (ValueError, TypeError):
            errors.append("Target weight must be a valid number")

    # Activity level validation
    valid_activity_levels = ['sedentary', 'light', 'moderate', 'active', 'very_active']
    if activity_level is not None and activity_level not in valid_activity_levels:
        errors.append(f"Activity level must be one of: {', '.join(valid_activity_levels)}")

    # Daily calorie goal validation
    if daily_calorie_goal is not None:
        if not isinstance(daily_calorie_goal, int) or daily_calorie_goal < 1000 or daily_calorie_goal > 3000:
            errors.append("Daily calorie goal must be between 1000 and 3000 calories")
            guardrail_triggers.append("calorie_goal_out_of_range")
        elif daily_calorie_goal < 1200:
            warnings.append("Very low calorie goal (<1200) may not be sustainable")
            guardrail_triggers.append("very_low_calorie_goal")

    # Cross-field validations
    if age and height_cm and weight_kg:
        # BMI calculation for additional validation
        try:
            height_m = float(height_cm) / 100
            bmi = float(weight_kg) / (height_m ** 2)

            if bmi < 15 or bmi > 50:
                errors.append("Calculated BMI is outside safe range (15-50)")
                guardrail_triggers.append("bmi_out_of_range")
            elif bmi < 18.5:
                warnings.append("BMI indicates underweight - weight loss may not be appropriate")
            elif bmi > 40:
                warnings.append("BMI indicates severe obesity - consult healthcare provider")
        except (ValueError, TypeError, ZeroDivisionError):
            pass  # Skip BMI validation if calculation fails

    # Generate suggestions
    suggestions = []
    if errors:
        suggestions.append("Please review and correct the validation errors above")
    if warnings:
        suggestions.append("Consider consulting a healthcare professional for personalized advice")

    is_valid = len(errors) == 0

    return {
        "status": "success" if is_valid else "warning" if warnings else "error",
        "data": {
            "is_valid": is_valid,
            "warnings": warnings,
            "errors": errors,
            "suggestions": suggestions,
            "guardrail_triggers": guardrail_triggers
        }
    }


async def _validate_meal_data(
    meal_data: Dict,
    user_profile: Optional[Dict] = None
) -> Dict[str, Any]:
    """Validate meal logging data."""
    # Placeholder - will be implemented with nutrition tools
    return {
        "status": "success",
        "data": {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "suggestions": [],
            "guardrail_triggers": []
        }
    }


async def _validate_workout_data(
    workout_data: Dict,
    user_profile: Optional[Dict] = None
) -> Dict[str, Any]:
    """Validate workout logging data."""
    # Placeholder - will be implemented with fitness tools
    return {
        "status": "success",
        "data": {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "suggestions": [],
            "guardrail_triggers": []
        }
    }


async def _validate_wellness_data(
    wellness_data: Dict,
    user_profile: Optional[Dict] = None
) -> Dict[str, Any]:
    """Validate wellness logging data."""
    # Placeholder - will be implemented with wellness tools
    return {
        "status": "success",
        "data": {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "suggestions": [],
            "guardrail_triggers": []
        }
    }


async def calculate_bmr(
    weight_kg: Decimal,
    height_cm: Decimal,
    age: int,
    gender: str = "average"
) -> Decimal:
    """
    Calculate Basal Metabolic Rate using Mifflin-St Jeor equation.

    Args:
        weight_kg: Weight in kilograms
        height_cm: Height in centimeters
        age: Age in years
        gender: Gender for calculation ('male', 'female', 'average')

    Returns:
        BMR in calories per day
    """
    # Mifflin-St Jeor equation
    if gender.lower() == "male":
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    elif gender.lower() == "female":
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161
    else:
        # Average of male/female for gender-neutral calculation
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 78

    return Decimal(str(round(float(bmr), 1)))


async def calculate_tdee(
    bmr: Decimal,
    activity_level: str
) -> Decimal:
    """
    Calculate Total Daily Energy Expenditure based on activity level.

    Args:
        bmr: Basal Metabolic Rate
        activity_level: Activity level category

    Returns:
        TDEE in calories per day
    """
    activity_multipliers = {
        'sedentary': Decimal('1.2'),      # Little to no exercise
        'light': Decimal('1.375'),        # Light exercise 1-3 days/week
        'moderate': Decimal('1.55'),      # Moderate exercise 3-5 days/week
        'active': Decimal('1.725'),       # Hard exercise 6-7 days/week
        'very_active': Decimal('1.9')     # Very hard exercise, physical job
    }

    multiplier = activity_multipliers.get(activity_level, Decimal('1.2'))
    return Decimal(str(round(float(bmr * multiplier), 1)))


async def suggest_calorie_goal(
    weight_kg: Decimal,
    height_cm: Decimal,
    age: int,
    activity_level: str,
    target_weight_kg: Optional[Decimal] = None
) -> Dict[str, Any]:
    """
    Suggest appropriate daily calorie goal for weight loss.

    Args:
        weight_kg: Current weight
        height_cm: Height in cm
        age: Age in years
        activity_level: Activity level
        target_weight_kg: Target weight (optional)

    Returns:
        Suggested calorie goal with reasoning
    """
    try:
        # Calculate BMR and TDEE
        bmr = await calculate_bmr(weight_kg, height_cm, age)
        tdee = await calculate_tdee(bmr, activity_level)

        # Suggest 500 calorie deficit for 1lb/week weight loss
        suggested_goal = tdee - 500

        # Ensure within safe ranges
        min_calories = 1200  # Minimum safe for weight loss
        max_calories = 3000  # Maximum reasonable

        suggested_goal = max(min_calories, min(max_calories, suggested_goal))

        return {
            "status": "success",
            "data": {
                "suggested_calories": int(suggested_goal),
                "bmr": float(bmr),
                "tdee": float(tdee),
                "reasoning": f"Based on {activity_level} activity level, suggesting 500 calorie deficit from maintenance calories"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "data": {
                "suggested_calories": 1800,  # Safe default
                "bmr": None,
                "tdee": None,
                "reasoning": "Using safe default due to calculation error"
            },
            "error": str(e)
        }


# Export functions for use as tools
__all__ = [
    'validate_user_input',
    'calculate_bmr',
    'calculate_tdee',
    'suggest_calorie_goal'
]