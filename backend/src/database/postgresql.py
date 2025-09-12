"""PostgreSQL database connection and management using asyncpg."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg
from asyncpg import Connection, Pool

from src.config import settings

logger = logging.getLogger(__name__)


class PostgreSQLManager:
    """PostgreSQL connection manager using asyncpg."""

    def __init__(self):
        self._pool: Optional[Pool] = None

    async def create_pool(self) -> Pool:
        """Create and return a connection pool."""
        if self._pool is None:
            try:
                self._pool = await asyncpg.create_pool(
                    host=settings.postgres_host,
                    port=settings.postgres_port,
                    user=settings.postgres_user,
                    password=settings.postgres_password,
                    database=settings.postgres_db,
                    min_size=5,
                    max_size=20,
                    command_timeout=30,
                    server_settings={
                        "jit": "off",  # Disable JIT for better performance on small queries
                        "application_name": "iot-backend",
                    },
                )
                logger.info(
                    f"PostgreSQL connection pool created: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
                )
            except Exception as e:
                logger.error(f"Failed to create PostgreSQL connection pool: {e}")
                raise
        return self._pool

    async def close_pool(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("PostgreSQL connection pool closed")

    @property
    def pool(self) -> Optional[Pool]:
        """Get the connection pool."""
        return self._pool

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Connection, None]:
        """Get a database connection from the pool."""
        if not self._pool:
            raise RuntimeError("Connection pool not initialized. Call create_pool() first.")
        
        async with self._pool.acquire() as connection:
            try:
                yield connection
            except Exception as e:
                logger.error(f"Database operation failed: {e}")
                raise

    async def execute_query(self, query: str, *args) -> list:
        """Execute a SELECT query and return results."""
        async with self.get_connection() as conn:
            try:
                result = await conn.fetch(query, *args)
                return [dict(record) for record in result]
            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                raise

    async def execute_command(self, command: str, *args) -> str:
        """Execute an INSERT/UPDATE/DELETE command."""
        async with self.get_connection() as conn:
            try:
                result = await conn.execute(command, *args)
                logger.debug(f"Command executed: {result}")
                return result
            except Exception as e:
                logger.error(f"Command execution failed: {e}")
                raise

    async def execute_transaction(self, commands: list[tuple[str, tuple]]) -> None:
        """Execute multiple commands in a transaction."""
        async with self.get_connection() as conn:
            async with conn.transaction():
                try:
                    for command, args in commands:
                        await conn.execute(command, *args)
                    logger.debug(f"Transaction completed with {len(commands)} commands")
                except Exception as e:
                    logger.error(f"Transaction failed: {e}")
                    raise

    async def health_check(self) -> bool:
        """Check if the database connection is healthy."""
        try:
            async with self.get_connection() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global PostgreSQL manager instance
postgresql_manager = PostgreSQLManager()


async def init_postgresql() -> None:
    """Initialize PostgreSQL connection pool."""
    await postgresql_manager.create_pool()


async def close_postgresql() -> None:
    """Close PostgreSQL connection pool."""
    await postgresql_manager.close_pool()


async def get_postgresql_connection() -> AsyncGenerator[Connection, None]:
    """Get a PostgreSQL connection."""
    async with postgresql_manager.get_connection() as conn:
        yield conn