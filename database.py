"""Локальное хранилище данных приложения."""

from pathlib import Path
import sqlite3


PROJECT_DIR = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_DIR / "data" / "dashboard.db"


def get_connection() -> sqlite3.Connection:
    """Возвращает соединение с SQLite с доступом к колонкам по имени."""
    DATABASE_PATH.parent.mkdir(exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    """Создаёт таблицы. Повторный запуск не удаляет рабочие данные."""
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS blanks (
                id INTEGER PRIMARY KEY,
                record_id TEXT,
                date TEXT,
                batch_id TEXT,
                employee TEXT,
                plan_qty REAL,
                fact_qty REAL,
                source_row INTEGER
            );

            CREATE TABLE IF NOT EXISTS welding_needs (
                id INTEGER PRIMARY KEY,
                record_id TEXT,
                date TEXT,
                batch_id TEXT,
                need_qty REAL,
                source_row INTEGER
            );

            CREATE TABLE IF NOT EXISTS documentation (
                id INTEGER PRIMARY KEY,
                record_id TEXT,
                date TEXT,
                employee TEXT,
                plan_docs REAL,
                fact_docs REAL,
                source_row INTEGER
            );

            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_blanks_date ON blanks(date);
            CREATE INDEX IF NOT EXISTS idx_blanks_batch ON blanks(batch_id);
            CREATE INDEX IF NOT EXISTS idx_welding_date ON welding_needs(date);
            CREATE INDEX IF NOT EXISTS idx_welding_batch ON welding_needs(batch_id);
            CREATE INDEX IF NOT EXISTS idx_documentation_date ON documentation(date);
            """
        )

