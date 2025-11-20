"""
Response formatting tool for Weight Loss Chat Agent.

This tool formats agent responses with appropriate tone and structure.
"""

import logging
from typing import Dict, Any, Optional

from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


async def format_response(
    response_type: str,
    content: Dict[str, Any],
    user_context: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    tool_context: Optional[ToolContext] = None
) -> Dict[str, Any]:
    """
    Format agent response with appropriate tone and structure.

    Args:
        response_type: Type of response (nutrition, fitness, wellness, general)
        content: Response content data
        user_context: User-specific context
        context: Additional context

    Returns:
        Dict with formatted response
    """
    try:
        formatted_response = ""

        if response_type == "nutrition_summary":
            # Format nutrition calculation response
            calories = content.get("total_calories", 0)
            protein = content.get("total_protein_g", 0)
            confidence = content.get("confidence_score", 0.5)

            formatted_response = f"✅ Meal logged!\n\n"
            formatted_response += f"**Nutrition Summary:**\n"
            formatted_response += f"• Calories: {calories} kcal\n"
            formatted_response += f"• Protein: {protein}g\n\n"

            if confidence < 0.7:
                formatted_response += "📝 *Note: These estimates have moderate confidence. Double-check portions if possible.*\n\n"
            elif confidence < 0.9:
                formatted_response += "📊 *Good estimates based on standard nutrition data.*\n\n"

            formatted_response += "Keep up the great work! 💪"

        elif response_type == "nutrition_analytics":
            # Format nutrition analytics response (daily/weekly summaries)
            date_str = content.get("date", "")
            total_calories = content.get("total_calories", 0)
            total_protein = content.get("total_protein_g", 0)
            meals_logged = content.get("meals_logged", 0)
            
            # Handle weekly analytics
            if "period_days" in content:
                period_days = content.get("period_days", 7)
                avg_calories = content.get("avg_daily_calories", 0)
                avg_protein = content.get("avg_daily_protein", 0)
                total_meals = content.get("total_meals", 0)
                
                formatted_response = f"📊 **Weekly Nutrition Summary**\n\n"
                formatted_response += f"**Period:** Last {period_days} days\n"
                formatted_response += f"**Total Meals:** {total_meals}\n"
                formatted_response += f"**Daily Average:**\n"
                formatted_response += f"• Calories: {avg_calories} kcal\n"
                formatted_response += f"• Protein: {avg_protein}g\n\n"
                
                if avg_calories > 0:
                    formatted_response += "Great progress! Keep tracking your meals! 💪"
                else:
                    formatted_response += "No meals logged this week yet. Let's get started! 🍎"
            else:
                # Daily summary
                formatted_response = f"📊 **Daily Nutrition Summary**\n\n"
                formatted_response += f"**Date:** {date_str}\n"
                formatted_response += f"**Meals Logged:** {meals_logged}\n"
                formatted_response += f"**Total:**\n"
                formatted_response += f"• Calories: {total_calories} kcal\n"
                formatted_response += f"• Protein: {total_protein}g\n\n"
                
                if total_calories > 0:
                    formatted_response += "You're doing great! Keep up the good work! 💪"
                else:
                    formatted_response += "No meals logged today yet. What have you eaten? 🍽️"

        elif response_type == "batch_collection":
            # Format batch collection prompt
            item_count = content.get("current_count", 0)
            meal_type = content.get("meal_type", "meal")

            if item_count == 0:
                formatted_response = f"Great! Let's log your {meal_type}. What did you eat?"
            else:
                formatted_response = f"Added to your {meal_type}. Total items: {item_count}. Anything else?"

        elif response_type == "batch_complete":
            # Format batch completion confirmation
            meal_type = content.get("meal_type", "meal")
            formatted_response = f"Got it! Processing your complete {meal_type} now..."

        elif response_type == "general_help":
            # Format general help response
            formatted_response = """👋 Hi! I'm your weight loss assistant!

**I can help you track:**
• **Meals**: "I ate scrambled eggs and toast"
• **Workouts**: "I did 3 sets of squats"
• **Wellness**: "I slept 8 hours and drank 6 glasses of water"
• **Progress**: "Show me my weekly summary"

Just type what you want to track!"""

        elif response_type == "error":
            # Format error response
            error_msg = content.get("error", "Something went wrong")
            formatted_response = f"😅 {error_msg}\n\nPlease try again or contact support if the problem persists."

        else:
            # Generic formatting
            text = content.get("text", "")
            formatted_response = text

        return {
            "formatted_response": formatted_response,
            "response_type": response_type,
            "tone": "supportive"  # Could be dynamic based on sentiment
        }

    except Exception as e:
        logger.error(f"Response formatting failed: {e}")
        return {
            "formatted_response": "I'm sorry, I had trouble formatting the response. Please try again.",
            "response_type": "error",
            "error": str(e)
        }


__all__ = ['format_response']