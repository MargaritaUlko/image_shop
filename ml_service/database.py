import os
import pickle
import time
import psycopg2
from psycopg2.extras import RealDictCursor


def _get_conn(retries: int = 3, delay: float = 2.0):
    for attempt in range(retries):
        try:
            return psycopg2.connect(
                dbname=os.getenv('DB_NAME', 'db'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', '123'),
                host=os.getenv('DB_HOST', 'db'),
                port=int(os.getenv('DB_PORT', 5432)),
                connect_timeout=10,
            )
        except psycopg2.OperationalError as e:
            if attempt == retries - 1:
                raise
            print(f"[DB] Connection failed ({e}), retrying in {delay}s...")
            time.sleep(delay)


def load_embeddings() -> dict:
    """Returns {artwork_id: numpy_vector}."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT artwork_id, vector FROM shop_app_artworkembedding")
            return {row[0]: pickle.loads(bytes(row[1])) for row in cur.fetchall()}
    finally:
        conn.close()


def save_embedding(artwork_id: int, vector) -> None:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO shop_app_artworkembedding (artwork_id, vector, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (artwork_id)
                DO UPDATE SET vector = EXCLUDED.vector, updated_at = NOW()
                """,
                (artwork_id, psycopg2.Binary(pickle.dumps(vector))),
            )
        conn.commit()
    finally:
        conn.close()


def get_all_artworks() -> list[tuple[int, str]]:
    """Returns list of (id, image_relative_path)."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, image FROM shop_app_artwork")
            return cur.fetchall()
    finally:
        conn.close()
