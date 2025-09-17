"""
PostgreSQL database connection and management service.

Provides connection pooling, transaction management, and database utilities
for the IoT telemetry dashboard backend.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg
from asyncpg import Pool, Connection
from fastapi import HTTPException


logger = logging.getLogger(__name__)


class PostgreSQLService:
    """PostgreSQL database connection service with pooling."""

    def __init__(self, database_url: str, **pool_kwargs):
        """
        Initialize PostgreSQL service.

        Args:
            database_url: PostgreSQL connection URL
            **pool_kwargs: Additional arguments for connection pool
        """
        self.database_url = database_url
        self.pool_kwargs = {
            'min_size': 5,
            'max_size': 20,
            'command_timeout': 30.0,
            'server_settings': {
                'application_name': 'iot_telemetry_dashboard',
                'timezone': 'UTC'
            },
            **pool_kwargs
        }
        self._pool: Optional[Pool] = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize database connection pool."""
        async with self._lock:
            if self._pool is None:
                try:
                    self._pool = await asyncpg.create_pool(
                        self.database_url,
                        **self.pool_kwargs
                    )
                    logger.info("PostgreSQL connection pool initialized")

                    # Test connection
                    async with self._pool.acquire() as conn:
                        version = await conn.fetchval("SELECT version()")
                        logger.info(f"Connected to PostgreSQL: {version}")

                except Exception as e:
                    logger.error(f"Failed to initialize PostgreSQL pool: {e}")
                    raise

    async def close(self) -> None:
        """Close database connection pool."""
        async with self._lock:
            if self._pool:
                await self._pool.close()
                self._pool = None
                logger.info("PostgreSQL connection pool closed")

    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._pool is not None

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Connection, None]:
        """
        Get database connection from pool.

        Yields:
            Database connection

        Raises:
            HTTPException: If service not initialized or connection fails
        """
        if not self._pool:
            raise HTTPException(
                status_code=500,
                detail="Database service not initialized"
            )

        try:
            async with self._pool.acquire() as conn:
                yield conn
        except asyncpg.PostgresError as e:
            logger.error(f"Database connection error: {e}")
            raise HTTPException(
                status_code=500,
                detail="Database connection failed"
            )
        except Exception as e:
            logger.error(f"Unexpected database error: {e}")
            raise HTTPException(
                status_code=500,
                detail="Database error"
            )

    @asynccontextmanager
    async def get_transaction(self) -> AsyncGenerator[Connection, None]:
        """
        Get database connection with transaction.

        Yields:
            Database connection within transaction

        Raises:
            HTTPException: If service not initialized or transaction fails
        """
        async with self.get_connection() as conn:
            async with conn.transaction():
                yield conn

    async def execute_query(
        self,
        query: str,
        *args,
        timeout: Optional[float] = None
    ) -> Any:
        """
        Execute query and return result.

        Args:
            query: SQL query to execute
            *args: Query parameters
            timeout: Query timeout in seconds

        Returns:
            Query result

        Raises:
            HTTPException: If query execution fails
        """
        try:
            async with self.get_connection() as conn:
                return await conn.fetch(query, *args, timeout=timeout)
        except asyncpg.PostgresError as e:
            logger.error(f"Query execution failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Query execution failed: {str(e)}"
            )

    async def execute_query_one(
        self,
        query: str,
        *args,
        timeout: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Execute query and return single result.

        Args:
            query: SQL query to execute
            *args: Query parameters
            timeout: Query timeout in seconds

        Returns:
            Single query result or None

        Raises:
            HTTPException: If query execution fails
        """
        try:
            async with self.get_connection() as conn:
                row = await conn.fetchrow(query, *args, timeout=timeout)
                return dict(row) if row else None
        except asyncpg.PostgresError as e:
            logger.error(f"Query execution failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Query execution failed: {str(e)}"
            )

    async def execute_command(
        self,
        command: str,
        *args,
        timeout: Optional[float] = None
    ) -> str:
        """
        Execute command and return status.

        Args:
            command: SQL command to execute
            *args: Command parameters
            timeout: Command timeout in seconds

        Returns:
            Command execution status

        Raises:
            HTTPException: If command execution fails
        """
        try:
            async with self.get_connection() as conn:
                return await conn.execute(command, *args, timeout=timeout)
        except asyncpg.PostgresError as e:
            logger.error(f"Command execution failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Command execution failed: {str(e)}"
            )

    async def execute_in_transaction(
        self,
        queries: list[tuple[str, tuple]],
        timeout: Optional[float] = None
    ) -> list[Any]:
        """
        Execute multiple queries in a transaction.

        Args:
            queries: List of (query, args) tuples
            timeout: Transaction timeout in seconds

        Returns:
            List of query results

        Raises:
            HTTPException: If transaction fails
        """
        try:
            results = []
            async with self.get_transaction() as conn:
                for query, args in queries:
                    result = await conn.fetch(query, *args, timeout=timeout)
                    results.append(result)
            return results
        except asyncpg.PostgresError as e:
            logger.error(f"Transaction failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Transaction failed: {str(e)}"
            )

    async def check_table_exists(self, table_name: str) -> bool:
        """
        Check if table exists in database.

        Args:
            table_name: Name of table to check

        Returns:
            True if table exists, False otherwise
        """
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = $1
            )
        """
        result = await self.execute_query_one(query, table_name)
        return result['exists'] if result else False

    async def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get table information including columns and constraints.

        Args:
            table_name: Name of table to inspect

        Returns:
            Dictionary with table information
        """
        columns_query = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = $1
            ORDER BY ordinal_position
        """

        constraints_query = """
            SELECT
                constraint_name,
                constraint_type
            FROM information_schema.table_constraints
            WHERE table_schema = 'public'
            AND table_name = $1
        """

        columns = await self.execute_query(columns_query, table_name)
        constraints = await self.execute_query(constraints_query, table_name)

        return {
            'table_name': table_name,
            'columns': [dict(col) for col in columns],
            'constraints': [dict(const) for const in constraints]
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform database health check.

        Returns:
            Health check status and metrics
        """
        try:
            start_time = asyncio.get_event_loop().time()

            # Simple query to test connection
            await self.execute_query_one("SELECT 1 as health_check")

            response_time = asyncio.get_event_loop().time() - start_time

            # Get pool status
            pool_status = {
                'size': self._pool.get_size() if self._pool else 0,
                'idle_count': self._pool.get_idle_size() if self._pool else 0
            }

            return {
                'status': 'healthy',
                'response_time_ms': round(response_time * 1000, 2),
                'pool': pool_status,
                'timestamp': asyncio.get_event_loop().time()
            }

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': asyncio.get_event_loop().time()
            }


# Global service instance
postgresql_service: Optional[PostgreSQLService] = None


async def get_postgresql_service() -> PostgreSQLService:
    """
    Dependency function to get PostgreSQL service instance.

    Returns:
        PostgreSQL service instance

    Raises:
        HTTPException: If service not initialized
    """
    global postgresql_service

    if postgresql_service is None:
        raise HTTPException(
            status_code=500,
            detail="PostgreSQL service not initialized"
        )

    return postgresql_service


async def initialize_postgresql_service(database_url: str, **kwargs) -> PostgreSQLService:
    """
    Initialize global PostgreSQL service instance.

    Args:
        database_url: PostgreSQL connection URL
        **kwargs: Additional pool configuration

    Returns:
        Initialized PostgreSQL service
    """
    global postgresql_service

    postgresql_service = PostgreSQLService(database_url, **kwargs)
    await postgresql_service.initialize()

    return postgresql_service


async def close_postgresql_service() -> None:
    """Close global PostgreSQL service instance."""
    global postgresql_service

    if postgresql_service:
        await postgresql_service.close()
        postgresql_service = None