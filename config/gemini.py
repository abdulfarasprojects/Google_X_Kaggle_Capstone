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

from google import genai
from google.adk import agents, sessions
from google.adk.models import Gemini
from google.genai import Client, types
from google.api_core import exceptions as google_exceptions
from functools import cached_property
from google.genai import Client, types
from functools import cached_property

from config.settings import settings
from config.logging import error_context, log_performance, ErrorHandler
from database.init import get_db_session
from database.models import ApiUsage


class PatchedGemini(Gemini):
    """
    Patched Gemini model that properly configures API authentication.
    
    The base Gemini class doesn't pass API keys to the Client, so we override
    the api_client property to include the API key from settings.
    """
    
    @cached_property
    def api_client(self):
        """Override api_client to include API key authentication."""
        return Client(
            api_key=settings.google_genai_api_key,
            http_options=types.HttpOptions(
                headers=self._tracking_headers,
                retry_options=self.retry_options,
            )
        )

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Google Gemini API client with ADK integration.

    Provides high-level interface for Gemini model interactions with
    built-in error handling, retry logic, and cost tracking.
    """

    def __init__(self):
        self.client: Optional[genai.Client] = None
        self._initialized = False
        self._rate_limiter = RateLimiter()

    async def initialize(self) -> bool:
        """
        Initialize the Gemini client.

        Returns:
            bool: True if initialization successful
        """
        try:
            with error_context("gemini_client_init"):
                # Create client with API key
                self.client = genai.Client(api_key=settings.google_genai_api_key)

                # Test connection with a simple request
                test_response = await self._test_connection()
                if test_response:
                    self._initialized = True
                    logger.info("Gemini client initialized successfully")
                    return True
                else:
                    logger.error("Gemini client test connection failed")
                    return False

        except Exception as e:
            logger.error(f"Gemini client initialization failed: {e}")
            return False

    async def _test_connection(self) -> bool:
        """Test connection to Gemini API."""
        try:
            # Create a simple test model
            model = self.client.models.generate_content(
                model=settings.gemini_model,
                contents="Hello",
                config=genai.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=10
                )
            )

            # Try to get a response
            response = await asyncio.wait_for(
                model,
                timeout=10
            )

            return response is not None

        except Exception as e:
            logger.warning(f"Gemini connection test failed: {e}")
            return False

    async def generate_content(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Generate content using Gemini model.

        Args:
            prompt: Text prompt for generation
            model: Model name (defaults to settings)
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
            **kwargs: Additional parameters

        Returns:
            Dict containing response data or None if failed
        """
        if not self._initialized or not self.client:
            logger.error("Gemini client not initialized")
            return None

        # Check rate limit
        if not await self._rate_limiter.check_limit():
            logger.warning("Gemini API rate limit exceeded")
            return None

        model = model or settings.gemini_model
        temperature = temperature if temperature is not None else settings.gemini_temperature
        max_tokens = max_tokens or settings.gemini_max_tokens

        start_time = datetime.utcnow()

        try:
            with error_context("gemini_generate_content"):
                # Create generation config
                config = genai.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    **kwargs
                )

                # Generate content
                response = await asyncio.wait_for(
                    self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=config
                    ),
                    timeout=settings.api_timeout_seconds
                )

                # Track API usage
                await self._track_api_usage("gemini", "generate_content", cost_usd=0.001)  # Estimate

                # Calculate performance
                duration = (datetime.utcnow() - start_time).total_seconds()
                log_performance("gemini_generate_content", duration, success=True)

                return {
                    "text": response.text if hasattr(response, 'text') else "",
                    "metadata": getattr(response, 'metadata', {}),
                    "usage": getattr(response, 'usage', {}),
                    "duration": duration
                }

        except google_exceptions.ResourceExhausted:
            logger.warning("Gemini API quota exceeded")
            await self._track_api_usage("gemini", "generate_content_quota_exceeded")
            return None

        except asyncio.TimeoutError:
            logger.warning("Gemini API request timed out")
            duration = (datetime.utcnow() - start_time).total_seconds()
            log_performance("gemini_generate_content", duration, success=False)
            return None

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            log_performance("gemini_generate_content", duration, success=False)

            if ErrorHandler.is_retryable(e):
                logger.warning(f"Retryable Gemini error: {e}")
            else:
                logger.error(f"Non-retryable Gemini error: {e}")

            return None

    async def _track_api_usage(self, provider: str, endpoint: str, request_count: int = 1, cost_usd: float = 0.0) -> None:
        """Track API usage for cost monitoring."""
        try:
            with get_db_session() as session:
                usage = ApiUsage(
                    provider=provider,
                    endpoint=endpoint,
                    request_count=request_count,
                    cost_usd=cost_usd
                )
                session.add(usage)
                session.commit()
        except Exception as e:
            logger.warning(f"Failed to track API usage: {e}")


class ADKAgentManager:
    """
    Google ADK Agent manager for multi-agent orchestration.

    Provides utilities for creating, managing, and coordinating
    multiple ADK agents with session management.
    """

    def __init__(self):
        self.gemini_client = GeminiClient()
        self.agents: Dict[str, agents.Agent] = {}
        self._initialized = False

    async def initialize(self) -> bool:
        """
        Initialize ADK agent manager.

        Returns:
            bool: True if initialization successful
        """
        try:
            with error_context("adk_agent_manager_init"):
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
    ) -> Optional[agents.Agent]:
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
            # Set default parameters
            agent_config = {
                "model": settings.gemini_model,
                "temperature": settings.gemini_temperature,
                "max_tokens": settings.gemini_max_tokens,
                "tools": tools or [],
                **kwargs
            }

            # Create agent
            agent = agents.Agent(
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
                # Create session
                session = sessions.Session(
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

    def get_agent(self, name: str) -> Optional[agents.Agent]:
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