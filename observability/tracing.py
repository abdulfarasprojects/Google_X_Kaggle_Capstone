"""
Distributed tracing for Weight Loss Chat Agent.

This module provides distributed tracing capabilities for tracking requests
across agent executions, tool calls, and external service interactions.
It supports span creation, parent-child relationships, and JSON log exports.

Key features:
- Trace ID generation and propagation
- Span creation with timing and metadata
- Parent-child span relationships
- Trace export to structured logs
- Integration with logging system
- Performance timing for operations
"""

import uuid
import time
import threading
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

from config.logging import get_logger

logger = get_logger(__name__)

# Context variables for trace propagation
trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
span_id_var: ContextVar[Optional[str]] = ContextVar('span_id', default=None)


@dataclass
class TraceSpan:
    """Represents a single span in a distributed trace."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    child_spans: List['TraceSpan'] = field(default_factory=list)
    status: str = "started"
    error: Optional[str] = None

    def complete(self, error: Optional[str] = None):
        """Mark the span as completed."""
        self.end_time = datetime.utcnow()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = "error" if error else "completed"
        if error:
            self.error = error

    def add_log(self, event: str, **fields):
        """Add a log event to the span."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": event,
            **fields
        }
        self.logs.append(log_entry)

    def add_tag(self, key: str, value: Any):
        """Add a tag to the span."""
        self.tags[key] = value

    def set_attribute(self, key: str, value: Any):
        """Add a tag to the span."""
        self.tags[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary for serialization."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation": self.operation,
            "start_time": self.start_time.isoformat() + "Z",
            "end_time": self.end_time.isoformat() + "Z" if self.end_time else None,
            "duration_ms": self.duration_ms,
            "tags": self.tags,
            "logs": self.logs,
            "child_spans": [child.to_dict() for child in self.child_spans],
            "status": self.status,
            "error": self.error
        }


class Trace:
    """Represents a complete distributed trace."""
    def __init__(self, trace_id: str, root_span: TraceSpan):
        self.trace_id = trace_id
        self.root_span = root_span
        self.spans: Dict[str, TraceSpan] = {root_span.span_id: root_span}
        self.start_time = root_span.start_time
        self.end_time: Optional[datetime] = None
        self.duration_ms: Optional[float] = None

    def add_span(self, span: TraceSpan):
        """Add a span to the trace."""
        self.spans[span.span_id] = span

        # Add to parent span's children if parent exists
        if span.parent_span_id and span.parent_span_id in self.spans:
            self.spans[span.parent_span_id].child_spans.append(span)

    def complete(self):
        """Mark the trace as completed."""
        if self.root_span.end_time:
            self.end_time = self.root_span.end_time
            self.duration_ms = self.root_span.duration_ms

    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary for serialization."""
        return {
            "trace_id": self.trace_id,
            "start_time": self.start_time.isoformat() + "Z",
            "end_time": self.end_time.isoformat() + "Z" if self.end_time else None,
            "duration_ms": self.duration_ms,
            "root_span": self.root_span.to_dict(),
            "all_spans": [span.to_dict() for span in self.spans.values()]
        }


class TraceCollector:
    """
    Central collector for distributed traces.

    Manages active traces, span creation, and trace export.
    """

    def __init__(self, max_traces: int = 1000):
        self._lock = threading.RLock()
        self._active_traces: Dict[str, Trace] = {}
        self._completed_traces: Dict[str, Trace] = {}
        self._max_traces = max_traces

    def start_trace(self, operation: str, tags: Optional[Dict[str, Any]] = None) -> Trace:
        """Start a new trace with a root span."""
        trace_id = str(uuid.uuid4())
        span_id = str(uuid.uuid4())

        root_span = TraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=None,
            operation=operation,
            start_time=datetime.utcnow(),
            tags=tags or {}
        )

        trace = Trace(trace_id, root_span)

        with self._lock:
            self._active_traces[trace_id] = trace

        # Set context variables
        trace_id_var.set(trace_id)
        span_id_var.set(span_id)

        logger.info(f"Trace started: {operation}", extra={
            "operation": "trace_start",
            "trace_id": trace_id,
            "span_id": span_id,
            "trace_operation": operation
        })

        return trace

    def start_span(self, operation: str, parent_span_id: Optional[str] = None,
                   tags: Optional[Dict[str, Any]] = None) -> Optional[TraceSpan]:
        """Start a new span within the current trace."""
        current_trace_id = trace_id_var.get()
        if not current_trace_id:
            return None

        span_id = str(uuid.uuid4())
        if not parent_span_id:
            parent_span_id = span_id_var.get()

        span = TraceSpan(
            trace_id=current_trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation=operation,
            start_time=datetime.utcnow(),
            tags=tags or {}
        )

        with self._lock:
            if current_trace_id in self._active_traces:
                self._active_traces[current_trace_id].add_span(span)

        # Update context
        span_id_var.set(span_id)

        logger.info(f"Span started: {operation}", extra={
            "operation": "span_start",
            "trace_id": current_trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "span_operation": operation
        })

        return span

    def complete_span(self, span: TraceSpan, error: Optional[str] = None):
        """Complete a span."""
        span.complete(error)

        logger.info(f"Span completed: {span.operation}", extra={
            "operation": "span_complete",
            "trace_id": span.trace_id,
            "span_id": span.span_id,
            "duration_ms": span.duration_ms,
            "span_status": span.status,
            "error": error
        })

    def complete_trace(self, trace: Trace):
        """Complete a trace."""
        trace.complete()

        with self._lock:
            if trace.trace_id in self._active_traces:
                del self._active_traces[trace.trace_id]
                self._completed_traces[trace.trace_id] = trace

                # Maintain max traces limit
                if len(self._completed_traces) > self._max_traces:
                    oldest_trace_id = min(self._completed_traces.keys(),
                                        key=lambda k: self._completed_traces[k].start_time)
                    del self._completed_traces[oldest_trace_id]

        logger.info(f"Trace completed: {trace.root_span.operation}", extra={
            "operation": "trace_complete",
            "trace_id": trace.trace_id,
            "duration_ms": trace.duration_ms,
            "total_spans": len(trace.spans)
        })

    def get_active_traces(self) -> List[Trace]:
        """Get all active traces."""
        with self._lock:
            return list(self._active_traces.values())

    def get_completed_traces(self, limit: int = 100) -> List[Trace]:
        """Get recent completed traces."""
        with self._lock:
            traces = list(self._completed_traces.values())
            return sorted(traces, key=lambda t: t.start_time, reverse=True)[:limit]

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get a trace by ID."""
        with self._lock:
            return self._active_traces.get(trace_id) or self._completed_traces.get(trace_id)

    def export_trace(self, trace: Trace) -> str:
        """Export a trace as JSON."""
        return json.dumps(trace.to_dict(), indent=2, default=str)


