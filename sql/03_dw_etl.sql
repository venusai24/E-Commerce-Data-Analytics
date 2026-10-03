-- Dimensions
INSERT INTO dw.dim_customers (
    customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state
)
SELECT 
    customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state
FROM stg.customers
ON CONFLICT (customer_id) DO NOTHING;

INSERT INTO dw.dim_products (
    product_id, product_category_name, product_category_name_english,
    product_name_length, product_description_length, product_photos_qty,
    product_weight_g, product_length_cm, product_height_cm, product_width_cm
)
SELECT 
    p.product_id, p.product_category_name, 
    COALESCE(t.product_category_name_english, p.product_category_name) as product_category_name_english,
    p.product_name_length, p.product_description_length, p.product_photos_qty,
    p.product_weight_g, p.product_length_cm, p.product_height_cm, p.product_width_cm
FROM stg.products p
LEFT JOIN stg.translation t ON p.product_category_name = t.product_category_name
ON CONFLICT (product_id) DO NOTHING;

INSERT INTO dw.dim_sellers (
    seller_id, seller_zip_code_prefix, seller_city, seller_state
)
SELECT 
    seller_id, seller_zip_code_prefix, seller_city, seller_state
FROM stg.sellers
ON CONFLICT (seller_id) DO NOTHING;

-- Populate dim_dates
INSERT INTO dw.dim_dates (date_id, date_actual, year, month, day, quarter, is_weekend)
SELECT 
    EXTRACT(YEAR FROM d)*10000 + EXTRACT(MONTH FROM d)*100 + EXTRACT(DAY FROM d) AS date_id,
    d::DATE AS date_actual,
    EXTRACT(YEAR FROM d) AS year,
    EXTRACT(MONTH FROM d) AS month,
    EXTRACT(DAY FROM d) AS day,
    EXTRACT(QUARTER FROM d) AS quarter,
    EXTRACT(DOW FROM d) IN (0, 6) AS is_weekend
FROM generate_series('2016-01-01'::timestamp, '2020-12-31'::timestamp, '1 day'::interval) d
ON CONFLICT DO NOTHING;

-- Facts
INSERT INTO dw.fact_orders
SELECT 
    o.order_id, c.customer_sk, o.order_status, o.order_purchase_timestamp,
    o.order_approved_at, o.order_delivered_carrier_date, o.order_delivered_customer_date,
    o.order_estimated_delivery_date, o.dq_ts_sequence_anomaly, o.dq_delivered_missing_ts,
    o.dq_status_ts_conflict
FROM stg.orders o
JOIN dw.dim_customers c ON o.customer_id = c.customer_id
ON CONFLICT (order_id) DO NOTHING;

INSERT INTO dw.fact_order_items
SELECT 
    i.order_id, i.order_item_id, p.product_sk, s.seller_sk, i.shipping_limit_date,
    i.price, i.freight_value, i.dq_price_outlier, i.dq_freight_outlier
FROM stg.order_items i
JOIN dw.dim_products p ON i.product_id = p.product_id
JOIN dw.dim_sellers s ON i.seller_id = s.seller_id
ON CONFLICT (order_id, order_item_id) DO NOTHING;

INSERT INTO dw.fact_order_payments
SELECT * FROM stg.order_payments
ON CONFLICT (order_id, payment_sequential) DO NOTHING;

INSERT INTO dw.fact_order_reviews
SELECT * FROM stg.order_reviews
ON CONFLICT (order_id) DO NOTHING;
