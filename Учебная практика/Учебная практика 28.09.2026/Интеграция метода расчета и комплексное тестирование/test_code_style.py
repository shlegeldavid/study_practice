import ast
import re
import unittest
from collections import Counter
from pathlib import Path


class CodeStyleTests(unittest.TestCase):
    def test_no_more_than_one_statement_starts_on_a_line(self) -> None:
        for file in Path(__file__).resolve().parent.glob("*.py"):
            with self.subTest(file=file.name):
                tree = ast.parse(file.read_text(encoding="utf-8-sig"))
                lines = Counter(node.lineno for node in ast.walk(tree) if isinstance(node, ast.stmt))
                self.assertEqual([line for line, count in lines.items() if count > 1], [])

    def test_functions_arguments_and_variables_use_snake_case(self) -> None:
        pattern = re.compile(r"^[a-z_][a-z0-9_]*$")
        constant_pattern = re.compile(r"^[A-Z_][A-Z0-9_]*$")
        for file in Path(__file__).resolve().parent.glob("*.py"):
            tree = ast.parse(file.read_text(encoding="utf-8-sig"))
            # Названия хуков unittest определены библиотекой и не могут быть переименованы.
            framework_methods = {
                method
                for cls in ast.walk(tree)
                if isinstance(cls, ast.ClassDef)
                and any(
                    isinstance(base, ast.Attribute)
                    and isinstance(base.value, ast.Name)
                    and base.value.id == "unittest"
                    and base.attr == "TestCase"
                    for base in cls.bases
                )
                for method in cls.body
                if isinstance(method, ast.FunctionDef)
                and method.name in ("setUp", "tearDown", "setUpClass", "tearDownClass")
            }
            for node in ast.walk(tree):
                if node in framework_methods:
                    continue
                name = None
                allow_constant = False
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    name = node.name
                elif isinstance(node, ast.arg):
                    name = node.arg
                elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    name = node.id
                    allow_constant = True
                elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
                    name = node.attr
                    allow_constant = True
                if name is not None:
                    with self.subTest(file=file.name, line=node.lineno, name=name):
                        self.assertTrue(
                            pattern.fullmatch(name) or (allow_constant and constant_pattern.fullmatch(name))
                        )


if __name__ == "__main__":
    unittest.main()
