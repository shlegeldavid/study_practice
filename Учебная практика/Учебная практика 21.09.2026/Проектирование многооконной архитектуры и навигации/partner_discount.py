def calculate_partner_discount(total_quantity: int) -> int:
    """Возвращает процент скидки по общему количеству проданного товара."""
    if total_quantity >= 300000:
        return 15
    if total_quantity >= 50000:
        return 10
    if total_quantity >= 10000:
        return 5
    return 0
