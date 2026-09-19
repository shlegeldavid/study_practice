import unittest

from partner_discount import calculate_partner_discount


class TestPartnerDiscount(unittest.TestCase):
    def test_quantity_9999(self):
        self.assertEqual(calculate_partner_discount(9999), 0)

    def test_quantity_10000(self):
        self.assertEqual(calculate_partner_discount(10000), 5)

    def test_quantity_49999(self):
        self.assertEqual(calculate_partner_discount(49999), 5)

    def test_quantity_50000(self):
        self.assertEqual(calculate_partner_discount(50000), 10)

    def test_quantity_300000(self):
        self.assertEqual(calculate_partner_discount(300000), 15)


if __name__ == "__main__":
    unittest.main()
