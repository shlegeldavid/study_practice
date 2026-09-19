import unittest

from partner_database import (
    connect_database,
    create_schema,
    get_all_partners,
)


class TestPartnerDatabase(unittest.TestCase):
    def setUp(self):
        self.connection = connect_database()
        create_schema(self.connection)

    def tearDown(self):
        self.connection.close()

    def add_partner(self, partner_id: int, name: str) -> None:
        self.connection.execute(
            """
            INSERT INTO partners (id, partner_type, name, director, phone, rating)
            VALUES (?, 'ООО', ?, 'Иванов И.И.', '+7 900 000 00 00', 5)
            """,
            (partner_id, name),
        )

    def test_partners_and_contacts_are_loaded(self):
        self.add_partner(1, "Ромашка")
        self.connection.executemany(
            "INSERT INTO sales_history (partner_id, quantity) VALUES (?, ?)",
            [(1, 7000), (1, 3000)],
        )
        self.connection.commit()

        partners = get_all_partners(self.connection)

        self.assertEqual(len(partners), 1)
        self.assertEqual(partners[0]["name"], "Ромашка")
        self.assertEqual(partners[0]["phone"], "+7 900 000 00 00")
        self.assertEqual(partners[0]["total_quantity"], 10000)
        self.assertEqual(partners[0]["discount_percent"], 5)

    def test_partner_without_sales_has_zero_discount(self):
        self.add_partner(2, "Север")
        self.connection.commit()

        partner = get_all_partners(self.connection)[0]

        self.assertEqual(partner["total_quantity"], 0)
        self.assertEqual(partner["discount_percent"], 0)

    def test_zero_quantity_has_zero_discount(self):
        self.add_partner(3, "Старт")
        self.connection.execute(
            "INSERT INTO sales_history (partner_id, quantity) VALUES (?, 0)", (3,)
        )
        self.connection.commit()

        partner = get_all_partners(self.connection)[0]

        self.assertEqual(partner["total_quantity"], 0)
        self.assertEqual(partner["discount_percent"], 0)

    def test_discount_levels(self):
        quantities = [0, 10000, 50000, 300000]
        expected_discounts = [0, 5, 10, 15]
        for number, quantity in enumerate(quantities, start=1):
            self.add_partner(number, f"Партнер {number}")
            self.connection.execute(
                "INSERT INTO sales_history (partner_id, quantity) VALUES (?, ?)",
                (number, quantity),
            )
        self.connection.commit()

        discounts = [item["discount_percent"] for item in get_all_partners(self.connection)]

        self.assertEqual(discounts, expected_discounts)


if __name__ == "__main__":
    unittest.main()
