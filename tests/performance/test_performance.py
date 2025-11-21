"""
Performance tests for the Weight Loss Tracker Agent.

Tests response times, throughput, and resource usage under load.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch
from statistics import mean, median, stdev
from concurrent.futures import ThreadPoolExecutor

from agents.root.agent import root_agent as RootAgent
from tools.nutrition.calculator import MealNutritionCalculatorTool
from tools.fitness.calculator import VolumeCalculatorTool
from database.init import get_db_session


class TestResponseTimePerformance:
    """Test response time performance for various operations."""

    @pytest.fixture
    def root_agent(self):
        """Create root agent instance."""
        return RootAgent()

    @pytest.mark.asyncio
    async def test_agent_response_time_baseline(self, root_agent, test_db_session, sample_user):
        """Test baseline response time for agent processing."""
        response_times = []

        with patch('agents.root.agent.get_db_session') as mock_db:
            mock_db.return_value.__aenter__.return_value = test_db_session

            test_messages = [
                "Hello",
                "How am I doing?",
                "What's my progress?",
                "Show me analytics"
            ]

            for message in test_messages:
                start_time = time.time()

                try:
                    response = await root_agent.process_message(
                        message=message,
                        user_id=sample_user["telegram_id"]
                    )
                    end_time = time.time()
                    response_time = end_time - start_time
                    response_times.append(response_time)

                    # Assert response time under 1 second for baseline
                    assert response_time < 1.0, f"Response too slow: {response_time}s for message: {message}"

                except Exception as e:
                    pytest.fail(f"Agent processing failed for message '{message}': {e}")

        # Calculate statistics
        avg_time = mean(response_times)
        median_time = median(response_times)

        # Assert average response time under 500ms
        assert avg_time < 0.5, f"Average response time too slow: {avg_time}s"
        assert median_time < 0.5, f"Median response time too slow: {median_time}s"

    @pytest.mark.asyncio
    async def test_meal_calculation_performance(self):
        """Test performance of meal nutrition calculations."""
        calculator = MealNutritionCalculatorTool()
        response_times = []

        # Test with various meal sizes
        test_cases = [
            # Small meal
            {"parsed_items": [{"description": "1 apple", "quantity": 1.0, "parsed_food": "apple", "confidence": 0.9}]},
            # Medium meal
            {"parsed_items": [
                {"description": "2 eggs", "quantity": 2.0, "parsed_food": "eggs", "confidence": 0.9},
                {"description": "1 cup rice", "quantity": 1.0, "parsed_food": "rice", "confidence": 0.85}
            ]},
            # Large meal
            {"parsed_items": [
                {"description": "200g chicken breast", "quantity": 200.0, "parsed_food": "chicken breast", "confidence": 0.9},
                {"description": "1 cup rice", "quantity": 1.0, "parsed_food": "rice", "confidence": 0.85},
                {"description": "1 cup broccoli", "quantity": 1.0, "parsed_food": "broccoli", "confidence": 0.8},
                {"description": "1 tbsp olive oil", "quantity": 1.0, "parsed_food": "olive oil", "confidence": 0.9}
            ]}
        ]

        for test_case in test_cases:
            start_time = time.time()

            result = await calculator.execute(
                parsed_items=test_case["parsed_items"],
                meal_type="lunch",
                user_id="perf_test_user"
            )

            end_time = time.time()
            response_time = end_time - start_time
            response_times.append(response_time)

            # Assert calculation completes within 200ms
            assert response_time < 0.2, f"Meal calculation too slow: {response_time}s"
            assert result.success, f"Meal calculation failed: {result.error}"

        # Assert performance scales reasonably
        small_time = response_times[0]
        large_time = response_times[2]
        # Large meal should not be more than 3x slower than small meal
        assert large_time < small_time * 3, f"Performance scaling issue: small={small_time}s, large={large_time}s"

    @pytest.mark.asyncio
    async def test_workout_volume_performance(self):
        """Test performance of workout volume calculations."""
        calculator = VolumeCalculatorTool()
        response_times = []

        # Test with various workout sizes
        test_cases = [
            # Single exercise
            {"parsed_exercises": [{"exercise_name": "push-ups", "sets": 3, "reps": 15}]},
            # Medium workout
            {"parsed_exercises": [
                {"exercise_name": "bench press", "sets": 3, "reps": 10, "weight": 80.0},
                {"exercise_name": "squats", "sets": 4, "reps": 8, "weight": 100.0}
            ]},
            # Large workout
            {"parsed_exercises": [
                {"exercise_name": "bench press", "sets": 4, "reps": 10, "weight": 80.0},
                {"exercise_name": "squats", "sets": 4, "reps": 8, "weight": 100.0},
                {"exercise_name": "deadlifts", "sets": 3, "reps": 5, "weight": 120.0},
                {"exercise_name": "pull-ups", "sets": 3, "reps": 8},
                {"exercise_name": "planks", "sets": 3, "reps": 1, "weight": None}  # Time-based
            ]}
        ]

        for test_case in test_cases:
            start_time = time.time()

            result = await calculator.execute(
                parsed_exercises=test_case["parsed_exercises"],
                user_id="perf_test_user"
            )

            end_time = time.time()
            response_time = end_time - start_time
            response_times.append(response_time)

            # Assert calculation completes within 100ms
            assert response_time < 0.1, f"Volume calculation too slow: {response_time}s"
            assert result.success, f"Volume calculation failed: {result.error}"

        # Assert performance is consistent
        avg_time = mean(response_times)
        assert avg_time < 0.05, f"Average volume calculation time too slow: {avg_time}s"


class TestConcurrentLoadPerformance:
    """Test performance under concurrent load."""

    @pytest.mark.asyncio
    async def test_concurrent_agent_requests(self, test_db_session, sample_user):
        """Test handling multiple concurrent agent requests."""
        agent = RootAgent()
        num_concurrent_requests = 10

        with patch('agents.root.agent.get_db_session') as mock_db:
            mock_db.return_value.__aenter__.return_value = test_db_session

            async def single_request(request_id):
                start_time = time.time()
                try:
                    response = await agent.process_message(
                        message=f"Hello from request {request_id}",
                        user_id=f"user_{request_id}"
                    )
                    end_time = time.time()
                    return end_time - start_time, response
                except Exception as e:
                    return None, str(e)

            # Execute concurrent requests
            start_time = time.time()
            tasks = [single_request(i) for i in range(num_concurrent_requests)]
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time

            # Analyze results
            response_times = [r[0] for r in results if r[0] is not None]
            errors = [r[1] for r in results if r[0] is None]

            # Assert no errors occurred
            assert len(errors) == 0, f"Concurrent requests failed: {errors}"

            # Assert all requests completed
            assert len(response_times) == num_concurrent_requests

            # Assert reasonable total time (should be much less than sequential)
            max_expected_time = max(response_times) * 2  # Allow some overhead
            assert total_time < max_expected_time, f"Concurrent execution too slow: {total_time}s"

            # Assert individual response times are reasonable
            for i, response_time in enumerate(response_times):
                assert response_time < 1.0, f"Request {i} too slow: {response_time}s"

    @pytest.mark.asyncio
    async def test_database_connection_pooling(self, test_db_session):
        """Test database connection pooling under load."""
        # This test ensures database connections are properly pooled
        # and don't exhaust resources under concurrent load

        async def db_operation(user_id):
            async with get_db_session() as session:
                # Simulate a simple database operation
                await asyncio.sleep(0.01)  # Small delay to simulate work
                return f"Operation completed for {user_id}"

        num_operations = 20

        start_time = time.time()
        tasks = [db_operation(f"user_{i}") for i in range(num_operations)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Assert all operations completed
        assert len(results) == num_operations
        assert all("completed" in r for r in results)

        # Assert reasonable total time
        assert total_time < 1.0, f"Database operations too slow: {total_time}s"


class TestMemoryAndResourceUsage:
    """Test memory usage and resource consumption."""

    @pytest.mark.asyncio
    async def test_memory_usage_growth(self):
        """Test that memory usage doesn't grow unbounded with repeated operations."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        agent = RootAgent()

        # Perform many operations
        num_operations = 100

        with patch('agents.root.agent.get_db_session') as mock_db:
            mock_db.return_value.__aenter__.return_value = None  # Mock session

            for i in range(num_operations):
                await agent.process_message(
                    message=f"Test message {i}",
                    user_id="memory_test_user"
                )

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory

        # Assert memory growth is reasonable (less than 50MB for 100 operations)
        assert memory_growth < 50, f"Excessive memory growth: {memory_growth}MB"

    @pytest.mark.asyncio
    async def test_no_resource_leaks(self):
        """Test that resources are properly cleaned up."""
        # This is a basic test - in a real scenario, you'd use specialized
        # tools to detect resource leaks

        agent = RootAgent()
        initial_object_count = len(agent.__dict__) if hasattr(agent, '__dict__') else 0

        # Perform operations
        with patch('agents.root.agent.get_db_session') as mock_db:
            mock_db.return_value.__aenter__.return_value = None

            for i in range(50):
                await agent.process_message(
                    message=f"Test message {i}",
                    user_id="resource_test_user"
                )

        final_object_count = len(agent.__dict__) if hasattr(agent, '__dict__') else 0

        # Object count should not grow significantly
        growth = final_object_count - initial_object_count
        assert growth < 10, f"Potential resource leak: object count grew by {growth}"


