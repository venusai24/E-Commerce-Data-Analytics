import pandas as pd
import numpy as np
import unicodedata
from typing import Tuple, List
from pathlib import Path
from .config import settings

def log_cleaning(rule_id: str, table_name: str, rows_affected: int, action: str) -> dict:
    return {
        "rule_id": rule_id,
        "table_name": table_name,
        "rows_affected": int(rows_affected),
        "action": action
    }

def clean_customers(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[dict]]:
    logs = []
    df["customer_zip_code_prefix"] = df["customer_zip_code_prefix"].astype(str).str.zfill(5)
    def normalize_str(s):
        if pd.isna(s): return s
        s = str(s).strip().lower()
        return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    
    orig_city = df["customer_city"].copy()
    df["customer_city"] = df["customer_city"].apply(normalize_str)
    affected_c3 = (orig_city != df["customer_city"]).sum()
    if affected_c3 > 0:
        logs.append(log_cleaning("C3", "customers", affected_c3, "FIX"))
        
    df["customer_state"] = df["customer_state"].str.upper()
    return df, logs

def clean_geolocation(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[dict]]:
    logs = []
    df["geolocation_zip_code_prefix"] = df["geolocation_zip_code_prefix"].astype(str).str.zfill(5)
    
    initial_rows = len(df)
    df = df.drop_duplicates().copy()
    affected_g1 = initial_rows - len(df)
    if affected_g1 > 0:
        logs.append(log_cleaning("G1", "geolocation", affected_g1, "DROP"))
        
    bbox = settings["cleaning"]["brazil_bbox"]
    is_out = (df["geolocation_lat"] < bbox["lat_min"]) | (df["geolocation_lat"] > bbox["lat_max"]) | \
             (df["geolocation_lng"] < bbox["lng_min"]) | (df["geolocation_lng"] > bbox["lng_max"])
    
    df["dq_out_of_bounds"] = is_out
    affected_g2 = is_out.sum()
    if affected_g2 > 0:
        logs.append(log_cleaning("G2", "geolocation", affected_g2, "FLAG"))
        
    valid_df = df[~df["dq_out_of_bounds"]]
    
    def mode_or_first(s):
        m = s.mode()
        return m.iloc[0] if not m.empty else s.iloc[0]
        
    collapsed = valid_df.groupby("geolocation_zip_code_prefix").agg(
        geolocation_lat=("geolocation_lat", "median"),
        geolocation_lng=("geolocation_lng", "median"),
        geolocation_city=("geolocation_city", mode_or_first),
        geolocation_state=("geolocation_state", mode_or_first)
    ).reset_index()
    
    logs.append(log_cleaning("G3", "geolocation", len(df), "FIX"))
    return collapsed, logs

def clean_orders(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[dict]]:
    logs = []
    ts_cols = [
        "order_purchase_timestamp", "order_approved_at", 
        "order_delivered_carrier_date", "order_delivered_customer_date", 
        "order_estimated_delivery_date"
    ]
    for col in ts_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce")
        
    seq_anomaly = (df["order_purchase_timestamp"] > df["order_approved_at"]) | \
                  (df["order_approved_at"] > df["order_delivered_carrier_date"]) | \
                  (df["order_delivered_carrier_date"] > df["order_delivered_customer_date"])
    df["dq_ts_sequence_anomaly"] = seq_anomaly
    affected_o3 = seq_anomaly.sum()
    if affected_o3 > 0:
        logs.append(log_cleaning("O3", "orders", affected_o3, "FLAG"))
        
    del_missing_ts = (df["order_status"] == "delivered") & df["order_delivered_customer_date"].isna()
    df["dq_delivered_missing_ts"] = del_missing_ts
    affected_o4 = del_missing_ts.sum()
    if affected_o4 > 0:
        logs.append(log_cleaning("O4", "orders", affected_o4, "FLAG"))
        
    non_del_has_ts = (df["order_status"] != "delivered") & df["order_delivered_customer_date"].notna()
    df["dq_status_ts_conflict"] = non_del_has_ts
    affected_o5 = non_del_has_ts.sum()
    if affected_o5 > 0:
        logs.append(log_cleaning("O5", "orders", affected_o5, "FLAG"))
        
    return df, logs

