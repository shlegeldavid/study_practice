from __future__ import annotations

import sqlite3
from pathlib import Path

from partner_discount import calculate_partner_discount


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS partners (
    id INTEGER PRIMARY KEY,
    partner_type TEXT NOT NULL,
    name TEXT NOT NULL,
    director TEXT NOT NULL,
    phone TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 0)
);

CREATE TABLE IF NOT EXISTS sales_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    partner_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    sale_date TEXT,
    FOREIGN KEY (partner_id) REFERENCES partners (id)
);
"""


PARTNER_LIST_QUERY = """
SELECT
    p.id,
    p.partner_type,
    p.name,
    p.director,
    p.phone,
    p.rating,
    COALESCE(SUM(s.quantity), 0) AS total_quantity
FROM partners AS p
LEFT JOIN sales_history AS s ON s.partner_id = p.id
GROUP BY p.id, p.partner_type, p.name, p.director, p.phone, p.rating
ORDER BY p.name
"""


def connect_database(database_path: str | Path = ":memory:") -> sqlite3.Connection:
    connection = sqlite3.connect(str(database_path))
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_SQL)
    connection.commit()


def get_all_partners(connection: sqlite3.Connection) -> list[dict[str, object]]:
    partners = []
    for row in connection.execute(PARTNER_LIST_QUERY).fetchall():
        total_quantity = int(row[6] or 0)
        partners.append(
            {
                "partner_id": row[0],
                "type": row[1],
                "name": row[2],
                "director": row[3],
                "phone": row[4],
                "rating": row[5],
                "total_quantity": total_quantity,
                "discount_percent": calculate_partner_discount(total_quantity),
            }
        )
    return partners


def seed_demo_data(connection: sqlite3.Connection) -> None:
    """Заполняет новую базу небольшим набором данных для демонстрации."""
    partner_count = connection.execute("SELECT COUNT(*) FROM partners").fetchone()[0]
    if partner_count > 0:
        return

    connection.executemany(
        """
        INSERT INTO partners (id, partner_type, name, director, phone, rating)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "ООО", "Ромашка", "Иванов Иван Иванович", "+7 223 322 22 32", 10),
            (2, "ООО", "Вектор", "Петров Пётр Петрович", "+7 495 120 45 67", 8),
            (3, "ИП", "Север", "Сидорова Анна Олеговна", "+7 812 765 43 21", 9),
            (4, "АО", "Маяк", "Орлов Сергей Андреевич", "+7 343 555 19 20", 7),
        ],
    )
    connection.executemany(
        """
        INSERT INTO sales_history (partner_id, quantity, sale_date)
        VALUES (?, ?, ?)
        """,
        [
            (1, 7000, "2026-09-01"),
            (1, 3000, "2026-09-10"),
            (2, 50000, "2026-09-05"),
            (4, 300000, "2026-09-12"),
        ],
    )
    connection.commit()
