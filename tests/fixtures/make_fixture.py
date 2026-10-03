import argparse
import json
import os
import random
import pandas as pd
import numpy as np
from pathlib import Path

def generate_fixtures(out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    random.seed(42)
    np.random.seed(42)

    # 1. Customers
    customers = pd.DataFrame({
        "customer_id": [f"c_id_{i}" for i in range(1, 601)],
        "customer_unique_id": [f"c_uid_{i}" for i in range(1, 601)],
        "customer_zip_code_prefix": ["01001" if i % 10 == 0 else f"{10000+i}" for i in range(1, 601)],
        "customer_city": ["são paulo" if i == 1 else "campinas" for i in range(1, 601)],
        "customer_state": ["SP"] * 600
    })

    # 2. Geolocation
    geo = pd.DataFrame({
        "geolocation_zip_code_prefix": ["01001", "01001", "10001", "99999"],
        "geolocation_lat": [-23.5, -23.5, -23.5, 45.0],
        "geolocation_lng": [-46.6, -46.6, -46.6, -100.0],
        "geolocation_city": ["sao paulo", "sao paulo", "campinas", "new york"],
        "geolocation_state": ["SP", "SP", "SP", "NY"]
    })

    # 3. Orders
    order_ids = [f"o_id_{i}" for i in range(1, 601)]
    status = ["delivered"] * 590 + ["canceled"] * 10
    
    purchase_dates = ["2017-05-01 10:00:00"] * 600
    purchase_dates[-1] = "2016-10-01 10:00:00" # out of window
    
    orders = pd.DataFrame({
        "order_id": order_ids,
        "customer_id": customers["customer_id"].values,
        "order_status": status,
        "order_purchase_timestamp": purchase_dates,
        "order_approved_at": ["2017-05-01 11:00:00"] * 600,
        "order_delivered_carrier_date": ["2017-05-02 10:00:00"] * 600,
        "order_delivered_customer_date": ["2017-05-05 10:00:00"] * 600,
        "order_estimated_delivery_date": ["2017-05-10 10:00:00"] * 600
    })
    orders.loc[1, "order_approved_at"] = "2017-04-30 10:00:00" # O3
    orders.loc[2, "order_delivered_customer_date"] = np.nan # O4

    # 4. Order Items
    items = []
    for i in range(1, 601):
        if i == 4:
            continue # O6
        items.append({
            "order_id": f"o_id_{i}",
            "order_item_id": "1",
            "product_id": f"p_id_{i % 10}",
            "seller_id": "s_id_1",
            "shipping_limit_date": "2017-05-05 10:00:00",
            "price": 10000.0 if i == 5 else 50.0, # I3
            "freight_value": 15.0
        })
    order_items = pd.DataFrame(items)

    # 5. Payments
    payments = []
    for i in range(1, 601):
        payments.append({
            "order_id": f"o_id_{i}",
            "payment_sequential": 1,
            "payment_type": "not_defined" if i == 6 else "credit_card",
            "payment_installments": 0 if i == 7 else 1,
            "payment_value": 0.0 if i == 8 else 65.0
        })
    order_payments = pd.DataFrame(payments)

    # 6. Reviews
    reviews = []
    for i in range(1, 601):
        reviews.append({
            "review_id": f"r_id_{i}",
            "order_id": f"o_id_{i}",
            "review_score": 5,
            "review_comment_title": "Good",
            "review_comment_message": "Good",
            "review_creation_date": "2017-05-06 00:00:00",
            "review_answer_timestamp": "2017-05-07 10:00:00"
        })
    reviews.append({
            "review_id": "r_id_9", 
            "order_id": "o_id_9",
            "review_score": 1,
            "review_comment_title": "Bad",
            "review_comment_message": "Bad",
            "review_creation_date": "2017-05-06 00:00:00",
            "review_answer_timestamp": "2017-05-08 10:00:00"
    })
    order_reviews = pd.DataFrame(reviews)

    # 7. Products
    products = pd.DataFrame({
        "product_id": [f"p_id_{i}" for i in range(10)],
        "product_category_name": ["esporte_lazer"] * 8 + [np.nan, "pc_gamer"],
        "product_name_lenght": [50] * 10,
        "product_description_lenght": [500] * 10,
        "product_photos_qty": [1] * 10,
        "product_weight_g": [200] * 10,
        "product_length_cm": [20] * 10,
        "product_height_cm": [20] * 10,
        "product_width_cm": [20] * 10
    })

    # 8. Sellers
    sellers = pd.DataFrame({
        "seller_id": ["s_id_1"],
        "seller_zip_code_prefix": ["01001"],
        "seller_city": ["sao paulo"],
        "seller_state": ["SP"]
    })

    # 9. Translation
    translation = pd.DataFrame({
        "product_category_name": ["esporte_lazer"],
        "product_category_name_english": ["sports_leisure"]
    })

    customers.to_csv(out_dir / "olist_customers_dataset.csv", index=False)
    geo.to_csv(out_dir / "olist_geolocation_dataset.csv", index=False)
    orders.to_csv(out_dir / "olist_orders_dataset.csv", index=False)
    order_items.to_csv(out_dir / "olist_order_items_dataset.csv", index=False)
    order_payments.to_csv(out_dir / "olist_order_payments_dataset.csv", index=False)
    order_reviews.to_csv(out_dir / "olist_order_reviews_dataset.csv", index=False)
    products.to_csv(out_dir / "olist_products_dataset.csv", index=False)
    sellers.to_csv(out_dir / "olist_sellers_dataset.csv", index=False)
    translation.to_csv(out_dir / "product_category_name_translation.csv", index=False)

    manifest = {
        "G1_duplicates": 1,
        "G2_out_of_brazil": 1,
        "O3_ts_sequence": 1,
        "O4_delivered_missing_ts": 1,
        "O6_no_items": 1,
        "P1_zero_payment": 1,
        "P2_zero_installments": 1,
        "P3_not_defined": 1,
        "R1_duplicate_reviews": 1,
        "PR1_null_category": 1,
        "PR2_untranslated": 1,
        "I3_price_outlier": 1,
        "C2_invalid_uf_or_zip": 0,
        "C3_accented_city": 1,
        "X1_loss_pct": 0
    }
    with open(out_dir / "defects_manifest.json", "w") as f:
        json.dump(manifest, f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    generate_fixtures(args.out)
