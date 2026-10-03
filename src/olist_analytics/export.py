import pandas as pd
from pathlib import Path
from .db import get_engine
from .config import settings

def export_bi_tables():
    try:
        engine = get_engine()
        with engine.connect() as conn:
            pass
    except Exception as e:
        print("Database connection failed. Cannot export tables.")
        return
        
    export_dir = Path(settings["paths"]["exports_dir"])
    export_dir.mkdir(parents=True, exist_ok=True)
    
    tables_to_export = [
        "dw.fact_orders", "dw.fact_order_items", "dw.fact_order_payments",
        "dw.dim_customers", "dw.dim_products", "dw.dim_sellers",
        "kpi.monthly_revenue", "kpi.delivery_performance", "kpi.seller_performance"
    ]
    
    print("Exporting BI tables to CSV...")
    for table in tables_to_export:
        df = pd.read_sql(f"SELECT * FROM {table}", engine)
        name = table.replace(".", "_")
        df.to_csv(export_dir / f"{name}.csv", index=False)
        
    print(f"Exported {len(tables_to_export)} tables to {export_dir}")
