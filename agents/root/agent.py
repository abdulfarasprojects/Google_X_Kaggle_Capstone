"""
Root Agent for Weight Loss Chat Agent using Google ADK.

This is the main orchestrator agent that routes user messages to appropriate
sub-agents based on intent and user state using Google ADK LlmAgent.
"""

import sys
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from config import settings as Config
from config.logging import get_logger
from tools.intent_classifier import classify_intent
from tools.sentiment_detector import detect_sentiment
from tools.response_formatter import format_response
from tools.batch_state_manager import get_batch_state, update_batch_state

# Import sub-agents
from agents.nutrition.agent import nutrition_agent
from agents.fitness.agent import fitness_agent
from agents.wellness.agent import wellness_agent
from agents.nudge.agent import nudge_agent
from agents.analytics.agent import analytics_agent

# Import Google ADK
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
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
async def logged_classify_intent(query: str, context: Optional[Dict[str, Any]] = None, tool_context: Optional[ToolContext] = None):
    """Wrapper for intent classification with logging."""
    logger.info(f"🔍 Classifying intent with query: {query}, context: {context}")
    result = await classify_intent(query, context, tool_context)
    logger.info(f"📋 Intent classification result: {result}")
    return result

async def logged_detect_sentiment(query: str, context: Optional[Dict[str, Any]] = None, tool_context: Optional[ToolContext] = None):
    """Wrapper for sentiment detection with logging."""
    logger.info(f"😊 Detecting sentiment with query: {query}, context: {context}")
    result = await detect_sentiment(query, context, tool_context)
    logger.info(f"📊 Sentiment detection result: {result}")
    return result

async def logged_format_response(response_type: str, content: Dict[str, Any], user_context: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None, tool_context: Optional[ToolContext] = None):
    """Wrapper for response formatting with logging."""
    logger.info(f"📝 Formatting response with response_type: {response_type}, content: {content}")
    result = await format_response(response_type, content, user_context, context, tool_context)
    logger.info(f"💬 Response formatting result: {result}")
    return result

async def logged_get_batch_state(context: Optional[Dict[str, Any]] = None, tool_context: Optional[ToolContext] = None):
    """Wrapper for batch state management with logging."""
    logger.info(f"📦 Getting batch state with context: {context}")
    result = await get_batch_state(context, tool_context)
    logger.info(f"📋 Batch state result: {result}")
    return result

async def logged_call_nutrition_agent(query: str, context: Optional[Dict[str, Any]] = None, tool_context: Optional[ToolContext] = None):
    """Wrapper for calling nutrition agent with logging."""
    logger.info(f"🍽️ Calling nutrition agent with query: {query}")
    # Use the ADK runner to run the nutrition agent
    from adk_integration import agent_runner
    try:
        response = await agent_runner.process_message(
            user_id="system",  # Use system user for agent-to-agent calls
            message=query,
            session_id=f"nutrition_{query[:20]}",
            context=context
        )
        logger.info(f"🍽️ Nutrition agent response: {response.get('text', '')[:100]}...")
        return {"response": response.get('text', ''), "agent": "nutrition"}
    except Exception as e:
        logger.error(f"Error calling nutrition agent: {e}")
        return {"response": f"Error processing nutrition request: {str(e)}", "agent": "nutrition"}

async def logged_call_fitness_agent(query: str, context: Optional[Dict[str, Any]] = None, tool_context: Optional[ToolContext] = None):
    """Wrapper for calling fitness agent with logging."""
    logger.info(f"💪 Calling fitness agent with query: {query}")
    from adk_integration import agent_runner
    try:
        response = await agent_runner.process_message(
            user_id="system",
            message=query,
            session_id=f"fitness_{query[:20]}",
            context=context
        )
        logger.info(f"💪 Fitness agent response: {response.get('text', '')[:100]}...")
        return {"response": response.get('text', ''), "agent": "fitness"}
    except Exception as e:
        logger.error(f"Error calling fitness agent: {e}")
        return {"response": f"Error processing fitness request: {str(e)}", "agent": "fitness"}

async def logged_call_wellness_agent(query: str, context: Optional[Dict[str, Any]] = None, tool_context: Optional[ToolContext] = None):
    """Wrapper for calling wellness agent with logging."""
    logger.info(f"😴 Calling wellness agent with query: {query}")
    from adk_integration import agent_runner
    try:
        response = await agent_runner.process_message(
            user_id="system",
            message=query,
            session_id=f"wellness_{query[:20]}",
            context=context
        )
        logger.info(f"😴 Wellness agent response: {response.get('text', '')[:100]}...")
        return {"response": response.get('text', ''), "agent": "wellness"}
    except Exception as e:
        logger.error(f"Error calling wellness agent: {e}")
        return {"response": f"Error processing wellness request: {str(e)}", "agent": "wellness"}

