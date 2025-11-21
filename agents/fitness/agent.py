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

# Observability imports
from observability.tracing import traced
from observability.metrics import record_request, record_response_time, record_error

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
        
        try:
            # Convert dict to proper ADK objects
            params_schema = Schema(
                type=GenaiType.OBJECT,
                properties={
                    param_name: Schema(
                        type=self._map_type(param_info.get('type', 'string')),
                        description=param_info.get('description', ''),
                        enum=param_info.get('enum'),
                        default=param_info.get('default'),
                        # Ensure minimum/maximum are converted to proper types
                        minimum=self._convert_constraint(param_info.get('minimum'), self._map_type(param_info.get('type', 'string'))),
                        maximum=self._convert_constraint(param_info.get('maximum'), self._map_type(param_info.get('type', 'string')))
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
        except Exception as e:
            logger.error(f"Error creating ManualFunctionTool schema: {e}")
            # Fallback to simple schema
            params_schema = Schema(
                type=GenaiType.OBJECT,
                properties={
                    param_name: Schema(
                        type=self._map_type(param_info.get('type', 'string') if isinstance(param_info, dict) else 'string'),
                        description=param_info.get('description', '') if isinstance(param_info, dict) else ''
                    )
                    for param_name, param_info in declaration_dict['parameters']['properties'].items()
                },
                required=declaration_dict['parameters'].get('required', [])
            )
            self._manual_declaration = FunctionDeclaration(
                name=declaration_dict['name'],
                description=declaration_dict['description'],
                parameters=params_schema
            )
    
    def _convert_constraint(self, value, genai_type):
        """Convert minimum/maximum constraint to proper type."""
        if value is None:
            return None
        try:
            from google.genai.types import Type as GenaiType
            if genai_type == GenaiType.INTEGER:
                return int(value) if value is not None else None
            elif genai_type == GenaiType.NUMBER:
                return float(value) if value is not None else None
            return value
        except Exception as e:
            logger.warning(f"Failed to convert constraint {value}: {e}")
            return None
    
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
@traced("parse_workout_batch")
async def logged_parse_workout_batch(exercise_descriptions: str, tool_context=None):
    """Wrapper for workout batch parsing with logging."""
    try:
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
    except TypeError as e:
        if "'<=' not supported" in str(e) or "not supported between instances" in str(e):
            logger.warning(f"Type comparison error in parse_workout_batch: {e}")
            return {"status": "error", "error": "Processing error, please try again"}
        raise
    except Exception as e:
        logger.error(f"Error in parse_workout_batch: {e}")
        return {"status": "error", "error": str(e)}

@traced("calculate_workout_volume")
async def logged_calculate_workout_volume(parsed_exercises_json: str, tool_context=None):
    """Wrapper for volume calculation with logging."""
    try:
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
    except TypeError as e:
        if "'<=' not supported" in str(e) or "not supported between instances" in str(e):
            logger.warning(f"Type comparison error in calculate_workout_volume: {e}")
            return {"status": "error", "error": "Processing error, please try again"}
        raise
    except Exception as e:
        logger.error(f"Error in calculate_workout_volume: {e}")
        return {"status": "error", "error": str(e)}

@traced("suggest_workout_progression")
async def logged_suggest_workout_progression(current_exercises_json: str, workout_history=None, user_profile=None, tool_context=None):
    """Wrapper for progression suggestions with logging."""
    try:
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
    except TypeError as e:
        if "'<=' not supported" in str(e) or "not supported between instances" in str(e):
            logger.warning(f"Type comparison error in suggest_workout_progression: {e}")
            return {"status": "error", "error": "Processing error, please try again"}
        raise
    except Exception as e:
        logger.error(f"Error in suggest_workout_progression: {e}")
        return {"status": "error", "error": str(e)}

@traced("store_workout_log")
async def logged_store_workout_log(exercises_json: str, total_volume: int, progression_suggestion: str = "", tool_context=None):
    """Wrapper for workout storage with logging."""
    try:
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
    except TypeError as e:
        if "'<=' not supported" in str(e) or "not supported between instances" in str(e):
            logger.warning(f"Type comparison error in store_workout_log: {e}")
            return {"status": "error", "error": "Processing error, please try again"}
        raise
    except Exception as e:
        logger.error(f"Error in store_workout_log: {e}")
        return {"status": "error", "error": str(e)}

@traced("get_workout_summary")
def logged_get_workout_summary(period: str = "today", tool_context=None):
    """Wrapper for workout summary queries with logging."""
    try:
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
    except TypeError as e:
        if "'<=' not supported" in str(e) or "not supported between instances" in str(e):
            logger.warning(f"Type comparison error in get_workout_summary: {e}")
            return {"status": "error", "error": "Processing error, please try again"}
        raise

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
workout_storage_tool = ManualFunctionTool(
    func=logged_store_workout_log,
    declaration_dict={
        "name": "logged_store_workout_log",
        "description": "Store a workout log with calculated volume and optional progression suggestions",
        "parameters": {
            "type": "object",
            "properties": {
                "exercises_json": {
                    "type": "string",
                    "description": "JSON string containing the workout exercises"
                },
                "total_volume": {
                    "type": "integer",
                    "description": "Total calculated workout volume"
                },
                "progression_suggestion": {
                    "type": "string",
                    "description": "Optional progression suggestion for the workout",
                    "default": ""
                }
            },
            "required": ["exercises_json", "total_volume"]
        }
    }
)

fitness_agent = LlmAgent(
    name="fitness_agent",
    model=PatchedGemini(model=Config.gemini_model),
    description="Fitness specialist that helps users log workouts and provides workout analytics. Receives exercise data from Root Agent via transfer_to_agent(), calculates volume, and provides workout summaries and progress tracking.",
    instruction="""
    You are a fitness specialist sub-agent that processes workout messages and provides workout analytics.
    
    CONTEXT: You are called from the Root Agent when the user's intent is classified as FITNESS.
    The Root Agent will transfer the user's message to you using transfer_to_agent().
    Your job is to process the fitness request and return results to the Root Agent.
    
    YOUR RESPONSIBILITIES:
    1. Parse exercise descriptions from the user's message
    2. Calculate workout volume (sets × reps × weight)
    3. Store the workout data in the database
    4. Provide progression suggestions
    5. Provide friendly summary/response to user
    
    EXERCISE PARSING:
    - Accept natural descriptions: "squats 3 sets of 10 reps at 185 pounds"
    - Handle multiple exercises in one message
    - Ask for clarification if needed
    - Support various formats (3x10, 3 sets of 10, etc.)
    
    WORKOUT PROCESSING WORKFLOW:
    When receiving a workout message from Root Agent:
    1. Parse exercise descriptions using logged_parse_workout_batch
    2. Calculate volume using logged_calculate_workout_volume
    3. Generate progression suggestions using logged_suggest_workout_progression
    4. Store the workout using logged_store_workout_log
    5. Provide a friendly summary with volume and progression tips
    
    WORKOUT ANALYTICS QUERIES:
    - Handle requests like: "how many workouts this week", "my exercise progress"
    - For "today", "this day", "daily" → get daily workout summary
    - For "week", "weekly", "this week" → get 7-day workout analytics
    - Provide workout summaries with encouraging feedback
    
    TOOLS AVAILABLE:
    - logged_parse_workout_batch: Parse exercise descriptions
    - logged_calculate_workout_volume: Calculate total volume and metrics
    - logged_suggest_workout_progression: Get personalized progression suggestions
    - logged_get_workout_summary: Get daily/weekly workout summaries
    - logged_store_workout_log: Store calculated workout data in database
    
    RESPONSE GUIDELINES:
    - Always be encouraging and motivational
    - Provide specific volume totals when logging workouts
    - Include progression suggestions to help users improve
    - For analytics: Include streaks, total volume, and trends
    - Use 1-2 emojis max per response
    - Keep responses concise and action-oriented
    - Celebrate consistency and progress
    
    IMPORTANT NOTES:
    - You are a SUB-AGENT. Do not try to handle non-fitness requests.
    - If the user's request is not about fitness, clearly indicate that and the Root Agent 
      will reroute the request to the appropriate specialist.
    - When calling tools, convert complex data structures to JSON strings
    """,
    tools=[
        batch_parser_tool,
        volume_calculator_tool,
        progression_tool,
        workout_summary_tool,
        workout_storage_tool,
    ],
)

# Alias for ADK web server framework compatibility
root_agent = fitness_agent

__all__ = ["fitness_agent", "root_agent"]