"""
Fitness agent for Weight Loss Chat Agent using Google ADK.

This agent processes complete workout batches using Google ADK LlmAgent.
"""

import sys
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from config import settings as Config
from config.logging import get_logger
from tools.fitness.batch_parser import parse_workout_batch
from tools.fitness.calculator import calculate_workout_volume
from tools.fitness.progress import suggest_workout_progression
from tools.fitness.workout_storage import store_workout_log
from database.workout_manager import workout_manager

# Import Google ADK
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from config.gemini import PatchedGemini

# Custom FunctionTool with manual declaration
class ManualFunctionTool(FunctionTool):
    def __init__(self, func, declaration_dict):
        super().__init__(func)
        from google.genai.types import FunctionDeclaration, Schema
        from google.genai.types import Type as GenaiType
        
        # Convert dict to proper ADK objects
        params_schema = Schema(
            type=GenaiType.OBJECT,
            properties={
                param_name: Schema(
                    type=self._map_type(param_info.get('type', 'string')),
                    description=param_info.get('description', ''),
                    enum=param_info.get('enum'),
                    default=param_info.get('default')
                ) if isinstance(param_info, dict) else Schema(type=self._map_type(param_info))
                for param_name, param_info in declaration_dict['parameters']['properties'].items()
            },
            required=declaration_dict['parameters'].get('required', [])
        )
        
        self._manual_declaration = FunctionDeclaration(
            name=declaration_dict['name'],
            description=declaration_dict['description'],
            parameters=params_schema
        )
    
    def _map_type(self, type_str):
        from google.genai.types import Type as GenaiType
        type_map = {
            'string': GenaiType.STRING,
            'integer': GenaiType.INTEGER,
            'number': GenaiType.NUMBER,
            'boolean': GenaiType.BOOLEAN,
            'array': GenaiType.ARRAY,
            'object': GenaiType.OBJECT
        }
        return type_map.get(type_str.lower(), GenaiType.STRING)
    
    def _get_declaration(self):
        return self._manual_declaration

logger = get_logger(__name__)

# Logging wrapper functions for tools
async def logged_parse_workout_batch(exercise_descriptions: str, tool_context=None):
    """Wrapper for workout batch parsing with logging."""
    # Extract user_id from tool_context
    user_id = tool_context.session.user_id if tool_context and hasattr(tool_context, 'session') and tool_context.session else 'unknown'
    
    # Parse the JSON string back to list
    import json
    try:
        descriptions_list = json.loads(exercise_descriptions)
    except:
        descriptions_list = [exercise_descriptions]  # fallback to single string
    
    logger.info(f"🏋️ Parsing workout batch: {descriptions_list}, user_id: {user_id}")
    result = await parse_workout_batch(descriptions_list, user_id, tool_context)
    logger.info(f"📋 Workout batch parsing result: {result}")
    return result

async def logged_calculate_workout_volume(parsed_exercises_json: str, tool_context=None):
    """Wrapper for volume calculation with logging."""
    # Extract user_id from tool_context
    user_id = tool_context.session.user_id if tool_context and hasattr(tool_context, 'session') and tool_context.session else 'unknown'
    
    # Parse the JSON string back to list of dicts
    import json
    try:
        parsed_exercises = json.loads(parsed_exercises_json)
    except:
        logger.error(f"Failed to parse parsed_exercises_json: {parsed_exercises_json}")
        return {"status": "error", "error": "Invalid JSON format for exercises"}
    
    logger.info(f"📊 Calculating workout volume: {len(parsed_exercises)} exercises, user_id: {user_id}")
    result = await calculate_workout_volume(parsed_exercises, user_id, tool_context)
    logger.info(f"💪 Volume calculation result: {result}")
    return result

async def logged_suggest_workout_progression(current_exercises_json: str, workout_history=None, user_profile=None, tool_context=None):
    """Wrapper for progression suggestions with logging."""
    # Extract user_id from tool_context
    user_id = tool_context.session.user_id if tool_context and hasattr(tool_context, 'session') and tool_context.session else 'unknown'
    
    # Parse the JSON string back to list of dicts
    import json
    try:
        current_exercises = json.loads(current_exercises_json)
    except:
        logger.error(f"Failed to parse current_exercises_json: {current_exercises_json}")
        return {"status": "error", "error": "Invalid JSON format for exercises"}
    
    logger.info(f"📈 Generating progression suggestions for user {user_id}: {len(current_exercises)} exercises")
    result = await suggest_workout_progression(current_exercises, user_id, workout_history, user_profile, tool_context)
    logger.info(f"🎯 Progression suggestions result: {result}")
    return result

async def logged_store_workout_log(exercises_json: str, total_volume: int, progression_suggestion: str = None, tool_context=None):
    """Wrapper for workout storage with logging."""
    # Extract user_id from tool_context
    user_id = tool_context.session.user_id if tool_context and hasattr(tool_context, 'session') and tool_context.session else 'unknown'
    
    # Parse the JSON string back to list of dicts
    import json
    try:
        exercises = json.loads(exercises_json)
    except:
        logger.error(f"Failed to parse exercises_json: {exercises_json}")
        return {"status": "error", "error": "Invalid JSON format for exercises"}
    
    logger.info(f"💾 Storing workout log for user {user_id}: {total_volume} volume, {len(exercises)} exercises")
    result = await store_workout_log(user_id, exercises, total_volume, progression_suggestion, tool_context)
    logger.info(f"✅ Workout storage result: {result}")
    return result

