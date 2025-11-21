"""
Logging and error handling infrastructure for Weight Loss Chat Agent.

This module provides comprehensive logging configuration and error handling
utilities. It ensures proper log formatting, sensitive data filtering,
and structured error reporting while maintaining privacy compliance.

Key features:
- Structured logging with JSON format and correlation IDs
- Sensitive data filtering and sanitization
- Error classification and handling
- Performance monitoring with timing
- Distributed tracing support
- User journey tracking
- GDPR-compliant logging practices
"""

import os
import sys
import json
import logging
import logging.handlers
import uuid
import time
import threading
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from contextvars import ContextVar

from config.settings import settings


# Context variables for distributed tracing and user journey tracking
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
agent_var: ContextVar[Optional[str]] = ContextVar('agent', default=None)
tool_var: ContextVar[Optional[str]] = ContextVar('tool', default=None)
journey_id_var: ContextVar[Optional[str]] = ContextVar('journey_id', default=None)
span_id_var: ContextVar[Optional[str]] = ContextVar('span_id', default=None)
parent_span_id_var: ContextVar[Optional[str]] = ContextVar('parent_span_id', default=None)


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter to remove sensitive user data from logs.

    Filters out personally identifiable information, API keys, and
    sensitive health data to ensure GDPR compliance.
    """

    SENSITIVE_PATTERNS = [
        # API keys and tokens
        r'api_key[^=]*=[\w\-]+',
        r'token[^=]*=[\w\-]+',
        r'key[^=]*=[\w\-]+',

        # Personal identifiers
        r'user_id[^=]*=\d+',
        r'telegram_id[^=]*=\d+',

        # Health data
        r'weight[^=]*=\d+',
        r'age[^=]*=\d+',
        r'height[^=]*=\d+',
        r'calories[^=]*=\d+',

        # Email patterns
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',

        # Phone numbers
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',

        # Addresses
        r'\d+\s+[\w\s]+(?:street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|lane|ln|way|place|pl|court|ct)\b',

        # Social security numbers
        r'\b\d{3}-\d{2}-\d{4}\b',
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter sensitive data from log records."""
        # Sanitize the message
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self._sanitize_text(record.msg)

        # Sanitize any extra fields
        if hasattr(record, 'exc_text') and record.exc_text:
            record.exc_text = self._sanitize_text(record.exc_text)

        return True

    def _sanitize_text(self, text: str) -> str:
        """Sanitize sensitive data from text."""
        import re

        sanitized = text
        for pattern in self.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)

        return sanitized