async def logged_call_analytics_agent(query: str, context: Optional[Dict[str, Any]] = None, tool_context: Optional[ToolContext] = None):
    """Wrapper for calling analytics agent with logging."""
    logger.info(f"📊 Calling analytics agent with query: {query}")
    from adk_integration import agent_runner
    try:
        response = await agent_runner.process_message(
            user_id="system",
            message=query,
            session_id=f"analytics_{query[:20]}",
            context=context
        )
        logger.info(f"📊 Analytics agent response: {response.get('text', '')[:100]}...")
        return {"response": response.get('text', ''), "agent": "analytics"}
    except Exception as e:
        logger.error(f"Error calling analytics agent: {e}")
        return {"response": f"Error processing analytics request: {str(e)}", "agent": "analytics"}

# Import sub-agent tools directly
from tools.nutrition.batch_parser import parse_meal_batch
from tools.nutrition.calculator import calculate_meal_nutrition
from tools.nutrition.meal_storage import store_meal_log
from database.meal_manager import meal_manager

# Import fitness tools
from tools.fitness.batch_parser import parse_workout_batch
from tools.fitness.calculator import calculate_workout_volume
from tools.fitness.progress import suggest_workout_progression
from tools.fitness.workout_storage import store_workout_log
from database.workout_manager import workout_manager

# Logging wrapper functions for sub-agent tools
async def logged_parse_meal_batch(food_items: str, meal_type: str = "lunch", tool_context=None):
    """Wrapper for meal batch parsing with logging."""
    # Extract user_id from tool_context
    user_id = tool_context.session.user_id if tool_context and hasattr(tool_context, 'session') and tool_context.session else 'unknown'
    
    logger.info(f"🍽️ Parsing meal batch: {food_items}, meal_type: {meal_type}, user_id: {user_id}")
    # Convert string to list if needed
    if isinstance(food_items, str):
        food_items = [item.strip() for item in food_items.split(',') if item.strip()]
    
    result = await parse_meal_batch(food_items, meal_type, user_id, tool_context)
    logger.info(f"📋 Meal batch parsing result: {result}")
    return result

async def logged_calculate_meal_nutrition(parsed_items_json: str, meal_type: str = "lunch", tool_context=None):
    """Wrapper for nutrition calculation with logging."""
    # Extract user_id from tool_context
    user_id = tool_context.session.user_id if tool_context and hasattr(tool_context, 'session') and tool_context.session else 'unknown'
    
    logger.info(f"🧮 Calculating meal nutrition: {parsed_items_json}, meal_type: {meal_type}, user_id: {user_id}")
    
    # Parse JSON string to list
    try:
        import json
        parsed_items = json.loads(parsed_items_json)
        if not isinstance(parsed_items, list):
            parsed_items = [parsed_items]  # Handle single item
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to parse parsed_items_json: {e}")
        return {"status": "error", "error": f"Invalid parsed_items format: {str(e)}"}
    
    result = await calculate_meal_nutrition(parsed_items, meal_type, user_id, tool_context)
    logger.info(f"📊 Nutrition calculation result: {result}")
    return result

async def logged_store_meal(meal_type: str, food_items: str, total_calories: float, total_protein: float, confidence: float = 0.8, tool_context=None):
    """Wrapper for storing meal with logging."""
    # Extract user_id from tool_context
    user_id = tool_context.session.user_id if tool_context and hasattr(tool_context, 'session') and tool_context.session else 'unknown'
    
    logger.info(f"💾 Storing meal for user {user_id}: {meal_type}, {total_calories} cal, {total_protein}g protein")
    
    # Convert food_items string to list format expected by store_meal_log
    if isinstance(food_items, str):
        # Simple parsing - assume comma-separated food names
        food_names = [item.strip() for item in food_items.split(',') if item.strip()]
        food_list = []
        for name in food_names:
            food_list.append({
                "food_name": name,
                "calories": total_calories / len(food_names) if food_names else total_calories,
                "protein_g": total_protein / len(food_names) if food_names else total_protein,
                "confidence": confidence,
                "source": "estimated"
            })
    else:
        food_list = food_items
    
    result = meal_manager.create_meal_log(user_id, meal_type, food_list, total_calories, total_protein, confidence)
    logger.info(f"✅ Meal storage result: {result}")
    return result

