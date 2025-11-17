# Weight Loss Chat Agent 🤖

A conversational AI-powered Telegram bot that helps users track their weight loss journey through nutrition, fitness, and wellness logging with autonomous nudges and personalized recommendations.

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)
![Google ADK](https://img.shields.io/badge/Google-ADK-green.svg)
![SQLite](https://img.shields.io/badge/Database-SQLite-blue.svg)

## ⚠️ Important Disclaimer

**THIS BOT DOES NOT PROVIDE MEDICAL ADVICE OR PROFESSIONAL HEALTH GUIDANCE**

- This application is for informational and tracking purposes only
- AI systems can make mistakes and provide inaccurate information
- Always consult qualified healthcare professionals for medical advice
- Use this tool cautiously and at your own risk
- The developers are not responsible for any health-related decisions made based on this bot's output

## 🌟 Features

This Telegram bot is a friendly, privacy-first AI weight loss companion designed to make healthy habits easier to build and track. It lets users log meals, workouts, water intake, sleep, and daily steps in a conversation—without judgment, tedious apps, or spreadsheets. With gentle nudges, smart batch processing, and weekly progress reports, it adapts to each user’s goals and schedule. The bot supports dietary restrictions, respects privacy, and recovers intelligently from errors or ambiguities, making it a trustworthy partner for sustainable weight management and wellness.

### ✅ Completed (Phase 1 MVP)
- **Conversational Onboarding**: Step-by-step profile setup with personalized calorie goals
- **User Profile Management**: Secure storage of demographics, goals, and preferences
- **Health-Focused Validation**: BMI checks, safe calorie ranges, and wellness guardrails

### 🚧 In Development
- **Nutrition Tracking**: Log meals with USDA API integration and calorie calculations
- **Fitness Logging**: Track workouts with volume calculations and progression suggestions
- **Wellness Monitoring**: Sleep, water intake, and step counting with correlations
- **Autonomous Nudges**: Scheduled reminders to maintain consistent habits
- **Progress Analytics**: Daily/weekly summaries with trends and insights

## 📱 How It Works

The Weight Loss Chat Agent is your personal health coach available 24/7 through Telegram. Simply chat with the bot to log your meals, workouts, and wellness metrics, and receive personalized guidance for your weight loss journey.

### Core Principles
- **Recommendation-Only**: The bot guides and tracks, but you control your journey
- **Data Minimization**: Only essential health data stored locally on your device
- **Privacy-First**: No cloud storage, GDPR compliant, data encryption at rest
- **Conversational AI**: Natural language processing powered by Google Gemini

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Telegram account
- Internet connection for API calls

### 1. Get Your Telegram Bot Token
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow the prompts
3. Save your bot token (starts with `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### 2. Clone and Setup
```bash
git clone <your-repo-url>
cd weight-loss-agent

# Install uv package manager (faster than pip)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv --python 3.12
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
uv pip install google-adk python-telegram-bot google-generativeai apscheduler pydantic
```

### 3. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit with your keys
nano .env
```

**Required Environment Variables:**
```env
# Telegram Bot (from BotFather)
TELEGRAM_BOT_TOKEN=your-bot-token-here
TELEGRAM_ADMIN_USER_ID=your-telegram-user-id

# Google AI (get from https://aistudio.google.com/)
GOOGLE_GENAI_API_KEY=your-gemini-api-key

# Nutrition APIs (free tier available)
USDA_FDC_API_KEY=demo
NUTRITIONIX_APP_ID=your-app-id
NUTRITIONIX_APP_KEY=your-app-key

# Database (local SQLite)
DATABASE_URL=sqlite:///./weight_loss_app.db
```

### 4. Initialize Database
```bash
# Create database tables
python -c "from database.models import init_db; init_db()"
```

### 5. Start the Bot
```bash
python -m telegram.bot
```

### 6. Test Your Bot
1. Open Telegram and search for your bot
2. Send `/start` or just say "hello"
3. Follow the onboarding prompts

## 💬 Usage Examples

### Onboarding (New Users)
```
You: Hi! I want to start tracking my weight loss

Bot: 👋 Welcome to your Weight Loss Assistant!
     I'm here to help you track your nutrition, fitness, and wellness.
     Ready to begin? Reply with 'yes' or 'start' to continue.

You: yes

Bot: Great! Let's get you set up. 📝
     First, I'll ask a few questions about your age, height, weight, and activity level.
     This helps me calculate your daily calorie needs.
     How old are you? (Please enter a number between 18-100)

You: 28

Bot: Thanks! Now, what's your height in centimeters? (e.g., 170)

You: 175

Bot: Perfect! Now, what's your current weight in kilograms? (e.g., 75.5)

You: 82

Bot: Great! Now, what's your target weight in kilograms? (This should be less than your current weight)

You: 75

Bot: Finally, what's your typical activity level?
     Choose the option that best describes you:
     • sedentary: Little to no exercise, desk job
     • light: Light exercise 1-3 days/week
     • moderate: Moderate exercise 3-5 days/week
     • active: Hard exercise 6-7 days/week
     • very_active: Very hard exercise, physical job, or 2x training
     Reply with one of: sedentary, light, moderate, active, very_active

You: moderate

Bot: Perfect! Based on your information, I suggest a daily calorie goal of 2200 calories.
     This creates a safe deficit for weight loss while considering your activity level.

     Here's a summary of your profile:
     • Age: 28 years
     • Height: 175 cm
     • Current Weight: 82 kg
     • Target Weight: 75 kg
     • Activity Level: moderate
     • Daily Calories: 2200

     Does this look correct? Reply 'yes' to save your profile, or 'no' to make changes.

You: yes

Bot: 🎉 Welcome aboard! Your profile has been created successfully.
     You're all set to start tracking your weight loss journey.
     Try starting with: 'I ate breakfast - 2 eggs and toast'
```

### Nutrition Logging (Coming Soon)
```
You: I ate breakfast - 2 eggs, toast, and coffee

Bot: Got it! I logged:
     • 2 eggs (140 calories, 12g protein)
     • 2 slices toast (160 calories, 6g protein)
     • Coffee (5 calories)

     Total: 305 calories, 18g protein
     Remaining budget: 1895 calories today

     Is that all for breakfast? (yes/no/add more)

You: add more

Bot: What else did you have?

You: a banana

Bot: Added banana (105 calories, 1.3g protein)

     Updated total: 410 calories, 19.3g protein
     Remaining budget: 1790 calories today

     Is that all for breakfast?

You: yes

Bot: ✅ Breakfast logged! You're doing great.
     Keep up the good work! 💪
```

### Fitness Tracking (Coming Soon)
```
You: I worked out today - 3 sets of squats with 80kg, 10 pull-ups, and 20 minutes cardio

Bot: Great workout! I logged:
     • Squats: 3 sets × 10 reps × 80kg = 2400 volume units
     • Pull-ups: 3 sets × 10 reps × bodyweight = 900 volume units
     • Cardio: 20 minutes steady-state

     Total volume: 3300 units (personal best!)
     Progression suggestion: Try 85kg squats next time

     How did that feel? Any notes about your form?

You: Felt good, but squats were challenging

Bot: Noted! Next time try 82.5kg for squats to keep progressing safely.
     You're building strength consistently! 🏋️‍♀️
```

### Wellness Monitoring (Coming Soon)
```
You: I slept 7.5 hours last night, quality was 8/10

Bot: Sleep logged! 7.5 hours with 8/10 quality rating.
     That's within the healthy range (7-9 hours).

     Your sleep trend this week: 7.2 hours average
     Water intake today: 0 glasses (aim for 8)
     Steps today: 0 (aim for 8000)

     How about some water to start your day? 💧

You: Just drank 2 glasses of water

Bot: Excellent! 2 glasses logged.
     Hydration progress: 2/8 glasses (25%)
     Keep it up! 💧
```

### Progress Analytics (Coming Soon)
```
You: Show me my progress this week

Bot: 📊 Your Weekly Progress Summary

     📅 Week of November 11-17, 2025

     🍎 Nutrition:
     • Average daily calories: 2150 (50 calories under goal)
     • Best day: Tuesday (2080 calories)
     • Protein average: 95g/day
     • Logged 6 out of 7 days

     💪 Fitness:
     • Total workouts: 4 sessions
     • Average volume: 2800 units
     • Personal best: Thursday (3200 units)
     • Progression: +15% volume increase

     😴 Wellness:
     • Sleep average: 7.3 hours/night
     • Water average: 6.2 glasses/day
     • Steps average: 7200/day
     • Correlation: Better sleep = lower calorie days

     🏆 Hero Stat: 4-day logging streak!
     🔥 You're on fire this week!

     Keep up the amazing work! Next goal: 5-day streak? 🎯
```

## 🏗️ Architecture

```
weight-loss-agent/
├── agents/                 # AI Agent implementations
│   ├── root/              # Main orchestrator agent
│   ├── onboarding/        # User profile setup
│   ├── nutrition/         # Meal logging & analysis
│   ├── fitness/           # Workout tracking
│   ├── wellness/          # Health metrics
│   └── nudge/             # Autonomous reminders
├── tools/                 # Agent tool functions
│   ├── nutrition/         # Food parsing, USDA API
│   ├── fitness/           # Exercise analysis
│   ├── wellness/          # Health correlations
│   ├── nudge/             # Scheduling & messaging
│   └── general/           # Shared utilities
├── database/              # SQLite models & managers
│   ├── models.py          # SQLAlchemy models
│   ├── init.py            # Database setup
│   └── *_manager.py       # Data access layers
├── config/                # Configuration management
│   ├── settings.py        # App settings
│   ├── logging.py         # Logging configuration
│   └── gemini.py          # Google AI client
├── telegram/              # Bot integration
│   └── bot.py             # Telegram bot handler
└── tests/                 # Test suites
```

### Key Technologies
- **AI Framework**: Google ADK (Agent Development Kit)
- **LLM**: Google Gemini 2.5 Flash
- **Messaging**: Telegram Bot API with python-telegram-bot
- **Database**: SQLite with SQLAlchemy ORM
- **Scheduling**: APScheduler for autonomous nudges
- **APIs**: USDA FoodData Central, Nutritionix (free tiers)

## 🔒 Privacy & Security

### Data Protection
- **Local Storage Only**: All data stored on user's device (no cloud sync)
- **Encryption at Rest**: SQLite database encrypted with AES-256
- **GDPR Compliant**: Right to data deletion and export
- **No Personal Data**: Only Telegram user ID, no emails or names

### API Security
- **Environment Variables**: All API keys stored securely
- **Log Sanitization**: Sensitive data removed from application logs
- **Rate Limiting**: Built-in protection against abuse
- **Cost Monitoring**: API usage tracking for billing control

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=agents --cov=tools --cov-report=html

# Run specific test categories
pytest tests/test_agents/
pytest tests/test_database/
pytest tests/test_tools/
```

## 🚀 Deployment

### Local Development
```bash
# Start bot in development mode
python -m telegram.bot

# With debug logging
DEBUG=1 python -m telegram.bot
```

### Production Deployment (Google Cloud Run)
```bash
# Build Docker image
docker build -t weight-loss-agent .

# Run locally for testing
docker run -p 8080:8080 weight-loss-agent

# Deploy to Cloud Run
gcloud run deploy weight-loss-agent \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Follow the constitution principles in `Docs/speckit_constitution.md`
4. Add tests for new functionality
5. Ensure 80%+ test coverage
6. Submit a pull request

### Code Standards
- **Type Hints**: 100% coverage required
- **Docstrings**: Google-style format
- **Linting**: `ruff check . && ruff format .`
- **Testing**: `pytest` with 80% coverage minimum

## 📚 Documentation

- **[Technical Specs](specs/001-weight-loss-agent/)**: Detailed feature specifications
- **[API Contracts](specs/001-weight-loss-agent/contracts/)**: Tool interface definitions
- **[Data Models](specs/001-weight-loss-agent/data-model.md)**: Database schema and relationships
- **[Constitution](Docs/speckit_constitution.md)**: Development principles and guidelines

## 🐛 Troubleshooting

### Bot Not Responding
```bash
# Check bot token validity
python -c "
import os
from telegram import Bot
bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
print('Bot info:', bot.get_me())
"
```

### Database Issues
```bash
# Reset database
rm weight_loss_app.db
python -c "from database.models import init_db; init_db()"
```

### API Errors
```bash
# Test Gemini API
python -c "
import google.generativeai as genai
genai.configure(api_key='YOUR_KEY')
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content('Hello')
print(response.text)
"
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Google ADK**: For the agent development framework
- **Telegram**: For the bot platform
- **USDA**: For nutrition data APIs
- **Nutritionix**: For food database access

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)
- **Documentation**: See `docs/` directory

---

**Remember**: This is a tool to guide your weight loss journey, but you're in control. Listen to your body, consult healthcare professionals for medical advice, and celebrate your progress along the way! 🌟</content>
<parameter name="filePath">/Users/abdulfaras/Google_X_Kaggle_Capstone/README.md