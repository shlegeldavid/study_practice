import sqlite3
import unittest

from partner_database import (
    add_partner,
    connect_database,
    create_schema,
    get_all_partners,
    get_partner_by_id,
    seed_demo_data,
    update_partner,
)


class PartnerDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = connect_database()
        create_schema(self.connection)
        self.partner = {
            "type": "ООО",
            "name": "Тестовый партнер",
            "rating": 7,
            "address": "г. Москва, ул. Тестовая, д. 1",
            "director": "Иванов Иван Иванович",
            "phone": "+7 (999) 123-45-67",
            "email": "partner@example.com",
        }

    def tearDown(self) -> None:
        self.connection.close()

    def test_add_partner_and_load_all_fields(self) -> None:
        partner_id = add_partner(self.connection, self.partner)
        loaded = get_partner_by_id(self.connection, partner_id)

        self.assertEqual(loaded, {"partner_id": partner_id, **self.partner})
        self.assertEqual(len(get_all_partners(self.connection)), 1)

    def test_update_preserves_sales_reference_and_discount(self) -> None:
        partner_id = add_partner(self.connection, self.partner)
        self.connection.execute(
            "INSERT INTO sales_history (partner_id, quantity) VALUES (?, ?)",
            (partner_id, 10000),
        )
        self.connection.commit()

        changed = {**self.partner, "name": "Новое название", "email": "new@example.com"}
        self.assertTrue(update_partner(self.connection, partner_id, changed))
        self.assertEqual(get_partner_by_id(self.connection, partner_id)["name"], "Новое название")
        self.assertEqual(get_partner_by_id(self.connection, partner_id)["email"], "new@example.com")
        self.assertEqual(
            self.connection.execute("SELECT partner_id FROM sales_history").fetchone()[0],
            partner_id,
        )
        self.assertEqual(get_all_partners(self.connection)[0]["discount_percent"], 5)
        self.assertEqual(self.connection.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_missing_partner_is_not_replaced_by_new_record(self) -> None:
        self.assertIsNone(get_partner_by_id(self.connection, 999))
        self.assertFalse(update_partner(self.connection, 999, self.partner))
        self.assertEqual(get_all_partners(self.connection), [])

    def test_existing_database_gains_columns_without_losing_sales(self) -> None:
        old = connect_database()
        try:
            old.executescript(
                """
                CREATE TABLE partners (
                    id INTEGER PRIMARY KEY,
                    partner_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    director TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    rating INTEGER NOT NULL
                );
                CREATE TABLE sales_history (
                    id INTEGER PRIMARY KEY,
                    partner_id INTEGER NOT NULL REFERENCES partners(id),
                    quantity INTEGER NOT NULL,
                    sale_date TEXT
                );
                INSERT INTO partners VALUES (10, 'ИП', 'Старая запись', 'Директор', '123', 3);
                INSERT INTO sales_history (partner_id, quantity) VALUES (10, 50000);
                """
            )
            create_schema(old)
            create_schema(old)
            loaded = get_partner_by_id(old, 10)
            self.assertEqual((loaded["address"], loaded["email"]), ("", ""))
            self.assertEqual(get_all_partners(old)[0]["discount_percent"], 10)
            self.assertEqual(old.execute("PRAGMA foreign_key_check").fetchall(), [])
        finally:
            old.close()

    def test_foreign_keys_reject_orphan_sale(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                "INSERT INTO sales_history (partner_id, quantity) VALUES (999, 1)"
            )

    def test_demo_partners_have_editable_contact_fields(self) -> None:
        seed_demo_data(self.connection)
        loaded = get_partner_by_id(self.connection, 1)
        self.assertTrue(loaded["address"])
        self.assertTrue(loaded["email"])


if __name__ == "__main__":
    unittest.main()
