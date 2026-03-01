import os
from psycopg_pool import AsyncConnectionPool
from pgvector.psycopg import register_vector_async

_pool: AsyncConnectionPool | None = None

_SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS messages (
    id         SERIAL PRIMARY KEY,
    category   TEXT        NOT NULL,
    text       TEXT        NOT NULL,
    media      TEXT,
    audios     TEXT[]      NOT NULL DEFAULT '{}',
    embedding  vector(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS messages_embedding_hnsw_idx
    ON messages USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 128);

CREATE INDEX IF NOT EXISTS messages_category_idx ON messages (category);

CREATE UNIQUE INDEX IF NOT EXISTS messages_category_text_uq
    ON messages (category, md5(text));
"""


async def _configure_conn(conn):
    await register_vector_async(conn)


async def _ensure_schema(pool: AsyncConnectionPool):
    async with pool.connection() as conn:
        await conn.execute(_SCHEMA)


async def init_pool():
    global _pool
    database_url = os.environ["DATABASE_URL"]
    _pool = AsyncConnectionPool(
        database_url,
        min_size=1,
        max_size=5,
        configure=_configure_conn,
        open=False,
    )
    await _pool.open()
    await _ensure_schema(_pool)


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> AsyncConnectionPool:
    if _pool is None:
        raise RuntimeError("DB pool is not initialised — call init_pool() first")
    return _pool
