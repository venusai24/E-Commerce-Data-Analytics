CREATE SCHEMA IF NOT EXISTS dw;

DROP TABLE IF EXISTS dw.dim_dates CASCADE;
CREATE TABLE dw.dim_dates (
    date_id INT PRIMARY KEY,
    date_actual DATE NOT NULL,
    year INT NOT NULL,
    month INT NOT NULL,
    day INT NOT NULL,
    quarter INT NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

DROP TABLE IF EXISTS dw.dim_customers CASCADE;
CREATE TABLE dw.dim_customers (
    customer_sk SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) UNIQUE NOT NULL,
    customer_unique_id VARCHAR(50) NOT NULL,
    customer_zip_code_prefix VARCHAR(10),
    customer_city VARCHAR(255),
    customer_state VARCHAR(5)
);

DROP TABLE IF EXISTS dw.dim_products CASCADE;
CREATE TABLE dw.dim_products (
    product_sk SERIAL PRIMARY KEY,
    product_id VARCHAR(50) UNIQUE NOT NULL,
    product_category_name VARCHAR(255),
    product_category_name_english VARCHAR(255),
    product_name_length NUMERIC,
    product_description_length NUMERIC,
    product_photos_qty NUMERIC,
    product_weight_g NUMERIC,
    product_length_cm NUMERIC,
    product_height_cm NUMERIC,
    product_width_cm NUMERIC
);

DROP TABLE IF EXISTS dw.dim_sellers CASCADE;
CREATE TABLE dw.dim_sellers (
    seller_sk SERIAL PRIMARY KEY,
    seller_id VARCHAR(50) UNIQUE NOT NULL,
    seller_zip_code_prefix VARCHAR(10),
    seller_city VARCHAR(255),
    seller_state VARCHAR(5)
);

DROP TABLE IF EXISTS dw.fact_orders CASCADE;
CREATE TABLE dw.fact_orders (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_sk INT REFERENCES dw.dim_customers(customer_sk),
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

DROP TABLE IF EXISTS dw.fact_order_items CASCADE;
CREATE TABLE dw.fact_order_items (
    order_id VARCHAR(50) REFERENCES dw.fact_orders(order_id),
    order_item_id INT,
    product_sk INT REFERENCES dw.dim_products(product_sk),
    seller_sk INT REFERENCES dw.dim_sellers(seller_sk),
    shipping_limit_date TIMESTAMP,
    price NUMERIC(12,2),
    freight_value NUMERIC(12,2),
    dq_price_outlier BOOLEAN,
    dq_freight_outlier BOOLEAN,
    PRIMARY KEY (order_id, order_item_id)
);

DROP TABLE IF EXISTS dw.fact_order_payments CASCADE;
CREATE TABLE dw.fact_order_payments (
    order_id VARCHAR(50) REFERENCES dw.fact_orders(order_id),
    payment_sequential INT,
    payment_type VARCHAR(50),
    payment_installments INT,
    payment_value NUMERIC(12,2),
    dq_zero_payment BOOLEAN,
    PRIMARY KEY (order_id, payment_sequential)
);

DROP TABLE IF EXISTS dw.fact_order_reviews CASCADE;
CREATE TABLE dw.fact_order_reviews (
    review_id VARCHAR(50),
    order_id VARCHAR(50) REFERENCES dw.fact_orders(order_id),
    review_score INT,
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date TIMESTAMP,
    review_answer_timestamp TIMESTAMP,
    PRIMARY KEY (order_id)
);
