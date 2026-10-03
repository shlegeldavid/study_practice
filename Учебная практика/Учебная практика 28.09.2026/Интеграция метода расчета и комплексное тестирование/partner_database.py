from __future__ import annotations

import sqlite3
from pathlib import Path

from partner_discount import calculate_partner_discount


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS product_types (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    coefficient REAL NOT NULL CHECK (coefficient > 0)
);

CREATE TABLE IF NOT EXISTS material_types (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    defect_percent REAL NOT NULL CHECK (defect_percent BETWEEN 0 AND 100)
);

CREATE TABLE IF NOT EXISTS partners (
    id INTEGER PRIMARY KEY,
    partner_type TEXT NOT NULL,
    name TEXT NOT NULL,
    director TEXT NOT NULL,
    phone TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 0),
    address TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS sales_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    partner_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    sale_date TEXT,
    product_id INTEGER REFERENCES products (id),
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


PARTNER_HISTORY_QUERY = """
SELECT
    COALESCE(p.name, 'Не указано') AS product_name,
    s.quantity,
    CASE
        WHEN s.sale_date IS NULL OR TRIM(s.sale_date) = '' THEN 'Не указана'
        ELSE COALESCE(STRFTIME('%d.%m.%Y', s.sale_date), s.sale_date)
    END AS sale_date
FROM sales_history AS s
LEFT JOIN products AS p ON p.id = s.product_id
WHERE s.partner_id = ?
ORDER BY s.sale_date DESC, s.id DESC
"""


def connect_database(database_path: str | Path = ":memory:") -> sqlite3.Connection:
    connection = sqlite3.connect(str(database_path))
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_SQL)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(partners)")}
    # Старые базы из прошлой практики сохраняют партнеров и историю продаж.
    if "address" not in columns:
        connection.execute("ALTER TABLE partners ADD COLUMN address TEXT NOT NULL DEFAULT ''")
    if "email" not in columns:
        connection.execute("ALTER TABLE partners ADD COLUMN email TEXT NOT NULL DEFAULT ''")
    sales_columns = {row[1] for row in connection.execute("PRAGMA table_info(sales_history)")}
    # У старых продаж нет названия продукции: сохраняем их без выдуманных данных.
    if "product_id" not in sales_columns:
        connection.execute(
            "ALTER TABLE sales_history ADD COLUMN product_id INTEGER REFERENCES products (id)"
        )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_sales_partner_date "
        "ON sales_history (partner_id, sale_date)"
    )
    connection.commit()


def get_partner_sales_history(
    connection: sqlite3.Connection, partner_id: int
) -> list[dict[str, object]]:
    rows = connection.execute(PARTNER_HISTORY_QUERY, (partner_id,)).fetchall()
    return [
        {"product_name": row[0], "quantity": row[1], "sale_date": row[2]}
        for row in rows
    ]


def get_partner_by_id(
    connection: sqlite3.Connection, partner_id: int
) -> dict[str, object] | None:
    row = connection.execute(
        """
        SELECT id, partner_type, name, rating, address, director, phone, email
        FROM partners
        WHERE id = ?
        """,
        (partner_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "partner_id": row[0],
        "type": row[1],
        "name": row[2],
        "rating": row[3],
        "address": row[4],
        "director": row[5],
        "phone": row[6],
        "email": row[7],
    }


def add_partner(connection: sqlite3.Connection, partner: dict[str, object]) -> int:
    cursor = connection.execute(
        """
        INSERT INTO partners (partner_type, name, rating, address, director, phone, email)
        VALUES (:type, :name, :rating, :address, :director, :phone, :email)
        """,
        partner,
    )
    connection.commit()
    return int(cursor.lastrowid)


def update_partner(
    connection: sqlite3.Connection, partner_id: int, partner: dict[str, object]
) -> bool:
    cursor = connection.execute(
        """
        UPDATE partners
        SET partner_type = :type,
            name = :name,
            rating = :rating,
            address = :address,
            director = :director,
            phone = :phone,
            email = :email
        WHERE id = :partner_id
        """,
        {**partner, "partner_id": partner_id},
    )
    connection.commit()
    return cursor.rowcount == 1


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


def seed_material_demo_data(connection: sqlite3.Connection) -> None:
    """Добавляет учебные значения только в пустые справочники."""
    if connection.execute("SELECT COUNT(*) FROM product_types").fetchone()[0] == 0:
        connection.executemany(
            "INSERT INTO product_types (id, name, coefficient) VALUES (?, ?, ?)",
            [(1, "Ламинат", 1.2), (2, "Паркетная доска", 1.5)],
        )
    if connection.execute("SELECT COUNT(*) FROM material_types").fetchone()[0] == 0:
        connection.executemany(
            "INSERT INTO material_types (id, name, defect_percent) VALUES (?, ?, ?)",
            [(1, "Демонстрационный материал А", 5.0), (2, "Демонстрационный материал Б", 2.5)],
        )
    connection.commit()


def seed_demo_data(connection: sqlite3.Connection) -> None:
    """Заполняет новую базу небольшим набором данных для демонстрации."""
    partner_count = connection.execute("SELECT COUNT(*) FROM partners").fetchone()[0]
    if partner_count > 0:
        return

    connection.executemany(
        """
        INSERT INTO partners (id, partner_type, name, director, phone, rating, address, email)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "ООО", "Ромашка", "Иванов Иван Иванович", "+7 223 322 22 32", 10,
             "г. Москва, ул. Примерная, д. 1", "romashka@example.com"),
            (2, "ООО", "Вектор", "Петров Пётр Петрович", "+7 495 120 45 67", 8,
             "г. Москва, ул. Примерная, д. 2", "vector@example.com"),
            (3, "ИП", "Север", "Сидорова Анна Олеговна", "+7 812 765 43 21", 9,
             "г. Санкт-Петербург, ул. Примерная, д. 3", "sever@example.com"),
            (4, "АО", "Маяк", "Орлов Сергей Андреевич", "+7 343 555 19 20", 7,
             "г. Екатеринбург, ул. Примерная, д. 4", "mayak@example.com"),
        ],
    )
    connection.executemany(
        "INSERT INTO products (name) VALUES (?) ON CONFLICT(name) DO NOTHING",
        [("Ламинат Дуб натуральный",), ("Паркетная доска Ясень",), ("Ламинат Дуб светлый",)],
    )
    connection.executemany(
        """
        INSERT INTO sales_history (partner_id, product_id, quantity, sale_date)
        VALUES (?, (SELECT id FROM products WHERE name = ?), ?, ?)
        """,
        [
            (1, "Ламинат Дуб натуральный", 7000, "2026-09-01"),
            (1, "Паркетная доска Ясень", 3000, "2026-09-10"),
            (2, "Ламинат Дуб светлый", 50000, "2026-09-05"),
            (4, "Ламинат Дуб натуральный", 300000, "2026-09-12"),
        ],
    )
    connection.commit()
