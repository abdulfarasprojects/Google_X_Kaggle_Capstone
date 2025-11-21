"""
Meal logging database manager.

This module provides database operations for meal logging, including
creation, retrieval, updates, and analytics for nutrition data.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
import json
from sqlalchemy.orm import Session

from database.init import get_db_session
from database.models import MealLog, UserProfile

# Observability imports
from observability.tracing import traced
from observability.metrics import record_request, record_response_time, record_error

logger = logging.getLogger(__name__)


class MealManager:
    """
    Database manager for meal logging operations.

    Provides CRUD operations and analytics for meal logs.
    """

    @staticmethod
    @traced("create_meal_log")
    def create_meal_log(
        user_id: str,
        meal_type: str,
        food_items: List[Dict[str, Any]],
        total_calories: float,
        total_protein_g: float,
        confidence_score: float,
        log_date: Optional[date] = None
    ) -> Optional[str]:
        """
        Create a new meal log entry.

        Args:
            user_id: User identifier
            meal_type: Type of meal
            food_items: List of food item dictionaries
            total_calories: Total calories for the meal
            total_protein_g: Total protein in grams
            confidence_score: Confidence in the nutrition data
            log_date: Date of the meal (defaults to today)

        Returns:
            Log ID if successful, None if failed
        """
        try:
            with get_db_session() as session:
                # Validate user exists
                user = session.query(UserProfile).filter_by(user_id=user_id).first()
                if not user:
                    logger.error(f"User not found: {user_id}")
                    return None

                # Use provided date or today
                meal_date = log_date or date.today()

                # Generate unique log ID
                log_id = f"{user_id}_{datetime.utcnow().timestamp()}"

                # Create meal log
                meal_log = MealLog(
                    log_id=log_id,
                    user_id=user_id,
                    meal_type=meal_type,
                    food_items=json.dumps(food_items),  # Convert to JSON string
                    total_calories=total_calories,
                    total_protein_g=total_protein_g,
                    confidence_score=confidence_score,
                    log_date=meal_date
                )

                session.add(meal_log)
                session.commit()

                logger.info(f"Created meal log: {log_id}")
                return log_id

        except Exception as e:
            logger.error(f"Failed to create meal log: {e}")
            return None

    @staticmethod
    def get_meal_logs(
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        meal_type: Optional[str] = None,
        limit: int = 50
    ) -> List[MealLog]:
        """
        Retrieve meal logs for a user.

        Args:
            user_id: User identifier
            start_date: Start date filter
            end_date: End date filter
            meal_type: Meal type filter
            limit: Maximum number of results

        Returns:
            List of MealLog objects
        """
        try:
            with get_db_session() as session:
                query = session.query(MealLog).filter_by(user_id=user_id)

                if start_date:
                    query = query.filter(MealLog.log_date >= start_date)
                if end_date:
                    query = query.filter(MealLog.log_date <= end_date)
                if meal_type:
                    query = query.filter(MealLog.meal_type == meal_type)

                return query.order_by(MealLog.log_date.desc(), MealLog.created_at.desc()).limit(limit).all()

        except Exception as e:
            logger.error(f"Failed to retrieve meal logs: {e}")
            return []

    @staticmethod
    @traced("get_daily_nutrition_summary")
    def get_daily_nutrition_summary(user_id: str, target_date: date) -> Dict[str, Any]:
        """
        Get nutrition summary for a specific day.

        Args:
            user_id: User identifier
            target_date: Date to summarize

        Returns:
            Dictionary with daily nutrition totals
        """
        try:
            with get_db_session() as session:
                meals = session.query(MealLog).filter_by(
                    user_id=user_id,
                    log_date=target_date
                ).all()

                summary = {
                    "date": target_date.isoformat(),
                    "total_calories": 0.0,
                    "total_protein_g": 0.0,
                    "meals_logged": len(meals),
                    "meals": []
                }

                for meal in meals:
                    summary["total_calories"] += meal.total_calories
                    summary["total_protein_g"] += meal.total_protein_g
                    summary["meals"].append({
                        "log_id": meal.log_id,
                        "meal_type": meal.meal_type,
                        "calories": meal.total_calories,
                        "protein_g": meal.total_protein_g,
                        "confidence": meal.confidence_score,
                        "created_at": meal.created_at.isoformat()
                    })

                return summary

        except Exception as e:
            logger.error(f"Failed to get daily nutrition summary: {e}")
            return {
                "date": target_date.isoformat(),
                "total_calories": 0.0,
                "total_protein_g": 0.0,
                "meals_logged": 0,
                "meals": []
            }

    @staticmethod
    @traced("get_nutrition_analytics")
    def get_nutrition_analytics(
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get nutrition analytics for recent period.

        Args:
            user_id: User identifier
            days: Number of days to analyze

        Returns:
            Analytics dictionary
        """
        try:
            with get_db_session() as session:
                # Calculate date range
                end_date = date.today()
                start_date = end_date - timedelta(days=days-1)

                # Get all meals in period
                meals = session.query(MealLog).filter(
                    MealLog.user_id == user_id,
                    MealLog.log_date >= start_date,
                    MealLog.log_date <= end_date
                ).all()

                if not meals:
                    return {
                        "period_days": days,
                        "total_meals": 0,
                        "avg_daily_calories": 0.0,
                        "avg_daily_protein": 0.0,
                        "meal_types_breakdown": {}
                    }

                # Calculate totals
                total_calories = sum(meal.total_calories for meal in meals)
                total_protein = sum(meal.total_protein_g for meal in meals)
                total_meals = len(meals)

                # Meal type breakdown
                meal_types = {}
                for meal in meals:
                    meal_type = meal.meal_type
                    if meal_type not in meal_types:
                        meal_types[meal_type] = {"count": 0, "calories": 0.0, "protein": 0.0}
                    meal_types[meal_type]["count"] += 1
                    meal_types[meal_type]["calories"] += meal.total_calories
                    meal_types[meal_type]["protein"] += meal.total_protein_g

                return {
                    "period_days": days,
                    "total_meals": total_meals,
                    "avg_daily_calories": round(total_calories / days, 1),
                    "avg_daily_protein": round(total_protein / days, 1),
                    "meal_types_breakdown": meal_types
                }

        except Exception as e:
            logger.error(f"Failed to get nutrition analytics: {e}")
            return {
                "period_days": days,
                "total_meals": 0,
                "avg_daily_calories": 0.0,
                "avg_daily_protein": 0.0,
                "meal_types_breakdown": {}
            }

    @staticmethod
    def update_meal_log(
        log_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update an existing meal log.

        Args:
            log_id: Meal log identifier
            updates: Fields to update

        Returns:
            True if successful, False otherwise
        """
        try:
            with get_db_session() as session:
                meal = session.query(MealLog).filter_by(log_id=log_id).first()
                if not meal:
                    logger.error(f"Meal log not found: {log_id}")
                    return False

                # Update allowed fields
                allowed_fields = [
                    'meal_type', 'food_items', 'total_calories',
                    'total_protein_g', 'confidence_score', 'log_date'
                ]

                for field, value in updates.items():
                    if field in allowed_fields:
                        setattr(meal, field, value)

                meal.updated_at = datetime.utcnow()
                session.commit()

                logger.info(f"Updated meal log: {log_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to update meal log: {e}")
            return False

    @staticmethod
    def create_manual_calorie_entry(
        user_id: str,
        calories: float,
        meal_type: Optional[str] = None,
        food_description: Optional[str] = None,
        confidence_level: str = "medium",
        validation_warnings: Optional[List[str]] = None,
        log_date: Optional[date] = None
    ) -> Optional[str]:
        """
        Create a manual calorie entry with confidence flagging.

        Args:
            user_id: User identifier
            calories: Calorie amount
            meal_type: Type of meal (optional)
            food_description: Description of food consumed
            confidence_level: Confidence level ('high', 'medium', 'low')
            validation_warnings: List of validation warnings
            log_date: Date of the entry (defaults to today)

        Returns:
            Log ID if successful, None if failed
        """
        try:
            with get_db_session() as session:
                # Validate user exists
                user = session.query(UserProfile).filter_by(user_id=user_id).first()
                if not user:
                    logger.error(f"User not found: {user_id}")
                    return None

                # Use provided date or today
                entry_date = log_date or date.today()

                # Generate unique log ID
                log_id = f"manual_{user_id}_{datetime.utcnow().timestamp()}"

                # Convert confidence level to numeric score
                confidence_scores = {"high": 0.9, "medium": 0.7, "low": 0.5}
                confidence_score = confidence_scores.get(confidence_level, 0.7)

                # Create food item for manual entry
                food_item = {
                    "name": food_description or "Manual calorie entry",
                    "calories": calories,
                    "confidence": confidence_level,
                    "warnings": validation_warnings or [],
                    "entry_type": "manual"
                }

                # Estimate basic nutrition (rough estimates)
                estimated_protein_g = calories * 0.25 / 4  # Assume 25% of calories from protein

                # Create meal log with manual entry flag
                meal_log = MealLog(
                    log_id=log_id,
                    user_id=user_id,
                    meal_type=meal_type or "manual_entry",
                    total_calories=calories,
                    total_protein_g=estimated_protein_g,
                    confidence_score=confidence_score,
                    log_date=entry_date
                )
                # Set food items using the property setter
                meal_log.food_items_list = [food_item]

                session.add(meal_log)
                session.commit()

                logger.info(f"Created manual calorie entry: {log_id} ({calories} cal, confidence: {confidence_level})")
                return log_id

        except Exception as e:
            logger.error(f"Failed to create manual calorie entry: {e}")
            return None
    def get_manual_entries_with_confidence(
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        min_confidence: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Get manual entries with confidence information.

        Args:
            user_id: User identifier
            start_date: Start date filter
            end_date: End date filter
            min_confidence: Minimum confidence score filter

        Returns:
            List of manual entries with confidence data
        """
        try:
            with get_db_session() as session:
                query = session.query(MealLog).filter_by(user_id=user_id)

                # Filter for manual entries (meal_type contains 'manual' or check food_items)
                query = query.filter(MealLog.meal_type.like('%manual%'))

                if start_date:
                    query = query.filter(MealLog.log_date >= start_date)
                if end_date:
                    query = query.filter(MealLog.log_date <= end_date)
                if min_confidence is not None:
                    query = query.filter(MealLog.confidence_score >= min_confidence)

                meals = query.order_by(MealLog.log_date.desc()).all()

                result = []
                for meal in meals:
                    # Extract manual entry details from food_items
                    manual_item = None
                    if meal.food_items and len(meal.food_items) > 0:
                        manual_item = meal.food_items[0]  # Assume first item for manual entries

                    result.append({
                        "log_id": meal.log_id,
                        "date": meal.log_date.isoformat(),
                        "calories": meal.total_calories,
                        "confidence_score": meal.confidence_score,
                        "confidence_level": _numeric_to_confidence_level(meal.confidence_score),
                        "food_description": manual_item.get("name") if manual_item else None,
                        "warnings": manual_item.get("warnings", []) if manual_item else [],
                        "created_at": meal.created_at.isoformat()
                    })

                return result

        except Exception as e:
            logger.error(f"Failed to get manual entries: {e}")
            return []


def _numeric_to_confidence_level(score: float) -> str:
    """Convert numeric confidence score to level."""
    if score >= 0.8:
        return "high"
    elif score >= 0.6:
        return "medium"
    else:
        return "low"


# Create singleton instance
meal_manager = MealManager()

# Convenience functions
def log_meal(
    user_id: str,
    meal_type: str,
    food_items: List[Dict[str, Any]],
    total_calories: float,
    total_protein_g: float,
    confidence_score: float
) -> Optional[str]:
    """Convenience function to log a meal."""
    return meal_manager.create_meal_log(
        user_id=user_id,
        meal_type=meal_type,
        food_items=food_items,
        total_calories=total_calories,
        total_protein_g=total_protein_g,
        confidence_score=confidence_score
    )

def log_manual_calories(
    user_id: str,
    calories: float,
    meal_type: Optional[str] = None,
    food_description: Optional[str] = None,
    confidence_level: str = "medium",
    validation_warnings: Optional[List[str]] = None
) -> Optional[str]:
    """Convenience function to log manual calories with confidence flagging."""
    return meal_manager.create_manual_calorie_entry(
        user_id=user_id,
        calories=calories,
        meal_type=meal_type,
        food_description=food_description,
        confidence_level=confidence_level,
        validation_warnings=validation_warnings
    )

__all__ = ['MealManager', 'meal_manager', 'log_meal', 'log_manual_calories']