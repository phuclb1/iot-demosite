#!/usr/bin/env python3
"""
Organization management CLI.

Command-line interface for managing organizations, sites, areas, and user permissions
in the IoT telemetry dashboard system.
"""

import asyncio
import sys
from typing import Optional, List, Dict, Any
import click
import json
from datetime import datetime
from tabulate import tabulate

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from ..database import get_async_session
from ..models.Organization import Organization
from ..models.Site import Site
from ..models.Area import Area
from ..models.Device import Device
from ..models.User import User


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


@click.group()
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
@click.pass_context
def cli(ctx, output_format):
    """IoT Dashboard Organization Management CLI."""
    ctx.ensure_object(dict)
    ctx.obj['format'] = output_format


# Organization Commands
@cli.group()
def org():
    """Organization management commands."""
    pass


@org.command('list')
@click.option('--active-only', is_flag=True, help='Show only active organizations')
@click.pass_context
def list_organizations(ctx, active_only):
    """List all organizations."""
    async def _list_orgs():
        session = await get_session()
        query = select(Organization)

        if active_only:
            query = query.where(Organization.is_active == True)

        result = await session.execute(query)
        organizations = result.scalars().all()

        data = [{
            'ID': org.id,
            'Name': org.name,
            'Slug': org.slug,
            'Active': '✓' if org.is_active else '✗',
            'Created': org.created_at.strftime('%Y-%m-%d'),
            'Sites': await count_sites(session, org.id),
            'Users': await count_users(session, org.id)
        } for org in organizations]

        return data

    async def count_sites(session, org_id):
        result = await session.execute(select(Site).where(Site.organization_id == org_id))
        return len(result.scalars().all())

    async def count_users(session, org_id):
        result = await session.execute(select(User).where(User.organization_permissions.contains([org_id])))
        return len(result.scalars().all())

    data = handle_async(_list_orgs())
    click.echo(format_output(data, ctx.obj['format']))


@org.command('create')
@click.argument('name')
@click.option('--slug', help='Organization slug (auto-generated if not provided)')
@click.option('--description', help='Organization description')
@click.option('--contact-email', help='Contact email')
@click.option('--contact-phone', help='Contact phone')
@click.pass_context
def create_organization(ctx, name, slug, description, contact_email, contact_phone):
    """Create a new organization."""
    async def _create_org():
        session = await get_session()

        # Generate slug if not provided
        if not slug:
            import re
            generated_slug = re.sub(r'[^a-zA-Z0-9-]', '-', name.lower()).strip('-')
            generated_slug = re.sub(r'-+', '-', generated_slug)
        else:
            generated_slug = slug

        # Check if slug already exists
        existing = await session.execute(
            select(Organization).where(Organization.slug == generated_slug)
        )
        if existing.scalars().first():
            raise ValueError(f"Organization with slug '{generated_slug}' already exists")

        # Create organization
        org = Organization(
            name=name,
            slug=generated_slug,
            description=description,
            contact_email=contact_email,
            contact_phone=contact_phone,
            is_active=True
        )

        session.add(org)
        await session.commit()
        await session.refresh(org)

        return {
            'id': org.id,
            'name': org.name,
            'slug': org.slug,
            'created_at': org.created_at
        }

    result = handle_async(_create_org())
    click.echo(f"✓ Organization created successfully")
    click.echo(format_output([result], ctx.obj['format']))


@org.command('update')
@click.argument('org_id')
@click.option('--name', help='New organization name')
@click.option('--description', help='New description')
@click.option('--contact-email', help='New contact email')
@click.option('--contact-phone', help='New contact phone')
@click.option('--active/--inactive', default=None, help='Set active status')
@click.pass_context
def update_organization(ctx, org_id, name, description, contact_email, contact_phone, active):
    """Update an organization."""
    async def _update_org():
        session = await get_session()

        org = await session.get(Organization, org_id)
        if not org:
            raise ValueError(f"Organization with ID '{org_id}' not found")

        # Update fields
        if name:
            org.name = name
        if description is not None:
            org.description = description
        if contact_email is not None:
            org.contact_email = contact_email
        if contact_phone is not None:
            org.contact_phone = contact_phone
        if active is not None:
            org.is_active = active

        org.updated_at = datetime.utcnow()

        await session.commit()
        await session.refresh(org)

        return {
            'id': org.id,
            'name': org.name,
            'slug': org.slug,
            'is_active': org.is_active,
            'updated_at': org.updated_at
        }

    result = handle_async(_update_org())
    click.echo(f"✓ Organization updated successfully")
    click.echo(format_output([result], ctx.obj['format']))