class JSONFormatter(logging.Formatter):
    """
    Enhanced JSON formatter for structured logging with observability features.

    Formats log records as JSON objects for better parsing and analysis.
    Includes timestamp, level, message, correlation ID, user journey tracking,
    agent/tool context, and performance metrics.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with observability context."""
        # Create base log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation and tracing context
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        user_id = user_id_var.get()
        if user_id:
            log_entry["user_id"] = user_id

        agent = agent_var.get()
        if agent:
            log_entry["agent"] = agent

        tool = tool_var.get()
        if tool:
            log_entry["tool"] = tool

        journey_id = journey_id_var.get()
        if journey_id:
            log_entry["journey_id"] = journey_id

        span_id = span_id_var.get()
        if span_id:
            log_entry["span_id"] = span_id

        parent_span_id = parent_span_id_var.get()
        if parent_span_id:
            log_entry["parent_span_id"] = parent_span_id

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            log_entry["exception_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None

        # Add performance metrics if present
        if hasattr(record, 'duration_ms'):
            log_entry["duration_ms"] = record.duration_ms

        if hasattr(record, 'status'):
            log_entry["status"] = record.status

        # Add metadata if present
        if hasattr(record, 'metadata') and record.metadata:
            log_entry["metadata"] = record.metadata

        # Add any extra fields from the record
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ('name', 'msg', 'args', 'levelname', 'levelno',
                             'pathname', 'filename', 'module', 'exc_info',
                             'exc_text', 'stack_info', 'lineno', 'funcName',
                             'created', 'msecs', 'relativeCreated', 'thread',
                             'threadName', 'processName', 'process', 'message',
                             'duration_ms', 'status', 'metadata'):
                    log_entry[key] = value

        return json.dumps(log_entry, default=str)


class ErrorHandler:
    """
    Centralized error handling and classification.

    Provides utilities for error classification, user-friendly messages,
    and appropriate error responses.
    """

    # Error categories and their user-friendly messages
    ERROR_CATEGORIES = {
        "network": {
            "message": "Network connection issue. Please check your internet connection.",
            "retryable": True,
            "log_level": "WARNING"
        },
        "api": {
            "message": "External service temporarily unavailable. Please try again.",
            "retryable": True,
            "log_level": "WARNING"
        },
        "validation": {
            "message": "Invalid input provided. Please check your request and try again.",
            "retryable": False,
            "log_level": "INFO"
        },
        "authentication": {
            "message": "Authentication failed. Please check your credentials.",
            "retryable": False,
            "log_level": "WARNING"
        },
        "authorization": {
            "message": "Access denied. You don't have permission for this action.",
            "retryable": False,
            "log_level": "WARNING"
        },
        "database": {
            "message": "Database temporarily unavailable. Please try again.",
            "retryable": True,
            "log_level": "ERROR"
        },
        "timeout": {
            "message": "Request timed out. Please try again.",
            "retryable": True,
            "log_level": "WARNING"
        },
        "rate_limit": {
            "message": "Too many requests. Please wait a moment and try again.",
            "retryable": True,
            "log_level": "INFO"
        },
        "system": {
            "message": "System error occurred. Please try again later.",
            "retryable": True,
            "log_level": "ERROR"
        }
    }

    @classmethod
    def classify_error(cls, error: Exception) -> Dict[str, Any]:
        """
        Classify an exception into a category with appropriate response.

        Args:
            error: The exception to classify

        Returns:
            Dict containing category info and user message
        """
        error_type = type(error).__name__
        error_message = str(error).lower()

        # Network-related errors
        if any(keyword in error_message for keyword in ['connection', 'network', 'timeout', 'unreachable']):
            return cls.ERROR_CATEGORIES["network"]

        # API-related errors
        if any(keyword in error_message for keyword in ['api', 'service', 'external', 'upstream']):
            return cls.ERROR_CATEGORIES["api"]

        # Authentication errors
        if any(keyword in error_message for keyword in ['auth', 'credential', 'token', 'key']):
            return cls.ERROR_CATEGORIES["authentication"]

        # Validation errors
        if any(keyword in error_message for keyword in ['invalid', 'validation', 'format', 'required']):
            return cls.ERROR_CATEGORIES["validation"]

        # Database errors
        if any(keyword in error_message for keyword in ['database', 'sqlite', 'sql', 'query']):
            return cls.ERROR_CATEGORIES["database"]

        # Timeout errors
        if 'timeout' in error_message or isinstance(error, TimeoutError):
            return cls.ERROR_CATEGORIES["timeout"]

        # Rate limiting
        if any(keyword in error_message for keyword in ['rate', 'limit', 'quota', 'throttle']):
            return cls.ERROR_CATEGORIES["rate_limit"]

        # Default to system error
        return cls.ERROR_CATEGORIES["system"]

    @classmethod
    def get_user_message(cls, error: Exception) -> str:
        """Get user-friendly error message for an exception."""
        category = cls.classify_error(error)
        return category["message"]

    @classmethod
    def is_retryable(cls, error: Exception) -> bool:
        """Check if an error is retryable."""
        category = cls.classify_error(error)
        return category["retryable"]

    @classmethod
    def get_log_level(cls, error: Exception) -> str:
        """Get appropriate log level for an error."""
        category = cls.classify_error(error)
        return category["log_level"]


def setup_logging(
    log_level: str = None,
    log_file: str = None,
    json_format: bool = True,
    enable_console: bool = True
) -> None:
    """
    Configure logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        json_format: Whether to use JSON formatting
        enable_console: Whether to enable console logging
    """
    # Use settings defaults
    log_level = log_level or settings.log_level
    log_file = log_file or str(settings.log_path)

    # Convert log level string to numeric
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(numeric_level)

    # Create formatters
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter()

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(sensitive_filter)
        root_logger.addHandler(console_handler)

    # File handler with rotation
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(sensitive_filter)
        root_logger.addHandler(file_handler)

    # Set specific log levels for noisy libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('google').setLevel(logging.WARNING)

    # Get logger for this module to log the configuration message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={log_level}, file={log_file}, json={json_format}")


@contextmanager
def error_context(operation: str, user_id: Optional[str] = None, **extra_context):
    """
    Context manager for operation error handling and logging.

    Usage:
        with error_context("user_registration", user_id=user_id):
            # risky operation
            pass
    """
    logger = logging.getLogger(__name__)
    start_time = datetime.utcnow()

    try:
        logger.info(f"Starting operation: {operation}", extra={
            "operation": operation,
            "user_id": user_id,
            **extra_context
        })
        yield

    except Exception as e:
        duration = (datetime.utcnow() - start_time).total_seconds()

        # Classify error
        error_info = ErrorHandler.classify_error(e)
        log_level = getattr(logging, error_info["log_level"])

        logger.log(log_level, f"Operation failed: {operation}", extra={
            "operation": operation,
            "user_id": user_id,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "duration_seconds": duration,
            "error_category": list(ErrorHandler.ERROR_CATEGORIES.keys())[
                list(ErrorHandler.ERROR_CATEGORIES.values()).index(error_info)
            ],
            **extra_context
        }, exc_info=True)

        raise

    else:
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Operation completed: {operation}", extra={
            "operation": operation,
            "user_id": user_id,
            "duration_seconds": duration,
            **extra_context
        })


