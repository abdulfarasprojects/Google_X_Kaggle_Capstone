"""
Database models for Weight Loss Chat Agent.

This module defines all database models using SQLAlchemy ORM for the weight loss
tracking system. All data is stored locally in SQLite for MVP privacy compliance.

Models include:
- User profiles with demographics and goals
- Meal logs with batch processing support
- Workout logs with progression tracking
- Wellness logs for sleep, water, and steps
- Nudge events for autonomous scheduling
- Progress summaries for analytics
- Session states for conversation management
- API usage tracking for cost monitoring
"""

import json
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, Date,
    DECIMAL, Boolean, ForeignKey, CheckConstraint, UniqueConstraint,
    Index, func
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Create declarative base
Base = declarative_base()

# Database engine configuration for SQLite
engine = create_engine(
    "sqlite:///weight_loss_app.db",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False  # Set to True for debugging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class UserProfile(Base):
    """
    User profile with demographics, goals, and preferences.

    Stores essential user information for personalization and validation.
    All fields include CHECK constraints for data integrity.
    """
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, comment="Unique Telegram user ID")
    age = Column(Integer, nullable=False, comment="Age in years (18-100)")
    height_cm = Column(DECIMAL(5,2), nullable=False, comment="Height in centimeters")
    weight_kg = Column(DECIMAL(5,2), nullable=False, comment="Current weight in kilograms")
    target_weight_kg = Column(DECIMAL(5,2), nullable=False, comment="Target weight in kilograms")
    activity_level = Column(String, nullable=False, comment="Activity level category")
    daily_calorie_goal = Column(Integer, nullable=False, comment="Calculated daily calorie budget")
    timezone = Column(String, nullable=False, comment="User's timezone")
    created_at = Column(DateTime, default=datetime.utcnow, comment="Profile creation timestamp")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="Last update timestamp")

    # Relationships
    meal_logs = relationship("MealLog", back_populates="user", cascade="all, delete-orphan")
    workout_logs = relationship("WorkoutLog", back_populates="user", cascade="all, delete-orphan")
    wellness_logs = relationship("WellnessLog", back_populates="user", cascade="all, delete-orphan")
    nudge_events = relationship("NudgeEvent", back_populates="user", cascade="all, delete-orphan")
    progress_summaries = relationship("ProgressSummary", back_populates="user", cascade="all, delete-orphan")
    session_states = relationship("SessionState", back_populates="user", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint('age >= 18 AND age <= 100', name='check_age_range'),
        CheckConstraint('height_cm >= 100 AND height_cm <= 250', name='check_height_range'),
        CheckConstraint('weight_kg >= 30 AND weight_kg <= 300', name='check_weight_range'),
        CheckConstraint('target_weight_kg < weight_kg', name='check_target_weight_less_than_current'),
        CheckConstraint('daily_calorie_goal >= 1000 AND daily_calorie_goal <= 3000', name='check_calorie_goal_range'),
        CheckConstraint("activity_level IN ('sedentary', 'light', 'moderate', 'active', 'very_active')", name='check_activity_level'),
    )


class MealLog(Base):
    """
    Meal consumption logs with batch processing support.

    Tracks food intake with nutritional calculations and confidence scoring.
    Supports up to 10 food items per meal for batch processing.
    """
    __tablename__ = "daily_logs_nutrition"

    log_id = Column(String, primary_key=True, comment="Unique log identifier")
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False, comment="Reference to user profile")
    meal_type = Column(String, nullable=False, comment="Meal type (breakfast, lunch, dinner, snack)")
    food_items = Column(Text, nullable=False, comment="JSON array of food item objects")  # Stored as JSON string
    total_calories = Column(Integer, nullable=False, comment="Sum of all food item calories")
    total_protein_g = Column(DECIMAL(6,2), nullable=False, comment="Sum of all food item protein")
    confidence_score = Column(DECIMAL(3,2), nullable=False, comment="Average confidence across all items")
    log_date = Column(Date, nullable=False, comment="Date of consumption")
    created_at = Column(DateTime, default=datetime.utcnow, comment="Log creation timestamp")

    # Relationships
    user = relationship("UserProfile", back_populates="meal_logs")

    # Constraints
    __table_args__ = (
        CheckConstraint("meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')", name='check_meal_type'),
        CheckConstraint('total_calories > 0', name='check_positive_calories'),
        CheckConstraint('total_protein_g >= 0', name='check_non_negative_protein'),
        CheckConstraint('confidence_score >= 0.0 AND confidence_score <= 1.0', name='check_confidence_range'),
        Index('idx_meal_logs_user_date', 'user_id', 'log_date'),
    )

    @property
    def food_items_list(self) -> List[Dict[str, Any]]:
        """Get food items as parsed JSON list."""
        return json.loads(self.food_items) if self.food_items else []

    @food_items_list.setter
    def food_items_list(self, value: List[Dict[str, Any]]) -> None:
        """Set food items from list as JSON string."""
        self.food_items = json.dumps(value)


