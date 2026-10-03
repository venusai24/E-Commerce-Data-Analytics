import pandas as pd
from pathlib import Path
from sqlalchemy import text
from .config import settings
from .db import get_engine

def load_staging_tables():
    engine = get_engine()
    stg_dir = Path(settings["paths"]["interim_dir"])
    
    tables = [
        "customers", "geolocation", "orders", "order_items", 
        "order_payments", "order_reviews", "products", "sellers", "translation"
    ]
    
    loaded = {}
    with engine.begin() as conn:
        for t in tables:
            pq_file = stg_dir / f"{t}.parquet"
            if pq_file.exists():
                df = pd.read_parquet(pq_file)
                df.to_sql(t, con=conn, schema="stg", if_exists="append", index=False)
                loaded[t] = len(df)
            else:
                print(f"Warning: {pq_file} not found.")
                
    # X3 Reconciliation check
    with engine.connect() as conn:
        res = conn.execute(text("SELECT COUNT(*) FROM stg.orders")).scalar()
        res_items = conn.execute(text("SELECT COUNT(DISTINCT order_id) FROM stg.order_items")).scalar()
        print(f"[X3 Check] Total orders: {res}, Orders with items: {res_items}")
        diff = res - res_items
        if diff > 1000:
            print(f"WARN: High number of orders without items ({diff})")
            
    print("Loaded staging tables successfully.")