@contextmanager
def request_context(correlation_id: Optional[str] = None, user_id: Optional[str] = None, journey_id: Optional[str] = None):
    """
    Context manager for request-level logging context.

    Sets correlation ID, user ID, and journey ID for all logs within the context.

    Args:
        correlation_id: Request correlation ID (generated if not provided)
        user_id: User identifier
        journey_id: User journey identifier (generated if not provided)
    """
    # Generate IDs if not provided
    corr_id = correlation_id or str(uuid.uuid4())
    journey = journey_id or str(uuid.uuid4())

    # Set context variables
    corr_token = correlation_id_var.set(corr_id)
    user_token = user_id_var.set(user_id) if user_id else None
    journey_token = journey_id_var.set(journey)

    try:
        yield {
            "correlation_id": corr_id,
            "user_id": user_id,
            "journey_id": journey
        }
    finally:
        # Reset context variables
        correlation_id_var.reset(corr_token)
        if user_token:
            user_id_var.reset(user_token)
        journey_id_var.reset(journey_token)


@contextmanager
def agent_context(agent_name: str, user_id: Optional[str] = None):
    """
    Context manager for agent execution logging.

    Sets agent context and tracks execution time.

    Args:
        agent_name: Name of the agent
        user_id: User identifier
    """
    logger = logging.getLogger(__name__)
    start_time = time.time()

    # Set agent context
    agent_token = agent_var.set(agent_name)
    user_token = user_id_var.set(user_id) if user_id else None

    try:
        logger.info(f"Agent execution started: {agent_name}", extra={
            "operation": "agent_start",
            "agent": agent_name,
            "user_id": user_id
        })
        yield
    finally:
        duration_ms = (time.time() - start_time) * 1000

        logger.info(f"Agent execution completed: {agent_name}", extra={
            "operation": "agent_complete",
            "agent": agent_name,
            "user_id": user_id,
            "duration_ms": duration_ms
        })

        # Reset context variables
        agent_var.reset(agent_token)
        if user_token:
            user_id_var.reset(user_token)


@contextmanager
def tool_context(tool_name: str, agent_name: Optional[str] = None, user_id: Optional[str] = None):
    """
    Context manager for tool execution logging.

    Sets tool context and tracks execution time.

    Args:
        tool_name: Name of the tool
        agent_name: Name of the agent using the tool
        user_id: User identifier
    """
    logger = logging.getLogger(__name__)
    start_time = time.time()

    # Set tool context
    tool_token = tool_var.set(tool_name)
    agent_token = agent_var.set(agent_name) if agent_name else None
    user_token = user_id_var.set(user_id) if user_id else None

    try:
        logger.info(f"Tool execution started: {tool_name}", extra={
            "operation": "tool_start",
            "tool": tool_name,
            "agent": agent_name,
            "user_id": user_id
        })
        yield
    finally:
        duration_ms = (time.time() - start_time) * 1000

        logger.info(f"Tool execution completed: {tool_name}", extra={
            "operation": "tool_complete",
            "tool": tool_name,
            "agent": agent_name,
            "user_id": user_id,
            "duration_ms": duration_ms
        })

        # Reset context variables
        tool_var.reset(tool_token)
        if agent_token:
            agent_var.reset(agent_token)
        if user_token:
            user_id_var.reset(user_token)


@contextmanager
def span_context(operation: str, parent_span_id: Optional[str] = None):
    """
    Context manager for distributed tracing spans.

    Creates a new span for the operation and tracks timing.

    Args:
        operation: Name of the operation
        parent_span_id: Parent span ID for nested operations
    """
    span_id = str(uuid.uuid4())
    start_time = datetime.utcnow()

    # Set span context
    span_token = span_id_var.set(span_id)
    parent_token = parent_span_id_var.set(parent_span_id) if parent_span_id else None

    try:
        yield span_id
    finally:
        end_time = datetime.utcnow()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        logger = logging.getLogger(__name__)
        logger.info(f"Span completed: {operation}", extra={
            "operation": operation,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "start_time": start_time.isoformat() + "Z",
            "end_time": end_time.isoformat() + "Z",
            "duration_ms": duration_ms
        })

        # Reset context variables
        span_id_var.reset(span_token)
        if parent_token:
            parent_span_id_var.reset(parent_token)


