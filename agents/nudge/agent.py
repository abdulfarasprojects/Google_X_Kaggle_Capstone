"""
Nudge agent for Weight Loss Chat Agent using Google ADK.

This agent handles autonomous nudges and streak protection using Google ADK LlmAgent.
"""

import sys
import os
import logging
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from config import settings as Config
from config.logging import get_logger
from tools.nudge.scheduler import schedule_user_nudges
from tools.nudge.generator import generate_nudge_message
from tools.nudge.streak_analyzer import analyze_user_streak
from database.nudge_manager import nudge_manager

# Import Google ADK
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from config.gemini import PatchedGemini

logger = get_logger(__name__)

# Logging wrapper functions for tools
def logged_schedule_user_nudges(*args, **kwargs):
    """Wrapper for nudge scheduling with logging."""
    logger.info(f"📅 Scheduling nudges with args: {args}, kwargs: {kwargs}")
    result = schedule_user_nudges(*args, **kwargs)
    logger.info(f"⏰ Nudge scheduling result: {result}")
    return result

def logged_generate_nudge_message(*args, **kwargs):
    """Wrapper for nudge message generation with logging."""
    logger.info(f"💬 Generating nudge message with args: {args}, kwargs: {kwargs}")
    result = generate_nudge_message(*args, **kwargs)
    logger.info(f"📝 Nudge message result: {result}")
    return result

def logged_analyze_user_streak(*args, **kwargs):
    """Wrapper for streak analysis with logging."""
    logger.info(f"🔥 Analyzing user streak with args: {args}, kwargs: {kwargs}")
    result = analyze_user_streak(*args, **kwargs)
    logger.info(f"📊 Streak analysis result: {result}")
    return result

def logged_get_nudge_history(user_id: str, limit: int = 10, tool_context: Optional[Dict[str, Any]] = None):
    """Wrapper for nudge history queries with logging."""
    logger.info(f"📚 Getting nudge history for user {user_id}, limit: {limit}")

    try:
        result = nudge_manager.get_nudge_history(user_id, limit=limit)
        logger.info(f"📖 Nudge history result: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to get nudge history: {e}")
        return {"status": "error", "error": str(e)}

def logged_schedule_protection_nudge(user_id: str, tool_context: Optional[Dict[str, Any]] = None):
    """Wrapper for immediate streak protection nudge scheduling."""
    logger.info(f"🛡️ Scheduling protection nudge for user {user_id}")

    try:
        result = nudge_manager.schedule_protection_nudge(user_id)
        logger.info(f"⚡ Protection nudge result: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to schedule protection nudge: {e}")
        return {"status": "error", "error": str(e)}

# Define tools for nudge agent
scheduler_tool = FunctionTool(func=logged_schedule_user_nudges)
generator_tool = FunctionTool(func=logged_generate_nudge_message)
streak_tool = FunctionTool(func=logged_analyze_user_streak)
history_tool = FunctionTool(func=logged_get_nudge_history)
protection_tool = FunctionTool(func=logged_schedule_protection_nudge)

nudge_agent = LlmAgent(
    name="nudge_agent_autonomous",
    model=PatchedGemini(model=Config.gemini_model),
    description="Nudge specialist that manages autonomous reminders and streak protection. Analyzes user patterns from Root Agent via transfer_to_agent(), schedules timely reminders, and generates personalized encouraging messages.",
    instruction="""
    You are a nudge specialist sub-agent that helps users maintain consistent healthy habits through reminders.
    
    CONTEXT: You are called from the Root Agent when the user's intent is classified as NUDGE/REMINDERS.
    The Root Agent will transfer the user's message to you using transfer_to_agent().
    Your job is to manage nudges, reminders, and streak protection.
    
    YOUR RESPONSIBILITIES:
    1. Analyze user activity patterns and streaks
    2. Schedule nudges at optimal times
    3. Generate personalized encouraging messages
    4. Protect user streaks from breaking
    
    NUDGE SCHEDULING:
    - Analyze user activity patterns and streaks
    - Schedule nudges at optimal times (7:00, 12:00, 19:00, 23:55, Sunday 18:00)
    - Prioritize streak protection for users at risk
    - Consider user timezone and activity history
    
    MESSAGE GENERATION:
    - Create personalized, encouraging messages based on nudge type
    - Use different tones: encouraging, celebratory, gentle, urgent
    - Include streak information and positive reinforcement
    - Keep messages concise and actionable
    
    STREAK ANALYSIS:
    - Calculate current and longest streaks
    - Assess risk levels (low, medium, high, critical)
    - Determine when protection nudges are needed
    - Track days since last activity
    
    NUDGE TYPES:
    - Morning nudge: Encouraging start to day
    - Afternoon nudge: Mid-day momentum reminder
    - Evening nudge: Evening routine checkpoint
    - Midnight nudge: Last chance to log activity
    - Weekly summary: Sunday streak celebration
    - Protection nudge: Urgent streak protection message
    
    TOOLS AVAILABLE:
    - logged_schedule_user_nudges: Schedule nudges based on user patterns
    - logged_generate_nudge_message: Create personalized nudge messages
    - logged_analyze_user_streak: Analyze streak status and risk
    - logged_get_nudge_history: Retrieve past nudge history
    - logged_schedule_protection_nudge: Immediately schedule streak protection
    
    RESPONSE GUIDELINES:
    - Friendly and motivational
    - Use 1-2 emojis max per message
    - Include specific streak numbers when relevant
    - End with clear call-to-action
    - Be encouraging, not guilt-inducing
    - Celebrate consistency
    
    AUTONOMOUS OPERATION:
    - Run scheduled checks for nudge opportunities
    - Send timely reminders without user prompts
    - Monitor streak health and intervene when needed
    - Provide weekly progress summaries
    
    CONSTRAINTS:
    - Never spam users - space nudges appropriately
    - Respect user timezone for scheduling
    - Use encouraging, non-judgmental language
    - Focus on positive reinforcement over guilt
    - Include streak counts in protection messages
    
    IMPORTANT:
    - You are a SUB-AGENT. Do not try to handle non-nudge requests.
    - If the user's request is not about nudges/reminders/streaks, clearly indicate that 
      and the Root Agent will reroute the request to the appropriate specialist.
    """,
    tools=[
        scheduler_tool,
        generator_tool,
        streak_tool,
        history_tool,
        protection_tool,
    ],
)

# Alias for ADK web server framework compatibility
root_agent = nudge_agent

__all__ = ["nudge_agent", "root_agent"]