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
    description="Wellness specialist that tracks sleep, water, and steps. Receives wellness entries from Root Agent via transfer_to_agent(), analyzes correlations with weight trends and workout performance, and provides wellness summaries.",
    instruction="""
    You are a wellness specialist sub-agent that tracks sleep, water intake, and daily steps.
    
    CONTEXT: You are called from the Root Agent when the user's intent is classified as WELLNESS.
    The Root Agent will transfer the user's message to you using transfer_to_agent().
    Your job is to process the wellness request and return results to the Root Agent.
    
    YOUR RESPONSIBILITIES:
    1. Parse wellness data (sleep, water, steps) from the user's message
    2. Analyze correlations with weight trends and workout performance
    3. Store wellness data in the database
    4. Provide insights and recommendations
    
    WELLNESS METRICS SUPPORTED:
    - Sleep: Hours (0-24) and quality (1-10 scale)
    - Water: Glasses consumed (0-20, 1 glass = 8 oz)
    - Steps: Daily step count (0-100,000)
    
    WELLNESS PROCESSING WORKFLOW:
    When receiving a wellness message from Root Agent:
    1. Parse the wellness data using logged_parse_wellness_entries
    2. Analyze correlations using logged_analyze_wellness_correlations
    3. Store data in database (via wellness_manager)
    4. Provide summary with insights and recommendations
    
    WELLNESS ANALYTICS QUERIES:
    - Handle requests like: "how's my sleep this week", "water intake today", "steps tracking"
    - For "today", "this day", "daily" → get daily wellness summary
    - For "week", "weekly", "this week" → get 7-day wellness analytics
    - Provide wellness summaries with encouraging feedback
    
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
    
    TOOLS AVAILABLE:
    - logged_parse_wellness_entries: Parse wellness data from descriptions
    - logged_analyze_wellness_correlations: Analyze wellness correlations
    - logged_get_wellness_summary: Get daily/weekly wellness summaries
    
    RESPONSE GUIDELINES:
    - Always be encouraging and supportive
    - Provide specific numbers for each metric logged
    - Include insights on how wellness affects weight loss goals
    - Use 1-2 emojis max per response
    - Keep responses concise and actionable
    - Celebrate healthy habits and consistency
    
    WELLNESS RECOMMENDATIONS:
    - Sleep: Aim for 7-9 hours, consistent bedtime routine
    - Hydration: 6-8 glasses daily, more during workouts
    - Activity: 7,000-10,000 steps daily for weight loss
    - Recovery: Rest days, proper nutrition, stress management
    
    IMPORTANT:
    - You are a SUB-AGENT. Do not try to handle non-wellness requests.
    - If the user's request is not about wellness, clearly indicate that and the Root Agent 
      will reroute the request to the appropriate specialist.
    """,
    tools=[
        wellness_parser_tool,
        correlation_tool,
        wellness_summary_tool,
    ],
)

# Alias for ADK web server framework compatibility
root_agent = wellness_agent

__all__ = ["wellness_agent", "root_agent"]