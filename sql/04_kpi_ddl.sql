CREATE SCHEMA IF NOT EXISTS kpi;

-- 8.1 Monthly Revenue
DROP VIEW IF EXISTS kpi.monthly_revenue CASCADE;
CREATE VIEW kpi.monthly_revenue AS
SELECT 
    d.year,
    d.month,
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(DISTINCT o.customer_sk) AS unique_customers,
    SUM(i.price) AS total_item_revenue,
    SUM(i.freight_value) AS total_freight_revenue
FROM dw.fact_orders o
JOIN dw.dim_dates d ON d.date_actual = o.order_purchase_timestamp::DATE
LEFT JOIN dw.fact_order_items i ON o.order_id = i.order_id
WHERE o.order_status NOT IN ('canceled', 'unavailable')
GROUP BY d.year, d.month
ORDER BY d.year, d.month;

-- 8.2 Delivery Performance
DROP VIEW IF EXISTS kpi.delivery_performance CASCADE;
CREATE VIEW kpi.delivery_performance AS
SELECT 
    d.year,
    d.month,
    COUNT(o.order_id) AS delivered_orders,
    AVG(EXTRACT(EPOCH FROM (o.order_delivered_customer_date - o.order_purchase_timestamp))/86400.0) AS avg_days_to_deliver,
    SUM(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1 ELSE 0 END) * 100.0 / COUNT(o.order_id) AS pct_late_deliveries
FROM dw.fact_orders o
JOIN dw.dim_dates d ON d.date_actual = o.order_purchase_timestamp::DATE
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY d.year, d.month
ORDER BY d.year, d.month;

-- 8.3 Seller Performance
DROP VIEW IF EXISTS kpi.seller_performance CASCADE;
CREATE VIEW kpi.seller_performance AS
SELECT 
    s.seller_id,
    s.seller_city,
    s.seller_state,
    COUNT(DISTINCT i.order_id) AS total_orders_fulfilled,
    SUM(i.price) AS total_revenue,
    AVG(r.review_score) AS avg_review_score
FROM dw.dim_sellers s
JOIN dw.fact_order_items i ON s.seller_sk = i.seller_sk
JOIN dw.fact_orders o ON i.order_id = o.order_id
LEFT JOIN dw.fact_order_reviews r ON o.order_id = r.order_id
WHERE o.order_status NOT IN ('canceled', 'unavailable')
GROUP BY s.seller_id, s.seller_city, s.seller_state;
