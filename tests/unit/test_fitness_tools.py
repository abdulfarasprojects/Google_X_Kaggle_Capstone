"""
Unit tests for fitness tools.

Tests workout parsing, volume calculation, and progression tracking.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import date, timedelta

from tools.fitness.calculator import VolumeCalculatorTool
from tools.fitness.batch_parser import BatchWorkoutParserTool, ParsedExercise
from tools.fitness.progress import ProgressionSuggesterTool as ProgressTrackerTool
from agents.base import ToolResult


class TestVolumeCalculatorTool:
    """Test cases for volume calculator tool."""

    @pytest.fixture
    def volume_tool(self):
        """Create volume calculator tool instance."""
        return VolumeCalculatorTool()

    @pytest.mark.asyncio
    async def test_calculate_weighted_exercise_volume(self, volume_tool):
        """Test volume calculation for weighted exercises."""
        exercises = [
            {
                "exercise_name": "bench press",
                "sets": 3,
                "reps": 10,
                "weight": 80.0,
                "weight_unit": "kg"
            },
            {
                "exercise_name": "squats",
                "sets": 4,
                "reps": 8,
                "weight": 100.0,
                "weight_unit": "kg"
            }
        ]

        result = await volume_tool.execute(
            parsed_exercises=exercises,
            user_id="test_user"
        )

        assert_tool_result_success(result)
        assert result.data["total_volume"] == (3*10*80) + (4*8*100)  # 2400 + 3200 = 5600
        assert len(result.data["exercise_breakdown"]) == 2
        assert result.data["volume_category"] == "intense"

    @pytest.mark.asyncio
    async def test_calculate_bodyweight_exercise_volume(self, volume_tool):
        """Test volume calculation for bodyweight exercises."""
        exercises = [
            {
                "exercise_name": "push-ups",
                "sets": 3,
                "reps": 15,
                "weight": None
            },
            {
                "exercise_name": "pull-ups",
                "sets": 4,
                "reps": 8,
                "weight": None
            }
        ]

        result = await volume_tool.execute(
            parsed_exercises=exercises,
            user_id="test_user"
        )

        assert_tool_result_success(result)
        assert result.data["total_volume"] == (3*15) + (4*8)  # 45 + 32 = 77
        assert result.data["volume_category"] == "light"

    @pytest.mark.asyncio
    async def test_calculate_mixed_exercises_volume(self, volume_tool):
        """Test volume calculation for mixed weighted and bodyweight exercises."""
        exercises = [
            {
                "exercise_name": "bench press",
                "sets": 3,
                "reps": 10,
                "weight": 70.0
            },
            {
                "exercise_name": "push-ups",
                "sets": 3,
                "reps": 20,
                "weight": None
            }
        ]

        result = await volume_tool.execute(
            parsed_exercises=exercises,
            user_id="test_user"
        )

        assert_tool_result_success(result)
        assert result.data["total_volume"] == (3*10*70) + (3*20)  # 2100 + 60 = 2160
        assert result.data["volume_category"] == "heavy"

    @pytest.mark.asyncio
    async def test_calculate_empty_exercises(self, volume_tool):
        """Test volume calculation with empty exercises."""
        result = await volume_tool.execute(
            parsed_exercises=[],
            user_id="test_user"
        )

        assert result.success is False
        assert "No exercises provided" in result.error

    @pytest.mark.asyncio
    async def test_calculate_progression_improvement(self, volume_tool):
        """Test progression calculation showing improvement."""
        current_exercises = [
            {
                "exercise_name": "bench press",
                "sets": 3,
                "reps": 12,
                "weight": 85.0
            }
        ]

        previous_workouts = [
            {
                "log_date": (date.today() - timedelta(days=7)).isoformat(),
                "exercises": [
                    {
                        "exercise_name": "bench press",
                        "sets": 3,
                        "reps": 10,
                        "weight": 80.0
                    }
                ]
            }
        ]

        result = await volume_tool.execute(
            parsed_exercises=current_exercises,
            user_id="test_user",
            previous_workouts=previous_workouts
        )

        assert_tool_result_success(result)
        assert result.data["progression"]["available"] is True
        assert result.data["progression"]["overall_trend"] == "improved"
        assert len(result.data["progression"]["exercise_progression"]) == 1

    @pytest.mark.asyncio
    async def test_calculate_progression_decline(self, volume_tool):
        """Test progression calculation showing decline."""
        current_exercises = [
            {
                "exercise_name": "squats",
                "sets": 3,
                "reps": 8,
                "weight": 90.0
            }
        ]

        previous_workouts = [
            {
                "log_date": (date.today() - timedelta(days=7)).isoformat(),
                "exercises": [
                    {
                        "exercise_name": "squats",
                        "sets": 4,
                        "reps": 10,
                        "weight": 100.0
                    }
                ]
            }
        ]

        result = await volume_tool.execute(
            parsed_exercises=current_exercises,
            user_id="test_user",
            previous_workouts=previous_workouts
        )

        assert_tool_result_success(result)
        assert result.data["progression"]["overall_trend"] == "declined"

    @pytest.mark.asyncio
    async def test_calculate_no_previous_workouts(self, volume_tool):
        """Test volume calculation without previous workout data."""
        exercises = [
            {
                "exercise_name": "deadlifts",
                "sets": 3,
                "reps": 5,
                "weight": 120.0
            }
        ]

        result = await volume_tool.execute(
            parsed_exercises=exercises,
            user_id="test_user",
            previous_workouts=[]
        )

        assert_tool_result_success(result)
        assert result.data["progression"]["available"] is False
        assert "No recent workouts" in result.data["progression"]["message"]


class TestBatchWorkoutParserTool:
    """Test cases for batch workout parser tool."""

    @pytest.fixture
    def parser_tool(self):
        """Create workout parser tool instance."""
        return BatchWorkoutParserTool()

    @pytest.mark.asyncio
    async def test_parse_weighted_exercises(self, parser_tool):
        """Test parsing weighted exercise descriptions."""
        descriptions = [
            "3 sets bench press 10 reps 80kg",
            "4 sets squats 8 reps 100kg"
        ]

        result = await parser_tool.execute(
            exercise_descriptions=descriptions,
            user_id="test_user"
        )

        assert_tool_result_success(result)
        assert len(result.data["parsed_exercises"]) == 2

        bench_press = result.data["parsed_exercises"][0]
        assert bench_press["exercise_name"] == "bench press"
        assert bench_press["sets"] == 3
        assert bench_press["reps"] == 10
        assert bench_press["weight"] == 80.0
        assert bench_press["weight_unit"] == "kg"

    @pytest.mark.asyncio
    async def test_parse_bodyweight_exercises(self, parser_tool):
        """Test parsing bodyweight exercise descriptions."""
        descriptions = [
            "3 sets push-ups 15 reps",
            "4 sets pull-ups 8 reps"
        ]

        result = await parser_tool.execute(
            exercise_descriptions=descriptions,
            user_id="test_user"
        )

        assert_tool_result_success(result)
        assert len(result.data["parsed_exercises"]) == 2

        pushups = result.data["parsed_exercises"][0]
        assert pushups["exercise_name"] == "push-ups"
        assert pushups["sets"] == 3
        assert pushups["reps"] == 15
        assert pushups["weight"] is None

    @pytest.mark.asyncio
    async def test_parse_varied_formats(self, parser_tool):
        """Test parsing exercises in varied formats."""
        descriptions = [
            "bench press 3x10 75lbs",
            "10 pull-ups",
            "squats 4 sets of 8 at 90kg"
        ]

        result = await parser_tool.execute(
            exercise_descriptions=descriptions,
            user_id="test_user"
        )

        assert_tool_result_success(result)
        assert len(result.data["parsed_exercises"]) == 3

    @pytest.mark.asyncio
    async def test_parse_batch_size_limit(self, parser_tool):
        """Test batch size limit enforcement."""
        descriptions = [f"exercise {i} 3 sets 10 reps" for i in range(11)]

        result = await parser_tool.execute(
            exercise_descriptions=descriptions,
            user_id="test_user"
        )

        assert result.success is False
        assert "Batch size exceeds maximum" in result.error

    @pytest.mark.asyncio
    async def test_parse_empty_batch(self, parser_tool):
        """Test parsing empty batch."""
        result = await parser_tool.execute(
            exercise_descriptions=[],
            user_id="test_user"
        )

        assert result.success is False
        assert "No exercise descriptions provided" in result.error

    @pytest.mark.asyncio
    async def test_parse_invalid_formats(self, parser_tool):
        """Test parsing invalid exercise formats."""
        descriptions = [
            "random text that is not an exercise",
            "exercise with no numbers"
        ]

        result = await parser_tool.execute(
            exercise_descriptions=descriptions,
            user_id="test_user"
        )

        assert_tool_result_success(result)
        # Should still attempt to parse, but with low confidence
        assert len(result.data["parsed_exercises"]) == 2
        for exercise in result.data["parsed_exercises"]:
            assert exercise["confidence"] < 0.5

    @pytest.mark.asyncio
    async def test_parse_mixed_weight_units(self, parser_tool):
        """Test parsing exercises with different weight units."""
        descriptions = [
            "bench press 3x10 200lbs",
            "squats 4x8 90kg"
        ]

        result = await parser_tool.execute(
            exercise_descriptions=descriptions,
            user_id="test_user"
        )

        assert_tool_result_success(result)
        assert len(result.data["parsed_exercises"]) == 2

        bench = result.data["parsed_exercises"][0]
        squats = result.data["parsed_exercises"][1]

        assert bench["weight_unit"] == "lbs"
        assert squats["weight_unit"] == "kg"


class TestProgressTrackerTool:
    """Test cases for progress tracker tool."""

    @pytest.fixture
    def progress_tool(self):
        """Create progress tracker tool instance."""
        return ProgressTrackerTool()

    @pytest.mark.asyncio
    async def test_track_exercise_progress(self, progress_tool):
        """Test tracking progress for specific exercises."""
        exercise_name = "bench press"
        user_id = "test_user"

        result = await progress_tool.execute(
            exercise_name=exercise_name,
            user_id=user_id,
            timeframe_days=30
        )

        assert_tool_result_success(result)
        assert "progress_data" in result.data
        assert "trend" in result.data
        assert "recommendations" in result.data

    @pytest.mark.asyncio
    async def test_track_overall_progress(self, progress_tool):
        """Test tracking overall workout progress."""
        user_id = "test_user"

        result = await progress_tool.execute(
            user_id=user_id,
            timeframe_days=90
        )

        assert_tool_result_success(result)
        assert "overall_progress" in result.data
        assert "volume_trend" in result.data
        assert "strength_gains" in result.data


# Helper function for tool result assertions
def assert_tool_result_success(result: ToolResult, expected_data_keys: list = None):
    """Assert that a tool result indicates success."""
    assert isinstance(result, ToolResult)
    assert result.success is True
    assert result.error is None
    if expected_data_keys and result.data:
        for key in expected_data_keys:
            assert key in result.data