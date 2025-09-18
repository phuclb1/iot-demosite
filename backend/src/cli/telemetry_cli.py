#!/usr/bin/env python3
"""
Telemetry query CLI.

Command-line interface for querying, analyzing, and exporting telemetry data
from InfluxDB with support for various aggregations and time ranges.
"""

import asyncio
import sys
from typing import Optional, List, Dict, Any, Union
import click
import json
import csv
from datetime import datetime, timedelta
from tabulate import tabulate
import pandas as pd

from influxdb_client import InfluxDBClient
from influxdb_client.client.exceptions import InfluxDBError

from ..database import get_async_session
from ..models.Device import Device
from ..models.Area import Area
from ..models.Site import Site
from ..models.Organization import Organization
from sqlalchemy import select
from sqlalchemy.orm import selectinload


class TelemetryQueryClient:
    """InfluxDB client wrapper for telemetry queries."""

    def __init__(self, url: str, token: str, org: str, bucket: str):
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.query_api = self.client.query_api()
        self.org = org
        self.bucket = bucket

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    async def query_telemetry(self, query: str) -> List[Dict[str, Any]]:
        """Execute InfluxDB query and return results."""
        try:
            tables = self.query_api.query(query, org=self.org)
            results = []

            for table in tables:
                for record in table.records:
                    results.append({
                        'time': record.get_time(),
                        'field': record.get_field(),
                        'value': record.get_value(),
                        'device_id': record.values.get('device_id'),
                        'organization': record.values.get('organization'),
                        'site': record.values.get('site'),
                        'area': record.values.get('area'),
                        'measurement': record.get_measurement()
                    })

            return results
        except InfluxDBError as e:
            raise click.ClickException(f"InfluxDB query failed: {e}")


async def get_session():
    """Get async database session."""
    async for session in get_async_session():
        return session


def format_output(data: Any, format_type: str = 'table') -> str:
    """Format output data for display."""
    if format_type == 'json':
        return json.dumps(data, indent=2, default=str)
    elif format_type == 'csv':
        if isinstance(data, list) and data:
            import io
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            return output.getvalue()
    elif format_type == 'table' and isinstance(data, list) and data:
        if isinstance(data[0], dict):
            headers = data[0].keys()
            rows = [list(item.values()) for item in data]
            return tabulate(rows, headers=headers, tablefmt='grid')

    return str(data)


def handle_async(coro):
    """Handle async function calls in click commands."""
    try:
        return asyncio.run(coro)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def parse_time_range(time_str: str) -> str:
    """Parse human-readable time range to InfluxDB format."""
    time_mappings = {
        '1h': '-1h',
        '1hour': '-1h',
        '6h': '-6h',
        '12h': '-12h',
        '1d': '-1d',
        '1day': '-1d',
        '7d': '-7d',
        '1w': '-7d',
        '1week': '-7d',
        '30d': '-30d',
        '1m': '-30d',
        '1month': '-30d'
    }

    return time_mappings.get(time_str.lower(), time_str)


@click.group()
@click.option('--influxdb-url', default='http://localhost:8086', help='InfluxDB URL')
@click.option('--influxdb-token', required=True, help='InfluxDB token')
@click.option('--influxdb-org', default='iot-org', help='InfluxDB organization')
@click.option('--influxdb-bucket', default='telemetry', help='InfluxDB bucket')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json', 'csv']), default='table',
              help='Output format')
@click.pass_context
def cli(ctx, influxdb_url, influxdb_token, influxdb_org, influxdb_bucket, output_format):
    """IoT Dashboard Telemetry Query CLI."""
    ctx.ensure_object(dict)
    ctx.obj.update({
        'influxdb_url': influxdb_url,
        'influxdb_token': influxdb_token,
        'influxdb_org': influxdb_org,
        'influxdb_bucket': influxdb_bucket,
        'format': output_format
    })


