#!/bin/bash
# Start the Telegram bot

cd /Users/abdulfaras/Google_X_Kaggle_Capstone

echo "🤖 Starting Telegram Bot..."
echo "Database has been reset - all user data deleted"
echo "The bot is now running and waiting for messages..."
echo ""
echo "Press Ctrl+C to stop the bot"
echo ""

# Run the bot
source .venv/bin/activate
python3 -m telegram_bot.bot