@org.command('delete')
@click.argument('org_id')
@click.option('--force', is_flag=True, help='Force delete even if organization has sites')
@click.confirmation_option(prompt='Are you sure you want to delete this organization?')
def delete_organization(org_id, force):
    """Delete an organization."""
    async def _delete_org():
        session = await get_session()

        org = await session.get(Organization, org_id)
        if not org:
            raise ValueError(f"Organization with ID '{org_id}' not found")

        # Check for existing sites
        sites_result = await session.execute(
            select(Site).where(Site.organization_id == org_id)
        )
        sites = sites_result.scalars().all()

        if sites and not force:
            raise ValueError(f"Organization has {len(sites)} sites. Use --force to delete anyway.")

        # Delete cascade (sites, areas, devices)
        if force and sites:
            for site in sites:
                # Delete areas and devices
                areas_result = await session.execute(
                    select(Area).where(Area.site_id == site.id)
                )
                areas = areas_result.scalars().all()

                for area in areas:
                    # Delete devices
                    devices_result = await session.execute(
                        select(Device).where(Device.area_id == area.id)
                    )
                    devices = devices_result.scalars().all()

                    for device in devices:
                        await session.delete(device)

                    await session.delete(area)

                await session.delete(site)

        await session.delete(org)
        await session.commit()

        return {'deleted': True, 'id': org_id}

    result = handle_async(_delete_org())
    click.echo(f"✓ Organization deleted successfully")


@org.command('show')
@click.argument('org_id')
@click.option('--include-sites', is_flag=True, help='Include sites information')
@click.pass_context
def show_organization(ctx, org_id, include_sites):
    """Show detailed organization information."""
    async def _show_org():
        session = await get_session()

        # Load organization with optional sites
        query = select(Organization).where(Organization.id == org_id)
        if include_sites:
            query = query.options(selectinload(Organization.sites))

        result = await session.execute(query)
        org = result.scalars().first()

        if not org:
            raise ValueError(f"Organization with ID '{org_id}' not found")

        org_data = {
            'ID': org.id,
            'Name': org.name,
            'Slug': org.slug,
            'Description': org.description or 'N/A',
            'Contact Email': org.contact_email or 'N/A',
            'Contact Phone': org.contact_phone or 'N/A',
            'Active': '✓' if org.is_active else '✗',
            'Created': org.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'Updated': org.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }

        # Add site information if requested
        if include_sites:
            sites_data = []
            for site in org.sites:
                areas_count = await session.execute(
                    select(Area).where(Area.site_id == site.id)
                )
                areas = areas_count.scalars().all()

                devices_count = 0
                for area in areas:
                    devices_result = await session.execute(
                        select(Device).where(Device.area_id == area.id)
                    )
                    devices_count += len(devices_result.scalars().all())

                sites_data.append({
                    'ID': site.id,
                    'Name': site.name,
                    'Location': site.location or 'N/A',
                    'Areas': len(areas),
                    'Devices': devices_count
                })

            return {'organization': org_data, 'sites': sites_data}

        return org_data

    result = handle_async(_show_org())

    if isinstance(result, dict) and 'sites' in result:
        click.echo("Organization Details:")
        click.echo(format_output([result['organization']], 'table'))
        click.echo("\nSites:")
        click.echo(format_output(result['sites'], 'table'))
    else:
        click.echo(format_output([result], ctx.obj['format']))


# Site Commands
@cli.group()
def site():
    """Site management commands."""
    pass


@site.command('list')
@click.option('--org-id', help='Filter by organization ID')
@click.pass_context
def list_sites(ctx, org_id):
    """List sites."""
    async def _list_sites():
        session = await get_session()

        query = select(Site).options(selectinload(Site.organization))
        if org_id:
            query = query.where(Site.organization_id == org_id)

        result = await session.execute(query)
        sites = result.scalars().all()

        data = []
        for site in sites:
            areas_result = await session.execute(
                select(Area).where(Area.site_id == site.id)
            )
            areas_count = len(areas_result.scalars().all())

            data.append({
                'ID': site.id,
                'Name': site.name,
                'Organization': site.organization.name,
                'Location': site.location or 'N/A',
                'Timezone': site.timezone,
                'Areas': areas_count,
                'Created': site.created_at.strftime('%Y-%m-%d')
            })

        return data

    data = handle_async(_list_sites())
    click.echo(format_output(data, ctx.obj['format']))


