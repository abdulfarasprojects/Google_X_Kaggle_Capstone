"""
Shared pytest fixtures and configuration for Weight Loss Tracker Agent tests.

This module provides:
- Database fixtures with in-memory SQLite
- Mock fixtures for external APIs (USDA, Nutritionix, Gemini)
- Test data fixtures for users and sample data
- Async test support
- Cleanup and teardown utilities
"""

import asyncio
import json
import os
import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any, Generator, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Import project modules
from database.models import Base, UserProfile, MealLog, WorkoutLog, WellnessLog, SessionState
from database.init import get_db_session
from config.settings import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_db_path():
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    yield f"sqlite:///{db_path}"

    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture(scope="session")
def test_engine(test_db_path):
    """Create a test database engine."""
    engine = create_engine(
        test_db_path,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_engine) -> Generator[Session, None, None]:
    """Create a test database session with transaction rollback."""
    connection = test_engine.connect()
    transaction = connection.begin()

    # Create a session bound to the connection
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    yield session

    # Rollback transaction and close
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def mock_db_session(test_db_session):
    """Mock the get_db_session function to return our test session."""
    with patch('database.init.get_db_session') as mock_get_session:
        mock_get_session.return_value.__enter__ = lambda: test_db_session
        mock_get_session.return_value.__exit__ = lambda *args: None
        yield test_db_session


@pytest.fixture(scope="function")
def sample_user(test_db_session) -> UserProfile:
    """Create a sample user for testing."""
    user = UserProfile(
        user_id="test_user_123",
        age=30,
        height_cm=175.0,
        weight_kg=80.0,
        target_weight_kg=75.0,
        activity_level="moderate",
        daily_calorie_goal=2200,
        timezone="UTC"
    )
    test_db_session.add(user)
    test_db_session.commit()
    return user


@pytest.fixture(scope="function")
def mock_usda_api():
    """Mock USDA nutrition API calls."""
    with patch('tools.nutrition.usda_client.lookup_nutrition_usda') as mock_lookup:
        # Mock successful response
        mock_lookup.return_value = {
            "status": "success",
            "data": {
                "food_name": "chicken breast",
                "calories_per_100g": 165,
                "protein_g_per_100g": 31.0,
                "carbs_g_per_100g": 0.0,
                "fat_g_per_100g": 3.6,
                "serving_size_g": 100
            }
        }
        yield mock_lookup


@pytest.fixture(scope="function")
def mock_nutritionix_api():
    """Mock Nutritionix API calls."""
    with patch('tools.nutrition.nutritionix_client.search_food') as mock_search:
        mock_search.return_value = {
            "status": "success",
            "data": {
                "food_name": "banana",
                "calories": 105,
                "protein_g": 1.3,
                "carbs_g": 27.0,
                "fat_g": 0.4,
                "serving_size_g": 118
            }
        }
        yield mock_search


@pytest.fixture(scope="function")
def mock_gemini_api():
    """Mock Google Gemini API calls."""
    with patch('config.gemini.PatchedGemini') as mock_gemini:
        mock_instance = MagicMock()
        mock_gemini.return_value = mock_instance

        # Mock async generate_content method
        mock_instance.generate_content_async = AsyncMock(return_value=MagicMock(
            text='{"calories": 250, "protein_g": 25, "carbs_g": 30, "fat_g": 8}'
        ))

        yield mock_instance


@pytest.fixture(scope="function")
def mock_external_apis(mock_usda_api, mock_nutritionix_api, mock_gemini_api):
    """Mock all external API calls."""
    yield {
        "usda": mock_usda_api,
        "nutritionix": mock_nutritionix_api,
        "gemini": mock_gemini_api
    }


@pytest.fixture(scope="function")
def mock_telegram_context():
    """Mock Telegram update context."""
    mock_context = MagicMock()
    mock_context.bot = MagicMock()
    mock_context.chat_data = {}
    mock_context.user_data = {}
    return mock_context


@pytest.fixture(scope="function")
def golden_datasets_path():
    """Path to golden datasets directory."""
    return Path(__file__).parent / "golden_datasets"


@pytest.fixture(scope="function")
def load_golden_dataset(golden_datasets_path):
    """Factory fixture to load golden datasets."""
    def _load_dataset(filename: str) -> Dict[str, Any]:
        path = golden_datasets_path / filename
        with open(path, 'r') as f:
            return json.load(f)
    return _load_dataset


