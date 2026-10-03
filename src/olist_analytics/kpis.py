import sqlalchemy
from pathlib import Path
from sqlalchemy import text
from .db import get_engine, run_sql_file

def build_kpis_views():
    try:
        engine = get_engine()
        with engine.connect() as conn:
            pass
    except (sqlalchemy.exc.OperationalError, ValueError):
        print("Database connection failed. To run `build-kpis`, please ensure Postgres is running.")
        return

    sql_dir = Path("sql")
    print("Building KPI Views...")
    run_sql_file(sql_dir / "04_kpi_ddl.sql")
    
    # Run DQ checks X4 and X5
    with engine.connect() as conn:
        res = conn.execute(text("""
            SELECT 
                COUNT(*) as total, 
                SUM(CASE WHEN order_status = 'delivered' THEN 1 ELSE 0 END) as delivered 
            FROM dw.fact_orders
        """)).fetchone()
        
        if res and res.total > 0:
            completion_rate = res.delivered / res.total
            print(f"[X4 Check] Order completion rate: {completion_rate:.2%}")
            if completion_rate < 0.90:
                print("WARN: Order completion rate is below 90%!")
                
        res_items = conn.execute(text("""
            SELECT SUM(price + freight_value) FROM dw.fact_order_items
        """)).scalar() or 0
        
        res_payments = conn.execute(text("""
            SELECT SUM(payment_value) FROM dw.fact_order_payments
        """)).scalar() or 0
        
        diff = abs(res_payments - res_items)
        pct_diff = diff / res_payments if res_payments > 0 else 0
        print(f"[X5 Check] Total Payments: {res_payments:.2f} | Total Items (w/ freight): {res_items:.2f} | Diff: {pct_diff:.2%}")
        
        if pct_diff > 0.05:
            print("WARN: Revenue reconciliation differs by more than 5%!")

    print("KPIs built successfully.")
