# Интеграция с базой данных

Небольшой пример на Python и SQLite. Для каждого партнера количество товара
берется из таблицы `sales_history`, после чего по нему рассчитывается скидка.

## Запуск

Нужен Python 3. Запускать команды можно из этой папки:

```text
python example.py
python -m unittest discover -s . -p "test_*.py"
```

Дополнительные библиотеки не нужны: используется стандартный модуль
`sqlite3`.

## Запрос

Суммарное количество продаж для одного партнера получается одним
параметризованным запросом:

```sql
SELECT
    p.id AS partner_id,
    p.name,
    COALESCE(SUM(s.quantity), 0) AS total_quantity
FROM partners AS p
LEFT JOIN sales_history AS s ON s.partner_id = p.id
WHERE p.id = ?
GROUP BY p.id, p.name;
```

Знак `?` заменяется значением `partner_id`, поэтому значение не склеивается
с текстом SQL-запроса. `LEFT JOIN` позволяет получить партнера, у которого
еще нет продаж, а `COALESCE` возвращает для него ноль.

Метод `get_partner_with_discount` возвращает словарь с полями партнера,
`total_quantity` и рассчитанным `discount_percent`. Если партнера нет в
таблице `partners`, метод возвращает `None`.