@cli.command('query')
@click.argument('device_id')
@click.option('--field', multiple=True, help='Telemetry fields to query (can specify multiple)')
@click.option('--start', default='1h', help='Start time (e.g., 1h, 1d, 2023-01-01T00:00:00Z)')
@click.option('--end', help='End time (default: now)')
@click.option('--interval', help='Aggregation interval (e.g., 1m, 5m, 1h)')
@click.option('--aggregation', type=click.Choice(['mean', 'max', 'min', 'sum', 'count']),
              default='mean', help='Aggregation function')
@click.option('--limit', type=int, help='Limit number of results')
@click.pass_context
def query_telemetry(ctx, device_id, field, start, end, interval, aggregation, limit):
    """Query telemetry data for a specific device."""
    def _query():
        with TelemetryQueryClient(
            ctx.obj['influxdb_url'],
            ctx.obj['influxdb_token'],
            ctx.obj['influxdb_org'],
            ctx.obj['influxdb_bucket']
        ) as client:

            # Build query
            start_time = parse_time_range(start) if not start.startswith('-') and 'T' not in start else start

            query_parts = [
                f'from(bucket: "{ctx.obj["influxdb_bucket"]}")',
                f'|> range(start: {start_time}' + (f', stop: {end}' if end else '') + ')',
                f'|> filter(fn: (r) => r._measurement == "device_telemetry")',
                f'|> filter(fn: (r) => r.device_id == "{device_id}")'
            ]

            # Add field filters
            if field:
                field_filters = ' or '.join([f'r._field == "{f}_value"' for f in field])
                query_parts.append(f'|> filter(fn: (r) => {field_filters})')

            # Add aggregation if interval specified
            if interval:
                query_parts.extend([
                    f'|> aggregateWindow(every: {interval}, fn: {aggregation}, createEmpty: false)',
                    '|> yield(name: "aggregated")'
                ])

            # Add limit if specified
            if limit:
                query_parts.append(f'|> limit(n: {limit})')

            query = '\n  '.join(query_parts)

            return asyncio.run(client.query_telemetry(query))

    data = handle_async(asyncio.coroutine(_query)())

    if not data:
        click.echo("No telemetry data found for the specified criteria.")
        return

    # Format data for display
    formatted_data = []
    for record in data:
        formatted_data.append({
            'Time': record['time'].strftime('%Y-%m-%d %H:%M:%S'),
            'Field': record['field'].replace('_value', ''),
            'Value': record['value'],
            'Device': record['device_id']
        })

    click.echo(format_output(formatted_data, ctx.obj['format']))


@cli.command('latest')
@click.argument('device_id')
@click.option('--field', multiple=True, help='Specific fields to get (default: all)')
@click.pass_context
def get_latest(ctx, device_id, field):
    """Get latest telemetry readings for a device."""
    def _get_latest():
        with TelemetryQueryClient(
            ctx.obj['influxdb_url'],
            ctx.obj['influxdb_token'],
            ctx.obj['influxdb_org'],
            ctx.obj['influxdb_bucket']
        ) as client:

            query_parts = [
                f'from(bucket: "{ctx.obj["influxdb_bucket"]}")',
                '|> range(start: -1h)',
                f'|> filter(fn: (r) => r._measurement == "device_telemetry")',
                f'|> filter(fn: (r) => r.device_id == "{device_id}")'
            ]

            if field:
                field_filters = ' or '.join([f'r._field == "{f}_value"' for f in field])
                query_parts.append(f'|> filter(fn: (r) => {field_filters})')

            query_parts.append('|> last()')

            query = '\n  '.join(query_parts)

            return asyncio.run(client.query_telemetry(query))

    data = handle_async(asyncio.coroutine(_get_latest)())

    if not data:
        click.echo("No recent telemetry data found.")
        return

    # Group by field and show latest value for each
    latest_readings = {}
    for record in data:
        field_name = record['field'].replace('_value', '')
        latest_readings[field_name] = {
            'Value': record['value'],
            'Time': record['time'].strftime('%Y-%m-%d %H:%M:%S'),
            'Device': record['device_id']
        }

    # Convert to list for formatting
    formatted_data = []
    for field_name, reading in latest_readings.items():
        formatted_data.append({
            'Field': field_name,
            **reading
        })

    click.echo(format_output(formatted_data, ctx.obj['format']))


