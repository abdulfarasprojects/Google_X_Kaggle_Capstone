"""
Nutrition reference data for approximate calculations.

This module contains static reference data for nutrition calculations,
including approximate nutritional values for common foods. Used as
fallback when we# Create singleton instance
nutrition_reference = NutritionReferenceData()

__all__ = ['NutritionReferenceData', 'nutrition_reference']rch is unavailable or for faster calculations.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class NutritionReferenceData:
    """
    Static reference data for nutrition calculations.

    Contains approximate nutritional information for common foods
    organized by category for easy lookup and calculation.
    """

    # Approximate nutrition data for common foods (per serving)
    FOOD_NUTRITION_DB = {
        # Breakfast Items
        'tuna sandwich': {'calories': 350, 'protein': 25, 'carbs': 30, 'fat': 12, 'serving': '1 sandwich'},
        'eggs': {'calories': 70, 'protein': 6, 'carbs': 0.5, 'fat': 5, 'serving': '1 large'},
        'toast': {'calories': 80, 'protein': 3, 'carbs': 15, 'fat': 1, 'serving': '1 slice'},
        'oatmeal': {'calories': 150, 'protein': 5, 'carbs': 27, 'fat': 2.5, 'serving': '1/2 cup dry'},
        'cereal': {'calories': 120, 'protein': 3, 'carbs': 24, 'fat': 1, 'serving': '1 cup'},
        'pancakes': {'calories': 227, 'protein': 6, 'carbs': 35, 'fat': 6, 'serving': '2 medium'},
        'waffles': {'calories': 218, 'protein': 6, 'carbs': 31, 'fat': 7, 'serving': '1 large'},
        'bacon': {'calories': 43, 'protein': 3, 'carbs': 0.1, 'fat': 3.3, 'serving': '1 slice'},
        'sausage': {'calories': 85, 'protein': 5, 'carbs': 0.5, 'fat': 7, 'serving': '1 link'},
        'bagel': {'calories': 250, 'protein': 9, 'carbs': 48, 'fat': 2, 'serving': '1 medium'},
        'muffin': {'calories': 340, 'protein': 6, 'carbs': 45, 'fat': 15, 'serving': '1 large'},
        'croissant': {'calories': 231, 'protein': 5, 'carbs': 26, 'fat': 12, 'serving': '1 medium'},
        'cinnamon roll': {'calories': 223, 'protein': 4, 'carbs': 32, 'fat': 9, 'serving': '1 medium'},

        # Fruits
        'apple': {'calories': 95, 'protein': 0.5, 'carbs': 25, 'fat': 0.3, 'serving': '1 medium'},
        'banana': {'calories': 105, 'protein': 1.3, 'carbs': 27, 'fat': 0.4, 'serving': '1 medium'},
        'orange': {'calories': 62, 'protein': 1.2, 'carbs': 15, 'fat': 0.2, 'serving': '1 medium'},
        'grapes': {'calories': 62, 'protein': 0.6, 'carbs': 16, 'fat': 0.3, 'serving': '1 cup'},
        'strawberries': {'calories': 49, 'protein': 1, 'carbs': 12, 'fat': 0.5, 'serving': '1 cup'},
        'blueberries': {'calories': 84, 'protein': 1.1, 'carbs': 21, 'fat': 0.5, 'serving': '1 cup'},
        'pineapple': {'calories': 82, 'protein': 1, 'carbs': 22, 'fat': 0.2, 'serving': '1 cup'},
        'watermelon': {'calories': 30, 'protein': 0.6, 'carbs': 8, 'fat': 0.2, 'serving': '1 cup'},
        'peach': {'calories': 59, 'protein': 1.4, 'carbs': 14, 'fat': 0.4, 'serving': '1 medium'},
        'pear': {'calories': 101, 'protein': 0.7, 'carbs': 27, 'fat': 0.2, 'serving': '1 medium'},

        # Vegetables
        'broccoli': {'calories': 55, 'protein': 3.7, 'carbs': 11, 'fat': 0.6, 'serving': '1 cup'},
        'carrots': {'calories': 25, 'protein': 0.6, 'carbs': 6, 'fat': 0.1, 'serving': '1 medium'},
        'potatoes': {'calories': 77, 'protein': 2, 'carbs': 17, 'fat': 0.1, 'serving': '1 medium'},
        'sweet potato': {'calories': 112, 'protein': 2, 'carbs': 26, 'fat': 0.1, 'serving': '1 medium'},
        'spinach': {'calories': 7, 'protein': 0.9, 'carbs': 1.1, 'fat': 0.1, 'serving': '1 cup'},
        'lettuce': {'calories': 5, 'protein': 0.5, 'carbs': 1, 'fat': 0.1, 'serving': '1 cup'},
        'tomatoes': {'calories': 22, 'protein': 1.1, 'carbs': 5, 'fat': 0.2, 'serving': '1 medium'},
        'cucumber': {'calories': 16, 'protein': 0.7, 'carbs': 3.6, 'fat': 0.1, 'serving': '1 medium'},
        'bell pepper': {'calories': 24, 'protein': 1, 'carbs': 6, 'fat': 0.3, 'serving': '1 medium'},
        'onion': {'calories': 44, 'protein': 1.2, 'carbs': 10, 'fat': 0.1, 'serving': '1 medium'},
        'garlic': {'calories': 4, 'protein': 0.2, 'carbs': 1, 'fat': 0, 'serving': '1 clove'},
        'zucchini': {'calories': 33, 'protein': 2.4, 'carbs': 6, 'fat': 0.6, 'serving': '1 cup'},
        'mushrooms': {'calories': 22, 'protein': 3.1, 'carbs': 3.3, 'fat': 0.3, 'serving': '1 cup'},
        'avocado': {'calories': 234, 'protein': 2.9, 'carbs': 12, 'fat': 21, 'serving': '1/2 medium'},

        # Proteins
        'chicken breast': {'calories': 165, 'protein': 31, 'carbs': 0, 'fat': 3.6, 'serving': '100g'},
        'chicken thigh': {'calories': 209, 'protein': 26, 'carbs': 0, 'fat': 10, 'serving': '100g'},
        'ground beef': {'calories': 152, 'protein': 20, 'carbs': 0, 'fat': 8, 'serving': '100g'},
        'steak': {'calories': 250, 'protein': 26, 'carbs': 0, 'fat': 15, 'serving': '100g'},
        'pork chop': {'calories': 231, 'protein': 29, 'carbs': 0, 'fat': 11, 'serving': '100g'},
        'salmon': {'calories': 206, 'protein': 22, 'carbs': 0, 'fat': 12, 'serving': '100g'},
        'tuna': {'calories': 144, 'protein': 25, 'carbs': 0, 'fat': 4.9, 'serving': '100g'},
        'shrimp': {'calories': 99, 'protein': 24, 'carbs': 0.3, 'fat': 0.3, 'serving': '100g'},
        'turkey': {'calories': 135, 'protein': 30, 'carbs': 0, 'fat': 1, 'serving': '100g'},
        'tofu': {'calories': 76, 'protein': 8, 'carbs': 2, 'fat': 4.8, 'serving': '100g'},
        'lentils': {'calories': 116, 'protein': 9, 'carbs': 20, 'fat': 0.4, 'serving': '1/2 cup'},
        'black beans': {'calories': 132, 'protein': 9, 'carbs': 24, 'fat': 0.5, 'serving': '1/2 cup'},
        'chickpeas': {'calories': 143, 'protein': 7.5, 'carbs': 25, 'fat': 2.6, 'serving': '1/2 cup'},
        'peanut butter': {'calories': 190, 'protein': 7, 'carbs': 6, 'fat': 16, 'serving': '2 tbsp'},
        'peanuts': {'calories': 567, 'protein': 26, 'carbs': 16, 'fat': 49, 'serving': '100g'},
        'almonds': {'calories': 164, 'protein': 6, 'carbs': 6, 'fat': 14, 'serving': '1 oz'},
        'walnuts': {'calories': 185, 'protein': 4, 'carbs': 4, 'fat': 18, 'serving': '1 oz'},
        'cashews': {'calories': 157, 'protein': 5, 'carbs': 9, 'fat': 12, 'serving': '1 oz'},

        # Dairy
        'milk': {'calories': 103, 'protein': 8, 'carbs': 12, 'fat': 2.4, 'serving': '1 cup'},
        'cheese': {'calories': 113, 'protein': 7, 'carbs': 1, 'fat': 9, 'serving': '1 oz'},
        'yogurt': {'calories': 150, 'protein': 12, 'carbs': 12, 'fat': 5, 'serving': '1 cup'},
        'cottage cheese': {'calories': 163, 'protein': 28, 'carbs': 6, 'fat': 2.3, 'serving': '1 cup'},
        'ice cream': {'calories': 137, 'protein': 2.3, 'carbs': 16, 'fat': 7.3, 'serving': '1/2 cup'},
        'butter': {'calories': 102, 'protein': 0.1, 'carbs': 0, 'fat': 11.5, 'serving': '1 tbsp'},

        # Grains & Carbs
        'rice': {'calories': 130, 'protein': 2.7, 'carbs': 28, 'fat': 0.3, 'serving': '1/2 cup cooked'},
        'pasta': {'calories': 157, 'protein': 6, 'carbs': 31, 'fat': 0.9, 'serving': '1 cup cooked'},
        'bread': {'calories': 79, 'protein': 3, 'carbs': 15, 'fat': 1, 'serving': '1 slice'},
        'quinoa': {'calories': 111, 'protein': 4, 'carbs': 20, 'fat': 1.9, 'serving': '1/2 cup cooked'},
        'brown rice': {'calories': 109, 'protein': 2.6, 'carbs': 23, 'fat': 0.9, 'serving': '1/2 cup cooked'},
        'potato chips': {'calories': 152, 'protein': 2, 'carbs': 15, 'fat': 10, 'serving': '1 oz'},
        'pretzels': {'calories': 108, 'protein': 3, 'carbs': 22, 'fat': 1, 'serving': '1 oz'},

        # Fast Food & Prepared Meals
        'hamburger': {'calories': 354, 'protein': 20, 'carbs': 29, 'fat': 17, 'serving': '1 medium'},
        'cheeseburger': {'calories': 535, 'protein': 27, 'carbs': 31, 'fat': 29, 'serving': '1 medium'},
        'french fries': {'calories': 365, 'protein': 4, 'carbs': 46, 'fat': 17, 'serving': 'medium'},
        'pizza': {'calories': 285, 'protein': 12, 'carbs': 36, 'fat': 10, 'serving': '1 slice'},
        'taco': {'calories': 156, 'protein': 9, 'carbs': 13, 'fat': 7, 'serving': '1 medium'},
        'burrito': {'calories': 340, 'protein': 14, 'carbs': 45, 'fat': 12, 'serving': '1 medium'},
        'sandwich': {'calories': 250, 'protein': 15, 'carbs': 30, 'fat': 8, 'serving': '1 medium'},

        # Snacks & Sweets
        'chocolate bar': {'calories': 235, 'protein': 3, 'carbs': 27, 'fat': 13, 'serving': '1.5 oz'},
        'cookies': {'calories': 53, 'protein': 1, 'carbs': 7, 'fat': 2.5, 'serving': '1 medium'},
        'cake': {'calories': 257, 'protein': 3, 'carbs': 37, 'fat': 11, 'serving': '1 slice'},
        'pie': {'calories': 323, 'protein': 4, 'carbs': 44, 'fat': 15, 'serving': '1 slice'},
        'candy': {'calories': 103, 'protein': 0, 'carbs': 27, 'fat': 0, 'serving': '1.5 oz'},
        'popcorn': {'calories': 31, 'protein': 1, 'carbs': 6, 'fat': 0.4, 'serving': '1 cup'},
        'trail mix': {'calories': 175, 'protein': 5, 'carbs': 16, 'fat': 12, 'serving': '1/4 cup'},

        # Beverages
        'soda can': {'calories': 140, 'protein': 0, 'carbs': 39, 'fat': 0, 'serving': '1 can'},
        'coffee': {'calories': 2, 'protein': 0.1, 'carbs': 0, 'fat': 0, 'serving': '1 cup'},
        'tea': {'calories': 2, 'protein': 0, 'carbs': 0.4, 'fat': 0, 'serving': '1 cup'},
        'orange juice': {'calories': 112, 'protein': 2, 'carbs': 26, 'fat': 0.5, 'serving': '1 cup'},
        'apple juice': {'calories': 114, 'protein': 0.2, 'carbs': 28, 'fat': 0.3, 'serving': '1 cup'},
        'beer': {'calories': 153, 'protein': 1.6, 'carbs': 12.6, 'fat': 0, 'serving': '12 oz'},
        'wine': {'calories': 125, 'protein': 0.1, 'carbs': 3.8, 'fat': 0, 'serving': '5 oz'},
        'protein shake': {'calories': 120, 'protein': 25, 'carbs': 3, 'fat': 1, 'serving': '1 scoop'},
        'smoothie': {'calories': 200, 'protein': 10, 'carbs': 35, 'fat': 3, 'serving': '1 medium'},

        # Salads & Mixed Dishes
        'salad': {'calories': 50, 'protein': 2, 'carbs': 10, 'fat': 0.5, 'serving': '1 cup'},
        'caesar salad': {'calories': 184, 'protein': 7, 'carbs': 10, 'fat': 14, 'serving': '1 medium'},
        'pasta salad': {'calories': 157, 'protein': 5, 'carbs': 25, 'fat': 5, 'serving': '1 cup'},
        'soup': {'calories': 70, 'protein': 3, 'carbs': 10, 'fat': 2, 'serving': '1 cup'},
        'stir fry': {'calories': 150, 'protein': 15, 'carbs': 15, 'fat': 6, 'serving': '1 cup'},
        'curry': {'calories': 200, 'protein': 12, 'carbs': 20, 'fat': 8, 'serving': '1 cup'},

        # Miscellaneous
        'hummus': {'calories': 166, 'protein': 8, 'carbs': 14, 'fat': 10, 'serving': '1/2 cup'},
        'guacamole': {'calories': 160, 'protein': 2, 'carbs': 9, 'fat': 15, 'serving': '1/2 cup'},
        'salsa': {'calories': 20, 'protein': 1, 'carbs': 4, 'fat': 0.2, 'serving': '1/4 cup'},
        'olive oil': {'calories': 119, 'protein': 0, 'carbs': 0, 'fat': 13.5, 'serving': '1 tbsp'},
        'honey': {'calories': 64, 'protein': 0.1, 'carbs': 17, 'fat': 0, 'serving': '1 tbsp'},
        'sugar': {'calories': 49, 'protein': 0, 'carbs': 13, 'fat': 0, 'serving': '1 tbsp'},
        'salt': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'serving': '1 tsp'},
    }

    @staticmethod
    def get_food_nutrition(food_name: str) -> Optional[Dict[str, Any]]:
        """
        Get nutrition data for a food item.

        Args:
            food_name: Name of the food to look up

        Returns:
            Dict with nutrition data or None if not found
        """
        food_key = food_name.lower().strip()

        # Direct lookup
        if food_key in NutritionReferenceData.FOOD_NUTRITION_DB:
            return NutritionReferenceData.FOOD_NUTRITION_DB[food_key].copy()

        # Fuzzy matching - check if food_name contains any known food
        for db_food, data in NutritionReferenceData.FOOD_NUTRITION_DB.items():
            if db_food in food_key or food_key in db_food:
                logger.info(f"Found approximate match: '{food_key}' -> '{db_food}'")
                return data.copy()

        return None

    @staticmethod
    def calculate_nutrition_from_reference(
        food_name: str,
        quantity: float = 1.0,
        unit: str = "serving"
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate nutrition for a food item using reference data.

        Args:
            food_name: Name of the food
            quantity: Quantity consumed
            unit: Unit of measurement

        Returns:
            Dict with calculated nutrition or None if food not found
        """
        nutrition_data = NutritionReferenceData.get_food_nutrition(food_name)
        if not nutrition_data:
            return None

        # For now, assume quantity refers to servings
        # In a more sophisticated implementation, we'd handle unit conversions
        scale_factor = quantity

        return {
            'food_name': food_name,
            'calories': round(nutrition_data['calories'] * scale_factor, 1),
            'protein_g': round(nutrition_data['protein'] * scale_factor, 1),
            'carbs_g': round(nutrition_data['carbs'] * scale_factor, 1),
            'fat_g': round(nutrition_data['fat'] * scale_factor, 1),
            'serving_size': nutrition_data['serving'],
            'quantity_used': quantity,
            'source': 'reference_db',
            'confidence': 0.7  # Lower confidence than web search
        }


# Create singleton instance
nutrition_reference = NutritionReferenceData()

__all__ = ['NutritionReferenceData', 'nutrition_reference']