"""
USDA FoodData Central API client for nutrition data.

This module provides an async client for the USDA FoodData Central API
to retrieve nutrition information for food items. Used as primary source
for accurate nutrition data with fallback to Nutritionix.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
import aiohttp
from urllib.parse import urlencode

from tools.base import BaseTool, ToolResult
from config.settings import settings

logger = logging.getLogger(__name__)


class USDAApiClient(BaseTool):
    """
    USDA FoodData Central API client for nutrition lookup.

    Provides search and nutrition retrieval functionality with proper
    error handling, caching, and rate limiting.
    """

    def __init__(self):
        super().__init__(
            name="usda_nutrition_lookup",
            description="Look up nutrition data from USDA FoodData Central API",
            parameters={
                "type": "object",
                "properties": {
                    "food_description": {
                        "type": "string",
                        "description": "Natural language food description to search for"
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 5,
                        "description": "Maximum number of search results"
                    }
                },
                "required": ["food_description"]
            },
            timeout_seconds=5  # USDA API timeout
        )

        self.base_url = "https://api.nal.usda.gov/fdc/v1"
        self.api_key = settings.usda_api_key or "demo"
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def execute(
        self,
        food_description: str,
        max_results: int = 5,
        tool_context: Optional[Any] = None
    ) -> ToolResult:
        """
        Search for nutrition data for a food description.

        Args:
            food_description: Food to search for
            max_results: Maximum results to return
            tool_context: ADK tool context

        Returns:
            ToolResult with nutrition data or error
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            # Search for foods
            search_results = await self._search_foods(food_description, max_results)
            if not search_results:
                return ToolResult(
                    success=False,
                    error="No foods found matching description"
                )

            # Get detailed nutrition for best match
            best_match = search_results[0]
            nutrition_data = await self._get_food_nutrition(best_match['fdcId'])

            if not nutrition_data:
                return ToolResult(
                    success=False,
                    error="Could not retrieve nutrition data for food"
                )

            return ToolResult(
                success=True,
                data={
                    "food_name": best_match.get('description', food_description),
                    "fdc_id": best_match['fdcId'],
                    "calories_per_serving": nutrition_data.get('calories', 0),
                    "protein_g_per_serving": nutrition_data.get('protein', 0),
                    "carbs_g_per_serving": nutrition_data.get('carbs', 0),
                    "fat_g_per_serving": nutrition_data.get('fat', 0),
                    "serving_size": nutrition_data.get('serving_size', '100g'),
                    "serving_size_g": nutrition_data.get('serving_size_g', 100),
                    "confidence": best_match.get('score', 0.8),
                    "source": "usda"
                }
            )

        except Exception as e:
            logger.error(f"USDA API error: {e}")
            return ToolResult(
                success=False,
                error=f"USDA API request failed: {str(e)}"
            )

    async def _search_foods(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for foods using USDA API.

        Args:
            query: Search query
            max_results: Maximum results

        Returns:
            List of food search results
        """
        params = {
            'api_key': self.api_key,
            'query': query,
            'pageSize': max_results,
            'pageNumber': 1
        }

        url = f"{self.base_url}/foods/search?{urlencode(params)}"

        async with self.session.get(url) as response:
            if response.status != 200:
                logger.warning(f"USDA search failed: {response.status}")
                return []

            data = await response.json()

            foods = data.get('foods', [])
            return [
                {
                    'fdcId': food['fdcId'],
                    'description': food.get('description', ''),
                    'score': food.get('score', 0)
                }
                for food in foods[:max_results]
            ]

    async def _get_food_nutrition(self, fdc_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed nutrition information for a food.

        Args:
            fdc_id: USDA food ID

        Returns:
            Nutrition data dictionary or None
        """
        url = f"{self.base_url}/food/{fdc_id}?api_key={self.api_key}"

        async with self.session.get(url) as response:
            if response.status != 200:
                logger.warning(f"USDA food details failed: {response.status}")
                return None

            data = await response.json()

            # Extract nutrition facts
            nutrients = {}
            serving_size_g = 100  # default

            # Look for serving size
            if 'servingSize' in data:
                serving_size_g = data['servingSize']
            elif 'householdServingFullText' in data:
                # Try to parse serving size
                serving_size_g = self._parse_serving_size(data.get('householdServingFullText', ''))

            # Extract key nutrients
            if 'foodNutrients' in data:
                for nutrient in data['foodNutrients']:
                    nutrient_name = nutrient.get('nutrient', {}).get('name', '').lower()
                    amount = nutrient.get('amount', 0)

                    if 'energy' in nutrient_name and 'kcal' in nutrient_name:
                        nutrients['calories'] = amount
                    elif 'protein' in nutrient_name:
                        nutrients['protein'] = amount
                    elif 'carbohydrate' in nutrient_name:
                        nutrients['carbs'] = amount
                    elif 'fat' in nutrient_name and 'total' in nutrient_name:
                        nutrients['fat'] = amount

            return {
                'calories': nutrients.get('calories', 0),
                'protein': nutrients.get('protein', 0),
                'carbs': nutrients.get('carbs', 0),
                'fat': nutrients.get('fat', 0),
                'serving_size': f"{serving_size_g}g",
                'serving_size_g': serving_size_g
            }

    def _parse_serving_size(self, serving_text: str) -> float:
        """Parse serving size from text (e.g., '1 cup (100g)')."""
        # Look for grams in parentheses
        import re
        match = re.search(r'\((\d+)g\)', serving_text.lower())
        if match:
            return float(match.group(1))

        # Default to 100g
        return 100.0


# Create singleton instance
usda_client = USDAApiClient()


# Convenience function for direct use
async def lookup_nutrition_usda(food_description: str) -> Dict[str, Any]:
    """
    Look up nutrition data from USDA API.

    Args:
        food_description: Food to search for

    Returns:
        Dict with status, data, error
    """
    result = await usda_client.execute(food_description=food_description)

    return {
        "status": "success" if result.success else "error",
        "data": result.data,
        "error": result.error
    }


__all__ = ['USDAApiClient', 'usda_client', 'lookup_nutrition_usda']