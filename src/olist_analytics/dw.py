from pathlib import Path
import sqlalchemy
from .db import get_engine, run_sql_file

def build_dimensional_warehouse():
    sql_dir = Path("sql")
    try:
        engine = get_engine()
        # Test connection
        with engine.connect() as conn:
            pass
    except (sqlalchemy.exc.OperationalError, ValueError):
        print("Database connection failed. To run `build-warehouse`, please ensure Postgres is running.")
        return

    print("Building Dimensional Warehouse DDL...")
    run_sql_file(sql_dir / "02_dw_ddl.sql")
    
    print("Executing ELT to populate DW...")
    run_sql_file(sql_dir / "03_dw_etl.sql")
    
    print("Dimensional Warehouse built successfully.")
