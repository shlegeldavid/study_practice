from partner_database import (
    connect_database,
    create_schema,
    get_partner_with_discount,
    seed_demo_data,
)


def main() -> None:
    connection = connect_database()
    try:
        create_schema(connection)
        seed_demo_data(connection)

        for partner_id in (1, 2, 3):
            partner = get_partner_with_discount(connection, partner_id)
            print(partner)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
