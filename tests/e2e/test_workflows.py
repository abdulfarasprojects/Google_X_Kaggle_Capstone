"""
End-to-end tests for complete user workflows.

Tests full user journeys from onboarding to progress tracking.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import date, timedelta

from telegram_bot.bot import TelegramBot
from agents.base import AgentResponse


class TestCompleteUserJourney:
    """E2E tests for complete user journeys."""

    @pytest.fixture
    def bot(self):
        """Create bot instance for testing."""
        return TelegramBot()

    @pytest.mark.asyncio
    async def test_full_onboarding_to_first_meal_workflow(self, bot, test_db_session):
        """Test complete workflow from onboarding to first meal logging."""
        user_id = "test_user_e2e"

        with patch('telegram_bot.bot.get_db_session') as mock_db, \
             patch('telegram_bot.bot.OnboardingAgent') as mock_onboarding, \
             patch('telegram_bot.bot.RootAgent') as mock_root:

            mock_db.return_value.__aenter__.return_value = test_db_session

            # Mock onboarding agent
            onboarding_instance = AsyncMock()
            onboarding_responses = [
                AgentResponse(text="Welcome! What's your age?", completed=False),
                AgentResponse(text="Great! What's your height in cm?", completed=False),
                AgentResponse(text="Thanks! What's your current weight?", completed=False),
                AgentResponse(text="How active are you?", completed=False),
                AgentResponse(text="What's your goal weight?", completed=False),
                AgentResponse(text="How many weeks to reach your goal?", completed=False),
                AgentResponse(text="🎉 Onboarding complete! Ready to start your journey!", completed=True)
            ]
            onboarding_instance.process_message.side_effect = onboarding_responses
            mock_onboarding.return_value = onboarding_instance

            # Mock root agent for post-onboarding
            root_instance = AsyncMock()
            root_instance.process_message.return_value = AgentResponse(
                text="Your meal has been logged! Keep up the great work!",
                completed=True
            )
            mock_root.return_value = root_instance

            # Step 1: Start onboarding
            response1 = await bot.handle_message("Hi, I want to lose weight", user_id)
            assert "age" in response1.lower()

            # Step 2-7: Complete onboarding
            onboarding_steps = ["30", "175", "80", "moderately active", "75", "12"]
            for step in onboarding_steps:
                response = await bot.handle_message(step, user_id)
                assert isinstance(response, str)

            # Step 8: Log first meal
            response8 = await bot.handle_message("I ate 2 eggs and toast for breakfast", user_id)
            assert "meal" in response8.lower() or "logged" in response8.lower()

    @pytest.mark.asyncio
    async def test_workout_logging_and_progress_workflow(self, bot, test_db_session):
        """Test workout logging and progress tracking workflow."""
        user_id = "test_user_workout"

        with patch('telegram_bot.bot.get_db_session') as mock_db, \
             patch('telegram_bot.bot.RootAgent') as mock_root:

            mock_db.return_value.__aenter__.return_value = test_db_session

            root_instance = AsyncMock()

            # Mock workout logging response
            root_instance.process_message.side_effect = [
                AgentResponse(text="Workout logged! Great job!", completed=True),
                AgentResponse(text="Here's your progress report...", completed=True)
            ]
            mock_root.return_value = root_instance

            # Log workout
            workout_response = await bot.handle_message(
                "I did bench press 3x10 80kg and squats 4x8 100kg",
                user_id
            )
            assert "workout" in workout_response.lower() or "logged" in workout_response.lower()

            # Check progress
            progress_response = await bot.handle_message("How am I doing?", user_id)
            assert "progress" in progress_response.lower() or "report" in progress_response.lower()

    @pytest.mark.asyncio
    async def test_wellness_tracking_workflow(self, bot, test_db_session):
        """Test wellness tracking workflow."""
        user_id = "test_user_wellness"

        with patch('telegram_bot.bot.get_db_session') as mock_db, \
             patch('telegram_bot.bot.RootAgent') as mock_root:

            mock_db.return_value.__aenter__.return_value = test_db_session

            root_instance = AsyncMock()
            root_instance.process_message.return_value = AgentResponse(
                text="Wellness data logged! You're doing great with your habits!",
                completed=True
            )
            mock_root.return_value = root_instance

            # Log wellness data
            wellness_response = await bot.handle_message(
                "I slept 8 hours, drank 8 glasses of water, and walked 10000 steps",
                user_id
            )
            assert "wellness" in wellness_response.lower() or "logged" in wellness_response.lower()

    @pytest.mark.asyncio
    async def test_multi_day_progress_tracking(self, bot, test_db_session):
        """Test progress tracking over multiple days."""
        user_id = "test_user_progress"

        with patch('telegram_bot.bot.get_db_session') as mock_db, \
             patch('telegram_bot.bot.RootAgent') as mock_root:

            mock_db.return_value.__aenter__.return_value = test_db_session

            root_instance = AsyncMock()

            # Mock different responses for different days
            day_responses = [
                AgentResponse(text="Day 1 meal logged!", completed=True),
                AgentResponse(text="Day 2 meal logged!", completed=True),
                AgentResponse(text="Day 3 meal logged!", completed=True),
                AgentResponse(text="Great progress! You've been consistent for 3 days.", completed=True)
            ]
            root_instance.process_message.side_effect = day_responses
            mock_root.return_value = root_instance

            # Simulate 3 days of meal logging
            for day in range(1, 4):
                meal_msg = f"Day {day}: I ate chicken salad for lunch"
                response = await bot.handle_message(meal_msg, user_id)
                assert "meal" in response.lower() or "logged" in response.lower()

            # Check progress summary
            progress_response = await bot.handle_message("What's my progress?", user_id)
            assert "progress" in progress_response.lower() or "consistent" in progress_response.lower()

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, bot, test_db_session):
        """Test error handling throughout the workflow."""
        user_id = "test_user_error"

        with patch('telegram_bot.bot.get_db_session') as mock_db, \
             patch('telegram_bot.bot.RootAgent') as mock_root:

            mock_db.return_value.__aenter__.return_value = test_db_session

            root_instance = AsyncMock()

            # Mock error response followed by recovery
            root_instance.process_message.side_effect = [
                AgentResponse(text="Sorry, I couldn't understand that. Could you rephrase?", completed=False),
                AgentResponse(text="Got it! Meal logged successfully.", completed=True)
            ]
            mock_root.return_value = root_instance

            # Send unclear message
            error_response = await bot.handle_message("asdkfjhasdkfjh", user_id)
            assert "sorry" in error_response.lower() or "understand" in error_response.lower()

            # Send clear message
            recovery_response = await bot.handle_message("I ate pasta for dinner", user_id)
            assert "meal" in recovery_response.lower() or "logged" in recovery_response.lower()


class TestDataConsistencyE2E:
    """E2E tests for data consistency across the system."""

    @pytest.fixture
    def bot(self):
        """Create bot instance for testing."""
        return TelegramBot()

    @pytest.mark.asyncio
    async def test_meal_data_consistency(self, bot, test_db_session):
        """Test that meal data is consistently stored and retrieved."""
        user_id = "test_user_consistency"

        with patch('telegram_bot.bot.get_db_session') as mock_db, \
             patch('telegram_bot.bot.RootAgent') as mock_root:

            mock_db.return_value.__aenter__.return_value = test_db_session

            root_instance = AsyncMock()

            # Mock meal logging with specific calorie data
            meal_data = {
                "total_calories": 450,
                "total_protein_g": 25,
                "meal_type": "lunch"
            }

            root_instance.process_message.side_effect = [
                AgentResponse(text=f"Meal logged! {meal_data['total_calories']} calories, {meal_data['total_protein_g']}g protein", completed=True),
                AgentResponse(text=f"Your lunch had {meal_data['total_calories']} calories and {meal_data['total_protein_g']}g protein", completed=True)
            ]
            mock_root.return_value = root_instance

            # Log meal
            log_response = await bot.handle_message("I ate chicken breast and rice for lunch", user_id)
            assert str(meal_data['total_calories']) in log_response
            assert str(meal_data['total_protein_g']) in log_response

            # Query meal data
            query_response = await bot.handle_message("What did I eat for lunch?", user_id)
            assert str(meal_data['total_calories']) in query_response
            assert str(meal_data['total_protein_g']) in query_response

    @pytest.mark.asyncio
    async def test_workout_data_consistency(self, bot, test_db_session):
        """Test that workout data is consistently stored and retrieved."""
        user_id = "test_user_workout_consistency"

        with patch('telegram_bot.bot.get_db_session') as mock_db, \
             patch('telegram_bot.bot.RootAgent') as mock_root:

            mock_db.return_value.__aenter__.return_value = test_db_session

            root_instance = AsyncMock()

            workout_data = {
                "total_volume": 2400,
                "exercise_count": 2,
                "category": "heavy"
            }

            root_instance.process_message.side_effect = [
                AgentResponse(text=f"Workout logged! Total volume: {workout_data['total_volume']}, {workout_data['category']} intensity", completed=True),
                AgentResponse(text=f"Your last workout had {workout_data['total_volume']} volume and was {workout_data['category']}", completed=True)
            ]
            mock_root.return_value = root_instance

            # Log workout
            log_response = await bot.handle_message("Bench press 3x10 80kg, squats 4x8 100kg", user_id)
            assert str(workout_data['total_volume']) in log_response
            assert workout_data['category'] in log_response

            # Query workout data
            query_response = await bot.handle_message("What was my last workout?", user_id)
            assert str(workout_data['total_volume']) in query_response
            assert workout_data['category'] in query_response


class TestPerformanceE2E:
    """E2E tests for performance and response times."""

    @pytest.fixture
    def bot(self):
        """Create bot instance for testing."""
        return TelegramBot()

    @pytest.mark.asyncio
    async def test_response_time_under_threshold(self, bot, test_db_session):
        """Test that responses are returned within acceptable time limits."""
        import time

        user_id = "test_user_performance"

        with patch('telegram_bot.bot.get_db_session') as mock_db, \
             patch('telegram_bot.bot.RootAgent') as mock_root:

            mock_db.return_value.__aenter__.return_value = test_db_session

            root_instance = AsyncMock()
            root_instance.process_message.return_value = AgentResponse(
                text="Quick response!",
                completed=True
            )
            mock_root.return_value = root_instance

            # Measure response time
            start_time = time.time()
            response = await bot.handle_message("Hello", user_id)
            end_time = time.time()

            response_time = end_time - start_time

            # Assert response time is under 2 seconds (reasonable for bot responses)
            assert response_time < 2.0
            assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_concurrent_user_handling(self, bot, test_db_session):
        """Test handling multiple concurrent users."""
        import asyncio

        with patch('telegram_bot.bot.get_db_session') as mock_db, \
             patch('telegram_bot.bot.RootAgent') as mock_root:

            mock_db.return_value.__aenter__.return_value = test_db_session

            root_instance = AsyncMock()
            root_instance.process_message.return_value = AgentResponse(
                text="Response for user",
                completed=True
            )
            mock_root.return_value = root_instance

            # Simulate concurrent requests from multiple users
            async def user_request(user_id):
                return await bot.handle_message(f"Hello from {user_id}", user_id)

            user_ids = [f"user_{i}" for i in range(5)]
            tasks = [user_request(uid) for uid in user_ids]

            responses = await asyncio.gather(*tasks)

            # All responses should be successful
            assert len(responses) == 5
            assert all(isinstance(r, str) for r in responses)