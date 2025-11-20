"""
Google ADK and Gemini API client initialization.

This module provides initialization and configuration for Google ADK (Agent Development Kit)
and Gemini API client. It handles authentication, client setup, and provides
utilities for AI agent interactions.

Key features:
- Google ADK client initialization
- Gemini model configuration
- Authentication and API key management
- Error handling and retry logic
- Cost tracking and rate limiting
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from functools import cached_property

from config.settings import settings
from config.logging import error_context, log_performance, ErrorHandler

# Lazy imports - avoid loading google.genai at module level as it has heavy dependencies
# These will be imported in _lazy_load_gemini() when needed
_genai = None
_Client = None
_types = None
_google_exceptions = None
_db_session = None
_ApiUsage = None

def _lazy_load_gemini():
    """Lazy load Gemini SDK only when needed"""
    global _genai, _Client, _types, _google_exceptions, _db_session, _ApiUsage
    
    if _genai is not None:
        return
    
    try:
        from google import genai
        from google.genai import Client, types
        from google.api_core import exceptions as google_exceptions
        from database.init import get_db_session
        from database.models import ApiUsage
        
        _genai = genai
        _Client = Client
        _types = types
        _google_exceptions = google_exceptions
        _db_session = get_db_session
        _ApiUsage = ApiUsage
    except ImportError as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to lazy load Gemini SDK: {e}")


logger = logging.getLogger(__name__)

# Lazy imports to avoid loading the entire google.adk stack on module import
# These will be imported only when ADKAgentManager is actually used
# from google.adk import agents, sessions
from google.adk.models import Gemini


class PatchedGemini(Gemini):
    """
    Patched Gemini model that properly configures API authentication.
    
    Inherits from Gemini and overrides the api_client property to include
    the API key from settings.
    """
    
    def __init__(self, model: str = "gemini-2.0-flash"):
        """Initialize the patched Gemini client"""
        # Initialize with model_name parameter
        super().__init__(model_name=model)
        # Initialize the API client attribute
        self._api_client = None
    
    @property
    def api_client(self):
        """Get or create the API client with proper authentication"""
        if self._api_client is None:
            _lazy_load_gemini()
            self._api_client = _Client(
                api_key=settings.google_genai_api_key,
                http_options=_types.HttpOptions()
            )
        return self._api_client


# GeminiClient and other heavy classes are disabled for now
# Only PatchedGemini is used, which does lazy loading on first access


class GeminiClient:
    """
    DISABLED - Google Gemini API client with ADK integration.
    Use PatchedGemini instead for lazy initialization.
    """

    def __init__(self):
        self.client = None
        self._initialized = False
        self._rate_limiter = None

    async def initialize(self) -> bool:
        raise NotImplementedError("GeminiClient is disabled. Use PatchedGemini instead.")


class ADKAgentManager:
    """
    Google ADK Agent manager for multi-agent orchestration.

    Provides utilities for creating, managing, and coordinating
    multiple ADK agents with session management.
    
    Note: This class uses lazy imports to avoid loading google.adk
    until it's actually needed.
    """

    def __init__(self):
        self.gemini_client = GeminiClient()
        self.agents: Dict[str, Any] = {}  # Will store agent instances
        self._initialized = False
        self._agents_module = None  # Lazy import
        self._sessions_module = None  # Lazy import

    def _ensure_adk_imports(self):
        """Lazily import ADK modules only when needed"""
        if self._agents_module is None:
            try:
                from google.adk import agents as agents_module
                from google.adk import sessions as sessions_module
                self._agents_module = agents_module
                self._sessions_module = sessions_module
            except ImportError as e:
                logger.error(f"Failed to import google.adk modules: {e}")
                raise

    async def initialize(self) -> bool:
        """
        Initialize ADK agent manager.

        Returns:
            bool: True if initialization successful
        """
        try:
            with error_context("adk_agent_manager_init"):
                # Ensure ADK modules are imported
                self._ensure_adk_imports()
                
                # Initialize Gemini client
                if not await self.gemini_client.initialize():
                    logger.error("Failed to initialize Gemini client for ADK")
                    return False

                self._initialized = True
                logger.info("ADK Agent manager initialized successfully")
                return True

        except Exception as e:
            logger.error(f"ADK agent manager initialization failed: {e}")
            return False

    def create_agent(
        self,
        name: str,
        description: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Optional[Any]:
        """
        Create a new ADK agent.

        Args:
            name: Agent name
            description: Agent description
            tools: List of tool schemas
            **kwargs: Additional agent configuration

        Returns:
            ADK Agent instance or None if failed
        """
        if not self._initialized:
            logger.error("ADK manager not initialized")
            return None

        try:
            # Ensure ADK imports are loaded
            self._ensure_adk_imports()
            
            # Set default parameters
            agent_config = {
                "model": settings.gemini_model,
                "temperature": settings.gemini_temperature,
                "max_tokens": settings.gemini_max_tokens,
                "tools": tools or [],
                **kwargs
            }

            # Create agent
            agent = self._agents_module.Agent(
                name=name,
                description=description,
                **agent_config
            )

            # Store agent
            self.agents[name] = agent

            logger.info(f"Created ADK agent: {name}")
            return agent

        except Exception as e:
            logger.error(f"Failed to create ADK agent {name}: {e}")
            return None

    async def run_agent_session(
        self,
        agent_name: str,
        user_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Run an agent session with message processing.

        Args:
            agent_name: Name of the agent to run
            user_id: User identifier
            message: User message
            context: Additional context

        Returns:
            Dict containing response data or None if failed
        """
        agent = self.agents.get(agent_name)
        if not agent:
            logger.error(f"Agent not found: {agent_name}")
            return None

        try:
            with error_context("adk_agent_session", user_id=user_id, agent=agent_name):
                # Ensure ADK imports are loaded
                self._ensure_adk_imports()
                
                # Create session
                session = self._sessions_module.Session(
                    agent=agent,
                    user_id=user_id,
                    context=context or {}
                )

                # Send message and get response
                response = await session.send_message_async(message)

                return {
                    "text": response.text if hasattr(response, 'text') else "",
                    "tool_calls": getattr(response, 'tool_calls', []),
                    "metadata": getattr(response, 'metadata', {}),
                    "session_id": getattr(session, 'id', None)
                }

        except Exception as e:
            logger.error(f"Agent session failed for {agent_name}: {e}")
            return None

    def get_agent(self, name: str) -> Optional[Any]:
        """Get agent by name."""
        return self.agents.get(name)

    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self.agents.keys())


class RateLimiter:
    """
    Simple rate limiter for API calls.

    Tracks request counts and enforces rate limits to prevent quota exhaustion.
    """

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: List[datetime] = []

    async def check_limit(self) -> bool:
        """
        Check if request is within rate limit.

        Returns:
            bool: True if request allowed, False if rate limited
        """
        now = datetime.utcnow()

        # Remove old requests outside the window
        cutoff = now - timedelta(minutes=1)
        self.requests = [req for req in self.requests if req > cutoff]

        # Check if under limit
        if len(self.requests) < self.requests_per_minute:
            self.requests.append(now)
            return True

        return False

    def get_remaining_requests(self) -> int:
        """Get remaining requests in current window."""
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=1)
        recent_requests = [req for req in self.requests if req > cutoff]
        return max(0, self.requests_per_minute - len(recent_requests))


# Global instances
gemini_client = GeminiClient()
adk_manager = ADKAgentManager()

# Export key classes and instances
__all__ = [
    'GeminiClient', 'ADKAgentManager', 'RateLimiter',
    'gemini_client', 'adk_manager'
]