@cli.command('aggregate')
@click.option('--org-id', help='Filter by organization')
@click.option('--site-id', help='Filter by site')
@click.option('--area-id', help='Filter by area')
@click.option('--field', required=True, help='Field to aggregate')
@click.option('--start', default='1d', help='Start time')
@click.option('--end', help='End time')
@click.option('--interval', default='1h', help='Aggregation interval')
@click.option('--aggregation', type=click.Choice(['mean', 'max', 'min', 'sum', 'count']),
              multiple=True, default=['mean'], help='Aggregation functions')
@click.pass_context
def aggregate_telemetry(ctx, org_id, site_id, area_id, field, start, end, interval, aggregation):
    """Aggregate telemetry data across devices."""
    def _aggregate():
        with TelemetryQueryClient(
            ctx.obj['influxdb_url'],
            ctx.obj['influxdb_token'],
            ctx.obj['influxdb_org'],
            ctx.obj['influxdb_bucket']
        ) as client:

            start_time = parse_time_range(start) if not start.startswith('-') and 'T' not in start else start

            query_parts = [
                f'from(bucket: "{ctx.obj["influxdb_bucket"]}")',
                f'|> range(start: {start_time}' + (f', stop: {end}' if end else '') + ')',
                f'|> filter(fn: (r) => r._measurement == "device_telemetry")',
                f'|> filter(fn: (r) => r._field == "{field}_value")'
            ]

            # Add hierarchy filters
            if area_id:
                query_parts.append(f'|> filter(fn: (r) => r.area == "{area_id}")')
            elif site_id:
                query_parts.append(f'|> filter(fn: (r) => r.site == "{site_id}")')
            elif org_id:
                query_parts.append(f'|> filter(fn: (r) => r.organization == "{org_id}")')

            # Add aggregation
            for agg_func in aggregation:
                query_parts.extend([
                    f'|> aggregateWindow(every: {interval}, fn: {agg_func}, createEmpty: false)',
                    f'|> map(fn: (r) => ({{ r with aggregation: "{agg_func}" }}))'
                ])

            query = '\n  '.join(query_parts)

            return asyncio.run(client.query_telemetry(query))

    data = handle_async(asyncio.coroutine(_aggregate)())

    if not data:
        click.echo("No telemetry data found for aggregation.")
        return

    # Format aggregated data
    formatted_data = []
    for record in data:
        formatted_data.append({
            'Time': record['time'].strftime('%Y-%m-%d %H:%M:%S'),
            'Field': field,
            'Aggregation': record.get('aggregation', 'unknown'),
            'Value': record['value'],
            'Organization': record.get('organization', 'N/A'),
            'Site': record.get('site', 'N/A')
        })

    click.echo(format_output(formatted_data, ctx.obj['format']))


@cli.command('export')
@click.argument('device_id')
@click.option('--start', default='1d', help='Start time')
@click.option('--end', help='End time')
@click.option('--field', multiple=True, help='Fields to export')
@click.option('--format', 'export_format', type=click.Choice(['csv', 'json', 'parquet']),
              default='csv', help='Export format')