async def logged_get_nutrition_summary(period: str = "today", tool_context=None):
    """Wrapper for nutrition summary with logging."""
    # Extract user_id from tool_context
    user_id = tool_context.session.user_id if tool_context and hasattr(tool_context, 'session') and tool_context.session else 'unknown'
    
    logger.info(f"📊 Getting nutrition summary for user {user_id}, period: {period}")
    
    try:
        if period.lower() in ["today", "day"]:
            result = meal_manager.get_daily_nutrition_summary(user_id, date.today())
        elif period.lower() in ["week", "weekly", "this week"]:
            result = meal_manager.get_nutrition_analytics(user_id, days=7)
        else:
            result = meal_manager.get_daily_nutrition_summary(user_id, date.today())
        
        logger.info(f"📈 Nutrition summary result: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to get nutrition summary: {e}")
        return {"status": "error", "error": str(e)}

# Fitness logging wrapper functions
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
    
    logger.info(f"🧮 Calculating workout volume: {parsed_exercises_json}, user_id: {user_id}")
    
    # Parse JSON string to list
    try:
        import json
        parsed_exercises = json.loads(parsed_exercises_json)
        if not isinstance(parsed_exercises, list):
            parsed_exercises = [parsed_exercises]  # Handle single item
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to parse parsed_exercises_json: {e}")
        return {"status": "error", "error": f"Invalid parsed_exercises format: {str(e)}"}
    
    result = await calculate_workout_volume(parsed_exercises, user_id, tool_context)
    logger.info(f"📊 Workout volume calculation result: {result}")
    return result

async def logged_suggest_workout_progression(current_exercises_json: str, tool_context=None):
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
    result = await suggest_workout_progression(current_exercises, user_id, None, None, tool_context)
    logger.info(f"🎯 Progression suggestions result: {result}")
    return result

async def logged_store_workout_log(exercises_json: str, total_volume: int, tool_context=None):
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
    result = await store_workout_log(user_id, exercises, total_volume, None, tool_context)
    logger.info(f"✅ Workout storage result: {result}")
    return result

async def logged_get_workout_summary(period: str = "today", tool_context=None):
    """Wrapper for workout summary with logging."""
    # Extract user_id from tool_context
    user_id = tool_context.session.user_id if tool_context and hasattr(tool_context, 'session') and tool_context.session else 'unknown'
    
    logger.info(f"📊 Getting workout summary for user {user_id}, period: {period}")
    
    try:
        if period.lower() in ["today", "day"]:
            result = workout_manager.get_daily_workout_summary(user_id, date.today())
        elif period.lower() in ["week", "weekly", "this week"]:
            result = workout_manager.get_workout_analytics(user_id, days=7)
        else:
            result = workout_manager.get_daily_workout_summary(user_id, date.today())
        
        logger.info(f"📈 Workout summary result: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to get workout summary: {e}")
        return {"status": "error", "error": str(e)}

# Define tools for root agent
intent_tool = FunctionTool(func=logged_classify_intent)
sentiment_tool = FunctionTool(func=logged_detect_sentiment)
response_tool = FunctionTool(func=logged_format_response)
batch_state_tool = FunctionTool(func=logged_get_batch_state)

# Define additional tools for root agent
meal_parser_tool = FunctionTool(func=logged_parse_meal_batch)
meal_calculator_tool = ManualFunctionTool(
    func=logged_calculate_meal_nutrition,
    declaration_dict={
        "name": "logged_calculate_meal_nutrition",
        "description": "Calculate nutrition information for parsed food items",
        "parameters": {
            "type": "object",
            "properties": {
                "parsed_items_json": {
                    "type": "string",
                    "description": "JSON string containing the parsed food items from meal parsing"
                },
                "meal_type": {
                    "type": "string",
                    "enum": ["breakfast", "lunch", "dinner", "snack"],
                    "description": "Type of meal"
                }
            },
            "required": ["parsed_items_json", "meal_type"]
        }
    }
)
meal_storage_tool = FunctionTool(func=logged_store_meal)
nutrition_summary_tool = FunctionTool(func=logged_get_nutrition_summary)

