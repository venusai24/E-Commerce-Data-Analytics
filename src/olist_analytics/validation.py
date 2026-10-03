import json
import pandas as pd
from pathlib import Path
from .config import settings

def validate_and_report(cleaned_dfs, cleaning_logs):
    # Aggregate logs by rule_id and table
    rules_summary = {}
    total_affected = 0
    
    for log in cleaning_logs:
        rule_id = log["rule_id"]
        table = log["table_name"]
        affected = log["rows_affected"]
        action = log["action"]
        
        if rule_id not in rules_summary:
            rules_summary[rule_id] = {"affected": 0, "action": action, "tables": {}}
            
        rules_summary[rule_id]["affected"] += affected
        rules_summary[rule_id]["tables"][table] = rules_summary[rule_id]["tables"].get(table, 0) + affected
        total_affected += affected
        
    reports_dir = Path(settings["paths"]["reports_dir"])
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    with open(reports_dir / "dq_report.json", "w") as f:
        json.dump({"total_defects_handled": total_affected, "rules": rules_summary}, f, indent=2)
        
    md_lines = ["# Data Quality Report", "", f"**Total Defects Handled:** {total_affected}", "", "## Rules Applied", ""]
    
    for rule_id, data in rules_summary.items():
        md_lines.append(f"### {rule_id}")
        md_lines.append(f"- **Action**: {data['action']}")
        md_lines.append(f"- **Total rows affected**: {data['affected']}")
        md_lines.append("- **Tables**: ")
        for table, count in data["tables"].items():
            md_lines.append(f"  - `{table}`: {count}")
        md_lines.append("")
        
    with open(reports_dir / "dq_report.md", "w") as f:
        f.write("\n".join(md_lines))
        
    # Write the human readable data quality log
    docs_dir = Path("docs")
    docs_dir.mkdir(parents=True, exist_ok=True)
    with open(docs_dir / "04_data_quality_log.md", "w") as f:
        f.write("\n".join(md_lines))
        
    print(f"Validation complete. Handled {total_affected} defects.")
