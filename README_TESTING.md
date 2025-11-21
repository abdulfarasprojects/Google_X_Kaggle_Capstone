# Weight Loss Tracker Agent - Testing Framework

This comprehensive testing framework evaluates the Weight Loss Tracker Agent's accuracy, performance, robustness, and coverage across all components.

## 🧪 Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Shared pytest fixtures and configuration
├── golden_datasets/           # Expected input/output test data
│   ├── nutrition_golden.json  # 50+ nutrition parsing test cases
│   ├── fitness_golden.json    # 50+ fitness parsing test cases
│   ├── wellness_golden.json   # 30+ wellness parsing test cases
│   ├── analytics_golden.json  # 20+ analytics test cases
│   └── general_golden.json    # 30+ general interaction test cases
├── unit/                      # Unit tests for individual components
│   ├── test_intent_classifier.py
│   ├── test_sentiment_detector.py
│   ├── test_nutrition_tools.py
│   ├── test_fitness_tools.py
│   ├── test_wellness_tools.py
│   └── test_profile_response_tools.py
├── integration/               # Integration tests for component interaction
│   └── test_agents.py
├── e2e/                       # End-to-end workflow tests
│   └── test_workflows.py
└── performance/               # Performance and load tests
    └── test_performance.py
```

## 🎯 Test Categories

### Unit Tests
- **Intent Classification**: Message routing accuracy
- **Sentiment Detection**: User emotion analysis
- **Nutrition Tools**: Food parsing, calculation, storage
- **Fitness Tools**: Exercise parsing, volume calculation
- **Wellness Tools**: Sleep/water/steps parsing, correlations
- **Profile & Response Tools**: Input validation, response formatting

### Integration Tests
- **Agent Communication**: Inter-agent message passing
- **Database Integration**: Data persistence and retrieval
- **API Integration**: External service mocking and validation

### End-to-End Tests
- **User Journeys**: Complete onboarding to progress tracking
- **Data Consistency**: Information accuracy across workflows
- **Error Recovery**: Graceful failure handling

### Performance Tests
- **Response Times**: Sub-second agent responses
- **Concurrent Load**: Multi-user scenario handling
- **Resource Usage**: Memory and connection pooling
- **Scalability**: Throughput and sustained load testing

## 📊 Evaluation Metrics

### Accuracy Metrics
- **Intent Classification**: >90% routing accuracy
- **Nutrition Parsing**: >85% food recognition accuracy
- **Fitness Parsing**: >88% exercise recognition accuracy
- **Wellness Parsing**: >82% metric extraction accuracy

### Performance Metrics
- **Response Time**: <500ms average agent response
- **Throughput**: >50 requests/second
- **Concurrent Users**: Support for 100+ simultaneous users
- **Memory Usage**: <100MB per 1000 requests

### Robustness Metrics
- **Error Recovery**: 99% graceful error handling
- **Input Validation**: 100% malicious input rejection
- **Fallback Handling**: Appropriate responses for edge cases

### Coverage Metrics
- **Code Coverage**: >85% overall coverage
- **Test Case Coverage**: 200+ test cases across all domains
- **Edge Case Coverage**: Comprehensive boundary testing

## 🚀 Running Tests

### Prerequisites
```bash
# Install test dependencies
pip install -r requirements-test.txt

# Install the package in development mode
pip install -e .
```

### Run All Tests
```bash
# Run complete test suite
pytest

# Run with coverage report
pytest --cov=. --cov-report=html

# Run with verbose output
pytest -v
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# End-to-end tests only
pytest tests/e2e/

# Performance tests only
pytest tests/performance/

# Run tests with specific marker
pytest -m "unit"
pytest -m "integration"
pytest -m "e2e"
pytest -m "performance"
```

### Run Tests in Parallel
```bash
# Run tests across multiple CPU cores
pytest -n auto

# Run with 4 workers
pytest -n 4
```

### Generate Coverage Reports
```bash
# HTML coverage report
pytest --cov=. --cov-report=html
open htmlcov/index.html

# Terminal coverage report
pytest --cov=. --cov-report=term-missing

