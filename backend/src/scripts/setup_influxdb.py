"""
InfluxDB schema setup script for IoT Telemetry Dashboard.

Handles creation and configuration of InfluxDB databases, retention policies,
and continuous queries for telemetry data management.
"""

import asyncio
import logging
import os
from typing import Optional, List, Dict, Any
from datetime import timedelta

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.domain.organization import Organization
from influxdb_client.domain.bucket import Bucket
from influxdb_client.domain.retention_rule import RetentionRule


logger = logging.getLogger(__name__)


class InfluxDBSetup:
    """InfluxDB schema and configuration setup."""

    def __init__(
        self,
        url: str,
        token: str,
        org: str,
        default_bucket: str = "telemetry"
    ):
        """
        Initialize InfluxDB setup client.

        Args:
            url: InfluxDB server URL
            token: Authentication token
            org: Organization name
            default_bucket: Default bucket name for telemetry data
        """
        self.url = url
        self.token = token
        self.org_name = org
        self.default_bucket = default_bucket
        self.client: Optional[InfluxDBClient] = None

    def connect(self):
        """Establish connection to InfluxDB."""
        self.client = InfluxDBClient(
            url=self.url,
            token=self.token,
            org=self.org_name
        )
        logger.info(f"Connected to InfluxDB at {self.url}")

    def disconnect(self):
        """Close InfluxDB connection."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from InfluxDB")

    def health_check(self) -> bool:
        """
        Check InfluxDB health status.

        Returns:
            True if InfluxDB is healthy, False otherwise
        """
        try:
            health = self.client.health()
            if health.status == "pass":
                logger.info("InfluxDB health check passed")
                return True
            else:
                logger.error(f"InfluxDB health check failed: {health.message}")
                return False
        except Exception as e:
            logger.error(f"InfluxDB health check failed: {e}")
            return False

    def create_organization(self) -> Organization:
        """
        Create organization if it doesn't exist.

        Returns:
            Organization object
        """
        try:
            orgs_api = self.client.organizations_api()

            # Check if organization already exists
            existing_orgs = orgs_api.find_organizations(org=self.org_name)
            if existing_orgs:
                logger.info(f"Organization '{self.org_name}' already exists")
                return existing_orgs[0]

            # Create new organization
            org = Organization(name=self.org_name)
            created_org = orgs_api.create_organization(org)
            logger.info(f"Created organization: {self.org_name}")
            return created_org

        except Exception as e:
            logger.error(f"Failed to create organization: {e}")
            raise

    def create_bucket(
        self,
        bucket_name: str,
        retention_hours: Optional[int] = None,
        description: Optional[str] = None
    ) -> Bucket:
        """
        Create bucket with optional retention policy.

        Args:
            bucket_name: Name of the bucket to create
            retention_hours: Retention period in hours (None for infinite)
            description: Optional bucket description

        Returns:
            Bucket object
        """
        try:
            buckets_api = self.client.buckets_api()

            # Check if bucket already exists
            existing_buckets = buckets_api.find_buckets(name=bucket_name)
            if existing_buckets.buckets:
                logger.info(f"Bucket '{bucket_name}' already exists")
                return existing_buckets.buckets[0]

            # Get organization
            orgs_api = self.client.organizations_api()
            org = orgs_api.find_organizations(org=self.org_name)[0]

            # Create retention rules
            retention_rules = []
            if retention_hours:
                retention_rule = RetentionRule(
                    type="expire",
                    every_seconds=retention_hours * 3600
                )
                retention_rules.append(retention_rule)

            # Create bucket
            bucket = Bucket(
                name=bucket_name,
                org_id=org.id,
                description=description,
                retention_rules=retention_rules
            )

            created_bucket = buckets_api.create_bucket(bucket)
            logger.info(f"Created bucket: {bucket_name}")

            if retention_hours:
                logger.info(f"Set retention policy: {retention_hours} hours")

            return created_bucket

        except Exception as e:
            logger.error(f"Failed to create bucket '{bucket_name}': {e}")
            raise

    def setup_telemetry_buckets(self):
        """Create all required buckets for telemetry data."""

        # Raw telemetry data bucket (30 days retention)
        self.create_bucket(
            bucket_name="telemetry_raw",
            retention_hours=30 * 24,  # 30 days
            description="Raw telemetry data from IoT devices"
        )

        # Aggregated telemetry data bucket (1 year retention)
        self.create_bucket(
            bucket_name="telemetry_aggregated",
            retention_hours=365 * 24,  # 1 year
            description="Aggregated telemetry data (hourly/daily averages)"
        )

        # Device status snapshots bucket (90 days retention)
        self.create_bucket(
            bucket_name="device_status",
            retention_hours=90 * 24,  # 90 days
            description="Device status snapshots and uptime tracking"
        )

        # System metrics bucket (7 days retention)
        self.create_bucket(
            bucket_name="system_metrics",
            retention_hours=7 * 24,  # 7 days
            description="System performance and health metrics"
        )

    def setup_tasks(self):
        """Create InfluxDB tasks for data processing."""

        tasks_api = self.client.tasks_api()

        # Get organization
        orgs_api = self.client.organizations_api()
        org = orgs_api.find_organizations(org=self.org_name)[0]

        # Task for hourly aggregation
        hourly_aggregation_flux = '''
option task = {
    name: "telemetry_hourly_aggregation",
    every: 1h,
}

from(bucket: "telemetry_raw")
    |> range(start: -2h, stop: -1h)
    |> filter(fn: (r) => r._measurement == "telemetry_reading")
    |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
    |> set(key: "_measurement", value: "telemetry_hourly")
    |> to(bucket: "telemetry_aggregated")
'''

        # Task for daily aggregation
        daily_aggregation_flux = '''
option task = {
    name: "telemetry_daily_aggregation",
    every: 1d,
}

from(bucket: "telemetry_aggregated")
    |> range(start: -2d, stop: -1d)
    |> filter(fn: (r) => r._measurement == "telemetry_hourly")
    |> aggregateWindow(every: 1d, fn: mean, createEmpty: false)
    |> set(key: "_measurement", value: "telemetry_daily")
    |> to(bucket: "telemetry_aggregated")
'''

        # Task for device uptime calculation
        device_uptime_flux = '''
option task = {
    name: "device_uptime_calculation",
    every: 15m,
}

from(bucket: "device_status")
    |> range(start: -30m)
    |> filter(fn: (r) => r._measurement == "device_status_snapshot")
    |> filter(fn: (r) => r._field == "status")
    |> aggregateWindow(every: 15m, fn: last, createEmpty: false)
    |> map(fn: (r) => ({
        r with
        _field: "uptime_percentage",
        _value: if r._value == "online" then 100.0 else 0.0
    }))
    |> to(bucket: "telemetry_aggregated")
'''

        tasks_config = [
            ("telemetry_hourly_aggregation", hourly_aggregation_flux),
            ("telemetry_daily_aggregation", daily_aggregation_flux),
            ("device_uptime_calculation", device_uptime_flux)
        ]

        for task_name, flux_query in tasks_config:
            try:
                # Check if task already exists
                existing_tasks = tasks_api.find_tasks(name=task_name)
                if existing_tasks:
                    logger.info(f"Task '{task_name}' already exists")
                    continue

                # Create task
                task = tasks_api.create_task_every(
                    flux=flux_query,
                    name=task_name,
                    every="1h" if "hourly" in task_name else ("1d" if "daily" in task_name else "15m"),
                    organization=org
                )
                logger.info(f"Created task: {task_name}")

            except Exception as e:
                logger.error(f"Failed to create task '{task_name}': {e}")

    def verify_setup(self) -> Dict[str, Any]:
        """
        Verify InfluxDB setup and return status.

        Returns:
            Dictionary with setup verification results
        """
        status = {
            "healthy": False,
            "organization_exists": False,
            "buckets": {},
            "tasks": {},
            "errors": []
        }

        try:
            # Health check
            status["healthy"] = self.health_check()

            # Check organization
            orgs_api = self.client.organizations_api()
            existing_orgs = orgs_api.find_organizations(org=self.org_name)
            status["organization_exists"] = len(existing_orgs) > 0

            # Check buckets
            buckets_api = self.client.buckets_api()
            expected_buckets = [
                "telemetry_raw",
                "telemetry_aggregated",
                "device_status",
                "system_metrics"
            ]

            for bucket_name in expected_buckets:
                buckets = buckets_api.find_buckets(name=bucket_name)
                status["buckets"][bucket_name] = len(buckets.buckets) > 0

            # Check tasks
            tasks_api = self.client.tasks_api()
            expected_tasks = [
                "telemetry_hourly_aggregation",
                "telemetry_daily_aggregation",
                "device_uptime_calculation"
            ]

            for task_name in expected_tasks:
                tasks = tasks_api.find_tasks(name=task_name)
                status["tasks"][task_name] = len(tasks) > 0

        except Exception as e:
            status["errors"].append(str(e))

        return status

    def setup_complete_schema(self):
        """Run complete InfluxDB schema setup."""
        logger.info("Starting InfluxDB schema setup")

        try:
            # Health check
            if not self.health_check():
                raise Exception("InfluxDB is not healthy")

            # Create organization
            self.create_organization()

            # Create buckets
            self.setup_telemetry_buckets()

            # Create tasks
            self.setup_tasks()

            # Verify setup
            status = self.verify_setup()

            if all([
                status["healthy"],
                status["organization_exists"],
                all(status["buckets"].values()),
                all(status["tasks"].values())
            ]):
                logger.info("InfluxDB schema setup completed successfully")
            else:
                logger.warning(f"InfluxDB setup completed with warnings: {status}")

        except Exception as e:
            logger.error(f"InfluxDB schema setup failed: {e}")
            raise


async def main():
    """Command-line interface for InfluxDB setup."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="InfluxDB schema setup")
    parser.add_argument("--url", required=True, help="InfluxDB server URL")
    parser.add_argument("--token", required=True, help="InfluxDB authentication token")
    parser.add_argument("--org", required=True, help="Organization name")
    parser.add_argument("--bucket", default="telemetry", help="Default bucket name")

    subparsers = parser.add_subparsers(dest="command", help="Setup commands")

    # Setup command
    subparsers.add_parser("setup", help="Run complete schema setup")

    # Verify command
    subparsers.add_parser("verify", help="Verify current setup")

    # Health command
    subparsers.add_parser("health", help="Check InfluxDB health")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Initialize setup client
    setup = InfluxDBSetup(
        url=args.url,
        token=args.token,
        org=args.org,
        default_bucket=args.bucket
    )

    try:
        setup.connect()

        if args.command == "health":
            healthy = setup.health_check()
            sys.exit(0 if healthy else 1)

        elif args.command == "verify":
            status = setup.verify_setup()
            print(f"InfluxDB Setup Status:")
            print(f"  Healthy: {status['healthy']}")
            print(f"  Organization exists: {status['organization_exists']}")
            print(f"  Buckets: {status['buckets']}")
            print(f"  Tasks: {status['tasks']}")

            if status['errors']:
                print(f"  Errors: {status['errors']}")

        elif args.command == "setup":
            setup.setup_complete_schema()

    finally:
        setup.disconnect()


if __name__ == "__main__":
    asyncio.run(main())