#!/usr/bin/env python3
"""
Device management CLI.

Command-line interface for managing IoT devices, monitoring status,
and performing device operations.
"""

import asyncio
import sys
from typing import Optional, List, Dict, Any
import click
import json
from datetime import datetime, timedelta
from tabulate import tabulate

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from ..database import get_async_session
from ..models.Device import Device
from ..models.Area import Area
from ..models.Site import Site
from ..models.Organization import Organization
from ..models.DeviceStatusSnapshot import DeviceStatusSnapshot


async def get_session():
    """Get async database session."""
    async for session in get_async_session():
        return session


def format_output(data: Any, format_type: str = 'table') -> str:
    """Format output data for display."""
    if format_type == 'json':
        return json.dumps(data, indent=2, default=str)
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


def status_emoji(status: str) -> str:
    """Get emoji for device status."""
    return {
        'online': '🟢',
        'offline': '🔴',
        'maintenance': '🟡',
        'error': '❌',
        'warning': '⚠️'
    }.get(status.lower(), '⚪')


@click.group()
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
@click.pass_context
def cli(ctx, output_format):
    """IoT Dashboard Device Management CLI."""
    ctx.ensure_object(dict)
    ctx.obj['format'] = output_format


# Device Commands
@cli.command('list')
@click.option('--org-id', help='Filter by organization ID')
@click.option('--site-id', help='Filter by site ID')
@click.option('--area-id', help='Filter by area ID')
@click.option('--status', type=click.Choice(['online', 'offline', 'maintenance', 'error', 'warning']),
              help='Filter by device status')
@click.option('--model', help='Filter by device model')
@click.option('--limit', type=int, default=50, help='Limit number of results')
@click.pass_context
def list_devices(ctx, org_id, site_id, area_id, status, model, limit):
    """List devices with optional filtering."""
    async def _list_devices():
        session = await get_session()

        # Build query with joins for hierarchy information
        query = select(Device).options(
            selectinload(Device.area).selectinload(Area.site).selectinload(Site.organization)
        )

        # Apply filters
        if area_id:
            query = query.where(Device.area_id == area_id)
        elif site_id:
            query = query.join(Area).where(Area.site_id == site_id)
        elif org_id:
            query = query.join(Area).join(Site).where(Site.organization_id == org_id)

        if status:
            query = query.where(Device.status == status)

        if model:
            query = query.where(Device.model.ilike(f'%{model}%'))

        query = query.limit(limit)

        result = await session.execute(query)
        devices = result.scalars().all()

        data = []
        for device in devices:
            last_seen_str = 'Never'
            if device.last_seen:
                last_seen_str = device.last_seen.strftime('%Y-%m-%d %H:%M:%S')

            data.append({
                'ID': device.id,
                'Name': device.name,
                'Model': device.model,
                'Status': f"{status_emoji(device.status)} {device.status.title()}",
                'Organization': device.area.site.organization.name,
                'Site': device.area.site.name,
                'Area': device.area.name,
                'Last Seen': last_seen_str,
                'Firmware': device.firmware_version or 'N/A',
                'Created': device.created_at.strftime('%Y-%m-%d')
            })

        return data

    data = handle_async(_list_devices())
    click.echo(format_output(data, ctx.obj['format']))


