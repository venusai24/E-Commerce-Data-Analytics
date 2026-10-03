import json
import pandas as pd
import numpy as np
from pathlib import Path
from .ingest import verify_and_load_raw_data
from .config import settings

APPROX_ROW_COUNTS = {
    "customers": 99441,
    "geolocation": 1000000,
    "order_items": 112650,
    "order_payments": 103886,
    "order_reviews": 99224,
    "orders": 99441,
    "products": 32951,
    "sellers": 3095,
    "translation": 71
}

def profile_data():
    dfs = verify_and_load_raw_data()
    reports_dir = Path(settings["paths"]["reports_dir"]) / "profile"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    summary = {}
    
    print(f"{'Table':<15} | {'Observed rows':<15} | {'Expected rows':<15} | {'Status'}")
    print("-" * 60)
    
    for name, df in dfs.items():
        obs_rows = len(df)
        exp_rows = APPROX_ROW_COUNTS[name]
        diff_pct = abs(obs_rows - exp_rows) / exp_rows * 100
        status = "WARN" if diff_pct > 5 else "PASS"
        print(f"{name:<15} | {obs_rows:<15} | {exp_rows:<15} | {status}")
        
        table_summary = {
            "row_count": obs_rows,
            "columns": {}
        }
        
        md_lines = [f"# Profile: {name}", "", f"Total Rows: {obs_rows}", "", "## Columns", ""]
        
        for col in df.columns:
            col_data = df[col]
            n_nulls = int(col_data.isnull().sum())
            null_pct = round(n_nulls / obs_rows * 100, 2) if obs_rows > 0 else 0
            n_unique = int(col_data.nunique())
            
            col_summary = {
                "dtype": str(col_data.dtype),
                "null_count": n_nulls,
                "null_pct": null_pct,
                "n_unique": n_unique
            }
            
            md_lines.extend([
                f"### `{col}`",
                f"- Type: `{col_data.dtype}`",
                f"- Nulls: {n_nulls} ({null_pct}%)",
                f"- Unique values: {n_unique}"
            ])
            
            if pd.api.types.is_numeric_dtype(col_data):
                col_summary["min"] = float(col_data.min()) if not pd.isna(col_data.min()) else None
                col_summary["max"] = float(col_data.max()) if not pd.isna(col_data.max()) else None
                md_lines.append(f"- Min: {col_summary['min']}")
                md_lines.append(f"- Max: {col_summary['max']}")
                
                if col in ["price", "freight_value", "payment_value", "review_score"]:
                    col_summary["mean"] = float(col_data.mean()) if not pd.isna(col_data.mean()) else None
                    col_summary["median"] = float(col_data.median()) if not pd.isna(col_data.median()) else None
                    col_summary["std"] = float(col_data.std()) if not pd.isna(col_data.std()) else None
                    col_summary["skew"] = float(col_data.skew()) if not pd.isna(col_data.skew()) else None
                    
                    md_lines.extend([
                        f"- Mean: {col_summary['mean']}",
                        f"- Median: {col_summary['median']}",
                        f"- Std: {col_summary['std']}",
                        f"- Skew: {col_summary['skew']}"
                    ])
                    
            if n_unique < 20:
                top_values = col_data.value_counts(dropna=False).head(5).to_dict()
                col_summary["top_values"] = {str(k): int(v) for k, v in top_values.items()}
                md_lines.append("- Top values:")
                for k, v in col_summary["top_values"].items():
                    md_lines.append(f"  - `{k}`: {v}")
                    
            table_summary["columns"][col] = col_summary
            md_lines.append("")
            
        summary[name] = table_summary
        
        with open(reports_dir / f"{name}.md", "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))
            
    with open(reports_dir / "profile_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

if __name__ == "__main__":
    profile_data()
