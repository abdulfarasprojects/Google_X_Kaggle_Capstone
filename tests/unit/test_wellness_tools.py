"""
Unit tests for wellness tools.

Tests wellness parsing, correlation analysis, and trend tracking.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import date, timedelta

from tools.wellness.parser import WellnessParserTool, ParsedWellnessEntry
from tools.wellness.correlations import WellnessCorrelationTool
from agents.base import ToolResult


class TestWellnessParserTool:
    """Test cases for wellness parser tool."""

    @pytest.fixture
    def parser_tool(self):
        """Create wellness parser tool instance."""
        return WellnessParserTool()

    @pytest.mark.asyncio
    async def test_parse_sleep_entries(self, parser_tool):
        """Test parsing sleep-related entries."""
        descriptions = [
            "slept 8 hours last night",
            "7.5 hours of sleep",
            "slept well, 9 hours"
        ]

        result = await parser_tool.execute(
            wellness_descriptions=descriptions,
            user_id="test_user"
        )

        assert_tool_result_success(result)
        assert len(result.data["parsed_entries"]) == 3

        sleep_entry = result.data["parsed_entries"][0]
        assert sleep_entry["entry_type"] == "sleep"
        assert sleep_entry["value"] == 8.0
        assert sleep_entry["unit"] == "hours"
        assert sleep_entry["confidence"] >= 0.8

    @pytest.mark.asyncio
    async def test_parse_water_entries(self, parser_tool):
        """Test parsing water intake entries."""
        descriptions = [
            "drank 8 glasses of water",
            "2 liters of water today",
            "10 cups water"
        ]

        result = await parser_tool.execute(
            wellness_descriptions=descriptions,
            user_id="test_user"
        )

        assert_tool_result_success(result)
        assert len(result.data["parsed_entries"]) == 3

        water_entry = result.data["parsed_entries"][0]
        assert water_entry["entry_type"] == "water"
        assert water_entry["value"] == 8.0
        assert water_entry["unit"] == "glasses"

    @pytest.mark.asyncio
    async def test_parse_steps_entries(self, parser_tool):
        """Test parsing steps count entries."""
        descriptions = [
            "walked 10000 steps today",
            "8000 steps yesterday",
            "12k steps"
        ]

        result = await parser_tool.execute(
            wellness_descriptions=descriptions,
            user_id="test_user"
        )

        assert_tool_result_success(result)
        assert len(result.data["parsed_entries"]) == 3

        steps_entry = result.data["parsed_entries"][0]
        assert steps_entry["entry_type"] == "steps"
        assert steps_entry["value"] == 10000.0
        assert steps_entry["unit"] == "steps"

    @pytest.mark.asyncio
    async def test_parse_mixed_wellness_entries(self, parser_tool):
        """Test parsing mixed wellness entries."""
        descriptions = [
            "slept 7 hours",
            "drank 6 glasses water",
            "walked 8500 steps"
        ]

        result = await parser_tool.execute(
            wellness_descriptions=descriptions,
            user_id="test_user"
        )

        assert_tool_result_success(result)
        assert len(result.data["parsed_entries"]) == 3

        entry_types = [entry["entry_type"] for entry in result.data["parsed_entries"]]
        assert "sleep" in entry_types
        assert "water" in entry_types
        assert "steps" in entry_types

    @pytest.mark.asyncio
    async def test_parse_batch_size_limit(self, parser_tool):
        """Test batch size limit enforcement."""
        descriptions = [f"wellness entry {i}" for i in range(11)]

        result = await parser_tool.execute(
            wellness_descriptions=descriptions,
            user_id="test_user"
        )

        assert result.success is False
        assert "Batch size exceeds maximum" in result.error

    @pytest.mark.asyncio
    async def test_parse_empty_batch(self, parser_tool):
        """Test parsing empty batch."""
        result = await parser_tool.execute(
            wellness_descriptions=[],
            user_id="test_user"
        )

        assert result.success is False
        assert "No wellness descriptions provided" in result.error

    @pytest.mark.asyncio
    async def test_parse_invalid_entries(self, parser_tool):
        """Test parsing invalid wellness entries."""
        descriptions = [
            "random text that is not wellness related",
            "exercise description instead of wellness"
        ]

        result = await parser_tool.execute(
            wellness_descriptions=descriptions,
            user_id="test_user"
        )

        assert_tool_result_success(result)
        # Should still attempt to parse, but with low confidence
        assert len(result.data["parsed_entries"]) == 2
        for entry in result.data["parsed_entries"]:
            assert entry["confidence"] < 0.5

    @pytest.mark.asyncio
    async def test_parse_varied_formats(self, parser_tool):
        """Test parsing wellness entries in varied formats."""
        descriptions = [
            "8 hrs sleep",
            "2L water",
            "10,000 steps",
            "slept 6.5h",
            "5 glasses H2O"
        ]

        result = await parser_tool.execute(
            wellness_descriptions=descriptions,
            user_id="test_user"
        )

        assert_tool_result_success(result)
        assert len(result.data["parsed_entries"]) == 5


class TestWellnessCorrelationTool:
    """Test cases for wellness correlation tool."""

    @pytest.fixture
    def correlation_tool(self):
        """Create wellness correlation tool instance."""
        return WellnessCorrelationTool()

    @pytest.mark.asyncio
    async def test_analyze_sleep_weight_correlation(self, correlation_tool):
        """Test analyzing correlation between sleep and weight loss."""
        wellness_data = [
            {
                "log_date": (date.today() - timedelta(days=i)).isoformat(),
                "sleep_hours": 8.0 if i % 2 == 0 else 6.0,
                "sleep_quality": 4 if i % 2 == 0 else 2,
                "water_glasses": 8,
                "steps_count": 8000
            } for i in range(14)  # 2 weeks of data
        ]

        weight_data = [
            {
                "log_date": (date.today() - timedelta(days=i)).isoformat(),
                "weight_kg": 80.0 - (i * 0.1)  # Gradual weight loss
            } for i in range(14)
        ]

        result = await correlation_tool.execute(
            wellness_data=wellness_data,
            weight_data=weight_data,
            user_id="test_user"
        )

        assert_tool_result_success(result)
        assert "correlations" in result.data
        assert "insights" in result.data
        assert "sleep" in result.data["correlations"]

    @pytest.mark.asyncio
    async def test_analyze_water_performance_correlation(self, correlation_tool):
        """Test analyzing correlation between water intake and workout performance."""
        wellness_data = [
            {
                "log_date": (date.today() - timedelta(days=i)).isoformat(),
                "sleep_hours": 7.5,
                "water_glasses": 10 if i % 2 == 0 else 4,  # Alternating high/low water
                "steps_count": 7000
            } for i in range(10)
        ]

        workout_data = [
            {
                "log_date": (date.today() - timedelta(days=i)).isoformat(),
                "total_volume": 2000 if i % 2 == 0 else 1500,  # Higher volume on high water days
                "exercises": []
            } for i in range(10)
        ]

        result = await correlation_tool.execute(
            wellness_data=wellness_data,
            workout_data=workout_data,
            user_id="test_user"
        )

        assert_tool_result_success(result)
        assert "water" in result.data["correlations"]
        assert "performance" in result.data["correlations"]

    @pytest.mark.asyncio
    async def test_analyze_steps_activity_correlation(self, correlation_tool):
        """Test analyzing correlation between steps and overall activity."""
        wellness_data = [
            {
                "log_date": (date.today() - timedelta(days=i)).isoformat(),
                "sleep_hours": 7.0,
                "water_glasses": 6,
                "steps_count": 5000 + (i * 500)  # Increasing steps
            } for i in range(7)
        ]

        result = await correlation_tool.execute(
            wellness_data=wellness_data,
            user_id="test_user"
        )

        assert_tool_result_success(result)
        assert "steps" in result.data["correlations"]
        assert "trends" in result.data

    @pytest.mark.asyncio
    async def test_analyze_insufficient_data(self, correlation_tool):
        """Test correlation analysis with insufficient data."""
        wellness_data = [
            {
                "log_date": date.today().isoformat(),
                "sleep_hours": 7.0,
                "water_glasses": 6,
                "steps_count": 5000
            }
        ]  # Only 1 day of data

        result = await correlation_tool.execute(
            wellness_data=wellness_data,
            user_id="test_user"
        )

        assert_tool_result_success(result)
        assert result.data["correlations"]["data_quality"] == "insufficient"

    @pytest.mark.asyncio
    async def test_generate_wellness_recommendations(self, correlation_tool):
        """Test generating wellness recommendations based on correlations."""
        # Create data showing poor sleep correlation with weight loss
        wellness_data = [
            {
                "log_date": (date.today() - timedelta(days=i)).isoformat(),
                "sleep_hours": 5.0,  # Consistently poor sleep
                "sleep_quality": 2,
                "water_glasses": 8,
                "steps_count": 8000
            } for i in range(14)
        ]

        weight_data = [
            {
                "log_date": (date.today() - timedelta(days=i)).isoformat(),
                "weight_kg": 80.0 - (i * 0.05)  # Slow weight loss
            } for i in range(14)
        ]

        result = await correlation_tool.execute(
            wellness_data=wellness_data,
            weight_data=weight_data,
            user_id="test_user"
        )

        assert_tool_result_success(result)
        assert "recommendations" in result.data
        assert len(result.data["recommendations"]) > 0
        # Should recommend improving sleep
        sleep_recs = [r for r in result.data["recommendations"] if "sleep" in r.lower()]
        assert len(sleep_recs) > 0


# Helper function for tool result assertions
def assert_tool_result_success(result: ToolResult, expected_data_keys: list = None):
    """Assert that a tool result indicates success."""
    assert isinstance(result, ToolResult)
    assert result.success is True
    assert result.error is None
    if expected_data_keys and result.data:
        for key in expected_data_keys:
            assert key in result.data