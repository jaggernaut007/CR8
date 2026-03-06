"""Async PostgreSQL connection pool management using asyncpg."""

import logging
from pathlib import Path

import asyncpg

logger = logging.getLogger(__name__)


async def init_pool(database_url: str) -> asyncpg.Pool:
    """Create and return an asyncpg connection pool.

    Args:
        database_url: PostgreSQL connection string.

    Returns:
        Initialized asyncpg connection pool.
    """
    logger.info("Initializing database connection pool")
    pool = await asyncpg.create_pool(
        database_url,
        min_size=2,
        max_size=10,
    )
    logger.info("Database pool created: min_size=2, max_size=10")
    return pool


async def close_pool(pool: asyncpg.Pool) -> None:
    """Gracefully close the connection pool.

    Args:
        pool: The asyncpg pool to close.
    """
    logger.info("Closing database connection pool")
    await pool.close()
    logger.info("Database pool closed")


async def run_schema(pool: asyncpg.Pool, schema_path: str | None = None) -> None:
    """Execute the schema SQL file against the database.

    Args:
        pool: Active asyncpg connection pool.
        schema_path: Path to schema.sql. Defaults to backend/db/schema.sql.
    """
    if schema_path is None:
        schema_path = str(Path(__file__).parent / "schema.sql")
    logger.info("Running schema from %s", schema_path)
    sql = Path(schema_path).read_text()
    async with pool.acquire() as conn:
        await conn.execute(sql)
    logger.info("Schema applied successfully")
