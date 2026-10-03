from pathlib import Path

from material_calculation import MaterialCalculator
from partner_database import connect_database, create_schema, seed_material_demo_data


def main() -> None:
    connection = connect_database(Path(__file__).resolve().parent / "partners.db")
    try:
        create_schema(connection)
        seed_material_demo_data(connection)
        calculator = MaterialCalculator(connection)
        result = calculator.calculate_material_amount(1, 1, 100, 2.5, 3.0)
        print(f"Необходимое количество материала: {result}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
