"""
Observability Alerts Module

Provides alerting capabilities for the Weight Loss Agent observability system.
Supports console notifications and Telegram alerts for various conditions.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
import json

from config.settings import settings
from observability.metrics import metrics_collector

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of alerts that can be triggered"""
    RESPONSE_TIME_HIGH = "response_time_high"
    ERROR_RATE_HIGH = "error_rate_high"
    API_FAILURE = "api_failure"
    DATABASE_CONNECTION_ERROR = "database_connection_error"
    MEMORY_USAGE_HIGH = "memory_usage_high"
    DISK_SPACE_LOW = "disk_space_low"
    AGENT_FAILURE_RATE_HIGH = "agent_failure_rate_high"


@dataclass
class Alert:
    """Represents an alert instance"""
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for serialization"""
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "metadata": self.metadata or {}
        }


class AlertNotifier:
    """Base class for alert notifiers"""

    async def notify(self, alert: Alert) -> bool:
        """Send notification for alert. Returns True if successful."""
        raise NotImplementedError


class ConsoleNotifier(AlertNotifier):
    """Console-based alert notifier"""

    async def notify(self, alert: Alert) -> bool:
        """Log alert to console"""
        try:
            severity_color = {
                AlertSeverity.LOW: "\033[92m",  # Green
                AlertSeverity.MEDIUM: "\033[93m",  # Yellow
                AlertSeverity.HIGH: "\033[91m",  # Red
                AlertSeverity.CRITICAL: "\033[95m"  # Magenta
            }.get(alert.severity, "\033[0m")

            reset_color = "\033[0m"

            message = f"{severity_color}[{alert.severity.value.upper()}] {alert.title}{reset_color}\n"
            message += f"  {alert.message}\n"
            message += f"  Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"

            if alert.metadata:
                message += f"  Metadata: {json.dumps(alert.metadata, indent=2)}\n"

            print(message)
            logger.info(f"Alert notification sent to console: {alert.alert_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send console alert: {e}")
            return False


class TelegramNotifier(AlertNotifier):
    """Telegram-based alert notifier"""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    async def notify(self, alert: Alert) -> bool:
        """Send alert via Telegram"""
        try:
            import aiohttp

            emoji_map = {
                AlertSeverity.LOW: "ℹ️",
                AlertSeverity.MEDIUM: "⚠️",
                AlertSeverity.HIGH: "🚨",
                AlertSeverity.CRITICAL: "💥"
            }

            emoji = emoji_map.get(alert.severity, "📢")

            message = f"{emoji} **{alert.title}**\n\n"
            message += f"{alert.message}\n\n"
            message += f"🕐 {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
            message += f"⚡ Severity: {alert.severity.value.upper()}"

            if alert.metadata:
                message += f"\n\n📊 Details:\n"
                for key, value in alert.metadata.items():
                    message += f"• {key}: {value}\n"

            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/sendMessage", json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Alert notification sent to Telegram: {alert.alert_id}")
                        return True
                    else:
                        logger.error(f"Telegram API error: {response.status} - {await response.text()}")
                        return False

        except ImportError:
            logger.warning("aiohttp not available for Telegram notifications")
            return False
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False


class AlertManager:
    """Manages alerts and notifications"""

    def __init__(self):
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notifiers: List[AlertNotifier] = []
        self.alert_rules: Dict[AlertType, Dict[str, Any]] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._is_running = False

        # Default alert rules
        self._setup_default_rules()

    def _setup_default_rules(self):
        """Setup default alert rules"""
        self.alert_rules = {
            AlertType.RESPONSE_TIME_HIGH: {
                "threshold": 5.0,  # seconds
                "severity": AlertSeverity.HIGH,
                "cooldown": 300,  # 5 minutes
                "description": "Response time exceeded threshold"
            },
            AlertType.ERROR_RATE_HIGH: {
                "threshold": 0.05,  # 5%
                "severity": AlertSeverity.MEDIUM,
                "cooldown": 600,  # 10 minutes
                "description": "Error rate exceeded threshold"
            },
            AlertType.API_FAILURE: {
                "severity": AlertSeverity.CRITICAL,
                "cooldown": 60,  # 1 minute
                "description": "API call failed"
            },
            AlertType.DATABASE_CONNECTION_ERROR: {
                "severity": AlertSeverity.CRITICAL,
                "cooldown": 30,  # 30 seconds
                "description": "Database connection failed"
            },
            AlertType.AGENT_FAILURE_RATE_HIGH: {
                "threshold": 0.10,  # 10%
                "severity": AlertSeverity.HIGH,
                "cooldown": 300,  # 5 minutes
                "description": "Agent failure rate exceeded threshold"
            }
        }

    def add_notifier(self, notifier: AlertNotifier):
        """Add an alert notifier"""
        self.notifiers.append(notifier)

    def create_alert(self, alert_type: AlertType, title: str, message: str,
                    metadata: Dict[str, Any] = None) -> str:
        """Create a new alert"""
        alert_id = f"{alert_type.value}_{int(datetime.now().timestamp())}"

        rule = self.alert_rules.get(alert_type, {})
        severity = rule.get("severity", AlertSeverity.MEDIUM)

        alert = Alert(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )

        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)

        # Keep only last 1000 alerts in history
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]

        logger.info(f"Alert created: {alert_id} - {title}")

        # Send notifications asynchronously
        asyncio.create_task(self._notify_alert(alert))

        return alert_id

    async def _notify_alert(self, alert: Alert):
        """Send alert to all notifiers"""
        for notifier in self.notifiers:
            try:
                success = await notifier.notify(alert)
                if not success:
                    logger.warning(f"Failed to send alert via {type(notifier).__name__}")
            except Exception as e:
                logger.error(f"Error notifying via {type(notifier).__name__}: {e}")

    def resolve_alert(self, alert_id: str):
        """Resolve an active alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.now()

            logger.info(f"Alert resolved: {alert_id}")

            # Send resolution notification
            resolution_alert = Alert(
                alert_id=f"{alert_id}_resolved",
                alert_type=alert.alert_type,
                severity=AlertSeverity.LOW,
                title=f"RESOLVED: {alert.title}",
                message=f"Alert has been resolved: {alert.message}",
                timestamp=datetime.now(),
                resolved=True,
                metadata={"original_alert_id": alert_id}
            )

            asyncio.create_task(self._notify_alert(resolution_alert))

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return list(self.active_alerts.values())

    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history"""
        return self.alert_history[-limit:]

    async def check_alerts(self):
        """Check metrics and create alerts based on rules"""
        try:
            # Check response time
            response_times = metrics_collector.get_histogram_data("response_time")
            if response_times and response_times.get("p95", 0) > self.alert_rules[AlertType.RESPONSE_TIME_HIGH]["threshold"]:
                rule = self.alert_rules[AlertType.RESPONSE_TIME_HIGH]
                if self._should_trigger_alert(AlertType.RESPONSE_TIME_HIGH, rule["cooldown"]):
                    self.create_alert(
                        AlertType.RESPONSE_TIME_HIGH,
                        "High Response Time Detected",
                        f"P95 response time is {response_times['p95']:.2f}s (threshold: {rule['threshold']}s)",
                        {"p95_response_time": response_times["p95"]}
                    )

            # Check error rate
            error_count = metrics_collector.get_counter_value("errors_total")
            total_requests = metrics_collector.get_counter_value("requests_total")

            if total_requests > 0:
                error_rate = error_count / total_requests
                if error_rate > self.alert_rules[AlertType.ERROR_RATE_HIGH]["threshold"]:
                    rule = self.alert_rules[AlertType.ERROR_RATE_HIGH]
                    if self._should_trigger_alert(AlertType.ERROR_RATE_HIGH, rule["cooldown"]):
                        self.create_alert(
                            AlertType.ERROR_RATE_HIGH,
                            "High Error Rate Detected",
                            f"Error rate is {error_rate:.1%} (threshold: {rule['threshold']:.1%})",
                            {"error_rate": error_rate, "error_count": error_count, "total_requests": total_requests}
                        )

            # Check agent failure rates
            agent_metrics = metrics_collector.get_all_metrics()
            for metric_name, metric_data in agent_metrics.items():
                if metric_name.startswith("agent_") and metric_name.endswith("_errors"):
                    agent_name = metric_name.replace("agent_", "").replace("_errors", "")
                    error_count = metric_data.get("value", 0)
                    success_metric = f"agent_{agent_name}_success"
                    success_count = agent_metrics.get(success_metric, {}).get("value", 0)

                    total = error_count + success_count
                    if total > 0:
                        failure_rate = error_count / total
                        if failure_rate > self.alert_rules[AlertType.AGENT_FAILURE_RATE_HIGH]["threshold"]:
                            rule = self.alert_rules[AlertType.AGENT_FAILURE_RATE_HIGH]
                            if self._should_trigger_alert(AlertType.AGENT_FAILURE_RATE_HIGH, rule["cooldown"]):
                                self.create_alert(
                                    AlertType.AGENT_FAILURE_RATE_HIGH,
                                    f"High Failure Rate: {agent_name}",
                                    f"Agent {agent_name} failure rate is {failure_rate:.1%} (threshold: {rule['threshold']:.1%})",
                                    {"agent": agent_name, "failure_rate": failure_rate, "error_count": error_count, "total_requests": total}
                                )

        except Exception as e:
            logger.error(f"Error checking alerts: {e}")

    def _should_trigger_alert(self, alert_type: AlertType, cooldown_seconds: int) -> bool:
        """Check if alert should be triggered based on cooldown"""
        now = datetime.now()

        # Check recent alerts of this type
        for alert in reversed(self.alert_history):
            if alert.alert_type == alert_type and not alert.resolved:
                # Still active
                return False

            if alert.alert_type == alert_type:
                # Check cooldown
                time_diff = (now - alert.timestamp).total_seconds()
                if time_diff < cooldown_seconds:
                    return False
                break

        return True

    async def start_monitoring(self):
        """Start the alert monitoring loop"""
        if self._is_running:
            return

        self._is_running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

        logger.info("Alert monitoring started")

    async def stop_monitoring(self):
        """Stop the alert monitoring loop"""
        self._is_running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("Alert monitoring stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._is_running:
            try:
                await self.check_alerts()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in alert monitoring loop: {e}")
                await asyncio.sleep(60)


# Global alert manager instance
alert_manager = AlertManager()

# Setup default notifiers
alert_manager.add_notifier(ConsoleNotifier())

# Setup Telegram notifier if configured
if hasattr(settings, 'TELEGRAM_BOT_TOKEN') and hasattr(settings, 'TELEGRAM_CHAT_ID'):
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
        alert_manager.add_notifier(TelegramNotifier(
            settings.TELEGRAM_BOT_TOKEN,
            settings.TELEGRAM_CHAT_ID
        ))


def create_response_time_alert(response_time: float, agent: str = None):
    """Create an alert for high response time"""
    metadata = {"response_time": response_time}
    if agent:
        metadata["agent"] = agent

    alert_manager.create_alert(
        AlertType.RESPONSE_TIME_HIGH,
        "High Response Time",
        f"Response time of {response_time:.2f}s exceeded threshold",
        metadata
    )


def create_error_rate_alert(error_rate: float, total_requests: int):
    """Create an alert for high error rate"""
    alert_manager.create_alert(
        AlertType.ERROR_RATE_HIGH,
        "High Error Rate",
        f"Error rate of {error_rate:.1%} with {total_requests} total requests",
        {"error_rate": error_rate, "total_requests": total_requests}
    )


def create_api_failure_alert(api_name: str, error: str):
    """Create an alert for API failure"""
    alert_manager.create_alert(
        AlertType.API_FAILURE,
        f"API Failure: {api_name}",
        f"API call to {api_name} failed: {error}",
        {"api_name": api_name, "error": error}
    )


def create_database_error_alert(error: str):
    """Create an alert for database connection error"""
    alert_manager.create_alert(
        AlertType.DATABASE_CONNECTION_ERROR,
        "Database Connection Error",
        f"Database connection failed: {error}",
        {"error": error}
    )


def create_agent_failure_alert(agent_name: str, failure_rate: float):
    """Create an alert for high agent failure rate"""
    alert_manager.create_alert(
        AlertType.AGENT_FAILURE_RATE_HIGH,
        f"Agent Failure: {agent_name}",
        f"Agent {agent_name} has failure rate of {failure_rate:.1%}",
        {"agent": agent_name, "failure_rate": failure_rate}
    )