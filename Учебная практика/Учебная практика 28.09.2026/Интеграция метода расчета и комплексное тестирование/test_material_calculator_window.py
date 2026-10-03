import sqlite3
import tkinter as tk
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import app


class MaterialCalculatorWindowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory(prefix="material-calculator-")
        self.addCleanup(self.temp_dir.cleanup)
        self.database_path = Path(self.temp_dir.name) / "partners.db"
        database_patch = patch.object(app, "DATABASE_PATH", self.database_path)
        database_patch.start()
        self.addCleanup(database_patch.stop)
        self.root = tk.Tk()
        self.addCleanup(self.root.destroy)
        self.root.withdraw()
        self.callback_errors = []
        self.root.report_callback_exception = self.record_callback_error
        self.main_window = app.MainWindow(self.root)
        self.main_window.calculator_button.invoke()
        self.root.update()
        self.calculator = self.main_window.calculator_window

    def tearDown(self) -> None:
        self.assertEqual(self.callback_errors, [])

    def record_callback_error(self, error_type, error, traceback) -> None:
        self.callback_errors.append(error)

    def fill_valid_values(self) -> None:
        for label, type_id in self.calculator.product_type_ids.items():
            if type_id == 1:
                self.calculator.values["product_type_id"].set(label)
        for label, type_id in self.calculator.material_type_ids.items():
            if type_id == 1:
                self.calculator.values["material_type_id"].set(label)
        self.calculator.values["quantity"].set("100")
        self.calculator.values["param_1"].set("2.5")
        self.calculator.values["param_2"].set("3.0")

    def test_calculate_button_displays_real_database_result(self) -> None:
        self.fill_valid_values()
        self.calculator.calculate_button.invoke()
        self.assertEqual(self.calculator.result_var.get(), "Необходимое количество материала: 945")
        self.assertEqual(str(self.calculator.product_type_combo["state"]), "readonly")
        self.assertEqual(str(self.calculator.material_type_combo["state"]), "readonly")

    def test_decimal_comma_is_accepted(self) -> None:
        self.fill_valid_values()
        self.calculator.values["param_1"].set("2,5")
        self.calculator.calculate_button.invoke()
        self.assertEqual(self.calculator.result_var.get(), "Необходимое количество материала: 945")

    def test_invalid_numbers_show_error_and_keep_window_open(self) -> None:
        for field, values in (
            ("quantity", ("0", "-1", "1.5", "", "abc")),
            ("param_1", ("0", "-2.5", "nan", "inf", "", "abc")),
            ("param_2", ("0", "-1", "-inf", "nan")),
        ):
            for value in values:
                with self.subTest(field=field, value=value):
                    self.fill_valid_values()
                    self.calculator.values[field].set(value)
                    with patch.object(app.messagebox, "showerror") as show_error:
                        self.calculator.calculate_button.invoke()
                        show_error.assert_called_once()
                        self.assertIn("больше 0", show_error.call_args.args[1])
                    self.assertEqual(self.calculator.result_var.get(), "Результат: расчет не выполнен")
                    self.assertTrue(self.calculator.window.winfo_exists())

    def test_missing_selection_or_unknown_id_is_reported(self) -> None:
        for field in ("product_type_id", "material_type_id"):
            for value in ("", "999 — Несуществующий тип"):
                with self.subTest(field=field, value=value):
                    self.fill_valid_values()
                    self.calculator.values[field].set(value)
                    with patch.object(app.messagebox, "showerror") as show_error:
                        self.calculator.calculate_button.invoke()
                        show_error.assert_called_once()
                        self.assertIn("существующие типы", show_error.call_args.args[1])
                    self.assertEqual(self.calculator.result_var.get(), "Результат: расчет не выполнен")

    def test_type_deleted_after_opening_returns_minus_one_to_ui(self) -> None:
        self.fill_valid_values()
        connection = app.connect_database(self.database_path)
        try:
            connection.execute("DELETE FROM product_types WHERE id = 1")
            connection.commit()
        finally:
            connection.close()
        with patch.object(app.messagebox, "showerror") as show_error:
            self.calculator.calculate_button.invoke()
            show_error.assert_called_once()
            self.assertIn("удален", show_error.call_args.args[1])
        self.assertEqual(self.calculator.result_var.get(), "Результат: расчет не выполнен")

    def test_returned_minus_one_is_not_displayed_as_material_amount(self) -> None:
        self.fill_valid_values()
        with patch.object(app.MaterialCalculator, "calculate_material_amount", return_value=-1):
            with patch.object(app.messagebox, "showerror") as show_error:
                self.calculator.calculate_button.invoke()
                show_error.assert_called_once()
        self.assertEqual(self.calculator.result_var.get(), "Результат: расчет не выполнен")

    def test_result_is_cleared_on_input_change_and_recovers_after_error(self) -> None:
        self.fill_valid_values()
        self.calculator.calculate_button.invoke()
        self.calculator.values["param_1"].set("-2.5")
        self.assertEqual(self.calculator.result_var.get(), "Результат: —")
        with patch.object(app.messagebox, "showerror"):
            self.calculator.calculate_button.invoke()
        self.calculator.values["param_1"].set("2.5")
        self.calculator.calculate_button.invoke()
        self.assertEqual(self.calculator.result_var.get(), "Необходимое количество материала: 945")

    def test_sql_failure_clears_old_result_and_shows_database_error(self) -> None:
        self.fill_valid_values()
        self.calculator.calculate_button.invoke()
        connection = app.connect_database(self.database_path)
        try:
            connection.execute("DROP TABLE material_types")
            connection.commit()
        finally:
            connection.close()
        with patch.object(app.messagebox, "showerror") as show_error:
            self.calculator.calculate_button.invoke()
            show_error.assert_called_once()
            self.assertEqual(show_error.call_args.args[0], "Ошибка базы данных")
        self.assertEqual(self.calculator.result_var.get(), "Результат: расчет не выполнен")

    def test_database_open_failure_does_not_leave_partial_window(self) -> None:
        self.calculator.back_button.invoke()
        with patch.object(app, "connect_database", side_effect=sqlite3.OperationalError("Test open failure")):
            with patch.object(app.messagebox, "showerror") as show_error:
                self.main_window.calculator_button.invoke()
                show_error.assert_called_once()
        self.assertIsNone(self.main_window.calculator_window)
        self.assertTrue(self.root.winfo_exists())
        self.assertFalse(any(isinstance(widget, tk.Toplevel) for widget in self.root.winfo_children()))

    def test_very_large_result_is_reported_without_callback_failure(self) -> None:
        self.fill_valid_values()
        self.calculator.values["quantity"].set("9" * 4000)
        self.calculator.values["param_1"].set("1e308")
        self.calculator.values["param_2"].set("1e308")
        with patch.object(app.messagebox, "showerror") as show_error:
            self.calculator.calculate_button.invoke()
            show_error.assert_called_once()
            self.assertIn("слишком велик", show_error.call_args.args[1])
        self.assertEqual(self.calculator.result_var.get(), "Результат: расчет не выполнен")

    def test_back_window_close_and_repeated_open_preserve_partner_list(self) -> None:
        initial_ids = list(self.main_window.partner_cards)
        self.main_window.open_material_calculator()
        self.assertIs(self.main_window.calculator_window, self.calculator)
        self.calculator.back_button.invoke()
        self.assertIsNone(self.main_window.calculator_window)
        self.main_window.calculator_button.invoke()
        window = self.main_window.calculator_window.window
        self.root.tk.call(window.protocol("WM_DELETE_WINDOW"))
        self.assertIsNone(self.main_window.calculator_window)
        self.assertEqual(list(self.main_window.partner_cards), initial_ids)


if __name__ == "__main__":
    unittest.main()
