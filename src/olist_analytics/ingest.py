import pandas as pd
from pathlib import Path
from typing import Dict
from .config import settings

EXPECTED_FILES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "translation": "product_category_name_translation.csv"
}

# IDs and zips as strings
DTYPES = {
    "customers": {"customer_id": str, "customer_unique_id": str, "customer_zip_code_prefix": str},
    "geolocation": {"geolocation_zip_code_prefix": str},
    "order_items": {"order_id": str, "order_item_id": str, "product_id": str, "seller_id": str},
    "order_payments": {"order_id": str},
    "order_reviews": {"review_id": str, "order_id": str},
    "orders": {"order_id": str, "customer_id": str},
    "products": {"product_id": str},
    "sellers": {"seller_id": str, "seller_zip_code_prefix": str},
    "translation": {}
}

def verify_and_load_raw_data() -> Dict[str, pd.DataFrame]:
    raw_dir = Path(settings["paths"]["raw_dir"])
    missing_files = []
    
    for key, filename in EXPECTED_FILES.items():
        if not (raw_dir / filename).exists():
            missing_files.append(filename)
            
    if missing_files:
        msg = (
            f"Missing {len(missing_files)} files in {raw_dir}: {', '.join(missing_files)}.\n"
            "Please download the dataset from Kaggle: "
            "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce\n"
            "Place the unzipped CSVs into the data/raw/ directory."
        )
        raise FileNotFoundError(msg)
        
    dataframes = {}
    for key, filename in EXPECTED_FILES.items():
        df = pd.read_csv(raw_dir / filename, dtype=DTYPES[key])
        dataframes[key] = df
        
    return dataframes
