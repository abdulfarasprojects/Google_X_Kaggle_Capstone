"""
Base agent framework for Weight Loss Chat Agent.

This module provides the foundational agent classes and utilities.
It implements the multi-agent architecture with base agent functionality,
tool calling, session management, and error handling.

Key components:
- BaseAgent: Abstract base class for all agents
- AgentRouter: Routes messages to appropriate sub-agents
- Tool infrastructure: Async tool calling with validation
- Session management: Conversation context and state
- Error handling: Graceful failure and user feedback
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass

from config.settings import settings
from database.init import get_db_session
from database.models import SessionState, ApiUsage

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    confidence: float = 1.0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AgentResponse:
    """Response from an agent."""
    text: str
    keyboard: Optional[Any] = None  # Telegram inline keyboard
    session_data: Optional[Dict[str, Any]] = None
    completed: bool = True


class BaseTool(ABC):
    """
    Abstract base class for agent tools.

    All tools must implement async execute method with proper error handling,
    timeouts, and result formatting.
    """

    def __init__(self, name: str, description: str, timeout_seconds: Optional[int] = None):
        self.name = name
        self.description = description
        self.timeout_seconds = timeout_seconds or settings.api_timeout_seconds

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            ToolResult: Execution result with success status and data
        """
        pass

    async def execute_with_timeout(self, **kwargs) -> ToolResult:
        """Execute tool with timeout protection."""
        try:
            return await asyncio.wait_for(
                self.execute(**kwargs),
                timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                error=f"Tool {self.name} timed out after {self.timeout_seconds} seconds"
            )
        except Exception as e:
            logger.error(f"Tool {self.name} execution error: {e}")
            return ToolResult(
                success=False,
                error=f"Tool execution failed: {str(e)}"
            )


