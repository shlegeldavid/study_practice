SELECT 'partners' AS table_name, COUNT(*) AS row_count FROM partners
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'sales', COUNT(*) FROM sales;

SELECT
    partner_id,
    company_name,
    inn,
    contact_email,
    phone,
    rating
FROM partners
ORDER BY partner_id;

SELECT
    product_id,
    product_name,
    unit
FROM products
ORDER BY product_id;

SELECT
    s.sale_id,
    pr.company_name,
    p.product_name,
    s.sale_date,
    s.quantity,
    s.unit_price,
    ROUND(s.quantity * s.unit_price, 2) AS total_amount
FROM sales AS s
JOIN partners AS pr ON pr.partner_id = s.partner_id
JOIN products AS p ON p.product_id = s.product_id
ORDER BY s.sale_id;

SELECT 'orphan partner_id' AS check_name, COUNT(*) AS violations
FROM sales AS s
LEFT JOIN partners AS p ON p.partner_id = s.partner_id
WHERE p.partner_id IS NULL

UNION ALL

SELECT 'orphan product_id', COUNT(*)
FROM sales AS s
LEFT JOIN products AS p ON p.product_id = s.product_id
WHERE p.product_id IS NULL

UNION ALL

SELECT 'invalid quantity', COUNT(*)
FROM sales
WHERE quantity <= 0

UNION ALL

SELECT 'invalid rating', COUNT(*)
FROM partners
WHERE rating IS NOT NULL AND rating NOT BETWEEN 0 AND 5;
