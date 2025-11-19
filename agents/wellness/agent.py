"""
Wellness agent for Weight Loss Chat Agent using Google ADK.

This agent processes complete wellness batches using Google ADK LlmAgent.
"""

import sys
import os
import logging
from typing import Dict, Any, Optional
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from config import settings as Config
from config.logging import get_logger
from tools.wellness.parser import parse_wellness_entries
from tools.wellness.correlations import analyze_wellness_correlations
from database.wellness_manager import wellness_manager

# Import Google ADK
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from config.gemini import PatchedGemini

logger = get_logger(__name__)

# Logging wrapper functions for tools
def logged_parse_wellness_entries(*args, **kwargs):
    """Wrapper for wellness parsing with logging."""
    logger.info(f"🌙 Parsing wellness entries with args: {args}, kwargs: {kwargs}")
    result = parse_wellness_entries(*args, **kwargs)
    logger.info(f"📋 Wellness parsing result: {result}")
    return result

def logged_analyze_wellness_correlations(*args, **kwargs):
    """Wrapper for wellness correlation analysis with logging."""
    logger.info(f"📊 Analyzing wellness correlations with args: {args}, kwargs: {kwargs}")
    result = analyze_wellness_correlations(*args, **kwargs)
    logger.info(f"🔗 Wellness correlations result: {result}")
    return result

def logged_get_wellness_summary(user_id: str, period: str = "today", tool_context: Optional[Dict[str, Any]] = None):
    """Wrapper for wellness summary queries with logging."""
    logger.info(f"📊 Getting wellness summary for user {user_id}, period: {period}")
    
    try:
        if period.lower() in ["today", "day"]:
            result = wellness_manager.get_daily_wellness_summary(user_id, date.today())
        elif period.lower() in ["week", "weekly", "this week"]:
            result = wellness_manager.get_wellness_analytics(user_id, days=7)
        else:
            # Default to today
            result = wellness_manager.get_daily_wellness_summary(user_id, date.today())
            
        logger.info(f"📈 Wellness summary result: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to get wellness summary: {e}")
        return {"status": "error", "error": str(e)}

# Define tools for wellness agent
wellness_parser_tool = FunctionTool(func=logged_parse_wellness_entries)
correlation_tool = FunctionTool(func=logged_analyze_wellness_correlations)
wellness_summary_tool = FunctionTool(func=logged_get_wellness_summary)

wellness_agent = LlmAgent(
    name="wellness_agent_batch",
    model=PatchedGemini(model=Config.gemini_model),
    description="Processes complete wellness batches and provides wellness analytics. Receives wellness entries from Root Agent, analyzes correlations with weight trends and workout performance, and provides wellness summaries.",
    instruction="""
    You are a wellness coach helping users track their wellness metrics. You have a natural conversation flow.

    CONVERSATION FLOW:
    1. When user says "wellness" or similar, acknowledge and start collecting: "Great! Let's track your wellness. What wellness metrics would you like to log today?"
    2. Ask for wellness details in natural way: "How many hours of sleep did you get? How many glasses of water? How many steps?"
    3. For each wellness metric mentioned, confirm and ask for more: "Got it! Any other wellness metrics?"
    4. Continue until user says "done", "finished", "that's all", "no more", etc.
    5. Then process the complete wellness data using your tools

    IMPORTANT: "wellness" by itself is NOT complete wellness data. It just means they want to start logging.

    ANALYTICS QUERIES:
    - Handle requests for wellness summaries: "how's my sleep this week", "water intake today"
    - For "today", "this day", "daily" → get daily wellness summary
    - For "week", "weekly", "this week" → get 7-day wellness analytics
    - Always include user_id in queries
    - Provide wellness summaries in friendly, encouraging messages

    WELLNESS METRICS:
    - Sleep: Hours (0-24) and quality (1-10 scale)
    - Water: Glasses consumed (0-20, 1 glass = 8 oz)
    - Steps: Daily step count (0-100,000)

    BATCH PROCESSING:
    - Only call tools when you have complete wellness data (user indicates they're done)
    - Call tools in sequence: parse → analyze correlations → provide summary
    - Provide encouraging summary with insights and recommendations

    TOOLS: Only call when ready to process complete wellness data or for analytics
    - logged_parse_wellness_entries: Parse wellness data from descriptions
    - logged_analyze_wellness_correlations: Analyze wellness correlations
    - logged_get_wellness_summary: Get daily/weekly wellness summaries

    CORRELATION ANALYSIS:
    - Sleep & Weight: Poor sleep may correlate with weight gain plateaus
    - Sleep & Performance: Inadequate sleep impacts workout recovery
    - Water & Weight: Hydration affects weight measurements and metabolism
    - Steps & Weight: Increased activity correlates with weight loss progress

    INSIGHT GENERATION:
    - Sleep < 7 hours: Recommend sleep prioritization
    - Water < 6 glasses: Suggest hydration improvement
    - Steps < 5,000: Recommend increased daily activity
    - Quality < 6/10: Suggest sleep hygiene improvements

    CONSTRAINTS:
    - No external API calls - use only provided data and local analysis
    - Validate input ranges (sleep 0-24h, water 0-20 glasses, steps 0-100k)
    - Flag unrealistic values for manual verification
    - Provide encouraging, non-judgmental feedback
    - Focus on actionable, achievable improvements

    WELLNESS RECOMMENDATIONS:
    - Sleep: Aim for 7-9 hours, consistent bedtime routine
    - Hydration: 6-8 glasses daily, more during workouts
    - Activity: 7,000-10,000 steps daily for weight loss
    - Recovery: Rest days, proper nutrition, stress management

    COMPLETION SIGNALS: "done", "finished", "that's all", "no more", "complete", "finished logging"

    RESPONSE STYLE:
    - Friendly and encouraging
    - Ask questions to continue collection
    - Provide detailed summary only when wellness data is complete
    - Use emojis sparingly (1-2 per response)

    CRITICAL: Never call tools when user just says "wellness". Always respond with questions to collect wellness data first.
    """,
    tools=[
        wellness_parser_tool,
        correlation_tool,
        wellness_summary_tool,
    ],
)

__all__ = ["wellness_agent"]