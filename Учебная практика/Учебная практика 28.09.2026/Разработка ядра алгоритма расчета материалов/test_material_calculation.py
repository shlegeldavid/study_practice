import inspect
import sqlite3
import unittest
from unittest.mock import Mock

from material_calculation import MaterialCalculator
from partner_database import connect_database, create_schema, seed_material_demo_data


class MaterialCalculationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = connect_database()
        create_schema(self.connection)
        seed_material_demo_data(self.connection)
        self.calculator = MaterialCalculator(self.connection)

    def tearDown(self) -> None:
        self.connection.close()

    def test_method_accepts_five_business_parameters(self) -> None:
        self.assertEqual(
            list(inspect.signature(self.calculator.calculate_material_amount).parameters),
            ["product_type_id", "material_type_id", "quantity", "param_1", "param_2"],
        )

    def test_formula_adds_defect_percentage(self) -> None:
        # 2.5 * 3 * 1.2 * 100 * (1 + 5 / 100) = 945.
        self.assertEqual(self.calculator.calculate_material_amount(1, 1, 100, 2.5, 3.0), 945)
        # 1 * 1 * 1.5 * 10 * (1 + 2.5 / 100) = 15.375 -> 16.
        self.assertEqual(self.calculator.calculate_material_amount(2, 2, 10, 1.0, 1.0), 16)

    def test_rounding_happens_after_defect_is_added(self) -> None:
        # 0.2 * 0.5 * 1.2 * 10 * 1.05 = 1.26 -> 2.
        self.assertEqual(self.calculator.calculate_material_amount(1, 1, 10, 0.2, 0.5), 2)

    def test_float_error_does_not_add_an_extra_unit(self) -> None:
        self.connection.execute("INSERT INTO product_types VALUES (3, 'Без коэффициента расхода', 1.0)")
        self.connection.execute("INSERT INTO material_types VALUES (3, 'Без брака', 0.0)")
        self.assertEqual(self.calculator.calculate_material_amount(3, 3, 50, 0.1, 0.2), 1)

    def test_small_positive_defect_still_rounds_up(self) -> None:
        self.connection.execute("INSERT INTO product_types VALUES (3, 'Тестовый тип', 1.0)")
        self.connection.execute("INSERT INTO material_types VALUES (3, 'Малый брак', 1e-300)")
        self.assertEqual(self.calculator.calculate_material_amount(3, 3, 1, 1.0, 1.0), 2)

    def test_unknown_or_invalid_type_ids_return_minus_one(self) -> None:
        for invalid in (999, 0, -1, 1.0, "1 OR 1=1", True, None, 2**63):
            for position in (0, 1):
                with self.subTest(invalid=invalid, position=position):
                    args = [1, 1, 100, 2.5, 3.0]
                    args[position] = invalid
                    self.assertEqual(self.calculator.calculate_material_amount(*args), -1)

    def test_invalid_quantity_returns_minus_one(self) -> None:
        for quantity in (0, -1, 1.5, "100", True, None):
            with self.subTest(quantity=quantity):
                self.assertEqual(self.calculator.calculate_material_amount(1, 1, quantity, 2.5, 3.0), -1)

    def test_invalid_product_parameters_return_minus_one(self) -> None:
        for invalid in (0, -0.1, float("nan"), float("inf"), float("-inf"), "2.5", True, None):
            for position in (3, 4):
                with self.subTest(invalid=invalid, position=position):
                    args = [1, 1, 100, 2.5, 3.0]
                    args[position] = invalid
                    self.assertEqual(self.calculator.calculate_material_amount(*args), -1)

    def test_updated_coefficients_are_read_from_database(self) -> None:
        self.connection.execute("UPDATE product_types SET coefficient = 2.0 WHERE id = 1")
        self.connection.execute("UPDATE material_types SET defect_percent = 10.0 WHERE id = 1")
        self.assertEqual(self.calculator.calculate_material_amount(1, 1, 100, 2.5, 3.0), 1650)

    def test_zero_and_full_defect_percentages(self) -> None:
        for percent, expected in ((0, 12), (100, 24)):
            with self.subTest(percent=percent):
                self.connection.execute(
                    "UPDATE material_types SET defect_percent = ? WHERE id = 1", (percent,)
                )
                self.assertEqual(self.calculator.calculate_material_amount(1, 1, 10, 1.0, 1.0), expected)

    def test_calculation_does_not_write_to_database(self) -> None:
        changes = self.connection.total_changes
        self.calculator.calculate_material_amount(1, 1, 100, 2.5, 3.0)
        self.assertEqual(self.connection.total_changes, changes)

    def test_invalid_reference_values_return_minus_one(self) -> None:
        connection = Mock()
        calculator = MaterialCalculator(connection)
        for row in ((0, 5), (-1, 5), (float("inf"), 5), (1.2, -1), (1.2, 101), (1.2, float("nan")), (None, 5)):
            with self.subTest(row=row):
                connection.execute.return_value.fetchone.return_value = row
                self.assertEqual(calculator.calculate_material_amount(1, 1, 10, 1.0, 1.0), -1)

    def test_schema_constraints_and_demo_seed_preserve_existing_values(self) -> None:
        self.connection.execute("UPDATE product_types SET coefficient = 2.0 WHERE id = 1")
        seed_material_demo_data(self.connection)
        self.assertEqual(self.connection.execute("SELECT coefficient FROM product_types WHERE id = 1").fetchone()[0], 2.0)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM product_types").fetchone()[0], 2)
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("INSERT INTO product_types VALUES (3, 'Неверный коэффициент', 0)")
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute("INSERT INTO material_types VALUES (3, 'Неверный процент', -1)")


if __name__ == "__main__":
    unittest.main()
