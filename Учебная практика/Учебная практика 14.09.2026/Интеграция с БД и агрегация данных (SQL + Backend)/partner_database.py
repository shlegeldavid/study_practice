from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from partner_discount import calculate_partner_discount


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS partners (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sales_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    partner_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    sale_date TEXT,
    FOREIGN KEY (partner_id) REFERENCES partners (id)
);
"""


PARTNER_SALES_QUERY = """
SELECT
    p.id AS partner_id,
    p.name,
    COALESCE(SUM(s.quantity), 0) AS total_quantity
FROM partners AS p
LEFT JOIN sales_history AS s ON s.partner_id = p.id
WHERE p.id = ?
GROUP BY p.id, p.name
"""


def connect_database(database_path: str | Path = ":memory:") -> sqlite3.Connection:
    """Открывает соединение с SQLite и включает проверку внешних ключей."""
    connection = sqlite3.connect(str(database_path))
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_schema(connection: sqlite3.Connection) -> None:
    """Создает таблицы, если их еще нет."""
    connection.executescript(SCHEMA_SQL)
    connection.commit()


def get_partner_with_discount(
    connection: sqlite3.Connection, partner_id: int
) -> Optional[dict[str, object]]:
    """Возвращает данные партнера, объем продаж и его текущую скидку."""
    row = connection.execute(PARTNER_SALES_QUERY, (partner_id,)).fetchone()
    if row is None:
        return None

    total_quantity = int(row[2])
    return {
        "partner_id": row[0],
        "name": row[1],
        "total_quantity": total_quantity,
        "discount_percent": calculate_partner_discount(total_quantity),
    }


def seed_demo_data(connection: sqlite3.Connection) -> None:
    """Добавляет несколько записей для запуска примера."""
    connection.executemany(
        "INSERT OR IGNORE INTO partners (id, name) VALUES (?, ?)",
        [
            (1, "ООО Ромашка"),
            (2, "ООО Вектор"),
            (3, "ООО Север"),
        ],
    )
    connection.executemany(
        "INSERT INTO sales_history (partner_id, quantity, sale_date) VALUES (?, ?, ?)",
        [
            (1, 7000, "2026-09-01"),
            (1, 3000, "2026-09-10"),
            (2, 50000, "2026-09-05"),
        ],
    )
    connection.commit()