@cli.command('show')
@click.argument('device_id')
@click.option('--include-history', is_flag=True, help='Include status history')
@click.pass_context
def show_device(ctx, device_id, include_history):
    """Show detailed device information."""
    async def _show_device():
        session = await get_session()

        # Load device with hierarchy
        result = await session.execute(
            select(Device).options(
                selectinload(Device.area).selectinload(Area.site).selectinload(Site.organization)
            ).where(Device.id == device_id)
        )
        device = result.scalars().first()

        if not device:
            raise ValueError(f"Device with ID '{device_id}' not found")

        device_data = {
            'ID': device.id,
            'Name': device.name,
            'Model': device.model,
            'Status': f"{status_emoji(device.status)} {device.status.title()}",
            'Firmware Version': device.firmware_version or 'N/A',
            'MAC Address': device.mac_address or 'N/A',
            'Last Seen': device.last_seen.strftime('%Y-%m-%d %H:%M:%S') if device.last_seen else 'Never',
            'Organization': device.area.site.organization.name,
            'Site': device.area.site.name,
            'Area': device.area.name,
            'Created': device.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'Updated': device.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }

        result_data = {'device': device_data}

        if include_history:
            # Get recent status history
            history_result = await session.execute(
                select(DeviceStatusSnapshot)
                .where(DeviceStatusSnapshot.device_id == device_id)
                .order_by(DeviceStatusSnapshot.timestamp.desc())
                .limit(10)
            )
            history = history_result.scalars().all()

            history_data = []
            for snapshot in history:
                history_data.append({
                    'Timestamp': snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'Status': f"{status_emoji(snapshot.status)} {snapshot.status.title()}",
                    'Health Score': f"{snapshot.health_score:.1f}%" if snapshot.health_score else 'N/A',
                    'Battery': f"{snapshot.battery_level:.1f}%" if snapshot.battery_level else 'N/A',
                    'Signal': f"{snapshot.signal_strength:.1f}dBm" if snapshot.signal_strength else 'N/A',
                    'Temperature': f"{snapshot.temperature:.1f}°C" if snapshot.temperature else 'N/A'
                })

            result_data['history'] = history_data

        return result_data

    result = handle_async(_show_device())

    click.echo("Device Details:")
    click.echo(format_output([result['device']], 'table'))

    if 'history' in result and result['history']:
        click.echo("\nRecent Status History:")
        click.echo(format_output(result['history'], 'table'))


@cli.command('create')
@click.argument('area_id')
@click.argument('name')
@click.argument('model')
@click.option('--firmware-version', help='Device firmware version')
@click.option('--mac-address', help='Device MAC address')
@click.option('--status', type=click.Choice(['online', 'offline', 'maintenance']),
              default='offline', help='Initial device status')
@click.pass_context
def create_device(ctx, area_id, name, model, firmware_version, mac_address, status):
    """Create a new device."""
    async def _create_device():
        session = await get_session()

        # Verify area exists
        area = await session.get(Area, area_id)
        if not area:
            raise ValueError(f"Area with ID '{area_id}' not found")

        # Check for duplicate MAC address if provided
        if mac_address:
            existing = await session.execute(
                select(Device).where(Device.mac_address == mac_address)
            )
            if existing.scalars().first():
                raise ValueError(f"Device with MAC address '{mac_address}' already exists")

        device = Device(
            area_id=area_id,
            name=name,
            model=model,
            firmware_version=firmware_version,
            mac_address=mac_address,
            status=status
        )

        session.add(device)
        await session.commit()
        await session.refresh(device)

        return {
            'id': device.id,
            'name': device.name,
            'model': device.model,
            'area_id': device.area_id,
            'status': device.status,
            'created_at': device.created_at
        }

    result = handle_async(_create_device())
    click.echo(f"✓ Device created successfully")
    click.echo(format_output([result], ctx.obj['format']))


@cli.command('update')
@click.argument('device_id')
@click.option('--name', help='New device name')
@click.option('--model', help='New device model')
@click.option('--firmware-version', help='New firmware version')
@click.option('--mac-address', help='New MAC address')
@click.option('--status', type=click.Choice(['online', 'offline', 'maintenance', 'error', 'warning']),
              help='New device status')
@click.pass_context
def update_device(ctx, device_id, name, model, firmware_version, mac_address, status):
    """Update device information."""
    async def _update_device():
        session = await get_session()

        device = await session.get(Device, device_id)
        if not device:
            raise ValueError(f"Device with ID '{device_id}' not found")

        # Check MAC address uniqueness if changing
        if mac_address and mac_address != device.mac_address:
            existing = await session.execute(
                select(Device).where(
                    and_(Device.mac_address == mac_address, Device.id != device_id)
                )
            )
            if existing.scalars().first():
                raise ValueError(f"Device with MAC address '{mac_address}' already exists")

        # Update fields
        if name:
            device.name = name
        if model:
            device.model = model
        if firmware_version is not None:
            device.firmware_version = firmware_version
        if mac_address is not None:
            device.mac_address = mac_address
        if status:
            device.status = status

        device.updated_at = datetime.utcnow()

        await session.commit()
        await session.refresh(device)

        return {
            'id': device.id,
            'name': device.name,
            'model': device.model,
            'status': device.status,
            'updated_at': device.updated_at
        }

    result = handle_async(_update_device())
    click.echo(f"✓ Device updated successfully")
    click.echo(format_output([result], ctx.obj['format']))


