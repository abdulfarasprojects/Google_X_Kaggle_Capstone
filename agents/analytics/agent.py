"""
Analytics agent for Weight Loss Chat Agent using Google ADK.

This agent provides progress analytics, trend analysis, and hero stats
using Google ADK LlmAgent.
"""

import sys
import os
import logging
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from config import settings as Config
from config.logging import get_logger
from tools.analytics.calculator import calculate_progress_metrics
from tools.analytics.trends import analyze_progress_trends
from tools.analytics.hero_stats import generate_hero_stats
from database.analytics_manager import analytics_manager

# Import Google ADK
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from config.gemini import PatchedGemini

logger = get_logger(__name__)

# Logging wrapper functions for tools
def logged_calculate_progress_metrics(*args, **kwargs):
    """Wrapper for progress metrics calculation with logging."""
    logger.info(f"📊 Calculating progress metrics with args: {args}, kwargs: {kwargs}")
    result = calculate_progress_metrics(*args, **kwargs)
    logger.info(f"📈 Progress metrics result: {result}")
    return result

def logged_analyze_progress_trends(*args, **kwargs):
    """Wrapper for trend analysis with logging."""
    logger.info(f"📉 Analyzing progress trends with args: {args}, kwargs: {kwargs}")
    result = analyze_progress_trends(*args, **kwargs)
    logger.info(f"📊 Trend analysis result: {result}")
    return result

def logged_generate_hero_stats(*args, **kwargs):
    """Wrapper for hero stats generation with logging."""
    logger.info(f"🏆 Generating hero stats with args: {args}, kwargs: {kwargs}")
    result = generate_hero_stats(*args, **kwargs)
    logger.info(f"🎉 Hero stats result: {result}")
    return result

def logged_get_progress_summary(user_id: str, period: str = "weekly", tool_context: Optional[Dict[str, Any]] = None):
    """Wrapper for progress summary queries with logging."""
    logger.info(f"📋 Getting progress summary for user {user_id}, period: {period}")

    try:
        if period.lower() in ["daily", "day", "today"]:
            result = analytics_manager.get_daily_progress_summary(user_id)
        elif period.lower() in ["weekly", "week", "this week"]:
            result = analytics_manager.get_weekly_progress_summary(user_id)
        elif period.lower() in ["monthly", "month", "this month"]:
            result = analytics_manager.get_monthly_progress_summary(user_id)
        else:
            # Default to weekly
            result = analytics_manager.get_weekly_progress_summary(user_id)

        logger.info(f"📊 Progress summary result: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to get progress summary: {e}")
        return {"status": "error", "error": str(e)}

# Define tools for analytics agent
progress_tool = FunctionTool(func=logged_calculate_progress_metrics)
trends_tool = FunctionTool(func=logged_analyze_progress_trends)
hero_tool = FunctionTool(func=logged_generate_hero_stats)
summary_tool = FunctionTool(func=logged_get_progress_summary)

analytics_agent = LlmAgent(
    name="analytics_agent_progress",
    model=PatchedGemini(model=Config.gemini_model),
    description="Analytics specialist that provides progress analytics, trend analysis, and achievement highlights. Analyzes user data from Root Agent via transfer_to_agent() to generate insights, summaries, and motivational hero stats.",
    instruction="""
    You are an analytics specialist sub-agent that provides insights and motivation through data analysis.
    
    CONTEXT: You are called from the Root Agent when the user's intent is classified as ANALYTICS.
    The Root Agent will transfer the user's message to you using transfer_to_agent().
    Your job is to analyze user data and return insights to the Root Agent.
    
    YOUR RESPONSIBILITIES:
    1. Calculate comprehensive progress metrics
    2. Analyze trends across different metrics
    3. Generate motivational hero stats and achievements
    4. Provide data-driven summaries and recommendations
    
    PROGRESS ANALYSIS:
    - Calculate comprehensive metrics (calories, workouts, sleep, water, steps, streaks)
    - Support daily, weekly, and monthly analysis periods
    - Provide clear summaries with budgets, actuals, and remaining amounts
    - Include comparisons to goals
    
    ANALYTICS QUERIES:
    - Handle requests like: "how am I doing this week", "show my progress", "what's my streak"
    - For "today", "daily", "day" → get daily progress summary
    - For "week", "weekly", "this week" → get weekly progress summary
    - For "month", "monthly", "this month" → get monthly progress summary
    - Provide encouraging, data-driven responses
    
    TREND ANALYSIS:
    - Analyze trends across metrics (calories, workouts, sleep, water, steps, streak)
    - Determine if trends are improving, declining, or stable
    - Provide confidence levels for trend analysis
    - Generate actionable insights and recommendations
    
    HERO STATS GENERATION:
    - Identify impressive achievements and milestones
    - Create motivational highlights from user data
    - Categorize achievements (streak, volume, consistency, milestone)
    - Rank achievements by impact level
    
    DATA INSIGHTS:
    - Compare actual vs goals/budgets
    - Highlight positive trends and improvements
    - Gently suggest areas for improvement
    - Celebrate consistency and streaks
    - Use hero stats to motivate continued progress
    
    TOOLS AVAILABLE:
    - logged_calculate_progress_metrics: Calculate detailed progress metrics
    - logged_analyze_progress_trends: Analyze trends in specific metrics
    - logged_generate_hero_stats: Create motivational achievement highlights
    - logged_get_progress_summary: Get formatted progress summaries
    
    RESPONSE GUIDELINES:
    - Data-driven but conversational
    - Use 1-2 emojis max per response
    - Include specific numbers and comparisons
    - End with positive reinforcement
    - Make complex data easy to understand
    - Celebrate achievements and consistency
    
    IMPORTANT:
    - You are a SUB-AGENT. Do not try to handle non-analytics requests.
    - Always provide context and explanations for metrics
    - Use encouraging, non-judgmental language
    - Focus on progress and achievements
    - Include actionable recommendations when trends need improvement
    - Show confidence levels for uncertain data
    """,
    tools=[
        progress_tool,
        trends_tool,
        hero_tool,
        summary_tool,
    ],
)

# Alias for ADK web server framework compatibility
root_agent = analytics_agent

__all__ = ["analytics_agent", "root_agent"]