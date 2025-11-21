# Weight Loss Tracker - Technical Documentation

This document contains detailed technical information about the implementation, extracted from the main README for clarity.

## Table of Contents
1. [Architecture Deep Dive](#architecture-deep-dive)
2. [Agent Implementation Details](#agent-implementation-details)
3. [Tool System](#tool-system)
4. [Database Schema](#database-schema)
5. [API Integration](#api-integration)
6. [Session Management](#session-management)
7. [Error Handling & Resilience](#error-handling--resilience)
8. [Security & Privacy](#security--privacy)
9. [Testing Strategy](#testing-strategy)
10. [Deployment Guide](#deployment-guide)

---

## Architecture Deep Dive

### Directory Structure
```
weight-loss-agent/
├── agents/                 # Google ADK Agent Implementations
│   ├── root/              # Main orchestrator LlmAgent
│   │   └── agent.py       # Intent routing & conversation management
│   ├── nutrition/         # Meal logging LlmAgent
│   │   ├── agent.py       # Nutrition processing & USDA integration
│   │   └── tools/         # Nutrition-specific tools
│   ├── fitness/           # Workout tracking LlmAgent
│   │   ├── agent.py       # Exercise analysis & progression
│   │   └── tools/         # Fitness calculation tools
│   ├── wellness/          # Health metrics LlmAgent
│   │   ├── agent.py       # Wellness correlations & insights
│   │   └── tools/         # Health analysis tools
│   ├── nudge/             # Reminder system LlmAgent
│   │   ├── agent.py       # Autonomous nudge generation
│   │   └── tools/         # Scheduling & messaging tools
│   └── analytics/         # Progress reporting LlmAgent
│       ├── agent.py       # Trend analysis & summaries
│       └── tools/         # Analytics calculation tools
├── tools/                 # Agent Tool Implementations
│   ├── base.py            # Common tool infrastructure
│   ├── intent_classifier.py # Natural language intent detection
│   ├── sentiment_detector.py # Emotional state analysis
│   ├── response_formatter.py # Structured response generation
│   ├── batch_state_manager.py # Multi-item conversation state
│   ├── nutrition/         # USDA API, parsing, calculations
│   ├── fitness/           # Volume calc, progression tracking
│   ├── wellness/          # Correlation analysis
│   ├── nudge/             # Scheduling, streak analysis
│   └── analytics/         # Progress metrics, trends
├── database/              # SQLite Persistence Layer
│   ├── models.py          # SQLAlchemy ORM models
│   ├── init.py            # Database initialization
│   ├── profile_manager.py # User profile operations
│   ├── meal_manager.py    # Nutrition logging
│   ├── workout_manager.py # Fitness tracking
│   ├── wellness_manager.py # Health metrics
│   ├── nudge_manager.py   # Reminder scheduling
│   └── analytics_manager.py # Progress analytics
├── config/                # Configuration Management
│   ├── settings.py        # Pydantic settings with validation
│   ├── logging.py         # Structured logging system
│   ├── gemini.py          # Google AI client wrapper
│   └── __init__.py        # Package initialization
├── telegram_bot/          # Telegram Integration
│   ├── __init__.py        # Package setup
│   ├── bot.py             # Telegram bot handler & ADK integration
│   └── scheduler.py       # Background job scheduling
├── adk_integration.py     # Google ADK Runner Integration
├── tests/                 # Test Suites
│   ├── unit/              # Unit tests for tools & models
│   ├── integration/       # Agent interaction tests
│   └── e2e/               # End-to-end conversation tests
└── specs/                 # Feature Specifications
    └── 001-weight-loss-agent/
        ├── spec.md        # User stories & requirements
        ├── plan.md        # Technical implementation plan
        ├── tasks.md       # Development task breakdown
        ├── data-model.md  # Database schema design
        └── contracts/     # API specifications
```

### Technology Stack

**Core Framework**
- **Google ADK (Agent Development Kit)**: v1.18+
- **LLM**: Google Gemini 2.5 Flash
- **Language**: Python 3.12+

**Database & Storage**
- **Database**: SQLite with SQLAlchemy ORM
- **Session Management**: Custom SessionState table in SQLite
- **Persistence**: Local file storage (privacy-first design)

**APIs & Services**
- **Messaging**: Telegram Bot API via python-telegram-bot v22+
- **Nutrition Data**: USDA FoodData Central API
- **Fallback Nutrition**: Nutritionix API
- **LLM Provider**: Google Generative AI API

**Infrastructure**
- **Configuration**: Pydantic v2 with environment-based settings
- **Scheduling**: APScheduler for autonomous features
- **Logging**: Structured JSON logging with sanitization
- **Testing**: pytest with asyncio support

---

## Agent Implementation Details

### 1. Root Agent (Coordinator)
**File**: `agents/root/agent.py`

**Purpose**: Main orchestrator that routes messages to specialized agents

**Implementation**:
```python
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from config.gemini import PatchedGemini

root_agent = LlmAgent(
    name="weight_loss_coach_root",
    model=PatchedGemini(model="gemini-2.5-flash"),
    description="Coordinator for weight loss tracking",
    instruction="""
    You are a supportive weight loss coach assistant.
    Route specialized requests to domain agents.
    Handle general conversation and emotional support.
    """,
    tools=[intent_tool, sentiment_tool, response_tool]
)
```

**Responsibilities**:
- Classify user intent using keyword analysis
- Route to appropriate specialized agent
- Handle general conversation
- Provide emotional support and encouragement
- Manage cross-domain concerns

**Routing Logic** (`adk_integration.py`):
```python
def _classify_intent(self, message: str) -> str:
    message_lower = message.lower()

    # Nutrition keywords
    if any(word in message_lower for word in 
           ['ate', 'food', 'meal', 'breakfast', 'calories']):
        return 'nutrition'

    # Fitness keywords
    if any(word in message_lower for word in 
           ['workout', 'exercise', 'gym', 'lift', 'sets']):
        return 'fitness'

    # Wellness keywords
    if any(word in message_lower for word in 
           ['sleep', 'water', 'steps', 'tired']):
        return 'wellness'

    # Analytics keywords
    if any(word in message_lower for word in 
           ['progress', 'stats', 'summary', 'trend']):
        return 'analytics'

    return 'root'  # Default to root agent
```

### 2. Nutrition Agent
**File**: `agents/nutrition/agent.py`

**Purpose**: Process meal logging with nutritional analysis

**Tools**:
- `batch_parser`: Extract multiple food items from text
- `usda_lookup`: Query USDA FoodData Central API
- `nutritionix_lookup`: Fallback nutrition database
- `manual_entry`: Last-resort calorie input
- `meal_storage`: Save to database

**Workflow**:
1. Parse user message for food items
2. Look up nutrition via USDA API
3. Fall back to Nutritionix if USDA fails
4. Request manual entry if both APIs fail
5. Calculate totals (calories, protein, etc.)
6. Store in database with confidence score
7. Return formatted response

**Example Processing**:
```
Input: "I ate breakfast - 2 eggs, toast, and coffee"

1. Parse: ["2 eggs", "toast", "coffee"]
2. USDA lookup:
   - "eggs, whole, raw" → 140 cal, 12g protein
   - "bread, white, toasted" → 160 cal, 6g protein
   - "coffee, brewed" → 5 cal, 0g protein
3. Calculate totals: 305 cal, 18g protein
4. Confidence: 0.95 (high matches)
5. Store in daily_logs_nutrition table
6. Response: "✅ Breakfast logged! 305 cal, 18g protein"
```

### 3. Fitness Agent
**File**: `agents/fitness/agent.py`

**Purpose**: Log workouts with volume tracking and progression

**Tools**:
- `exercise_parser`: Extract exercises, sets, reps, weight
- `volume_calculator`: Calculate training volume
- `progression_suggester`: AI-powered next workout suggestion
- `workout_storage`: Save to database

**Volume Calculation**:
```python
volume = sets × reps × weight

Example:
"3 sets squats at 80kg" = 3 × 10 × 80 = 2400 volume units
```

**Progression Logic**:
- Compare to previous workouts
- Suggest 2.5-5% weight increase
- Track personal records
- Provide form reminders

### 4. Wellness Agent
**File**: `agents/wellness/agent.py`

**Purpose**: Track sleep, water, steps with health correlations

**Tools**:
- `wellness_parser`: Extract sleep/water/steps metrics
- `correlation_analyzer`: Find patterns in data
- `wellness_storage`: Save to database

**Correlation Analysis**:
```python
# Example insights
"Better sleep (8h) correlates with lower calorie intake"
"Days with 10k+ steps show higher water consumption"
"Sleep quality <6 associated with workout skips"
```

### 5. Analytics Agent
**File**: `agents/analytics/agent.py`

**Purpose**: Generate progress reports and trend analysis

**Tools**:
- `progress_calculator`: Aggregate statistics
- `trend_analyzer`: Identify patterns over time
- `hero_stat_generator`: Highlight achievements

**Report Structure**:
```
📊 Weekly Progress (Nov 13-19)

🍎 Nutrition:
- Avg calories: 2150/day (50 under goal)
- Protein avg: 95g/day
- Logged: 6/7 days

💪 Fitness:
- Workouts: 4 sessions
- Volume: +15% vs last week
- PR: Squats 85kg

😴 Wellness:
- Sleep: 7.3h avg
- Water: 6.2 glasses/day
- Steps: 7200/day avg

🏆 Hero Stat: 4-day logging streak!
```

### 6. Nudge Agent
**File**: `agents/nudge/agent.py`

**Purpose**: Autonomous reminders and streak protection

**Tools**:
- `schedule_analyzer`: Determine optimal reminder times
- `nudge_generator`: Create personalized messages
- `streak_tracker`: Monitor logging consistency

**Nudge Types**:
- **Morning**: "Good morning! Ready to log breakfast?"
- **Midday**: "How's your water intake today?"
- **Evening**: "Don't forget to log dinner!"
- **Weekly**: "Time for your weekly progress summary!"
- **Streak Protection**: "You've logged 6 days straight—don't break the streak!"

---

## Tool System

### Tool Categories

**1. Core Tools** (Available to all agents)
- `intent_classifier.py`: Gemini-powered intent detection
- `sentiment_detector.py`: Emotional state analysis
- `response_formatter.py`: Telegram-formatted responses
- `batch_state_manager.py`: Multi-turn conversation handling

**2. Nutrition Tools** (`tools/nutrition/`)
- `batch_parser.py`: Multi-food item extraction
- `usda_client.py`: USDA FoodData Central integration
- `nutritionix_client.py`: Nutritionix API fallback
- `calculator.py`: Calorie and macro calculations
- `manual_entry.py`: User-provided calorie input

**3. Fitness Tools** (`tools/fitness/`)
- `batch_parser.py`: Multi-exercise extraction
- `calculator.py`: Training volume computation
- `progression.py`: Next workout suggestions

**4. Wellness Tools** (`tools/wellness/`)
- `parser.py`: Sleep/water/steps extraction
- `correlations.py`: Health pattern analysis

**5. Analytics Tools** (`tools/analytics/`)
- `calculator.py`: Progress metric aggregation
- `trends.py`: Historical pattern detection
- `hero_stats.py`: Achievement highlighting

**6. Nudge Tools** (`tools/nudge/`)
- `scheduler.py`: Timezone-aware timing
- `generator.py`: Personalized message creation
- `streak_analyzer.py`: Consistency tracking

### Tool Implementation Pattern

**Example: USDA Nutrition Lookup**
```python
# tools/nutrition/usda_client.py
from google.adk.tools import FunctionTool

async def lookup_nutrition_usda(
    food_item: str,
    quantity: float = 1.0,
    unit: str = "serving"
) -> Dict[str, Any]:
    """
    Look up nutritional information from USDA FoodData Central.

    Args:
        food_item: Name of food (e.g., "chicken breast")
        quantity: Amount (default: 1.0)
        unit: Unit of measurement (default: "serving")

    Returns:
        Dictionary with calories, protein, confidence score
    """
    # Implementation
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{USDA_API_BASE}/foods/search",
            params={"query": food_item, "api_key": API_KEY}
        )
        data = response.json()

        # Parse and return
        return {
            "food_name": food_item,
            "calories": calculate_calories(data, quantity),
            "protein_g": calculate_protein(data, quantity),
            "confidence": match_confidence(food_item, data)
        }

# Register as ADK tool
usda_tool = FunctionTool(func=lookup_nutrition_usda)
```

### API Fallback Chain

**Nutrition API Hierarchy**:
```
1. USDA FoodData Central (primary)
   └─ Fails? → 2. Nutritionix API (fallback)
               └─ Fails? → 3. Manual Entry (last resort)
```

**Implementation**:
```python
async def get_nutrition(food_item: str) -> Dict:
    try:
        return await lookup_nutrition_usda(food_item)
    except USDAAPIError:
        logger.warning("USDA failed, trying Nutritionix")
        try:
            return await lookup_nutrition_nutritionix(food_item)
        except NutritionixAPIError:
            logger.error("All APIs failed, requesting manual entry")
            return {"requires_manual_entry": True}
```

---

## Database Schema

### Complete SQLite Schema

The application uses SQLite for persistent storage with 8 tables:

#### 1. UserProfile
**Purpose**: Store user demographics and goals

```sql
CREATE TABLE users (
    user_id VARCHAR PRIMARY KEY,
    age INTEGER NOT NULL CHECK (age >= 18 AND age <= 100),
    height_cm DECIMAL(5,2) NOT NULL CHECK (height_cm >= 100 AND height_cm <= 250),
    weight_kg DECIMAL(5,2) NOT NULL CHECK (weight_kg >= 30 AND weight_kg <= 300),
    target_weight_kg DECIMAL(5,2) NOT NULL CHECK (target_weight_kg < weight_kg),
    activity_level VARCHAR NOT NULL CHECK (activity_level IN 
        ('sedentary', 'light', 'moderate', 'active', 'very_active')),
    daily_calorie_goal INTEGER NOT NULL CHECK (daily_calorie_goal >= 1000 
        AND daily_calorie_goal <= 3000),
    timezone VARCHAR NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Validation Rules**:
- Age: 18-100 years
- Height: 100-250 cm
- Weight: 30-300 kg
- Target weight must be less than current weight
- Activity level: 5 predefined categories
- Calorie goal: 1000-3000 cal/day

#### 2. MealLog
**Purpose**: Track food intake with batch support

```sql
CREATE TABLE daily_logs_nutrition (
    log_id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(user_id),
    meal_type VARCHAR NOT NULL CHECK (meal_type IN 
        ('breakfast', 'lunch', 'dinner', 'snack')),
    food_items TEXT NOT NULL,  -- JSON array of food objects
    total_calories INTEGER NOT NULL CHECK (total_calories > 0),
    total_protein_g DECIMAL(6,2) NOT NULL CHECK (total_protein_g >= 0),
    confidence_score DECIMAL(3,2) NOT NULL CHECK (confidence_score >= 0.0 
        AND confidence_score <= 1.0),
    log_date DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_meal_logs_user_date (user_id, log_date)
);
```

**Food Items JSON Format**:
```json
[
    {
        "name": "eggs, whole, raw",
        "quantity": 2,
        "unit": "large",
        "calories": 140,
        "protein_g": 12,
        "confidence": 0.95
    },
    {
        "name": "bread, white, toasted",
        "quantity": 2,
        "unit": "slice",
        "calories": 160,
        "protein_g": 6,
        "confidence": 0.90
    }
]
```

#### 3. WorkoutLog
**Purpose**: Exercise sessions with progression

```sql
CREATE TABLE daily_logs_fitness (
    log_id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(user_id),
    exercises TEXT NOT NULL,  -- JSON array of exercise objects
    total_volume INTEGER NOT NULL CHECK (total_volume >= 0),
    progression_suggestion TEXT,
    log_date DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_workout_logs_user_date (user_id, log_date)
);
```

**Exercises JSON Format**:
```json
[
    {
        "name": "squats",
        "sets": 3,
        "reps": 10,
        "weight_kg": 80,
        "volume": 2400
    },
    {
        "name": "bench press",
        "sets": 3,
        "reps": 8,
        "weight_kg": 60,
        "volume": 1440
    }
]
```

#### 4. WellnessLog
**Purpose**: Daily wellness metrics

```sql
CREATE TABLE daily_logs_wellness (
    log_id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(user_id),
    sleep_hours DECIMAL(4,2) NOT NULL CHECK (sleep_hours >= 0 
        AND sleep_hours <= 24),
    sleep_quality INTEGER NOT NULL CHECK (sleep_quality >= 1 
        AND sleep_quality <= 10),
    water_glasses DECIMAL(4,2) NOT NULL CHECK (water_glasses >= 0 
        AND water_glasses <= 20),
    steps_count INTEGER NOT NULL CHECK (steps_count >= 0 
        AND steps_count <= 100000),
    log_date DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, log_date),
    INDEX idx_wellness_logs_user_date (user_id, log_date)
);
```

**Constraints**:
- One wellness log per user per day
- Sleep hours: 0-24
- Sleep quality: 1-10 scale
- Water: 0-20 glasses
- Steps: 0-100,000

#### 5. NudgeEvent
**Purpose**: Autonomous reminder scheduling

```sql
CREATE TABLE nudges (
    nudge_id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(user_id),
    nudge_type VARCHAR NOT NULL CHECK (nudge_type IN 
        ('morning', 'midday', 'evening', 'weekly', 'streak_protection')),
    message TEXT NOT NULL,
    scheduled_time DATETIME NOT NULL,
    delivered_at DATETIME,
    status VARCHAR NOT NULL DEFAULT 'scheduled' CHECK (status IN 
        ('scheduled', 'delivered', 'failed', 'cancelled')),
    INDEX idx_nudges_scheduled (scheduled_time),
    INDEX idx_nudges_user_status (user_id, status)
);
```

#### 6. ProgressSummary
**Purpose**: Aggregated analytics

```sql
CREATE TABLE progress_summaries (
    summary_id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(user_id),
    period_type VARCHAR NOT NULL CHECK (period_type IN 
        ('daily', 'weekly', 'monthly')),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL CHECK (period_end >= period_start),
    calories_logged INTEGER DEFAULT 0 CHECK (calories_logged >= 0),
    workouts_completed INTEGER DEFAULT 0 CHECK (workouts_completed >= 0),
    sleep_avg_hours DECIMAL(4,2),
    water_avg_glasses DECIMAL(4,2),
    steps_avg_count INTEGER,
    streak_days INTEGER DEFAULT 0 CHECK (streak_days >= 0),
    hero_stat TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_progress_user_period (user_id, period_type, period_end)
);
```

#### 7. SessionState
**Purpose**: Conversation context and batch processing state

```sql
CREATE TABLE batch_states (
    batch_id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(user_id),
    batch_type VARCHAR CHECK (batch_type IN 
        ('meal', 'workout', 'wellness', 'onboarding', 'greeting', 
         'consent', 'age', 'height', 'weight', 'target_weight', 
         'activity_level', 'review_profile', 'complete')),
    batch_items TEXT,  -- JSON array
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sessions_expires (expires_at)
);
```

**Important**: This table provides **persistent session storage**, NOT in-memory. Sessions survive bot restarts and expire after 24 hours for security.

#### 8. ApiUsage
**Purpose**: Cost monitoring

```sql
CREATE TABLE api_usage (
    usage_id VARCHAR PRIMARY KEY,
    provider VARCHAR NOT NULL,
    endpoint VARCHAR NOT NULL,
    request_count INTEGER NOT NULL DEFAULT 1 CHECK (request_count > 0),
    cost_usd DECIMAL(6,4) NOT NULL DEFAULT 0.0 CHECK (cost_usd >= 0),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_api_usage_provider_date (provider, created_at)
);
```

---

## API Integration

### 1. USDA FoodData Central API

**Endpoint**: `https://api.nal.usda.gov/fdc/v1/foods/search`

**Authentication**: API key in query parameter

**Request Example**:
```python
params = {
    "query": "chicken breast",
    "api_key": USDA_API_KEY,
    "dataType": ["Survey (FNDDS)", "SR Legacy"],
    "pageSize": 5
}
```

**Response Parsing**:
```python
{
    "foods": [
        {
            "fdcId": 171477,
            "description": "Chicken, broiler, breast, meat only, raw",
            "foodNutrients": [
                {"nutrientName": "Energy", "value": 165, "unitName": "KCAL"},
                {"nutrientName": "Protein", "value": 31, "unitName": "G"}
            ]
        }
    ]
}
```

**Challenges & Solutions**:
- **380K+ foods**: Use relevance ranking and confidence scoring
- **Ambiguous names**: Default to most common preparation
- **Missing data**: Fall back to Nutritionix
- **Rate limits**: Implement exponential backoff

### 2. Nutritionix API

**Endpoint**: `https://trackapi.nutritionix.com/v2/natural/nutrients`

**Authentication**: App ID and App Key headers

**Request Example**:
```python
headers = {
    "x-app-id": NUTRITIONIX_APP_ID,
    "x-app-key": NUTRITIONIX_APP_KEY,
    "Content-Type": "application/json"
}

payload = {
    "query": "2 eggs and toast"
}
```

**Advantages over USDA**:
- Natural language processing
- Handles portions better
- Multi-food parsing
- Brand name support

### 3. Google Gemini API

**Used For**:
- Intent classification
- Sentiment analysis
- Response formatting
- Progression suggestions

**Configuration**:
```python
import google.generativeai as genai

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# Example: Intent classification
response = model.generate_content(
    f"Classify this message intent: '{user_message}'\n"
    f"Options: nutrition, fitness, wellness, analytics, general"
)
```

### 4. Telegram Bot API

**Implementation**: `python-telegram-bot` v22+

**Key Handlers**:
```python
from telegram.ext import Application, MessageHandler, CommandHandler

app = Application.builder().token(TELEGRAM_TOKEN).build()

# Handlers
app.add_handler(CommandHandler("start", start_command))
app.add_handler(MessageHandler(filters.TEXT, handle_message))

# Start polling
app.run_polling()
```

---

## Session Management

### SessionState Implementation

**Problem with InMemorySessionService**:
- Data stored in RAM only
- Lost on application restart
- No historical access
- Limited debugging capability

**Solution: SQLite SessionState Table**

**Features**:
1. **Persistent across restarts**
2. **24-hour automatic expiration**
3. **Batch processing support**
4. **Full conversation history**

**Implementation** (`database/models.py`):
```python
class SessionState(Base):
    __tablename__ = "batch_states"

    batch_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.user_id'))
    batch_type = Column(String)  # 'meal', 'workout', etc.
    batch_items = Column(Text)   # JSON array
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Usage Example**:
```python
# Start batch processing
session = SessionState(
    batch_id=f"meal_{user_id}_{timestamp}",
    user_id=user_id,
    batch_type="meal",
    batch_items=json.dumps([]),
    expires_at=datetime.utcnow() + timedelta(hours=24)
)
db.add(session)
db.commit()

# Add items to batch
session.batch_items = json.dumps([
    {"food": "eggs", "quantity": 2},
    {"food": "toast", "quantity": 2}
])
db.commit()

# Complete batch
process_batch(session.batch_items)
db.delete(session)
db.commit()
```

**Cleanup Job**:
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('interval', hours=1)
def cleanup_expired_sessions():
    db = SessionLocal()
    expired = db.query(SessionState).filter(
        SessionState.expires_at < datetime.utcnow()
    ).all()

    for session in expired:
        db.delete(session)

    db.commit()
    db.close()
```

---

## Error Handling & Resilience

### Error Handling Strategy

**1. API Failure Handling**

```python
async def robust_nutrition_lookup(food_item: str) -> Dict:
    """Lookup with fallback chain and graceful degradation."""

    # Try USDA first
    try:
        result = await lookup_nutrition_usda(food_item)
        if result['confidence'] > 0.7:
            return result
    except USDAAPIError as e:
        logger.warning(f"USDA API failed: {e}")

    # Fall back to Nutritionix
    try:
        result = await lookup_nutrition_nutritionix(food_item)
        return result
    except NutritionixAPIError as e:
        logger.warning(f"Nutritionix API failed: {e}")

    # Request manual entry
    return {
        "requires_manual_entry": True,
        "message": "I couldn't find nutrition data. How many calories?"
    }
```

**2. Database Error Handling**

```python
def safe_db_operation(operation):
    """Decorator for safe database operations with retry."""
    @functools.wraps(operation)
    def wrapper(*args, **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return operation(*args, **kwargs)
            except OperationalError as e:
                if attempt == max_retries - 1:
                    logger.error(f"DB operation failed after {max_retries} attempts")
                    raise
                logger.warning(f"DB error, retrying... ({attempt + 1}/{max_retries})")
                time.sleep(0.1 * (2 ** attempt))  # Exponential backoff
    return wrapper

@safe_db_operation
def store_meal_log(meal_data):
    db = SessionLocal()
    log = MealLog(**meal_data)
    db.add(log)
    db.commit()
    db.close()
```

**3. Agent Error Handling**

```python
async def process_with_fallback(user_message: str) -> Dict:
    """Process message with graceful error handling."""
    try:
        # Try normal agent processing
        response = await agent_runner.process_message(
            user_id=user_id,
            message=user_message
        )
        return response

    except GeminiAPIError as e:
        logger.error(f"LLM API error: {e}")
        return {
            "text": "I'm having trouble understanding. Could you rephrase?"
        }

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            "text": "Sorry, something went wrong. Please try again."
        }
```

### Input Validation

**User Input Sanitization**:
```python
def validate_and_sanitize_input(user_input: str) -> str:
    """Validate and clean user input."""

    # Length check
    if len(user_input) > 1000:
        raise ValueError("Message too long (max 1000 characters)")

    # Remove control characters
    cleaned = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', user_input)

    # Strip whitespace
    cleaned = cleaned.strip()

    # Ensure not empty
    if not cleaned:
        raise ValueError("Empty message")

    return cleaned
```

**Database Constraint Validation**:
```python
def validate_user_profile(profile_data: Dict) -> None:
    """Validate user profile before database insertion."""

    if not (18 <= profile_data['age'] <= 100):
        raise ValueError("Age must be 18-100")

    if not (100 <= profile_data['height_cm'] <= 250):
        raise ValueError("Height must be 100-250 cm")

    if profile_data['target_weight_kg'] >= profile_data['weight_kg']:
        raise ValueError("Target weight must be less than current weight")

    if profile_data['activity_level'] not in VALID_ACTIVITY_LEVELS:
        raise ValueError(f"Invalid activity level")
```

---

## Security & Privacy

### Data Protection

**1. Local Storage Only**
- All data stored in SQLite on device
- No cloud synchronization
- No external data sharing
- User controls their data file

**2. PII Sanitization in Logs**

```python
# config/logging.py
def sanitize_log_data(data: Dict) -> Dict:
    """Remove sensitive information from logs."""

    sensitive_fields = {
        'user_id', 'email', 'phone', 'password', 
        'api_key', 'token', 'telegram_id'
    }

    sanitized = {}
    for key, value in data.items():
        if key.lower() in sensitive_fields:
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        else:
            sanitized[key] = value

    return sanitized
```

**3. Session Security**
- 24-hour automatic expiration
- No session sharing between users
- Secure session ID generation

```python
import secrets

def generate_session_id(user_id: str) -> str:
    """Generate cryptographically secure session ID."""
    random_part = secrets.token_urlsafe(16)
    timestamp = datetime.utcnow().isoformat()
    return f"session_{user_id}_{timestamp}_{random_part}"
```

**4. API Key Protection**
- Environment variable storage
- No hardcoded keys
- gitignore for .env files

```python
# config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    telegram_bot_token: str
    google_genai_api_key: str
    usda_fdc_api_key: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

settings = Settings()
```

### GDPR Compliance (Planned)

**Data Portability**:
```python
def export_user_data(user_id: str) -> bytes:
    """Export all user data in JSON format."""
    db = SessionLocal()

    user_data = {
        "profile": db.query(UserProfile).filter_by(user_id=user_id).first(),
        "meals": db.query(MealLog).filter_by(user_id=user_id).all(),
        "workouts": db.query(WorkoutLog).filter_by(user_id=user_id).all(),
        "wellness": db.query(WellnessLog).filter_by(user_id=user_id).all(),
    }

    return json.dumps(user_data, indent=2, cls=AlchemyEncoder).encode()
```

**Right to Deletion**:
```python
def delete_user_data(user_id: str) -> None:
    """Permanently delete all user data (GDPR compliance)."""
    db = SessionLocal()

    # Cascade delete handles related tables
    user = db.query(UserProfile).filter_by(user_id=user_id).first()
    if user:
        db.delete(user)
        db.commit()

    db.close()
    logger.info(f"User data deleted: {user_id}")
```

---

## Testing Strategy

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── golden_datasets/         # Test data
│   ├── nutrition_golden.json
│   ├── fitness_golden.json
│   └── wellness_golden.json
├── unit/                    # Unit tests
│   ├── test_intent_classifier.py
│   ├── test_nutrition_tools.py
│   └── test_database_models.py
├── integration/             # Integration tests
│   ├── test_nutrition_agent.py
│   └── test_agent_routing.py
└── e2e/                     # End-to-end tests
    ├── test_onboarding_flow.py
    └── test_meal_logging_flow.py
```

### Example Unit Test

```python
# tests/unit/test_intent_classifier.py
import pytest
from tools.intent_classifier import classify_intent

@pytest.mark.asyncio
async def test_nutrition_intent_detection():
    """Test intent classification for nutrition queries."""

    test_cases = [
        ("I ate 2 eggs", "nutrition"),
        ("had breakfast", "nutrition"),
        ("logged 500 calories", "nutrition"),
    ]

    for message, expected_intent in test_cases:
        result = await classify_intent(message)
        assert result['intent'] == expected_intent
        assert result['confidence'] > 0.8
```

### Example Integration Test

```python
# tests/integration/test_nutrition_agent.py
import pytest
from agents.nutrition.agent import nutrition_agent

@pytest.mark.asyncio
async def test_meal_processing_with_usda(mock_usda_api):
    """Test full meal processing flow."""

    # Mock USDA API response
    mock_usda_api.return_value = {
        "calories": 140,
        "protein_g": 12,
        "confidence": 0.95
    }

    # Process message
    result = await nutrition_agent.process("I ate 2 eggs")

    # Assertions
    assert "logged" in result['text'].lower()
    assert "140" in result['text']  # Calories mentioned
    assert result['status'] == 'success'
```

### Example E2E Test

```python
# tests/e2e/test_meal_logging_flow.py
import pytest
from adk_integration import process_agent_message

@pytest.mark.asyncio
async def test_complete_meal_logging_flow(test_user, clean_db):
    """Test complete meal logging from user input to database."""

    # User sends message
    response1 = await process_agent_message(
        user_id=test_user.user_id,
        message="I ate breakfast - 2 eggs and toast"
    )

    # Verify response
    assert "breakfast" in response1['text'].lower()
    assert "logged" in response1['text'].lower()

    # Verify database entry
    db = SessionLocal()
    meals = db.query(MealLog).filter_by(
        user_id=test_user.user_id
    ).all()

    assert len(meals) == 1
    assert meals[0].meal_type == "breakfast"
    assert meals[0].total_calories > 0

    db.close()
```

### Test Coverage Goals

**Minimum Requirements**:
- Overall coverage: >80%
- Agent coverage: 100% (all agents tested)
- Tool coverage: 100% (all tools tested)
- Database operations: 100%

**Running Tests**:
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=agents --cov=tools --cov=database --cov-report=html

# Run specific test file
pytest tests/unit/test_intent_classifier.py

# Run with verbose output
pytest -v

# Run only integration tests
pytest tests/integration/
```

---

## Deployment Guide

### Local Development

**1. Environment Setup**
```bash
# Clone repository
git clone <repo-url>
cd weight-loss-agent

# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv --python 3.12
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

# Install dependencies
uv pip install -r requirements.txt
```

**2. Configuration**
```bash
# Copy environment template
cp .env.example .env

# Edit with your API keys
nano .env
```

**3. Database Initialization**
```bash
# Create database tables
python -c "from database.models import init_db; init_db()"

# Verify schema
python -c "from database.models import create_database_schema; print(create_database_schema())"
```

**4. Start Bot**
```bash
# Run bot
python -m telegram_bot.bot

# With debug logging
DEBUG=1 LOG_LEVEL=DEBUG python -m telegram_bot.bot
```

### Production Deployment (Google Cloud Run)

**Coming Soon**: Docker containerization and Cloud Run deployment guide

**Planned Steps**:
1. Create Dockerfile
2. Build container image
3. Push to Google Container Registry
4. Deploy to Cloud Run with environment variables
5. Configure Cloud SQL for production database
6. Set up monitoring and alerting

---

## Performance Optimization

### Caching Strategy

**1. Nutrition Data Caching**
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
async def cached_usda_lookup(food_item: str) -> Dict:
    """Cache USDA API responses to reduce API calls."""
    return await lookup_nutrition_usda(food_item)
```

**2. Session Caching**
```python
from cachetools import TTLCache

session_cache = TTLCache(maxsize=100, ttl=300)  # 5-minute TTL

def get_session_with_cache(session_id: str):
    if session_id in session_cache:
        return session_cache[session_id]

    session = db.query(SessionState).filter_by(
        batch_id=session_id
    ).first()

    session_cache[session_id] = session
    return session
```

### Database Optimization

**1. Indexes**
- All foreign keys indexed
- Common query patterns indexed (user_id + date)
- Composite indexes for analytics queries

**2. Query Optimization**
```python
# Bad: N+1 query problem
for meal in user.meal_logs:
    print(meal.food_items)  # Separate query for each

# Good: Eager loading
meals = db.query(MealLog).filter_by(user_id=user_id).all()
```

**3. Connection Pooling**
```python
from sqlalchemy.pool import StaticPool

engine = create_engine(
    "sqlite:///weight_loss_app.db",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Connection pooling
    echo=False
)
```

---

## Troubleshooting

### Common Issues

**1. ADK Import Errors**
```bash
# Symptom
ImportError: No module named 'google.adk'

# Solution
uv pip install google-adk
python -c "from google.adk.agents import LlmAgent; print('Success')"
```

**2. Database Locked**
```bash
# Symptom
sqlite3.OperationalError: database is locked

# Solution
# Ensure only one bot instance running
pkill -f telegram_bot
python -m telegram_bot.bot
```

**3. USDA API Failures**
```bash
# Symptom
USDAAPIError: 403 Forbidden

# Solution
# Check API key is valid
echo $USDA_FDC_API_KEY
# Try with 'demo' key for testing
```

---

## Appendix

### Environment Variables Reference

```bash
# Required
TELEGRAM_BOT_TOKEN=<from BotFather>
GOOGLE_GENAI_API_KEY=<from AI Studio>
USDA_FDC_API_KEY=<from FoodData Central>

# Optional
NUTRITIONIX_APP_ID=<app id>
NUTRITIONIX_APP_KEY=<app key>
DATABASE_URL=sqlite:///./weight_loss_app.db
DATABASE_ENCRYPT=false
DATABASE_KEY=<encryption key if enabled>
LOG_LEVEL=INFO
DEBUG=false
TELEGRAM_ADMIN_USER_ID=<your telegram user id>
```

### Key Metrics

**Performance Targets**:
- Response time (p95): <3 seconds
- Response time (p99): <5 seconds
- API call success rate: >95%
- Database query time: <100ms

**Quality Targets**:
- Intent classification accuracy: >95%
- Food item extraction accuracy: >90%
- Calorie calculation accuracy: ±10%
- Code coverage: >80%

---

**Document Version**: 1.0  
**Last Updated**: November 20, 2025  
**Status**: Complete

For additional information, see:
- [Executive Summary]
- [Project Journey]
- [[Main README]](https://github.com/abdulfarasprojects/Google_X_Kaggle_Capstone/blob/main/README.md)
