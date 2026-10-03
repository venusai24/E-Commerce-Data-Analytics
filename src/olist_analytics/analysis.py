import pandas as pd
from pathlib import Path
from sqlalchemy import text
from .config import settings
from .db import get_engine

def get_top_bottom_categories(engine):
    query = """
    SELECT 
        p.product_category_name_english as category,
        COUNT(DISTINCT i.order_id) as order_volume,
        SUM(i.price) as total_revenue
    FROM dw.fact_order_items i
    JOIN dw.dim_products p ON i.product_sk = p.product_sk
    GROUP BY p.product_category_name_english
    HAVING COUNT(DISTINCT i.order_id) >= 100
    """
    df = pd.read_sql(query, engine)
    return df.sort_values('total_revenue', ascending=False)

def get_geo_delivery_hotspots(engine):
    query = """
    SELECT 
        c.customer_state,
        c.customer_city,
        AVG(EXTRACT(EPOCH FROM (o.order_delivered_customer_date - o.order_purchase_timestamp))/86400.0) AS avg_delivery_days,
        COUNT(o.order_id) as volume
    FROM dw.fact_orders o
    JOIN dw.dim_customers c ON o.customer_sk = c.customer_sk
    WHERE o.order_delivered_customer_date IS NOT NULL
    GROUP BY c.customer_state, c.customer_city
    HAVING COUNT(o.order_id) >= 50
    """
    df = pd.read_sql(query, engine)
    return df.sort_values('avg_delivery_days', ascending=False)

def get_cohort_retention(engine):
    query = """
    WITH first_purchase AS (
        SELECT c.customer_unique_id, 
               DATE_TRUNC('month', MIN(o.order_purchase_timestamp)) as cohort_month
        FROM dw.fact_orders o
        JOIN dw.dim_customers c ON o.customer_sk = c.customer_sk
        GROUP BY c.customer_unique_id
    ),
    purchases AS (
        SELECT c.customer_unique_id, 
               DATE_TRUNC('month', o.order_purchase_timestamp) as purchase_month
        FROM dw.fact_orders o
        JOIN dw.dim_customers c ON o.customer_sk = c.customer_sk
    )
    SELECT 
        f.cohort_month,
        p.purchase_month,
        COUNT(DISTINCT p.customer_unique_id) as customers
    FROM purchases p
    JOIN first_purchase f ON p.customer_unique_id = f.customer_unique_id
    GROUP BY f.cohort_month, p.purchase_month
    ORDER BY f.cohort_month, p.purchase_month
    """
    df = pd.read_sql(query, engine)
    return df

def run_analysis():
    try:
        engine = get_engine()
        with engine.connect() as conn:
            pass
    except Exception as e:
        print("Database connection failed. Cannot run analysis.")
        return None

    reports_dir = Path(settings["paths"]["reports_dir"])
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    print("Running Top/Bottom Categories analysis...")
    cat_df = get_top_bottom_categories(engine)
    cat_df.to_csv(reports_dir / "top_categories.csv", index=False)
    
    print("Running Geographic Delivery Hotspots analysis...")
    geo_df = get_geo_delivery_hotspots(engine)
    geo_df.to_csv(reports_dir / "geo_hotspots.csv", index=False)
    
    print("Running Cohort Retention analysis...")
    cohort_df = get_cohort_retention(engine)
    cohort_df.to_csv(reports_dir / "cohort_retention.csv", index=False)
    
    print(f"Analysis saved to {reports_dir}")