@click.option('--output', '-o', help='Output file (default: stdout)')
@click.pass_context
def export_telemetry(ctx, device_id, start, end, field, export_format, output):
    """Export telemetry data to file."""
    def _export():
        with TelemetryQueryClient(
            ctx.obj['influxdb_url'],
            ctx.obj['influxdb_token'],
            ctx.obj['influxdb_org'],
            ctx.obj['influxdb_bucket']
        ) as client:

            start_time = parse_time_range(start) if not start.startswith('-') and 'T' not in start else start

            query_parts = [
                f'from(bucket: "{ctx.obj["influxdb_bucket"]}")',
                f'|> range(start: {start_time}' + (f', stop: {end}' if end else '') + ')',
                f'|> filter(fn: (r) => r._measurement == "device_telemetry")',
                f'|> filter(fn: (r) => r.device_id == "{device_id}")'
            ]

            if field:
                field_filters = ' or '.join([f'r._field == "{f}_value"' for f in field])
                query_parts.append(f'|> filter(fn: (r) => {field_filters})')

            query_parts.append('|> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")')

            query = '\n  '.join(query_parts)

            return asyncio.run(client.query_telemetry(query))

    data = handle_async(asyncio.coroutine(_export)())

    if not data:
        click.echo("No telemetry data found for export.")
        return

    # Convert to DataFrame for easier manipulation
    df_data = []
    for record in data:
        df_data.append({
            'timestamp': record['time'],
            'device_id': record['device_id'],
            **{k: v for k, v in record.items() if k not in ['time', 'device_id', 'field', 'measurement']}
        })

    df = pd.DataFrame(df_data)

    if output:
        if export_format == 'csv':
            df.to_csv(output, index=False)
        elif export_format == 'json':
            df.to_json(output, orient='records', date_format='iso')
        elif export_format == 'parquet':
            df.to_parquet(output, index=False)

        click.echo(f"✓ Data exported to {output}")
    else:
        if export_format == 'csv':
            click.echo(df.to_csv(index=False))
        elif export_format == 'json':
            click.echo(df.to_json(orient='records', date_format='iso', indent=2))
        else:
            click.echo("Parquet format requires output file (-o)")


@cli.command('stats')
@click.argument('device_id')
@click.option('--field', required=True, help='Field to analyze')
@click.option('--start', default='1d', help='Start time')
@click.option('--end', help='End time')
@click.pass_context
def field_statistics(ctx, device_id, field, start, end):
    """Calculate statistics for a telemetry field."""
    def _stats():
        with TelemetryQueryClient(
            ctx.obj['influxdb_url'],
            ctx.obj['influxdb_token'],
            ctx.obj['influxdb_org'],
            ctx.obj['influxdb_bucket']
        ) as client:

            start_time = parse_time_range(start) if not start.startswith('-') and 'T' not in start else start

            # Query for basic statistics
            stats_queries = {
                'count': f'''
                    from(bucket: "{ctx.obj["influxdb_bucket"]}")
                    |> range(start: {start_time}{f', stop: {end}' if end else ''})
                    |> filter(fn: (r) => r._measurement == "device_telemetry")
                    |> filter(fn: (r) => r.device_id == "{device_id}")
                    |> filter(fn: (r) => r._field == "{field}_value")
                    |> count()
                ''',
                'mean': f'''
                    from(bucket: "{ctx.obj["influxdb_bucket"]}")
                    |> range(start: {start_time}{f', stop: {end}' if end else ''})
                    |> filter(fn: (r) => r._measurement == "device_telemetry")
                    |> filter(fn: (r) => r.device_id == "{device_id}")
                    |> filter(fn: (r) => r._field == "{field}_value")
                    |> mean()
                ''',
                'min': f'''
                    from(bucket: "{ctx.obj["influxdb_bucket"]}")
                    |> range(start: {start_time}{f', stop: {end}' if end else ''})
                    |> filter(fn: (r) => r._measurement == "device_telemetry")
                    |> filter(fn: (r) => r.device_id == "{device_id}")
                    |> filter(fn: (r) => r._field == "{field}_value")
                    |> min()
                ''',
                'max': f'''
                    from(bucket: "{ctx.obj["influxdb_bucket"]}")
                    |> range(start: {start_time}{f', stop: {end}' if end else ''})
                    |> filter(fn: (r) => r._measurement == "device_telemetry")
                    |> filter(fn: (r) => r.device_id == "{device_id}")
                    |> filter(fn: (r) => r._field == "{field}_value")
                    |> max()
                ''',
                'stddev': f'''
                    from(bucket: "{ctx.obj["influxdb_bucket"]}")
                    |> range(start: {start_time}{f', stop: {end}' if end else ''})
                    |> filter(fn: (r) => r._measurement == "device_telemetry")
                    |> filter(fn: (r) => r.device_id == "{device_id}")
                    |> filter(fn: (r) => r._field == "{field}_value")
                    |> stddev()
                '''
            }

            results = {}
            for stat_name, query in stats_queries.items():
                try:
                    data = asyncio.run(client.query_telemetry(query))
                    if data:
                        results[stat_name] = data[0]['value']
                except Exception as e:
                    results[stat_name] = f"Error: {e}"

            return results

    stats = handle_async(asyncio.coroutine(_stats)())

    # Format statistics
    stats_data = []
    for stat_name, value in stats.items():
        stats_data.append({
            'Statistic': stat_name.title(),
            'Value': f"{value:.2f}" if isinstance(value, (int, float)) else str(value)
        })

    click.echo(f"Statistics for {field} on device {device_id}:")
    click.echo(format_output(stats_data, 'table'))


