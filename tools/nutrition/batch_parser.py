"""
Batch food parsing tools for nutrition logging.

This module provides tools for parsing natural language food descriptions
into structured data for nutrition calculation. Supports batch processing
of multiple food items with confidence scoring.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


@dataclass
class ParsedFoodItem:
    """Structured representation of a parsed food item."""
    description: str
    quantity: float
    unit: str
    parsed_food: str
    confidence: float


class BatchFoodParserTool(BaseTool):
    """
    Tool for parsing batch food descriptions into structured format.

    Uses pattern matching and heuristics to extract quantity, unit, and food name
    from natural language descriptions. Supports batch processing for meal logging.
    """

    def __init__(self):
        super().__init__(
            name="parse_meal_batch",
            description="Parse and validate a batch of food items for nutrition calculation",
            parameters={
                "type": "object",
                "properties": {
                    "food_descriptions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of food item descriptions",
                        "maxItems": 10
                    },
                    "meal_type": {
                        "type": "string",
                        "enum": ["breakfast", "lunch", "dinner", "snack"],
                        "description": "Type of meal"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "Telegram user ID for context"
                    }
                },
                "required": ["food_descriptions", "meal_type", "user_id"]
            }
        )

        # Common food units and their normalizations
        self.UNITS = {
            # Volume
            'cup': 'cup', 'cups': 'cup', 'c': 'cup',
            'tablespoon': 'tablespoon', 'tablespoons': 'tablespoon', 'tbsp': 'tablespoon', 'tbs': 'tablespoon',
            'teaspoon': 'teaspoon', 'teaspoons': 'teaspoon', 'tsp': 'teaspoon',
            'liter': 'liter', 'liters': 'liter', 'l': 'liter',
            'milliliter': 'milliliter', 'milliliters': 'milliliter', 'ml': 'milliliter',
            'gallon': 'gallon', 'gallons': 'gallon', 'gal': 'gallon',
            'quart': 'quart', 'quarts': 'quart', 'qt': 'quart',
            'pint': 'pint', 'pints': 'pint', 'pt': 'pint',
            'fluid ounce': 'fluid_ounce', 'fluid ounces': 'fluid_ounce', 'fl oz': 'fluid_ounce',

            # Weight
            'pound': 'pound', 'pounds': 'pound', 'lb': 'pound', 'lbs': 'pound',
            'ounce': 'ounce', 'ounces': 'ounce', 'oz': 'ounce',
            'gram': 'gram', 'grams': 'gram', 'g': 'gram',
            'kilogram': 'kilogram', 'kilograms': 'kilogram', 'kg': 'kilogram',

            # Count
            'piece': 'piece', 'pieces': 'piece',
            'slice': 'slice', 'slices': 'slice',
            'whole': 'whole',
            'half': 'half',
            'quarter': 'quarter', 'quarters': 'quarter'
        }

        # Quantity patterns
        self.QUANTITY_PATTERNS = [
            (r'^(\d+(?:\.\d+)?)\s+(.+)$', 0.9),  # "2 eggs"
            (r'^(\d+)\s*/\s*(\d+)\s+(.+)$', 0.8),  # "1/2 cup"
            (r'^(a|an)\s+(.+)$', 0.7),  # "a banana"
            (r'^(half|quarter)\s+(?:a|an)?\s*(.+)$', 0.8),  # "half apple"
            (r'^(one|two|three|four|five|six|seven|eight|nine|ten)\s+(.+)$', 0.8),  # "two eggs"
        ]

        # Word to number mapping
        self.WORD_NUMBERS = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'a': 1, 'an': 1, 'half': 0.5, 'quarter': 0.25
        }

    async def execute(
        self,
        food_descriptions: List[str],
        meal_type: str,
        user_id: str,
        tool_context: Optional[Any] = None
    ) -> ToolResult:
        """
        Parse batch of food descriptions.

        Args:
            food_descriptions: List of food item descriptions (max 10)
            meal_type: Type of meal
            user_id: User ID for context
            tool_context: ADK tool context

        Returns:
            ToolResult with parsed items or error
        """
        try:
            # Validate batch size
            if len(food_descriptions) > 10:
                return ToolResult(
                    success=False,
                    error="Batch size exceeds maximum of 10 items"
                )

            if len(food_descriptions) == 0:
                return ToolResult(
                    success=False,
                    error="No food descriptions provided"
                )

            parsed_items = []
            validation_errors = []

            for i, description in enumerate(food_descriptions):
                try:
                    parsed = self._parse_food_description(description)
                    parsed_items.append(parsed)
                except Exception as e:
                    validation_errors.append(f"Item {i+1}: {str(e)}")
                    # Add with low confidence
                    parsed_items.append(ParsedFoodItem(
                        description=description,
                        quantity=1.0,
                        unit="piece",
                        parsed_food=description,
                        confidence=0.1
                    ))

            batch_complete = len(validation_errors) == 0

            return ToolResult(
                success=True,
                data={
                    "parsed_items": [
                        {
                            "description": item.description,
                            "quantity": item.quantity,
                            "unit": item.unit,
                            "parsed_food": item.parsed_food,
                            "confidence": item.confidence
                        }
                        for item in parsed_items
                    ],
                    "batch_complete": batch_complete,
                    "validation_errors": validation_errors
                }
            )

        except Exception as e:
            logger.error(f"Batch parsing failed: {e}")
            return ToolResult(
                success=False,
                error=f"Batch parsing failed: {str(e)}"
            )

    def _parse_food_description(self, description: str) -> ParsedFoodItem:
        """
        Parse a single food description into structured format.

        Args:
            description: Natural language food description

        Returns:
            ParsedFoodItem: Structured food data

        Raises:
            ValueError: If parsing fails
        """
        original_desc = description.strip()
        desc = original_desc.lower()

        # Try each pattern
        for pattern, base_confidence in self.QUANTITY_PATTERNS:
            match = re.match(pattern, desc)
            if match:
                return self._extract_from_match(match, original_desc, base_confidence)

        # Fallback: treat as single item
        return ParsedFoodItem(
            description=original_desc,
            quantity=1.0,
            unit="piece",
            parsed_food=original_desc,
            confidence=0.5
        )

    def _extract_from_match(self, match: re.Match, original_desc: str, base_confidence: float) -> ParsedFoodItem:
        """Extract quantity, unit, and food from regex match."""
        groups = match.groups()

        if len(groups) == 2:
            # Pattern: quantity + food
            qty_str, food_part = groups
            quantity = self._parse_quantity(qty_str)
        elif len(groups) == 3:
            # Pattern: fraction or word number + food
            if '/' in groups[0]:
                # Fraction like "1/2"
                num, denom = groups[0].split('/')
                quantity = float(num) / float(denom)
                food_part = groups[2]
            else:
                # Word number
                quantity = self._parse_quantity(groups[0])
                food_part = groups[2]
        else:
            raise ValueError(f"Unexpected match groups: {groups}")

        # Extract unit and food from food_part
        unit, food, unit_confidence = self._extract_unit_and_food(food_part)

        # Calculate overall confidence
        confidence = min(base_confidence * unit_confidence, 1.0)

        return ParsedFoodItem(
            description=original_desc,
            quantity=quantity,
            unit=unit,
            parsed_food=food,
            confidence=confidence
        )

    def _parse_quantity(self, qty_str: str) -> float:
        """Parse quantity string to float."""
        qty_str = qty_str.lower().strip()

        # Word numbers
        if qty_str in self.WORD_NUMBERS:
            return float(self.WORD_NUMBERS[qty_str])

        # Fractions
        if '/' in qty_str:
            try:
                num, denom = qty_str.split('/')
                return float(num) / float(denom)
            except (ValueError, ZeroDivisionError):
                pass

        # Regular numbers
        try:
            return float(qty_str)
        except ValueError:
            return 1.0  # fallback

    def _extract_unit_and_food(self, food_part: str) -> Tuple[str, str, float]:
        """
        Extract unit and food name from food part.

        Returns:
            Tuple of (unit, food_name, confidence)
        """
        words = food_part.lower().split()
        unit = "piece"  # default
        confidence = 0.8

        # Look for unit at the beginning
        if words and words[0] in self.UNITS:
            unit = self.UNITS[words[0]]
            food_words = words[1:]
            confidence = 0.9
        else:
            food_words = words

        # Clean up food name
        food_name = ' '.join(food_words).strip()

        # Remove common articles
        food_name = re.sub(r'^(a|an|the)\s+', '', food_name)

        # If no food name left, use original
        if not food_name:
            food_name = food_part
            confidence = 0.6

        return unit, food_name, confidence


# Create singleton instance
batch_parser_tool = BatchFoodParserTool()


# Convenience function for direct use
async def parse_meal_batch(
    food_descriptions: List[str],
    meal_type: str,
    user_id: str,
    tool_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Parse a batch of food items for nutrition calculation.

    This is the main API function that matches the contract specification.

    Args:
        food_descriptions: List of food item descriptions (max 10 items)
        meal_type: Type of meal ('breakfast', 'lunch', 'dinner', 'snack')
        user_id: Telegram user ID for context
        tool_context: Optional ADK tool context

    Returns:
        Dict with status, data, and error fields
    """
    result = await batch_parser_tool.execute(
        food_descriptions=food_descriptions,
        meal_type=meal_type,
        user_id=user_id,
        tool_context=tool_context
    )

    return {
        "status": "success" if result.success else "error",
        "data": result.data,
        "error": result.error
    }


__all__ = ['BatchFoodParserTool', 'batch_parser_tool', 'parse_meal_batch']