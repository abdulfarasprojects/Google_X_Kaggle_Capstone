"""
Unit tests for intent classifier tool.

Tests intent classification accuracy against various inputs.
"""

import pytest
from unittest.mock import MagicMock

from tools.intent_classifier import classify_intent


class TestIntentClassifier:
    """Test cases for intent classification functionality."""

    @pytest.mark.asyncio
    async def test_nutrition_intent_food_keywords(self):
        """Test nutrition intent detection with food keywords."""
        test_cases = [
            ("I ate breakfast", "nutrition"),
            ("ate lunch with chicken", "nutrition"),
            ("dinner was rice and vegetables", "nutrition"),
            ("snack time - apple", "nutrition"),
            ("hungry for some protein", "nutrition"),
            ("cooked a meal", "nutrition"),
        ]

        for message, expected_intent in test_cases:
            result = await classify_intent(message)
            assert result["intent"] == expected_intent
            assert result["confidence"] >= 0.5
            assert "reasoning" in result

    @pytest.mark.asyncio
    async def test_fitness_intent_exercise_keywords(self):
        """Test fitness intent detection with exercise keywords."""
        test_cases = [
            ("did squats today", "fitness"),
            ("worked out at gym", "fitness"),
            ("ran 5km this morning", "fitness"),
            ("cardio session", "fitness"),
            ("strength training", "fitness"),
            ("lifted weights", "fitness"),
        ]

        for message, expected_intent in test_cases:
            result = await classify_intent(message)
            assert result["intent"] == expected_intent
            assert result["confidence"] >= 0.5
            assert "reasoning" in result

    @pytest.mark.asyncio
    async def test_wellness_intent_health_keywords(self):
        """Test wellness intent detection with health keywords."""
        test_cases = [
            ("slept 8 hours", "wellness"),
            ("drank 8 glasses of water", "wellness"),
            ("walked 10000 steps", "wellness"),
            ("feeling tired", "wellness"),
            ("good rest today", "wellness"),
            ("high energy levels", "wellness"),
        ]

        for message, expected_intent in test_cases:
            result = await classify_intent(message)
            assert result["intent"] == expected_intent
            assert result["confidence"] >= 0.5
            assert "reasoning" in result

    @pytest.mark.asyncio
    async def test_analytics_intent_progress_keywords(self):
        """Test analytics intent detection with progress keywords."""
        test_cases = [
            ("how is my progress", "analytics"),
            ("show me stats", "analytics"),
            ("weekly summary", "analytics"),
            ("weight loss trend", "analytics"),
            ("calorie average", "analytics"),
            ("workout streak", "analytics"),
        ]

        for message, expected_intent in test_cases:
            result = await classify_intent(message)
            assert result["intent"] == expected_intent
            assert result["confidence"] >= 0.5
            assert "reasoning" in result

    @pytest.mark.asyncio
    async def test_help_intent_question_keywords(self):
        """Test help intent detection with question keywords."""
        test_cases = [
            ("how does this work", "help"),
            ("what can you do", "help"),
            ("help me please", "help"),
            ("what are the commands", "help"),
            ("how to use this", "help"),
        ]

        for message, expected_intent in test_cases:
            result = await classify_intent(message)
            assert result["intent"] == expected_intent
            assert result["confidence"] >= 0.5
            assert "reasoning" in result

    @pytest.mark.asyncio
    async def test_default_fallback(self):
        """Test default fallback to nutrition intent."""
        test_cases = [
            "random message",
            "something unclear",
            "no keywords here",
            "",
            "   ",
        ]

        for message in test_cases:
            result = await classify_intent(message)
            assert result["intent"] == "nutrition"  # Default fallback
            assert result["confidence"] <= 0.6  # Lower confidence for unclear messages
            assert "reasoning" in result

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(self):
        """Test that classification is case insensitive."""
        test_cases = [
            ("ATE BREAKFAST", "nutrition"),
            ("Did Squats Today", "fitness"),
            ("SLEPT WELL", "wellness"),
            ("How Is My Progress", "analytics"),
        ]

        for message, expected_intent in test_cases:
            result = await classify_intent(message)
            assert result["intent"] == expected_intent
            assert result["confidence"] >= 0.5

    @pytest.mark.asyncio
    async def test_whitespace_handling(self):
        """Test handling of extra whitespace."""
        test_cases = [
            ("  ate breakfast  ", "nutrition"),
            ("did   squats", "fitness"),
            ("\tslept well\n", "wellness"),
        ]

        for message, expected_intent in test_cases:
            result = await classify_intent(message)
            assert result["intent"] == expected_intent
            assert result["confidence"] >= 0.5

    @pytest.mark.asyncio
    async def test_confidence_levels(self):
        """Test that confidence levels are appropriate."""
        # High confidence cases
        high_confidence_cases = [
            "I ate chicken for lunch",
            "squats 3 sets of 10",
            "slept 8 hours quality 9/10",
            "show me my progress",
        ]

        for message in high_confidence_cases:
            result = await classify_intent(message)
            assert result["confidence"] >= 0.7

        # Lower confidence cases
        low_confidence_cases = [
            "random text",
            "unclear message",
        ]

        for message in low_confidence_cases:
            result = await classify_intent(message)
            assert result["confidence"] <= 0.6

    @pytest.mark.asyncio
    async def test_reasoning_field(self):
        """Test that reasoning field is present and meaningful."""
        test_cases = [
            "ate breakfast",
            "did squats",
            "slept well",
            "show progress",
        ]

        for message in test_cases:
            result = await classify_intent(message)
            assert "reasoning" in result
            assert len(result["reasoning"]) > 0
            assert "keywords" in result["reasoning"].lower()

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling for invalid inputs."""
        # Test with None input
        result = await classify_intent(None)
        assert result["intent"] == "nutrition"
        assert result["confidence"] <= 0.2
        assert "error" in result["reasoning"].lower() or "Classification error" in result["reasoning"]

    @pytest.mark.asyncio
    async def test_tool_context_handling(self):
        """Test handling of tool context parameter."""
        # Mock tool context
        mock_context = MagicMock()
        mock_context._invocation_context.session.user_id = "test_user"

        result = await classify_intent("ate breakfast", tool_context=mock_context)
        assert result["intent"] == "nutrition"
        assert result["confidence"] >= 0.5

        # Test without tool context
        result = await classify_intent("ate breakfast")
        assert result["intent"] == "nutrition"
        assert result["confidence"] >= 0.5