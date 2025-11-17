"""
Telegram bot integration layer for Weight Loss Chat Agent.

This module provides the Telegram bot interface using python-telegram-bot
with async handlers. It manages message routing, conversation states,
and integrates with the agent framework for processing user requests.

Key features:
- Async message handling with timeouts
- Conversation state management
- Error handling and user feedback
- Admin commands and monitoring
- Webhook and polling support
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta

from telegram import Update, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)
from telegram.error import TimedOut, NetworkError

from config.settings import settings
from database.init import get_db_session
from database.models import SessionState, UserProfile, MealLog, WorkoutLog, WellnessLog

logger = logging.getLogger(__name__)


class TelegramBot:
    """
    Telegram bot integration with async message handling.

    Manages bot lifecycle, message routing, and conversation state.
    Integrates with agent framework for processing user requests.
    """

    def __init__(self, agent_router: Optional[Callable] = None):
        """
        Initialize Telegram bot.

        Args:
            agent_router: Function to route messages to appropriate agents
        """
        self.agent_router = agent_router
        self.application: Optional[Application] = None
        self._running = False

    async def initialize(self) -> None:
        """Initialize the bot application with handlers."""
        logger.info("Initializing Telegram bot...")

        # Create application
        self.application = Application.builder().token(settings.telegram_bot_token).build()

        # Add command handlers
        self._add_command_handlers()

        # Add message handlers
        self._add_message_handlers()

        # Add error handler
        self.application.add_error_handler(self._handle_error)

        # Set bot commands
        await self._set_bot_commands()

        logger.info("Telegram bot initialized successfully")

    def _add_command_handlers(self) -> None:
        """Add command handlers for bot commands."""
        if not self.application:
            return

        # Basic commands
        self.application.add_handler(CommandHandler("start", self._handle_start))
        self.application.add_handler(CommandHandler("help", self._handle_help))
        self.application.add_handler(CommandHandler("status", self._handle_status))
        self.application.add_handler(CommandHandler("cancel", self._handle_cancel))

        # Admin commands
        self.application.add_handler(CommandHandler("admin", self._handle_admin))
        self.application.add_handler(CommandHandler("stats", self._handle_stats))

    def _add_message_handlers(self) -> None:
        """Add message handlers for different content types."""
        if not self.application:
            return

        # Handle text messages (main conversation)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )

        # Handle callback queries from inline keyboards
        self.application.add_handler(CallbackQueryHandler(self._handle_callback))

        # Handle photos (for food logging)
        self.application.add_handler(
            MessageHandler(filters.PHOTO, self._handle_photo)
        )

    async def _set_bot_commands(self) -> None:
        """Set bot command menu for better UX."""
        commands = [
            BotCommand("start", "Begin your weight loss journey"),
            BotCommand("help", "Get help and instructions"),
            BotCommand("status", "Check your current status"),
            BotCommand("cancel", "Cancel current operation"),
        ]

        if self.application:
            await self.application.bot.set_my_commands(commands)

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command - initialize user onboarding."""
        user = update.effective_user
        if not user:
            return

        user_id = str(user.id)
        logger.info(f"User {user_id} started bot")

        # Check if user profile exists
        with get_db_session() as session:
            profile = session.query(UserProfile).filter_by(user_id=user_id).first()

            if profile:
                # Existing user - welcome back
                message = (
                    f"Welcome back, {user.first_name}! 👋\n\n"
                    "I'm here to help you with your weight loss journey. "
                    "What would you like to do today?\n\n"
                    "• Log a meal\n"
                    "• Record a workout\n"
                    "• Track wellness metrics\n"
                    "• View progress\n\n"
                    "Just tell me what you'd like to do!"
                )
            else:
                # New user - start onboarding
                message = (
                    f"Hello {user.first_name}! 👋 Welcome to your personal weight loss assistant!\n\n"
                    "I'm here to help you track your nutrition, fitness, and wellness "
                    "to achieve your weight loss goals.\n\n"
                    "To get started, I need to know a bit about you. "
                    "What's your age?"
                )

                # Create initial session state for onboarding
                session_state = SessionState(
                    batch_id=f"onboard_{user_id}",
                    user_id=user_id,
                    batch_type="onboarding",
                    expires_at=datetime.utcnow() + timedelta(hours=settings.session_timeout_hours)
                )
                session.add(session_state)
                session.commit()

        await update.message.reply_text(message)

    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command - show help information."""
        help_text = (
            "🤖 Weight Loss Assistant Help\n\n"
            "I can help you track:\n"
            "• 🍎 Nutrition & meals\n"
            "• 💪 Fitness & workouts\n"
            "• 😴 Sleep & wellness\n"
            "• 📊 Progress & analytics\n\n"
            "Commands:\n"
            "/start - Begin or restart\n"
            "/status - Check your progress\n"
            "/help - Show this help\n"
            "/cancel - Cancel current action\n\n"
            "Just type naturally! For example:\n"
            "• 'I ate 2 eggs and toast'\n"
            "• 'I did 50 push-ups'\n"
            "• 'I slept 8 hours'\n"
            "• 'Show my progress'"
        )

        await update.message.reply_text(help_text)

    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command - show user status."""
        user = update.effective_user
        if not user:
            return

        user_id = str(user.id)

        with get_db_session() as session:
            profile = session.query(UserProfile).filter_by(user_id=user_id).first()

            if not profile:
                await update.message.reply_text(
                    "You haven't set up your profile yet. Use /start to begin!"
                )
                return

            # Get recent activity counts
            today = datetime.utcnow().date()

            meal_count = session.query(MealLog).filter(
                MealLog.user_id == user_id,
                MealLog.log_date == today
            ).count()

            workout_count = session.query(WorkoutLog).filter(
                WorkoutLog.user_id == user_id,
                WorkoutLog.log_date == today
            ).count()

            wellness_count = session.query(WellnessLog).filter(
                WellnessLog.user_id == user_id,
                WellnessLog.log_date == today
            ).count()

            status_text = (
                f"📊 Your Status Today\n\n"
                f"🎯 Goal: {profile.daily_calorie_goal} calories\n"
                f"⚖️ Current weight: {profile.weight_kg}kg\n"
                f"🎂 Age: {profile.age}\n\n"
                f"Today's Activity:\n"
                f"🍽️ Meals logged: {meal_count}\n"
                f"💪 Workouts: {workout_count}\n"
                f"😴 Wellness entries: {wellness_count}\n\n"
                "Keep up the great work! 💪"
            )

        await update.message.reply_text(status_text)

    async def _handle_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /cancel command - cancel current operation."""
        user = update.effective_user
        if not user:
            return

        user_id = str(user.id)

        # Clear any active session state
        with get_db_session() as session:
            session.query(SessionState).filter_by(user_id=user_id).delete()
            session.commit()

        await update.message.reply_text(
            "✅ Cancelled. What would you like to do instead?"
        )

    async def _handle_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /admin command - admin functions (admin only)."""
        user = update.effective_user
        if not user or str(user.id) != settings.telegram_admin_user_id:
            await update.message.reply_text("❌ Admin access denied.")
            return

        # Admin functions would go here
        await update.message.reply_text("🔧 Admin panel - implement admin functions here")

    async def _handle_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stats command - show bot statistics (admin only)."""
        user = update.effective_user
        if not user or str(user.id) != settings.telegram_admin_user_id:
            await update.message.reply_text("❌ Admin access denied.")
            return

        # Bot statistics would go here
        await update.message.reply_text("📈 Bot statistics - implement stats here")

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages - route to appropriate agent."""
        user = update.effective_user
        message = update.message
        if not user or not message or not message.text:
            return

        user_id = str(user.id)
        text = message.text.strip()

        logger.info(f"Message from user {user_id}: {text[:100]}...")

        # Route to agent framework
        if self.agent_router:
            try:
                # Set typing indicator
                await update.message.chat.send_action("typing")

                # Process with timeout
                response = await asyncio.wait_for(
                    self.agent_router(user_id, text, context),
                    timeout=settings.bot_response_timeout
                )

                # Send response
                if isinstance(response, dict) and 'text' in response:
                    reply_text = response['text']
                    reply_markup = response.get('keyboard')

                    if reply_markup:
                        await message.reply_text(reply_text, reply_markup=reply_markup)
                    else:
                        await message.reply_text(reply_text)
                else:
                    await message.reply_text(str(response))

            except asyncio.TimeoutError:
                await message.reply_text(
                    "⏰ I'm taking too long to respond. Please try again."
                )
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await message.reply_text(
                    "❌ Sorry, I encountered an error. Please try again."
                )
        else:
            # Fallback response
            await message.reply_text(
                "🤖 I'm still learning! Please use /help to see what I can do."
            )

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline keyboards."""
        query = update.callback_query
        if not query:
            return

        await query.answer()

        # Handle callback data
        callback_data = query.data
        user_id = str(query.from_user.id)

        logger.info(f"Callback from user {user_id}: {callback_data}")

        # Route callback to agent framework
        if self.agent_router:
            try:
                response = await self.agent_router(user_id, f"callback:{callback_data}", context)

                if response and 'text' in response:
                    await query.edit_message_text(
                        text=response['text'],
                        reply_markup=response.get('keyboard')
                    )
                else:
                    await query.edit_message_text(text="✅ Processed")

            except Exception as e:
                logger.error(f"Error processing callback: {e}")
                await query.edit_message_text(text="❌ Error processing request")

    async def _handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle photo messages (for food logging)."""
        user = update.effective_user
        if not user:
            return

        await update.message.reply_text(
            "📸 I can see you sent a photo! Photo analysis for food logging "
            "will be available in a future update. For now, please describe your meal in text."
        )

    async def _handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors in the bot."""
        logger.error(f"Bot error: {context.error}")

        # Try to notify user if possible
        try:
            if update and update.effective_chat:
                await update.effective_chat.send_message(
                    "❌ Sorry, I encountered an unexpected error. Please try again."
                )
        except Exception:
            pass  # Don't let error handling cause more errors

    async def send_message(self, user_id: str, text: str, keyboard: Optional[InlineKeyboardMarkup] = None) -> bool:
        """
        Send a message to a specific user (for nudges, etc.).

        Args:
            user_id: Telegram user ID
            text: Message text
            keyboard: Optional inline keyboard

        Returns:
            bool: True if message sent successfully
        """
        if not self.application:
            return False

        try:
            if keyboard:
                await self.application.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=keyboard
                )
            else:
                await self.application.bot.send_message(
                    chat_id=user_id,
                    text=text
                )
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {user_id}: {e}")
            return False

    async def start_polling(self) -> None:
        """Start the bot with polling (for development)."""
        if not self.application:
            await self.initialize()

        logger.info("Starting bot with polling...")
        self._running = True

        try:
            await self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
        except Exception as e:
            logger.error(f"Bot polling failed: {e}")
        finally:
            self._running = False

    async def start_webhook(self, webhook_url: str, port: int = 8080) -> None:
        """
        Start the bot with webhook (for production).

        Args:
            webhook_url: Webhook URL for Telegram
            port: Port to listen on
        """
        if not self.application:
            await self.initialize()

        logger.info(f"Starting bot with webhook on port {port}...")
        self._running = True

        try:
            await self.application.run_webhook(
                listen="0.0.0.0",
                port=port,
                webhook_url=webhook_url,
                allowed_updates=Update.ALL_TYPES
            )
        except Exception as e:
            logger.error(f"Bot webhook failed: {e}")
        finally:
            self._running = False

    async def stop(self) -> None:
        """Stop the bot gracefully."""
        logger.info("Stopping bot...")
        self._running = False

        if self.application:
            await self.application.stop()
            await self.application.shutdown()

    @property
    def is_running(self) -> bool:
        """Check if bot is currently running."""
        return self._running


# Global bot instance
bot = TelegramBot()

# Export key classes and functions
__all__ = ['TelegramBot', 'bot']