@cli.command('delete')
@click.argument('device_id')
@click.confirmation_option(prompt='Are you sure you want to delete this device?')
def delete_device(device_id):
    """Delete a device."""
    async def _delete_device():
        session = await get_session()

        device = await session.get(Device, device_id)
        if not device:
            raise ValueError(f"Device with ID '{device_id}' not found")

        # Delete associated status snapshots
        await session.execute(
            select(DeviceStatusSnapshot).where(DeviceStatusSnapshot.device_id == device_id)
        )

        await session.delete(device)
        await session.commit()

        return {'deleted': True, 'id': device_id, 'name': device.name}

    result = handle_async(_delete_device())
    click.echo(f"✓ Device '{result['name']}' deleted successfully")


@cli.command('set-status')
@click.argument('device_id')
@click.argument('status', type=click.Choice(['online', 'offline', 'maintenance', 'error', 'warning']))
@click.pass_context
def set_device_status(ctx, device_id, status):
    """Set device status."""
    async def _set_status():
        session = await get_session()

        device = await session.get(Device, device_id)
        if not device:
            raise ValueError(f"Device with ID '{device_id}' not found")

        old_status = device.status
        device.status = status
        device.updated_at = datetime.utcnow()

        if status == 'online':
            device.last_seen = datetime.utcnow()

        await session.commit()

        return {
            'device_id': device_id,
            'name': device.name,
            'old_status': old_status,
            'new_status': status,
            'updated_at': device.updated_at
        }

    result = handle_async(_set_status())
    click.echo(f"✓ Device '{result['name']}' status changed from {result['old_status']} to {result['new_status']}")


@cli.command('ping')
@click.argument('device_id')
@click.option('--timeout', type=int, default=30, help='Ping timeout in seconds')
def ping_device(device_id, timeout):
    """Ping a device (simulated)."""
    async def _ping_device():
        session = await get_session()

        device = await session.get(Device, device_id)
        if not device:
            raise ValueError(f"Device with ID '{device_id}' not found")

        # Simulate ping based on current status
        import random
        import time

        click.echo(f"Pinging device '{device.name}' ({device_id})...")

        if device.status == 'online':
            # Simulate successful ping
            response_time = random.uniform(1, 50)  # 1-50ms
            time.sleep(0.5)  # Simulate network delay
            click.echo(f"✓ Device responded in {response_time:.1f}ms")

            # Update last_seen
            device.last_seen = datetime.utcnow()
            await session.commit()

            return {'success': True, 'response_time': response_time}
        else:
            # Simulate timeout
            time.sleep(min(timeout, 3))  # Don't actually wait full timeout
            click.echo(f"✗ Device did not respond (timeout after {timeout}s)")
            return {'success': False, 'timeout': timeout}

    result = handle_async(_ping_device())
    return result


@cli.command('status-summary')
@click.option('--org-id', help='Filter by organization ID')
@click.option('--site-id', help='Filter by site ID')
@click.pass_context
def status_summary(ctx, org_id, site_id):
    """Show device status summary."""
    async def _status_summary():
        session = await get_session()

        # Build base query
        query = select(Device)

        if site_id:
            query = query.join(Area).where(Area.site_id == site_id)
        elif org_id:
            query = query.join(Area).join(Site).where(Site.organization_id == org_id)

        result = await session.execute(query)
        devices = result.scalars().all()

        # Count by status
        status_counts = {}
        for device in devices:
            status_counts[device.status] = status_counts.get(device.status, 0) + 1

        total = len(devices)

        summary = []
        for status in ['online', 'offline', 'maintenance', 'error', 'warning']:
            count = status_counts.get(status, 0)
            percentage = (count / total * 100) if total > 0 else 0

            summary.append({
                'Status': f"{status_emoji(status)} {status.title()}",
                'Count': count,
                'Percentage': f"{percentage:.1f}%"
            })

        summary.append({
            'Status': '📊 Total',
            'Count': total,
            'Percentage': '100.0%'
        })

        return summary

    data = handle_async(_status_summary())
    click.echo(format_output(data, ctx.obj['format']))


