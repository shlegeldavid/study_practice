import sqlite3
import unittest

from partner_database import (
    connect_database,
    create_schema,
    get_all_partners,
    get_partner_sales_history,
    seed_demo_data,
)


class PartnerHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = connect_database()
        create_schema(self.connection)
        seed_demo_data(self.connection)

    def tearDown(self) -> None:
        self.connection.close()

    def test_history_contains_product_quantity_and_formatted_date(self) -> None:
        self.assertEqual(
            get_partner_sales_history(self.connection, 1),
            [
                {"product_name": "Паркетная доска Ясень", "quantity": 3000, "sale_date": "10.09.2026"},
                {"product_name": "Ламинат Дуб натуральный", "quantity": 7000, "sale_date": "01.09.2026"},
            ],
        )
        self.assertEqual(get_partner_sales_history(self.connection, 2)[0]["quantity"], 50000)

    def test_partner_without_sales_and_missing_partner_have_empty_history(self) -> None:
        self.assertEqual(get_partner_sales_history(self.connection, 3), [])
        self.assertEqual(get_partner_sales_history(self.connection, 999), [])

    def test_partner_filter_is_parameterized(self) -> None:
        self.assertEqual(get_partner_sales_history(self.connection, "1 OR 1=1"), [])

    def test_sales_on_same_date_have_stable_order(self) -> None:
        self.connection.executemany(
            "INSERT INTO sales_history (partner_id, quantity, sale_date) VALUES (1, ?, '2026-10-03')",
            [(20,), (30,)],
        )
        history = get_partner_sales_history(self.connection, 1)
        self.assertEqual([sale["quantity"] for sale in history], [30, 20, 3000, 7000])

    def test_missing_product_and_date_do_not_hide_a_sale(self) -> None:
        self.connection.execute(
            "INSERT INTO sales_history (partner_id, quantity) VALUES (3, 10)"
        )
        self.assertEqual(
            get_partner_sales_history(self.connection, 3),
            [{"product_name": "Не указано", "quantity": 10, "sale_date": "Не указана"}],
        )

    def test_product_foreign_key_rejects_unknown_product(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                "INSERT INTO sales_history (partner_id, product_id, quantity) VALUES (1, 999, 10)"
            )

    def test_old_database_keeps_sales_ids_dates_and_discounts(self) -> None:
        old = connect_database()
        try:
            old.executescript(
                """
                CREATE TABLE partners (
                    id INTEGER PRIMARY KEY, partner_type TEXT NOT NULL,
                    name TEXT NOT NULL, director TEXT NOT NULL,
                    phone TEXT NOT NULL, rating INTEGER NOT NULL
                );
                CREATE TABLE sales_history (
                    id INTEGER PRIMARY KEY, partner_id INTEGER REFERENCES partners(id),
                    quantity INTEGER NOT NULL, sale_date TEXT
                );
                INSERT INTO partners VALUES (10, 'ООО', 'Старый партнер', 'Директор', '123', 5);
                INSERT INTO sales_history VALUES (25, 10, 50000, '2026-09-01');
                """
            )
            create_schema(old)
            create_schema(old)
            seed_demo_data(old)
            self.assertEqual(old.execute("SELECT COUNT(*) FROM partners").fetchone()[0], 1)
            self.assertEqual(
                old.execute("SELECT id, partner_id, quantity, sale_date, product_id FROM sales_history").fetchall(),
                [(25, 10, 50000, "2026-09-01", None)],
            )
            self.assertEqual(
                get_partner_sales_history(old, 10),
                [{"product_name": "Не указано", "quantity": 50000, "sale_date": "01.09.2026"}],
            )
            self.assertEqual(get_all_partners(old)[0]["discount_percent"], 10)
            self.assertEqual(old.execute("PRAGMA foreign_key_check").fetchall(), [])
            old.execute("INSERT INTO products (id, name) VALUES (7, 'Продукция из архива')")
            old.execute("UPDATE sales_history SET product_id = 7 WHERE id = 25")
            self.assertEqual(get_partner_sales_history(old, 10)[0]["product_name"], "Продукция из архива")
        finally:
            old.close()


if __name__ == "__main__":
    unittest.main()
