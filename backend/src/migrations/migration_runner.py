"""
Database migration runner for IoT Telemetry Dashboard.

Handles applying and tracking PostgreSQL database migrations.
Supports forward migrations, rollbacks, and migration status tracking.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import re

import asyncpg
from datetime import datetime


logger = logging.getLogger(__name__)


class MigrationRunner:
    """Database migration runner."""

    def __init__(self, database_url: str):
        """
        Initialize migration runner.

        Args:
            database_url: PostgreSQL connection URL
        """
        self.database_url = database_url
        self.migrations_dir = Path(__file__).parent
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """Initialize database connection pool."""
        self.pool = await asyncpg.create_pool(self.database_url)
        await self._create_migrations_table()

    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()

    async def _create_migrations_table(self):
        """Create migrations tracking table if it doesn't exist."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id SERIAL PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL UNIQUE,
                    checksum VARCHAR(64) NOT NULL,
                    applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_schema_migrations_filename
                ON schema_migrations(filename);

                CREATE INDEX IF NOT EXISTS idx_schema_migrations_applied_at
                ON schema_migrations(applied_at);
            """)

    def _get_migration_files(self) -> List[Path]:
        """
        Get list of migration files sorted by filename.

        Returns:
            List of migration file paths
        """
        migration_files = []
        for file_path in self.migrations_dir.glob("*.sql"):
            # Only include files that match migration naming pattern: NNN_description.sql
            if re.match(r'^\d{3}_.*\.sql$', file_path.name):
                migration_files.append(file_path)

        # Sort by filename to ensure correct order
        migration_files.sort(key=lambda x: x.name)
        return migration_files

    def _calculate_checksum(self, file_path: Path) -> str:
        """
        Calculate checksum for migration file.

        Args:
            file_path: Path to migration file

        Returns:
            SHA-256 checksum of file contents
        """
        import hashlib

        with open(file_path, 'rb') as f:
            content = f.read()
            return hashlib.sha256(content).hexdigest()

    async def get_applied_migrations(self) -> List[Dict[str, Any]]:
        """
        Get list of applied migrations.

        Returns:
            List of applied migration records
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT filename, checksum, applied_at
                FROM schema_migrations
                ORDER BY filename
            """)

            return [dict(row) for row in rows]

    async def get_pending_migrations(self) -> List[str]:
        """
        Get list of pending migration filenames.

        Returns:
            List of pending migration filenames
        """
        applied_migrations = await self.get_applied_migrations()
        applied_filenames = {migration['filename'] for migration in applied_migrations}

        migration_files = self._get_migration_files()
        pending_migrations = []

        for file_path in migration_files:
            if file_path.name not in applied_filenames:
                pending_migrations.append(file_path.name)

        return pending_migrations

    async def validate_applied_migrations(self) -> List[str]:
        """
        Validate that applied migrations haven't been modified.

        Returns:
            List of migration filenames with checksum mismatches
        """
        applied_migrations = await self.get_applied_migrations()
        mismatched_migrations = []

        for migration in applied_migrations:
            file_path = self.migrations_dir / migration['filename']

            if not file_path.exists():
                mismatched_migrations.append(f"{migration['filename']} (file missing)")
                continue

            current_checksum = self._calculate_checksum(file_path)
            if current_checksum != migration['checksum']:
                mismatched_migrations.append(f"{migration['filename']} (checksum mismatch)")

        return mismatched_migrations

    async def apply_migration(self, filename: str) -> bool:
        """
        Apply a single migration.

        Args:
            filename: Migration filename to apply

        Returns:
            True if migration was applied successfully
        """
        file_path = self.migrations_dir / filename

        if not file_path.exists():
            raise ValueError(f"Migration file not found: {filename}")

        # Check if migration is already applied
        async with self.pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT filename FROM schema_migrations WHERE filename = $1",
                filename
            )

            if existing:
                logger.warning(f"Migration {filename} is already applied")
                return False

        # Read migration content
        with open(file_path, 'r') as f:
            migration_sql = f.read()

        # Calculate checksum
        checksum = self._calculate_checksum(file_path)

        # Apply migration in transaction
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                try:
                    # Execute migration SQL
                    await conn.execute(migration_sql)

                    # Record migration as applied
                    await conn.execute("""
                        INSERT INTO schema_migrations (filename, checksum)
                        VALUES ($1, $2)
                    """, filename, checksum)

                    logger.info(f"Applied migration: {filename}")
                    return True

                except Exception as e:
                    logger.error(f"Failed to apply migration {filename}: {e}")
                    raise

    async def apply_all_pending_migrations(self) -> int:
        """
        Apply all pending migrations.

        Returns:
            Number of migrations applied
        """
        pending_migrations = await self.get_pending_migrations()

        if not pending_migrations:
            logger.info("No pending migrations to apply")
            return 0

        logger.info(f"Applying {len(pending_migrations)} pending migrations")

        applied_count = 0
        for filename in pending_migrations:
            try:
                if await self.apply_migration(filename):
                    applied_count += 1
            except Exception as e:
                logger.error(f"Migration {filename} failed: {e}")
                raise

        logger.info(f"Successfully applied {applied_count} migrations")
        return applied_count

    async def rollback_migration(self, filename: str) -> bool:
        """
        Rollback a migration (remove from tracking table).

        Note: This doesn't execute rollback SQL, it just removes the migration
        from the tracking table. Manual rollback SQL execution is required.

        Args:
            filename: Migration filename to rollback

        Returns:
            True if migration was rolled back successfully
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM schema_migrations WHERE filename = $1",
                filename
            )

            if result == "DELETE 1":
                logger.info(f"Rolled back migration: {filename}")
                return True
            else:
                logger.warning(f"Migration {filename} was not found in tracking table")
                return False

    async def get_migration_status(self) -> Dict[str, Any]:
        """
        Get overall migration status.

        Returns:
            Dictionary with migration status information
        """
        applied_migrations = await self.get_applied_migrations()
        pending_migrations = await self.get_pending_migrations()
        mismatched_migrations = await self.validate_applied_migrations()

        return {
            "applied_count": len(applied_migrations),
            "pending_count": len(pending_migrations),
            "applied_migrations": [m['filename'] for m in applied_migrations],
            "pending_migrations": pending_migrations,
            "mismatched_migrations": mismatched_migrations,
            "last_applied": applied_migrations[-1]['applied_at'] if applied_migrations else None
        }

    async def reset_database(self, confirm: bool = False) -> bool:
        """
        Reset database by dropping all tables and reapplying migrations.

        Args:
            confirm: Must be True to actually perform reset

        Returns:
            True if reset was successful
        """
        if not confirm:
            raise ValueError("Database reset requires explicit confirmation")

        logger.warning("Resetting database - this will drop all tables!")

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Drop all tables
                await conn.execute("""
                    DROP SCHEMA public CASCADE;
                    CREATE SCHEMA public;
                    GRANT ALL ON SCHEMA public TO PUBLIC;
                """)

                logger.info("Dropped all tables")

        # Recreate migrations table and apply all migrations
        await self._create_migrations_table()
        applied_count = await self.apply_all_pending_migrations()

        logger.info(f"Database reset complete. Applied {applied_count} migrations.")
        return True


