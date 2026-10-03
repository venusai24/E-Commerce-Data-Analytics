import pandas as pd
from pathlib import Path
from .db import get_engine
from .config import settings

def generate_report():
    try:
        engine = get_engine()
        with engine.connect() as conn:
            pass
    except Exception as e:
        print("Database connection failed. Cannot generate report.")
        return
        
    reports_dir = Path(settings["paths"]["reports_dir"])
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = reports_dir / "olist_final_report.xlsx"
    print(f"Generating Excel report at {report_path}...")
    
    with pd.ExcelWriter(report_path, engine="xlsxwriter") as writer:
        df_rev = pd.read_sql("SELECT * FROM kpi.monthly_revenue", engine)
        df_rev.to_excel(writer, sheet_name="Monthly Revenue", index=False)
        
        df_del = pd.read_sql("SELECT * FROM kpi.delivery_performance", engine)
        df_del.to_excel(writer, sheet_name="Delivery Perf", index=False)
        
        df_sell = pd.read_sql("SELECT * FROM kpi.seller_performance", engine)
        df_sell.to_excel(writer, sheet_name="Seller Perf", index=False)
        
    print("Report generation complete.")
