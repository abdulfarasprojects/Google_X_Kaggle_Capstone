"""
Unit tests for sentiment detector tool.

Tests sentiment analysis accuracy against various inputs.
"""

import pytest
from unittest.mock import MagicMock

from tools.sentiment_detector import detect_sentiment


class TestSentimentDetector:
    """Test cases for sentiment detection functionality."""

    @pytest.mark.asyncio
    async def test_positive_sentiment_detection(self):
        """Test positive sentiment detection."""
        test_cases = [
            ("feeling great today!", "positive"),
            ("awesome workout session", "positive"),
            ("proud of my progress", "positive"),
            ("excited for tomorrow", "positive"),
            ("love this app", "positive"),
            ("fantastic results", "positive"),
        ]

        for message, expected_sentiment in test_cases:
            result = await detect_sentiment(message)
            assert result["sentiment"] == expected_sentiment
            assert result["confidence"] >= 0.5
            assert "indicators" in result

    @pytest.mark.asyncio
    async def test_negative_sentiment_detection(self):
        """Test negative sentiment detection."""
        test_cases = [
            ("feeling frustrated", "negative"),
            ("this is hard", "negative"),
            ("struggling with motivation", "negative"),
            ("disappointed with results", "negative"),
            ("hate working out", "negative"),
            ("terrible day", "negative"),
        ]

        for message, expected_sentiment in test_cases:
            result = await detect_sentiment(message)
            assert result["sentiment"] == expected_sentiment
            assert result["confidence"] >= 0.5
            assert "indicators" in result

    @pytest.mark.asyncio
    async def test_neutral_sentiment_detection(self):
        """Test neutral sentiment detection."""
        test_cases = [
            ("what is my progress", "neutral"),
            ("how does this work", "neutral"),
            ("show me stats", "neutral"),
            ("ate breakfast", "neutral"),
            ("random message", "neutral"),
        ]

        for message, expected_sentiment in test_cases:
            result = await detect_sentiment(message)
            assert result["sentiment"] == expected_sentiment
            assert result["confidence"] >= 0.3
            assert "indicators" in result

    @pytest.mark.asyncio
    async def test_emotional_state_detection(self):
        """Test emotional state classification."""
        test_cases = [
            ("proud of losing weight", "accomplished"),
            ("excited for the weekend", "enthusiastic"),
            ("frustrated with slow progress", "frustrated"),
            ("worried about plateau", "concerned"),
            ("great workout today", "positive"),
        ]

        for message, expected_emotional_state in test_cases:
            result = await detect_sentiment(message)
            assert result["emotional_state"] == expected_emotional_state
            assert result["confidence"] >= 0.5

    @pytest.mark.asyncio
    async def test_exclamation_mark_enthusiasm(self):
        """Test that exclamation marks increase confidence."""
        message_with_exclamation = "great workout!"
        message_without = "great workout"

        result_with = await detect_sentiment(message_with_exclamation)
        result_without = await detect_sentiment(message_without)

        assert result_with["sentiment"] == "positive"
        assert result_without["sentiment"] == "positive"
        assert result_with["confidence"] >= result_without["confidence"]
        assert result_with["indicators"]["exclamation_marks"] == 1
        assert result_without["indicators"]["exclamation_marks"] == 0

    @pytest.mark.asyncio
    async def test_question_mark_neutral(self):
        """Test that question marks affect neutral sentiment."""
        message_with_question = "how am I doing?"
        message_without = "I am doing well"

        result_with = await detect_sentiment(message_with_question)
        result_without = await detect_sentiment(message_without)

        assert result_with["sentiment"] == "neutral"
        assert result_without["sentiment"] == "positive"
        assert result_with["indicators"]["question_marks"] == 1

    @pytest.mark.asyncio
    async def test_case_insensitive_detection(self):
        """Test that sentiment detection is case insensitive."""
        test_cases = [
            ("FEELING GREAT!", "positive"),
            ("Struggling Today", "negative"),
            ("How Am I Doing?", "neutral"),
        ]

        for message, expected_sentiment in test_cases:
            result = await detect_sentiment(message)
            assert result["sentiment"] == expected_sentiment

    @pytest.mark.asyncio
    async def test_whitespace_handling(self):
        """Test handling of extra whitespace."""
        test_cases = [
            ("  feeling great!  ", "positive"),
            (" struggling today ", "negative"),
            ("\thow am I doing?\n", "neutral"),
        ]

        for message, expected_sentiment in test_cases:
            result = await detect_sentiment(message)
            assert result["sentiment"] == expected_sentiment

    @pytest.mark.asyncio
    async def test_confidence_ranges(self):
        """Test that confidence values are within expected ranges."""
        test_messages = [
            "great!",
            "struggling",
            "how are you",
            "random text",
        ]

        for message in test_messages:
            result = await detect_sentiment(message)
            assert 0.0 <= result["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_indicators_structure(self):
        """Test that indicators field has correct structure."""
        result = await detect_sentiment("great workout!")

        required_keys = [
            "positive_words",
            "negative_words",
            "neutral_words",
            "exclamation_marks",
            "question_marks"
        ]

        for key in required_keys:
            assert key in result["indicators"]
            assert isinstance(result["indicators"][key], int)
            assert result["indicators"][key] >= 0

    @pytest.mark.asyncio
    async def test_multiple_sentiment_words(self):
        """Test handling of multiple sentiment words."""
        message = "feeling great and awesome today!"
        result = await detect_sentiment(message)

        assert result["sentiment"] == "positive"
        assert result["indicators"]["positive_words"] >= 2
        assert result["confidence"] >= 0.7  # Higher confidence with multiple indicators

    @pytest.mark.asyncio
    async def test_mixed_sentiment_resolution(self):
        """Test resolution when message has mixed sentiment."""
        # Positive should win with more positive words
        message = "feeling good but a little tired"
        result = await detect_sentiment(message)

        assert result["sentiment"] == "positive"
        assert result["indicators"]["positive_words"] >= 1

    @pytest.mark.asyncio
    async def test_empty_input_handling(self):
        """Test handling of empty or minimal inputs."""
        test_cases = ["", "   ", "ok"]

        for message in test_cases:
            result = await detect_sentiment(message)
            assert result["sentiment"] == "neutral"
            assert result["emotional_state"] == "neutral"
            assert 0.1 <= result["confidence"] <= 0.6

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling for invalid inputs."""
        # Test with None input
        result = await detect_sentiment(None)
        assert result["sentiment"] == "neutral"
        assert result["confidence"] <= 0.2
        assert "error" in result

    @pytest.mark.asyncio
    async def test_tool_context_handling(self):
        """Test handling of tool context parameter."""
        # Mock tool context
        mock_context = MagicMock()
        mock_context._invocation_context.session.user_id = "test_user"

        result = await detect_sentiment("feeling great!", tool_context=mock_context)
        assert result["sentiment"] == "positive"
        assert result["confidence"] >= 0.5

        # Test without tool context
        result = await detect_sentiment("feeling great!")
        assert result["sentiment"] == "positive"
        assert result["confidence"] >= 0.5