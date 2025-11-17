"""
Base tool infrastructure for Weight Loss Chat Agent.

This module provides the foundational tool classes and utilities for agent tool calling.
All tools follow async patterns with proper error handling, validation, and timeouts.

Key components:
- BaseTool: Abstract base class for all tools
- Tool registry: Centralized tool management
- Validation utilities: Input validation and sanitization
- Error handling: Standardized error responses
- Async utilities: Timeout and retry mechanisms
"""

import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union, Callable
from datetime import datetime, date
from dataclasses import dataclass, asdict

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """
    Standardized result from tool execution.

    Provides consistent format for tool responses with success status,
    data payload, error information, and metadata.
    """
    success: bool
    data: Any = None
    error: Optional[str] = None
    confidence: float = 1.0
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolResult':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ValidationResult:
    """Result of input validation."""
    valid: bool
    value: Any = None
    error: Optional[str] = None
    sanitized: Any = None


class BaseTool(ABC):
    """
    Abstract base class for all agent tools.

    All tools must implement the execute method with async support,
    proper error handling, and standardized result formatting.
    """

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
        requires_validation: bool = True
    ):
        """
        Initialize tool.

        Args:
            name: Unique tool name
            description: Human-readable description
            parameters: JSON schema for tool parameters
            timeout_seconds: Execution timeout (defaults to settings)
            requires_validation: Whether to validate inputs
        """
        self.name = name
        self.description = description
        self.parameters = parameters or self._get_default_parameters()
        self.timeout_seconds = timeout_seconds or settings.api_timeout_seconds
        self.requires_validation = requires_validation

        # Register tool
        ToolRegistry.register(self)

        logger.debug(f"Initialized tool: {name}")

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            ToolResult: Execution result
        """
        pass

    def _get_default_parameters(self) -> Dict[str, Any]:
        """Get default parameter schema."""
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute_with_timeout(self, **kwargs) -> ToolResult:
        """
        Execute tool with timeout protection and validation.

        Args:
            **kwargs: Tool parameters

        Returns:
            ToolResult: Execution result
        """
        try:
            # Validate inputs if required
            if self.requires_validation:
                validation = self._validate_inputs(kwargs)
                if not validation.valid:
                    return ToolResult(
                        success=False,
                        error=f"Input validation failed: {validation.error}"
                    )
                kwargs = validation.sanitized or kwargs

            # Execute with timeout
            return await asyncio.wait_for(
                self.execute(**kwargs),
                timeout=self.timeout_seconds
            )

        except asyncio.TimeoutError:
            logger.warning(f"Tool {self.name} timed out after {self.timeout_seconds}s")
            return ToolResult(
                success=False,
                error=f"Tool execution timed out after {self.timeout_seconds} seconds"
            )
        except Exception as e:
            logger.error(f"Tool {self.name} execution error: {e}")
            return ToolResult(
                success=False,
                error=f"Tool execution failed: {str(e)}"
            )

    def _validate_inputs(self, inputs: Dict[str, Any]) -> ValidationResult:
        """
        Validate tool inputs against parameter schema.

        Args:
            inputs: Input parameters

        Returns:
            ValidationResult: Validation outcome
        """
        try:
            # Basic validation - check required parameters
            required = self.parameters.get("required", [])
            properties = self.parameters.get("properties", {})

            for param in required:
                if param not in inputs:
                    return ValidationResult(
                        valid=False,
                        error=f"Missing required parameter: {param}"
                    )

            # Type validation for known parameters
            sanitized = {}
            for param, value in inputs.items():
                if param in properties:
                    prop_schema = properties[param]
                    validation = self._validate_parameter(param, value, prop_schema)
                    if not validation.valid:
                        return validation
                    sanitized[param] = validation.sanitized or value
                else:
                    sanitized[param] = value

            return ValidationResult(valid=True, value=inputs, sanitized=sanitized)

        except Exception as e:
            return ValidationResult(
                valid=False,
                error=f"Validation error: {str(e)}"
            )

    def _validate_parameter(self, name: str, value: Any, schema: Dict[str, Any]) -> ValidationResult:
        """Validate individual parameter against schema."""
        param_type = schema.get("type")

        # Type validation
        if param_type == "string":
            if not isinstance(value, str):
                return ValidationResult(
                    valid=False,
                    error=f"Parameter {name} must be a string"
                )

            # Length validation
            min_length = schema.get("minLength")
            max_length = schema.get("maxLength")
            if min_length and len(value) < min_length:
                return ValidationResult(
                    valid=False,
                    error=f"Parameter {name} must be at least {min_length} characters"
                )
            if max_length and len(value) > max_length:
                return ValidationResult(
                    valid=False,
                    error=f"Parameter {name} must be at most {max_length} characters"
                )

            # Pattern validation
            pattern = schema.get("pattern")
            if pattern and not re.match(pattern, value):
                return ValidationResult(
                    valid=False,
                    error=f"Parameter {name} does not match required pattern"
                )

        elif param_type == "number":
            try:
                num_value = float(value)
            except (ValueError, TypeError):
                return ValidationResult(
                    valid=False,
                    error=f"Parameter {name} must be a number"
                )

            # Range validation
            minimum = schema.get("minimum")
            maximum = schema.get("maximum")
            if minimum is not None and num_value < minimum:
                return ValidationResult(
                    valid=False,
                    error=f"Parameter {name} must be at least {minimum}"
                )
            if maximum is not None and num_value > maximum:
                return ValidationResult(
                    valid=False,
                    error=f"Parameter {name} must be at most {maximum}"
                )

            return ValidationResult(valid=True, value=num_value, sanitized=num_value)

        elif param_type == "integer":
            try:
                int_value = int(value)
            except (ValueError, TypeError):
                return ValidationResult(
                    valid=False,
                    error=f"Parameter {name} must be an integer"
                )

            # Range validation
            minimum = schema.get("minimum")
            maximum = schema.get("maximum")
            if minimum is not None and int_value < minimum:
                return ValidationResult(
                    valid=False,
                    error=f"Parameter {name} must be at least {minimum}"
                )
            if maximum is not None and int_value > maximum:
                return ValidationResult(
                    valid=False,
                    error=f"Parameter {name} must be at most {maximum}"
                )

            return ValidationResult(valid=True, value=int_value, sanitized=int_value)

        elif param_type == "boolean":
            if isinstance(value, str):
                if value.lower() in ('true', '1', 'yes', 'on'):
                    return ValidationResult(valid=True, value=True, sanitized=True)
                elif value.lower() in ('false', '0', 'no', 'off'):
                    return ValidationResult(valid=True, value=False, sanitized=False)

            bool_value = bool(value)
            return ValidationResult(valid=True, value=bool_value, sanitized=bool_value)

        elif param_type == "array":
            if not isinstance(value, list):
                return ValidationResult(
                    valid=False,
                    error=f"Parameter {name} must be an array"
                )

            # Length validation
            min_items = schema.get("minItems")
            max_items = schema.get("maxItems")
            if min_items and len(value) < min_items:
                return ValidationResult(
                    valid=False,
                    error=f"Parameter {name} must have at least {min_items} items"
                )
            if max_items and len(value) > max_items:
                return ValidationResult(
                    valid=False,
                    error=f"Parameter {name} must have at most {max_items} items"
                )

        # If no specific validation, accept as-is
        return ValidationResult(valid=True, value=value)

    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema for ADK integration."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class ToolRegistry:
    """Central registry for tool management."""

    _tools: Dict[str, BaseTool] = {}

    @classmethod
    def register(cls, tool: BaseTool) -> None:
        """Register a tool instance."""
        cls._tools[tool.name] = tool

    @classmethod
    def get_tool(cls, name: str) -> Optional[BaseTool]:
        """Get tool by name."""
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> List[BaseTool]:
        """List all registered tools."""
        return list(cls._tools.values())

    @classmethod
    def get_tool_schemas(cls) -> List[Dict[str, Any]]:
        """Get schemas for all registered tools."""
        return [tool.get_schema() for tool in cls._tools.values()]


class ValidationUtils:
    """Utility functions for input validation and sanitization."""

    @staticmethod
    def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
        """Sanitize text input."""
        if not isinstance(text, str):
            text = str(text)

        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())

        # Truncate if needed
        if max_length and len(text) > max_length:
            text = text[:max_length].rstrip()

        return text

    @staticmethod
    def validate_date(date_str: str) -> Optional[date]:
        """Validate and parse date string."""
        try:
            return datetime.fromisoformat(date_str).date()
        except (ValueError, TypeError):
            return None

    @staticmethod
    def validate_number(value: Any, min_val: Optional[float] = None, max_val: Optional[float] = None) -> Optional[float]:
        """Validate numeric value with range."""
        try:
            num = float(value)
            if min_val is not None and num < min_val:
                return None
            if max_val is not None and num > max_val:
                return None
            return num
        except (ValueError, TypeError):
            return None

    @staticmethod
    def validate_list(items: List[Any], max_items: Optional[int] = None) -> bool:
        """Validate list constraints."""
        if max_items and len(items) > max_items:
            return False
        return True


class AsyncUtils:
    """Utilities for async operations."""

    @staticmethod
    async def retry_async(
        func: Callable,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        exceptions: tuple = (Exception,)
    ) -> Any:
        """
        Retry async function with exponential backoff.

        Args:
            func: Async function to retry
            max_attempts: Maximum number of attempts
            delay: Initial delay between attempts
            backoff: Backoff multiplier
            exceptions: Exception types to retry on

        Returns:
            Function result

        Raises:
            Last exception if all attempts fail
        """
        current_delay = delay

        for attempt in range(max_attempts):
            try:
                return await func()
            except exceptions as e:
                if attempt == max_attempts - 1:
                    raise e

                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {current_delay}s...")
                await asyncio.sleep(current_delay)
                current_delay *= backoff

    @staticmethod
    async def gather_with_timeout(
        tasks: List[asyncio.Task],
        timeout: Optional[float] = None
    ) -> List[Any]:
        """
        Run tasks with timeout protection.

        Args:
            tasks: List of async tasks
            timeout: Timeout in seconds

        Returns:
            List of results (None for timed out tasks)
        """
        if timeout is None:
            timeout = settings.api_timeout_seconds

        try:
            return await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Task gathering timed out after {timeout}s")
            return [None] * len(tasks)


# Export key classes and utilities
__all__ = [
    'ToolResult', 'ValidationResult', 'BaseTool', 'ToolRegistry',
    'ValidationUtils', 'AsyncUtils'
]