class WorkoutLog(Base):
    """
    Exercise session logs with progression tracking.

    Tracks workout sessions with volume calculations and AI-generated progression suggestions.
    Supports up to 10 exercises per session.
    """
    __tablename__ = "daily_logs_fitness"

    log_id = Column(String, primary_key=True, comment="Unique log identifier")
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False, comment="Reference to user profile")
    exercises = Column(Text, nullable=False, comment="JSON array of exercise objects")  # Stored as JSON string
    total_volume = Column(Integer, nullable=False, comment="Calculated total volume score")
    progression_suggestion = Column(Text, comment="AI-generated progression recommendation")
    log_date = Column(Date, nullable=False, comment="Date of workout")
    created_at = Column(DateTime, default=datetime.utcnow, comment="Log creation timestamp")

    # Relationships
    user = relationship("UserProfile", back_populates="workout_logs")

    # Constraints
    __table_args__ = (
        CheckConstraint('total_volume >= 0', name='check_non_negative_volume'),
        Index('idx_workout_logs_user_date', 'user_id', 'log_date'),
    )

    @property
    def exercises_list(self) -> List[Dict[str, Any]]:
        """Get exercises as parsed JSON list."""
        return json.loads(self.exercises) if self.exercises else []

    @exercises_list.setter
    def exercises_list(self, value: List[Dict[str, Any]]) -> None:
        """Set exercises from list as JSON string."""
        self.exercises = json.dumps(value)


class WellnessLog(Base):
    """
    Daily wellness metrics tracking.

    Tracks sleep, water intake, and steps with unique constraint per user per day.
    Allows zero values for tracking purposes (e.g., insomnia days).
    """
    __tablename__ = "daily_logs_wellness"

    log_id = Column(String, primary_key=True, comment="Unique log identifier")
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False, comment="Reference to user profile")
    sleep_hours = Column(DECIMAL(4,2), nullable=False, comment="Hours of sleep")
    sleep_quality = Column(Integer, nullable=False, comment="Self-reported quality (1-10 scale)")
    water_glasses = Column(DECIMAL(4,2), nullable=False, comment="Glasses of water consumed")
    steps_count = Column(Integer, nullable=False, comment="Daily step count")
    log_date = Column(Date, nullable=False, comment="Date of wellness tracking")
    created_at = Column(DateTime, default=datetime.utcnow, comment="Log creation timestamp")

    # Relationships
    user = relationship("UserProfile", back_populates="wellness_logs")

    # Constraints
    __table_args__ = (
        CheckConstraint('sleep_hours >= 0 AND sleep_hours <= 24', name='check_sleep_hours_range'),
        CheckConstraint('sleep_quality >= 1 AND sleep_quality <= 10', name='check_sleep_quality_range'),
        CheckConstraint('water_glasses >= 0 AND water_glasses <= 20', name='check_water_glasses_range'),
        CheckConstraint('steps_count >= 0 AND steps_count <= 100000', name='check_steps_range'),
        UniqueConstraint('user_id', 'log_date', name='unique_user_date_wellness'),
        Index('idx_wellness_logs_user_date', 'user_id', 'log_date'),
    )


class NudgeEvent(Base):
    """
    Autonomous nudge scheduling and delivery tracking.

    Tracks scheduled autonomous nudges with delivery status and timing.
    Supports different nudge types for various reminder scenarios.
    """
    __tablename__ = "nudges"

    nudge_id = Column(String, primary_key=True, comment="Unique nudge identifier")
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False, comment="Reference to user profile")
    nudge_type = Column(String, nullable=False, comment="Nudge type category")
    message = Column(Text, nullable=False, comment="The nudge message content")
    scheduled_time = Column(DateTime, nullable=False, comment="When nudge was scheduled")
    delivered_at = Column(DateTime, comment="When nudge was actually delivered")
    status = Column(String, nullable=False, default='scheduled', comment="Delivery status")

    # Relationships
    user = relationship("UserProfile", back_populates="nudge_events")

    # Constraints
    __table_args__ = (
        CheckConstraint("nudge_type IN ('morning', 'midday', 'evening', 'weekly', 'streak_protection')", name='check_nudge_type'),
        CheckConstraint("status IN ('scheduled', 'delivered', 'failed', 'cancelled')", name='check_nudge_status'),
        Index('idx_nudges_scheduled', 'scheduled_time'),
        Index('idx_nudges_user_status', 'user_id', 'status'),
    )


