"""
Observability Dashboard for Weight Loss Chat Agent.

A Flask-based monitoring dashboard providing real-time metrics, logs,
traces, and system health monitoring with interactive visualizations.

Features:
- Real-time metrics dashboard
- Searchable log viewer
- Trace explorer
- Performance charts
- System health monitoring
- API usage analytics
"""

import os
import json
import time
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
import threading

from flask import Flask, render_template, jsonify, request, Response
from flask_cors import CORS

# Import observability modules
from config.logging import get_logger
from config.settings import settings
from observability.metrics import metrics_collector
from observability.tracing import trace_collector

logger = get_logger(__name__)

# Create Flask app
app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), 'static'))

CORS(app)

# Global state for real-time updates
dashboard_state = {
    "last_update": datetime.now(UTC),
    "active_connections": 0,
    "update_interval": 5  # seconds
}


@app.route('/')
def index():
    """Main dashboard overview page."""
    return render_template('dashboard.html')


@app.route('/dashboard/')
def dashboard():
    """Dashboard overview with key metrics."""
    return render_template('dashboard.html')


@app.route('/dashboard/logs')
def logs():
    """Searchable log viewer."""
    return render_template('logs.html')


@app.route('/dashboard/traces')
def traces():
    """Trace explorer."""
    return render_template('traces.html')


@app.route('/dashboard/metrics')
def detailed_metrics():
    """Detailed metrics charts."""
    return render_template('metrics.html')


@app.route('/dashboard/health')
def health():
    """System health check."""
    return render_template('health.html')


# API Endpoints

@app.route('/api/metrics')
def get_metrics():
    """Get current metrics data."""
    try:
        # Try to load from file first, fall back to in-memory collector
        metrics_file = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'metrics.json')
        if os.path.exists(metrics_file):
            try:
                with open(metrics_file, 'r') as f:
                    metrics = json.load(f)
                logger.debug("Loaded metrics from file")
            except Exception as e:
                logger.warning(f"Failed to load metrics from file: {e}")
                metrics = metrics_collector.get_all_metrics()
        else:
            metrics = metrics_collector.get_all_metrics()

        # Add computed metrics
        counters = metrics.get('counters', {})
        total_requests = sum(counter.get('value', 0) for counter in counters.values()
                           if 'requests' in counter.get('description', '').lower())

        total_errors = sum(counter.get('value', 0) for counter in counters.values()
                          if 'error' in counter.get('description', '').lower())

        error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0

        metrics['computed'] = {
            'total_requests': total_requests,
            'total_errors': total_errors,
            'error_rate_percent': round(error_rate, 2)
        }

        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/logs')
