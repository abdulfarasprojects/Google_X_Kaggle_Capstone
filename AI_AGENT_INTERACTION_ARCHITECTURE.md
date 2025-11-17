# How Your Weight Loss Chat Bot Works (Simple Explanation)

## What This System Does

Your weight loss chat bot is like a team of smart helpers working together. It uses Google's AI tools to help people track their food, exercise, and weight loss goals through Telegram messages. Instead of one big AI doing everything, it has different specialists that each handle specific tasks.

## How Everything Connects

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram Bot  │───▶│   ADK Runner    │───▶│   Root Agent    │
│                 │    │                 │    │                 │
│ • Gets messages │    │ • Manages       │    │ • Figures out   │
│   from users    │    │   conversations │    │   what you want │
│ • Sends replies │    │ • Runs AI       │    │ • Batch mode    │
│                 │    │   agents        │    │ • Sends to      │
│                 │    │                 │    │   specialists   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                    ┌──────────────────────────────────┼──────────────────────────────────┐
                    │                                  │                                  │
            ┌──────────────┐                   ┌──────────────┐                   ┌──────────────┐
            │ Food Expert  │                   │ Exercise     │                   │ Wellness     │
            │ Agent        │                   │ Agent        │                   │ Agent        │
            │              │                   │ (Coming Soon) │                   │ (Coming Soon)│
            │ • Counts      │                   │              │                   │              │
            │   calories    │                   │              │                   │              │
            │ • Uses USDA   │                   │              │                   │              │
            │   database    │                   │              │                   │              │
            └──────────────┘                   └──────────────┘                   └──────────────┘
                                                       │
                                               ┌──────────────┐
                                               │ New User     │
                                               │ Setup Agent  │
                                               │              │
                                               │ • Creates     │
                                               │   profiles    │
                                               │ • Asks        │
                                               │   questions   │
                                               │ • Sets goals  │
                                               └──────────────┘
```

## 1. The Telegram Bot (Your Chat Interface)

### How Messages Get Processed

The Telegram bot is like the receptionist at a busy office. It takes messages from users and passes them to the right people:

```python
# telegram_bot/bot.py - Message Handler
async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(user.id)
    text = message.text.strip()

    # Send to AI system
    response = await self.agent_router(user_id, text, context)
    await message.reply_text(response['text'])
```

**What it does:**
- Receives messages from Telegram users
- Gets the user's ID and message text
- Sends everything to the AI system
- Shows typing indicators while working
- Sends back the AI's response

### Special Commands

The bot understands these special commands:
- `/start` - Sets up new users or welcomes back existing ones
- `/help` - Shows what the bot can do
- `/status` - Shows your progress and goals
- `/cancel` - Stops whatever you're doing

### Handling Slow Responses

If the AI takes too long to respond, the bot gives up and tells the user:

```python
# If AI takes too long, stop waiting
response = await asyncio.wait_for(
    self.agent_router(user_id, text, context),
    timeout=settings.bot_response_timeout
)
```

## 2. The ADK System (AI Manager)

### Running the AI Agents

The ADK Runner is like a project manager who coordinates all the AI helpers:

```python
# adk_integration.py
class ADKAgentRunner:
    def __init__(self):
        self.runner = InMemoryRunner(agent=root_agent)

    async def process_message(self, user_id, message, session_id, context):
        events = await self.runner.run_debug(
            user_messages=[message],
            user_id=user_id,
            session_id=session_id,
            verbose=True
        )
        # Get the final answer
        return self._extract_response(events)
