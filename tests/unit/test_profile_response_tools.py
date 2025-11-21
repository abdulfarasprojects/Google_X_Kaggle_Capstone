"""
Unit tests for profile validator and response formatter tools.

Tests input validation and response formatting functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch
from decimal import Decimal

from tools.profile_validator import (
    validate_user_input,
    ProfileValidationError,
    _validate_profile_data,
    _validate_meal_data,
    _validate_workout_data,
    _validate_wellness_data
)
from tools.response_formatter import format_response


class TestProfileValidator:
    """Test cases for profile validation functions."""

    @pytest.mark.asyncio
    async def test_validate_profile_data_valid(self):
        """Test validation of valid profile data."""
        profile_data = {
            "age": 30,
            "height_cm": 175,
            "weight_kg": 80.0,
            "activity_level": "moderately_active",
            "goal_weight_kg": 75.0,
            "timeframe_weeks": 12
        }

        result = await validate_user_input(
            input_data=profile_data,
            validation_type="profile"
        )

        assert result["status"] == "success"
        assert result["is_valid"] is True
        assert len(result["warnings"]) == 0
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_validate_profile_data_invalid_age(self):
        """Test validation with invalid age."""
        profile_data = {
            "age": 15,  # Too young
            "height_cm": 175,
            "weight_kg": 80.0,
            "activity_level": "moderately_active",
            "goal_weight_kg": 75.0
        }

        result = await validate_user_input(
            input_data=profile_data,
            validation_type="profile"
        )

        assert result["status"] == "success"
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
        assert "age" in str(result["errors"]).lower()

    @pytest.mark.asyncio
    async def test_validate_profile_data_invalid_height(self):
        """Test validation with invalid height."""
        profile_data = {
            "age": 30,
            "height_cm": 50,  # Too short
            "weight_kg": 80.0,
            "activity_level": "moderately_active",
            "goal_weight_kg": 75.0
        }

        result = await validate_user_input(
            input_data=profile_data,
            validation_type="profile"
        )

        assert result["status"] == "success"
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_validate_profile_data_invalid_weight(self):
        """Test validation with invalid weight."""
        profile_data = {
            "age": 30,
            "height_cm": 175,
            "weight_kg": 30.0,  # Too light
            "activity_level": "moderately_active",
            "goal_weight_kg": 25.0  # Unrealistic goal
        }

        result = await validate_user_input(
            input_data=profile_data,
            validation_type="profile"
        )

        assert result["status"] == "success"
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_validate_profile_data_unrealistic_goal(self):
        """Test validation with unrealistic weight loss goal."""
        profile_data = {
            "age": 30,
            "height_cm": 175,
            "weight_kg": 80.0,
            "activity_level": "moderately_active",
            "goal_weight_kg": 50.0,  # Lose 30kg in 12 weeks = unhealthy
            "timeframe_weeks": 12
        }

        result = await validate_user_input(
            input_data=profile_data,
            validation_type="profile"
        )

        assert result["status"] == "success"
        assert result["is_valid"] is False
        assert len(result["warnings"]) > 0 or len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_validate_meal_data_valid(self):
        """Test validation of valid meal data."""
        meal_data = {
            "meal_type": "breakfast",
            "food_items": ["2 eggs", "1 cup oatmeal"],
            "total_calories": 350,
            "total_protein_g": 20
        }

        result = await validate_user_input(
            input_data=meal_data,
            validation_type="meal"
        )

        assert result["status"] == "success"
        assert result["is_valid"] is True

    @pytest.mark.asyncio
    async def test_validate_meal_data_invalid_calories(self):
        """Test validation with invalid calorie values."""
        meal_data = {
            "meal_type": "lunch",
            "food_items": ["chicken breast"],
            "total_calories": 5000,  # Unrealistically high
            "total_protein_g": 50
        }

        result = await validate_user_input(
            input_data=meal_data,
            validation_type="meal"
        )

        assert result["status"] == "success"
        assert result["is_valid"] is False
        assert len(result["warnings"]) > 0

    @pytest.mark.asyncio
    async def test_validate_workout_data_valid(self):
        """Test validation of valid workout data."""
        workout_data = {
            "exercises": [
                {
                    "name": "bench press",
                    "sets": 3,
                    "reps": 10,
                    "weight": 80.0
                }
            ],
            "duration_minutes": 45,
            "total_volume": 2400
        }

        result = await validate_user_input(
            input_data=workout_data,
            validation_type="workout"
        )

        assert result["status"] == "success"
        assert result["is_valid"] is True

    @pytest.mark.asyncio
    async def test_validate_workout_data_invalid_volume(self):
        """Test validation with invalid workout volume."""
        workout_data = {
            "exercises": [
                {
                    "name": "bench press",
                    "sets": 10,
                    "reps": 100,
                    "weight": 200.0
                }
            ],
            "duration_minutes": 30,
            "total_volume": 200000  # Unrealistically high
        }

        result = await validate_user_input(
            input_data=workout_data,
            validation_type="workout"
        )

        assert result["status"] == "success"
        assert result["is_valid"] is False
        assert len(result["warnings"]) > 0

    @pytest.mark.asyncio
    async def test_validate_wellness_data_valid(self):
        """Test validation of valid wellness data."""
        wellness_data = {
            "sleep_hours": 8.0,
            "sleep_quality": 4,
            "water_glasses": 8,
            "steps_count": 10000
        }

        result = await validate_user_input(
            input_data=wellness_data,
            validation_type="wellness"
        )

        assert result["status"] == "success"
        assert result["is_valid"] is True

    @pytest.mark.asyncio
    async def test_validate_wellness_data_invalid_sleep(self):
        """Test validation with invalid sleep hours."""
        wellness_data = {
            "sleep_hours": 25.0,  # Impossible
            "sleep_quality": 4,
            "water_glasses": 8,
            "steps_count": 10000
        }

        result = await validate_user_input(
            input_data=wellness_data,
            validation_type="wellness"
        )

        assert result["status"] == "success"
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_validate_invalid_type(self):
        """Test validation with invalid validation type."""
        result = await validate_user_input(
            input_data={},
            validation_type="invalid_type"
        )

        assert result["status"] == "error"
        assert "Unsupported validation type" in result["error"]


class TestResponseFormatter:
    """Test cases for response formatting functions."""

    @pytest.mark.asyncio
    async def test_format_nutrition_summary(self):
        """Test formatting nutrition summary response."""
        content = {
            "total_calories": 450,
            "total_protein_g": 25,
            "confidence_score": 0.85
        }

        result = await format_response(
            response_type="nutrition_summary",
            content=content
        )

        assert "Meal logged!" in result["formatted_response"]
        assert "450 kcal" in result["formatted_response"]
        assert "25g" in result["formatted_response"]
        assert "Good estimates" in result["formatted_response"]

    @pytest.mark.asyncio
    async def test_format_nutrition_summary_low_confidence(self):
        """Test formatting nutrition summary with low confidence."""
        content = {
            "total_calories": 350,
            "total_protein_g": 20,
            "confidence_score": 0.6
        }

        result = await format_response(
            response_type="nutrition_summary",
            content=content
        )

        assert "moderate confidence" in result["formatted_response"]

    @pytest.mark.asyncio
    async def test_format_workout_summary(self):
        """Test formatting workout summary response."""
        content = {
            "total_volume": 2400,
            "exercise_count": 3,
            "duration_minutes": 45,
            "progression": "improved"
        }

        result = await format_response(
            response_type="workout_summary",
            content=content
        )

        assert "Workout logged!" in result["formatted_response"]
        assert "2400" in result["formatted_response"]
        assert "45 minutes" in result["formatted_response"]

    @pytest.mark.asyncio
    async def test_format_progress_report(self):
        """Test formatting progress report response."""
        content = {
            "weight_change_kg": -2.1,
            "weight_change_percent": -2.5,
            "days_logged": 14,
            "avg_calories_day": 1850,
            "total_workouts": 8,
            "trend": "on_track"
        }

        result = await format_response(
            response_type="progress_report",
            content=content
        )

        assert "Progress Report" in result["formatted_response"]
        assert "-2.1 kg" in result["formatted_response"]
        assert "-2.5%" in result["formatted_response"]
        assert "14 days" in result["formatted_response"]

    @pytest.mark.asyncio
    async def test_format_wellness_summary(self):
        """Test formatting wellness summary response."""
        content = {
            "sleep_hours": 7.5,
            "sleep_quality": 4,
            "water_glasses": 8,
            "steps_count": 9500,
            "insights": ["Good sleep quality", "Adequate hydration"]
        }

        result = await format_response(
            response_type="wellness_summary",
            content=content
        )

        assert "Wellness logged!" in result["formatted_response"]
        assert "7.5 hours" in result["formatted_response"]
        assert "8 glasses" in result["formatted_response"]
        assert "9500 steps" in result["formatted_response"]

    @pytest.mark.asyncio
    async def test_format_general_response(self):
        """Test formatting general response."""
        content = {
            "message": "Hello! How can I help you with your weight loss journey?",
            "suggestions": ["Log your meals", "Track your workouts"]
        }

        result = await format_response(
            response_type="general",
            content=content
        )

        assert "Hello!" in result["formatted_response"]
        assert "weight loss journey" in result["formatted_response"]

    @pytest.mark.asyncio
    async def test_format_error_response(self):
        """Test formatting error response."""
        content = {
            "error": "Unable to process request",
            "suggestion": "Please try again later"
        }

        result = await format_response(
            response_type="error",
            content=content
        )

        assert "Sorry" in result["formatted_response"]
        assert "Unable to process request" in result["formatted_response"]

    @pytest.mark.asyncio
    async def test_format_with_user_context(self):
        """Test formatting with user context."""
        content = {
            "total_calories": 400,
            "total_protein_g": 22
        }

        user_context = {
            "name": "John",
            "daily_calorie_goal": 2000
        }

        result = await format_response(
            response_type="nutrition_summary",
            content=content,
            user_context=user_context
        )

        assert "John" in result["formatted_response"] or "calories" in result["formatted_response"]