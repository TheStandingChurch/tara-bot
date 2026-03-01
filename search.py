import os

import openai
from psycopg.rows import dict_row

import db

_client = openai.AsyncOpenAI(
    api_key=os.environ.get("OPENAI_API_KEY") or os.environ.get("API_KEY")
)


async def embed_query(text: str) -> list[float]:
    response = await _client.embeddings.create(
        input=text,
        model="text-embedding-3-small",
    )
    return response.data[0].embedding


async def search(category: str, user_query: str, top_k: int = 5) -> list[dict]:
    embedding = await embed_query(user_query)
    pool = db.get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        rows = await conn.execute(
            """
            SELECT text, media, audios
            FROM messages
            WHERE category = %s AND embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (category, embedding, top_k),
        )
        return await rows.fetchall()