```

**What it handles:**
- Keeps track of conversations
- Runs the AI agents
- Collects responses from agents
- Handles errors gracefully

### Remembering Conversations

Each chat gets a unique ID so the system remembers what you talked about:

```python
# Create unique conversation ID
session_id = f"session_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
```

This way, the AI can remember what you said earlier in the conversation.

## 3. The Main AI (Root Agent)

### The Boss AI

The root agent is the main AI that decides what to do with your messages. It's like a smart manager who:

```python
# agents/root/agent.py
root_agent = LlmAgent(
    name="weight_loss_coach_root",
    model=PatchedGemini(model=Config.gemini_model),
    description="Main helper for weight loss tracking on Telegram",
    instruction="""
    You are a friendly, supportive weight loss coach on Telegram.

    YOUR JOBS:
    1. Figure out what the user wants (food logging, questions, progress)
    2. Notice how they're feeling and respond kindly
    3. For multiple food items: Use GROUP MODE
    4. When user says "that's all": Send group to food expert
    5. Direct requests: Food → food_agent, Exercise → exercise_agent, etc.
    6. Combine answers from specialists into one helpful message
    """,
    tools=[intent_tool, sentiment_tool, response_tool, batch_state_tool],
)
```

### Special Tools the Main AI Uses

#### What Do You Want? Tool
```python
async def classify_intent(query: str, context=None, tool_context=None):
    # Figures out what the user is trying to do
    # Returns: {"intent": "nutrition", "confidence": 0.8, "reasoning": "..."}
```

**Types of requests it recognizes:**
- `nutrition` - Logging food and meals
- `fitness` - Tracking workouts and exercise
- `wellness` - Sleep, water, steps, mood
- `analytics` - Progress reports and stats
- `onboarding` - Setting up new user profiles
- `help` - Getting assistance

#### How Are You Feeling? Tool
```python
async def detect_sentiment(query: str, context=None, tool_context=None):
    # Checks the user's mood from their message
    # Returns: {"sentiment": "positive", "emotional_state": "enthusiastic", "confidence": 0.9}
```

#### Message Formatter Tool
```python
async def format_response(response_type, content, user_context=None, context=None, tool_context=None):
    # Makes responses sound natural and helpful
    # Returns: {"formatted_response": "...", "response_type": "nutrition_summary"}
```

#### Group Manager Tool
```python
async def get_batch_state(context=None, tool_context=None):
    # Keeps track of grouped items during logging
    # Returns: {"has_active_batch": true, "batch_type": "meal", "current_items": [...]}
```

### Group Mode for Multiple Items

When you log several foods at once, the AI uses "group mode" to collect everything before processing:

```
You: "I ate 2 eggs"
AI: "2 eggs noted. Anything else for breakfast?"

You: "Also toast and coffee"
AI: "Toast and coffee added. Anything more?"

You: "That's everything"
AI: [Sends complete list to Food Expert]
     [Gets back: 450 calories, 25g protein]
AI: "Breakfast logged! 450 calories, 25g protein ✅"
```

**Group Mode Rules:**
1. Always ask if there's more after each item
2. Never process incomplete groups
3. Wait for you to say you're done
4. Send complete groups to specialists
5. Combine results into one clear message

## 4. Specialist AI Helpers

### Food Expert AI

This AI is the nutrition specialist who calculates calories and nutrients:

```python
# agents/nutrition/agent.py
nutrition_agent = LlmAgent(
    name="nutrition_agent_batch",
    model=PatchedGemini(model=Config.gemini_model),
    description="Handles complete meal groups using USDA database",
    instruction="""
    You are a nutrition expert who gets COMPLETE MEAL GROUPS.

    YOUR TASK:
    - Get: List of all foods from one meal
    - Look up: Each food in USDA nutrition database
    - Calculate: Total calories, protein, carbs, fat for the meal
    - Return: Meal summary with numbers
    """,
    tools=[batch_parser_tool, batch_calculator_tool, usda_tool],
)
```

**Tools it uses:**
- `parse_meal_batch()` - Understands food descriptions
- `calculate_meal_nutrition()` - Adds up nutrition numbers
- `lookup_nutrition_usda()` - Gets data from official USDA database

**What it returns:**
```json
{
    "status": "success",
    "meal_type": "breakfast",
    "foods": [
        {"name": "eggs", "quantity": "2 large", "calories": 140, "protein": 12},
        {"name": "toast", "quantity": "1 slice", "calories": 120, "protein": 4}
    ],
    "totals": {"calories": 260, "protein": 16, "carbs": 25, "fat": 8},
    "confidence": 0.92,
    "notes": "Based on USDA database with high confidence"
}
```

### New User Setup AI

This AI helps new users create their profiles by asking questions:

```python
# agents/onboarding_agent.py
class OnboardingAgent:
    def __init__(self):
        self.states = {
            "greeting": self._handle_greeting,
            "consent": self._handle_consent,
            "age": self._handle_age,
            "height": self._handle_height,
            "weight": self._handle_weight,
            "target_weight": self._handle_target_weight,
            "activity_level": self._handle_activity_level,
            "review_profile": self._handle_review_profile,
            "complete": self._handle_complete
        }
