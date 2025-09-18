#!/usr/bin/env python3
"""
MQTT Testing CLI

A comprehensive command-line interface for testing MQTT functionality,
including publishing test messages, monitoring telemetry streams, and
validating device connectivity.
"""

import asyncio
import json
import random
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
import uuid

import click
import asyncio_mqtt as aiomqtt
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, TaskID
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.spinner import Spinner

from ..services.mqtt_message_parser import (
    MQTTMessageParser,
    TelemetryMessage,
    StatusMessage,
    HeartbeatMessage,
    AlertMessage,
    MessageType,
    TelemetryReading,
    DeviceStatus
)
from ..config import get_settings

console = Console()
settings = get_settings()

@dataclass
class TestMessage:
    """Test message configuration"""
    message_type: str
    device_id: str
    interval: float
    count: int
    payload: Dict[str, Any]

@dataclass
class ConnectionStats:
    """MQTT connection statistics"""
    connected: bool = False
    messages_sent: int = 0
    messages_received: int = 0
    errors: int = 0
    start_time: Optional[datetime] = None
    last_message_time: Optional[datetime] = None

class MQTTTestClient:
    """MQTT test client for publishing and subscribing"""

    def __init__(self, broker_host: str, broker_port: int, username: Optional[str] = None, password: Optional[str] = None):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.client: Optional[aiomqtt.Client] = None
        self.stats = ConnectionStats()
        self.message_parser = MQTTMessageParser()
        self.received_messages: List[Dict[str, Any]] = []

    async def connect(self) -> bool:
        """Connect to MQTT broker"""
        try:
            self.client = aiomqtt.Client(
                hostname=self.broker_host,
                port=self.broker_port,
                username=self.username,
                password=self.password,
                identifier=f"mqtt_test_cli_{uuid.uuid4().hex[:8]}"
            )
            await self.client.__aenter__()
            self.stats.connected = True
            self.stats.start_time = datetime.now()
            console.print(f"[green]✓[/green] Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
            return True
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to connect to MQTT broker: {e}")
            self.stats.errors += 1
            return False

    async def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client:
            try:
                await self.client.__aexit__(None, None, None)
                self.stats.connected = False
                console.print("[yellow]Disconnected from MQTT broker[/yellow]")
            except Exception as e:
                console.print(f"[red]Error disconnecting: {e}[/red]")

    async def publish_message(self, topic: str, payload: Union[str, Dict[str, Any]], qos: int = 0) -> bool:
        """Publish a message to MQTT topic"""
        if not self.client or not self.stats.connected:
            console.print("[red]Not connected to MQTT broker[/red]")
            return False

        try:
            if isinstance(payload, dict):
                payload_str = json.dumps(payload)
            else:
                payload_str = str(payload)

            await self.client.publish(topic, payload_str, qos=qos)
            self.stats.messages_sent += 1
            self.stats.last_message_time = datetime.now()
            return True
        except Exception as e:
            console.print(f"[red]Failed to publish message: {e}[/red]")
            self.stats.errors += 1
            return False

    async def subscribe_and_monitor(self, topics: List[str], duration: Optional[int] = None):
        """Subscribe to topics and monitor messages"""
        if not self.client or not self.stats.connected:
            console.print("[red]Not connected to MQTT broker[/red]")
            return

        try:
            # Subscribe to all topics
            for topic in topics:
                await self.client.subscribe(topic)
                console.print(f"[blue]Subscribed to topic: {topic}[/blue]")

            start_time = time.time()

            async for message in self.client.messages:
                try:
                    # Parse the message
                    payload = json.loads(message.payload.decode())

                    # Validate with message parser
                    parsed_message = self.message_parser.parse_message(payload)

                    # Store the received message
                    message_data = {
                        "topic": message.topic.value,
                        "timestamp": datetime.now().isoformat(),
                        "payload": payload,
                        "parsed": parsed_message is not None,
                        "message_type": parsed_message.message_type.value if parsed_message else "unknown"
                    }
                    self.received_messages.append(message_data)
                    self.stats.messages_received += 1

                    # Display the message
                    self._display_received_message(message_data)

                except json.JSONDecodeError:
                    console.print(f"[red]Invalid JSON in message from {message.topic.value}[/red]")
                    self.stats.errors += 1
                except Exception as e:
                    console.print(f"[red]Error processing message: {e}[/red]")
                    self.stats.errors += 1

                # Check duration limit
                if duration and (time.time() - start_time) >= duration:
                    break

        except Exception as e:
            console.print(f"[red]Error during monitoring: {e}[/red]")
            self.stats.errors += 1

    def _display_received_message(self, message_data: Dict[str, Any]):
        """Display a received message in a formatted way"""
        timestamp = message_data["timestamp"]
        topic = message_data["topic"]
        message_type = message_data["message_type"]
        parsed = "✓" if message_data["parsed"] else "✗"

        console.print(f"[cyan]{timestamp}[/cyan] [{topic}] {message_type} {parsed}")

        # Show payload details for parsed messages
        if message_data["parsed"] and message_data["payload"]:
            payload = message_data["payload"]
            if "device_id" in payload:
                console.print(f"  Device: {payload['device_id']}")
            if "readings" in payload:
                readings = payload["readings"]
                if isinstance(readings, list) and readings:
                    for reading in readings[:3]:  # Show first 3 readings
                        if isinstance(reading, dict):
                            field = reading.get("field", "unknown")
                            value = reading.get("value", "N/A")
                            unit = reading.get("unit", "")
                            console.print(f"    {field}: {value} {unit}")
            elif "status" in payload:
                console.print(f"  Status: {payload['status']}")

class MQTTTestGenerator:
    """Generate test messages for MQTT testing"""

    @staticmethod
    def generate_telemetry_message(device_id: str, reading_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate a realistic telemetry message"""
        if not reading_types:
            reading_types = ["temperature", "humidity", "pressure", "battery_level"]

        readings = []
        for reading_type in reading_types:
            reading = MQTTTestGenerator._generate_reading(reading_type)
            readings.append(reading)

        return {
            "message_type": "telemetry",
            "device_id": device_id,
            "timestamp": datetime.now().isoformat(),
            "readings": readings
        }

    @staticmethod
    def generate_status_message(device_id: str, status: Optional[str] = None) -> Dict[str, Any]:
        """Generate a device status message"""
        if not status:
            status = random.choice(["online", "offline", "maintenance", "error"])

        message = {
            "message_type": "status",
            "device_id": device_id,
            "timestamp": datetime.now().isoformat(),
            "status": status
        }

        # Add optional fields for online devices
        if status == "online":
            message.update({
                "battery_level": random.randint(10, 100),
                "signal_strength": random.randint(-100, -30),
                "firmware_version": f"v{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}"
            })

        return message

    @staticmethod
    def generate_heartbeat_message(device_id: str) -> Dict[str, Any]:
        """Generate a heartbeat message"""
        return {
            "message_type": "heartbeat",
            "device_id": device_id,
            "timestamp": datetime.now().isoformat(),
            "uptime": random.randint(3600, 86400 * 30),  # 1 hour to 30 days
            "memory_usage": random.randint(30, 80),
            "cpu_usage": random.randint(5, 95)
        }

    @staticmethod
    def generate_alert_message(device_id: str, alert_type: Optional[str] = None) -> Dict[str, Any]:
        """Generate an alert message"""
        if not alert_type:
            alert_type = random.choice(["temperature_high", "battery_low", "connection_lost", "sensor_error"])

        severity_map = {
            "temperature_high": "warning",
            "battery_low": "warning",
            "connection_lost": "error",
            "sensor_error": "critical"
        }

        return {
            "message_type": "alert",
            "device_id": device_id,
            "timestamp": datetime.now().isoformat(),
            "alert_type": alert_type,
            "severity": severity_map.get(alert_type, "info"),
            "description": f"Alert: {alert_type.replace('_', ' ').title()}",
            "acknowledgment_required": alert_type in ["connection_lost", "sensor_error"]
        }

    @staticmethod
    def _generate_reading(reading_type: str) -> Dict[str, Any]:
        """Generate a single sensor reading"""
        reading_configs = {
            "temperature": {"min": -20, "max": 50, "unit": "°C", "decimals": 1},
            "humidity": {"min": 0, "max": 100, "unit": "%", "decimals": 1},
            "pressure": {"min": 900, "max": 1100, "unit": "hPa", "decimals": 2},
            "battery_level": {"min": 0, "max": 100, "unit": "%", "decimals": 0},
            "voltage": {"min": 3.0, "max": 5.0, "unit": "V", "decimals": 2},
            "current": {"min": 0.1, "max": 2.0, "unit": "A", "decimals": 3},
            "power": {"min": 0.5, "max": 10.0, "unit": "W", "decimals": 2},
            "light": {"min": 0, "max": 1000, "unit": "lux", "decimals": 0},
            "sound": {"min": 30, "max": 120, "unit": "dB", "decimals": 1},
            "co2": {"min": 350, "max": 5000, "unit": "ppm", "decimals": 0}
        }

        config = reading_configs.get(reading_type, {"min": 0, "max": 100, "unit": "", "decimals": 2})

        value = random.uniform(config["min"], config["max"])
        value = round(value, config["decimals"])

        return {
            "field": reading_type,
            "value": value,
            "unit": config["unit"],
            "timestamp": datetime.now().isoformat(),
            "quality": random.choice(["good", "good", "good", "fair", "poor"])  # Bias toward "good"
        }

# CLI Commands
@click.group()
@click.option('--broker-host', default='localhost', help='MQTT broker hostname')
@click.option('--broker-port', default=1883, help='MQTT broker port')
@click.option('--username', help='MQTT username')
@click.option('--password', help='MQTT password')
@click.pass_context
def cli(ctx, broker_host, broker_port, username, password):
    """MQTT Testing CLI - Test MQTT connectivity and message flow"""
    ctx.ensure_object(dict)
    ctx.obj['client'] = MQTTTestClient(broker_host, broker_port, username, password)

@cli.command('test-connection')
@click.pass_context
async def test_connection(ctx):
    """Test MQTT broker connection"""
    client: MQTTTestClient = ctx.obj['client']

    console.print("[blue]Testing MQTT connection...[/blue]")

    connected = await client.connect()
    if connected:
        console.print("[green]✓ Connection test successful[/green]")
        await client.disconnect()
    else:
        console.print("[red]✗ Connection test failed[/red]")
        raise click.Abort()

@cli.command('publish')
@click.option('--topic', required=True, help='MQTT topic to publish to')
@click.option('--message-type', type=click.Choice(['telemetry', 'status', 'heartbeat', 'alert']),
              default='telemetry', help='Type of message to generate')
@click.option('--device-id', required=True, help='Device ID for the message')
@click.option('--count', default=1, help='Number of messages to send')
@click.option('--interval', default=1.0, help='Interval between messages (seconds)')
@click.option('--qos', default=0, type=click.IntRange(0, 2), help='MQTT QoS level')
@click.option('--reading-types', help='Comma-separated list of reading types for telemetry')
@click.option('--status', help='Device status for status messages')
@click.option('--alert-type', help='Alert type for alert messages')
@click.pass_context
async def publish(ctx, topic, message_type, device_id, count, interval, qos, reading_types, status, alert_type):
    """Publish test messages to MQTT topic"""
    client: MQTTTestClient = ctx.obj['client']

    if not await client.connect():
        raise click.Abort()

    try:
        reading_types_list = reading_types.split(',') if reading_types else None

        with Progress() as progress:
            task = progress.add_task(f"Publishing {count} messages...", total=count)

            for i in range(count):
                # Generate message based on type
                if message_type == 'telemetry':
                    payload = MQTTTestGenerator.generate_telemetry_message(device_id, reading_types_list)
                elif message_type == 'status':
                    payload = MQTTTestGenerator.generate_status_message(device_id, status)
                elif message_type == 'heartbeat':
                    payload = MQTTTestGenerator.generate_heartbeat_message(device_id)
                elif message_type == 'alert':
                    payload = MQTTTestGenerator.generate_alert_message(device_id, alert_type)

                # Publish the message
                success = await client.publish_message(topic, payload, qos)

                if success:
                    console.print(f"[green]✓[/green] Published {message_type} message {i+1}/{count}")
                else:
                    console.print(f"[red]✗[/red] Failed to publish message {i+1}/{count}")

                progress.update(task, advance=1)

                # Wait for interval (except on last message)
                if i < count - 1:
                    await asyncio.sleep(interval)

        # Display statistics
        stats_table = Table(title="Publishing Statistics")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="green")

        stats_table.add_row("Messages Sent", str(client.stats.messages_sent))
        stats_table.add_row("Errors", str(client.stats.errors))
        stats_table.add_row("Success Rate", f"{(client.stats.messages_sent / count) * 100:.1f}%")

        console.print(stats_table)

    finally:
        await client.disconnect()

@cli.command('monitor')
@click.option('--topics', required=True, help='Comma-separated list of MQTT topics to monitor')
@click.option('--duration', type=int, help='Monitoring duration in seconds (unlimited if not specified)')
@click.option('--save-to-file', help='Save received messages to JSON file')
@click.pass_context
async def monitor(ctx, topics, duration, save_to_file):
    """Monitor MQTT topics for incoming messages"""
    client: MQTTTestClient = ctx.obj['client']

    if not await client.connect():
        raise click.Abort()

    try:
        topics_list = [topic.strip() for topic in topics.split(',')]

        console.print(f"[blue]Monitoring topics: {', '.join(topics_list)}[/blue]")
        if duration:
            console.print(f"[blue]Duration: {duration} seconds[/blue]")
        else:
            console.print("[blue]Duration: unlimited (Ctrl+C to stop)[/blue]")

        console.print("[yellow]Press Ctrl+C to stop monitoring[/yellow]")
        console.print()

        # Start monitoring
        await client.subscribe_and_monitor(topics_list, duration)

        # Display final statistics
        stats_table = Table(title="Monitoring Statistics")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="green")

        stats_table.add_row("Messages Received", str(client.stats.messages_received))
        stats_table.add_row("Errors", str(client.stats.errors))
        if client.stats.start_time:
            duration_actual = (datetime.now() - client.stats.start_time).total_seconds()
            stats_table.add_row("Duration", f"{duration_actual:.1f} seconds")
            if client.stats.messages_received > 0:
                rate = client.stats.messages_received / duration_actual
                stats_table.add_row("Message Rate", f"{rate:.2f} msg/sec")

        console.print(stats_table)

        # Save to file if requested
        if save_to_file and client.received_messages:
            with open(save_to_file, 'w') as f:
                json.dump(client.received_messages, f, indent=2)
            console.print(f"[green]✓ Saved {len(client.received_messages)} messages to {save_to_file}[/green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped by user[/yellow]")
    finally:
        await client.disconnect()

@cli.command('stress-test')
@click.option('--topic', required=True, help='MQTT topic for stress testing')
@click.option('--device-count', default=10, help='Number of simulated devices')
@click.option('--message-rate', default=1.0, help='Messages per second per device')
@click.option('--duration', default=60, help='Test duration in seconds')
@click.option('--message-type', type=click.Choice(['telemetry', 'mixed']),
              default='telemetry', help='Type of messages to send')
@click.pass_context
async def stress_test(ctx, topic, device_count, message_rate, duration, message_type):
    """Run MQTT stress test with multiple simulated devices"""
    client: MQTTTestClient = ctx.obj['client']

    if not await client.connect():
        raise click.Abort()

    try:
        console.print(f"[blue]Starting stress test...[/blue]")
        console.print(f"Devices: {device_count}")
        console.print(f"Message rate: {message_rate} msg/sec per device")
        console.print(f"Duration: {duration} seconds")
        console.print(f"Total expected messages: {device_count * message_rate * duration:.0f}")
        console.print()

        # Generate device IDs
        device_ids = [f"test_device_{i:03d}" for i in range(device_count)]

        # Calculate message interval per device
        interval = 1.0 / message_rate

        start_time = time.time()

        # Create tasks for each device
        async def device_task(device_id: str):
            messages_sent = 0
            last_message_time = time.time()

            while (time.time() - start_time) < duration:
                # Generate appropriate message
                if message_type == 'telemetry':
                    payload = MQTTTestGenerator.generate_telemetry_message(device_id)
                else:  # mixed
                    msg_types = ['telemetry', 'status', 'heartbeat']
                    selected_type = random.choice(msg_types)
                    if selected_type == 'telemetry':
                        payload = MQTTTestGenerator.generate_telemetry_message(device_id)
                    elif selected_type == 'status':
                        payload = MQTTTestGenerator.generate_status_message(device_id)
                    else:  # heartbeat
                        payload = MQTTTestGenerator.generate_heartbeat_message(device_id)

                # Publish message
                await client.publish_message(topic, payload)
                messages_sent += 1

                # Wait for next message time
                next_message_time = last_message_time + interval
                sleep_time = max(0, next_message_time - time.time())
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                last_message_time = time.time()

            return messages_sent

        # Run all device tasks concurrently
        with Progress() as progress:
            task = progress.add_task("Running stress test...", total=duration)

            # Start all device tasks
            device_tasks = [device_task(device_id) for device_id in device_ids]

            # Monitor progress
            while (time.time() - start_time) < duration:
                elapsed = time.time() - start_time
                progress.update(task, completed=elapsed)
                await asyncio.sleep(0.1)

            # Wait for all tasks to complete
            results = await asyncio.gather(*device_tasks)

        # Calculate and display results
        total_messages = sum(results)
        actual_duration = time.time() - start_time
        actual_rate = total_messages / actual_duration
        expected_rate = device_count * message_rate

        results_table = Table(title="Stress Test Results")
        results_table.add_column("Metric", style="cyan")
        results_table.add_column("Value", style="green")

        results_table.add_row("Duration", f"{actual_duration:.1f} seconds")
        results_table.add_row("Total Messages Sent", str(total_messages))
        results_table.add_row("Actual Message Rate", f"{actual_rate:.2f} msg/sec")
        results_table.add_row("Expected Message Rate", f"{expected_rate:.2f} msg/sec")
        results_table.add_row("Rate Efficiency", f"{(actual_rate / expected_rate) * 100:.1f}%")
        results_table.add_row("Messages per Device", f"{total_messages / device_count:.1f}")
        results_table.add_row("Errors", str(client.stats.errors))

        console.print(results_table)

    finally:
        await client.disconnect()

@cli.command('validate')
@click.option('--file', 'file_path', required=True, help='JSON file containing MQTT messages to validate')
@click.pass_context
def validate(ctx, file_path):
    """Validate MQTT messages from a JSON file"""

    try:
        with open(file_path, 'r') as f:
            messages = json.load(f)

        if not isinstance(messages, list):
            messages = [messages]

        parser = MQTTMessageParser()
        valid_count = 0
        invalid_count = 0

        results_table = Table(title="Message Validation Results")
        results_table.add_column("Index", style="cyan")
        results_table.add_column("Type", style="blue")
        results_table.add_column("Device ID", style="green")
        results_table.add_column("Status", style="bold")
        results_table.add_column("Issues", style="red")

        for i, message in enumerate(messages):
            try:
                parsed = parser.parse_message(message)
                if parsed:
                    valid_count += 1
                    results_table.add_row(
                        str(i + 1),
                        parsed.message_type.value,
                        parsed.device_id,
                        "[green]✓ Valid[/green]",
                        ""
                    )
                else:
                    invalid_count += 1
                    results_table.add_row(
                        str(i + 1),
                        message.get("message_type", "unknown"),
                        message.get("device_id", "unknown"),
                        "[red]✗ Invalid[/red]",
                        "Failed to parse"
                    )
            except Exception as e:
                invalid_count += 1
                results_table.add_row(
                    str(i + 1),
                    message.get("message_type", "unknown"),
                    message.get("device_id", "unknown"),
                    "[red]✗ Invalid[/red]",
                    str(e)
                )

        console.print(results_table)

        # Summary
        summary_table = Table(title="Validation Summary")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Count", style="green")
        summary_table.add_column("Percentage", style="blue")

        total = valid_count + invalid_count
        summary_table.add_row("Total Messages", str(total), "100.0%")
        summary_table.add_row("Valid Messages", str(valid_count), f"{(valid_count/total)*100:.1f}%")
        summary_table.add_row("Invalid Messages", str(invalid_count), f"{(invalid_count/total)*100:.1f}%")

        console.print(summary_table)

    except FileNotFoundError:
        console.print(f"[red]Error: File '{file_path}' not found[/red]")
        raise click.Abort()
    except json.JSONDecodeError as e:
        console.print(f"[red]Error: Invalid JSON in file: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()

# Helper function to run async commands
def run_async(coro):
    """Helper to run async commands"""
    return asyncio.run(coro)

# Attach async runner to commands that need it
test_connection.callback = lambda ctx: run_async(test_connection.callback(ctx))
publish.callback = lambda ctx, **kwargs: run_async(publish.callback(ctx, **kwargs))
monitor.callback = lambda ctx, **kwargs: run_async(monitor.callback(ctx, **kwargs))
stress_test.callback = lambda ctx, **kwargs: run_async(stress_test.callback(ctx, **kwargs))

if __name__ == '__main__':
    cli()