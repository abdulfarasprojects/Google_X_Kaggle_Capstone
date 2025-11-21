"""
Integration tests for agent functionality.

Tests end-to-end agent processing with mocked dependencies.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import date

from agents.onboarding_agent import OnboardingAgent
from agents.nutrition.agent import nutrition_agent as NutritionAgent
from agents.fitness.agent import fitness_agent as FitnessAgent
from agents.wellness.agent import wellness_agent as WellnessAgent
from agents.analytics.agent import analytics_agent as AnalyticsAgent
from agents.root.agent import root_agent as RootAgent
from agents.base import AgentResponse


class TestOnboardingAgentIntegration:
    """Integration tests for onboarding agent."""

    @pytest.fixture
    def onboarding_agent(self):
        """Create onboarding agent instance."""
        return OnboardingAgent()

    @pytest.mark.asyncio
    async def test_complete_onboarding_flow(self, onboarding_agent, test_db_session, sample_user):
        """Test complete onboarding flow from start to finish."""
        # Mock external dependencies
        with patch('agents.onboarding_agent.get_db_session') as mock_db, \
             patch('agents.onboarding_agent.format_response') as mock_format:

            mock_db.return_value.__aenter__.return_value = test_db_session
            mock_format.return_value = {"formatted_response": "Welcome to your weight loss journey!"}

            # Step 1: Initial greeting
            response1 = await onboarding_agent.process_message(
                message="Hi, I want to start my weight loss journey",
                user_id=sample_user["telegram_id"]
            )

            assert isinstance(response1, AgentResponse)
            assert "weight loss" in response1.text.lower() or "welcome" in response1.text.lower()

            # Step 2: Age input
            response2 = await onboarding_agent.process_message(
                message="30",
                user_id=sample_user["telegram_id"]
            )

            assert isinstance(response2, AgentResponse)

            # Step 3: Height input
            response3 = await onboarding_agent.process_message(
                message="175",
                user_id=sample_user["telegram_id"]
            )

            assert isinstance(response3, AgentResponse)

            # Step 4: Weight input
            response4 = await onboarding_agent.process_message(
                message="80",
                user_id=sample_user["telegram_id"]
            )

            assert isinstance(response4, AgentResponse)

            # Step 5: Activity level
            response5 = await onboarding_agent.process_message(
                message="moderately active",
                user_id=sample_user["telegram_id"]
            )

            assert isinstance(response5, AgentResponse)

            # Step 6: Goal weight
            response6 = await onboarding_agent.process_message(
                message="75",
                user_id=sample_user["telegram_id"]
            )

            assert isinstance(response6, AgentResponse)

            # Step 7: Timeframe
            response7 = await onboarding_agent.process_message(
                message="12 weeks",
                user_id=sample_user["telegram_id"]
            )

            assert isinstance(response7, AgentResponse)
            assert response7.completed is True

    @pytest.mark.asyncio
    async def test_onboarding_with_invalid_data(self, onboarding_agent, test_db_session):
        """Test onboarding with invalid data handling."""
        with patch('agents.onboarding_agent.get_db_session') as mock_db:
            mock_db.return_value.__aenter__.return_value = test_db_session

            # Invalid age
            response = await onboarding_agent.process_message(
                message="10",  # Too young
                user_id="test_user"
            )

            assert isinstance(response, AgentResponse)
            assert "age" in response.text.lower() or "invalid" in response.text.lower()


class TestNutritionAgentIntegration:
    """Integration tests for nutrition agent."""

    @pytest.fixture
    def nutrition_agent(self):
        """Create nutrition agent instance."""
        return NutritionAgent()

    @pytest.mark.asyncio
    async def test_meal_logging_flow(self, nutrition_agent, test_db_session, sample_user):
        """Test complete meal logging flow."""
        with patch('agents.nutrition.agent.get_db_session') as mock_db, \
             patch('agents.nutrition.agent.BatchFoodParserTool') as mock_parser, \
             patch('agents.nutrition.agent.MealNutritionCalculatorTool') as mock_calculator, \
             patch('agents.nutrition.agent.format_response') as mock_format:

            mock_db.return_value.__aenter__.return_value = test_db_session

            # Mock parser response
            mock_parser_instance = AsyncMock()
            mock_parser_instance.execute.return_value = MagicMock(
                success=True,
                data={"parsed_items": [
                    {"description": "2 eggs", "quantity": 2.0, "parsed_food": "eggs", "confidence": 0.9}
                ]}
            )
            mock_parser.return_value = mock_parser_instance

            # Mock calculator response
            mock_calculator_instance = AsyncMock()
            mock_calculator_instance.execute.return_value = MagicMock(
                success=True,
                data={
                    "total_calories": 140,
                    "total_protein_g": 12,
                    "macros": {"carbs": 1, "fat": 10}
                }
            )
            mock_calculator.return_value = mock_calculator_instance

            mock_format.return_value = {"formatted_response": "Meal logged successfully!"}

            # Process meal logging message
            response = await nutrition_agent.process_message(
                message="I ate 2 eggs for breakfast",
                user_id=sample_user["telegram_id"]
            )

            assert isinstance(response, AgentResponse)
            assert "meal" in response.text.lower() or "logged" in response.text.lower()

    @pytest.mark.asyncio
    async def test_nutrition_query_handling(self, nutrition_agent, test_db_session, sample_user):
        """Test nutrition-related queries."""
        with patch('agents.nutrition.agent.get_db_session') as mock_db, \
             patch('agents.nutrition.agent.format_response') as mock_format:

            mock_db.return_value.__aenter__.return_value = test_db_session
            mock_format.return_value = {"formatted_response": "Here's your nutrition advice..."}

            response = await nutrition_agent.process_message(
                message="How many calories should I eat per day?",
                user_id=sample_user["telegram_id"]
            )

            assert isinstance(response, AgentResponse)
            assert "calories" in response.text.lower() or "nutrition" in response.text.lower()


class TestFitnessAgentIntegration:
    """Integration tests for fitness agent."""

    @pytest.fixture
    def fitness_agent(self):
        """Create fitness agent instance."""
        return FitnessAgent()

    @pytest.mark.asyncio
    async def test_workout_logging_flow(self, fitness_agent, test_db_session, sample_user):
        """Test complete workout logging flow."""
        with patch('agents.fitness.agent.get_db_session') as mock_db, \
             patch('agents.fitness.agent.BatchWorkoutParserTool') as mock_parser, \
             patch('agents.fitness.agent.VolumeCalculatorTool') as mock_calculator, \
             patch('agents.fitness.agent.format_response') as mock_format:

            mock_db.return_value.__aenter__.return_value = test_db_session

            # Mock parser response
            mock_parser_instance = AsyncMock()
            mock_parser_instance.execute.return_value = MagicMock(
                success=True,
                data={"parsed_exercises": [
                    {"exercise_name": "bench press", "sets": 3, "reps": 10, "weight": 80.0}
                ]}
            )
            mock_parser.return_value = mock_parser_instance

            # Mock calculator response
            mock_calculator_instance = AsyncMock()
            mock_calculator_instance.execute.return_value = MagicMock(
                success=True,
                data={
                    "total_volume": 2400,
                    "exercise_breakdown": [],
                    "volume_category": "heavy"
                }
            )
            mock_calculator.return_value = mock_calculator_instance

            mock_format.return_value = {"formatted_response": "Workout logged successfully!"}

            # Process workout logging message
            response = await fitness_agent.process_message(
                message="I did bench press 3 sets of 10 reps at 80kg",
                user_id=sample_user["telegram_id"]
            )

            assert isinstance(response, AgentResponse)
            assert "workout" in response.text.lower() or "logged" in response.text.lower()

    @pytest.mark.asyncio
    async def test_fitness_query_handling(self, fitness_agent, test_db_session, sample_user):
        """Test fitness-related queries."""
        with patch('agents.fitness.agent.get_db_session') as mock_db, \
             patch('agents.fitness.agent.format_response') as mock_format:

            mock_db.return_value.__aenter__.return_value = test_db_session
            mock_format.return_value = {"formatted_response": "Here's your fitness advice..."}

            response = await fitness_agent.process_message(
                message="What exercises should I do for weight loss?",
                user_id=sample_user["telegram_id"]
            )

            assert isinstance(response, AgentResponse)
            assert "exercise" in response.text.lower() or "fitness" in response.text.lower()


class TestWellnessAgentIntegration:
    """Integration tests for wellness agent."""

    @pytest.fixture
    def wellness_agent(self):
        """Create wellness agent instance."""
        return WellnessAgent()

    @pytest.mark.asyncio
    async def test_wellness_logging_flow(self, wellness_agent, test_db_session, sample_user):
        """Test complete wellness logging flow."""
        with patch('agents.wellness.agent.get_db_session') as mock_db, \
             patch('agents.wellness.agent.WellnessParserTool') as mock_parser, \
             patch('agents.wellness.agent.format_response') as mock_format:

            mock_db.return_value.__aenter__.return_value = test_db_session

            # Mock parser response
            mock_parser_instance = AsyncMock()
            mock_parser_instance.execute.return_value = MagicMock(
                success=True,
                data={"parsed_entries": [
                    {"entry_type": "sleep", "value": 8.0, "unit": "hours", "confidence": 0.9}
                ]}
            )
            mock_parser.return_value = mock_parser_instance

            mock_format.return_value = {"formatted_response": "Wellness data logged successfully!"}

            # Process wellness logging message
            response = await wellness_agent.process_message(
                message="I slept 8 hours last night",
                user_id=sample_user["telegram_id"]
            )

            assert isinstance(response, AgentResponse)
            assert "wellness" in response.text.lower() or "logged" in response.text.lower()

    @pytest.mark.asyncio
    async def test_wellness_query_handling(self, wellness_agent, test_db_session, sample_user):
        """Test wellness-related queries."""
        with patch('agents.wellness.agent.get_db_session') as mock_db, \
             patch('agents.wellness.agent.format_response') as mock_format:

            mock_db.return_value.__aenter__.return_value = test_db_session
            mock_format.return_value = {"formatted_response": "Here's your wellness advice..."}

            response = await wellness_agent.process_message(
                message="How much water should I drink daily?",
                user_id=sample_user["telegram_id"]
            )

            assert isinstance(response, AgentResponse)
            assert "water" in response.text.lower() or "wellness" in response.text.lower()


class TestAnalyticsAgentIntegration:
    """Integration tests for analytics agent."""

    @pytest.fixture
    def analytics_agent(self):
        """Create analytics agent instance."""
        return AnalyticsAgent()

    @pytest.mark.asyncio
    async def test_progress_report_generation(self, analytics_agent, test_db_session, sample_user):
        """Test progress report generation."""
        with patch('agents.analytics.agent.get_db_session') as mock_db, \
             patch('agents.analytics.agent.format_response') as mock_format:

            mock_db.return_value.__aenter__.return_value = test_db_session
            mock_format.return_value = {"formatted_response": "Here's your progress report..."}

            response = await analytics_agent.process_message(
                message="Show me my progress",
                user_id=sample_user["telegram_id"]
            )

            assert isinstance(response, AgentResponse)
            assert "progress" in response.text.lower() or "report" in response.text.lower()

    @pytest.mark.asyncio
    async def test_analytics_query_handling(self, analytics_agent, test_db_session, sample_user):
        """Test analytics-related queries."""
        with patch('agents.analytics.agent.get_db_session') as mock_db, \
             patch('agents.analytics.agent.format_response') as mock_format:

            mock_db.return_value.__aenter__.return_value = test_db_session
            mock_format.return_value = {"formatted_response": "Here's your analytics..."}

            response = await analytics_agent.process_message(
                message="What's my average calorie intake?",
                user_id=sample_user["telegram_id"]
            )

            assert isinstance(response, AgentResponse)
            assert "calorie" in response.text.lower() or "average" in response.text.lower()


class TestRootAgentIntegration:
    """Integration tests for root agent routing."""

    @pytest.fixture
    def root_agent(self):
        """Create root agent instance."""
        return RootAgent()

    @pytest.mark.asyncio
    async def test_message_routing_to_nutrition(self, root_agent, test_db_session, sample_user):
        """Test routing nutrition-related messages."""
        with patch('agents.root.agent.get_db_session') as mock_db, \
             patch('agents.root.agent.NutritionAgent') as mock_nutrition_agent:

            mock_db.return_value.__aenter__.return_value = test_db_session

            mock_agent_instance = AsyncMock()
            mock_agent_instance.process_message.return_value = AgentResponse(
                text="Nutrition response",
                completed=True
            )
            mock_nutrition_agent.return_value = mock_agent_instance

            response = await root_agent.process_message(
                message="I ate chicken and rice for lunch",
                user_id=sample_user["telegram_id"]
            )

            assert isinstance(response, AgentResponse)
            assert "nutrition" in response.text.lower() or "response" in response.text.lower()

    @pytest.mark.asyncio
    async def test_message_routing_to_fitness(self, root_agent, test_db_session, sample_user):
        """Test routing fitness-related messages."""
        with patch('agents.root.agent.get_db_session') as mock_db, \
             patch('agents.root.agent.FitnessAgent') as mock_fitness_agent:

            mock_db.return_value.__aenter__.return_value = test_db_session

            mock_agent_instance = AsyncMock()
            mock_agent_instance.process_message.return_value = AgentResponse(
                text="Fitness response",
                completed=True
            )
            mock_fitness_agent.return_value = mock_agent_instance

            response = await root_agent.process_message(
                message="I did squats and bench press today",
                user_id=sample_user["telegram_id"]
            )

            assert isinstance(response, AgentResponse)
            assert "fitness" in response.text.lower() or "response" in response.text.lower()

    @pytest.mark.asyncio
    async def test_message_routing_to_wellness(self, root_agent, test_db_session, sample_user):
        """Test routing wellness-related messages."""
        with patch('agents.root.agent.get_db_session') as mock_db, \
             patch('agents.root.agent.WellnessAgent') as mock_wellness_agent:

            mock_db.return_value.__aenter__.return_value = test_db_session

            mock_agent_instance = AsyncMock()
            mock_agent_instance.process_message.return_value = AgentResponse(
                text="Wellness response",
                completed=True
            )
            mock_wellness_agent.return_value = mock_agent_instance

            response = await root_agent.process_message(
                message="I slept 7 hours and drank 8 glasses of water",
                user_id=sample_user["telegram_id"]
            )

            assert isinstance(response, AgentResponse)
            assert "wellness" in response.text.lower() or "response" in response.text.lower()

    @pytest.mark.asyncio
    async def test_general_query_handling(self, root_agent, test_db_session, sample_user):
        """Test handling general queries."""
        with patch('agents.root.agent.get_db_session') as mock_db, \
             patch('agents.root.agent.format_response') as mock_format:

            mock_db.return_value.__aenter__.return_value = test_db_session
            mock_format.return_value = {"formatted_response": "General response"}

            response = await root_agent.process_message(
                message="Hello, how are you?",
                user_id=sample_user["telegram_id"]
            )

            assert isinstance(response, AgentResponse)