"""
Wellness parsing tools for sleep, water, and steps tracking.

This module provides tools for parsing natural language wellness entries
into structured data for correlation analysis and trend tracking.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


@dataclass
class ParsedWellnessEntry:
    """Structured representation of a parsed wellness entry."""
    entry_type: str  # 'sleep', 'water', 'steps'
    value: float
    unit: str
    description: str
    confidence: float


class WellnessParserTool(BaseTool):
    """
    Tool for parsing wellness entries (sleep, water, steps).

    Uses pattern matching to extract wellness metrics from natural language
    descriptions for manual entry tracking.
    """

    def __init__(self):
        super().__init__(
            name="parse_wellness_entries",
            description="Parse and validate wellness entries for sleep, water, and steps tracking",
            parameters={
                "type": "object",
                "properties": {
                    "wellness_descriptions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of wellness metric descriptions",
                        "maxItems": 10
                    },
                    "user_id": {
                        "type": "string",
                        "description": "Telegram user ID for context"
                    }
                },
                "required": ["wellness_descriptions", "user_id"]
            }
        )

        # Sleep patterns
        self.SLEEP_PATTERNS = [
            (r'^(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\s*(?:sleep|slept)?$', 0.95, 'sleep', 'hours'),
            (r'^slept\s+(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)$', 0.95, 'sleep', 'hours'),
            (r'^sleep\s*(?:quality)?\s*:?\s*(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)$', 0.9, 'sleep', 'hours'),
            (r'^(\d+)\s*(?:hours?|hrs?|h)\s+(\d+)\s*(?:minutes?|mins?|min|m)$', 0.9, 'sleep', 'hours'),
            (r'^(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\s+sleep\s+quality\s*:?\s*(\d+(?:\.\d+)?)\s*/?\s*10$', 0.85, 'sleep', 'hours'),
        ]

        # Water patterns
        self.WATER_PATTERNS = [
            (r'^(\d+(?:\.\d+)?)\s*(?:glasses?|cups?|bottles?)\s*(?:of\s+)?(?:water|water intake)?$', 0.95, 'water', 'glasses'),
            (r'^drank\s+(\d+(?:\.\d+)?)\s*(?:glasses?|cups?|bottles?)\s*(?:of\s+)?(?:water)?$', 0.95, 'water', 'glasses'),
            (r'^(\d+(?:\.\d+)?)\s*(?:liters?|litres?|l)\s*(?:of\s+)?(?:water)?$', 0.9, 'water', 'liters'),
            (r'^(\d+(?:\.\d+)?)\s*(?:milliliters?|millilitres?|ml)\s*(?:of\s+)?(?:water)?$', 0.9, 'water', 'ml'),
            (r'^water\s*:?\s*(\d+(?:\.\d+)?)\s*(?:glasses?|cups?|bottles?)?$', 0.85, 'water', 'glasses'),
        ]

        # Steps patterns
        self.STEPS_PATTERNS = [
            (r'^(\d+(?:,?\d+)*)\s*(?:steps?|step count)?$', 0.95, 'steps', 'steps'),
            (r'^(?:walked|steps?)\s*:?\s*(\d+(?:,?\d+)*)$', 0.95, 'steps', 'steps'),
            (r'^(\d+)\s*(?:k|thousand)\s*(?:steps?|step count)?$', 0.9, 'steps', 'steps'),
            (r'^step\s+count\s*:?\s*(\d+(?:,?\d+)*)$', 0.9, 'steps', 'steps'),
        ]

        # Unit conversions
        self.UNIT_CONVERSIONS = {
            'water': {
                'glasses': 1.0,  # 1 glass = 8 oz
                'cups': 1.0,     # 1 cup = 8 oz (assume)
                'bottles': 1.0,  # 1 bottle = 8 oz (assume)
                'liters': 4.0,   # 1 liter = ~4 glasses
                'ml': 0.004,     # 1 ml = ~0.004 glasses
                'ounces': 0.125, # 1 oz = 0.125 glasses
                'oz': 0.125,
            }
        }

    async def execute(
        self,
        wellness_descriptions: List[str],
        user_id: str,
        tool_context: Optional[Any] = None
    ) -> ToolResult:
        """
        Parse batch of wellness descriptions.

        Args:
            wellness_descriptions: List of wellness metric descriptions (max 10)
            user_id: User ID for context
            tool_context: ADK tool context

        Returns:
            ToolResult with parsed wellness entries or error
        """
        try:
            # Validate batch size
            if len(wellness_descriptions) > 10:
                return ToolResult(
                    success=False,
                    error="Batch size exceeds maximum of 10 wellness entries"
                )

            if len(wellness_descriptions) == 0:
                return ToolResult(
                    success=False,
                    error="No wellness descriptions provided"
                )

            parsed_entries = []
            validation_errors = []

            for i, description in enumerate(wellness_descriptions):
                try:
                    parsed = self._parse_wellness_description(description)
                    parsed_entries.append(parsed)
                except Exception as e:
                    validation_errors.append(f"Entry {i+1}: {str(e)}")
                    # Add with low confidence defaults
                    parsed_entries.append(ParsedWellnessEntry(
                        entry_type="unknown",
                        value=0.0,
                        unit="unknown",
                        description=description,
                        confidence=0.1
                    ))

            batch_complete = len(validation_errors) == 0

            # Aggregate by type (sleep, water, steps)
            aggregated = self._aggregate_wellness_entries(parsed_entries)

            return ToolResult(
                success=True,
                data={
                    "parsed_entries": [
                        {
                            "entry_type": entry.entry_type,
                            "value": entry.value,
                            "unit": entry.unit,
                            "description": entry.description,
                            "confidence": entry.confidence
                        }
                        for entry in parsed_entries
                    ],
                    "aggregated": aggregated,
                    "batch_complete": batch_complete,
                    "validation_errors": validation_errors
                }
            )

        except Exception as e:
            logger.error(f"Batch wellness parsing failed: {e}")
            return ToolResult(
                success=False,
                error=f"Batch wellness parsing failed: {str(e)}"
            )

    def _parse_wellness_description(self, description: str) -> ParsedWellnessEntry:
        """
        Parse a single wellness description into structured format.

        Args:
            description: Natural language wellness description

        Returns:
            ParsedWellnessEntry: Structured wellness data

        Raises:
            ValueError: If parsing fails
        """
        original_desc = description.strip()
        desc = original_desc.lower()

        # Try sleep patterns
        for pattern, confidence, entry_type, unit in self.SLEEP_PATTERNS:
            match = re.match(pattern, desc)
            if match:
                return self._extract_sleep_entry(match, original_desc, confidence, unit)

        # Try water patterns
        for pattern, confidence, entry_type, unit in self.WATER_PATTERNS:
            match = re.match(pattern, desc)
            if match:
                return self._extract_water_entry(match, original_desc, confidence, unit)

        # Try steps patterns
        for pattern, confidence, entry_type, unit in self.STEPS_PATTERNS:
            match = re.match(pattern, desc)
            if match:
                return self._extract_steps_entry(match, original_desc, confidence, unit)

        # Fallback: unknown type
        raise ValueError(f"Could not parse wellness description: {original_desc}")

    def _extract_sleep_entry(self, match: re.Match, original_desc: str, confidence: float, unit: str) -> ParsedWellnessEntry:
        """Extract sleep entry from regex match."""
        groups = match.groups()

        if len(groups) >= 1:
            if len(groups) == 1:
                # Simple hours
                hours = float(groups[0])
            elif len(groups) == 2 and 'minutes' in original_desc.lower():
                # Hours and minutes
                hours = float(groups[0])
                minutes = float(groups[1])
                hours += minutes / 60
            else:
                # Sleep with quality
                hours = float(groups[0])
                # Quality is in second group but we don't use it here

            # Validate sleep hours
            if hours < 0 or hours > 24:
                raise ValueError(f"Sleep hours must be between 0-24, got {hours}")

            return ParsedWellnessEntry(
                entry_type="sleep",
                value=hours,
                unit=unit,
                description=original_desc,
                confidence=confidence
            )

        raise ValueError("Could not extract sleep value")

    def _extract_water_entry(self, match: re.Match, original_desc: str, confidence: float, unit: str) -> ParsedWellnessEntry:
        """Extract water entry from regex match."""
        groups = match.groups()

        if len(groups) >= 1:
            value = float(groups[0])

            # Convert to standardized unit (glasses)
            if unit in self.UNIT_CONVERSIONS['water']:
                conversion_factor = self.UNIT_CONVERSIONS['water'][unit]
                value *= conversion_factor

            # Validate water intake
            if value < 0 or value > 20:
                raise ValueError(f"Water intake must be between 0-20 glasses, got {value}")

            return ParsedWellnessEntry(
                entry_type="water",
                value=value,
                unit="glasses",
                description=original_desc,
                confidence=confidence
            )

        raise ValueError("Could not extract water value")

    def _extract_steps_entry(self, match: re.Match, original_desc: str, confidence: float, unit: str) -> ParsedWellnessEntry:
        """Extract steps entry from regex match."""
        groups = match.groups()

        if len(groups) >= 1:
            # Handle comma separators and 'k' suffix
            steps_str = groups[0].replace(',', '')
            if 'k' in steps_str.lower():
                steps_str = steps_str.lower().replace('k', '')
                steps = float(steps_str) * 1000
            else:
                steps = float(steps_str)

            # Validate step count
            if steps < 0 or steps > 100000:
                raise ValueError(f"Step count must be between 0-100,000, got {steps}")

            return ParsedWellnessEntry(
                entry_type="steps",
                value=steps,
                unit=unit,
                description=original_desc,
                confidence=confidence
            )

        raise ValueError("Could not extract steps value")

    def _aggregate_wellness_entries(self, entries: List[ParsedWellnessEntry]) -> Dict[str, Any]:
        """
        Aggregate wellness entries by type.

        Args:
            entries: List of parsed wellness entries

        Returns:
            Dict with aggregated values by type
        """
        aggregated = {
            "sleep_hours": None,
            "sleep_quality": None,  # Not parsed here, but structure for future
            "water_glasses": None,
            "steps_count": None
        }

        for entry in entries:
            if entry.entry_type == "sleep":
                if aggregated["sleep_hours"] is None:
                    aggregated["sleep_hours"] = entry.value
                else:
                    # If multiple sleep entries, take the highest confidence
                    existing_confidence = next((e.confidence for e in entries
                                              if e.entry_type == "sleep" and e.value == aggregated["sleep_hours"]), 0)
                    if entry.confidence > existing_confidence:
                        aggregated["sleep_hours"] = entry.value

            elif entry.entry_type == "water":
                if aggregated["water_glasses"] is None:
                    aggregated["water_glasses"] = entry.value
                else:
                    # Sum water intake if multiple entries
                    aggregated["water_glasses"] += entry.value

            elif entry.entry_type == "steps":
                if aggregated["steps_count"] is None:
                    aggregated["steps_count"] = entry.value
                else:
                    # If multiple step entries, take the highest confidence
                    existing_confidence = next((e.confidence for e in entries
                                              if e.entry_type == "steps" and e.value == aggregated["steps_count"]), 0)
                    if entry.confidence > existing_confidence:
                        aggregated["steps_count"] = entry.value

        return aggregated


# Create singleton instance
wellness_parser_tool = WellnessParserTool()


# Convenience function for direct use
async def parse_wellness_entries(
    wellness_descriptions: List[str],
    user_id: str,
    tool_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Parse a batch of wellness entries for tracking.

    This is the main API function that matches the contract specification.

    Args:
        wellness_descriptions: List of wellness metric descriptions (max 10 items)
        user_id: Telegram user ID for context
        tool_context: Optional ADK tool context

    Returns:
        Dict with status, data, and error fields
    """
    result = await wellness_parser_tool.execute(
        wellness_descriptions=wellness_descriptions,
        user_id=user_id,
        tool_context=tool_context
    )

    return {
        "status": "success" if result.success else "error",
        "data": result.data,
        "error": result.error
    }


__all__ = ['WellnessParserTool', 'wellness_parser_tool', 'parse_wellness_entries']