async def main():
    """Command-line interface for migration runner."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Database migration runner")
    parser.add_argument("--database-url", required=True, help="PostgreSQL connection URL")

    subparsers = parser.add_subparsers(dest="command", help="Migration commands")

    # Status command
    subparsers.add_parser("status", help="Show migration status")

    # Apply command
    apply_parser = subparsers.add_parser("apply", help="Apply migrations")
    apply_parser.add_argument("--migration", help="Specific migration to apply")

    # Rollback command
    rollback_parser = subparsers.add_parser("rollback", help="Rollback migration")
    rollback_parser.add_argument("migration", help="Migration to rollback")

    # Reset command
    reset_parser = subparsers.add_parser("reset", help="Reset database")
    reset_parser.add_argument("--confirm", action="store_true", help="Confirm database reset")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Initialize migration runner
    runner = MigrationRunner(args.database_url)

    try:
        await runner.initialize()

        if args.command == "status":
            status = await runner.get_migration_status()
            print(f"Applied migrations: {status['applied_count']}")
            print(f"Pending migrations: {status['pending_count']}")

            if status['mismatched_migrations']:
                print(f"Mismatched migrations: {status['mismatched_migrations']}")

            if status['pending_migrations']:
                print(f"Pending: {', '.join(status['pending_migrations'])}")

        elif args.command == "apply":
            if args.migration:
                await runner.apply_migration(args.migration)
            else:
                await runner.apply_all_pending_migrations()

        elif args.command == "rollback":
            await runner.rollback_migration(args.migration)

        elif args.command == "reset":
            await runner.reset_database(confirm=args.confirm)

    finally:
        await runner.close()


if __name__ == "__main__":
    asyncio.run(main())