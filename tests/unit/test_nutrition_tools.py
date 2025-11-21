"""
Unit tests for nutrition tools.

Tests nutrition calculation, parsing, and storage functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch

from tools.nutrition.calculator import MealNutritionCalculatorTool, NutritionItem
from tools.nutrition.batch_parser import BatchFoodParserTool
from tools.nutrition.manual_entry import process_manual_calorie_entry
from agents.base import ToolResult


class TestNutritionCalculatorTool:
    """Test cases for nutrition calculator tool."""

    @pytest.fixture
    def calculator_tool(self):
        """Create calculator tool instance."""
        return MealNutritionCalculatorTool()

    @pytest.mark.asyncio
    async def test_calculate_meal_nutrition_success(self, calculator_tool, mock_gemini_api):
        """Test successful nutrition calculation."""
        parsed_items = [
            {
                "description": "2 eggs",
                "quantity": 2.0,
                "unit": "piece",
                "parsed_food": "egg",
                "confidence": 0.9
            },
            {
                "description": "1 cup rice",
                "quantity": 1.0,
                "unit": "cup",
                "parsed_food": "rice",
                "confidence": 0.85
            }
        ]

        result = await calculator_tool.execute(
            parsed_items=parsed_items,
            meal_type="breakfast",
            user_id="test_user"
        )

        assert_tool_result_success(result)
        assert "total_calories" in result.data
        assert "total_protein_g" in result.data
        assert "macros" in result.data
        assert result.data["total_calories"] > 0
        assert result.data["total_protein_g"] > 0

    @pytest.mark.asyncio
    async def test_calculate_meal_nutrition_empty_items(self, calculator_tool):
        """Test nutrition calculation with empty items."""
        result = await calculator_tool.execute(
            parsed_items=[],
            meal_type="breakfast",
            user_id="test_user"
        )

        assert result.success is False
        assert "No food items provided" in result.error

    @pytest.mark.asyncio
    async def test_calculate_meal_nutrition_invalid_items(self, calculator_tool):
        """Test nutrition calculation with invalid items."""
        invalid_items = [
            {"invalid": "data"}
        ]

        result = await calculator_tool.execute(
            parsed_items=invalid_items,
            meal_type="breakfast",
            user_id="test_user"
        )

        assert result.success is False
        assert "error" in result.error.lower()

    @pytest.mark.asyncio
    async def test_nutrition_item_creation(self):
        """Test NutritionItem dataclass creation."""
        item = NutritionItem(
            food_name="chicken breast",
            calories=165.0,
            protein_g=31.0,
            carbs_g=0.0,
            fat_g=3.6,
            confidence=0.9,
            source="USDA"
        )

        assert item.food_name == "chicken breast"
        assert item.calories == 165.0
        assert item.protein_g == 31.0
        assert item.confidence == 0.9
        assert item.source == "USDA"


class TestBatchFoodParserTool:
    """Test cases for batch food parser tool."""

    @pytest.fixture
    def parser_tool(self):
        """Create parser tool instance."""
        return BatchFoodParserTool()

    @pytest.mark.asyncio
    async def test_parse_simple_food_items(self, parser_tool):
        """Test parsing simple food descriptions."""
        food_descriptions = ["2 eggs", "1 apple", "200g chicken"]

        result = await parser_tool.execute(
            food_descriptions=food_descriptions,
            meal_type="breakfast",
            user_id="test_user"
        )

        assert_tool_result_success(result)
        assert len(result.data["parsed_items"]) == 3

        # Check first item (eggs)
        eggs_item = result.data["parsed_items"][0]
        assert eggs_item["quantity"] == 2.0
        assert eggs_item["unit"] == "piece"
        assert eggs_item["parsed_food"] == "eggs"
        assert eggs_item["confidence"] >= 0.8

    @pytest.mark.asyncio
    async def test_parse_fraction_quantities(self, parser_tool):
        """Test parsing fractional quantities."""
        food_descriptions = ["1/2 cup rice", "0.5 apple"]

        result = await parser_tool.execute(
            food_descriptions=food_descriptions,
            meal_type="lunch",
            user_id="test_user"
        )

        assert_tool_result_success(result)
        assert len(result.data["parsed_items"]) == 2

        rice_item = result.data["parsed_items"][0]
        assert rice_item["quantity"] == 0.5
        assert rice_item["unit"] == "cup"
        assert rice_item["parsed_food"] == "rice"

    @pytest.mark.asyncio
    async def test_parse_word_quantities(self, parser_tool):
        """Test parsing word-based quantities."""
        food_descriptions = ["a banana", "half chicken breast"]

        result = await parser_tool.execute(
            food_descriptions=food_descriptions,
            meal_type="snack",
            user_id="test_user"
        )

        assert_tool_result_success(result)
        assert len(result.data["parsed_items"]) == 2

        banana_item = result.data["parsed_items"][0]
        assert banana_item["quantity"] == 1.0
        assert banana_item["parsed_food"] == "banana"

    @pytest.mark.asyncio
    async def test_parse_batch_size_limit(self, parser_tool):
        """Test batch size limit enforcement."""
        # Create 11 items (over limit)
        food_descriptions = [f"item {i}" for i in range(11)]

        result = await parser_tool.execute(
            food_descriptions=food_descriptions,
            meal_type="dinner",
            user_id="test_user"
        )

        assert result.success is False
        assert "Batch size exceeds maximum" in result.error

    @pytest.mark.asyncio
    async def test_parse_empty_batch(self, parser_tool):
        """Test parsing empty batch."""
        result = await parser_tool.execute(
            food_descriptions=[],
            meal_type="breakfast",
            user_id="test_user"
        )

        assert result.success is False
        assert "No food descriptions provided" in result.error

    @pytest.mark.asyncio
    async def test_parse_misspellings(self, parser_tool):
        """Test parsing with common misspellings."""
        food_descriptions = ["chiken breast", "bannana"]

        result = await parser_tool.execute(
            food_descriptions=food_descriptions,
            meal_type="lunch",
            user_id="test_user"
        )

        assert_tool_result_success(result)
        assert len(result.data["parsed_items"]) == 2

        # Should still parse even with misspellings
        chicken_item = result.data["parsed_items"][0]
        assert "chicken" in chicken_item["parsed_food"].lower() or "chiken" in chicken_item["parsed_food"].lower()
        assert chicken_item["confidence"] < 0.9  # Lower confidence for misspellings


class TestManualCalorieEntry:
    """Test cases for manual calorie entry processing."""

    @pytest.mark.asyncio
    async def test_manual_calorie_entry_simple(self):
        """Test simple manual calorie entry."""
        text = "500 calories"

        result = process_manual_calorie_entry(text)

        assert result["status"] == "success"
        assert result["calories"] == 500
        assert result["description"] == "Manual calorie entry"

    @pytest.mark.asyncio
    async def test_manual_calorie_entry_with_description(self):
        """Test manual entry with description."""
        text = "ate 300 calories from pizza"

        result = process_manual_calorie_entry(text)

        assert result["status"] == "success"
        assert result["calories"] == 300
        assert "pizza" in result["description"].lower()

    @pytest.mark.asyncio
    async def test_manual_calorie_entry_invalid(self):
        """Test invalid manual calorie entry."""
        text = "no calories mentioned"

        result = process_manual_calorie_entry(text)

        assert result["status"] == "error"
        assert "Could not parse" in result["error"]

    @pytest.mark.asyncio
    async def test_manual_calorie_entry_edge_cases(self):
        """Test edge cases for manual entry."""
        test_cases = [
            ("0 calories", 0),
            ("1000 calories", 1000),
            ("ate 250 cal", 250),
        ]

        for text, expected_calories in test_cases:
            result = process_manual_calorie_entry(text)
            assert result["status"] == "success"
            assert result["calories"] == expected_calories


# Helper function for tool result assertions
def assert_tool_result_success(result: ToolResult, expected_data_keys: list = None):
    """Assert that a tool result indicates success."""
    assert isinstance(result, ToolResult)
    assert result.success is True
    assert result.error is None
    if expected_data_keys and result.data:
        for key in expected_data_keys:
            assert key in result.data