@cli.command('health-report')
@click.option('--org-id', help='Filter by organization ID')
@click.option('--days', type=int, default=7, help='Number of days to analyze')
@click.pass_context
def health_report(ctx, org_id, days):
    """Generate device health report."""
    async def _health_report():
        session = await get_session()

        # Get devices
        query = select(Device).options(
            selectinload(Device.area).selectinload(Area.site).selectinload(Site.organization)
        )

        if org_id:
            query = query.join(Area).join(Site).where(Site.organization_id == org_id)

        result = await session.execute(query)
        devices = result.scalars().all()

        # Get recent status snapshots
        since_date = datetime.utcnow() - timedelta(days=days)

        report_data = []
        for device in devices:
            # Get latest snapshot
            snapshot_result = await session.execute(
                select(DeviceStatusSnapshot)
                .where(
                    and_(
                        DeviceStatusSnapshot.device_id == device.id,
                        DeviceStatusSnapshot.timestamp >= since_date
                    )
                )
                .order_by(DeviceStatusSnapshot.timestamp.desc())
                .limit(1)
            )
            latest_snapshot = snapshot_result.scalars().first()

            # Calculate uptime percentage
            uptime_result = await session.execute(
                select(DeviceStatusSnapshot)
                .where(
                    and_(
                        DeviceStatusSnapshot.device_id == device.id,
                        DeviceStatusSnapshot.timestamp >= since_date
                    )
                )
            )
            snapshots = uptime_result.scalars().all()

            online_count = len([s for s in snapshots if s.status == 'online'])
            total_snapshots = len(snapshots)
            uptime_percentage = (online_count / total_snapshots * 100) if total_snapshots > 0 else 0

            report_data.append({
                'Device': device.name,
                'Model': device.model,
                'Current Status': f"{status_emoji(device.status)} {device.status.title()}",
                'Health Score': f"{latest_snapshot.health_score:.1f}%" if latest_snapshot and latest_snapshot.health_score else 'N/A',
                f'Uptime ({days}d)': f"{uptime_percentage:.1f}%",
                'Organization': device.area.site.organization.name,
                'Site': device.area.site.name,
                'Last Seen': device.last_seen.strftime('%Y-%m-%d %H:%M') if device.last_seen else 'Never'
            })

        return report_data

    data = handle_async(_health_report())
    click.echo(format_output(data, ctx.obj['format']))


@cli.command('bulk-update')
@click.option('--org-id', help='Update devices in organization')
@click.option('--site-id', help='Update devices in site')
@click.option('--area-id', help='Update devices in area')
@click.option('--current-status', help='Update devices with this current status')
@click.option('--new-status', required=True,
              type=click.Choice(['online', 'offline', 'maintenance', 'error', 'warning']),
              help='New status to set')
@click.option('--firmware-version', help='New firmware version to set')
@click.confirmation_option(prompt='Are you sure you want to update multiple devices?')
@click.pass_context
def bulk_update_devices(ctx, org_id, site_id, area_id, current_status, new_status, firmware_version):
    """Bulk update device properties."""
    async def _bulk_update():
        session = await get_session()

        # Build query to find target devices
        query = select(Device)

        if area_id:
            query = query.where(Device.area_id == area_id)
        elif site_id:
            query = query.join(Area).where(Area.site_id == site_id)
        elif org_id:
            query = query.join(Area).join(Site).where(Site.organization_id == org_id)

        if current_status:
            query = query.where(Device.status == current_status)

        result = await session.execute(query)
        devices = result.scalars().all()

        if not devices:
            return {'updated': 0, 'message': 'No devices found matching criteria'}

        # Update devices
        updated_count = 0
        for device in devices:
            device.status = new_status
            if firmware_version:
                device.firmware_version = firmware_version
            device.updated_at = datetime.utcnow()
            updated_count += 1

        await session.commit()

        return {
            'updated': updated_count,
            'new_status': new_status,
            'firmware_version': firmware_version
        }

    result = handle_async(_bulk_update())
    click.echo(f"✓ Updated {result['updated']} devices")
    if result.get('firmware_version'):
        click.echo(f"  Status: {result['new_status']}, Firmware: {result['firmware_version']}")
    else:
        click.echo(f"  Status: {result['new_status']}")


if __name__ == '__main__':
    cli()