def logged_get_workout_summary(period: str = "today", tool_context=None):
    """Wrapper for workout summary queries with logging."""
    # Extract user_id from tool_context
    user_id = tool_context.session.user_id if tool_context and hasattr(tool_context, 'session') and tool_context.session else 'unknown'
    
    logger.info(f"📊 Getting workout summary for user {user_id}, period: {period}")
    
    try:
        if period.lower() in ["today", "day"]:
            result = workout_manager.get_daily_workout_summary(user_id, date.today())
        elif period.lower() in ["week", "weekly", "this week"]:
            result = workout_manager.get_workout_analytics(user_id, days=7)
        else:
            # Default to today
            result = workout_manager.get_daily_workout_summary(user_id, date.today())
            
        logger.info(f"📈 Workout summary result: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to get workout summary: {e}")
        return {"status": "error", "error": str(e)}

# Define tools for fitness agent
batch_parser_tool = FunctionTool(func=logged_parse_workout_batch)
volume_calculator_tool = FunctionTool(func=logged_calculate_workout_volume)
progression_tool = ManualFunctionTool(
    func=logged_suggest_workout_progression,
    declaration_dict={
        "name": "logged_suggest_workout_progression",
        "description": "Generate personalized workout progression suggestions based on current exercises",
        "parameters": {
            "type": "object",
            "properties": {
                "current_exercises_json": {
                    "type": "string",
                    "description": "JSON string containing the current workout exercises"
                }
            },
            "required": ["current_exercises_json"]
        }
    }
)
workout_summary_tool = FunctionTool(func=logged_get_workout_summary)
workout_storage_tool = FunctionTool(func=logged_store_workout_log)

fitness_agent = LlmAgent(
    name="fitness_agent",
    model=PatchedGemini(model=Config.gemini_model),
    description="Fitness coach that helps users log individual workouts and provides workout analytics. Processes exercise data from conversations and provides workout summaries and progress tracking.",
    instruction="""
    You are a friendly fitness coach helping users track their individual workouts and view their progress.

    WORKOUT PROCESSING:
    - Accept natural descriptions: "squats 3 sets of 10 reps at 185 pounds"
    - Parse automatically using parse_workout_batch tool
    - Calculate volume using calculate_workout_volume
    - Store the workout using store_workout_log
    - Provide progression suggestions and summary

    ANALYTICS QUERIES:
    - Handle requests for workout summaries: "how many workouts this week", "my exercise progress"
    - For "today", "this day", "daily" → get daily workout summary
    - For "week", "weekly", "this week" → get 7-day workout analytics
    - Always include user_id in queries
    - Provide workout summaries in friendly, encouraging messages

    EXERCISE PARSING:
    - Accept natural descriptions: "squats 3 sets of 10 reps at 185 pounds"
    - Parse automatically using parse_workout_batch tool
    - Handle multiple exercises in one message
    - Ask for clarification if needed

    WORKFLOW FOR WORKOUT LOGGING:
    When receiving a workout message:
    1. Parse the exercise descriptions using parse_workout_batch (pass exercise_descriptions as JSON string)
    2. Calculate volume using calculate_workout_volume (pass parsed_exercises as JSON string)
    3. Store the workout using store_workout_log (pass exercises as JSON string, total_volume as integer)
    4. Provide progression suggestions and summary

    IMPORTANT: When calling tools, convert complex data structures to JSON strings:
    - For parse_workout_batch: pass exercise_descriptions as a JSON array string like '["squats 3x10", "bench press 4x8"]'
    - For calculate_workout_volume: pass parsed_exercises as a JSON string of the exercise objects
    - For store_workout_log: pass exercises as a JSON string of the exercise objects
    - For suggest_workout_progression: pass current_exercises as a JSON string of the exercises

    TOOLS: Call when ready to process workout data
    - parse_workout_batch: Convert exercise descriptions to structured data (expects JSON string of descriptions)
    - calculate_workout_volume: Get total volume and metrics (expects JSON string of parsed exercises)
    - suggest_workout_progression: Personalized improvement recommendations (expects JSON string of exercises)
    - logged_get_workout_summary: Get daily/weekly workout summaries and analytics
    - logged_store_workout_log: Store calculated workout data in database (expects JSON string of exercises)

    RESPONSE STYLE:
    - Friendly and encouraging
    - Provide detailed summary with volume, feedback, and next suggestions
    - Use emojis sparingly (1-2 per response)

    CRITICAL: Process each workout message individually using the tools in sequence.
    """,
    tools=[
        batch_parser_tool,
        volume_calculator_tool,
        progression_tool,
        workout_summary_tool,
        workout_storage_tool,
    ],
)

__all__ = ["fitness_agent"]