def get_logs():
    """Get recent logs with optional filtering."""
    try:
        # Get query parameters
        limit = int(request.args.get('limit', 100))
        level = request.args.get('level')
        agent = request.args.get('agent')
        user_id = request.args.get('user_id')
        search = request.args.get('search')

        # Read recent logs from log file
        logs = read_recent_logs(limit=limit)

        # Apply filters
        filtered_logs = []
        for log in logs:
            if level and log.get('level') != level:
                continue
            if agent and log.get('agent') != agent:
                continue
            if user_id and log.get('user_id') != user_id:
                continue
            if search and search.lower() not in json.dumps(log).lower():
                continue
            filtered_logs.append(log)

        return jsonify({
            "logs": filtered_logs[:limit],
            "total": len(filtered_logs),
            "filters": {
                "level": level,
                "agent": agent,
                "user_id": user_id,
                "search": search
            }
        })
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/traces')
def get_traces():
    """Get trace data."""
    try:
        active_traces = trace_collector.get_active_traces()
        completed_traces = trace_collector.get_completed_traces(limit=50)

        traces_data = {
            "active": [trace.to_dict() for trace in active_traces],
            "completed": [trace.to_dict() for trace in completed_traces]
        }

        return jsonify(traces_data)
    except Exception as e:
        logger.error(f"Error getting traces: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/trace/<trace_id>')
def get_trace(trace_id: str):
    """Get detailed trace information."""
    try:
        trace = trace_collector.get_trace(trace_id)
        if not trace:
            return jsonify({"error": "Trace not found"}), 404

        return jsonify(trace.to_dict())
    except Exception as e:
        logger.error(f"Error getting trace {trace_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/health')
def get_health():
    """Get system health status."""
    try:
        from config.logging import HealthChecker
        health = HealthChecker.get_system_health()

        # Add observability health
        health["observability"] = {
            "metrics_collector": "healthy",
            "trace_collector": "healthy",
            "active_traces": len(trace_collector.get_active_traces()),
            "completed_traces": len(trace_collector.get_completed_traces())
        }

        return jsonify(health)
    except Exception as e:
        logger.error(f"Error getting health: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/performance')
def get_performance():
    """Get performance analytics."""
    try:
        # Get response time histogram data
        response_time_hist = metrics_collector.get_histogram("agent_response_time_seconds")
        if response_time_hist:
            percentiles = {
                "p50": response_time_hist.get_quantile(0.5),
                "p95": response_time_hist.get_quantile(0.95),
                "p99": response_time_hist.get_quantile(0.99)
            }
        else:
            percentiles = {"p50": 0, "p95": 0, "p99": 0}

        # Get agent performance breakdown
        agent_requests = defaultdict(int)
        agent_errors = defaultdict(int)

        for name, counter in metrics_collector._counters.items():
            if "agent_requests_total" in name:
                for tag_key, tag_value in counter.tags.items():
                    if tag_key == "agent":
                        agent_requests[tag_value] += counter.value

            if "agent_errors_total" in name:
                for tag_key, tag_value in counter.tags.items():
                    if tag_key == "agent":
                        agent_errors[tag_value] += counter.value

        agent_performance = []
        for agent in agent_requests:
            total = agent_requests[agent]
            errors = agent_errors.get(agent, 0)
            success_rate = ((total - errors) / total * 100) if total > 0 else 0
            agent_performance.append({
                "agent": agent,
                "total_requests": total,
                "errors": errors,
                "success_rate": round(success_rate, 2)
            })

        return jsonify({
            "response_time_percentiles": percentiles,
            "agent_performance": agent_performance
        })
    except Exception as e:
        logger.error(f"Error getting performance data: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/stream')
def stream_updates():
    """Server-sent events for real-time updates."""
    def generate():
        while True:
            try:
                # Send metrics update
                metrics = metrics_collector.get_all_metrics()
                yield f"data: {json.dumps({'type': 'metrics', 'data': metrics})}\n\n"

                # Send health update
                from config.logging import HealthChecker
                health = HealthChecker.get_system_health()
                yield f"data: {json.dumps({'type': 'health', 'data': health})}\n\n"

                time.sleep(dashboard_state["update_interval"])

            except Exception as e:
                logger.error(f"Error in stream: {e}")
                time.sleep(1)

    return Response(generate(), mimetype='text/event-stream')


def read_recent_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """Read recent logs from the log file."""
    logs = []

    try:
        log_file = settings.log_path
        if not log_file.exists():
            return logs

        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()[-limit:]  # Get last N lines

        for line in reversed(lines):  # Process in reverse to get newest first
            line = line.strip()
            if not line:
                continue

            try:
                log_entry = json.loads(line)
                logs.append(log_entry)
                if len(logs) >= limit:
                    break
            except json.JSONDecodeError:
                # Skip malformed lines
                continue

    except Exception as e:
        logger.error(f"Error reading logs: {e}")

    return logs


@app.context_processor
def inject_globals():
    """Inject global variables into templates."""
    return {
        'now': datetime.now(UTC),
        'settings': settings
    }


if __name__ == '__main__':
    logger.info(f"Starting observability dashboard on port {settings.dashboard_port}")
    app.run(
        host='0.0.0.0',
        port=settings.dashboard_port,
        debug=settings.debug,
        threaded=True
    )