\set ON_ERROR_STOP on

BEGIN;

TRUNCATE TABLE sales, products, partners RESTART IDENTITY;

\copy partners (partner_id, company_name, inn, contact_email, phone, rating) FROM 'import_partners_clean.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8', NULL '');

CREATE TEMP TABLE tmp_sales (
    sale_id INTEGER,
    partner_id INTEGER,
    product_name VARCHAR(255),
    sale_date DATE,
    quantity INTEGER,
    source_total_amount DECIMAL(14, 2)
);

\copy tmp_sales (sale_id, partner_id, product_name, sale_date, quantity, source_total_amount) FROM 'import_sales_clean.txt' WITH (FORMAT csv, HEADER true, DELIMITER E'\t', ENCODING 'UTF8', NULL '');

INSERT INTO products (product_name, unit)
SELECT
    product_name,
    'шт.'
FROM tmp_sales
GROUP BY product_name
ORDER BY product_name;

INSERT INTO sales (
    sale_id,
    partner_id,
    product_id,
    sale_date,
    quantity,
    unit_price
)
SELECT
    s.sale_id,
    s.partner_id,
    p.product_id,
    s.sale_date,
    s.quantity,
    ROUND(s.source_total_amount / s.quantity, 4)
FROM tmp_sales AS s
JOIN partners AS pr ON pr.partner_id = s.partner_id
JOIN products AS p ON p.product_name = s.product_name
ORDER BY s.sale_id;

SELECT setval(
    pg_get_serial_sequence('partners', 'partner_id'),
    (SELECT MAX(partner_id) FROM partners),
    true
);

SELECT setval(
    pg_get_serial_sequence('products', 'product_id'),
    (SELECT MAX(product_id) FROM products),
    true
);

SELECT setval(
    pg_get_serial_sequence('sales', 'sale_id'),
    (SELECT MAX(sale_id) FROM sales),
    true
);

COMMIT;

SELECT 'partners' AS table_name, COUNT(*) AS row_count FROM partners
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'sales', COUNT(*) FROM sales;
