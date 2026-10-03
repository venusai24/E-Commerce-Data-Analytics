import json
from pathlib import Path
from olist_analytics.cleaning import (
    clean_customers, clean_geolocation, clean_orders,
    clean_order_items, clean_payments, clean_reviews,
    clean_products, clean_sellers
)
from olist_analytics.ingest import EXPECTED_FILES, DTYPES
import pandas as pd

def test_cleaning_on_fixture():
    fixture_dir = Path("tests/fixtures/generated")
    if not fixture_dir.exists():
        return
        
    with open(fixture_dir / "defects_manifest.json") as f:
        manifest = json.load(f)
        
    dfs = {}
    for key, filename in EXPECTED_FILES.items():
        dfs[key] = pd.read_csv(fixture_dir / filename, dtype=DTYPES[key])
        
    c_df, c_logs = clean_customers(dfs["customers"])
    assert any(log["rule_id"] == "C3" and log["rows_affected"] == manifest["C3_accented_city"] for log in c_logs)
    
    g_df, g_logs = clean_geolocation(dfs["geolocation"])
    assert any(log["rule_id"] == "G1" and log["rows_affected"] == manifest["G1_duplicates"] for log in g_logs)
    assert any(log["rule_id"] == "G2" and log["rows_affected"] == manifest["G2_out_of_brazil"] for log in g_logs)
    
    o_df, o_logs = clean_orders(dfs["orders"])
    assert any(log["rule_id"] == "O3" and log["rows_affected"] == manifest["O3_ts_sequence"] for log in o_logs)
    assert any(log["rule_id"] == "O4" and log["rows_affected"] == manifest["O4_delivered_missing_ts"] for log in o_logs)
    
    p_df, p_logs = clean_payments(dfs["order_payments"])
    assert any(log["rule_id"] == "P1" and log["rows_affected"] == manifest["P1_zero_payment"] for log in p_logs)
    assert any(log["rule_id"] == "P2" and log["rows_affected"] == manifest["P2_zero_installments"] for log in p_logs)
    assert any(log["rule_id"] == "P3" and log["rows_affected"] == manifest["P3_not_defined"] for log in p_logs)
    
    r_df, r_logs = clean_reviews(dfs["order_reviews"])
    assert any(log["rule_id"] == "R1" and log["rows_affected"] == manifest["R1_duplicate_reviews"] for log in r_logs)
    
    pr_df, pr_logs = clean_products(dfs["products"])
    assert any(log["rule_id"] == "PR1" and log["rows_affected"] == manifest["PR1_null_category"] for log in pr_logs)
    
    i_df, i_logs = clean_order_items(dfs["order_items"])
    assert any(log["rule_id"] == "I3" and log["rows_affected"] == manifest["I3_price_outlier"] for log in i_logs)