```

**Setup Process:**
1. **Welcome** - Greets user and gets permission
2. **Gather Info** - Asks for age, height, weight, target weight, activity level
3. **Check Answers** - Validates input and calculates calorie goals
4. **Review** - Shows profile summary for confirmation
5. **Finish** - Creates profile and starts normal chatting

## 5. Real Examples of How Messages Flow

### Example 1: Logging a Meal

```
Your Message: "I ate 2 eggs for breakfast"

1. Telegram Bot → ADK System
2. ADK Runner → Main AI
3. Main AI checks intent → "This is about food"
4. Main AI checks mood → "Neutral"
5. Main AI starts group mode: "2 eggs noted. More for breakfast?"
6. You reply: "That's all"
7. Main AI sends ["2 eggs"] to Food Expert
8. Food Expert calculates and returns nutrition info
9. Main AI formats reply: "Breakfast logged! 140 calories, 12g protein ✅"
10. Reply goes back to you
```

### Example 2: New User Starting

```
Your Message: "/start"

1. Telegram Bot sees you're new (no profile)
2. Sends you to Setup AI
3. Setup AI: "Welcome! Ready to set up your profile?"
4. You: "Yes"
5. Question flow: Age → Height → Weight → Target → Activity → Review → Done
6. Profile saved to database
7. You can now chat normally with Main AI
```

### Example 3: Checking Progress

```
Your Message: "How am I doing this week?"

1. Main AI checks intent → "This is about progress"
2. Main AI would send to Progress AI (coming soon)
3. Progress AI looks up your data in database
4. Returns progress report
5. Main AI makes it easy to read and sends to you
```

## 6. How Data Moves and Gets Stored

### Keeping Track of Conversations

The system remembers things in three ways:

1. **AI Memory** - Remembers conversation flow between messages
2. **Group Memory** - Temporarily stores items while you're logging multiple things
3. **Database Memory** - Permanently stores your profile and logged data

### Database Storage

Your information is saved in a local database with these main sections:

- `UserProfile` - Your personal info and goals
- `MealLog` - All your food logging entries
- `WorkoutLog` - Your exercise records
- `WellnessLog` - Sleep, water, steps, mood tracking
- `SessionState` - Temporary conversation info

## 7. Handling Problems

### Timeouts
If the AI takes too long, it stops and tells you:

```python
# Stop waiting after timeout
response = await asyncio.wait_for(
    self.agent_router(user_id, text, context),
    timeout=settings.bot_response_timeout
)
```

### Backup Plans
- AI errors → Simple error message
- Too slow → "Taking too long, try again"
- Bad input → Helpful correction suggestions

### Tracking Issues
- Logs everything that happens
- Records errors with details
- Monitors how fast responses are

## 8. Future Additions

### New AI Specialists Planned

1. **Exercise AI** - Handle workout logging and tracking
2. **Wellness AI** - Track sleep, water, steps, and mood
3. **Progress AI** - Create reports and insights
4. **Reminder AI** - Send motivational messages and tips

### Cool New Features

- **Photo Recognition** - Take pictures of food to log automatically
- **Voice Logging** - Speak your meals instead of typing
- **App Connections** - Link with fitness trackers and apps
- **Multiple Languages** - Support different languages

## 9. How to Run and Test

### Local Testing
```bash
# Get required software
pip install -r requirements.txt

# Run for testing
python -m telegram_bot.bot

# Run for real use
python -m telegram_bot.bot --webhook
```

### ADK Web Testing
You can also test directly with Google's AI tools:

```bash
adk web
```

This gives you a web page to chat with the AI agents directly, great for testing and fixing issues.

## Summary

Your weight loss bot is like a team of AI specialists working together. The main AI figures out what you want, then sends the work to the right specialist (food expert, exercise coach, etc.). This keeps things organized and lets each AI focus on what they do best. The system can grow by adding more specialists as you add new features.