@site.command('create')
@click.argument('org_id')
@click.argument('name')
@click.option('--location', help='Site location')
@click.option('--timezone', default='UTC', help='Site timezone')
@click.pass_context
def create_site(ctx, org_id, name, location, timezone):
    """Create a new site."""
    async def _create_site():
        session = await get_session()

        # Verify organization exists
        org = await session.get(Organization, org_id)
        if not org:
            raise ValueError(f"Organization with ID '{org_id}' not found")

        # Generate slug
        import re
        slug = re.sub(r'[^a-zA-Z0-9-]', '-', name.lower()).strip('-')
        slug = re.sub(r'-+', '-', slug)

        # Check for duplicate slug within organization
        existing = await session.execute(
            select(Site).where(
                and_(Site.organization_id == org_id, Site.slug == slug)
            )
        )
        if existing.scalars().first():
            raise ValueError(f"Site with slug '{slug}' already exists in this organization")

        site = Site(
            organization_id=org_id,
            name=name,
            slug=slug,
            location=location,
            timezone=timezone
        )

        session.add(site)
        await session.commit()
        await session.refresh(site)

        return {
            'id': site.id,
            'name': site.name,
            'slug': site.slug,
            'organization_id': site.organization_id,
            'created_at': site.created_at
        }

    result = handle_async(_create_site())
    click.echo(f"✓ Site created successfully")
    click.echo(format_output([result], ctx.obj['format']))


# Area Commands
@cli.group()
def area():
    """Area management commands."""
    pass


@area.command('list')
@click.option('--site-id', help='Filter by site ID')
@click.pass_context
def list_areas(ctx, site_id):
    """List areas."""
    async def _list_areas():
        session = await get_session()

        query = select(Area).options(selectinload(Area.site))
        if site_id:
            query = query.where(Area.site_id == site_id)

        result = await session.execute(query)
        areas = result.scalars().all()

        data = []
        for area in areas:
            devices_result = await session.execute(
                select(Device).where(Device.area_id == area.id)
            )
            devices = devices_result.scalars().all()
            online_devices = len([d for d in devices if d.status == 'online'])

            data.append({
                'ID': area.id,
                'Name': area.name,
                'Site': area.site.name,
                'Description': area.description or 'N/A',
                'Devices': len(devices),
                'Online': online_devices,
                'Created': area.created_at.strftime('%Y-%m-%d')
            })

        return data

    data = handle_async(_list_areas())
    click.echo(format_output(data, ctx.obj['format']))


@area.command('create')
@click.argument('site_id')
@click.argument('name')
@click.option('--description', help='Area description')
@click.pass_context
def create_area(ctx, site_id, name, description):
    """Create a new area."""
    async def _create_area():
        session = await get_session()

        # Verify site exists
        site = await session.get(Site, site_id)
        if not site:
            raise ValueError(f"Site with ID '{site_id}' not found")

        # Generate slug
        import re
        slug = re.sub(r'[^a-zA-Z0-9-]', '-', name.lower()).strip('-')
        slug = re.sub(r'-+', '-', slug)

        # Check for duplicate slug within site
        existing = await session.execute(
            select(Area).where(
                and_(Area.site_id == site_id, Area.slug == slug)
            )
        )
        if existing.scalars().first():
            raise ValueError(f"Area with slug '{slug}' already exists in this site")

        area = Area(
            site_id=site_id,
            name=name,
            slug=slug,
            description=description
        )

        session.add(area)
        await session.commit()
        await session.refresh(area)

        return {
            'id': area.id,
            'name': area.name,
            'slug': area.slug,
            'site_id': area.site_id,
            'created_at': area.created_at
        }

    result = handle_async(_create_area())
    click.echo(f"✓ Area created successfully")
    click.echo(format_output([result], ctx.obj['format']))


# User Management Commands
@cli.group()
def user():
    """User management commands."""
    pass


@user.command('list')
@click.option('--org-id', help='Filter by organization access')
@click.pass_context
def list_users(ctx, org_id):
    """List users."""
    async def _list_users():
        session = await get_session()

        query = select(User)
        if org_id:
            query = query.where(User.organization_permissions.contains([org_id]))

        result = await session.execute(query)
        users = result.scalars().all()

        data = [{
            'ID': user.id,
            'Name': user.name,
            'Email': user.email,
            'Role': user.role.title(),
            'Organizations': len(user.organization_permissions),
            'Created': user.created_at.strftime('%Y-%m-%d')
        } for user in users]

        return data

    data = handle_async(_list_users())
    click.echo(format_output(data, ctx.obj['format']))