@pytest.fixture(scope="function")
def nutrition_golden_data(load_golden_dataset):
    """Load nutrition golden dataset."""
    return load_golden_dataset("nutrition_golden.json")


@pytest.fixture(scope="function")
def fitness_golden_data(load_golden_dataset):
    """Load fitness golden dataset."""
    return load_golden_dataset("fitness_golden.json")


@pytest.fixture(scope="function")
def wellness_golden_data(load_golden_dataset):
    """Load wellness golden dataset."""
    return load_golden_dataset("wellness_golden.json")


@pytest.fixture(scope="function")
def analytics_golden_data(load_golden_dataset):
    """Load analytics golden dataset."""
    return load_golden_dataset("analytics_golden.json")


@pytest.fixture(scope="function")
def general_golden_data(load_golden_dataset):
    """Load general golden dataset."""
    return load_golden_dataset("general_golden.json")


@pytest.fixture(scope="function")
def mock_agent_router():
    """Mock agent router for testing."""
    with patch('agents.base.router') as mock_router:
        mock_router.route_message = AsyncMock()
        yield mock_router


@pytest.fixture(scope="function")
def mock_adk_agent():
    """Mock Google ADK LlmAgent."""
    with patch('google.adk.agents.LlmAgent') as mock_agent_class:
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        mock_agent.process_message_async = AsyncMock()
        yield mock_agent


@pytest.fixture(scope="function")
def performance_timer():
    """Fixture for measuring execution time in performance tests."""
    import time

    class Timer:
        def __enter__(self):
            self.start = time.perf_counter()
            return self

        def __exit__(self, *args):
            self.end = time.perf_counter()
            self.duration = self.end - self.start

    return Timer


@pytest.fixture(scope="session")
def pytest_configure():
    """Configure pytest for async tests and custom markers."""
    pytest.mark.asyncio = pytest.mark.asyncio


# Custom pytest markers
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests for individual components")
    config.addinivalue_line("markers", "integration: Integration tests for component interaction")
    config.addinivalue_line("markers", "e2e: End-to-end tests for complete workflows")
    config.addinivalue_line("markers", "performance: Performance and load tests")
    config.addinivalue_line("markers", "golden: Tests using golden datasets")
    config.addinivalue_line("markers", "slow: Tests that take longer than 1 second")


# Test utilities
def assert_api_response_success(response: Dict[str, Any], expected_keys: list = None):
    """Assert that an API response indicates success."""
    assert response.get("status") == "success"
    if expected_keys:
        for key in expected_keys:
            assert key in response


def assert_tool_result_success(result, expected_data_keys: list = None):
    """Assert that a tool result indicates success."""
    from agents.base import ToolResult
    assert isinstance(result, ToolResult)
    assert result.success is True
    assert result.error is None
    if expected_data_keys and result.data:
        for key in expected_data_keys:
            assert key in result.data


def create_test_meal_log(user_id: str, meal_type: str, food_items: list, calories: int, protein: float) -> MealLog:
    """Create a test meal log entry."""
    import uuid
    from datetime import date

    return MealLog(
        log_id=str(uuid.uuid4()),
        user_id=user_id,
        meal_type=meal_type,
        food_items=json.dumps(food_items),
        total_calories=calories,
        total_protein_g=protein,
        confidence_score=0.9,
        log_date=date.today()
    )


def create_test_workout_log(user_id: str, exercises: list, volume: int) -> WorkoutLog:
    """Create a test workout log entry."""
    import uuid
    from datetime import date

    return WorkoutLog(
        log_id=str(uuid.uuid4()),
        user_id=user_id,
        exercises=json.dumps(exercises),
        total_volume=volume,
        log_date=date.today()
    )


def create_test_wellness_log(user_id: str, sleep_hours: float, water_glasses: float, steps: int) -> WellnessLog:
    """Create a test wellness log entry."""
    import uuid
    from datetime import date

    return WellnessLog(
        log_id=str(uuid.uuid4()),
        user_id=user_id,
        sleep_hours=sleep_hours,
        sleep_quality=7,
        water_glasses=water_glasses,
        steps_count=steps,
        log_date=date.today()
    )


# Export utilities for use in tests
__all__ = [
    'assert_api_response_success',
    'assert_tool_result_success',
    'create_test_meal_log',
    'create_test_workout_log',
    'create_test_wellness_log'
]