@cli.command('devices')
@click.option('--org-id', help='Filter by organization')
@click.option('--site-id', help='Filter by site')
@click.option('--area-id', help='Filter by area')
@click.option('--with-telemetry', is_flag=True, help='Only show devices with recent telemetry')
@click.pass_context
def list_devices_with_telemetry(ctx, org_id, site_id, area_id, with_telemetry):
    """List devices with telemetry data availability."""
    async def _list_devices():
        session = await get_session()

        # Build query
        query = select(Device).options(
            selectinload(Device.area).selectinload(Area.site).selectinload(Site.organization)
        )

        if area_id:
            query = query.where(Device.area_id == area_id)
        elif site_id:
            query = query.join(Area).where(Area.site_id == site_id)
        elif org_id:
            query = query.join(Area).join(Site).where(Site.organization_id == org_id)

        result = await session.execute(query)
        devices = result.scalars().all()

        # Check telemetry availability for each device
        device_data = []

        with TelemetryQueryClient(
            ctx.obj['influxdb_url'],
            ctx.obj['influxdb_token'],
            ctx.obj['influxdb_org'],
            ctx.obj['influxdb_bucket']
        ) as client:

            for device in devices:
                telemetry_info = 'No data'

                if with_telemetry:
                    # Check for recent telemetry
                    query = f'''
                        from(bucket: "{ctx.obj["influxdb_bucket"]}")
                        |> range(start: -24h)
                        |> filter(fn: (r) => r._measurement == "device_telemetry")
                        |> filter(fn: (r) => r.device_id == "{device.id}")
                        |> last()
                        |> limit(n: 1)
                    '''

                    try:
                        data = await client.query_telemetry(query)
                        if data:
                            last_time = data[0]['time']
                            telemetry_info = f"Last: {last_time.strftime('%Y-%m-%d %H:%M:%S')}"
                        elif with_telemetry:
                            continue  # Skip devices without telemetry
                    except Exception:
                        if with_telemetry:
                            continue

                device_data.append({
                    'Device ID': device.id,
                    'Name': device.name,
                    'Model': device.model,
                    'Status': device.status.title(),
                    'Organization': device.area.site.organization.name,
                    'Site': device.area.site.name,
                    'Area': device.area.name,
                    'Telemetry': telemetry_info
                })

        return device_data

    data = handle_async(_list_devices())
    click.echo(format_output(data, ctx.obj['format']))


if __name__ == '__main__':
    cli()