"""
Manual calorie entry tools for Weight Loss Chat Agent.

This module provides tools for manual calorie entry with validation,
confidence scoring, and nutritional estimation.
"""

import logging
import re
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


def parse_manual_calorie_entry(text: str) -> Dict[str, Any]:
    """
    Parse manual calorie entry from user text.

    Supports formats like:
    - "500 calories"
    - "ate 300 cal"
    - "consumed 250 kcal"
    - "manual entry 400 calories"

    Args:
        text: User input text

    Returns:
        Dict with parsed data or error
    """
    try:
        # Clean and normalize text
        text = text.lower().strip()

        # Patterns for calorie extraction
        calorie_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:cal|kcal|calories?|cals?)',  # "500 cal", "300 calories"
            r'ate\s+(\d+(?:\.\d+)?)\s*(?:cal|kcal|calories?|cals?)',  # "ate 300 cal"
            r'consumed\s+(\d+(?:\.\d+)?)\s*(?:cal|kcal|calories?|cals?)',  # "consumed 250 kcal"
            r'manual\s+(?:entry\s+)?(\d+(?:\.\d+)?)\s*(?:cal|kcal|calories?|cals?)',  # "manual 400 calories"
        ]

        calories = None
        for pattern in calorie_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                calories = float(match.group(1))
                break

        if calories is None:
            return {
                "status": "error",
                "error": "Could not parse calorie amount from text",
                "example": "Try: '500 calories' or 'ate 300 cal'"
            }

        # Validate calorie range (reasonable bounds)
        if calories < 0:
            return {
                "status": "error",
                "error": "Calorie amount cannot be negative"
            }

        if calories > 5000:
            return {
                "status": "warning",
                "message": f"High calorie entry: {calories} cal. Is this correct?",
                "calories": calories,
                "confidence": "low"
            }

        # Extract additional context
        meal_type = _extract_meal_type(text)
        food_description = _extract_food_description(text)

        # Calculate confidence score
        confidence = _calculate_entry_confidence(text, calories)

        return {
            "status": "success",
            "calories": calories,
            "meal_type": meal_type,
            "food_description": food_description,
            "confidence": confidence,
            "entry_type": "manual",
            "parsed_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to parse manual calorie entry: {e}")
        return {
            "status": "error",
            "error": f"Parsing failed: {str(e)}"
        }


