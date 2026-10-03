CREATE SCHEMA IF NOT EXISTS stg;

DROP TABLE IF EXISTS stg.customers CASCADE;
CREATE TABLE stg.customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    customer_unique_id VARCHAR(50),
    customer_zip_code_prefix VARCHAR(10),
    customer_city VARCHAR(255),
    customer_state VARCHAR(5)
);

DROP TABLE IF EXISTS stg.geolocation CASCADE;
CREATE TABLE stg.geolocation (
    geolocation_zip_code_prefix VARCHAR(10) PRIMARY KEY,
    geolocation_lat NUMERIC,
    geolocation_lng NUMERIC,
    geolocation_city VARCHAR(255),
    geolocation_state VARCHAR(5)
);

DROP TABLE IF EXISTS stg.orders CASCADE;
CREATE TABLE stg.orders (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50),
    order_status VARCHAR(50),
    order_purchase_timestamp TIMESTAMP,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP,
    dq_ts_sequence_anomaly BOOLEAN,
    dq_delivered_missing_ts BOOLEAN,
    dq_status_ts_conflict BOOLEAN
);

DROP TABLE IF EXISTS stg.order_items CASCADE;
CREATE TABLE stg.order_items (
    order_id VARCHAR(50),
    order_item_id INT,
    product_id VARCHAR(50),
    seller_id VARCHAR(50),
    shipping_limit_date TIMESTAMP,
    price NUMERIC(12,2),
    freight_value NUMERIC(12,2),
    dq_price_outlier BOOLEAN,
    dq_freight_outlier BOOLEAN,
    PRIMARY KEY (order_id, order_item_id)
);

DROP TABLE IF EXISTS stg.order_payments CASCADE;
CREATE TABLE stg.order_payments (
    order_id VARCHAR(50),
    payment_sequential INT,
    payment_type VARCHAR(50),
    payment_installments INT,
    payment_value NUMERIC(12,2),
    dq_zero_payment BOOLEAN,
    PRIMARY KEY (order_id, payment_sequential)
);

DROP TABLE IF EXISTS stg.order_reviews CASCADE;
CREATE TABLE stg.order_reviews (
    review_id VARCHAR(50),
    order_id VARCHAR(50) PRIMARY KEY,
    review_score INT,
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date TIMESTAMP,
    review_answer_timestamp TIMESTAMP
);

DROP TABLE IF EXISTS stg.products CASCADE;
CREATE TABLE stg.products (
    product_id VARCHAR(50) PRIMARY KEY,
    product_category_name VARCHAR(255),
    product_name_length NUMERIC,
    product_description_length NUMERIC,
    product_photos_qty NUMERIC,
    product_weight_g NUMERIC,
    product_length_cm NUMERIC,
    product_height_cm NUMERIC,
    product_width_cm NUMERIC
);

DROP TABLE IF EXISTS stg.sellers CASCADE;
CREATE TABLE stg.sellers (
    seller_id VARCHAR(50) PRIMARY KEY,
    seller_zip_code_prefix VARCHAR(10),
    seller_city VARCHAR(255),
    seller_state VARCHAR(5)
);

DROP TABLE IF EXISTS stg.translation CASCADE;
CREATE TABLE stg.translation (
    product_category_name VARCHAR(255) PRIMARY KEY,
    product_category_name_english VARCHAR(255)
);
