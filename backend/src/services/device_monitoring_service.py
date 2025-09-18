"""
Device status monitoring service.

Monitors device health, connectivity, and performance metrics with
alerting capabilities and automated status updates.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from influxdb_client import InfluxDBClient

from ..models.Device import Device
from ..models.DeviceStatusSnapshot import DeviceStatusSnapshot
from ..database import get_async_session

# Setup logging
logger = logging.getLogger(__name__)


class DeviceStatus(str, Enum):
    """Device status enumeration."""
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    WARNING = "warning"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class DeviceHealthMetrics:
    """Device health metrics."""
    device_id: str
    last_seen: Optional[datetime] = None
    status: DeviceStatus = DeviceStatus.OFFLINE
    battery_level: Optional[float] = None
    signal_strength: Optional[float] = None
    uptime_seconds: Optional[int] = None
    firmware_version: Optional[str] = None
    telemetry_count_last_hour: int = 0
    avg_response_time_ms: Optional[float] = None
    error_count_last_hour: int = 0
    temperature: Optional[float] = None
    is_healthy: bool = True
    health_score: float = 100.0
    alerts: List[str] = field(default_factory=list)


@dataclass
class MonitoringRule:
    """Device monitoring rule definition."""
    name: str
    description: str
    condition: Callable[[DeviceHealthMetrics], bool]
    severity: AlertSeverity
    action: Optional[Callable[[str, DeviceHealthMetrics], None]] = None
    enabled: bool = True
    cooldown_minutes: int = 5


@dataclass
class MonitoringConfig:
    """Configuration for device monitoring service."""
    # Timing Configuration
    check_interval_seconds: int = 30
    offline_threshold_minutes: int = 5
    health_check_interval_minutes: int = 1

    # InfluxDB Configuration
    influxdb_url: str = "http://localhost:8086"
    influxdb_token: str = ""
    influxdb_org: str = "iot-org"
    influxdb_bucket: str = "telemetry"

    # Thresholds
    low_battery_threshold: float = 20.0
    poor_signal_threshold: float = -80.0
    high_temperature_threshold: float = 80.0
    min_telemetry_rate_per_hour: int = 10
    max_error_rate_per_hour: int = 5

    # Alerting
    enable_alerts: bool = True
    alert_endpoints: List[str] = field(default_factory=list)
    max_alerts_per_device_per_hour: int = 10


class DeviceMonitoringService:
    """Device status monitoring and alerting service."""

    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.running = False
        self.influxdb_client: Optional[InfluxDBClient] = None

        # Monitoring state
        self.device_metrics: Dict[str, DeviceHealthMetrics] = {}
        self.monitoring_rules: List[MonitoringRule] = []
        self.alert_cooldowns: Dict[str, datetime] = {}
        self.alert_counts: Dict[str, Dict[str, int]] = {}  # device_id -> {hour: count}

        # Background tasks
        self.background_tasks: List[asyncio.Task] = []

        # Initialize default monitoring rules
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        """Initialize default monitoring rules."""
        self.monitoring_rules = [
            MonitoringRule(
                name="device_offline",
                description="Device has been offline for too long",
                condition=lambda m: m.status == DeviceStatus.OFFLINE and (
                    not m.last_seen or
                    (datetime.utcnow() - m.last_seen).total_seconds() > self.config.offline_threshold_minutes * 60
                ),
                severity=AlertSeverity.ERROR
            ),
            MonitoringRule(
                name="low_battery",
                description="Device battery level is critically low",
                condition=lambda m: (
                    m.battery_level is not None and
                    m.battery_level < self.config.low_battery_threshold
                ),
                severity=AlertSeverity.WARNING
            ),
            MonitoringRule(
                name="poor_signal",
                description="Device signal strength is poor",
                condition=lambda m: (
                    m.signal_strength is not None and
                    m.signal_strength < self.config.poor_signal_threshold
                ),
                severity=AlertSeverity.WARNING
            ),
            MonitoringRule(
                name="high_temperature",
                description="Device temperature is above safe threshold",
                condition=lambda m: (
                    m.temperature is not None and
                    m.temperature > self.config.high_temperature_threshold
                ),
                severity=AlertSeverity.CRITICAL
            ),
            MonitoringRule(
                name="low_telemetry_rate",
                description="Device telemetry rate is below expected threshold",
                condition=lambda m: m.telemetry_count_last_hour < self.config.min_telemetry_rate_per_hour,
                severity=AlertSeverity.WARNING
            ),
            MonitoringRule(
                name="high_error_rate",
                description="Device error rate is above acceptable threshold",
                condition=lambda m: m.error_count_last_hour > self.config.max_error_rate_per_hour,
                severity=AlertSeverity.ERROR
            ),
        ]

    async def start(self):
        """Start the monitoring service."""
        if self.running:
            logger.warning("Monitoring service already running")
            return

        logger.info("Starting device monitoring service")

        try:
            # Initialize InfluxDB client
            self.influxdb_client = InfluxDBClient(
                url=self.config.influxdb_url,
                token=self.config.influxdb_token,
                org=self.config.influxdb_org
            )

            # Test connection
            health = self.influxdb_client.health()
            if health.status != "pass":
                raise Exception(f"InfluxDB health check failed: {health.message}")

            # Start background tasks
            self.running = True
            self._start_background_tasks()

            logger.info("Device monitoring service started successfully")

        except Exception as e:
            logger.error(f"Failed to start monitoring service: {e}")
            await self.stop()
            raise

    async def stop(self):
        """Stop the monitoring service."""
        logger.info("Stopping device monitoring service")

        self.running = False

        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()

        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)

        # Close InfluxDB client
        if self.influxdb_client:
            self.influxdb_client.close()

        logger.info("Device monitoring service stopped")

    def _start_background_tasks(self):
        """Start background monitoring tasks."""
        # Device health checker
        self.background_tasks.append(
            asyncio.create_task(self._device_health_checker())
        )

        # Status updater
        self.background_tasks.append(
            asyncio.create_task(self._status_updater())
        )

        # Alert processor
        self.background_tasks.append(
            asyncio.create_task(self._alert_processor())
        )

        # Cleanup task
        self.background_tasks.append(
            asyncio.create_task(self._cleanup_task())
        )

    async def _device_health_checker(self):
        """Background task to check device health."""
        while self.running:
            try:
                await self._check_all_device_health()
                await asyncio.sleep(self.config.health_check_interval_minutes * 60)
            except Exception as e:
                logger.error(f"Device health checker error: {e}")
                await asyncio.sleep(60)

    async def _status_updater(self):
        """Background task to update device statuses."""
        while self.running:
            try:
                await self._update_device_statuses()
                await asyncio.sleep(self.config.check_interval_seconds)
            except Exception as e:
                logger.error(f"Status updater error: {e}")
                await asyncio.sleep(30)

    async def _alert_processor(self):
        """Background task to process alerts."""
        while self.running:
            try:
                await self._process_alerts()
                await asyncio.sleep(30)  # Check for alerts every 30 seconds
            except Exception as e:
                logger.error(f"Alert processor error: {e}")
                await asyncio.sleep(30)

    async def _cleanup_task(self):
        """Background task for cleanup operations."""
        while self.running:
            try:
                await self._cleanup_old_data()
                await asyncio.sleep(3600)  # Cleanup every hour
            except Exception as e:
                logger.error(f"Cleanup task error: {e}")
                await asyncio.sleep(3600)

    async def _check_all_device_health(self):
        """Check health for all monitored devices."""
        async with get_async_session() as session:
            # Get all active devices
            result = await session.execute(
                select(Device).where(Device.status != "maintenance")
            )
            devices = result.scalars().all()

            for device in devices:
                try:
                    await self._update_device_metrics(device.id)
                except Exception as e:
                    logger.error(f"Failed to update metrics for device {device.id}: {e}")

    async def _update_device_metrics(self, device_id: str):
        """Update health metrics for a specific device."""
        try:
            # Get latest telemetry data from InfluxDB
            telemetry_data = await self._query_device_telemetry(device_id)

            # Get latest status data
            status_data = await self._query_device_status(device_id)

            # Calculate metrics
            metrics = self._calculate_health_metrics(device_id, telemetry_data, status_data)

            # Update metrics cache
            self.device_metrics[device_id] = metrics

            logger.debug(f"Updated metrics for device {device_id}: health_score={metrics.health_score}")

        except Exception as e:
            logger.error(f"Failed to update metrics for device {device_id}: {e}")
            # Create default metrics for offline device
            self.device_metrics[device_id] = DeviceHealthMetrics(
                device_id=device_id,
                status=DeviceStatus.ERROR,
                is_healthy=False,
                health_score=0.0,
                alerts=[f"Failed to retrieve metrics: {str(e)}"]
            )

    async def _query_device_telemetry(self, device_id: str) -> Dict[str, Any]:
        """Query recent telemetry data for a device."""
        query = f'''
        from(bucket: "{self.config.influxdb_bucket}")
          |> range(start: -1h)
          |> filter(fn: (r) => r._measurement == "device_telemetry")
          |> filter(fn: (r) => r.device_id == "{device_id}")
          |> last()
        '''

        try:
            query_api = self.influxdb_client.query_api()
            tables = query_api.query(query, org=self.config.influxdb_org)

            telemetry_data = {}
            for table in tables:
                for record in table.records:
                    field_name = record.get_field()
                    value = record.get_value()
                    telemetry_data[field_name] = value

            return telemetry_data

        except Exception as e:
            logger.warning(f"Failed to query telemetry for device {device_id}: {e}")
            return {}

    async def _query_device_status(self, device_id: str) -> Dict[str, Any]:
        """Query recent status data for a device."""
        query = f'''
        from(bucket: "{self.config.influxdb_bucket}")
          |> range(start: -1h)
          |> filter(fn: (r) => r._measurement == "device_status")
          |> filter(fn: (r) => r.device_id == "{device_id}")
          |> last()
        '''

        try:
            query_api = self.influxdb_client.query_api()
            tables = query_api.query(query, org=self.config.influxdb_org)

            status_data = {}
            for table in tables:
                for record in table.records:
                    field_name = record.get_field()
                    value = record.get_value()
                    status_data[field_name] = value

            return status_data

        except Exception as e:
            logger.warning(f"Failed to query status for device {device_id}: {e}")
            return {}

    def _calculate_health_metrics(self, device_id: str, telemetry_data: Dict[str, Any], status_data: Dict[str, Any]) -> DeviceHealthMetrics:
        """Calculate health metrics for a device."""
        metrics = DeviceHealthMetrics(device_id=device_id)

        # Extract status information
        if status_data:
            metrics.status = DeviceStatus(status_data.get('status', 'offline'))
            metrics.battery_level = status_data.get('battery_level')
            metrics.signal_strength = status_data.get('signal_strength')
            metrics.uptime_seconds = status_data.get('uptime_seconds')
            metrics.firmware_version = status_data.get('firmware_version')

        # Extract telemetry information
        if telemetry_data:
            metrics.temperature = telemetry_data.get('temperature_value')

        # Calculate health score
        health_score = 100.0

        # Penalize for offline status
        if metrics.status == DeviceStatus.OFFLINE:
            health_score -= 50
        elif metrics.status == DeviceStatus.ERROR:
            health_score -= 30
        elif metrics.status == DeviceStatus.WARNING:
            health_score -= 10

        # Penalize for low battery
        if metrics.battery_level is not None:
            if metrics.battery_level < 10:
                health_score -= 20
            elif metrics.battery_level < 20:
                health_score -= 10
            elif metrics.battery_level < 30:
                health_score -= 5

        # Penalize for poor signal
        if metrics.signal_strength is not None:
            if metrics.signal_strength < -90:
                health_score -= 15
            elif metrics.signal_strength < -80:
                health_score -= 10
            elif metrics.signal_strength < -70:
                health_score -= 5

        # Penalize for high temperature
        if metrics.temperature is not None:
            if metrics.temperature > 85:
                health_score -= 25
            elif metrics.temperature > 80:
                health_score -= 15
            elif metrics.temperature > 75:
                health_score -= 5

        metrics.health_score = max(0.0, health_score)
        metrics.is_healthy = metrics.health_score > 70.0

        return metrics

    async def _update_device_statuses(self):
        """Update device statuses in database."""
        async with get_async_session() as session:
            for device_id, metrics in self.device_metrics.items():
                try:
                    # Update device status
                    await session.execute(
                        update(Device)
                        .where(Device.id == device_id)
                        .values(
                            status=metrics.status.value,
                            last_seen=metrics.last_seen
                        )
                    )

                    # Create status snapshot
                    snapshot = DeviceStatusSnapshot(
                        device_id=device_id,
                        status=metrics.status.value,
                        health_score=metrics.health_score,
                        battery_level=metrics.battery_level,
                        signal_strength=metrics.signal_strength,
                        temperature=metrics.temperature,
                        uptime_seconds=metrics.uptime_seconds,
                        firmware_version=metrics.firmware_version,
                        telemetry_count_last_hour=metrics.telemetry_count_last_hour,
                        error_count_last_hour=metrics.error_count_last_hour,
                        timestamp=datetime.utcnow()
                    )

                    session.add(snapshot)

                except Exception as e:
                    logger.error(f"Failed to update status for device {device_id}: {e}")

            await session.commit()

    async def _process_alerts(self):
        """Process alerts based on monitoring rules."""
        if not self.config.enable_alerts:
            return

        for device_id, metrics in self.device_metrics.items():
            for rule in self.monitoring_rules:
                if not rule.enabled:
                    continue

                try:
                    # Check if rule condition is met
                    if rule.condition(metrics):
                        await self._trigger_alert(device_id, rule, metrics)

                except Exception as e:
                    logger.error(f"Error processing rule {rule.name} for device {device_id}: {e}")

    async def _trigger_alert(self, device_id: str, rule: MonitoringRule, metrics: DeviceHealthMetrics):
        """Trigger an alert for a device."""
        alert_key = f"{device_id}:{rule.name}"

        # Check cooldown
        if alert_key in self.alert_cooldowns:
            cooldown_expires = self.alert_cooldowns[alert_key] + timedelta(minutes=rule.cooldown_minutes)
            if datetime.utcnow() < cooldown_expires:
                return

        # Check rate limit
        current_hour = datetime.utcnow().strftime("%Y-%m-%d-%H")
        device_alerts = self.alert_counts.setdefault(device_id, {})
        hour_count = device_alerts.setdefault(current_hour, 0)

        if hour_count >= self.config.max_alerts_per_device_per_hour:
            logger.warning(f"Alert rate limit exceeded for device {device_id}")
            return

        # Create alert
        alert_data = {
            'device_id': device_id,
            'rule_name': rule.name,
            'severity': rule.severity.value,
            'description': rule.description,
            'timestamp': datetime.utcnow().isoformat(),
            'metrics': {
                'status': metrics.status.value,
                'health_score': metrics.health_score,
                'battery_level': metrics.battery_level,
                'signal_strength': metrics.signal_strength,
                'temperature': metrics.temperature,
                'last_seen': metrics.last_seen.isoformat() if metrics.last_seen else None
            }
        }

        # Log alert
        logger.warning(f"Alert triggered: {rule.name} for device {device_id} - {rule.description}")

        # Execute custom action if defined
        if rule.action:
            try:
                await rule.action(device_id, metrics)
            except Exception as e:
                logger.error(f"Failed to execute alert action for {rule.name}: {e}")

        # Send alert to endpoints
        await self._send_alert(alert_data)

        # Update cooldown and rate limit
        self.alert_cooldowns[alert_key] = datetime.utcnow()
        device_alerts[current_hour] += 1

    async def _send_alert(self, alert_data: Dict[str, Any]):
        """Send alert to configured endpoints."""
        # For now, just log the alert
        # In a real implementation, this would send to webhook endpoints, email, Slack, etc.
        logger.info(f"Alert: {json.dumps(alert_data, indent=2)}")

        # TODO: Implement actual alert delivery mechanisms
        # - HTTP webhooks
        # - Email notifications
        # - Slack/Teams integration
        # - SMS alerts

    async def _cleanup_old_data(self):
        """Clean up old monitoring data."""
        try:
            # Clean up old alert cooldowns (older than 24 hours)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            expired_keys = [
                key for key, timestamp in self.alert_cooldowns.items()
                if timestamp < cutoff_time
            ]
            for key in expired_keys:
                del self.alert_cooldowns[key]

            # Clean up old alert counts (older than 2 hours)
            current_hour = datetime.utcnow().strftime("%Y-%m-%d-%H")
            for device_id in list(self.alert_counts.keys()):
                device_alerts = self.alert_counts[device_id]
                old_hours = [
                    hour for hour in device_alerts.keys()
                    if hour < current_hour
                ]
                for hour in old_hours:
                    del device_alerts[hour]

                if not device_alerts:
                    del self.alert_counts[device_id]

            logger.debug("Completed monitoring data cleanup")

        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")

    # Public API methods

    async def get_device_health(self, device_id: str) -> Optional[DeviceHealthMetrics]:
        """Get current health metrics for a device."""
        return self.device_metrics.get(device_id)

    async def get_all_device_health(self) -> Dict[str, DeviceHealthMetrics]:
        """Get health metrics for all monitored devices."""
        return self.device_metrics.copy()

    async def add_monitoring_rule(self, rule: MonitoringRule):
        """Add a custom monitoring rule."""
        self.monitoring_rules.append(rule)
        logger.info(f"Added monitoring rule: {rule.name}")

    async def remove_monitoring_rule(self, rule_name: str) -> bool:
        """Remove a monitoring rule by name."""
        for i, rule in enumerate(self.monitoring_rules):
            if rule.name == rule_name:
                del self.monitoring_rules[i]
                logger.info(f"Removed monitoring rule: {rule_name}")
                return True
        return False

    async def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring service statistics."""
        total_devices = len(self.device_metrics)
        healthy_devices = sum(1 for m in self.device_metrics.values() if m.is_healthy)
        online_devices = sum(1 for m in self.device_metrics.values() if m.status == DeviceStatus.ONLINE)

        return {
            'total_devices': total_devices,
            'healthy_devices': healthy_devices,
            'unhealthy_devices': total_devices - healthy_devices,
            'online_devices': online_devices,
            'offline_devices': sum(1 for m in self.device_metrics.values() if m.status == DeviceStatus.OFFLINE),
            'error_devices': sum(1 for m in self.device_metrics.values() if m.status == DeviceStatus.ERROR),
            'warning_devices': sum(1 for m in self.device_metrics.values() if m.status == DeviceStatus.WARNING),
            'maintenance_devices': sum(1 for m in self.device_metrics.values() if m.status == DeviceStatus.MAINTENANCE),
            'health_percentage': (healthy_devices / total_devices * 100) if total_devices > 0 else 100,
            'online_percentage': (online_devices / total_devices * 100) if total_devices > 0 else 0,
            'monitoring_rules': len(self.monitoring_rules),
            'active_rules': len([r for r in self.monitoring_rules if r.enabled]),
            'is_running': self.running
        }


# Global service instance
_monitoring_service: Optional[DeviceMonitoringService] = None


async def start_monitoring_service(config: MonitoringConfig) -> DeviceMonitoringService:
    """Start the global device monitoring service."""
    global _monitoring_service

    if _monitoring_service and _monitoring_service.running:
        logger.warning("Monitoring service already running")
        return _monitoring_service

    _monitoring_service = DeviceMonitoringService(config)
    await _monitoring_service.start()
    return _monitoring_service


async def stop_monitoring_service():
    """Stop the global device monitoring service."""
    global _monitoring_service

    if _monitoring_service:
        await _monitoring_service.stop()
        _monitoring_service = None


def get_monitoring_service() -> Optional[DeviceMonitoringService]:
    """Get the current monitoring service instance."""
    return _monitoring_service