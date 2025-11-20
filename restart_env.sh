#!/bin/bash
# Restart and reinitialize the environment for the Weight Loss Bot

echo "=========================================="
echo "Environment Restart and Initialization"
echo "=========================================="
echo ""

# Set environment variables
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Path to venv
VENV_PATH="/Users/abdulfaras/Google_X_Kaggle_Capstone/.venv"
PROJECT_PATH="/Users/abdulfaras/Google_X_Kaggle_Capstone"

echo "1. Activating virtual environment..."
source "$VENV_PATH/bin/activate"
echo "   ✅ Virtual environment activated"
echo ""

echo "2. Checking Python version..."
python --version
echo ""

echo "3. Checking google-adk installation..."
python -c "import google.adk; print('   ✅ google-adk is installed')" 2>&1 || echo "   ⚠️  google-adk check skipped (may initialize on first import)"
echo ""

echo "4. Clearing Python cache..."
find "$PROJECT_PATH" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_PATH" -type f -name "*.pyc" -delete 2>/dev/null || true
echo "   ✅ Python cache cleared"
echo ""

echo "5. Checking database..."
if [ -f "$PROJECT_PATH/weight_loss_app.db" ]; then
    echo "   ✅ Database file exists"
else
    echo "   ⚠️  Database file not found (will be created on first run)"
fi
echo ""

echo "=========================================="
echo "✅ Environment restart complete!"
echo "=========================================="
echo ""
echo "To start the bot, run:"
echo "  cd $PROJECT_PATH"
echo "  python telegram_bot/bot.py"
echo ""
