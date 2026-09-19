import time

from partner_database import connect_database, create_schema, get_all_partners


def main() -> None:
    connection = connect_database()
    try:
        create_schema(connection)
        partners = [
            (
                number,
                "ООО",
                f"Тестовый партнер {number:04d}",
                "Тестовый Директор",
                "+7 900 000 00 00",
                5,
            )
            for number in range(1, 1001)
        ]
        connection.executemany(
            """
            INSERT INTO partners (id, partner_type, name, director, phone, rating)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            partners,
        )
        connection.executemany(
            "INSERT INTO sales_history (partner_id, quantity) VALUES (?, ?)",
            [(number, number * 100) for number in range(2, 1001)],
        )
        connection.commit()

        started_at = time.perf_counter()
        result = get_all_partners(connection)
        elapsed = time.perf_counter() - started_at

        assert len(result) == 1000
        assert result[0]["discount_percent"] == 0
        assert all(item["discount_percent"] in (0, 5, 10, 15) for item in result)
        print(f"Загружено партнеров: {len(result)}")
        print(f"Время получения списка: {elapsed:.3f} сек.")
        print("Демонстрационный тест пройден успешно")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