# Fitness tools
workout_parser_tool = FunctionTool(func=logged_parse_workout_batch)
workout_calculator_tool = FunctionTool(func=logged_calculate_workout_volume)
workout_progression_tool = ManualFunctionTool(
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
workout_storage_tool = FunctionTool(func=logged_store_workout_log)
workout_summary_tool = FunctionTool(func=logged_get_workout_summary)

# Create Root Agent
root_agent = LlmAgent(
    name="weight_loss_coach_root",
    model=PatchedGemini(model=Config.gemini_model),
    description="Main orchestrator for weight loss tracking via Telegram. Routes user requests to specialized agents (Nutrition, Fitness, Wellness).",
    instruction="""
    You are a supportive, non-judgmental weight loss coach assistant on Telegram.
    
    YOUR RESPONSIBILITIES:
    1. Check if user has a profile - if not, handle onboarding conversation directly
    2. Understand user intent (logging meals, workouts, asking questions, viewing progress)
    3. Detect emotional state and respond with empathy
    4. For NUTRITION intent: Process meal logging using ONLY the direct meal processing tools
       - NEVER call sub-agents like logged_call_nutrition_agent
       - ALWAYS use logged_parse_meal_batch to parse food items
       - ALWAYS use logged_calculate_meal_nutrition to calculate nutrition
       - ALWAYS use logged_store_meal to save the meal to database
       - Use logged_get_nutrition_summary to get progress info
    5. For FITNESS intent: Process workout logging using ONLY the direct workout processing tools
       - NEVER transfer to sub-agents like fitness_agent
       - ALWAYS use logged_parse_workout_batch to parse exercise descriptions
       - ALWAYS use logged_calculate_workout_volume to calculate workout volume
       - ALWAYS use logged_suggest_workout_progression to get progression suggestions
       - ALWAYS use logged_store_workout_log to save the workout to database
       - Use logged_get_workout_summary to get workout progress info
    6. For ANALYTICS intent: Use nutrition and workout summary tools for progress analysis
       - Handle queries like "how am I doing this week", "show my progress", "what's my streak"
    7. Synthesize responses into single supportive message
    
    MEAL LOGGING WORKFLOW:
    When user mentions food (like "pizza", "ate eggs", "lunch was salad"):
    CRITICAL: You MUST follow this exact sequence and call ALL tools before responding:
    1. Call logged_parse_meal_batch to parse the food items
    2. Call logged_calculate_meal_nutrition with parsed_items_json as a JSON string. Take the 'parsed_items' array from step 1 and convert it to JSON format: "[{\"description\": \"pizza\", \"quantity\": 1.0, \"unit\": \"piece\", \"parsed_food\": \"pizza\", \"confidence\": 0.5}]"
    3. Call logged_store_meal to save the meal data
    4. ONLY THEN generate a final response to the user
    
    WORKOUT LOGGING WORKFLOW:
    When user mentions exercises (like "squats 3 sets of 10", "bench press 4x8", "ran 5 miles"):
    CRITICAL: You MUST follow this exact sequence and call ALL tools before responding:
    1. Call logged_parse_workout_batch to parse the exercise descriptions (pass as JSON array string)
    2. Call logged_calculate_workout_volume with parsed_exercises_json as a JSON string from step 1
    3. Call logged_suggest_workout_progression with current_exercises_json as a JSON string from step 1
    4. Call logged_store_workout_log to save the workout data (pass exercises as JSON string and total_volume as integer)
    5. ONLY THEN generate a final response to the user
    
    IMPORTANT: Do NOT respond to the user until you have called ALL tools in sequence for each workflow.
    Do NOT stop after the first tool call. You MUST complete the entire workflow.
    
    CRITICAL JSON FORMATTING: All JSON parameters MUST be valid JSON strings. Do not pass Python list syntax. Always use proper JSON formatting with double quotes.
    
    IMPORTANT RULES:
    - NEVER call logged_call_nutrition_agent, logged_call_fitness_agent or any sub-agent functions
    - NEVER transfer to sub-agents - handle everything directly with tools
    - ONLY use the direct processing tools for meals and workouts
    - Always complete the full workflow: parse -> calculate -> suggest -> store -> respond
    - For analytics queries: Use logged_get_nutrition_summary and logged_get_workout_summary
    
    ONBOARDING FLOW:
    - If user says "start" or has no profile: "Welcome! What's your age?"
    - After age: "Thanks! What's your height in cm?"
    - After height: "Perfect! What's your current weight in kg?"
    - After weight: "Great! What's your target weight?"
    - After target: Show activity options and calculate calories
    - After activity: Show profile summary and ask for confirmation
    - After confirmation: Save profile and welcome user
    
    TONE: Supportive coach, warm, encouraging. Use 1-2 emojis max per message.
    
    CRITICAL: 
    - Handle onboarding directly without calling tools
    - For nutrition/food logging: ONLY use the direct meal processing tools (parse, calculate, store)
    - For fitness/workout logging: ONLY use the direct workout processing tools (parse, calculate, suggest, store)
    - For analytics queries: Use summary tools
    - NEVER call sub-agents or transfer to them
    
    IMPORTANT: After calling tools, you MUST generate a final response message to the user. Do not end with tool calls - always provide a complete response.
    Always respond with a complete, helpful message that answers the user's question.
    
    """,
    tools=[
        intent_tool,
        sentiment_tool,
        response_tool,
        meal_parser_tool,
        meal_calculator_tool,
        meal_storage_tool,
        nutrition_summary_tool,
        workout_parser_tool,
        workout_calculator_tool,
        workout_progression_tool,
        workout_storage_tool,
        workout_summary_tool,
    ],
    sub_agents=[],  # Handle everything directly with tools, no sub-agent transfers
)