class TestScalabilityBenchmarks:
    """Benchmark tests for scalability assessment."""

    @pytest.mark.asyncio
    async def test_throughput_benchmark(self):
        """Benchmark maximum throughput of the system."""
        agent = RootAgent()
        num_requests = 50

        with patch('agents.root.agent.get_db_session') as mock_db:
            mock_db.return_value.__aenter__.return_value = None

            async def benchmark_request(request_id):
                start_time = time.time()
                await agent.process_message(
                    message=f"Benchmark request {request_id}",
                    user_id=f"bench_user_{request_id}"
                )
                end_time = time.time()
                return end_time - start_time

            # Execute benchmark
            start_time = time.time()
            tasks = [benchmark_request(i) for i in range(num_requests)]
            response_times = await asyncio.gather(*tasks)
            total_time = time.time() - start_time

            # Calculate throughput metrics
            throughput = num_requests / total_time  # requests per second
            avg_response_time = mean(response_times)
            p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]

            # Assert minimum performance standards
            assert throughput > 10, f"Throughput too low: {throughput} req/s"
            assert avg_response_time < 0.2, f"Average response time too high: {avg_response_time}s"
            assert p95_response_time < 0.5, f"P95 response time too high: {p95_response_time}s"

    @pytest.mark.asyncio
    async def test_load_sustainability(self):
        """Test that the system can sustain load over time."""
        agent = RootAgent()
        duration_seconds = 10
        target_rps = 5  # Target requests per second

        with patch('agents.root.agent.get_db_session') as mock_db:
            mock_db.return_value.__aenter__.return_value = None

            request_count = 0
            start_time = time.time()
            end_time = start_time + duration_seconds

            async def sustained_request():
                nonlocal request_count
                while time.time() < end_time:
                    await agent.process_message(
                        message=f"Sustained request {request_count}",
                        user_id="sustained_user"
                    )
                    request_count += 1
                    await asyncio.sleep(1.0 / target_rps)  # Control request rate

            # Run sustained load
            await sustained_request()

            actual_duration = time.time() - start_time
            actual_rps = request_count / actual_duration

            # Assert sustained performance
            assert actual_rps >= target_rps * 0.8, f"Sustained RPS too low: {actual_rps}"
            assert request_count > duration_seconds * target_rps * 0.8, f"Too few requests completed: {request_count}"