class ProgressSummary(Base):
    """
    Aggregated analytics for progress tracking and reporting.

    Stores calculated summaries for different time periods with hero stats
    and trend analysis. Used for weekly/monthly progress reports.
    """
    __tablename__ = "progress_summaries"

    summary_id = Column(String, primary_key=True, comment="Unique summary identifier")
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False, comment="Reference to user profile")
    period_type = Column(String, nullable=False, comment="Summary period type")
    period_start = Column(Date, nullable=False, comment="Start date of summary period")
    period_end = Column(Date, nullable=False, comment="End date of summary period")
    calories_logged = Column(Integer, default=0, comment="Total calories logged in period")
    workouts_completed = Column(Integer, default=0, comment="Number of workout sessions")
    sleep_avg_hours = Column(DECIMAL(4,2), comment="Average sleep hours")
    water_avg_glasses = Column(DECIMAL(4,2), comment="Average water intake")
    steps_avg_count = Column(Integer, comment="Average daily steps")
    streak_days = Column(Integer, default=0, comment="Current logging streak")
    hero_stat = Column(Text, comment="Most impressive achievement in period")
    created_at = Column(DateTime, default=datetime.utcnow, comment="Summary creation timestamp")

    # Relationships
    user = relationship("UserProfile", back_populates="progress_summaries")

    # Constraints
    __table_args__ = (
        CheckConstraint("period_type IN ('daily', 'weekly', 'monthly')", name='check_period_type'),
        CheckConstraint('period_end >= period_start', name='check_period_dates'),
        CheckConstraint('calories_logged >= 0', name='check_non_negative_calories'),
        CheckConstraint('workouts_completed >= 0', name='check_non_negative_workouts'),
        CheckConstraint('streak_days >= 0', name='check_non_negative_streak'),
        Index('idx_progress_user_period', 'user_id', 'period_type', 'period_end'),
    )


class SessionState(Base):
    """
    Conversation context and batch processing state management.

    Tracks current conversation state for batch processing workflows.
    Automatically expires after 24 hours for security and cleanup.
    """
    __tablename__ = "batch_states"

    batch_id = Column(String, primary_key=True, comment="Unique session identifier")
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False, comment="Reference to user profile")
    batch_type = Column(String, comment="Current batch type (meal, workout, wellness)")
    batch_items = Column(Text, comment="JSON array of current batch items")  # Stored as JSON string
    expires_at = Column(DateTime, nullable=False, comment="When session expires")
    created_at = Column(DateTime, default=datetime.utcnow, comment="Session creation timestamp")

    # Relationships
    user = relationship("UserProfile", back_populates="session_states")

    # Constraints
    __table_args__ = (
        CheckConstraint("batch_type IN ('meal', 'workout', 'wellness') OR batch_type IS NULL", name='check_batch_type'),
        Index('idx_sessions_expires', 'expires_at'),
    )

    @property
    def batch_items_list(self) -> Optional[List[Dict[str, Any]]]:
        """Get batch items as parsed JSON list."""
        return json.loads(self.batch_items) if self.batch_items else None

    @batch_items_list.setter
    def batch_items_list(self, value: Optional[List[Dict[str, Any]]]) -> None:
        """Set batch items from list as JSON string."""
        self.batch_items = json.dumps(value) if value is not None else None


class ApiUsage(Base):
    """
    API usage tracking for cost monitoring and rate limiting.

    Global table tracking API calls across all providers for billing
    and optimization purposes. No foreign key relationships.
    """
    __tablename__ = "api_usage"

    usage_id = Column(String, primary_key=True, comment="Unique usage record identifier")
    provider = Column(String, nullable=False, comment="API provider name")
    endpoint = Column(String, nullable=False, comment="Specific API endpoint called")
    request_count = Column(Integer, nullable=False, default=1, comment="Number of requests made")
    cost_usd = Column(DECIMAL(6,4), nullable=False, default=0.0, comment="Cost in USD")
    created_at = Column(DateTime, default=datetime.utcnow, comment="Usage record timestamp")

    # Constraints
    __table_args__ = (
        CheckConstraint('request_count > 0', name='check_positive_request_count'),
        CheckConstraint('cost_usd >= 0', name='check_non_negative_cost'),
        Index('idx_api_usage_provider_date', 'provider', 'created_at'),
    )


def init_db() -> None:
    """
    Initialize the database by creating all tables.

    This function should be called once during application startup
    to ensure all database tables exist with proper schema.
    """
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """
    Get a database session for operations.

    Returns a SQLAlchemy session that should be closed after use.
    Use in FastAPI dependency injection or with context managers.
    """
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


def create_database_schema() -> str:
    """
    Generate the complete SQLite schema as SQL DDL statements.

    Returns the full schema as a string for documentation or migration purposes.
    This matches the schema defined in data-model.md.
    """
    from sqlalchemy.schema import CreateTable

    schema_parts = []
    for table in Base.metadata.sorted_tables:
        schema_parts.append(str(CreateTable(table).compile(engine)))

    return "\n\n".join(schema_parts)


# Export all models for easy importing
__all__ = [
    'Base', 'engine', 'SessionLocal',
    'UserProfile', 'MealLog', 'WorkoutLog', 'WellnessLog',
    'NudgeEvent', 'ProgressSummary', 'SessionState', 'ApiUsage',
    'init_db', 'get_db', 'create_database_schema'
]