"""Локальное хранилище данных приложения."""

from pathlib import Path
import sqlite3


PROJECT_DIR = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_DIR / "data" / "dashboard.db"
DATA_TABLES = ("blanks", "welding_needs", "documentation")
EDITABLE_COLUMNS = {
    "blanks": ("record_id", "date", "batch_id", "employee", "plan_qty", "fact_qty"),
    "welding_needs": ("record_id", "date", "batch_id", "need_qty"),
    "documentation": ("record_id", "date", "employee", "plan_docs", "fact_docs"),
}


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


def get_meta(key: str) -> str | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT value FROM app_meta WHERE key = ?", (key,)
        ).fetchone()
    return row["value"] if row else None


def set_meta(key: str, value: str) -> None:
    with get_connection() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO app_meta (key, value) VALUES (?, ?)",
            (key, value),
        )


def get_records(table: str) -> list[dict]:
    """Возвращает записи участка в порядке даты и идентификатора."""
    if table not in DATA_TABLES:
        raise ValueError(f"Неизвестная таблица: {table}")
    with get_connection() as connection:
        rows = connection.execute(
            f"SELECT * FROM {table} ORDER BY date, id"
        ).fetchall()
    return [dict(row) for row in rows]


def replace_records(table: str, records: list[dict]) -> None:
    """Сохраняет изменения одного участка, не затрагивая другие таблицы."""
    if table not in DATA_TABLES:
        raise ValueError(f"Неизвестная таблица: {table}")
    columns = EDITABLE_COLUMNS[table]
    rows = [tuple(record.get(column) for column in columns) for record in records]
    placeholders = ", ".join("?" for _ in columns)
    with get_connection() as connection:
        connection.execute(f"DELETE FROM {table}")
        connection.executemany(
            f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
            rows,
        )