def clean_order_items(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[dict]]:
    logs = []
    df["shipping_limit_date"] = pd.to_datetime(df["shipping_limit_date"], errors="coerce")
    
    iqr_mult = settings["stats"]["outliers"]["iqr_multiplier"]
    for col, flag in [("price", "dq_price_outlier"), ("freight_value", "dq_freight_outlier")]:
        log_val = np.log1p(df[col])
        q1, q3 = log_val.quantile(0.25), log_val.quantile(0.75)
        iqr = q3 - q1
        upper = q3 + iqr_mult * iqr
        is_outlier = log_val > upper
        df[flag] = is_outlier
        affected = is_outlier.sum()
        if affected > 0:
            logs.append(log_cleaning("I3", "order_items", affected, "FLAG"))
            
    return df, logs

def clean_payments(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[dict]]:
    logs = []
    zero_val = df["payment_value"] == 0
    df["dq_zero_payment"] = zero_val
    affected_p1 = zero_val.sum()
    if affected_p1 > 0:
        logs.append(log_cleaning("P1", "order_payments", affected_p1, "FLAG"))
        
    zero_inst = df["payment_installments"] == 0
    df.loc[zero_inst, "payment_installments"] = np.nan
    affected_p2 = zero_inst.sum()
    if affected_p2 > 0:
        logs.append(log_cleaning("P2", "order_payments", affected_p2, "FIX"))
        
    not_def = df["payment_type"] == "not_defined"
    affected_p3 = not_def.sum()
    if affected_p3 > 0:
        logs.append(log_cleaning("P3", "order_payments", affected_p3, "FLAG"))
        
    return df, logs

def clean_reviews(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[dict]]:
    logs = []
    df["review_creation_date"] = pd.to_datetime(df["review_creation_date"], errors="coerce")
    df["review_answer_timestamp"] = pd.to_datetime(df["review_answer_timestamp"], errors="coerce")
    
    initial_rows = len(df)
    df = df.sort_values(
        by=["order_id", "review_answer_timestamp", "review_creation_date", "review_id"],
        ascending=[True, False, False, False]
    )
    df = df.drop_duplicates(subset=["order_id"], keep="first")
    affected_r1 = initial_rows - len(df)
    if affected_r1 > 0:
        logs.append(log_cleaning("R1", "order_reviews", affected_r1, "FIX"))
        
    return df, logs

def clean_products(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[dict]]:
    logs = []
    df = df.rename(columns={
        "product_name_lenght": "product_name_length",
        "product_description_lenght": "product_description_length"
    })
    
    null_cat = df["product_category_name"].isna()
    df.loc[null_cat, "product_category_name"] = "unknown"
    affected_pr1 = null_cat.sum()
    if affected_pr1 > 0:
        logs.append(log_cleaning("PR1", "products", affected_pr1, "FIX"))
        
    return df, logs

def clean_sellers(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[dict]]:
    logs = []
    df["seller_zip_code_prefix"] = df["seller_zip_code_prefix"].astype(str).str.zfill(5)
    def normalize_str(s):
        if pd.isna(s): return s
        s = str(s).strip().lower()
        return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    df["seller_city"] = df["seller_city"].apply(normalize_str)
    return df, logs

def clean_all_data():
    from .ingest import verify_and_load_raw_data
    
    dfs = verify_and_load_raw_data()
    all_logs = []
    
    cleaners = {
        "customers": clean_customers,
        "geolocation": clean_geolocation,
        "orders": clean_orders,
        "order_items": clean_order_items,
        "order_payments": clean_payments,
        "order_reviews": clean_reviews,
        "products": clean_products,
        "sellers": clean_sellers,
        "translation": lambda df: (df, [])
    }
    
    cleaned_dfs = {}
    for name, df in dfs.items():
        cleaned_df, logs = cleaners[name](df)
        cleaned_dfs[name] = cleaned_df
        all_logs.extend(logs)
        
    from .validation import validate_and_report
    validate_and_report(cleaned_dfs, all_logs)
    
    stg_dir = Path(settings["paths"]["interim_dir"])
    stg_dir.mkdir(parents=True, exist_ok=True)
    
    for name, df in cleaned_dfs.items():
        df.to_parquet(stg_dir / f"{name}.parquet", index=False)
        
    print(f"Cleaned {len(cleaned_dfs)} tables and saved to {stg_dir}")
