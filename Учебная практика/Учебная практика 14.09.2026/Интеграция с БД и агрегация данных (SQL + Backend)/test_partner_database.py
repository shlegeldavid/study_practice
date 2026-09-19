import unittest

from partner_database import connect_database, create_schema, get_partner_with_discount


class TestPartnerDatabase(unittest.TestCase):
    def setUp(self):
        self.connection = connect_database()
        create_schema(self.connection)

    def tearDown(self):
        self.connection.close()

    def test_sales_are_summed_and_discount_is_added(self):
        self.connection.execute("INSERT INTO partners (id, name) VALUES (?, ?)", (1, "Вектор"))
        self.connection.executemany(
            "INSERT INTO sales_history (partner_id, quantity) VALUES (?, ?)",
            [(1, 7000), (1, 3000)],
        )
        self.connection.commit()

        result = get_partner_with_discount(self.connection, 1)

        self.assertEqual(
            result,
            {
                "partner_id": 1,
                "name": "Вектор",
                "total_quantity": 10000,
                "discount_percent": 5,
            },
        )

    def test_partner_without_sales_has_zero_quantity_and_discount(self):
        self.connection.execute("INSERT INTO partners (id, name) VALUES (?, ?)", (2, "Север"))
        self.connection.commit()

        result = get_partner_with_discount(self.connection, 2)

        self.assertEqual(result["total_quantity"], 0)
        self.assertEqual(result["discount_percent"], 0)

    def test_missing_partner_returns_none(self):
        self.assertIsNone(get_partner_with_discount(self.connection, 999))


if __name__ == "__main__":
    unittest.main()
