"""
Metrics collection and monitoring for Weight Loss Chat Agent.

This module provides comprehensive metrics collection for monitoring system
performance, user engagement, and operational health. It supports both
in-memory metrics storage and Prometheus-compatible exports.

Key features:
- Request/response metrics by agent
- Performance histograms and distributions
- Error rate tracking by type
- API usage monitoring
- Database performance metrics
- User engagement analytics
- Cache performance tracking
- Prometheus-compatible exports
"""

import os
import json
import time
import threading
from typing import Dict, List, Any, Optional, Counter as CounterType
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio

from config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MetricPoint:
    """Individual metric data point with timestamp and value."""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CounterMetric:
    """Counter metric that monotonically increases."""
    name: str
    description: str
    value: int = 0
    tags: Dict[str, str] = field(default_factory=dict)

    def increment(self, amount: int = 1, **tag_overrides):
        """Increment the counter by the given amount."""
        self.value += amount
        tags = {**self.tags, **tag_overrides}

        logger.info(f"Counter incremented: {self.name}", extra={
            "operation": "metric_increment",
            "metric_name": self.name,
            "metric_value": self.value,
            "increment_amount": amount,
            "metric_tags": tags
        })


@dataclass
class GaugeMetric:
    """Gauge metric that can increase or decrease."""
    name: str
    description: str
    value: float = 0.0
    tags: Dict[str, str] = field(default_factory=dict)

    def set(self, value: float, **tag_overrides):
        """Set the gauge to the given value."""
        self.value = value
        tags = {**self.tags, **tag_overrides}

        logger.info(f"Gauge set: {self.name}", extra={
            "operation": "metric_set",
            "metric_name": self.name,
            "metric_value": self.value,
            "metric_tags": tags
        })

    def increment(self, amount: float = 1.0, **tag_overrides):
        """Increment the gauge by the given amount."""
        self.value += amount
        tags = {**self.tags, **tag_overrides}

        logger.info(f"Gauge incremented: {self.name}", extra={
            "operation": "metric_increment",
            "metric_name": self.name,
            "metric_value": self.value,
            "increment_amount": amount,
            "metric_tags": tags
        })

    def decrement(self, amount: float = 1.0, **tag_overrides):
        """Decrement the gauge by the given amount."""
        self.value -= amount
        tags = {**self.tags, **tag_overrides}

        logger.info(f"Gauge decremented: {self.name}", extra={
            "operation": "metric_decrement",
            "metric_name": self.name,
            "metric_value": self.value,
            "decrement_amount": amount,
            "metric_tags": tags
        })


@dataclass
class HistogramMetric:
    """Histogram metric for tracking distributions."""
    name: str
    description: str
    buckets: List[float] = field(default_factory=lambda: [0.1, 0.5, 1.0, 2.5, 5.0, 10.0])
    counts: CounterType[float] = field(default_factory=Counter)
    sum: float = 0.0
    count: int = 0
    tags: Dict[str, str] = field(default_factory=dict)

    def observe(self, value: float, **tag_overrides):
        """Observe a value in the histogram."""
        self.count += 1
        self.sum += value

        # Ensure buckets is a list (defensive programming)
        if isinstance(self.buckets, dict):
            # Legacy format: convert dict keys back to sorted list
            buckets_list = []
            for k in self.buckets.keys():
                if k == 'Infinity' or k == float('inf'):
                    buckets_list.append(float('inf'))
                else:
                    try:
                        buckets_list.append(float(k))
                    except (ValueError, TypeError):
                        pass
            buckets_list = sorted(buckets_list)
            self.buckets = buckets_list
        
        # Find the appropriate bucket
        try:
            bucket = next((b for b in self.buckets if value <= b), float('inf'))
        except TypeError as e:
            # If comparison still fails, use a safe default
            logger.warning(f"Error comparing bucket values in histogram {self.name}: {e}. Using Infinity.")
            bucket = float('inf')
        
        self.counts[bucket] += 1

        tags = {**self.tags, **tag_overrides}

        logger.info(f"Histogram observation: {self.name}", extra={
            "operation": "metric_observe",
            "metric_name": self.name,
            "metric_value": value,
            "bucket": bucket,
            "metric_tags": tags
        })

    def get_quantile(self, quantile: float) -> float:
        """Calculate quantile from histogram data."""
        if self.count == 0:
            return 0.0

        # Simple quantile calculation
        sorted_buckets = sorted(self.buckets)
        target_count = quantile * self.count

        cumulative = 0
        for bucket in sorted_buckets:
            cumulative += self.counts[bucket]
            if cumulative >= target_count:
                return bucket

        return sorted_buckets[-1] if sorted_buckets else 0.0


