# Weight Loss Chat Agent: Technical Clarifications & Implementation Details

**Document Version:** 1.0  
**Last Updated:** November 16, 2025  
**Purpose:** Detailed technical specifications for all components

---

## Table of Contents

1. [API Integration Specifications](#api-integration-specifications)
2. [Database Schema Definition](#database-schema-definition)
3. [Tool Function Specifications](#tool-function-specifications)
4. [Nudge Agent Scheduling Configuration](#nudge-agent-scheduling-configuration)
5. [Guardrail Implementation Details](#guardrail-implementation-details)
6. [Session State Structure](#session-state-structure)
7. [Error Handling & User Messages](#error-handling--user-messages)
8. [Testing Data & Golden Sets](#testing-data--golden-sets)
9. [Configuration Management](#configuration-management)
10. [Deployment Configuration](#deployment-configuration)

---

## API Integration Specifications

### 1. USDA FoodData Central API

#### Endpoint Reference

```
Base URL: https://api.nal.usda.gov/fdc/v1/

Main Endpoints:
1. GET /foods/search       - Search for foods by keywords
2. GET /food/{fdcId}       - Get detailed nutrition for one food
3. GET /foods              - Get details for multiple foods by FDC IDs
4. GET /foods/list         - Get paginated list of foods
```

#### Food Search Endpoint

```
METHOD: GET or POST
URL: https://api.nal.usda.gov/fdc/v1/foods/search

REQUIRED PARAMETERS:
- api_key (string): **will share the key later, leave a placeholder in config file and add this to gitignore**

OPTIONAL PARAMETERS:
- query (string): Search term (e.g., "eggs", "chicken breast")
- pageSize (integer): Results per page (default: 25, max: 200)
- pageNumber (integer): Page number (0-indexed)
- sortBy (string): Sort order (relevance [default], dataType)
- sortOrder (string): asc | desc (default: desc)

AUTHENTICATION: API key in query parameter
Example: ?api_key=YOUR_API_KEY

EXAMPLE REQUEST:
curl "https://api.nal.usda.gov/fdc/v1/foods/search?api_key=DEMO_KEY&query=eggs&pageSize=10"

RESPONSE FORMAT (JSON):
{
  "foods": [
    {
      "fdcId": "168143",
      "description": "Egg, chicken, raw, whole",
      "dataType": "Survey (FNDDS)",
      "foodNutrients": [
        {
          "nutrientId": 203,
          "nutrientName": "Protein",
          "unitName": "g",
          "value": 13.6,
          "derivationCode": "LCCD"
        },
        {
          "nutrientId": 208,
          "nutrientName": "Energy",
          "unitName": "kcal",
          "value": 155,
          "derivationCode": "LCCD"
        },
        {
          "nutrientId": 204,
          "nutrientName": "Total lipid (fat)",
          "unitName": "g",
          "value": 11.6
        }
      ]
    }
  ],
  "totalHits": 150,
  "currentPage": 0,
  "totalPages": 15
}

KEY NUTRIENT IDs TO EXTRACT:
- 203 = Protein (grams)
- 204 = Total Fat (grams)
- 205 = Carbohydrate (grams)
- 208 = Energy/Calories (kcal)
- 262 = Caffeine (mg)
- 269 = Sugars (grams)
```

#### Food Details Endpoint

```
METHOD: GET
URL: https://api.nal.usda.gov/fdc/v1/food/{fdcId}

EXAMPLE: https://api.nal.usda.gov/fdc/v1/food/168143?api_key=DEMO_KEY

RESPONSE: Same as above but for single food with all nutrient details
```

#### Implementation Pattern

```python
import aiohttp
import asyncio
from typing import Dict, List, Optional

class USDAFDCClient:
    """USDA FoodData Central API client"""
    
    BASE_URL = "https://api.nal.usda.gov/fdc/v1"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def search_food(
        self,
        query: str,
        page_size: int = 10,
        timeout: int = 5
    ) -> Dict[str, any]:
        """
        Search for foods by keyword
        
        Args:
            query: Food search term (e.g., "eggs")
            page_size: Results per page (10-200)
            timeout: Request timeout in seconds
        
        Returns:
            {
                "status": "success" | "error",
                "foods": [
                    {
                        "fdc_id": "168143",
                        "name": "Egg, chicken, raw, whole",
                        "calories": 155,
                        "protein": 13.6,
                        "fat": 11.6,
                        "carbs": 1.1,
                        "confidence": 0.95
                    }
                ],
                "total_hits": 150
            }
        """
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        params = {
            "api_key": self.api_key,
            "query": query,
            "pageSize": page_size
        }
        
        try:
            async with asyncio.timeout(timeout):
                async with self.session.get(
                    f"{self.BASE_URL}/foods/search",
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "status": "success",
                            "foods": [self._parse_food(f) for f in data.get("foods", [])],
                            "total_hits": data.get("totalHits", 0)
                        }
                    else:
                        return {
                            "status": "error",
                            "error": f"HTTP {response.status}",
                            "message": f"USDA API returned error: {response.status}"
                        }
        
        except asyncio.TimeoutError:
            return {
                "status": "error",
                "error": "timeout",
                "message": "USDA API request timed out after 5 seconds"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(type(e).__name__),
                "message": f"Failed to query USDA API: {str(e)}"
            }
    
    @staticmethod
    def _parse_food(food_data: Dict) -> Dict:
        """Extract nutrition data from USDA response"""
        
        nutrients = {}
        
        # Map nutrient IDs to names
        nutrient_map = {
            203: "protein",
            204: "fat",
            205: "carbs",
            208: "calories"
        }
        
        for nutrient in food_data.get("foodNutrients", []):
            nutrient_id = nutrient.get("nutrientId")
            if nutrient_id in nutrient_map:
                nutrients[nutrient_map[nutrient_id]] = nutrient.get("value", 0)
        
        return {
            "fdc_id": food_data.get("fdcId"),
            "name": food_data.get("description", "Unknown"),
            "calories": int(nutrients.get("calories", 0)),
            "protein": round(nutrients.get("protein", 0), 1),
            "fat": round(nutrients.get("fat", 0), 1),
            "carbs": round(nutrients.get("carbs", 0), 1),
            "confidence": 0.95  # USDA data is highly reliable
        }
    
    async def close(self):
        if self.session:
            await self.session.close()
```

#### Rate Limiting & Quotas

```
RATE LIMITS:
- Free tier: 1,200 requests per hour (20 requests/minute)
- No quota exhaustion for registered users

HANDLING:
- Implement exponential backoff (1s, 2s, 4s)
- Check response headers for rate limit info
- Cache results for 24 hours to reduce calls
```

---

### 2. Nutritionix API (Fallback)

#### Endpoint Reference

```
Base URL: https://www.nutritionix.com/api/v2/

Main Endpoints:
1. POST /search/instant - Quick search (instant suggestions)
2. GET /search/item     - Detailed search by UPC or item ID
3. POST /natural/nutrients - Parse natural language food descriptions
```

#### Instant Search Endpoint

```
METHOD: POST
URL: https://www.nutritionix.com/api/v2/search/instant

NO AUTHENTICATION REQUIRED (free)

PARAMETERS (JSON body):
{
  "query": "eggs",
  "detailed": false,
  "limit": 10
}

OPTIONAL PARAMETERS:
- detailed (boolean): Include full nutrient fields (default: false)
- branded_region (integer): 1=US, 2=UK (default: 1)
- common (boolean): Include common foods (default: true)

RESPONSE FORMAT:
{
  "common": [
    {
      "nix_item_id": "51c549ff97c3e6efadd60294",
      "food_name": "Egg",
      "nf_calories": 70,
      "nf_protein": 6,
      "nf_total_fat": 5,
      "nf_total_carbohydrate": 1,
      "serving_unit": "medium",
      "serving_weight_grams": 44
    }
  ],
  "branded": [
    {
      "nix_item_id": "51c54aff97c3e6efadd64c57",
      "food_name": "Eggland's Best - Eggs",
      "nf_calories": 70,
      ...
    }
  ]
}

IMPLEMENTATION:
async def search_nutritionix(query: str) -> Dict:
    async with aiohttp.ClientSession() as session:
        payload = {
            "query": query,
            "detailed": False,
            "limit": 5
        }
        
        try:
            async with asyncio.timeout(3):  # Faster timeout than USDA
                async with session.post(
                    "https://www.nutritionix.com/api/v2/search/instant",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "status": "success",
                            "foods": data.get("common", []) + data.get("branded", []),
                            "confidence": 0.80  # Slightly lower than USDA
                        }
        except asyncio.TimeoutError:
            return {"status": "error", "error": "timeout"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
```

#### Fallback Logic

```python
async def lookup_nutrition_with_fallback(
    food_description: str
) -> Dict:
    """
    Try USDA first, then Nutritionix, then local database
    
    This is the orchestration pattern to use
    """
    
    # Try 1: USDA
    usda_result = await usda_client.search_food(food_description)
    if usda_result["status"] == "success":
        return usda_result
    
    logger.warning(f"USDA API failed: {usda_result.get('error')}")
    
    # Try 2: Nutritionix
    nutritionix_result = await search_nutritionix(food_description)
    if nutritionix_result["status"] == "success":
        return nutritionix_result
    
    logger.warning(f"Nutritionix API failed: {nutritionix_result.get('error')}")
    
    # Try 3: Local database
    local_result = query_local_food_db(food_description)
    if local_result:
        return {
            "status": "success",
            "foods": [local_result],
            "confidence": 0.60  # Lower confidence for local DB
        }
    
    # All failed
    return {
        "status": "error",
        "error": "all_apis_failed",
        "message": "Could not find nutritional data. Please estimate calories."
    }
```

---

### 3. Google Gemini API Configuration

#### Model Configuration

```python
import google.generativeai as genai

# Configuration for Gemini 2.5 Flash (MVP)
GEMINI_CONFIG = {
    "model": "gemini-2.5-flash",  # Fastest + cheapest
    
    "generation_config": {
        "temperature": 0.7,        # Moderate creativity (not 0, not high)
        "top_p": 0.95,             # Nucleus sampling
        "top_k": 40,               # Top-k sampling
        "max_output_tokens": 1024, # Limit response length
        "response_mime_type": "text/plain"
    },
    
    "safety_settings": [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        }
    ]
}

# Initialize client
genai.configure(api_key=os.getenv("GOOGLE_GENAI_API_KEY"))

# Create model with config
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config=GEMINI_CONFIG["generation_config"],
    safety_settings=GEMINI_CONFIG["safety_settings"]
)

# Usage in agent
async def generate_response(prompt: str) -> str:
    """Generate response with timeout and error handling"""
    
    try:
        # Timeout: 30 seconds max
        response = await asyncio.wait_for(
            asyncio.to_thread(
                model.generate_content,
                prompt
            ),
            timeout=30
        )
        
        return response.text
    
    except asyncio.TimeoutError:
        logger.error("Gemini API timeout (>30 sec)")
        return "Response generation timed out. Please try again."
    
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return "System error generating response. Please try again."
```

#### Parameter Guidance

| Parameter | MVP Value | Explanation |
|-----------|-----------|-------------|
| **temperature** | 0.7 | Moderate creativity (0=deterministic, 2=max randomness) |
| **top_p** | 0.95 | 95% of probability mass (0.9-0.95 typical) |
| **top_k** | 40 | Consider top 40 tokens (40-100 typical) |
| **max_output_tokens** | 1024 | Keep responses concise (<2KB) |
| **response_mime_type** | text/plain | Plain text, not JSON for MVP |

#### Cost Tracking

```python
# Track API usage for cost monitoring
class GeminiCostTracker:
    """Monitor Gemini API costs"""
    
    # Pricing (as of Nov 2025)
    PRICE_PER_1M_INPUT = 0.075   # USD per 1M tokens
    PRICE_PER_1M_OUTPUT = 0.30   # USD per 1M output tokens
    
    async def track_usage(self, prompt: str, response: str) -> Dict:
        """Estimate cost of API call"""
        
        # Rough estimate (actual tokens counted server-side)
        input_tokens = len(prompt.split()) * 1.3
        output_tokens = len(response.split()) * 1.3
        
        input_cost = (input_tokens / 1_000_000) * self.PRICE_PER_1M_INPUT
        output_cost = (output_tokens / 1_000_000) * self.PRICE_PER_1M_OUTPUT
        total_cost = input_cost + output_cost
        
        logger.info(f"Gemini API usage - Input: {input_tokens:.0f} tokens, Output: {output_tokens:.0f} tokens, Cost: ${total_cost:.6f}")
        
        # Store in database for monthly billing
        db.api_usage.insert({
            "provider": "gemini",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": total_cost,
            "timestamp": datetime.now()
        })
        
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": total_cost
        }
```

#### Rate Limiting & Quotas

```
FREE TIER (MVP):
- 60 requests per minute
- 1500 requests per day
- No per-month quota

PAID TIER (Post-MVP):
- Higher quotas with billing

HANDLING:
- Implement exponential backoff
- Queue requests if exceeding rate limit
- Cache common responses (morning nudge, focus goals)
```

---

## Database Schema Definition

### SQLite Table Structures

```sql
-- 1. USERS TABLE
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    telegram_user_id INTEGER UNIQUE NOT NULL,
    first_name TEXT,
    last_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP,
    consent_gdpr BOOLEAN DEFAULT 0,  -- GDPR consent
    consent_data_processing BOOLEAN DEFAULT 0,
    deleted_at TIMESTAMP,  -- Soft delete for GDPR
    INDEX idx_telegram_user_id (telegram_user_id)
);

-- 2. PROFILES TABLE
CREATE TABLE profiles (
    profile_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    age INTEGER CHECK(age >= 18 AND age <= 120),
    height_cm DECIMAL(5, 2),  -- Centimeters
    current_weight_kg DECIMAL(5, 2),
    target_weight_kg DECIMAL(5, 2),
    activity_level TEXT DEFAULT 'moderate',  -- sedentary, light, moderate, active
    daily_calorie_goal INTEGER DEFAULT 1500,
    daily_protein_goal_g INTEGER DEFAULT 120,
    daily_water_goal_oz INTEGER DEFAULT 64,
    daily_steps_goal INTEGER DEFAULT 10000,
    timezone TEXT DEFAULT 'UTC',
    preferences_json TEXT,  -- JSON: {nudge_times, units, etc}
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_user_id (user_id)
);

-- 3. SESSIONS TABLE
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_data TEXT NOT NULL,  -- JSON: {batch, logs, streak, etc}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_user_id (user_id),
    INDEX idx_expires_at (expires_at)
);

-- 4. DAILY_LOGS TABLE (Nutrition)
CREATE TABLE daily_logs_nutrition (
    log_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    meal_type TEXT NOT NULL,  -- breakfast, lunch, dinner, snack
    food_items TEXT NOT NULL,  -- JSON: [{name, quantity, calories, protein}]
    total_calories INTEGER,
    total_protein_g DECIMAL(5, 1),
    total_carbs_g DECIMAL(5, 1),
    total_fat_g DECIMAL(5, 1),
    confidence DECIMAL(3, 2),  -- 0.0-1.0
    notes TEXT,
    created_at TIMESTAMP NOT NULL,
    log_date DATE NOT NULL,  -- User's local date
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_user_date (user_id, log_date),
    INDEX idx_created_at (created_at)
);

-- 5. DAILY_LOGS TABLE (Fitness)
CREATE TABLE daily_logs_fitness (
    log_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    exercises TEXT NOT NULL,  -- JSON: [{name, sets, reps, weight_lbs, form_tips}]
    total_volume INTEGER,  -- Total sets × reps across session
    session_duration_min INTEGER,
    body_parts TEXT,  -- JSON: ["chest", "triceps"]
    notes TEXT,
    created_at TIMESTAMP NOT NULL,
    log_date DATE NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_user_date (user_id, log_date)
);

-- 6. DAILY_LOGS TABLE (Wellness)
CREATE TABLE daily_logs_wellness (
    log_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    water_intake_oz INTEGER,
    sleep_duration_hours DECIMAL(3, 1),
    sleep_quality_1_10 INTEGER CHECK(sleep_quality_1_10 >= 1 AND sleep_quality_1_10 <= 10),
    steps_count INTEGER,
    notes TEXT,
    created_at TIMESTAMP NOT NULL,
    log_date DATE NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_user_date (user_id, log_date),
    UNIQUE(user_id, log_date)  -- One wellness log per day
);

-- 7. CONVERSATIONS TABLE (Emotional Context)
CREATE TABLE conversations (
    message_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    user_message TEXT NOT NULL,
    agent_response TEXT,
    sentiment_score DECIMAL(3, 2),  -- -1.0 to 1.0
    emotion TEXT,  -- positive, neutral, negative, guilt, frustration, crisis
    alert_level TEXT,  -- none, low, medium, high, critical
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_user_created (user_id, created_at)
);

-- 8. NUDGES TABLE (Tracking sent nudges)
CREATE TABLE nudges (
    nudge_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    nudge_type TEXT NOT NULL,  -- morning, midday, evening, weekly, streak, focus
    message_text TEXT,
    scheduled_time TIMESTAMP,
    sent_time TIMESTAMP,
    delivery_status TEXT DEFAULT 'pending',  -- pending, sent, failed, opened
    focus_goal TEXT,  -- Goal highlighted (for focus nudges)
    snooze_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_user_type (user_id, nudge_type),
    INDEX idx_scheduled_time (scheduled_time)
);

-- 9. STREAKS TABLE (Logging streaks)
CREATE TABLE streaks (
    streak_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    current_streak_days INTEGER DEFAULT 1,
    longest_streak_days INTEGER DEFAULT 1,
    last_log_date DATE,
    streak_broken_count INTEGER DEFAULT 0,  -- Times streak was broken
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    UNIQUE(user_id)  -- One streak record per user
);

-- 10. API_USAGE TABLE (Cost tracking)
CREATE TABLE api_usage (
    usage_id TEXT PRIMARY KEY,
    user_id TEXT,  -- NULL for system-level calls
    provider TEXT NOT NULL,  -- gemini, usda, nutritionix
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost DECIMAL(8, 6),
    status TEXT,  -- success, error, timeout
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_provider_date (provider, created_at)
);

-- 11. BATCH_STATES TABLE (Temporary batch collection)
CREATE TABLE batch_states (
    batch_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    batch_type TEXT NOT NULL,  -- meal, workout, hydration
    items_json TEXT NOT NULL,  -- JSON: [{item data}]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,  -- 30 min timeout
    status TEXT DEFAULT 'active',  -- active, processing, completed
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_user_status (user_id, status),
    INDEX idx_expires_at (expires_at)
);
```

### Data Types & Constraints

| Field | Type | Constraints | Purpose |
|-------|------|-------------|---------|
| user_id | TEXT | PRIMARY KEY | Unique user identifier |
| calories | INTEGER | NOT NULL, >=0 | Never negative |
| age | INTEGER | 18-120 | Valid age range |
| weight_kg | DECIMAL(5,2) | >=30, <=300 | Reasonable weight |
| confidence | DECIMAL(3,2) | 0.0-1.0 | Probability score |
| log_date | DATE | NOT NULL | User's local date |

### Migration Strategy

```python
# Use Alembic for database migrations (lightweight)
from alembic import op
import sqlalchemy as sa

def upgrade():
    """Add new column"""
    op.add_column(
        'profiles',
        sa.Column('timezone', sa.String(50), nullable=False, default='UTC')
    )

def downgrade():
    """Remove column"""
    op.drop_column('profiles', 'timezone')
```

---

## Tool Function Specifications

### Function Signature Template

```python
from typing import Dict, List, Optional, Any
from google.adk.tools import ToolContext

async def tool_name(
    param1: str,
    param2: int,
    tool_context: Optional[ToolContext] = None
) -> Dict[str, Any]:
    """
    One-line summary of what tool does.
    
    Detailed description. Explain edge cases, guardrails, fallback behavior.
    
    Args:
        param1 (str): Description of param1
        param2 (int): Description of param2, valid range, constraints
        tool_context (ToolContext, optional): ADK-provided context
    
    Returns:
        dict: {
            "status": "success" | "error" | "warning",
            "data": {...},
            "confidence": float,
            "error_message": str (if status != success),
            "metadata": {...}
        }
    
    Raises:
        ValueError: If parameters invalid
        asyncio.TimeoutError: If operation exceeds timeout
    
    Example:
        >>> result = await tool_name("test", 42)
        >>> result["status"]
        "success"
    
    Guardrails:
        - Input must be non-empty
        - Max timeout: 5 seconds
        - Confidence must be 0.0-1.0
    """
    
    # PHASE 1: Input Validation
    if not param1 or len(param1) < 3:
        raise ValueError("param1 too short (<3 chars)")
    
    if param2 < 0 or param2 > 1000:
        raise ValueError(f"param2 out of range: {param2}")
    
    try:
        # PHASE 2: Main Logic with Timeout
        result = await asyncio.wait_for(
            _do_work(param1, param2),
            timeout=5
        )
        
        return {
            "status": "success",
            "data": result,
            "confidence": 0.95,
            "metadata": {"param1": param1, "param2": param2}
        }
    
    except asyncio.TimeoutError:
        logger.warning(f"Timeout for {param1}")
        return {
            "status": "error",
            "error": "timeout",
            "message": "Operation exceeded 5 second timeout"
        }
    
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return {
            "status": "error",
            "error": "validation",
            "message": str(e)
        }
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            "status": "error",
            "error": "unexpected",
            "message": "System error occurred"
        }
```

### Tool Function Examples

#### Parse Meal Batch Tool

```python
async def parse_meal_batch(
    food_items: List[str],
    meal_type: str,
    user_id: str,
    tool_context: Optional[ToolContext] = None
) -> Dict[str, Any]:
    """
    Parse a complete meal batch and lookup nutrition.
    
    Args:
        food_items: List of food descriptions (e.g., ["2 eggs", "1 toast"])
        meal_type: "breakfast" | "lunch" | "dinner" | "snack"
        user_id: User ID for personalization
        tool_context: ADK context
    
    Returns:
        {
            "status": "success",
            "meal_type": "breakfast",
            "foods": [
                {"name": "eggs", "quantity": "2 large", "calories": 140, "protein": 12, "confidence": 0.95},
                {"name": "toast", "quantity": "1 slice", "calories": 120, "protein": 4, "confidence": 0.90}
            ],
            "totals": {"calories": 260, "protein": 16},
            "confidence": 0.93
        }
    """
    
    # Validation
    if not food_items or len(food_items) == 0:
        return {"status": "error", "message": "Empty food list"}
    
    if len(food_items) > 10:
        return {"status": "error", "message": "Too many items (max 10)"}
    
    parsed_foods = []
    total_cal = 0
    total_protein = 0
    confidences = []
    
    for food_item in food_items:
        try:
            # Lookup nutrition (with fallback chain)
            nutrition = await lookup_nutrition_with_fallback(food_item)
            
            if nutrition["status"] == "success":
                food_data = nutrition["foods"][0]
                parsed_foods.append(food_data)
                
                total_cal += food_data.get("calories", 0)
                total_protein += food_data.get("protein", 0)
                confidences.append(food_data.get("confidence", 0.5))
            
            else:
                # Flag individual item lookup failure
                parsed_foods.append({
                    "name": food_item,
                    "calories": 0,
                    "protein": 0,
                    "confidence": 0,
                    "error": "lookup_failed"
                })
        
        except Exception as e:
            logger.error(f"Parse error for {food_item}: {e}")
            parsed_foods.append({
                "name": food_item,
                "error": str(e)
            })
    
    # Calculate average confidence
    avg_confidence = (sum(confidences) / len(confidences)) if confidences else 0.0
    
    # Guardrail: Flag unusual values
    warnings = []
    if total_cal > 1500:
        warnings.append("High calorie meal (>1500), verify accuracy")
    if total_cal < 100:
        warnings.append("Low calorie meal (<100), missing items?")
    
    return {
        "status": "success",
        "meal_type": meal_type,
        "foods": parsed_foods,
        "totals": {
            "calories": total_cal,
            "protein": round(total_protein, 1)
        },
        "confidence": round(avg_confidence, 2),
        "warnings": warnings
    }
```

#### Detect Sentiment Tool

```python
async def detect_sentiment(
    message: str,
    tool_context: Optional[ToolContext] = None
) -> Dict[str, Any]:
    """
    Detect user emotional state and alert level.
    
    Args:
        message: User's message
        tool_context: ADK context
    
    Returns:
        {
            "sentiment": "positive" | "neutral" | "negative" | "crisis",
            "score": -1.0 to 1.0,
            "emotion": "motivation" | "frustration" | "guilt" | "despair",
            "alert_level": "none" | "low" | "medium" | "high" | "critical",
            "recommended_action": str
        }
    """
    
    msg_lower = message.lower()
    
    # CRISIS DETECTION (highest priority)
    crisis_keywords = ["kill myself", "end it", "no point", "give up"]
    if any(keyword in msg_lower for keyword in crisis_keywords):
        return {
            "sentiment": "crisis",
            "score": -1.0,
            "emotion": "despair",
            "alert_level": "critical",
            "recommended_action": "ESCALATE_TO_HUMAN_IMMEDIATELY"
        }
    
    # Negative emotions (moderate)
    negative_keywords = ["ugh", "frustrated", "annoyed", "disappointed", "hate"]
    if any(keyword in msg_lower for keyword in negative_keywords):
        return {
            "sentiment": "negative",
            "score": -0.6,
            "emotion": "frustration",
            "alert_level": "medium",
            "recommended_action": "NORMALIZE_AND_ENCOURAGE"
        }
    
    # Positive emotions
    positive_keywords = ["awesome", "great", "love", "proud", "nailed"]
    if any(keyword in msg_lower for keyword in positive_keywords):
        return {
            "sentiment": "positive",
            "score": 0.8,
            "emotion": "motivation",
            "alert_level": "none",
            "recommended_action": "CELEBRATE"
        }
    
    # Default: neutral
    return {
        "sentiment": "neutral",
        "score": 0.0,
        "emotion": "neutral",
        "alert_level": "none",
        "recommended_action": "CONTINUE_NORMALLY"
    }
```

---

## Nudge Agent Scheduling Configuration

### APScheduler Setup

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import pytz

class NudgeSchedulerService:
    """Manages autonomous nudge scheduling"""
    
    def __init__(self, telegram_bot):
        self.scheduler = AsyncIOScheduler()
        self.telegram_bot = telegram_bot
    
    def start(self):
        """Start scheduler"""
        self.scheduler.start()
        self._register_nudge_jobs()
    
    def _register_nudge_jobs(self):
        """Register all scheduled nudge jobs"""
        
        # 1. MORNING NUDGE (07:00 every day)
        self.scheduler.add_job(
            self._execute_morning_nudge,
            CronTrigger(hour=7, minute=0, timezone='UTC'),
            id='nudge_morning',
            name='Morning Motivational Nudge',
            replace_existing=True,
            max_instances=1  # Prevent duplicate execution
        )
        
        # 2. MIDDAY NUDGE (12:00 every day)
        self.scheduler.add_job(
            self._execute_midday_nudge,
            CronTrigger(hour=12, minute=0, timezone='UTC'),
            id='nudge_midday',
            name='Midday Activity Check',
            replace_existing=True,
            max_instances=1
        )
        
        # 3. EVENING NUDGE (19:00 every day)
        self.scheduler.add_job(
            self._execute_evening_nudge,
            CronTrigger(hour=19, minute=0, timezone='UTC'),
            id='nudge_evening',
            name='Evening Focus Goal',
            replace_existing=True,
            max_instances=1
        )
        
        # 4. WEEKLY REPORT (Sunday 18:00)
        self.scheduler.add_job(
            self._execute_weekly_report,
            CronTrigger(day_of_week=6, hour=18, minute=0, timezone='UTC'),
            id='nudge_weekly',
            name='Weekly Synthesis Report',
            replace_existing=True,
            max_instances=1
        )
        
        # 5. STREAK PROTECTION (23:55 every day)
        self.scheduler.add_job(
            self._execute_streak_protection,
            CronTrigger(hour=23, minute=55, timezone='UTC'),
            id='nudge_streak',
            name='Streak Protection Nudge',
            replace_existing=True,
            max_instances=1
        )
        
        # 6. FOCUS GOAL (06:00 every day)
        self.scheduler.add_job(
            self._execute_focus_goal,
            CronTrigger(hour=6, minute=0, timezone='UTC'),
            id='nudge_focus',
            name='Daily Focus Goal',
            replace_existing=True,
            max_instances=1
        )
```

### Cron Expression Reference

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (0 = Sunday)
│ │ │ │ │
│ │ │ │ │
* * * * *

EXAMPLES FOR NUDGES:

07:00 every day:        CronTrigger(hour=7, minute=0)
12:00 every day:        CronTrigger(hour=12, minute=0)
19:00 every day:        CronTrigger(hour=19, minute=0)
23:55 every day:        CronTrigger(hour=23, minute=55)
18:00 Sunday only:      CronTrigger(day_of_week=6, hour=18, minute=0)
```

### Focus Goal Selection Algorithm

```python
async def select_focus_goal(user_id: str) -> Dict:
    """
    Select ONE goal with lowest adherence in past 7 days.
    Rotate daily to prevent burnout.
    
    Returns:
        {
            "selected_goal": "protein_intake" | "water_intake" | "steps" | etc,
            "adherence_percent": 45,
            "reason": "Lowest adherence this week"
        }
    """
    
    # Get last 7 days of logs
    logs = db.daily_logs.find({
        "user_id": user_id,
        "log_date": {"$gte": datetime.now().date() - timedelta(days=7)}
    })
    
    # Calculate adherence per goal
    goals = {
        "calories": _calculate_calorie_adherence(logs),
        "protein": _calculate_protein_adherence(logs),
        "water": _calculate_water_adherence(logs),
        "steps": _calculate_steps_adherence(logs),
        "workouts": _calculate_workout_adherence(logs),
        "sleep": _calculate_sleep_adherence(logs)
    }
    
    # Sort by lowest adherence
    sorted_goals = sorted(goals.items(), key=lambda x: x[1])
    
    # Check if goal was focused yesterday
    yesterday_focus = db.nudges.find_one({
        "user_id": user_id,
        "nudge_type": "focus",
        "created_at": {"$gte": datetime.now() - timedelta(hours=24)}
    })
    
    # Select goal (skip if was yesterday's focus)
    for goal_name, adherence in sorted_goals:
        if yesterday_focus and yesterday_focus.get("focus_goal") == goal_name:
            continue  # Skip, pick next lowest
        
        return {
            "selected_goal": goal_name,
            "adherence_percent": adherence,
            "reason": f"Lowest adherence this week ({adherence}%)"
        }
    
    # Fallback: rotate alphabetically
    return {
        "selected_goal": sorted(goals.keys())[0],
        "adherence_percent": goals[sorted(goals.keys())[0]],
        "reason": "Rotated by date"
    }
```

### Timezone Handling

```python
from datetime import datetime
import pytz

def adjust_nudge_time_for_user_timezone(
    user_id: str,
    nudge_type: str,
    default_time: str  # "07:00"
) -> str:
    """
    Convert nudge time from UTC to user's timezone.
    
    Example:
    - User in PST (UTC-8): 07:00 UTC → 23:00 previous day PST
    - Adjust to user's preferred time if customized
    """
    
    # Get user's timezone preference
    user_profile = db.profiles.find_one({"user_id": user_id})
    user_tz = pytz.timezone(user_profile.get("timezone", "UTC"))
    
    # Parse default time
    default_hour, default_minute = map(int, default_time.split(":"))
    
    # Convert to user's timezone
    utc_time = datetime.now(pytz.UTC).replace(hour=default_hour, minute=default_minute)
    user_time = utc_time.astimezone(user_tz)
    
    return user_time.strftime("%H:%M")
```

---

## Guardrail Implementation Details

### Validation Thresholds

```python
class GuardrailThresholds:
    """All validation thresholds in one place"""
    
    # Age & Demographics
    AGE_MIN = 18
    AGE_MAX = 100
    
    # Weight & Height
    WEIGHT_MIN_KG = 30
    WEIGHT_MAX_KG = 300
    HEIGHT_MIN_CM = 100
    HEIGHT_MAX_CM = 250
    
    # Calorie Ranges
    CALORIE_MIN_PER_MEAL = 50    # Extremely light meal
    CALORIE_MAX_PER_MEAL = 2000  # Very large meal
    CALORIE_DAILY_MIN = 800      # Dangerously low
    CALORIE_DAILY_MAX = 5000     # Dangerously high
    CALORIE_SAFE_DEFICIT = 500   # Safe daily deficit
    CALORIE_MAX_DEFICIT = 1000   # Maximum recommended deficit
    
    # Protein
    PROTEIN_MIN_G = 0
    PROTEIN_MAX_G = 300  # Per meal
    
    # Water
    WATER_MIN_DAILY_OZ = 8       # Bare minimum
    WATER_MAX_DAILY_OZ = 300     # Excessive (possible overhydration)
    WATER_WARNING_HIGH_OZ = 200  # Alert above this
    
    # Sleep
    SLEEP_MIN_HOURS = 4          # Unhealthy minimum
    SLEEP_MAX_HOURS = 12         # Excessive
    SLEEP_QUALITY_MIN = 1
    SLEEP_QUALITY_MAX = 10
    
    # Steps
    STEPS_MIN = 0
    STEPS_MAX = 100000           # Unrealistic
    STEPS_GOAL_DEFAULT = 10000
    STEPS_WARNING_LOW = 1000     # Very sedentary day
    
    # Confidence Score
    CONFIDENCE_LOW_THRESHOLD = 0.75      # Show warning if below
    CONFIDENCE_MEDIUM_THRESHOLD = 0.60   # Show uncertainty range
    CONFIDENCE_HIGH_THRESHOLD = 0.85     # Show with confidence
    
    # Batch Processing
    BATCH_MAX_ITEMS = 10
    BATCH_TIMEOUT_MIN = 30
    
    # Logging Frequency
    LOGS_MAX_PER_DAY = 20  # Flag if suspicious
    
    # Streak
    STREAK_BREAK_THRESHOLD_HOURS = 24
```

### Validation Implementation

```python
class GuardrailValidator:
    """Validates all inputs against guardrails"""
    
    def validate_calorie_entry(self, calories: int) -> Dict:
        """Validate calorie entry"""
        
        if calories < 0:
            return {
                "valid": False,
                "error": "negative_value",
                "message": "Calories can't be negative",
                "suggested_value": abs(calories)
            }
        
        if calories > GuardrailThresholds.CALORIE_MAX_PER_MEAL:
            return {
                "valid": False,
                "error": "implausibly_high",
                "message": f"{calories} calories seems too high for one meal",
                "action": "ask_for_confirmation",
                "suggested_range": f"50-{GuardrailThresholds.CALORIE_MAX_PER_MEAL}"
            }
        
        if calories < GuardrailThresholds.CALORIE_MIN_PER_MEAL:
            return {
                "valid": False,
                "error": "implausibly_low",
                "message": f"{calories} calories seems too low",
                "action": "ask_for_clarification",
                "hint": "Did you forget items?"
            }
        
        return {"valid": True}
    
    def validate_confidence_score(self, score: float) -> bool:
        """Validate confidence is 0.0-1.0"""
        
        if not (0.0 <= score <= 1.0):
            logger.error(f"Invalid confidence score: {score}")
            return False
        
        return True
    
    def get_confidence_qualifier(self, confidence: float) -> str:
        """Get user-friendly confidence message"""
        
        if confidence >= GuardrailThresholds.CONFIDENCE_HIGH_THRESHOLD:
            return "High confidence estimate"
        elif confidence >= GuardrailThresholds.CONFIDENCE_MEDIUM_THRESHOLD:
            return "Rough estimate (may vary)"
        else:
            return "Low confidence - consider providing more detail"

# Usage
validator = GuardrailValidator()

# Validate user input
result = validator.validate_calorie_entry(5000)
if not result["valid"]:
    # Show user-friendly error message
    print(result["message"])
```

### Confidence Thresholding

```python
def calculate_food_confidence(
    api_source: str,
    exact_match: bool,
    quantity_specified: bool
) -> float:
    """
    Calculate confidence score for nutrition estimate
    
    Confidence factors:
    - API source: USDA (0.95) > Nutritionix (0.80) > Local (0.60)
    - Exact match vs fuzzy
    - Quantity specified vs estimated
    """
    
    # Base confidence from source
    source_confidence = {
        "usda": 0.95,
        "nutritionix": 0.80,
        "local": 0.60
    }
    
    confidence = source_confidence.get(api_source, 0.50)
    
    # Adjust for match type
    if not exact_match:
        confidence *= 0.90  # Reduce by 10% for fuzzy match
    
    # Adjust for quantity
    if not quantity_specified:
        confidence *= 0.85  # Reduce by 15% if quantity unclear
    
    return round(confidence, 2)

# Show confidence to user
confidence = calculate_food_confidence("usda", True, True)
if confidence < 0.75:
    user_message = f"Approximately {calories} cal (rough estimate)"
else:
    user_message = f"{calories} calories"
```

---

## Session State Structure

### Complete Session Data Model

```python
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class SessionState:
    """Complete session state structure"""
    
    def __init__(self, user_id: str, profile_data: Dict):
        self.user_id = user_id
        
        # User profile (immutable during session)
        self.user_profile = {
            "id": user_id,
            "age": profile_data.get("age"),
            "height_cm": profile_data.get("height_cm"),
            "weight_kg": profile_data.get("weight_kg"),
            "target_weight_kg": profile_data.get("target_weight_kg"),
            "daily_calorie_goal": profile_data.get("daily_calorie_goal", 1500),
            "daily_protein_goal_g": profile_data.get("daily_protein_goal_g", 120),
            "daily_water_goal_oz": profile_data.get("daily_water_goal_oz", 64),
            "daily_steps_goal": profile_data.get("daily_steps_goal", 10000),
            "timezone": profile_data.get("timezone", "UTC")
        }
        
        # Current batch collection state
        self.current_batch = {
            "active": False,
            "type": None,  # "meal", "workout", "hydration"
            "items": [],  # List of collected items
            "started_at": None,
            "batch_id": None
        }
        
        # Today's logs aggregated
        self.today_logs = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "nutrition": {
                "meals": [],  # List of meal batches
                "total_calories": 0,
                "total_protein_g": 0,
                "remaining_calories": self.user_profile["daily_calorie_goal"]
            },
            "fitness": {
                "workouts": [],
                "total_volume": 0,
                "session_count": 0
            },
            "wellness": {
                "water_oz": 0,
                "sleep_hours": 0,
                "sleep_quality": 0,
                "steps": 0
            }
        }
        
        # Emotional context (30-day rolling window)
        self.emotional_history = [
            # {
            #   "timestamp": "2025-11-16T10:30:00Z",
            #   "sentiment_score": 0.5,
            #   "emotion": "neutral",
            #   "message": "..."
            # }
        ]
        
        # Streak data
        self.streak_data = {
            "current_streak": 0,
            "longest_streak": 0,
            "last_log_date": None,
            "days_since_break": 0
        }
        
        # Nudge preferences
        self.nudge_preferences = {
            "morning_enabled": True,
            "morning_time": "07:00",
            "midday_enabled": True,
            "midday_time": "12:00",
            "evening_enabled": True,
            "evening_time": "19:00",
            "weekly_enabled": True,
            "weekly_day": "Sunday",
            "weekly_time": "18:00",
            "streak_protection_enabled": True,
            "snoozed_until": None
        }
        
        # Session metadata
        self.metadata = {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
            "message_count": 0
        }
    
    def to_dict(self) -> Dict:
        """Convert to serializable dict"""
        return {
            "user_id": self.user_id,
            "user_profile": self.user_profile,
            "current_batch": self.current_batch,
            "today_logs": self.today_logs,
            "emotional_history": self.emotional_history[-30:],  # Last 30
            "streak_data": self.streak_data,
            "nudge_preferences": self.nudge_preferences,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SessionState":
        """Restore from dict"""
        session = cls(data["user_id"], data["user_profile"])
        session.current_batch = data.get("current_batch", session.current_batch)
        session.today_logs = data.get("today_logs", session.today_logs)
        session.emotional_history = data.get("emotional_history", [])
        session.streak_data = data.get("streak_data", session.streak_data)
        session.nudge_preferences = data.get("nudge_preferences", session.nudge_preferences)
        session.metadata = data.get("metadata", session.metadata)
        return session
```

### Session Persistence

```python
import json
from datetime import datetime

class SessionPersistence:
    """Handle session save/load"""
    
    def save_session(self, session: SessionState) -> bool:
        """Save session to database"""
        
        try:
            session_data = session.to_dict()
            
            # Store in database
            db.sessions.update_one(
                {"session_id": session.user_id},
                {
                    "$set": {
                        "session_data": json.dumps(session_data),
                        "last_updated": datetime.now(),
                        "expires_at": datetime.now() + timedelta(hours=24)
                    }
                },
                upsert=True  # Insert if doesn't exist
            )
            
            logger.info(f"Session saved for user {session.user_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False
    
    def load_session(self, user_id: str) -> Optional[SessionState]:
        """Load session from database"""
        
        try:
            record = db.sessions.find_one({
                "session_id": user_id,
                "expires_at": {"$gte": datetime.now()}  # Not expired
            })
            
            if record:
                session_data = json.loads(record["session_data"])
                return SessionState.from_dict(session_data)
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None
    
    def auto_save_interval(self, session: SessionState, interval_sec: int = 60):
        """Periodically save session (every 60 sec)"""
        
        async def save_loop():
            while True:
                await asyncio.sleep(interval_sec)
                self.save_session(session)
        
        return asyncio.create_task(save_loop())
```

---

## Error Handling & User Messages

### Standard Error Codes

```python
class ErrorCode:
    """Standard error codes for consistent handling"""
    
    # API Errors
    API_TIMEOUT = "api_timeout"
    API_RATE_LIMIT = "api_rate_limit"
    API_INVALID_RESPONSE = "api_invalid_response"
    API_NOT_FOUND = "api_not_found"
    
    # Validation Errors
    VALIDATION_INVALID_INPUT = "validation_invalid_input"
    VALIDATION_OUT_OF_RANGE = "validation_out_of_range"
    VALIDATION_MISSING_FIELD = "validation_missing_field"
    
    # System Errors
    DATABASE_ERROR = "database_error"
    TIMEOUT_ERROR = "timeout_error"
    UNEXPECTED_ERROR = "unexpected_error"
    
    # Business Logic Errors
    BATCH_EMPTY = "batch_empty"
    BATCH_EXPIRED = "batch_expired"
    BATCH_TOO_LARGE = "batch_too_large"
    INSUFFICIENT_DATA = "insufficient_data"

class ErrorMessage:
    """User-friendly error messages"""
    
    MESSAGES = {
        "api_timeout": "System is a bit slow. Please try again in a moment.",
        "api_rate_limit": "Too many requests. Let's wait a minute and try again.",
        "validation_invalid_input": "I didn't understand that. Could you rephrase?",
        "batch_empty": "Oops! No items in batch. Start over?",
        "database_error": "System error. Your data is safe. Try again?",
        "timeout_error": "Request took too long. Please try again.",
        "unexpected_error": "Something unexpected happened. My apologies! Try again?"
    }
    
    @classmethod
    def get_user_message(cls, error_code: str) -> str:
        """Get user-friendly message for error code"""
        return cls.MESSAGES.get(error_code, "System error. Try again?")
```

### Logging Strategy

```python
import logging
from logging.handlers import RotatingFileHandler

# Configure logging (privacy-first)
logger = logging.getLogger("weight_loss_agent")
logger.setLevel(logging.INFO)

# Don't log sensitive data
SENSITIVE_PATTERNS = [
    "calorie", "protein", "weight", "meal", "food", "password", "api_key"
]

def safe_log(message: str, **kwargs) -> str:
    """Remove sensitive data before logging"""
    
    msg = message
    for pattern in SENSITIVE_PATTERNS:
        # Replace values after sensitive keys
        msg = msg.replace(f"{pattern}=", f"{pattern}=***")
    
    return msg

# Log levels
logger.debug("Debug: detailed information")      # Development only
logger.info("Info: general information")         # Normal flow
logger.warning("Warning: something unexpected")  # Guardrail triggered
logger.error("Error: something failed")          # Tool error
logger.critical("Critical: system failure")      # Database down, etc

# Example
logger.info("User logged meal batch")  # ✅ OK
# logger.info(f"Logged {food_items} with {calories} cal")  # ❌ NO - sensitive
```

---

## Testing Data & Golden Sets

### Test User Profiles

```python
TEST_USERS = {
    "user_normal": {
        "age": 30,
        "height_cm": 175,
        "weight_kg": 85,
        "target_weight_kg": 75,
        "daily_calorie_goal": 1800,
        "daily_protein_goal_g": 150,
        "timezone": "UTC"
    },
    "user_petite": {
        "age": 25,
        "height_cm": 155,
        "weight_kg": 55,
        "target_weight_kg": 50,
        "daily_calorie_goal": 1500,
        "daily_protein_goal_g": 100,
        "timezone": "UTC"
    },
    "user_athlete": {
        "age": 35,
        "height_cm": 190,
        "weight_kg": 95,
        "target_weight_kg": 85,
        "daily_calorie_goal": 2500,
        "daily_protein_goal_g": 200,
        "timezone": "UTC"
    }
}
```

### Mock API Responses

```python
# Mock USDA API response
MOCK_USDA_RESPONSE = {
    "foods": [
        {
            "fdcId": "168143",
            "description": "Egg, chicken, raw, whole",
            "foodNutrients": [
                {"nutrientId": 203, "nutrientName": "Protein", "value": 13.6},
                {"nutrientId": 208, "nutrientName": "Energy", "value": 155},
                {"nutrientId": 204, "nutrientName": "Total lipid (fat)", "value": 11.6}
            ]
        }
    ],
    "totalHits": 1
}

# Mock Gemini API response
MOCK_GEMINI_RESPONSE = "You've logged 2 eggs + toast = 260 cal, 14g protein ✅ You're 200 cal under goal today!"
```

### Golden Test Cases with Expected Data

```python
GOLDEN_TEST_CASES = [
    {
        "id": "test_simple_meal",
        "name": "Log simple breakfast",
        "user_input": "Had 2 eggs and toast",
        "expected_steps": [
            {
                "step": "1: Parse input",
                "expected": "Intent recognized as meal logging"
            },
            {
                "step": "2: Ask confirmation",
                "expected": "Bot asks 'Anything else?'"
            },
            {
                "step": "3: User confirms",
                "input": "That's all",
                "expected": "Bot processes batch"
            },
            {
                "step": "4: Lookup nutrition",
                "expected": "USDA returns: Eggs 70 cal/each, Toast 120 cal/slice"
            },
            {
                "step": "5: Calculate totals",
                "expected": "260 cal, 14g protein"
            },
            {
                "step": "6: Return to user",
                "expected": "Logged ✅ 260 cal, 14g protein. 1200 cal remaining today!"
            }
        ],
        "golden_metrics": {
            "confidence": ">0.85",
            "latency_sec": "<3",
            "success": True
        }
    }
]
```

---

## Configuration Management

### Environment Variables Schema

```bash
# .env.example (copy to .env and fill in values)

# Google Cloud
GOOGLE_CLOUD_PROJECT=weight-loss-agent-prod
GOOGLE_CLOUD_LOCATION=us-central1

# LLM Configuration
LLM_MODEL=gemini-2.5-flash
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=1024

# APIs
GOOGLE_GENAI_API_KEY=your_api_key_here
USDA_FDC_API_KEY=your_usda_key_here
NUTRITIONIX_API_ID=your_nutritionix_id
NUTRITIONIX_API_KEY=your_nutritionix_key

# Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyzABCDEFGhi
TELEGRAM_ADMIN_USER_ID=987654321

# Database
DATABASE_URL=sqlite:///./weight_loss_app.db

# Features
ENABLE_EMOTIONAL_CONTEXT=true
ENABLE_RAG=true
ENABLE_NUDGE_AGENT=true

# Scheduling
NUDGE_MORNING_TIME=07:00
NUDGE_MIDDAY_TIME=12:00
NUDGE_EVENING_TIME=19:00
NUDGE_WEEKLY_TIME=18:00
NUDGE_STREAK_PROTECTION_TIME=23:55
NUDGE_FOCUS_GOAL_TIME=06:00

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log

# Environment
ENVIRONMENT=development  # development, staging, production
```

### Configuration Validation

```python
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    """Configuration with validation"""
    
    # Google Cloud
    google_cloud_project: str
    google_cloud_location: str = "us-central1"
    
    # LLM
    llm_model: str = "gemini-2.5-flash"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1024
    
    # APIs
    google_genai_api_key: str
    usda_fdc_api_key: str
    telegram_bot_token: str
    
    # Database
    database_url: str = "sqlite:///./weight_loss_app.db"
    
    # Features
    enable_emotional_context: bool = True
    enable_rag: bool = True
    enable_nudge_agent: bool = True
    
    # Validation
    @validator('llm_temperature')
    def temperature_range(cls, v):
        if not (0 <= v <= 2):
            raise ValueError("Temperature must be 0-2")
        return v
    
    @validator('llm_max_tokens')
    def max_tokens_range(cls, v):
        if v > 8192:
            raise ValueError("Max tokens limited to 8192")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Load and validate
settings = Settings()
```

---

## Deployment Configuration

### Dockerfile

```dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user for security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (for webhooks)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run application
CMD ["python", "-m", "uvicorn", "telegram_bot.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Cloud Run Deployment

```bash
#!/bin/bash

# Configuration
PROJECT_ID="weight-loss-agent-prod"
REGION="us-central1"
SERVICE_NAME="weight-loss-agent"
IMAGE_NAME="weight-loss-agent:latest"

# Build and push
docker build -t gcr.io/$PROJECT_ID/$IMAGE_NAME .
docker push gcr.io/$PROJECT_ID/$IMAGE_NAME

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$IMAGE_NAME \
  --platform managed \
  --region $REGION \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 100 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID" \
  --env-vars-file .env.prod \
  --allow-unauthenticated
```

### Environment Variables for Production

```env
# .env.prod (Secure version for Cloud Run)

# Use Google Secret Manager for sensitive values
GOOGLE_GENAI_API_KEY=projects/12345/secrets/gemini-key/versions/latest
USDA_FDC_API_KEY=projects/12345/secrets/usda-key/versions/latest
TELEGRAM_BOT_TOKEN=projects/12345/secrets/telegram-token/versions/latest

# Other config
ENVIRONMENT=production
LOG_LEVEL=WARNING  # Less verbose in prod
DATABASE_URL=sqlite:///./weight_loss_app.db  # Local to Cloud Run instance
```

---

**Document Status:** ✅ Complete, Ready for Implementation  
**Version:** 1.0  
**Created:** November 16, 2025  
**All sections fully detailed with code examples, API specs, and configuration.**