@contextmanager
def database_context(operation: str, table: Optional[str] = None):
    """
    Context manager for database operation logging.

    Tracks database query timing and context.

    Args:
        operation: Database operation (select, insert, update, delete)
        table: Table name being operated on
    """
    logger = logging.getLogger(__name__)
    start_time = time.time()

    try:
        logger.debug(f"Database operation started: {operation}", extra={
            "operation": "db_start",
            "db_operation": operation,
            "table": table
        })
        yield
    finally:
        duration_ms = (time.time() - start_time) * 1000

        logger.info(f"Database operation completed: {operation}", extra={
            "operation": "db_complete",
            "db_operation": operation,
            "table": table,
            "duration_ms": duration_ms
        })


@contextmanager
def api_context(provider: str, endpoint: str, method: str = "GET"):
    """
    Context manager for API call logging.

    Tracks API call latency and context.

    Args:
        provider: API provider name
        endpoint: API endpoint
        method: HTTP method
    """
    logger = logging.getLogger(__name__)
    start_time = time.time()

    try:
        logger.debug(f"API call started: {provider} {method} {endpoint}", extra={
            "operation": "api_start",
            "api_provider": provider,
            "api_endpoint": endpoint,
            "api_method": method
        })
        yield
    finally:
        duration_ms = (time.time() - start_time) * 1000

        logger.info(f"API call completed: {provider} {method} {endpoint}", extra={
            "operation": "api_complete",
            "api_provider": provider,
            "api_endpoint": endpoint,
            "api_method": method,
            "duration_ms": duration_ms
        })


def log_user_journey_event(event_type: str, user_id: str, details: Optional[Dict[str, Any]] = None):
    """
    Log user journey events for tracking user experience.

    Args:
        event_type: Type of journey event (start, milestone, end, error)
        user_id: User identifier
        details: Additional event details
    """
    logger = logging.getLogger(__name__)
    logger.info(f"User journey event: {event_type}", extra={
        "operation": "journey_event",
        "event_type": event_type,
        "user_id": user_id,
        "journey_details": details or {}
    })


def log_metric(name: str, value: float, tags: Optional[Dict[str, str]] = None, metadata: Optional[Dict[str, Any]] = None):
    """
    Log custom metrics for monitoring and alerting.

    Args:
        name: Metric name
        value: Metric value
        tags: Metric tags for filtering
        metadata: Additional metadata
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Metric: {name} = {value}", extra={
        "operation": "metric",
        "metric_name": name,
        "metric_value": value,
        "metric_tags": tags or {},
        "metadata": metadata or {}
    })


def log_performance(operation: str, duration: float, success: bool = True, **metrics) -> None:
    """
    Log performance metrics for operations.

    Args:
        operation: Name of the operation
        duration: Duration in seconds
        success: Whether the operation succeeded
        **metrics: Additional performance metrics
    """
    logger = logging.getLogger(__name__)
    logger.info("Performance metric", extra={
        "operation": operation,
        "duration_seconds": duration,
        "success": success,
        **metrics
    })


class HealthChecker:
    """Health check utilities for monitoring system status."""

    @staticmethod
    def check_database() -> Dict[str, Any]:
        """Check database connectivity and health."""
        try:
            from database.init import db_manager
            stats = db_manager.get_database_stats()
            return {
                "status": "healthy",
                "database_size_mb": stats.get("file_size_mb", 0),
                "table_count": len([k for k in stats.keys() if k.endswith("_count")])
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    @staticmethod
    def check_api_keys() -> Dict[str, Any]:
        """Check API key configuration."""
        issues = []

        if not settings.telegram_bot_token:
            issues.append("Telegram bot token not configured")

        if not settings.google_genai_api_key:
            issues.append("Gemini API key not configured")

        return {
            "status": "healthy" if not issues else "warning",
            "issues": issues
        }

    @staticmethod
    def get_system_health() -> Dict[str, Any]:
        """Get overall system health status."""
        database_health = HealthChecker.check_database()
        api_health = HealthChecker.check_api_keys()

        overall_status = "healthy"
        if database_health["status"] == "unhealthy" or api_health["status"] == "warning":
            overall_status = "warning"
        if database_health["status"] == "unhealthy":
            overall_status = "unhealthy"

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": database_health,
                "api_keys": api_health
            }
        }


# Initialize logging on import
setup_logging()

# Export key classes and functions
__all__ = [
    'SensitiveDataFilter', 'JSONFormatter', 'ErrorHandler',
    'setup_logging', 'error_context', 'request_context', 'agent_context',
    'tool_context', 'span_context', 'database_context', 'api_context',
    'log_user_journey_event', 'log_metric', 'log_performance', 'HealthChecker', 'get_logger'
]


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)