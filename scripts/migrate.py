"""
One-time migration: JSONL files → Postgres with embeddings.

Usage:
    DATABASE_URL=... OPENAI_API_KEY=... python scripts/migrate.py

Safe to re-run — the unique index on (category, md5(text)) ensures
ON CONFLICT DO NOTHING skips already-imported rows.
"""

import json
import os
import sys
import time

import openai
import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

# Resolve data dir relative to this script's location
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPTS_DIR, "..", "data")

# JSONL file → category name used in the DB
FILES = {
    "life.jsonl":     "life",
    "student.jsonl":  "learning",   # note: stored as 'learning', not 'student'
    "family.jsonl":   "family",
    "business.jsonl": "business",
}

BATCH_SIZE = 100
BATCH_PAUSE = 0.5  # seconds between OpenAI embedding batches


def load_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def embed_batch(client: openai.OpenAI, texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(
        input=texts,
        model="text-embedding-3-small",
    )
    return [item.embedding for item in response.data]


def migrate():
    database_url = os.environ.get("DATABASE_URL")
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("API_KEY")

    if not database_url:
        sys.exit("ERROR: DATABASE_URL environment variable is not set.")
    if not api_key:
        sys.exit("ERROR: OPENAI_API_KEY environment variable is not set.")

    client = openai.OpenAI(api_key=api_key)

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        register_vector(conn)

        # Ensure schema exists (idempotent)
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id         SERIAL PRIMARY KEY,
                category   TEXT        NOT NULL,
                text       TEXT        NOT NULL,
                media      TEXT,
                audios     TEXT[]      NOT NULL DEFAULT '{}',
                embedding  vector(1536),
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS messages_category_text_uq
                ON messages (category, md5(text))
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS messages_embedding_hnsw_idx
                ON messages USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 128)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS messages_category_idx ON messages (category)
        """)
        conn.commit()

        total_inserted = 0

        for filename, category in FILES.items():
            path = os.path.join(DATA_DIR, filename)
            if not os.path.exists(path):
                print(f"WARNING: {path} not found, skipping.")
                continue

            rows = load_jsonl(path)
            print(f"\n{filename} → category='{category}': {len(rows)} rows")

            # Process in batches
            for batch_start in range(0, len(rows), BATCH_SIZE):
                batch = rows[batch_start: batch_start + BATCH_SIZE]
                texts = [r["text"] for r in batch]

                print(f"  Embedding rows {batch_start + 1}–{batch_start + len(batch)}…", end=" ", flush=True)
                embeddings = embed_batch(client, texts)
                print("done")

                inserted = 0
                for row, embedding in zip(batch, embeddings):
                    audios = row.get("audios") or []
                    if isinstance(audios, str):
                        audios = [audios]

                    result = conn.execute(
                        """
                        INSERT INTO messages (category, text, media, audios, embedding)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT ON CONSTRAINT messages_category_text_uq DO NOTHING
                        """,
                        (
                            category,
                            row["text"],
                            row.get("media"),
                            audios,
                            embedding,
                        ),
                    )
                    inserted += result.rowcount

                conn.commit()
                total_inserted += inserted
                print(f"  Inserted {inserted}/{len(batch)} rows (skipped duplicates)")

                if batch_start + BATCH_SIZE < len(rows):
                    time.sleep(BATCH_PAUSE)

        print(f"\nMigration complete. Total rows inserted: {total_inserted}")

        # Verification counts
        print("\nRow counts by category:")
        for row in conn.execute("SELECT category, COUNT(*) AS n FROM messages GROUP BY category ORDER BY category"):
            print(f"  {row['category']}: {row['n']}")


if __name__ == "__main__":
    migrate()
