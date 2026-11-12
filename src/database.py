import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("webhunter.db")


def init_db() -> None:
    """Cria a tabela de anúncios vistos caso ainda não exista."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seen_ads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT,
                price REAL,
                source TEXT,
                found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def is_ad_seen(url: str) -> bool:
    """Verifica se a URL já foi processada anteriormente."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM seen_ads WHERE url = ?", (url,))
        return cursor.fetchone() is not None


def mark_ad_as_seen(url: str, title: str, price: float, source: str) -> None:
    """Registra um novo anúncio no banco para evitar alertas duplicados."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO seen_ads (url, title, price, source, found_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (url, title, price, source, datetime.now().isoformat()),
        )
        conn.commit()