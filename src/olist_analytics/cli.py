import argparse
import sys

def profile(args):
    from .profiling import profile_data
    profile_data()

def clean(args):
    from .cleaning import clean_all_data
    clean_all_data()

def load_staging(args):
    from .load import load_staging_tables
    load_staging_tables()

def build_warehouse(args):
    from .dw import build_dimensional_warehouse
    build_dimensional_warehouse()

def build_kpis(args):
    from .kpis import build_kpis_views
    build_kpis_views()

def dq_check(args):
    print("dq-check logic is handled in build-kpis")

def analyze(args):
    from .analysis import run_analysis
    run_analysis()

def export(args):
    from .export import export_bi_tables
    export_bi_tables()

def report(args):
    from .report import generate_report
    generate_report()

def run_all(args):
    print("Starting full pipeline...")
    clean(args)
    load_staging(args)
    build_warehouse(args)
    build_kpis(args)
    analyze(args)
    export(args)
    report(args)
    print("Full pipeline completed.")

def main():
    parser = argparse.ArgumentParser(prog="olist_analytics")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("profile", help="Run data profiling")
    subparsers.add_parser("clean", help="Clean raw data")
    subparsers.add_parser("load-staging", help="Load cleaned data to staging")
    subparsers.add_parser("build-warehouse", help="Build star schema warehouse")
    subparsers.add_parser("build-kpis", help="Build KPI views")
    subparsers.add_parser("dq-check", help="Run data quality checks")
    subparsers.add_parser("analyze", help="Run analysis and stats")
    subparsers.add_parser("export", help="Export BI tables")
    subparsers.add_parser("report", help="Generate Excel report")
    subparsers.add_parser("run-all", help="Run full pipeline")

    args = parser.parse_args()

    commands = {
        "profile": profile,
        "clean": clean,
        "load-staging": load_staging,
        "build-warehouse": build_warehouse,
        "build-kpis": build_kpis,
        "dq-check": dq_check,
        "analyze": analyze,
        "export": export,
        "report": report,
        "run-all": run_all,
    }

    commands[args.command](args)

if __name__ == "__main__":
    main()
