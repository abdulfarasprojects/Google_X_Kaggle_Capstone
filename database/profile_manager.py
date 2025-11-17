"""
Profile Manager for Weight Loss Chat Agent.

This module provides high-level functions for managing user profiles including:
- Profile creation and validation
- Profile retrieval and updates
- Profile deletion (GDPR compliance)
- Profile search and listing operations

All operations include proper error handling and logging.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from database.models import UserProfile
from database.init import get_db_session
from tools.profile_validator import validate_user_input
from config.logging import get_logger

logger = get_logger(__name__)


class ProfileManagerError(Exception):
    """Raised when profile management operations fail."""
    pass


async def create_user_profile(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new user profile.

    Args:
        profile_data: Dictionary containing profile information

    Returns:
        Dict with creation status and profile data

    Raises:
        ProfileManagerError: If profile creation fails
    """
    try:
        # Validate profile data
        validation = await validate_user_input(profile_data, "profile")
        if not validation["data"]["is_valid"]:
            errors = validation["data"]["errors"]
            raise ProfileManagerError(f"Profile validation failed: {'; '.join(errors)}")

        # Check if profile already exists
        user_id = profile_data.get("user_id")
        if not user_id:
            raise ProfileManagerError("user_id is required for profile creation")

        with get_db_session() as session:
            existing = session.query(UserProfile).filter_by(user_id=user_id).first()
            if existing:
                raise ProfileManagerError(f"Profile already exists for user {user_id}")

            # Create new profile
            profile = UserProfile(**profile_data)
            session.add(profile)
            session.commit()

            logger.info(f"Created profile for user {user_id}")
            return {
                "status": "created",
                "user_id": user_id,
                "profile": profile_to_dict(profile)
            }

    except SQLAlchemyError as e:
        logger.error(f"Database error creating profile: {e}")
        raise ProfileManagerError(f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error creating profile: {e}")
        raise ProfileManagerError(f"Unexpected error: {str(e)}")


async def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a user profile by user ID.

    Args:
        user_id: Telegram user ID

    Returns:
        Profile data as dictionary, or None if not found
    """
    try:
        with get_db_session() as session:
            profile = session.query(UserProfile).filter_by(user_id=user_id).first()
            if profile:
                return profile_to_dict(profile)
            return None

    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving profile for user {user_id}: {e}")
        raise ProfileManagerError(f"Database error: {str(e)}")


async def update_user_profile(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update an existing user profile.

    Args:
        user_id: Telegram user ID
        updates: Dictionary of fields to update

    Returns:
        Dict with update status and updated profile data

    Raises:
        ProfileManagerError: If profile update fails
    """
    try:
        # Get existing profile for validation context
        existing_profile = await get_user_profile(user_id)
        if not existing_profile:
            raise ProfileManagerError(f"Profile not found for user {user_id}")

        # Validate updates
        validation = await validate_user_input(updates, "profile", existing_profile)
        if not validation["data"]["is_valid"]:
            errors = validation["data"]["errors"]
            raise ProfileManagerError(f"Profile validation failed: {'; '.join(errors)}")

        # Apply updates
        with get_db_session() as session:
            profile = session.query(UserProfile).filter_by(user_id=user_id).first()
            if not profile:
                raise ProfileManagerError(f"Profile not found for user {user_id}")

            # Update fields
            for key, value in updates.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)

            profile.updated_at = datetime.utcnow()
            session.commit()

            logger.info(f"Updated profile for user {user_id}")
            return {
                "status": "updated",
                "user_id": user_id,
                "profile": profile_to_dict(profile)
            }

    except SQLAlchemyError as e:
        logger.error(f"Database error updating profile for user {user_id}: {e}")
        raise ProfileManagerError(f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error updating profile for user {user_id}: {e}")
        raise ProfileManagerError(f"Unexpected error: {str(e)}")


async def delete_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Delete a user profile (GDPR compliance).

    This permanently removes all user data from the system.

    Args:
        user_id: Telegram user ID

    Returns:
        Dict with deletion status

    Raises:
        ProfileManagerError: If profile deletion fails
    """
    try:
        with get_db_session() as session:
            profile = session.query(UserProfile).filter_by(user_id=user_id).first()
            if not profile:
                raise ProfileManagerError(f"Profile not found for user {user_id}")

            # Delete profile (cascade will handle related records)
            session.delete(profile)
            session.commit()

            logger.info(f"Deleted profile for user {user_id}")
            return {
                "status": "deleted",
                "user_id": user_id
            }

    except SQLAlchemyError as e:
        logger.error(f"Database error deleting profile for user {user_id}: {e}")
        raise ProfileManagerError(f"Database error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error deleting profile for user {user_id}: {e}")
        raise ProfileManagerError(f"Unexpected error: {str(e)}")


async def list_user_profiles(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """
    List user profiles (admin function).

    Args:
        limit: Maximum number of profiles to return
        offset: Number of profiles to skip

    Returns:
        List of profile dictionaries
    """
    try:
        with get_db_session() as session:
            profiles = session.query(UserProfile).limit(limit).offset(offset).all()
            return [profile_to_dict(profile) for profile in profiles]

    except SQLAlchemyError as e:
        logger.error(f"Database error listing profiles: {e}")
        raise ProfileManagerError(f"Database error: {str(e)}")


async def search_profiles_by_age_range(min_age: int, max_age: int) -> List[Dict[str, Any]]:
    """
    Search profiles by age range.

    Args:
        min_age: Minimum age
        max_age: Maximum age

    Returns:
        List of matching profiles
    """
    try:
        with get_db_session() as session:
            profiles = session.query(UserProfile).filter(
                UserProfile.age >= min_age,
                UserProfile.age <= max_age
            ).all()
            return [profile_to_dict(profile) for profile in profiles]

    except SQLAlchemyError as e:
        logger.error(f"Database error searching profiles by age: {e}")
        raise ProfileManagerError(f"Database error: {str(e)}")


async def get_profile_stats() -> Dict[str, Any]:
    """
    Get aggregate statistics about user profiles.

    Returns:
        Dict with profile statistics
    """
    try:
        with get_db_session() as session:
            total_profiles = session.query(UserProfile).count()

            if total_profiles == 0:
                return {
                    "total_profiles": 0,
                    "average_age": None,
                    "average_height": None,
                    "average_weight": None,
                    "activity_distribution": {}
                }

            # Calculate averages
            avg_age = session.query(UserProfile).with_entities(
                session.query(UserProfile.age).label('avg_age')
            ).first()

            avg_height = session.query(UserProfile).with_entities(
                session.query(UserProfile.height_cm).label('avg_height')
            ).first()

            avg_weight = session.query(UserProfile).with_entities(
                session.query(UserProfile.weight_kg).label('avg_weight')
            ).first()

            # Activity level distribution
            activity_counts = {}
            for profile in session.query(UserProfile).all():
                level = profile.activity_level
                activity_counts[level] = activity_counts.get(level, 0) + 1

            return {
                "total_profiles": total_profiles,
                "average_age": float(avg_age[0]) if avg_age[0] else None,
                "average_height": float(avg_height[0]) if avg_height[0] else None,
                "average_weight": float(avg_weight[0]) if avg_weight[0] else None,
                "activity_distribution": activity_counts
            }

    except SQLAlchemyError as e:
        logger.error(f"Database error getting profile stats: {e}")
        raise ProfileManagerError(f"Database error: {str(e)}")


def profile_to_dict(profile: UserProfile) -> Dict[str, Any]:
    """
    Convert UserProfile model to dictionary.

    Args:
        profile: UserProfile instance

    Returns:
        Dictionary representation of profile
    """
    return {
        "user_id": profile.user_id,
        "age": profile.age,
        "height_cm": float(profile.height_cm),
        "weight_kg": float(profile.weight_kg),
        "target_weight_kg": float(profile.target_weight_kg),
        "activity_level": profile.activity_level,
        "daily_calorie_goal": profile.daily_calorie_goal,
        "timezone": profile.timezone,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None
    }


# Export functions for use in other modules
__all__ = [
    'create_user_profile',
    'get_user_profile',
    'update_user_profile',
    'delete_user_profile',
    'list_user_profiles',
    'search_profiles_by_age_range',
    'get_profile_stats',
    'profile_to_dict',
    'ProfileManagerError'
]