def validate_manual_entry(calories: float, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Validate a manual calorie entry with contextual checks.

    Args:
        calories: Calorie amount to validate
        context: Optional context (user profile, recent entries, etc.)

    Returns:
        Validation result with confidence and warnings
    """
    try:
        warnings = []
        confidence = "high"

        # Basic range validation
        if calories <= 0:
            return {
                "valid": False,
                "error": "Calorie amount must be positive",
                "confidence": "invalid"
            }

        # Reasonable daily limits
        if calories > 3000:
            warnings.append("Very high calorie entry - please verify")
            confidence = "low"

        # Check against user profile if available
        if context and "user_profile" in context:
            profile = context["user_profile"]
            daily_goal = profile.get("daily_calorie_goal", 2000)

            if calories > daily_goal * 1.5:
                warnings.append(f"Entry exceeds 150% of daily goal ({daily_goal} cal)")
                confidence = "medium"

        # Check for suspicious patterns
        if context and "recent_entries" in context:
            recent = context["recent_entries"]
            if len(recent) >= 3:
                avg_recent = sum(entry.get("calories", 0) for entry in recent) / len(recent)
                if abs(calories - avg_recent) / avg_recent > 2.0:
                    warnings.append("Entry significantly different from recent average")
                    confidence = "medium"

        return {
            "valid": True,
            "confidence": confidence,
            "warnings": warnings,
            "recommendations": _generate_validation_recommendations(warnings, confidence)
        }

    except Exception as e:
        logger.error(f"Failed to validate manual entry: {e}")
        return {
            "valid": False,
            "error": f"Validation failed: {str(e)}",
            "confidence": "unknown"
        }


def estimate_nutrition_from_calories(calories: float, meal_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Estimate basic nutritional breakdown from calorie amount.

    This provides rough estimates for protein, carbs, fat based on typical meal compositions.

    Args:
        calories: Total calories
        meal_type: Type of meal (breakfast, lunch, dinner, snack)

    Returns:
        Estimated nutritional breakdown
    """
    try:
        # Base macronutrient ratios (can be adjusted based on meal type)
        if meal_type == "breakfast":
            # Higher carb breakfast
            carb_ratio = 0.5
            protein_ratio = 0.2
            fat_ratio = 0.3
        elif meal_type == "lunch" or meal_type == "dinner":
            # Balanced main meal
            carb_ratio = 0.4
            protein_ratio = 0.3
            fat_ratio = 0.3
        elif meal_type == "snack":
            # Higher fat/protein snack
            carb_ratio = 0.3
            protein_ratio = 0.3
            fat_ratio = 0.4
        else:
            # Default balanced
            carb_ratio = 0.4
            protein_ratio = 0.25
            fat_ratio = 0.35

        # Calculate grams (4 cal/g for carbs/protein, 9 cal/g for fat)
        carb_cal = calories * carb_ratio
        protein_cal = calories * protein_ratio
        fat_cal = calories * fat_ratio

        carbs_g = carb_cal / 4
        protein_g = protein_cal / 4
        fat_g = fat_cal / 9

        return {
            "estimated_carbs_g": round(carbs_g, 1),
            "estimated_protein_g": round(protein_g, 1),
            "estimated_fat_g": round(fat_g, 1),
            "estimation_method": "calorie-based",
            "confidence": "low",
            "note": "These are rough estimates. For accurate nutrition, use food logging instead."
        }

    except Exception as e:
        logger.error(f"Failed to estimate nutrition: {e}")
        return {
            "error": f"Estimation failed: {str(e)}"
        }


def _extract_meal_type(text: str) -> Optional[str]:
    """Extract meal type from text."""
    meal_keywords = {
        "breakfast": ["breakfast", "morning", "bfast"],
        "lunch": ["lunch", "midday", "noon"],
        "dinner": ["dinner", "supper", "evening"],
        "snack": ["snack", "treat", "bite"]
    }

    text_lower = text.lower()
    for meal_type, keywords in meal_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            return meal_type

    return None


def _extract_food_description(text: str) -> Optional[str]:
    """Extract food description from manual entry text."""
    # Remove calorie-related words and extract remaining description
    clean_text = re.sub(r'\d+(?:\.\d+)?\s*(?:cal|kcal|calories?|cals?)', '', text, flags=re.IGNORECASE)
    clean_text = re.sub(r'(?:ate|consumed|manual\s+(?:entry\s+)?)', '', clean_text, flags=re.IGNORECASE)
    clean_text = clean_text.strip()

    # Return description if it's meaningful length
    if len(clean_text) > 3 and len(clean_text) < 100:
        return clean_text

    return None


def _calculate_entry_confidence(text: str, calories: float) -> str:
    """Calculate confidence level for manual entry."""
    confidence_score = 0

    # Explicit calorie mention
    if re.search(r'\b\d+(?:\.\d+)?\s*(?:cal|kcal|calories?|cals?)\b', text, re.IGNORECASE):
        confidence_score += 2

    # Manual entry keywords
    if re.search(r'\b(manual|entry|exact|precise)\b', text, re.IGNORECASE):
        confidence_score += 1

    # Reasonable calorie range
    if 50 <= calories <= 2000:
        confidence_score += 1
    elif 2000 < calories <= 3000:
        confidence_score += 0.5

    # Has food description
    if _extract_food_description(text):
        confidence_score += 0.5

    # Has meal type
    if _extract_meal_type(text):
        confidence_score += 0.5

    # Determine confidence level
    if confidence_score >= 3:
        return "high"
    elif confidence_score >= 2:
        return "medium"
    else:
        return "low"


def _generate_validation_recommendations(warnings: list, confidence: str) -> list:
    """Generate recommendations based on validation results."""
    recommendations = []

    if confidence == "low":
        recommendations.append("Consider using food logging for more accurate nutrition data")
        recommendations.append("Double-check your calorie calculation")

    if any("daily goal" in w for w in warnings):
        recommendations.append("This entry is much higher than your daily goal - please verify")

    if any("recent average" in w for w in warnings):
        recommendations.append("This differs significantly from your recent entries - is this accurate?")

    return recommendations


# Convenience functions for agent integration
def process_manual_calorie_entry(text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Complete processing pipeline for manual calorie entry.

    Args:
        text: User input text
        context: Optional context for validation

    Returns:
        Complete processing result
    """
    # Parse the entry
    parsed = parse_manual_calorie_entry(text)
    if parsed["status"] != "success":
        return parsed

    # Validate the entry
    validation = validate_manual_entry(parsed["calories"], context)

    # Add validation results
    parsed.update({
        "validation": validation,
        "overall_confidence": min(parsed["confidence"], validation.get("confidence", "low"),
                                key=lambda x: {"high": 3, "medium": 2, "low": 1}.get(x, 0))
    })

    # Add nutritional estimates
    estimates = estimate_nutrition_from_calories(
        parsed["calories"],
        parsed.get("meal_type")
    )
    parsed["estimates"] = estimates

    return parsed