import ast
import unittest
from pathlib import Path

from material_calculation import MaterialCalculator
from partner_database import (
    add_partner,
    connect_database,
    create_schema,
    get_all_partners,
    get_partner_by_id,
    get_partner_sales_history,
    seed_demo_data,
    seed_material_demo_data,
    update_partner,
)


class SqlSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = connect_database()
        create_schema(self.connection)
        seed_demo_data(self.connection)
        seed_material_demo_data(self.connection)
        self.payload = "x'); DROP TABLE partners; --"
        self.partner = {
            "type": "ООО",
            "name": self.payload,
            "rating": 5,
            "address": self.payload,
            "director": self.payload,
            "phone": self.payload,
            "email": self.payload,
        }

    def tearDown(self) -> None:
        self.connection.close()

    def test_add_partner_saves_sql_like_fields_literally(self) -> None:
        partner_id = add_partner(self.connection, self.partner)
        self.assertEqual(get_partner_by_id(self.connection, partner_id), {"partner_id": partner_id, **self.partner})
        self.assertEqual(len(get_all_partners(self.connection)), 5)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM sales_history").fetchone()[0], 4)

    def test_update_with_sql_like_text_changes_only_selected_partner(self) -> None:
        untouched = get_partner_by_id(self.connection, 2)
        self.assertTrue(update_partner(self.connection, 1, self.partner))
        self.assertEqual(get_partner_by_id(self.connection, 1)["name"], self.payload)
        self.assertEqual(get_partner_by_id(self.connection, 2), untouched)
        self.assertEqual(len(get_partner_sales_history(self.connection, 1)), 2)
        self.assertEqual(self.connection.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_sql_in_id_cannot_read_or_update_other_records(self) -> None:
        initial = get_all_partners(self.connection)
        for invalid_id in ("1 OR 1=1", "1; DROP TABLE partners; --", "' OR '1'='1"):
            with self.subTest(invalid_id=invalid_id):
                self.assertIsNone(get_partner_by_id(self.connection, invalid_id))
                self.assertEqual(get_partner_sales_history(self.connection, invalid_id), [])
                self.assertFalse(update_partner(self.connection, invalid_id, self.partner))
                calculator = MaterialCalculator(self.connection)
                self.assertEqual(calculator.calculate_material_amount(invalid_id, 1, 100, 2.5, 3.0), -1)
                self.assertEqual(calculator.calculate_material_amount(1, invalid_id, 100, 2.5, 3.0), -1)
        self.assertEqual(get_all_partners(self.connection), initial)

    def test_production_sql_uses_fixed_query_text(self) -> None:
        root = Path(__file__).resolve().parent
        for name in ("app.py", "partner_database.py", "material_calculation.py", "example_material_calculation.py"):
            tree = ast.parse((root / name).read_text(encoding="utf-8-sig"))
            constants = {
                target.id: node.value.value
                for node in tree.body
                if isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
                for target in node.targets
                if isinstance(target, ast.Name)
            }
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr in ("execute", "executemany", "executescript"):
                        with self.subTest(file=name, line=node.lineno):
                            query = node.args[0]
                            if isinstance(query, ast.Name):
                                self.assertIn(query.id, constants)
                                query_text = constants[query.id]
                            else:
                                self.assertIsInstance(query, ast.Constant)
                                query_text = query.value
                            self.assertIsInstance(query_text, str)
                            if "?" in query_text or ":type" in query_text or ":partner_id" in query_text:
                                self.assertGreaterEqual(len(node.args), 2)


if __name__ == "__main__":
    unittest.main()