@user.command('grant-access')
@click.argument('user_id')
@click.argument('org_id')
@click.pass_context
def grant_org_access(ctx, user_id, org_id):
    """Grant user access to an organization."""
    async def _grant_access():
        session = await get_session()

        user = await session.get(User, user_id)
        if not user:
            raise ValueError(f"User with ID '{user_id}' not found")

        org = await session.get(Organization, org_id)
        if not org:
            raise ValueError(f"Organization with ID '{org_id}' not found")

        if org_id not in user.organization_permissions:
            user.organization_permissions.append(org_id)
            await session.commit()
            return {'granted': True, 'user': user.name, 'organization': org.name}
        else:
            return {'granted': False, 'message': 'User already has access to this organization'}

    result = handle_async(_grant_access())
    if result['granted']:
        click.echo(f"✓ Access granted to {result['user']} for {result['organization']}")
    else:
        click.echo(f"ℹ {result['message']}")


@user.command('revoke-access')
@click.argument('user_id')
@click.argument('org_id')
@click.pass_context
def revoke_org_access(ctx, user_id, org_id):
    """Revoke user access from an organization."""
    async def _revoke_access():
        session = await get_session()

        user = await session.get(User, user_id)
        if not user:
            raise ValueError(f"User with ID '{user_id}' not found")

        org = await session.get(Organization, org_id)
        if not org:
            raise ValueError(f"Organization with ID '{org_id}' not found")

        if org_id in user.organization_permissions:
            user.organization_permissions.remove(org_id)
            await session.commit()
            return {'revoked': True, 'user': user.name, 'organization': org.name}
        else:
            return {'revoked': False, 'message': 'User does not have access to this organization'}

    result = handle_async(_revoke_access())
    if result['revoked']:
        click.echo(f"✓ Access revoked from {result['user']} for {result['organization']}")
    else:
        click.echo(f"ℹ {result['message']}")


# Statistics Commands
@cli.command('stats')
@click.option('--org-id', help='Statistics for specific organization')
@click.pass_context
def show_stats(ctx, org_id):
    """Show system statistics."""
    async def _get_stats():
        session = await get_session()

        if org_id:
            # Organization-specific stats
            org = await session.get(Organization, org_id)
            if not org:
                raise ValueError(f"Organization with ID '{org_id}' not found")

            sites_result = await session.execute(
                select(Site).where(Site.organization_id == org_id)
            )
            sites = sites_result.scalars().all()

            areas_count = 0
            devices_count = 0
            online_devices = 0

            for site in sites:
                areas_result = await session.execute(
                    select(Area).where(Area.site_id == site.id)
                )
                site_areas = areas_result.scalars().all()
                areas_count += len(site_areas)

                for area in site_areas:
                    devices_result = await session.execute(
                        select(Device).where(Device.area_id == area.id)
                    )
                    area_devices = devices_result.scalars().all()
                    devices_count += len(area_devices)
                    online_devices += len([d for d in area_devices if d.status == 'online'])

            return [{
                'Metric': 'Organization',
                'Value': org.name
            }, {
                'Metric': 'Sites',
                'Value': len(sites)
            }, {
                'Metric': 'Areas',
                'Value': areas_count
            }, {
                'Metric': 'Total Devices',
                'Value': devices_count
            }, {
                'Metric': 'Online Devices',
                'Value': online_devices
            }, {
                'Metric': 'Offline Devices',
                'Value': devices_count - online_devices
            }]
        else:
            # System-wide stats
            orgs_result = await session.execute(select(Organization))
            orgs = orgs_result.scalars().all()

            sites_result = await session.execute(select(Site))
            sites = sites_result.scalars().all()

            areas_result = await session.execute(select(Area))
            areas = areas_result.scalars().all()

            devices_result = await session.execute(select(Device))
            devices = devices_result.scalars().all()

            users_result = await session.execute(select(User))
            users = users_result.scalars().all()

            online_devices = len([d for d in devices if d.status == 'online'])

            return [{
                'Metric': 'Organizations',
                'Value': len(orgs)
            }, {
                'Metric': 'Sites',
                'Value': len(sites)
            }, {
                'Metric': 'Areas',
                'Value': len(areas)
            }, {
                'Metric': 'Total Devices',
                'Value': len(devices)
            }, {
                'Metric': 'Online Devices',
                'Value': online_devices
            }, {
                'Metric': 'Offline Devices',
                'Value': len(devices) - online_devices
            }, {
                'Metric': 'Users',
                'Value': len(users)
            }]

    data = handle_async(_get_stats())
    click.echo(format_output(data, ctx.obj['format']))


if __name__ == '__main__':
    cli()