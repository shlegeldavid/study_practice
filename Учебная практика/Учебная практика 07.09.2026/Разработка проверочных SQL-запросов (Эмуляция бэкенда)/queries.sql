-- 1. Список партнеров и количество их отгрузок.
SELECT
    p.partner_id,
    p.company_name,
    p.inn,
    p.contact_email,
    p.phone,
    p.rating,
    COUNT(s.sale_id) AS deliveries_count
FROM partners AS p
LEFT JOIN sales AS s ON s.partner_id = p.partner_id
GROUP BY
    p.partner_id,
    p.company_name,
    p.inn,
    p.contact_email,
    p.phone,
    p.rating
ORDER BY p.company_name;


-- 2. Добавление партнера и его первой тестовой отгрузки
-- в рамках одной транзакции.
BEGIN;

DELETE FROM sales
WHERE partner_id = (
    SELECT partner_id FROM partners WHERE inn = '7709999999'
);

DELETE FROM partners WHERE inn = '7709999999';

WITH new_partner AS (
    INSERT INTO partners (
        company_name,
        inn,
        contact_email,
        phone,
        rating
    )
    VALUES (
        'ООО "Новый Партнер"',
        '7709999999',
        'new_partner@example.com',
        '+7 (900) 000-00-00',
        5.0
    )
    RETURNING partner_id
)
INSERT INTO sales (
    partner_id,
    product_id,
    sale_date,
    quantity,
    unit_price
)
SELECT
    np.partner_id,
    p.product_id,
    CURRENT_DATE,
    10,
    500.0000
FROM new_partner AS np
CROSS JOIN LATERAL (
    SELECT product_id
    FROM products
    ORDER BY product_id
    LIMIT 1
) AS p;

COMMIT;


-- 3. История отгрузок партнера за выбранный период.
PREPARE partner_sales_history (INTEGER, DATE, DATE) AS
SELECT
    pr.company_name,
    p.product_name,
    s.sale_date,
    s.quantity,
    s.unit_price,
    ROUND(s.quantity * s.unit_price, 2) AS total_amount
FROM sales AS s
JOIN partners AS pr ON pr.partner_id = s.partner_id
JOIN products AS p ON p.product_id = s.product_id
WHERE s.partner_id = $1
  AND s.sale_date BETWEEN $2 AND $3
ORDER BY s.sale_date, p.product_name;

EXECUTE partner_sales_history(1, '2026-03-01', '2026-03-31');
DEALLOCATE partner_sales_history;
