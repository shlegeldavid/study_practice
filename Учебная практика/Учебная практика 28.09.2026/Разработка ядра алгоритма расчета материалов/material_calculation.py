import sqlite3
from fractions import Fraction
from math import ceil, isfinite


class MaterialCalculator:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def calculate_material_amount(
        self,
        product_type_id: int,
        material_type_id: int,
        quantity: int,
        param_1: float,
        param_2: float,
    ) -> int:
        """Возвращает расход с запасом на брак или -1 для неверных данных."""
        for type_id in (product_type_id, material_type_id):
            if type(type_id) is not int or not 0 < type_id <= 2**63 - 1:
                return -1
        if type(quantity) is not int or quantity <= 0:
            return -1
        for parameter in (param_1, param_2):
            if type(parameter) not in (int, float) or parameter <= 0:
                return -1
            if type(parameter) is float and not isfinite(parameter):
                return -1

        row = self.connection.execute(
            """
            SELECT p.coefficient, m.defect_percent
            FROM product_types AS p
            CROSS JOIN material_types AS m
            WHERE p.id = ? AND m.id = ?
            """,
            (product_type_id, material_type_id),
        ).fetchone()
        if row is None:
            return -1
        coefficient, defect_percent = row
        for value in (coefficient, defect_percent):
            if type(value) not in (int, float):
                return -1
            if type(value) is float and not isfinite(value):
                return -1
        if coefficient <= 0 or not 0 <= defect_percent <= 100:
            return -1

        # Десятичные значения считаем точно, чтобы погрешность float не завысила ceil.
        base_per_unit = (
            Fraction(str(param_1)) * Fraction(str(param_2)) * Fraction(str(coefficient))
        )
        total_clean = base_per_unit * quantity
        total_with_defect = total_clean * (1 + Fraction(str(defect_percent)) / 100)
        return ceil(total_with_defect)