class BaseAgent(ABC):
    """
    Abstract base agent class.

    Provides common functionality for all agents:
    - Tool calling infrastructure
    - Session state management
    - Error handling and logging
    - Response formatting
    """

    def __init__(self, name: str, description: str, tools: Optional[List[BaseTool]] = None):
        """
        Initialize agent.

        Args:
            name: Agent name
            description: Agent description
            tools: List of tools this agent can use
        """
        self.name = name
        self.description = description
        self.tools = tools or []

        logger.info(f"Initialized agent: {name}")

    @abstractmethod
    async def process_message(self, user_id: str, message: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """
        Process a user message and return response.

        Args:
            user_id: User identifier
            message: User message text
            context: Additional context (session data, etc.)

        Returns:
            AgentResponse: Formatted response for user
        """
        pass

    async def _get_session_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get current session data for user."""
        try:
            with get_db_session() as session:
                session_state = session.query(SessionState).filter_by(user_id=user_id).first()
                if session_state and session_state.expires_at > datetime.utcnow():
                    return {
                        "batch_type": session_state.batch_type,
                        "batch_items": session_state.batch_items_list,
                        "expires_at": session_state.expires_at.isoformat()
                    }
        except Exception as e:
            logger.error(f"Failed to get session data: {e}")
        return None
        """Get current session data for user."""
        try:
            with get_db_session() as session:
                session_state = session.query(SessionState).filter_by(user_id=user_id).first()
                if session_state and session_state.expires_at > datetime.utcnow():
                    return {
                        "batch_type": session_state.batch_type,
                        "batch_items": session_state.batch_items_list,
                        "expires_at": session_state.expires_at.isoformat()
                    }
        except Exception as e:
            logger.error(f"Failed to get session data: {e}")
        return None

    async def _update_session_data(self, user_id: str, session_data: Dict[str, Any]) -> None:
        """Update session data for user."""
        try:
            with get_db_session() as session:
                # Remove existing session
                session.query(SessionState).filter_by(user_id=user_id).delete()

                # Create new session if data provided
                if session_data:
                    expires_at = datetime.utcnow() + timedelta(hours=settings.session_timeout_hours)
                    session_state = SessionState(
                        batch_id=f"{user_id}_{datetime.utcnow().timestamp()}",
                        user_id=user_id,
                        batch_type=session_data.get("batch_type"),
                        batch_items=json.dumps(session_data.get("batch_items", [])),
                        expires_at=expires_at
                    )
                    session.add(session_state)
                session.commit()
        except Exception as e:
            logger.error(f"Failed to update session data: {e}")

    def _format_response(self, text: str, keyboard: Optional[Any] = None, session_data: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Format agent response."""
        return AgentResponse(
            text=text,
            keyboard=keyboard,
            session_data=session_data,
            completed=True
        )


class AgentRouter:
    """
    Routes messages to appropriate sub-agents.

    Manages the multi-agent architecture by analyzing user intent
    and routing to specialized agents (nutrition, fitness, wellness, etc.).
    """

    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.fallback_agent: Optional[BaseAgent] = None

    def register_agent(self, agent_type: str, agent: BaseAgent) -> None:
        """Register an agent for a specific type."""
        self.agents[agent_type] = agent
        logger.info(f"Registered agent: {agent_type}")

    def set_fallback_agent(self, agent: BaseAgent) -> None:
        """Set the fallback agent for unrecognized requests."""
        self.fallback_agent = agent

    async def route_message(self, user_id: str, message: str, telegram_context: Optional[Any] = None) -> AgentResponse:
        """
        Route message to appropriate agent.

        Args:
            user_id: User identifier
            message: User message
            telegram_context: Telegram update context

        Returns:
            AgentResponse: Response from appropriate agent
        """
        try:
            # Analyze message intent
            agent_type = await self._analyze_intent(user_id, message)

            # Get appropriate agent
            agent = self.agents.get(agent_type, self.fallback_agent)

            if not agent:
                return AgentResponse(
                    text="I'm not sure how to help with that. Try /help for available options.",
                    completed=True
                )

            # Process message with agent
            context = {"telegram_context": telegram_context}
            response = await agent.process_message(user_id, message, context)

            return response

        except Exception as e:
            logger.error(f"Message routing failed: {e}")
            return AgentResponse(
                text="Sorry, I encountered an error processing your request. Please try again.",
                completed=True
            )

    async def _analyze_intent(self, user_id: str, message: str) -> str:
        """
        Analyze user intent to determine appropriate agent.

        Uses simple keyword matching for MVP. Could be enhanced with ML classification.
        """
        message_lower = message.lower()

        # Nutrition keywords
        nutrition_keywords = [
            'eat', 'ate', 'food', 'meal', 'breakfast', 'lunch', 'dinner', 'snack',
            'calories', 'protein', 'nutrition', 'hungry', 'recipe', 'cook'
        ]

        # Fitness keywords
        fitness_keywords = [
            'workout', 'exercise', 'gym', 'lift', 'run', 'cardio', 'strength',
            'training', 'muscle', 'weight', 'sets', 'reps', 'push', 'pull'
        ]

        # Wellness keywords
        wellness_keywords = [
            'sleep', 'water', 'steps', 'wellness', 'tired', 'rest', 'drink',
            'walk', 'bed', 'wake', 'stress', 'mood', 'energy'
        ]

        # Progress/analytics keywords
        progress_keywords = [
            'progress', 'analytics', 'stats', 'summary', 'report', 'chart',
            'trend', 'weight', 'loss', 'gain', 'average', 'total'
        ]

        # Check for nutrition intent
        if any(keyword in message_lower for keyword in nutrition_keywords):
            return "nutrition"

        # Check for fitness intent
        if any(keyword in message_lower for keyword in fitness_keywords):
            return "fitness"

        # Check for wellness intent
        if any(keyword in message_lower for keyword in wellness_keywords):
            return "wellness"

        # Check for progress intent
        if any(keyword in message_lower for keyword in progress_keywords):
            return "analytics"

        # Default to root agent for general queries
        return "root"


# Global router instance
router = AgentRouter()

# Export key classes
__all__ = [
    'ToolResult', 'AgentResponse', 'BaseTool', 'BaseAgent', 'AgentRouter', 'router'
]