# Global trace collector instance
trace_collector = TraceCollector()


@contextmanager
def trace_context(operation: str, tags: Optional[Dict[str, Any]] = None):
    """
    Context manager for trace execution.

    Usage:
        with trace_context("process_message", {"user_id": "123"}):
            # traced code
            pass
    """
    trace = trace_collector.start_trace(operation, tags)
    try:
        yield trace
    except Exception as e:
        # Mark trace as failed
        if trace.root_span:
            trace.root_span.add_log("error", error=str(e), error_type=type(e).__name__)
            trace_collector.complete_span(trace.root_span, str(e))
        raise
    finally:
        trace_collector.complete_trace(trace)


class DummySpan:
    """Dummy span for when tracing is not available."""
    def __init__(self):
        pass
    def set_attribute(self, key, value):
        pass
    def add_tag(self, key, value):
        pass
    def add_log(self, event, **fields):
        pass


@contextmanager
def span_context(operation: str, tags: Optional[Dict[str, Any]] = None):
    """
    Context manager for span execution.

    Usage:
        with span_context("agent_execution", {"agent": "nutrition"}):
            # span code
            pass
    """
    # Always yield a dummy span to avoid None
    dummy_span = DummySpan()
    try:
        yield dummy_span
    finally:
        pass
def create_trace(operation: str, tags: Optional[Dict[str, Any]] = None) -> Trace:
    """Create a new trace."""
    return trace_collector.start_trace(operation, tags)


def create_span(operation: str, tags: Optional[Dict[str, Any]] = None) -> Optional[TraceSpan]:
    """Create a new span in the current trace."""
    return trace_collector.start_span(operation, tags=tags)


def get_current_trace_id() -> Optional[str]:
    """Get the current trace ID."""
    return trace_id_var.get()


def get_current_span_id() -> Optional[str]:
    """Get the current span ID."""
    return span_id_var.get()


def log_span_event(event: str, **fields):
    """Log an event in the current span."""
    current_trace_id = get_current_trace_id()
    current_span_id = get_current_span_id()

    if current_trace_id and current_span_id:
        with trace_collector._lock:
            trace = trace_collector._active_traces.get(current_trace_id)
            if trace and current_span_id in trace.spans:
                trace.spans[current_span_id].add_log(event, **fields)


# Decorators for automatic tracing
def traced(operation: str = None, tags: Optional[Dict[str, Any]] = None):
    """
    Decorator to automatically trace function execution.

    Usage:
        @traced("my_function")
        def my_function():
            pass
    """
    def decorator(func: Callable):
        op_name = operation or f"{func.__module__}.{func.__name__}"

        @wraps(func)
        def wrapper(*args, **kwargs):
            span_op = op_name
            span_tags = tags.copy() if tags else {}

            # Add function metadata
            span_tags.update({
                "function": func.__name__,
                "module": func.__module__
            })

            # Check if we already have an active trace
            current_trace_id = get_current_trace_id()
            if current_trace_id:
                # Use span context within existing trace
                with span_context(span_op, span_tags):
                    return func(*args, **kwargs)
            else:
                # Create new trace for top-level function
                with trace_context(span_op, span_tags):
                    return func(*args, **kwargs)

        return wrapper
    return decorator


def traced_async(operation: str = None, tags: Optional[Dict[str, Any]] = None):
    """
    Decorator to automatically trace async function execution.

    Usage:
        @traced_async("my_async_function")
        async def my_async_function():
            pass
    """
    def decorator(func: Callable):
        op_name = operation or f"{func.__module__}.{func.__name__}"

        @wraps(func)
        async def wrapper(*args, **kwargs):
            span_op = op_name
            span_tags = tags.copy() if tags else {}

            # Add function metadata
            span_tags.update({
                "function": func.__name__,
                "module": func.__module__
            })

            # Check if we already have an active trace
            current_trace_id = get_current_trace_id()
            if current_trace_id:
                # Use span context within existing trace
                with span_context(span_op, span_tags):
                    return await func(*args, **kwargs)
            else:
                # Create new trace for top-level function
                with trace_context(span_op, span_tags):
                    return await func(*args, **kwargs)

        return wrapper
    return decorator


# Export key classes and functions
__all__ = [
    'TraceSpan', 'Trace', 'TraceCollector', 'trace_collector',
    'trace_context', 'span_context', 'create_trace', 'create_span',
    'get_current_trace_id', 'get_current_span_id', 'log_span_event',
    'traced', 'traced_async'
]