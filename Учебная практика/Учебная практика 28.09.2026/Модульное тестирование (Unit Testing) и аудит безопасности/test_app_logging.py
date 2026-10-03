import io
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import app
from app_logging import LOGGER, configure_logging


class AppLoggingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory(prefix="app-logging-")
        self.addCleanup(self.temp_dir.cleanup)
        self.log_path = Path(self.temp_dir.name) / "app.log"
        configure_logging(self.log_path)
        self.addCleanup(configure_logging)

    def test_database_error_contains_timestamp_and_readable_message(self) -> None:
        with patch.object(app.messagebox, "showerror"):
            app.show_database_error("загрузить партнеров", sqlite3.OperationalError("Test database locked"), Mock())
        content = self.log_path.read_text(encoding="utf-8")
        self.assertRegex(content, r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \| ERROR \|")
        self.assertIn("Ошибка базы данных при попытке загрузить партнеров", content)
        self.assertIn("Test database locked", content)

    def test_log_appends_without_duplicate_handlers(self) -> None:
        LOGGER.error("Первая ошибка")
        configure_logging(self.log_path)
        configure_logging(self.log_path)
        LOGGER.error("Вторая ошибка")
        lines = self.log_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(len(LOGGER.handlers), 1)
        self.assertIn("Первая ошибка", lines[0])
        self.assertIn("Вторая ошибка", lines[1])

    def test_unavailable_log_file_is_explicitly_reported_in_console(self) -> None:
        console = io.StringIO()
        with patch("sys.stderr", console):
            configure_logging(Path(self.temp_dir.name))
            LOGGER.error("Ошибка после отказа файла")
        content = console.getvalue()
        self.assertIn("Не удалось открыть app.log", content)
        self.assertIn("ошибки записываются в консоль", content)
        self.assertIn("Ошибка после отказа файла", content)
        self.assertRegex(content, r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \| ERROR \|")

    def test_startup_database_exception_is_logged_and_handled(self) -> None:
        root = Mock()
        with patch.object(app, "configure_logging", side_effect=lambda: configure_logging(self.log_path)):
            with patch.object(app.tk, "Tk", return_value=root):
                with patch.object(app, "MainWindow", side_effect=sqlite3.OperationalError("Test startup failure")):
                    with patch.object(app.messagebox, "showerror") as show_error:
                        app.main()
                        show_error.assert_called_once()
        root.destroy.assert_called_once()
        root.mainloop.assert_not_called()
        self.assertIn("Test startup failure", self.log_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