# XML coverage report (for CI/CD)
pytest --cov=. --cov-report=xml
```

## 🏗️ Test Configuration

### pytest.ini
- Asyncio support for concurrent testing
- Coverage configuration with 85% minimum threshold
- Marker definitions for test categorization
- Strict configuration for reliable test execution

### Fixtures (conftest.py)
- **test_db_session**: Isolated SQLite database for each test
- **mock_external_apis**: Mocked USDA, Nutritionix, and Gemini APIs
- **sample_user**: Pre-configured test user data
- **golden_dataset**: Parametrized test data from JSON files

### Golden Datasets
Structured test data containing realistic input/output pairs:
```json
{
  "test_case_id": "nutrition_001",
  "input": "I ate 2 eggs and toast for breakfast",
  "expected_output": {
    "parsed_foods": ["2 eggs", "toast"],
    "total_calories": 280,
    "confidence": 0.9
  },
  "edge_case": false
}
```

## 🔧 Test Development

### Adding New Unit Tests
```python
import pytest
from tools.nutrition.calculator import MealNutritionCalculatorTool

class TestMealCalculator:
    @pytest.mark.asyncio
    async def test_calculate_simple_meal(self):
        calculator = MealNutritionCalculatorTool()

        result = await calculator.execute(
            parsed_items=[{"food": "apple", "quantity": 1}],
            meal_type="snack",
            user_id="test_user"
        )

        assert result.success
        assert result.data["total_calories"] > 0
```

### Adding New Integration Tests
```python
import pytest
from agents.nutrition.agent import NutritionAgent

class TestNutritionAgentIntegration:
    @pytest.mark.asyncio
    async def test_meal_logging_workflow(self, test_db_session, sample_user):
        agent = NutritionAgent()

        with patch('agents.nutrition.agent.get_db_session') as mock_db:
            mock_db.return_value.__aenter__.return_value = test_db_session

            response = await agent.process_message(
                message="I ate chicken for lunch",
                user_id=sample_user["telegram_id"]
            )

            assert "meal" in response.text.lower()
```

### Adding Performance Tests
```python
import pytest
import time

class TestPerformance:
    @pytest.mark.asyncio
    async def test_response_time_under_100ms(self):
        start_time = time.time()

        # Perform operation
        result = await some_async_operation()

        end_time = time.time()
        response_time = end_time - start_time

        assert response_time < 0.1
        assert result.success
```

## 📈 CI/CD Integration

### GitHub Actions Example
```yaml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    - name: Run tests
      run: pytest --cov=. --cov-report=xml
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

## 🐛 Debugging Tests

### Common Issues
1. **Async Test Failures**: Ensure `@pytest.mark.asyncio` decorator
2. **Database Connection Errors**: Use `test_db_session` fixture
3. **API Mocking Issues**: Verify mock return values match expected types
4. **Coverage Gaps**: Run `pytest --cov=. --cov-report=html` and check missing lines

### Debugging Commands
```bash
# Run single test with debug output
pytest tests/unit/test_nutrition_tools.py::TestNutritionCalculatorTool::test_calculate_meal_nutrition_success -v -s

# Run with PDB on failure
pytest --pdb

# Run with detailed tracebacks
pytest --tb=long

# Profile test performance
pytest --durations=10
```

## 📋 Test Maintenance

### Updating Golden Datasets
1. Add new test cases to appropriate JSON files
2. Ensure realistic input/output pairs
3. Update test expectations if behavior changes
4. Validate against real user data patterns

### Code Coverage Goals
- **Statements**: >85%
- **Branches**: >80%
- **Functions**: >90%
- **Lines**: >85%

### Performance Baselines
- **Unit Tests**: <100ms per test
- **Integration Tests**: <500ms per test
- **E2E Tests**: <2s per test
- **Performance Tests**: <10s per test

## 🤝 Contributing

### Test Naming Conventions
- `test_<functionality>_<scenario>_<expected_result>`
- `Test<ClassName>` for test classes
- Descriptive docstrings for all tests

### Test Organization
- Group related tests in classes
- Use fixtures for common setup/teardown
- Parametrize tests with `@pytest.mark.parametrize`
- Mark slow tests with `@pytest.mark.slow`

### Code Quality
- Follow PEP 8 style guidelines
- Add type hints to test functions
- Use descriptive variable names
- Include assertions for all expected behavior

## 📚 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Testing Python Applications](https://testandcode.com/)
- [Google Test Blog](https://testing.googleblog.com/)