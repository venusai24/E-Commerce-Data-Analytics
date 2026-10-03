import sqlalchemy
from pathlib import Path
from .config import get_db_url

def get_engine():
    return sqlalchemy.create_engine(get_db_url())

def run_sql_file(engine, file_path: Path):
    with engine.begin() as conn:
        with open(file_path, "r", encoding="utf-8") as f:
            sql = f.read()
        if sql.strip():
            conn.execute(sqlalchemy.text(sql))

def run_sql_dir(engine, dir_path: Path):
    sql_files = sorted(dir_path.glob("*.sql"))
    for file_path in sql_files:
        run_sql_file(engine, file_path)
