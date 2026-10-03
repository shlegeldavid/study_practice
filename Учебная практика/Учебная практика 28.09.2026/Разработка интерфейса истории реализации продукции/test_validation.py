import unittest

from app import validate_partner_fields


class PartnerValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.values = {
            "name": " Ромашка ",
            "type": "ООО",
            "rating": "0",
            "address": "",
            "director": "",
            "phone": "",
            "email": " office@example.com ",
        }
        self.types = ("ЗАО", "ООО", "ИП", "АО", "ПАО")

    def test_zero_rating_and_optional_fields_are_accepted(self) -> None:
        partner = validate_partner_fields(self.values, self.types)
        self.assertEqual(partner["rating"], 0)
        self.assertEqual(partner["name"], "Ромашка")
        self.assertEqual(partner["email"], "office@example.com")
        self.assertEqual(partner["address"], "")

    def test_name_and_email_are_required(self) -> None:
        for field in ("name", "email"):
            with self.subTest(field=field):
                values = {**self.values, field: "   "}
                with self.assertRaisesRegex(ValueError, "повторите сохранение"):
                    validate_partner_fields(values, self.types)

    def test_rating_must_be_nonnegative_integer(self) -> None:
        for rating in ("", "-1", "2.5", "abc"):
            with self.subTest(rating=rating):
                values = {**self.values, "rating": rating}
                with self.assertRaisesRegex(ValueError, "Рейтинг"):
                    validate_partner_fields(values, self.types)

    def test_rating_must_fit_sqlite_integer(self) -> None:
        values = {**self.values, "rating": str(2**63)}
        with self.assertRaisesRegex(ValueError, "слишком большой"):
            validate_partner_fields(values, self.types)

    def test_type_must_come_from_list(self) -> None:
        values = {**self.values, "type": "Другое"}
        with self.assertRaisesRegex(ValueError, "Выберите тип"):
            validate_partner_fields(values, self.types)


if __name__ == "__main__":
    unittest.main()