class MetricsCollector:
    """
    Central metrics collection and storage system.

    Provides thread-safe metrics collection with automatic cleanup
    and export capabilities. Now includes file persistence for
    cross-process sharing.
    """

    def __init__(self, persistence_file: Optional[str] = None):
        self._lock = threading.RLock()
        self._counters: Dict[str, CounterMetric] = {}
        self._gauges: Dict[str, GaugeMetric] = {}
        self._histograms: Dict[str, HistogramMetric] = {}
        self._start_time = datetime.utcnow()
        self._persistence_file = persistence_file or os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'metrics.json')
        self._last_save = datetime.utcnow()
        self._save_interval = 0.1  # Save every 100ms
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self._persistence_file), exist_ok=True)
        
        # Load existing data
        self._load_from_file()

    def _load_from_file(self):
        """Load metrics from persistent storage."""
        try:
            if os.path.exists(self._persistence_file):
                with open(self._persistence_file, 'r') as f:
                    data = json.load(f)
                    self._load_metrics_data(data)
                logger.info(f"Loaded metrics from {self._persistence_file}")
        except Exception as e:
            logger.warning(f"Failed to load metrics from file: {e}")

    def _load_metrics_data(self, data: Dict[str, Any]):
        """Load metrics data from dictionary."""
        # Load counters
        for name, counter_data in data.get('counters', {}).items():
            counter = CounterMetric(
                name=name,
                description=counter_data.get('description', f'Loaded counter: {name}'),
                value=counter_data.get('value', 0),
                tags=counter_data.get('tags', {})
            )
            self._counters[name] = counter

        # Load gauges
        for name, gauge_data in data.get('gauges', {}).items():
            gauge = GaugeMetric(
                name=name,
                description=gauge_data.get('description', f'Loaded gauge: {name}'),
                value=gauge_data.get('value', 0.0),
                tags=gauge_data.get('tags', {})
            )
            self._gauges[name] = gauge

        # Load histograms
        for name, hist_data in data.get('histograms', {}).items():
            # Convert buckets from saved format back to floats
            buckets_data = hist_data.get('buckets', [0.1, 0.5, 1.0, 2.5, 5.0, 10.0])
            
            # Handle case where buckets were saved as dict keys (legacy format)
            if isinstance(buckets_data, dict):
                buckets = []
                for k in buckets_data.keys():
                    if k == 'Infinity':
                        buckets.append(float('inf'))
                    else:
                        try:
                            buckets.append(float(k))
                        except (ValueError, TypeError):
                            pass
                buckets = sorted(buckets)
            else:
                # Buckets is a list
                buckets = []
                for b in buckets_data:
                    if b == 'Infinity' or b == float('inf'):
                        buckets.append(float('inf'))
                    else:
                        try:
                            buckets.append(float(b))
                        except (ValueError, TypeError):
                            pass
            
            histogram = HistogramMetric(
                name=name,
                description=hist_data.get('description', f'Loaded histogram: {name}'),
                buckets=buckets if buckets else [0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
                tags=hist_data.get('tags', {})
            )
            histogram.count = hist_data.get('count', 0)
            histogram.sum = hist_data.get('sum', 0.0)
            histogram.counts = Counter(hist_data.get('counts', {}))
            self._histograms[name] = histogram

    def _save_to_file(self):
        """Save metrics to persistent storage."""
        try:
            data = self.get_all_metrics()
            with open(self._persistence_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            self._last_save = datetime.utcnow()
            logger.debug(f"Saved metrics to {self._persistence_file}")
        except Exception as e:
            logger.warning(f"Failed to save metrics to file: {e}")

    def _should_save(self) -> bool:
        """Check if metrics should be saved."""
        return (datetime.utcnow() - self._last_save).total_seconds() >= self._save_interval

    def create_counter(self, name: str, description: str, tags: Optional[Dict[str, str]] = None) -> CounterMetric:
        """Create a new counter metric."""
        with self._lock:
            if name in self._counters:
                return self._counters[name]

            counter = CounterMetric(name=name, description=description, tags=tags or {})
            self._counters[name] = counter
            return counter

    def create_gauge(self, name: str, description: str, tags: Optional[Dict[str, str]] = None) -> GaugeMetric:
        """Create a new gauge metric."""
        with self._lock:
            if name in self._gauges:
                return self._gauges[name]

            gauge = GaugeMetric(name=name, description=description, tags=tags or {})
            self._gauges[name] = gauge
            return gauge

    def create_histogram(self, name: str, description: str, buckets: Optional[List[float]] = None,
                        tags: Optional[Dict[str, str]] = None) -> HistogramMetric:
        """Create a new histogram metric."""
        with self._lock:
            if name in self._histograms:
                return self._histograms[name]

            histogram = HistogramMetric(name=name, description=description,
                                      buckets=buckets or HistogramMetric.buckets,
                                      tags=tags or {})
            self._histograms[name] = histogram
            return histogram

    def get_counter(self, name: str) -> Optional[CounterMetric]:
        """Get an existing counter by name."""
        return self._counters.get(name)

    def get_gauge(self, name: str) -> Optional[GaugeMetric]:
        """Get an existing gauge by name."""
        return self._gauges.get(name)

    def get_histogram(self, name: str) -> Optional[HistogramMetric]:
        """Get an existing histogram by name."""
        return self._histograms.get(name)

    def increment_counter(self, name: str, amount: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter, creating it if it doesn't exist."""
        counter = self.get_counter(name)
        if not counter:
            counter = self.create_counter(name, f"Auto-created counter: {name}")
        counter.increment(amount, **(tags or {}))
        # Always save for critical metrics
        if "requests" in name or "errors" in name:
            self._save_to_file()
        elif self._should_save():
            self._save_to_file()

    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge value, creating it if it doesn't exist."""
        gauge = self.get_gauge(name)
        if not gauge:
            gauge = self.create_gauge(name, f"Auto-created gauge: {name}")
        gauge.set(value, **(tags or {}))
        if self._should_save():
            self._save_to_file()

    def observe_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Observe a value in a histogram, creating it if it doesn't exist."""
        histogram = self.get_histogram(name)
        if not histogram:
            histogram = self.create_histogram(name, f"Auto-created histogram: {name}")
        histogram.observe(value, **(tags or {}))
        # Always save for critical metrics
        if "response_time" in name:
            self._save_to_file()
        elif self._should_save():
            self._save_to_file()

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics as a dictionary."""
        with self._lock:
            return {
                "counters": {name: {"value": counter.value, "description": counter.description, "tags": counter.tags}
                           for name, counter in self._counters.items()},
                "gauges": {name: {"value": gauge.value, "description": gauge.description, "tags": gauge.tags}
                          for name, gauge in self._gauges.items()},
                "histograms": {name: {
                    "count": hist.count,
                    "sum": hist.sum,
                    "buckets": [float('inf') if b == float('inf') else b for b in hist.buckets] if isinstance(hist.buckets, list) else list(hist.buckets.keys()),
                    "counts": dict(hist.counts),
                    "description": hist.description,
                    "tags": hist.tags
                } for name, hist in self._histograms.items()},
                "metadata": {
                    "collection_start_time": self._start_time.isoformat() + "Z",
                    "current_time": datetime.utcnow().isoformat() + "Z"
                }
            }

    def reset_all(self):
        """Reset all metrics to their initial state."""
        with self._lock:
            for counter in self._counters.values():
                counter.value = 0
            for gauge in self._gauges.values():
                gauge.value = 0.0
            for histogram in self._histograms.values():
                histogram.counts.clear()
                histogram.sum = 0.0
                histogram.count = 0

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []

        with self._lock:
            # Counters
            for name, counter in self._counters.items():
                lines.append(f"# HELP {name} {counter.description}")
                lines.append(f"# TYPE {name} counter")
                tags_str = ",".join(f'{k}="{v}"' for k, v in counter.tags.items())
                if tags_str:
                    lines.append(f'{name}{{{tags_str}}} {counter.value}')
                else:
                    lines.append(f'{name} {counter.value}')

            # Gauges
            for name, gauge in self._gauges.items():
                lines.append(f"# HELP {name} {gauge.description}")
                lines.append(f"# TYPE {name} gauge")
                tags_str = ",".join(f'{k}="{v}"' for k, v in gauge.tags.items())
                if tags_str:
                    lines.append(f'{name}{{{tags_str}}} {gauge.value}')
                else:
                    lines.append(f'{name} {gauge.value}')

            # Histograms
            for name, histogram in self._histograms.items():
                lines.append(f"# HELP {name} {histogram.description}")
                lines.append(f"# TYPE {name} histogram")

                # Sum
                lines.append(f'{name}_sum {histogram.sum}')
                # Count
                lines.append(f'{name}_count {histogram.count}')

                # Buckets
                cumulative = 0
                for bucket in sorted(histogram.buckets):
                    cumulative += histogram.counts[bucket]
                    lines.append(f'{name}_bucket{{le="{bucket}"}} {cumulative}')
                lines.append(f'{name}_bucket{{le="+Inf"}} {histogram.count}')

        return "\n".join(lines)


# Global metrics collector instance
metrics_collector = MetricsCollector()

# Pre-defined metrics for the Weight Loss Agent
request_counter = metrics_collector.create_counter(
    "agent_requests_total",
    "Total number of agent requests processed",
    tags={"service": "weight_loss_agent"}
)

response_time_histogram = metrics_collector.create_histogram(
    "agent_response_time_seconds",
    "Response time distribution for agent requests",
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
    tags={"service": "weight_loss_agent"}
)

error_counter = metrics_collector.create_counter(
    "agent_errors_total",
    "Total number of agent errors by type",
    tags={"service": "weight_loss_agent"}
)

api_call_counter = metrics_collector.create_counter(
    "api_calls_total",
    "Total number of API calls by provider",
    tags={"service": "weight_loss_agent"}
)

db_query_counter = metrics_collector.create_counter(
    "db_queries_total",
    "Total number of database queries",
    tags={"service": "weight_loss_agent"}
)

active_sessions_gauge = metrics_collector.create_gauge(
    "active_sessions",
    "Number of currently active user sessions",
    tags={"service": "weight_loss_agent"}
)

cache_hit_ratio_gauge = metrics_collector.create_gauge(
    "cache_hit_ratio",
    "Cache hit ratio (0.0 to 1.0)",
    tags={"service": "weight_loss_agent"}
)

user_engagement_histogram = metrics_collector.create_histogram(
    "user_messages_per_session",
    "Distribution of messages per user session",
    buckets=[1.0, 2.0, 5.0, 10.0, 20.0, 50.0],
    tags={"service": "weight_loss_agent"}
)


# Convenience functions for common metric operations
def record_request(agent: str, user_id: Optional[str] = None):
    """Record an agent request."""
    tags = {"agent": agent}
    if user_id:
        tags["user_id"] = user_id
    request_counter.increment(tags=tags)


def record_response_time(agent: str, duration_seconds: float, user_id: Optional[str] = None, **tags):
    """Record response time for an agent request."""
    all_tags = {"agent": agent}
    if user_id:
        all_tags["user_id"] = user_id
    all_tags.update(tags)
    response_time_histogram.observe(duration_seconds, **all_tags)


def record_error(error_type: str, agent: Optional[str] = None, user_id: Optional[str] = None, **tags):
    """Record an error occurrence."""
    all_tags = {"error_type": error_type}
    if agent:
        all_tags["agent"] = agent
    if user_id:
        all_tags["user_id"] = user_id
    all_tags.update(tags)
    error_counter.increment(tags=all_tags)


def record_api_call(provider: str, endpoint: Optional[str] = None, success: bool = True):
    """Record an API call."""
    tags = {"provider": provider, "success": str(success)}
    if endpoint:
        tags["endpoint"] = endpoint
    api_call_counter.increment(tags=tags)


def record_db_query(operation: str, table: Optional[str] = None, duration_ms: Optional[float] = None):
    """Record a database query."""
    tags = {"operation": operation}
    if table:
        tags["table"] = table
    db_query_counter.increment(tags=tags)

    if duration_ms is not None:
        metrics_collector.observe_histogram("db_query_duration_ms", duration_ms, **tags)


def update_active_sessions(count: int):
    """Update the active sessions gauge."""
    active_sessions_gauge.set(count)


def update_cache_hit_ratio(ratio: float):
    """Update the cache hit ratio gauge."""
    cache_hit_ratio_gauge.set(ratio)


def record_user_engagement(messages_count: int, session_duration_minutes: Optional[float] = None):
    """Record user engagement metrics."""
    user_engagement_histogram.observe(messages_count)

    if session_duration_minutes is not None:
        metrics_collector.observe_histogram("session_duration_minutes", session_duration_minutes)


# Export key classes and functions
__all__ = [
    'MetricPoint', 'CounterMetric', 'GaugeMetric', 'HistogramMetric',
    'MetricsCollector', 'metrics_collector',
    'record_request', 'record_response_time', 'record_error',
    'record_api_call', 'record_db_query', 'update_active_sessions',
    'update_cache_hit_ratio', 'record_user_engagement'
]