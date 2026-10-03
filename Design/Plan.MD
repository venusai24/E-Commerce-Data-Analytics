# Olist Revenue Drivers: An End-to-End E-Commerce KPI and Root-Cause Analysis

**Design Document and Implementation Plan** (written to be executed by an AI coding agent, with a human in the loop at marked checkpoints)

Version 1.0

---

## Table of Contents

0. Operating rules for the AI coding agent
1. Project overview
2. Key design decisions
3. Dataset reference
4. Architecture, tech stack, repository layout, environment
5. Metric dictionary
6. Data cleaning and data-quality specification
7. Warehouse design (PostgreSQL star schema)
8. SQL analytics layer
9. Python analysis specification
10. Deliverable specifications (BI exports, Excel report, dashboard, memo)
11. Automation and CI
12. Testing strategy
13. Implementation plan by phase
14. Documentation, resume and interview-readiness deliverables
15. Pitfalls and risk register
16. Definition of Done
- Appendix A: `config/settings.yaml`
- Appendix B: Category group mapping seed
- Appendix C: Power BI DAX measures
- Appendix D: Insight memo template

---

## 0. Operating rules for the AI coding agent

Read this entire document before writing any code. These rules override convenience.

1. **Follow the phases in order** (Section 13). Do not start phase N+1 until phase N's acceptance criteria pass. Run `ruff check .` and `pytest` at the end of every phase.
2. **Never hardcode result numbers.** Any "expected" figure in this document (row counts, totals, percentages) comes from public exploratory analyses and is approximate. Use such figures only as *sanity checks with tolerances*. The data files are the source of truth. If the data disagrees with this document, trust the data and record the discrepancy in `docs/DECISIONS.md`.
3. **Never silently drop or alter data.** Every row removed or value modified must be recorded in `audit.cleaning_log` (rule id, table, rows affected, action). Prefer *flagging* over deleting. Only exact duplicate rows are dropped, and that drop is logged.
4. **Money is `NUMERIC(12,2)` in the database and `Decimal`/float-with-rounding in Python, never float columns in the DB.** Timestamps are naive local Brazilian time; do not convert time zones.
5. **All logic lives in `src/` and `sql/`.** Notebooks are for narrative and exploration only and must import functions from `src/olist_analytics`.
6. **Deterministic and idempotent.** Every pipeline step can be re-run safely. Use fixed random seeds (`stats.random_seed`). Use explicit `ORDER BY` when assigning surrogate keys.
7. **No fabricated insights.** Every statement in `docs/insight_memo_draft.md` must trace to a table, query, or test output. Generate `reports/memo_facts.json` from the analysis outputs and write the memo from that file only.
8. **Readable over clever.** The human owner must be able to explain every line in an interview. Use plain pandas and plain SQL. Add comments that explain *why*, not *what*. At the end of each phase, append a section to `docs/LEARNING_NOTES.md` (what was built, key concepts, 5 likely interview questions with short answers).
9. **Human checkpoints (marked ✋).** At each checkpoint, write a summary of results and open questions to `docs/CHECKPOINTS.md` and stop for human review before finalizing dependent work (insight memo, dashboard).
10. **Ambiguity rule.** If something is not specified, choose the simplest option consistent with this document and log the choice in `docs/DECISIONS.md` (date, decision, rationale).
11. **Do not commit data or secrets.** `data/` and `.env` are git-ignored. The Olist dataset is licensed CC BY-NC-SA 4.0; do not redistribute it.
12. **Git hygiene.** One commit per task, conventional commit messages (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
13. **Cross-platform.** The Python CLI (`python -m olist_analytics ...`) is the source of truth. The `Makefile` is a thin convenience wrapper. Do not put logic in Makefile recipes or shell scripts.

---

## 1. Project overview

### 1.1 Purpose

A portfolio project for entry-level Data Analyst roles. It demonstrates the full analyst workflow on realistic, messy, multi-table data: ingestion, cleaning and validation, dimensional modeling, advanced SQL, KPI design, root-cause analysis, statistics, BI dashboarding, automation, and written communication.

### 1.2 Central business question

> Between January 2017 and August 2018, how did marketplace revenue evolve, which months showed the largest changes, and which drivers (order volume, basket size, price, category mix, customer type, geography, sellers, fulfilment quality) explain those changes?

### 1.3 Secondary questions

1. Is revenue growth driven by more customers or by more spend per customer? Do customers come back?
2. Which product categories and regions contributed most to growth and to declines?
3. Is revenue concentrated in a few sellers or categories?
4. How does fulfilment performance (delivery time, lateness) evolve, and how does it relate to customer review scores? Is the relationship statistically and practically significant? What can and can't be concluded causally?
5. What do payment behaviors (type, installments) look like, and do they shift over time?

### 1.4 Deliverables

| ID | Deliverable | Format |
|---|---|---|
| D1 | Reproducible pipeline: raw CSV → cleaned staging → star schema → KPI views | Python package + SQL files |
| D2 | Data quality report and cleaning log | `reports/dq_report.md/.json`, `audit.*` tables |
| D3 | Warehouse documentation (ER diagram, data dictionary, metric dictionary) | `docs/*.md` |
| D4 | Analytical SQL layer with window functions, CTEs, subqueries, optimization notes | `sql/04_kpi/*.sql`, `docs/query_optimization.md` |
| D5 | Statistical analysis (decomposition, cohort, RFM, hypothesis tests) | `src/olist_analytics/analysis/`, notebooks, `reports/` |
| D6 | Interactive BI dashboard (Power BI or Tableau Public) | built by the human from agent-prepared exports and spec |
| D7 | Automated Excel executive report | `reports/olist_executive_summary.xlsx` |
| D8 | 1–2 page insight memo with recommendations, assumptions, limitations | `docs/insight_memo.md` |
| D9 | Automation and quality gates (CLI, CI, tests) | `Makefile`, `.github/workflows/ci.yml`, `tests/` |
| D10 | README, learning notes, resume bullets, interview Q&A | `README.md`, `docs/LEARNING_NOTES.md`, `docs/RESUME_AND_INTERVIEW.md` |

### 1.5 Non-goals (do not build)

Machine learning models, forecasting models, NLP on review text, dbt, Airflow, cloud deployment, streaming, a web app. (See stretch goals in Section 13, Phase 9, for optional extensions.) The BI dashboard file itself (.pbix / .twbx) cannot be produced by a coding agent; the agent prepares everything needed and the human builds it (Phase 7).

---

## 2. Key design decisions

| # | Decision | Rationale |
|---|---|---|
| 1 | **ETL for cleaning (pandas) + ELT/SQL for modeling and KPIs** | Shows pandas cleaning skill and strong SQL skill without duplicating logic: Python cleans and validates, SQL models and analyzes. |
| 2 | **PostgreSQL 16 in Docker** | Industry-standard relational DB; supports window functions, `FILTER`, `PERCENTILE_CONT`, materialized views. Docker makes setup reproducible. |
| 3 | **Star schema with two facts (`fact_orders` at order grain, `fact_order_items` at item grain)** | Different KPIs need different grains. Prevents join fan-out and double counting; conformed dimensions are shared. |
| 4 | **Revenue = sum of item `price`, excluding freight, for valid orders** | Freight is pass-through logistics cost, not merchandise sales. Freight is reported separately. |
| 5 | **Valid revenue order = status not in (`canceled`, `unavailable`) and at least one item** | Booked-revenue basis. A delivered-only sensitivity analysis is required (Section 9.6). |
| 6 | **Month attribution by purchase timestamp** | Revenue is attributed when the customer places the order, avoiding delivery-lag distortion. |
| 7 | **Analysis window 2017-01-01 to 2018-08-31** | 2016 is very sparse and Sept–Oct 2018 is truncated; including them creates fake "growth" and fake "collapse". |
| 8 | **Outliers are flagged, not removed**, with a sensitivity analysis | Removing data hides real behavior; flagging keeps transparency. |
| 9 | **`customer_unique_id` identifies a person** (`customer_id` is per order) | Using `customer_id` would make every customer look like a one-time buyer. |
| 10 | **BI tool-agnostic exports** | The user may use Power BI or Tableau Public. Agent produces star-schema CSV/Parquet exports plus a dashboard spec with DAX and Tableau notes. |
| 11 | **Statistics reported with effect sizes and confidence intervals, not just p-values** | With about 100k orders almost everything is "significant"; practical significance and causal caution matter more. |
| 12 | **Fixture dataset with seeded defects for tests and CI** | The real data cannot be committed, and tests must verify that cleaning rules actually catch known defects. |

---

## 3. Dataset reference

**Source:** Kaggle dataset `olistbr/brazilian-ecommerce` ("Brazilian E-Commerce Public Dataset by Olist"). Download manually from Kaggle (requires a free account) and place the 9 CSV files in `data/raw/`, or use `kaggle datasets download -d olistbr/brazilian-ecommerce --unzip -p data/raw` if the Kaggle CLI is configured. The `ingest` step must verify all 9 files exist and fail with a clear message listing missing files and the download instructions.

**License:** CC BY-NC-SA 4.0. Portfolio use with attribution is fine. Add attribution to the README. Do not commit the data.

**Coverage:** about 100k orders placed between September 2016 and October 2018 (anonymized, a sample of a marketplace; absolute revenue is not Olist's real revenue).

### 3.1 Files, grain, and columns (approximate row counts are for sanity checks only)

| File | Grain | Approx. rows | Columns |
|---|---|---|---|
| `olist_customers_dataset.csv` | one row per `customer_id` (an order-level id) | 99,441 | `customer_id`, `customer_unique_id`, `customer_zip_code_prefix`, `customer_city`, `customer_state` |
| `olist_geolocation_dataset.csv` | many rows per zip prefix | ~1,000,000 | `geolocation_zip_code_prefix`, `geolocation_lat`, `geolocation_lng`, `geolocation_city`, `geolocation_state` |
| `olist_order_items_dataset.csv` | one row per (`order_id`, `order_item_id`) | ~112,650 | `order_id`, `order_item_id`, `product_id`, `seller_id`, `shipping_limit_date`, `price`, `freight_value` |
| `olist_order_payments_dataset.csv` | one row per (`order_id`, `payment_sequential`) | ~103,886 | `order_id`, `payment_sequential`, `payment_type`, `payment_installments`, `payment_value` |
| `olist_order_reviews_dataset.csv` | one row per review (an order can have several) | ~99,224 | `review_id`, `order_id`, `review_score`, `review_comment_title`, `review_comment_message`, `review_creation_date`, `review_answer_timestamp` |
| `olist_orders_dataset.csv` | one row per `order_id` | 99,441 | `order_id`, `customer_id`, `order_status`, `order_purchase_timestamp`, `order_approved_at`, `order_delivered_carrier_date`, `order_delivered_customer_date`, `order_estimated_delivery_date` |
| `olist_products_dataset.csv` | one row per `product_id` | ~32,951 | `product_id`, `product_category_name`, `product_name_lenght`, `product_description_lenght`, `product_photos_qty`, `product_weight_g`, `product_length_cm`, `product_height_cm`, `product_width_cm` |
| `olist_sellers_dataset.csv` | one row per `seller_id` | ~3,095 | `seller_id`, `seller_zip_code_prefix`, `seller_city`, `seller_state` |
| `product_category_name_translation.csv` | one row per category | ~71 | `product_category_name`, `product_category_name_english` |

Note the source typos `product_name_lenght` and `product_description_lenght`; rename them to `product_name_length` and `product_description_length` in staging.

### 3.2 Relationships

```
customers.customer_id ──< orders.order_id >── order_items (order_id) ──> products.product_id
                                       │                       └──────> sellers.seller_id
                                       ├── order_payments (order_id)
                                       └── order_reviews  (order_id)
customers/sellers.zip_code_prefix ── geolocation.zip_code_prefix (many rows per prefix)
products.product_category_name ── translation.product_category_name
```

### 3.3 Known quirks (the cleaning spec in Section 6 is built around these; verify each during profiling)

1. `customer_id` is unique per order; the same person can have several `customer_id`s but only one `customer_unique_id`. Only a small share of people (roughly 3%) have more than one order, so retention numbers will be low. This is a real property of the data and a finding in itself.
2. Zip code prefixes are 5-digit strings that may have leading zeros; reading them as integers corrupts them. Always read as `str`.
3. Geolocation has a very large number of exact duplicate rows and several coordinates per zip prefix; some coordinates fall outside Brazil.
4. Timestamps are strings and some are null depending on status. A few orders have impossible timestamp sequences (for example carrier pickup before purchase).
5. Roughly 8 orders are `delivered` but lack a delivered-to-customer timestamp; roughly 775 orders have no items (mostly canceled/unavailable but not all).
6. One order may have several payment rows (voucher plus card, installments); a few rows have `payment_value` of 0, `payment_type` of `not_defined`, or `payment_installments` of 0.
7. Some `review_id` values repeat, and some orders have more than one review. Deduplicate to one review per order.
8. About 610 products have a null category; 2 categories present in products are missing from the translation file (`pc_gamer`, `portateis_cozinha_e_preparadores_de_alimentos`).
9. Order volume is tiny in late 2016 (and nearly absent in some months) and truncated after August 2018. A month-over-month "change" at either end is a coverage artifact.
10. Some city names are inconsistently spelled or accented.
11. Price and freight are heavily right-skewed with extreme values.

---

## 4. Architecture, tech stack, repository layout, environment

### 4.1 Data flow

```mermaid
flowchart LR
  A[Kaggle CSVs<br/>data/raw] --> B[Profile<br/>pandas]
  B --> C[Clean and validate<br/>pandas]
  C --> D[(PostgreSQL<br/>schema stg)]
  C --> L[(schema audit<br/>cleaning log, DQ results, runs)]
  D --> E[(schema dw<br/>star schema)]
  E --> F[(schema kpi<br/>SQL views)]
  F --> G[Python analysis<br/>bridge, PVM, cohorts, RFM, stats]
  G --> H[Exports<br/>CSV / Parquet]
  H --> I[BI dashboard<br/>Power BI or Tableau]
  G --> J[Excel executive report]
  G --> K[Insight memo]
```

Database schemas: `stg` (cleaned 1:1 copies of source tables), `dw` (star schema), `kpi` (analytical views), `audit` (persistent run history, cleaning log, DQ results). Raw CSVs stay immutable on disk and are not loaded into the database.

### 4.2 Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | type hints everywhere |
| Data wrangling | pandas ≥ 2.2, numpy | plain, readable code |
| Stats | scipy, statsmodels | Mann-Whitney, chi-square, proportion CIs, logistic regression |
| DB | PostgreSQL 16 (Docker) | |
| DB access | SQLAlchemy ≥ 2.0 + psycopg 3 (`postgresql+psycopg://`) | explicit DDL in `.sql` files; pandas `to_sql(method="multi", chunksize=10000)` or COPY for loads |
| Config | PyYAML + python-dotenv | `config/settings.yaml`, `.env` |
| Excel | XlsxWriter | native charts and formulas |
| Plots | matplotlib, seaborn | static figures for notebooks and the memo |
| Parquet | pyarrow | interim and export files |
| CLI | argparse (stdlib) | one subcommand per pipeline step |
| Quality | pytest, ruff (lint + format) | |
| CI | GitHub Actions with a Postgres service container | |
| Notebooks | Jupyter (dev dependency) | narrative only |

### 4.3 Repository layout

```
olist-revenue-drivers/
├── README.md
├── pyproject.toml
├── Makefile
├── docker-compose.yml
├── .env.example
├── .gitignore
├── .github/workflows/ci.yml
├── config/
│   ├── settings.yaml
│   ├── category_groups.csv            # category_name_english -> category_group (Appendix B)
│   └── brazil_regions.csv             # state (UF) -> macro-region
├── data/                              # git-ignored
│   ├── raw/                           # the 9 Kaggle CSVs
│   ├── interim/                       # cleaned parquet files
│   └── exports/
│       ├── model/                     # star-schema tables for BI
│       └── analysis/                  # precomputed analysis tables for BI
├── docs/
│   ├── 01_business_context.md
│   ├── 02_metric_dictionary.md
│   ├── 03_data_dictionary.md
│   ├── 04_data_quality_log.md
│   ├── 05_dashboard_spec.md
│   ├── er_diagram.md
│   ├── query_optimization.md
│   ├── insight_memo_draft.md          # agent draft; human writes docs/insight_memo.md
│   ├── assumptions_and_limitations.md
│   ├── DECISIONS.md
│   ├── CHECKPOINTS.md
│   ├── LEARNING_NOTES.md
│   └── RESUME_AND_INTERVIEW.md
├── sql/
│   ├── 00_schemas.sql
│   ├── 01_stg_ddl.sql
│   ├── 02_dw_ddl.sql
│   ├── 03_dw_load/
│   │   ├── 01_dim_date.sql
│   │   ├── 02_dim_customer.sql
│   │   ├── 03_dim_product.sql
│   │   ├── 04_dim_seller.sql
│   │   ├── 05_fact_orders.sql
│   │   └── 06_fact_order_items.sql
│   ├── 04_kpi/                        # one view per file, numbered
│   ├── 05_indexes.sql
│   └── 06_audit_ddl.sql
├── src/olist_analytics/
│   ├── __init__.py
│   ├── __main__.py                    # enables python -m olist_analytics
│   ├── cli.py
│   ├── config.py
│   ├── db.py
│   ├── ingest.py
│   ├── profiling.py
│   ├── cleaning.py
│   ├── validation.py
│   ├── load.py
│   ├── warehouse.py                   # runs SQL files in order
│   ├── analysis/
│   │   ├── bridge.py                  # price-volume-mix and driver drill-downs
│   │   ├── customers.py               # cohort/RFM post-processing
│   │   ├── operations.py              # delivery vs reviews
│   │   ├── stats_utils.py
│   │   └── sensitivity.py
│   ├── exports.py
│   └── reporting/
│       ├── excel_report.py
│       └── memo_facts.py
├── notebooks/
│   ├── 01_profiling.ipynb
│   ├── 02_revenue_drivers.ipynb
│   └── 03_statistical_tests.ipynb
├── tests/
│   ├── fixtures/make_fixture.py
│   ├── test_cleaning.py
│   ├── test_validation.py
│   ├── test_stats_utils.py
│   ├── test_bridge.py
│   └── integration/
│       ├── test_warehouse.py
│       └── test_kpi_views.py
├── reports/                           # generated outputs (git-ignored except curated figures)
│   ├── profile/
│   ├── figures/
│   └── ...
└── dashboard/
    ├── dax_measures.md
    ├── tableau_calculations.md
    └── screenshots/                   # human adds
```

### 4.4 Environment

`docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:16
    container_name: olist_pg
    environment:
      POSTGRES_USER: olist
      POSTGRES_PASSWORD: olist_dev_password
      POSTGRES_DB: olist
    ports:
      - "5433:5432"          # host port 5433 avoids clashing with a local Postgres
    volumes:
      - olist_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U olist -d olist"]
      interval: 5s
      timeout: 5s
      retries: 10
volumes:
  olist_pgdata:
```

`.env.example`:

```
DATABASE_URL=postgresql+psycopg://olist:olist_dev_password@localhost:5433/olist
OLIST_DATA_DIR=data/raw
```

`pyproject.toml` essentials: package `olist_analytics` in `src/`, dependencies `pandas>=2.2`, `numpy`, `scipy`, `statsmodels`, `sqlalchemy>=2`, `psycopg[binary]>=3`, `pyyaml`, `python-dotenv`, `xlsxwriter`, `pyarrow`, `matplotlib`, `seaborn`; optional `dev` extras `pytest`, `ruff`, `jupyter`, `ipykernel`. Configure ruff (line length 100) and pytest (markers: `integration`).

**CLI commands** (`python -m olist_analytics <command>`): `profile`, `clean`, `load-staging`, `build-warehouse`, `build-kpis`, `dq-check`, `analyze`, `export`, `report`, `run-all`. `run-all` executes them in order and stops on any error-severity DQ failure. **Makefile targets** wrap these: `setup`, `db-up`, `db-down`, `profile`, `clean`, `load`, `warehouse`, `kpis`, `dq`, `analyze`, `export`, `report`, `all`, `test`, `lint`, `fixture`.

---

## 5. Metric dictionary

Reproduce this table in `docs/02_metric_dictionary.md`. Every dashboard measure, SQL view, and memo number must use these definitions.

### 5.1 Base filters

- **Valid revenue order** (`is_valid_revenue_order`): `order_status NOT IN ('canceled','unavailable')` (configurable in `analysis.excluded_statuses`) AND the order has at least one item.
- **In analysis window** (`in_analysis_window`): purchase date between `analysis.window_start` and `analysis.window_end` inclusive.
- **Month** = calendar month of `order_purchase_timestamp`.
- **Delivery-metrics eligible** (`delivery_metrics_eligible`): `order_status = 'delivered'` AND delivered-to-customer timestamp is not null AND delivered timestamp ≥ purchase timestamp.

### 5.2 Metrics

| Metric | Definition | Notes |
|---|---|---|
| Revenue | `SUM(price)` over items of valid orders | Excludes freight. Primary KPI. |
| Freight revenue | `SUM(freight_value)` over items of valid orders | |
| Orders | count distinct `order_id` among valid orders | |
| Units | count of item rows among valid orders | |
| Active customers | count distinct `customer_unique_id` with at least one valid order in the period | |
| New customers | active customers whose first-ever valid order is in the period | First order measured over full history, not only the window. |
| Returning customers | active customers minus new customers | |
| AOV | Revenue ÷ Orders | |
| Items per order | Units ÷ Orders | basket size |
| Average item price (ASP) | Revenue ÷ Units | |
| Revenue per active customer | Revenue ÷ Active customers | |
| Repeat purchase rate | customers with ≥ 2 valid orders ÷ customers with ≥ 1 valid order (up to window end) | |
| Cohort retention M*k* | share of a cohort (first valid order month) with ≥ 1 valid order in cohort month + *k* | M0 = 100% by construction. |
| Delivery days | (delivered-to-customer timestamp − purchase timestamp) in days, 2 decimals | eligible orders only |
| Delay days | delivered date − estimated delivery date, in whole days (positive = late) | compare dates, not timestamps; eligible orders only |
| Late order | `delay_days > late_threshold_days` (default 0) | |
| On-time rate | eligible orders not late ÷ eligible orders | |
| Avg review score | mean of the single deduplicated review score per order | |
| % 1-star, % low score, % 5-star | share of reviewed orders with score = 1, ≤ 2, = 5 | |
| Freight ratio | `SUM(freight_value) ÷ SUM(price)` | aggregate ratio, not mean of ratios |
| Top-10 seller share | revenue of the 10 largest sellers ÷ total revenue (per month or period) | |
| Seller HHI | `10,000 × Σ(seller_share²)` | concentration index |
| MoM growth % | `(Revenue_t ÷ Revenue_{t-1} − 1) × 100` | |
| 3-month moving average | average of current and previous 2 months | |
| YTD revenue | cumulative revenue within the calendar year | |
| Orders effect / AOV effect | revenue bridge terms, defined in Section 9.1 | |
| Volume / mix / price effect | price-volume-mix terms, defined in Section 9.1 | |

---

## 6. Data cleaning and data-quality specification

Cleaning is implemented in `cleaning.py` as small, individually testable functions (one per rule or per table). Output: cleaned parquet files in `data/interim/`, rows loaded into `stg.*`, entries in `audit.cleaning_log` and `audit.dq_results`, and a rendered `reports/dq_report.md` and `.json`.

### 6.1 General standardization (all tables)

- Read every CSV with explicit `dtype` mappings; ID and zip columns as `str`. Never let pandas infer IDs or zip codes as numbers.
- Strip whitespace from all string columns. Lowercase city names and categories; remove accents from city names (`unicodedata.normalize("NFKD", ...)`). Uppercase state codes and validate against the 27 Brazilian UFs in `config/brazil_regions.csv`.
- Zip prefixes: zero-pad to 5 characters.
- Parse timestamps with `pd.to_datetime(..., errors="coerce")` and log how many values failed to parse.
- Rename source typos (`*_lenght` → `*_length`).

### 6.2 Rule catalog

Action codes: **FIX** (value corrected deterministically), **FLAG** (add boolean flag, keep row), **DROP** (remove rows, always logged), **REPORT** (measure and report only). Severity: **E** = pipeline halts if violated after cleaning; **W** = warning in report.

| ID | Table | Rule | Action | Sev |
|---|---|---|---|---|
| C1 | customers | `customer_id` unique | REPORT | E |
| C2 | customers | state in valid UF list; zip is 5-char string | FIX/REPORT | W |
| C3 | customers | normalize city (lowercase, accent-free) | FIX | W |
| G1 | geolocation | exact duplicate rows | DROP (logged) | W |
| G2 | geolocation | lat/lng outside Brazil bounding box (`cleaning.brazil_bbox`) | FLAG, exclude from aggregation | W |
| G3 | geolocation | collapse to one row per zip prefix: median lat, median lng, modal city/state | FIX (aggregate) | W |
| O1 | orders | `order_id` unique | REPORT | E |
| O2 | orders | all 5 timestamp columns parse | FIX (coerce to null) | W |
| O3 | orders | timestamp sequence violated (purchase ≤ approved ≤ carrier ≤ delivered) | FLAG `dq_ts_sequence_anomaly` | W |
| O4 | orders | status `delivered` but delivered timestamp null | FLAG `dq_delivered_missing_ts` | W |
| O5 | orders | non-delivered status but delivered timestamp present | FLAG `dq_status_ts_conflict` | W |
| O6 | orders | order has no items | FLAG (becomes `has_items = false` in warehouse) | W |
| O7 | orders | order has no payment rows | FLAG | W |
| I1 | order_items | (`order_id`,`order_item_id`) unique | REPORT | E |
| I2 | order_items | `price > 0` and `freight_value ≥ 0` | REPORT | E |
| I3 | order_items | price/freight outliers (IQR on log1p, multiplier `stats.outliers.iqr_multiplier`) | FLAG `dq_price_outlier`, `dq_freight_outlier` | W |
| I4 | order_items | FK integrity to orders, products, sellers | REPORT | E |
| P1 | payments | `payment_value = 0` | FLAG `dq_zero_payment` | W |
| P2 | payments | `payment_installments = 0` | FIX to null and FLAG | W |
| P3 | payments | `payment_type = 'not_defined'` | FLAG | W |
| P4 | payments | per order, total payments vs (items + freight): reconcile within 1 BRL | REPORT (match rate) | W |
| R1 | reviews | multiple reviews per order and repeated `review_id` | FIX: keep the latest per order (max `review_answer_timestamp`, tie-break max `review_creation_date`, then `review_id`); record `review_count` | W |
| R2 | reviews | `review_score` in 1..5 | REPORT | E |
| R3 | reviews | comment fields are not used downstream | REPORT null rates only | W |
| PR1 | products | null category | FIX to `unknown` | W |
| PR2 | products | category missing from translation | FIX using `cleaning.category_patches`, else `unknown` | W |
| PR3 | products | null or zero weight/dimensions, null photos | FLAG `dq_missing_dimensions` | W |
| S1 | sellers | `seller_id` unique; same normalization as customers | REPORT/FIX | E/W |
| X1 | all | row counts raw → stg, loss per table ≤ `cleaning.max_row_loss_pct` | REPORT | E |
| X2 | orders | at least one valid order inside the analysis window | REPORT | E |
| X3 | all | raw total of item price and freight equals the sum in `stg` (within 0.01) | REPORT | E |

### 6.3 Cleaning principles

1. **Flag over delete.** The only deletions are exact duplicate rows (G1) and the review collapse (R1), both logged with counts.
2. **Quantify.** Each rule records `rows_checked`, `rows_affected`, `pct_affected` in `audit.dq_results` (run id, rule id, table, metric values, status PASS/WARN/FAIL).
3. **Explain.** `docs/04_data_quality_log.md` lists every rule with the observed count on the real data and a one-sentence justification of the chosen action (generated from `audit.dq_results` plus hand-written rationale).
4. **Reconcile.** After loading `stg`, the pipeline recomputes raw vs staged row counts and money totals and halts on mismatch beyond tolerance.

### 6.4 Profiling (before cleaning)

`profile` writes `reports/profile/<table>.md` and a combined `reports/profile/profile_summary.json`: row count, per-column dtype, null count and %, distinct count, min/max for numeric and date columns, top 5 values for low-cardinality columns, and basic descriptive statistics (mean, median, std, skew) for `price`, `freight_value`, `payment_value`, and review score. It also prints a **sanity-check table**: observed vs approximate expected values from Section 3.1 with a tolerance of ±5%; mismatches are warnings, not failures.

---

## 7. Warehouse design (PostgreSQL star schema)

### 7.1 Schemas

`stg`, `dw`, `kpi`, `audit`. `build-warehouse` drops and recreates `dw` and `kpi` each run. `load-staging` drops and recreates `stg`. `audit` persists across runs (append-only history).

### 7.2 ER diagram

Render this in `docs/er_diagram.md` (Mermaid) and export a PNG for the README.

```mermaid
erDiagram
  dim_date ||--o{ fact_orders : purchase_date_key
  dim_date ||--o{ fact_order_items : purchase_date_key
  dim_customer ||--o{ fact_orders : customer_key
  dim_customer ||--o{ fact_order_items : customer_key
  dim_product ||--o{ fact_order_items : product_key
  dim_seller ||--o{ fact_order_items : seller_key
  fact_orders ||--|{ fact_order_items : order_key
  fact_orders ||--o{ fact_payments : order_key
  dim_payment_type ||--o{ fact_payments : payment_type_key
```

### 7.3 Dimension tables

**`dw.dim_date`** (generated with `generate_series` from 2016-09-01 to 2018-12-31): `date_key INT PK (YYYYMMDD)`, `date DATE`, `year`, `quarter`, `month`, `month_name`, `year_month TEXT ('YYYY-MM')`, `month_start DATE`, `week_of_year`, `day_of_week`, `day_name`, `is_weekend BOOL`, `special_event TEXT NULL` (loaded from `analysis.special_events` in config; seed with Black Friday 2017-11-24).

**`dw.dim_customer`** (grain: one row per `customer_unique_id`): `customer_key INT PK (identity)`, `customer_unique_id TEXT UNIQUE`, `zip_prefix`, `city`, `state`, `region`, `lat`, `lng`. If a person has several order-level `customer_id`s with different locations, take the location from their most recent order (`DISTINCT ON ... ORDER BY purchase_ts DESC`). Assign keys with deterministic ordering by `customer_unique_id`.

**`dw.dim_product`**: `product_key PK`, `product_id UNIQUE`, `category_name_pt`, `category_name_en`, `category_group` (from `config/category_groups.csv`), `name_length`, `description_length`, `photos_qty`, `weight_g`, `length_cm`, `height_cm`, `width_cm`, `volume_cm3` (derived), `dq_missing_dimensions BOOL`.

**`dw.dim_seller`**: `seller_key PK`, `seller_id UNIQUE`, `zip_prefix`, `city`, `state`, `region`, `lat`, `lng`.

**`dw.dim_payment_type`**: `payment_type_key PK`, `payment_type` (credit_card, boleto, voucher, debit_card, not_defined).

### 7.4 Fact tables

**`dw.fact_orders`** (grain: one row per order):

| Column | Type | Notes |
|---|---|---|
| `order_key` | INT PK identity | assigned `ORDER BY order_id` |
| `order_id` | TEXT UNIQUE | |
| `customer_id` | TEXT | order-level id kept for traceability |
| `customer_key` | INT FK | person-level key |
| `purchase_ts`, `approved_ts`, `carrier_ts`, `delivered_ts` | TIMESTAMP | naive |
| `estimated_delivery_date` | DATE | |
| `purchase_date_key` | INT FK → dim_date | |
| `delivered_date_key` | INT NULL | |
| `order_status` | TEXT | |
| `n_items`, `n_sellers` | INT | 0 if none |
| `items_value`, `freight_value`, `order_total` | NUMERIC(12,2) | aggregated from items **before** joining |
| `payment_value`, `n_payments`, `primary_payment_type`, `max_installments` | | aggregated from payments **before** joining |
| `review_score` | SMALLINT NULL | one per order (cleaned) |
| `review_count` | INT | raw number of reviews for the order |
| `delivery_days` | NUMERIC(8,2) NULL | eligible orders only |
| `delay_days` | INT NULL | eligible orders only |
| `is_late` | BOOL NULL | NULL if not eligible |
| `delay_bucket` | TEXT NULL | `1_early_gt7d`, `2_early_1_7d`, `3_on_day`, `4_late_1_3d`, `5_late_4_7d`, `6_late_gt7d` |
| `has_items`, `is_valid_revenue_order`, `in_analysis_window`, `delivery_metrics_eligible` | BOOL | per Section 5.1 |
| `dq_ts_sequence_anomaly`, `dq_delivered_missing_ts`, `dq_status_ts_conflict` | BOOL | carried from cleaning |

**`dw.fact_order_items`** (grain: one row per order item): `order_item_key PK identity`, `order_key FK`, `order_id`, `order_item_id`, `customer_key`, `product_key`, `seller_key`, `purchase_date_key`, `shipping_limit_ts`, `price NUMERIC(12,2)`, `freight_value NUMERIC(12,2)`, `item_total` (price + freight), `is_valid_revenue_order`, `in_analysis_window` (denormalized from the order), `dq_price_outlier`, `dq_freight_outlier`.

**`dw.fact_payments`** (grain: order × payment sequence): `order_key`, `payment_sequential`, `payment_type_key`, `installments`, `payment_value`, `dq_zero_payment`.

**Join discipline (critical):** never join items, payments, and reviews to orders in one query without pre-aggregating each to order grain (that multiplies rows). Build `fact_orders` from CTEs that aggregate each child table to one row per `order_id`, then join the CTEs.

### 7.5 Keys, constraints, indexes (`sql/02_dw_ddl.sql`, `sql/05_indexes.sql`)

- Primary keys on all tables; foreign keys from facts to dimensions; `NOT NULL` on keys; `CHECK (price >= 0)`, `CHECK (review_score BETWEEN 1 AND 5)`.
- Indexes: `fact_orders(purchase_date_key)`, `fact_orders(customer_key)`, partial index `fact_orders(purchase_date_key) WHERE is_valid_revenue_order AND in_analysis_window`, `fact_order_items(order_key)`, `fact_order_items(product_key)`, `fact_order_items(seller_key)`, `fact_order_items(purchase_date_key)`.
- Run `ANALYZE` on all `dw` tables after load.

### 7.6 Reconciliation (must pass, see tests)

1. `COUNT(*) FROM dw.fact_orders` = `COUNT(*) FROM stg.orders`.
2. `SUM(price)` in `dw.fact_order_items` = `SUM(price)` in `stg.order_items` (to the cent), and per order, `SUM(fact_order_items.price) = fact_orders.items_value`.
3. `COUNT(DISTINCT customer_unique_id)` in `dim_customer` = distinct `customer_unique_id` in `stg.customers`.
4. No fan-out: `COUNT(*) = COUNT(DISTINCT order_id)` on `fact_orders`.

---

## 8. SQL analytics layer

Views live in schema `kpi`, one per file in `sql/04_kpi/`, numbered so they run in dependency order. Each file starts with a comment block: purpose, grain, definitions used, and the interview-level explanation of any non-obvious construct.

### 8.1 View catalog

| File | View | Grain | Purpose |
|---|---|---|---|
| `01_monthly_kpis.sql` | `kpi.v_monthly_kpis` | month | revenue, freight, orders, customers (new/returning), AOV, items/order, ASP, MoM %, 3M MA, YTD |
| `02_revenue_bridge_orders_aov.sql` | `kpi.v_revenue_bridge_orders_aov` | month vs previous month | orders effect and AOV effect |
| `03_monthly_category.sql` | `kpi.v_monthly_category` (materialized) | month × category group | revenue, units, orders, avg price, share |
| `04_monthly_geo.sql` | `kpi.v_monthly_region_state` | month × state | revenue, orders, freight ratio, avg delivery days |
| `05_seller_monthly.sql` | `kpi.v_seller_monthly`, `kpi.v_seller_concentration` | month × seller; month | revenue rank per month, top-10 share, HHI |
| `06_customer_orders.sql` | `kpi.v_customer_order_sequence` | order | order sequence per customer, days since previous order (`LAG`) |
| `07_cohort_retention.sql` | `kpi.v_cohort_retention` | cohort month × month index | retention matrix |
| `08_rfm.sql` | `kpi.v_rfm` | customer | recency, frequency, monetary, scores, segment |
| `09_delivery_monthly.sql` | `kpi.v_delivery_monthly` | month | on-time rate, avg and P90 delivery days, avg review, % 1-star |
| `10_delay_bucket_reviews.sql` | `kpi.v_delay_bucket_reviews` | delay bucket | orders, avg score, % 1-star, % low |
| `11_payment_mix_monthly.sql` | `kpi.v_payment_mix_monthly` | month × payment type | share of orders and value, avg installments |
| `12_new_vs_returning_monthly.sql` | `kpi.v_new_vs_returning_monthly` | month × customer type | revenue, orders, AOV |
| `13_sensitivity_delivered_only.sql` | `kpi.v_monthly_kpis_delivered_only` | month | same as view 01 but only `delivered` orders |

### 8.2 Reference SQL (implement exactly these semantics)

**`kpi.v_monthly_kpis`**

```sql
CREATE OR REPLACE VIEW kpi.v_monthly_kpis AS
WITH valid_orders AS (
    SELECT o.customer_key, d.year_month, d.month_start,
           o.items_value, o.freight_value, o.n_items
    FROM dw.fact_orders o
    JOIN dw.dim_date d ON d.date_key = o.purchase_date_key
    WHERE o.is_valid_revenue_order AND o.in_analysis_window
),
first_orders AS (          -- first valid order per person over the FULL history
    SELECT customer_key, MIN(purchase_ts) AS first_ts
    FROM dw.fact_orders
    WHERE is_valid_revenue_order
    GROUP BY customer_key
),
monthly AS (
    SELECT v.year_month, v.month_start,
           SUM(v.items_value)                         AS revenue,
           SUM(v.freight_value)                       AS freight,
           COUNT(*)                                   AS orders,
           SUM(v.n_items)                             AS units,
           COUNT(DISTINCT v.customer_key)             AS active_customers,
           COUNT(DISTINCT v.customer_key) FILTER (
               WHERE date_trunc('month', f.first_ts)::date = v.month_start
           )                                          AS new_customers
    FROM valid_orders v
    JOIN first_orders f USING (customer_key)
    GROUP BY v.year_month, v.month_start
)
SELECT year_month, month_start, revenue, freight, orders, units,
       active_customers, new_customers,
       active_customers - new_customers                                AS returning_customers,
       ROUND(revenue / orders, 2)                                      AS aov,
       ROUND(units::numeric / orders, 3)                               AS items_per_order,
       ROUND(revenue / units, 2)                                       AS avg_item_price,
       ROUND(100.0 * (revenue / NULLIF(LAG(revenue) OVER w, 0) - 1), 2) AS revenue_mom_pct,
       ROUND(AVG(revenue) OVER (ORDER BY month_start
                                ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS revenue_3m_ma,
       SUM(revenue) OVER (PARTITION BY date_part('year', month_start)
                          ORDER BY month_start)                        AS revenue_ytd
FROM monthly
WINDOW w AS (ORDER BY month_start)
ORDER BY month_start;
```

**`kpi.v_revenue_bridge_orders_aov`** (sequential decomposition: volume at old AOV, then AOV change at new volume)

```sql
CREATE OR REPLACE VIEW kpi.v_revenue_bridge_orders_aov AS
WITH m AS (
    SELECT month_start, year_month, revenue, orders, revenue / orders AS aov
    FROM kpi.v_monthly_kpis
),
b AS (
    SELECT *,
           LAG(revenue) OVER (ORDER BY month_start) AS prev_revenue,
           LAG(orders)  OVER (ORDER BY month_start) AS prev_orders,
           LAG(aov)     OVER (ORDER BY month_start) AS prev_aov
    FROM m
)
SELECT year_month, prev_revenue, revenue,
       revenue - prev_revenue                  AS delta_revenue,
       (orders - prev_orders) * prev_aov       AS orders_effect,
       orders * (aov - prev_aov)               AS aov_effect
FROM b
WHERE prev_revenue IS NOT NULL;
-- invariant (tested): orders_effect + aov_effect = delta_revenue (tolerance 0.01)
```

**`kpi.v_cohort_retention`** (restrict `cohort_month` to cohorts within the analysis window and activity to months ≤ `window_end` in the final SELECT or the export step; M0 must equal 100%)

```sql
CREATE OR REPLACE VIEW kpi.v_cohort_retention AS
WITH cust_months AS (
    SELECT customer_key, date_trunc('month', purchase_ts)::date AS order_month
    FROM dw.fact_orders
    WHERE is_valid_revenue_order
    GROUP BY customer_key, date_trunc('month', purchase_ts)::date
),
cohorts AS (
    SELECT customer_key, MIN(order_month) AS cohort_month
    FROM cust_months GROUP BY customer_key
),
activity AS (
    SELECT c.cohort_month,
           ((EXTRACT(YEAR  FROM age(m.order_month, c.cohort_month)) * 12)
           + EXTRACT(MONTH FROM age(m.order_month, c.cohort_month)))::int AS month_index,
           COUNT(DISTINCT m.customer_key) AS active_customers
    FROM cust_months m
    JOIN cohorts c USING (customer_key)
    GROUP BY c.cohort_month, month_index
)
SELECT cohort_month, month_index, active_customers,
       FIRST_VALUE(active_customers) OVER (PARTITION BY cohort_month ORDER BY month_index) AS cohort_size,
       ROUND(100.0 * active_customers /
             FIRST_VALUE(active_customers) OVER (PARTITION BY cohort_month ORDER BY month_index), 2) AS retention_pct
FROM activity;
```

**`kpi.v_delay_bucket_reviews`**

```sql
CREATE OR REPLACE VIEW kpi.v_delay_bucket_reviews AS
SELECT delay_bucket,
       COUNT(*)                                        AS orders,
       ROUND(AVG(review_score), 3)                     AS avg_review_score,
       ROUND(100.0 * AVG((review_score = 1)::int), 2)  AS pct_1_star,
       ROUND(100.0 * AVG((review_score <= 2)::int), 2) AS pct_low_score
FROM dw.fact_orders
WHERE delivery_metrics_eligible AND review_score IS NOT NULL AND in_analysis_window
GROUP BY delay_bucket
ORDER BY delay_bucket;
```

**`kpi.v_rfm` specification** (write the SQL yourself): snapshot date = `window_end + snapshot_offset_days`. Per customer over valid orders with purchase ≤ window end: `recency_days` = snapshot − last purchase date; `frequency` = number of valid orders; `monetary` = sum of `items_value`. Scores: `r_score = NTILE(5) OVER (ORDER BY recency_days DESC)` (5 = most recent), `m_score = NTILE(5) OVER (ORDER BY monetary ASC)` (5 = highest), `f_score = CASE WHEN frequency = 1 THEN 1 WHEN frequency = 2 THEN 2 ELSE 3 END` (frequency is nearly always 1, so quintiles are meaningless). Segments (mutually exclusive, exhaustive):

| Segment | Rule |
|---|---|
| Loyal Active | `f_score >= 2` and `r_score >= 3` |
| Lapsed Repeat | `f_score >= 2` and `r_score <= 2` |
| Recent High-Value | `f_score = 1`, `r_score >= 4`, `m_score >= 4` |
| Recent Standard | `f_score = 1`, `r_score >= 4`, `m_score <= 3` |
| Lapsing High-Value | `f_score = 1`, `r_score <= 3`, `m_score >= 4` |
| Dormant | `f_score = 1`, `r_score <= 3`, `m_score <= 3` |

### 8.3 SQL showcase checklist (all must appear somewhere in `sql/`)

CTE chains; subqueries in `FROM` and `WHERE` (at least one correlated subquery); `JOIN` types (inner, left, and a self-join or anti-join via `LEFT JOIN ... IS NULL`); `GROUP BY` with `HAVING`; `CASE`; conditional aggregation with `FILTER`; window functions `ROW_NUMBER`, `RANK`/`DENSE_RANK`, `LAG`/`LEAD`, running `SUM() OVER`, moving `AVG() OVER (ROWS BETWEEN ...)`, `NTILE`, `FIRST_VALUE`; `PERCENTILE_CONT` (P50/P90 delivery days); `DISTINCT ON`; date functions (`date_trunc`, `age`, `generate_series`); set operation (`UNION ALL` or `EXCEPT`); a materialized view with `REFRESH MATERIALIZED VIEW`; `COALESCE`/`NULLIF` for safe division.

### 8.4 Query optimization deliverable (`docs/query_optimization.md`)

Pick two non-trivial queries (for example the seller-concentration view and the category-by-month aggregation). For each: record `EXPLAIN (ANALYZE, BUFFERS)` output **before** indexes/materialization, apply one change (index, partial index, pre-aggregation, or materialized view), record the output **after**, and explain in 3–5 sentences what the planner did differently (seq scan vs index scan, rows, time). Include screenshots or pasted plans.

---

## 9. Python analysis specification

Python handles what is awkward or less transparent in SQL: multi-dimensional decomposition, statistical testing, bootstrap intervals, sensitivity analysis, and exporting. All functions read from `kpi.*` / `dw.*` via SQLAlchemy and return DataFrames; none contain hardcoded results.

### 9.1 Revenue bridges

**Level 1: Orders × AOV** (from `kpi.v_revenue_bridge_orders_aov`). For months t−1 → t:

```
Revenue = Orders × AOV
ΔRevenue = (O1 − O0) × A0          [orders effect]
         + O1 × (A1 − A0)          [AOV effect]
```

Further split the AOV effect using `AOV = items_per_order × avg_item_price`: basket effect = `O1 × (IPO1 − IPO0) × ASP0`, price effect = `O1 × IPO1 × (ASP1 − ASP0)`. Verify components sum to the AOV effect.

**Level 2: Price-Volume-Mix (PVM) by category group** (`analysis/bridge.py`):

```python
def price_volume_mix(df: pd.DataFrame, base: str, compare: str, group_col: str = "category_group") -> pd.DataFrame:
    """df columns: year_month, <group_col>, units, revenue. Returns one row per group."""
```

Definitions (period 0 = base, 1 = compare; Q = total units; s = group's share of units; P = group's average price):

```
R_t = Q_t × Σ_c ( s_c,t × P_c,t )
Volume effect_c = (Q1 − Q0) × s_c,0 × P_c,0
Mix effect_c    = Q1 × (s_c,1 − s_c,0) × P_c,0
Price effect_c  = Q1 × s_c,1 × (P_c,1 − P_c,0)
Σ_c (volume + mix + price) = R_1 − R_0      [must hold within 1e-6]
```

Edge cases: a group present only in the compare period has `P_c,0` undefined, so set `P_c,0 = P_c,1` (price effect 0; its whole contribution lands in mix). A group present only in the base period has `P_c,1` undefined, so set `P_c,1 = P_c,0` (and `s_c,1 = 0`). Return also `delta_revenue_c = R_c,1 − R_c,0` and rank groups by absolute contribution. Output columns: `group, units_base, units_cmp, price_base, price_cmp, share_base, share_cmp, revenue_base, revenue_cmp, delta_revenue, volume_effect, mix_effect, price_effect`.

**Bridge for all consecutive months:** compute the Level-1 bridge and aggregate Level-2 effects (sum over groups of volume, mix, price) for every consecutive month pair in the window and export as `bridge_monthly.csv` so the dashboard can show any month's waterfall.

### 9.2 Driver drill-down

For each focal period pair (9.3), compute contribution to ΔRevenue (compare minus base) and rank the top and bottom contributors for each of:

1. **Category group** (and top 10 individual categories)
2. **Region and state** (customer location)
3. **Seller** (top 15 contributors, plus a "long tail" bucket); also top-10 share and HHI in both periods
4. **New vs returning customers** (revenue, orders, AOV, share)
5. **Payment type** (value share and average installments)

Output one tidy table per dimension: `dimension, member, revenue_base, revenue_cmp, delta_revenue, pct_of_total_delta`.

### 9.3 Focal periods (config `analysis.focal_periods`)

The pipeline analyzes (a) the `top_n_declines` largest negative MoM changes and `top_n_increases` largest positive MoM changes inside the window (auto-detected from `kpi.v_monthly_kpis`), (b) manual pairs listed in config (seed with the month after the Black Friday 2017 peak, and a mid-2018 slowdown, **after verifying in the data that both are real changes**), and (c) a year-over-year comparison for the months present in both years (Jan–Aug 2017 vs Jan–Aug 2018). Write `reports/focal_periods.json` listing each pair with its label and ΔRevenue. Seasonality (Black Friday, holidays) must be called out whenever a decline follows a spike; MoM comparisons after a peak are partly mean reversion, and the YoY view is the cleaner read.

### 9.4 Customer analysis

- **Repeat purchase rate** overall and by first-order month.
- **Cohort retention matrix**: pivot `kpi.v_cohort_retention` (cohorts within the window, `month_index` 0..`cohort.max_month_index`). Export long and wide formats. Expect very low M1+ retention; compute the weighted average M1, M3, M6 retention and state clearly that it is low. Investigate (do not assume) whether low repeat behavior is a feature of the business or a data artifact (the dataset is a sample; see limitations).
- **RFM segmentation**: from `kpi.v_rfm`; report segment sizes, revenue share, average review score, average AOV.
- **New vs returning revenue** over time; share of growth attributable to new customers.
- **Revenue per customer and customer count decomposition**: Revenue = Active customers × Revenue per customer, as a second bridge alongside Orders × AOV.

### 9.5 Operations, experience, and statistics (`analysis/operations.py`, `analysis/stats_utils.py`)

Population for all tests: `delivery_metrics_eligible AND review_score IS NOT NULL AND in_analysis_window`. Use `stats.alpha = 0.05`, `stats.bootstrap_resamples = 10000`, `stats.random_seed = 42`.

Utility functions in `stats_utils.py` (each unit-tested): `bootstrap_ci(data, stat_fn, n, seed, alpha)`, `cliffs_delta(x, y)`, `rank_biserial_from_u(u, n1, n2)`, `diff_in_proportions_ci(x1, n1, x2, n2, alpha)` (Newcombe or Wald; document the choice), `describe(series)` (n, mean, median, std, skew, P5/P25/P75/P95).

| Test | Question | Method | Report |
|---|---|---|---|
| T1 | Do late orders get lower review scores than on-time orders? | Mann-Whitney U (two-sided) on `review_score`, late vs not late | U, p-value, Cliff's δ (effect size), group medians and means, bootstrap 95% CI for the mean difference |
| T2 | Do late orders get more 1-star reviews? | Two-proportion z-test (or chi-square) on `review_score = 1` | proportions, difference, 95% CI, p-value |
| T3 | Does review score fall as delay grows? | Spearman ρ between `delay_days` and `review_score` for late orders; mean score by delay bucket | ρ with bootstrap CI, bucket table (from `kpi.v_delay_bucket_reviews`), monotonicity statement |
| T4 | Did the late-delivery rate change after the Black Friday 2017 volume spike? | Chi-square test of independence (late vs on-time) between a baseline window (Aug–Oct 2017) and the post-spike window (Nov 2017–Mar 2018, configurable) | late rates, difference, 95% CI, p-value, Cramér's V |
| T5 | Does the late-delivery effect on low scores survive controls? | Logistic regression: `low_score (≤2) ~ is_late + delivery_days + freight_ratio + category_group + customer_region + price_bucket` (statsmodels) | odds ratio for `is_late` with 95% CI; pseudo-R²; a clear statement that this is association, not causation |

Mandatory interpretation rules for every test: (1) report the effect size and CI next to the p-value; (2) with n ≈ 100k, tiny effects are "significant", so discuss practical size in plain language; (3) include a **correlation vs causation** paragraph: unobserved confounders (product quality, seller behavior, customer expectations, estimated-date padding by seller) could drive both lateness and low scores; (4) state test assumptions (independence, ordinal scale) and why a non-parametric test was chosen for ordinal 1–5 scores.

**Descriptive statistics** (output to `reports/descriptive_stats.md`): mean, median, std, skew, and percentiles for `price`, `freight_value`, `delivery_days`, `delay_days`, `payment_value`, `review_score`, with histograms (log scale where skewed). Also the freight ratio by region and the share of orders by number of items.

### 9.6 Outliers and sensitivity (`analysis/sensitivity.py`)

Re-run the headline results under alternative assumptions and show whether conclusions hold:

1. **Revenue definition:** booked (default) vs delivered-only (`kpi.v_monthly_kpis_delivered_only`). Compare monthly revenue, MoM %, and the identified largest-change months.
2. **Outliers:** include vs exclude rows flagged `dq_price_outlier`. Report monthly revenue difference and whether any focal-period conclusion changes.
3. **Window edges:** show what happens if 2016 and Sept–Oct 2018 are included (a short figure demonstrating the coverage artifact that justifies the window).
4. **Late threshold:** `late_threshold_days` of 0 vs 3; effect on T1/T2 results.

Output `reports/sensitivity_summary.md` with a table of "headline finding | default | alternative | conclusion changes?".

### 9.7 Analysis output files

All written to `data/exports/analysis/` (CSV and Parquet) and also referenced in `reports/`:

`monthly_kpis`, `bridge_monthly`, `pvm_focal_periods` (long format with `period_label`), `drivers_focal_periods` (long, one dimension per row group), `cohort_retention_long`, `cohort_retention_wide`, `rfm_segments`, `rfm_customers` (customer-level, anonymized keys only), `delay_bucket_reviews`, `delivery_monthly`, `test_results` (one row per test with statistic, p, effect size, CI), `seller_concentration_monthly`, `payment_mix_monthly`, `sensitivity_summary`.

---

## 10. Deliverable specifications

### 10.1 BI exports (`export` step)

Write to `data/exports/model/` the star-schema tables as CSV (UTF-8, header row, ISO dates, `.` decimal separator): `dim_date`, `dim_customer`, `dim_product`, `dim_seller`, `fact_orders`, `fact_order_items`, and also Parquet copies. Analysis tables (Section 9.7) go to `data/exports/analysis/`. Include `README_exports.md` listing each file, grain, row count, and how to relate it to others. Drop free-text columns (review comments are not exported). Customer-level exports use only the surrogate `customer_key` and `customer_unique_id` hash (SHA-256 of the id plus a salt from config); no raw IDs in `rfm_customers`.

### 10.2 Excel executive report (`reporting/excel_report.py`, XlsxWriter)

File `reports/olist_executive_summary.xlsx`, regenerated by `report`. Sheets:

1. `README`: purpose, run timestamp, data window, metric definitions summary.
2. `KPI_Summary`: headline KPIs for the latest full month, previous month, same month last year (if available), with growth cells computed by **Excel formulas** (not pasted values).
3. `Monthly_Trend`: monthly KPI table with a native line chart (revenue and 3M MA) and a column chart for orders vs AOV.
4. `Revenue_Bridge`: for each focal period, a bridge table and a waterfall-style chart (stacked column with an invisible base series, since XlsxWriter has no native waterfall).
5. `Category_Drivers`: top and bottom contributors with data bars.
6. `Customers`: new vs returning, cohort retention heatmap using conditional-format color scales, RFM segment table.
7. `Delivery_vs_Reviews`: delay bucket table and column chart.
8. `Data_Quality`: rule summary (pass/warn counts) from `audit.dq_results`.

Formatting: consistent number formats (BRL with thousands separators, percentages with one decimal), frozen header rows, column widths set, print setup landscape.

### 10.3 Dashboard specification (`docs/05_dashboard_spec.md`, `dashboard/dax_measures.md`, `dashboard/tableau_calculations.md`)

The agent writes the spec and measure definitions; the **human builds** the dashboard in Power BI Desktop or Tableau Public (Phase 7). Model: import the star-schema CSVs (`fact_orders`, `fact_order_items`, `dim_*`) plus analysis tables. Relationships: `fact_orders[purchase_date_key]` → `dim_date[date_key]` (active), `fact_orders[delivered_date_key]` → `dim_date[date_key]` (inactive); `fact_orders[customer_key]` → `dim_customer`; `fact_order_items[order_key]` → `fact_orders[order_key]` (many-to-one, single direction); `fact_order_items[product_key]`, `[seller_key]` → dims. Mark `dim_date` as the date table. DAX measures are in Appendix C.

Pages (each with a headline sentence at the top that states the takeaway, not just a chart title):

| Page | Visuals | Interactions |
|---|---|---|
| **1. Executive Overview** | KPI cards (Revenue, Orders, AOV, Active customers, On-time %, Avg review) each with MoM delta; monthly revenue line with 3M MA and an annotation for the Black Friday 2017 month; revenue by region (map or bar); top 10 categories bar | slicers: date range, region, category group |
| **2. Revenue Drivers** | revenue bridge waterfall for the selected month (orders effect, AOV effect, then category volume/mix/price) from `bridge_monthly`; bar of category ΔRevenue; table of top state contributors | single-select slicer: month to explain (compare vs previous month) |
| **3. Customers and Retention** | new vs returning revenue (stacked area); cohort retention heatmap (matrix with conditional color); RFM segment bars (size, revenue share); repeat-rate card with a note that low repeat purchase is a property of this dataset | cohort-month slicer |
| **4. Operations and Experience** | on-time rate and avg review score by month (combo chart); avg review by delay bucket (column); state map of avg delivery days; seller leaderboard (revenue, late rate, avg review) | slicer: state, category group |
| **5. About and Data Notes** | metric definitions, window and filters, data quality summary, limitations, dataset attribution and link to the repo | none |

Design rules: one color for the main measure and one highlight color; no 3D, no pies with more than 4 slices; sort bars; consistent number formatting; titles state insights; tooltips on every chart; accessible contrast; fits 16:9; every page ends with a "how to read this" caption. Publish to Power BI Service (publish-to-web) or Tableau Public and add the link and screenshots to the README.

### 10.4 Insight memo

`reports/memo_facts.json` (generated by `reporting/memo_facts.py`) holds every number the memo may cite: headline KPIs, focal-period deltas and decompositions, top contributors, retention figures, test results, sensitivity outcomes. The agent produces `docs/insight_memo_draft.md` from the template in Appendix D by filling placeholders from that JSON. **The human reviews, rewrites in their own voice, and saves the final as `docs/insight_memo.md`** (✋ checkpoint). Length: at most two pages (about 800–1,000 words) plus an appendix.

---

## 11. Automation and CI

### 11.1 Pipeline automation

- `python -m olist_analytics run-all` runs: profile → clean → load-staging → build-warehouse → build-kpis → dq-check → analyze → export → report. It records each step in `audit.pipeline_runs` (`run_id`, step, started_at, finished_at, status, rows_in, rows_out, message).
- **Quality gates:** the run halts on any rule with severity E failing (Section 6.2) and on any failed reconciliation (Section 7.6). Warnings are listed in `reports/dq_report.md`.
- **Automated data-quality checks** (`dq-check`) can run standalone against the database: PK uniqueness, FK orphans, null rates for key columns, value ranges, row-count reconciliation, revenue reconciliation, freshness (max purchase date vs expected), and metric sanity (for example no negative revenue month, M0 retention = 100%).
- **Automated recurring report:** `report` regenerates the Excel workbook and `reports/dq_report.md`. Document a local scheduling example in the README (cron on Linux/macOS, Task Scheduler on Windows) that runs `run-all` daily and archives the workbook with a date suffix.
- **Honest framing:** because the Olist data is a static historical snapshot, "refresh" simulates a recurring pipeline: the value is that the pipeline is idempotent, tested, and gated. State this in the README.

### 11.2 GitHub Actions (`.github/workflows/ci.yml`)

```yaml
name: ci
on:
  push: { branches: [main] }
  pull_request:
  schedule:
    - cron: "0 3 * * 1"      # weekly run on the fixture dataset: simulates a scheduled refresh
  workflow_dispatch:
jobs:
  test-and-run:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: olist
          POSTGRES_PASSWORD: olist_dev_password
          POSTGRES_DB: olist
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U olist -d olist"
          --health-interval 5s --health-timeout 5s --health-retries 10
    env:
      DATABASE_URL: postgresql+psycopg://olist:olist_dev_password@localhost:5432/olist
      OLIST_DATA_DIR: tests/fixtures/generated
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11", cache: pip }
      - run: pip install -e ".[dev]"
      - run: ruff check . && ruff format --check .
      - run: python tests/fixtures/make_fixture.py --out tests/fixtures/generated
      - run: pytest -q
      - run: python -m olist_analytics run-all
      - uses: actions/upload-artifact@v4
        with:
          name: reports
          path: reports/
```

The CI pipeline runs on the **fixture dataset** (the real data cannot be committed), so the fixture generator must produce orders inside the configured analysis window.

---

## 12. Testing strategy

| Layer | What | Tool |
|---|---|---|
| Unit: cleaning | each rule against the fixture's seeded defects; assert exact affected counts | pytest |
| Unit: validation | DQ framework returns PASS/WARN/FAIL correctly; E-severity raises | pytest |
| Unit: stats | `bootstrap_ci` covers the true mean on a known distribution (seeded); `cliffs_delta` on hand-computed samples; proportion CI against a known reference | pytest |
| Unit: bridge | PVM components sum to ΔRevenue for random inputs (property-style loop, 200 random cases incl. new/disappearing groups); Orders×AOV effects sum to Δ | pytest |
| Integration: warehouse | reconciliation checks from Section 7.6; no fan-out; FK integrity; flags consistent (`is_valid_revenue_order` false for canceled/unavailable) | pytest with `@pytest.mark.integration`, Postgres service |
| Integration: KPI views | M0 retention = 100%; `orders_effect + aov_effect = delta_revenue`; monthly revenue sums equal direct sum from fact table for the window; RFM segments are exhaustive and exclusive; delay buckets cover all eligible orders | pytest |
| Smoke | `run-all` on the fixture exits 0 and produces the expected files | CI |

**Fixture generator (`tests/fixtures/make_fixture.py`):** generates all 9 CSVs in Olist format with about 600 orders from a seeded RNG, dates inside the analysis window (include a few outside it to test the filter), and **deliberately seeded defects** with known counts: duplicate geolocation rows, out-of-Brazil coordinates, repeated review ids and multiple reviews per order, orders with impossible timestamp order, delivered orders with null delivered timestamp, orders with no items, a zero-value payment, `payment_installments = 0`, null and untranslated product categories, a price outlier, leading-zero zip codes, accented city names. The generator writes a `defects_manifest.json` with the expected counts, which tests assert against.

---

## 13. Implementation plan by phase

Suggested pace for one person working with an AI agent: about 4–5 weeks part-time. Each phase lists tasks, outputs, acceptance criteria (AC), and what the human should be able to explain afterwards ("Human learning goals", also written to `docs/LEARNING_NOTES.md`).

### Phase 0: Scaffolding and environment (Day 1)

**Tasks**
1. Create the repository layout (Section 4.3), `pyproject.toml`, `.gitignore` (ignore `data/`, `.env`, `reports/` except `reports/figures/`, `__pycache__`, `.venv`), `.env.example`, `Makefile`, `docker-compose.yml`.
2. Implement `config.py` (loads `config/settings.yaml`, overrides paths with env vars, validates required keys), `db.py` (SQLAlchemy engine factory, `run_sql_file(path)`, `run_sql_dir(dir)`), `cli.py` with all subcommands as stubs that log "not implemented", and `__main__.py`.
3. Write `sql/00_schemas.sql` and `sql/06_audit_ddl.sql` (`audit.pipeline_runs`, `audit.cleaning_log`, `audit.dq_results`).
4. Add a CI skeleton (lint and test only) and an initial `README.md` stub.
5. Create `config/brazil_regions.csv` (Section Appendix A lists the 27 UFs by region) and `config/category_groups.csv` seeded from Appendix B.

**AC:** `docker compose up -d` brings Postgres healthy; `python -m olist_analytics --help` lists all commands; `make test` and `make lint` pass; schemas `stg`, `dw`, `kpi`, `audit` exist after `python -m olist_analytics build-warehouse` (even with empty tables).

**Human learning goals:** what Docker Compose does, why config is separate from code.

### Phase 1: Data acquisition and profiling (Days 2–3)

**Tasks**
1. Implement `ingest.py`: verify the 9 files, read with explicit dtypes (IDs and zip as `str`), return a dict of DataFrames; clear error if files are missing.
2. Implement `profiling.py` and the `profile` command (Section 6.4), writing `reports/profile/*`.
3. Generate `docs/03_data_dictionary.md` from the profile (column, type, null %, example values), plus hand-written business meaning for each column (agent drafts, human refines).
4. In `notebooks/01_profiling.ipynb`, load the profile outputs and add short written observations about each known quirk in Section 3.3: confirm or contradict each with numbers.

**AC:** profile report exists for all 9 tables; the sanity-check table prints with within-tolerance flags; all 11 quirks in Section 3.3 are explicitly confirmed or contradicted in the notebook.

**Human learning goals:** grain of each table, primary/foreign keys, why `customer_unique_id` matters, what skew and nulls look like in real data.

### Phase 2: Cleaning, validation, staging (Days 4–7) ✋

**Tasks**
1. Build `tests/fixtures/make_fixture.py` with seeded defects and `defects_manifest.json` (Section 12) **first**.
2. Implement `cleaning.py` rule by rule (Section 6.2), each as a function returning `(cleaned_df, log_entries)`. Write `tests/test_cleaning.py` asserting exact counts from the manifest.
3. Implement `validation.py`: a small rule runner that evaluates E/W checks on cleaned frames and on `stg` tables, writes `audit.dq_results`, and raises on any E failure.
4. Write `sql/01_stg_ddl.sql` (typed tables with PKs, `NUMERIC(12,2)` money, flags) and `load.py` (create tables from DDL, append cleaned frames in FK-safe order, record row counts).
5. Implement the `clean` and `load-staging` commands and the reconciliation check X3 (money totals raw vs staged).
6. Render `reports/dq_report.md` and `.json`; write `docs/04_data_quality_log.md` (observed counts on the real data and rationale per rule).

**AC:** all cleaning tests pass on the fixture; on the real data, `clean` + `load-staging` run end to end; X1–X3 pass; every dropped or modified row count appears in `audit.cleaning_log`; staged order count equals raw order count; the DQ report lists each rule's observed count.

**✋ Checkpoint 1:** summarize the DQ findings, any rules whose observed counts differ greatly from Section 3.3, and any decisions made, in `docs/CHECKPOINTS.md`. The human reviews the cleaning decisions (these are interview talking points).

**Human learning goals:** missing values, duplicates, inconsistent formats, validation vs cleaning, flag-vs-drop trade-offs, audit trails.

### Phase 3: Dimensional model and warehouse (Days 8–10)

**Tasks**
1. Write `sql/02_dw_ddl.sql` per Section 7 (keys, constraints, types).
2. Write the load scripts in `sql/03_dw_load/` in dependency order. Build `fact_orders` from pre-aggregated CTEs (items, payments, reviews). Derive delivery metrics and flags exactly as defined in Section 5.1. Build dimensions with deterministic surrogate keys.
3. Create `config/category_groups.csv`, load it into a small `dw.ref_category_group` table, and populate `dim_product.category_group` (build fails if any category is unmapped; unmapped goes to `Other` only if `strict_category_groups: false`).
4. Write `sql/05_indexes.sql`; run `ANALYZE`.
5. Implement `warehouse.py` and the `build-warehouse` command (drops and recreates `dw`, runs scripts in order).
6. Write `docs/er_diagram.md` (Mermaid from Section 7.2) and export a PNG.
7. Write `tests/integration/test_warehouse.py` for the reconciliation checks in Section 7.6.

**AC:** `build-warehouse` runs on real data in under about 2 minutes; all reconciliation tests pass; no row fan-out; `dim_product.category_group` has no nulls; `fact_orders.delay_bucket` is non-null exactly where `delivery_metrics_eligible` is true.

**Human learning goals:** star schema vs normalized tables, grain, surrogate vs natural keys, why pre-aggregate before joining, fact vs dimension.

### Phase 4: KPI views and advanced SQL (Days 11–14)

**Tasks**
1. Implement every view in Section 8.1, using the reference SQL in 8.2 exactly where given and writing the rest to the stated specs.
2. Make sure every SQL construct in the Section 8.3 checklist appears at least once; add a checklist table to `docs/LEARNING_NOTES.md` mapping each construct to a file.
3. Implement `build-kpis` (runs `sql/04_kpi/*.sql`, then `REFRESH MATERIALIZED VIEW`).
4. Produce `docs/query_optimization.md` (Section 8.4) with before/after plans for two queries.
5. Write `tests/integration/test_kpi_views.py` (Section 12).
6. Write `docs/02_metric_dictionary.md` from Section 5, plus the exact SQL expression behind each metric.

**AC:** all views build; invariants in tests pass; `kpi.v_monthly_kpis` covers exactly the months in the analysis window with no gaps; M0 retention = 100% for every cohort; optimization doc contains two real before/after plans.

**Human learning goals:** window functions (`LAG`, running totals, `NTILE`), CTE structure, cohort logic, why the metric definition matters, reading `EXPLAIN`.

### Phase 5: Python analysis and statistics (Days 15–21) ✋

**Tasks**
1. Implement `analysis/stats_utils.py` with unit tests (Section 9.5).
2. Implement `analysis/bridge.py`: Level-1 and Level-2 bridges, PVM function, driver drill-downs (Sections 9.1–9.2), with `tests/test_bridge.py` (sum-to-delta property tests).
3. Implement focal period detection (Section 9.3) and write `reports/focal_periods.json`.
4. Implement `analysis/customers.py` (repeat rate, cohort matrix wide/long, RFM summaries).
5. Implement `analysis/operations.py` for tests T1–T5, and `analysis/sensitivity.py` (Section 9.6).
6. Implement the `analyze` command: runs everything and writes outputs listed in Section 9.7 plus figures to `reports/figures/` (revenue trend with window edges shown, bridge waterfalls, category contribution bars, cohort heatmap, delay-bucket vs review chart, distributions).
7. Build `notebooks/02_revenue_drivers.ipynb` and `notebooks/03_statistical_tests.ipynb` as narrative notebooks that call `src` functions and interpret outputs in markdown.
8. Implement `reporting/memo_facts.py` generating `reports/memo_facts.json`.

**AC:** all unit tests pass; `analyze` completes and produces every file in Section 9.7; each test result in `test_results` includes statistic, p-value, effect size, and CI; the sensitivity table states for each headline finding whether it survives the alternatives; figures are readable (labelled axes, titles that state the finding).

**✋ Checkpoint 2:** write the top findings and any surprises to `docs/CHECKPOINTS.md`. The human validates that the explanations are plausible and that nothing is over-claimed (especially causal language) before the memo is written.

**Human learning goals:** decomposition thinking (orders × AOV, price/volume/mix), correlation vs causation, hypothesis testing, effect sizes vs p-values, confidence intervals, bootstrap, sensitivity analysis.

### Phase 6: Exports, Excel report, memo draft (Days 22–24)

**Tasks**
1. Implement `exports.py` and the `export` command (Section 10.1) including `README_exports.md`.
2. Implement `reporting/excel_report.py` and the `report` command (Section 10.2).
3. Generate `docs/insight_memo_draft.md` from `memo_facts.json` and the Appendix D template; write `docs/assumptions_and_limitations.md`.
4. Draft the dashboard specification files (`docs/05_dashboard_spec.md`, `dashboard/dax_measures.md`, `dashboard/tableau_calculations.md`) per Section 10.3 and Appendix C.

**AC:** exports exist with correct row counts matching the warehouse; the Excel workbook opens without errors, has all 8 sheets, formula cells compute (no `#REF!`/`#NAME?`), and charts render; every number in the memo draft appears in `memo_facts.json`.

### Phase 7: Dashboard (human-led, agent-assisted) (Days 25–29) ✋

**Tasks (human)**
1. Choose Power BI Desktop or Tableau Public. Import the model CSVs and analysis CSVs; create relationships as in Section 10.3.
2. Create the measures from Appendix C (or Tableau equivalents), build the five pages, apply design rules, add tooltips and headline sentences.
3. Publish (Power BI publish-to-web or Tableau Public), capture screenshots into `dashboard/screenshots/`, and add the link to the README.
4. Write the final `docs/insight_memo.md` in your own voice from the draft.

**Tasks (agent, on request):** generate DAX/calculated field variations, review the spec, write alt-text and the "how to read this" captions, check that dashboard totals match `kpi.v_monthly_kpis` (a reconciliation checklist in `dashboard/RECONCILIATION.md`: Revenue, Orders, AOV for three sample months must match SQL to the cent).

**AC:** dashboard totals reconcile with SQL for at least three months; each page has a takeaway headline; link and screenshots are in the README; the memo is finalized by the human.

**Human learning goals:** star-schema modeling in a BI tool, DAX context (filter vs row context), choosing charts, data storytelling.

### Phase 8: Automation, CI, documentation polish (Days 30–33)

**Tasks**
1. Implement `run-all` with step logging to `audit.pipeline_runs` and halting on E-severity failures; implement `dq-check` standalone.
2. Complete the GitHub Actions workflow (Section 11.2); confirm it passes on the fixture; add the CI badge to the README.
3. Complete the README (Section 14.1), `docs/01_business_context.md`, `docs/LEARNING_NOTES.md`, `docs/RESUME_AND_INTERVIEW.md`.
4. Run a clean-clone test: fresh clone, new virtualenv, `docker compose up -d`, place data, `make all`; fix every friction point; time the run and record it in the README.

**AC:** a stranger can reproduce the project from the README alone; CI is green; `make all` succeeds from a clean clone; no secrets or data are tracked by git (`git ls-files` check).

### Phase 9: Stretch goals (optional, only after Definition of Done is met)

Port SQL models to dbt (Postgres adapter) with tests; add a simple seasonal-naive forecast baseline with error metrics; sentiment-free review text keyword frequency (top words in 1-star reviews, Portuguese stopwords); add `fact_payments` analysis of installment behavior; Great Expectations suite replacing the custom validation runner.

---

## 14. Documentation, resume and interview-readiness deliverables

### 14.1 README structure

1. Title, one-sentence pitch, CI badge, dashboard link, 2–3 screenshots.
2. **The business question** and the headline findings (3 bullets, filled from the final memo).
3. Architecture diagram (Section 4.1) and star-schema diagram.
4. Tech stack and why.
5. Quickstart: prerequisites, clone, `.env`, Docker, data download instructions, `make all`, expected runtime.
6. Repository tour.
7. Key analytical methods (bridge, PVM, cohorts, RFM, tests) in one paragraph each.
8. Data quality summary (top five issues found and how they were handled).
9. Assumptions and limitations (summary; link to `docs/assumptions_and_limitations.md`).
10. How to run tests and CI.
11. Dataset attribution and license note.

### 14.2 Assumptions and limitations (must appear in `docs/assumptions_and_limitations.md`)

Dataset is an anonymized sample, so absolute revenue is not the company's true revenue; no cost or margin data, so profitability can't be assessed; no marketing, traffic, or channel data, so acquisition drivers can't be tested; no returns/refund data; reviews are one per order and self-selected; customer identity depends on `customer_unique_id` and low repeat rates may partly reflect the sampling or the marketplace model; coverage is thin outside the window; seasonality can't be separated from trend with fewer than two full years; delivery lateness is measured against Olist's own estimate, which sellers and the platform may pad; associations in the tests are not causal.

### 14.3 Resume bullet templates (fill with real results; keep one line each, start with a verb, include a number)

- Built an end-to-end analytics pipeline (**Python, pandas, PostgreSQL**) cleaning 9 relational tables (~[N]k rows) with [N] automated data-quality rules and a full audit log, modeled into a star schema with reconciled revenue totals.
- Wrote [N] analytical **SQL** views using CTEs and window functions (cohort retention, RFM, running totals, rankings) and cut a key query from [X] ms to [Y] ms via indexing and materialization.
- Diagnosed a [X]% month-over-month revenue change by decomposing into orders, AOV, and category price-volume-mix, identifying [driver] as [Z]% of the movement.
- Tested whether late deliveries lower customer ratings (Mann-Whitney, bootstrap CIs, logistic regression): late orders scored [X] points lower (95% CI [a, b]), while documenting why the result is not causal.
- Built a [Power BI/Tableau] dashboard (5 pages, [N] measures) and an automated Excel executive report; delivered a 2-page insight memo with [N] recommendations.
- Added unit and integration tests ([N] tests) and a GitHub Actions pipeline with data-quality gates.

### 14.4 Interview-readiness checklist (the human should be able to answer all of these; the agent drafts model answers in `docs/RESUME_AND_INTERVIEW.md`)

1. Walk me through the project in two minutes. What was the question and what did you find?
2. Why a star schema? What is the grain of each fact table? What would go wrong if you joined items, payments, and reviews in one query?
3. How did you define revenue and why exclude freight? How would conclusions change with delivered-only revenue?
4. Why `customer_unique_id`? How did you define a new vs returning customer?
5. Explain the revenue bridge. Why do the effects sum to the change? What is the interaction term and how did you handle it?
6. What does PVM tell you that a simple category growth table doesn't?
7. Write a query live: month-over-month revenue growth; top 3 categories per month; customers with 2+ orders.
8. Explain `LAG`, `NTILE`, `PARTITION BY`, and a running total in plain language.
9. What data quality issues did you find? Which did you fix, flag, or drop and why? How did you prove nothing was lost silently?
10. Why Mann-Whitney instead of a t-test? Why report effect size next to the p-value? What is a confidence interval?
11. Does lateness *cause* bad reviews? What would you need to claim that? What A/B test or quasi-experiment could help?
12. Retention is low. Is that a data artifact or a business reality? How would you check?
13. What assumptions or limitations could change your recommendations?
14. How is the pipeline automated and how do you know it isn't silently producing wrong numbers?
15. What would you do next with more data or time?

---

## 15. Pitfalls and risk register

| Risk | Consequence | Mitigation |
|---|---|---|
| Join fan-out (items × payments × reviews) | Revenue overstated several-fold | Pre-aggregate children to order grain; reconciliation tests |
| Using `customer_id` as the person key | Repeat rate near zero; wrong new/returning | Use `customer_unique_id`; test distinct counts |
| Zip prefixes read as integers | Lost leading zeros, bad geolocation joins | Read as `str`, zero-pad, test with fixture |
| Including 2016 and Sept–Oct 2018 | Fake growth/collapse in MoM | Analysis window; sensitivity chart |
| Treating post-spike decline as a "problem" | Wrong conclusion (mean reversion, seasonality) | YoY comparison; explicit seasonality discussion |
| Multiple reviews per order | Double-counted scores | Keep one per order, log the rule |
| Voucher or zero-value payments | Payment reconciliation noise | Flag; report match rate; don't force equality |
| Float money in DB | Rounding drift | `NUMERIC(12,2)` |
| p-hacking or over-claiming causality | Loss of credibility | Effect sizes, CIs, explicit causal caveats, sensitivity table |
| Cleaning logic duplicated in SQL and Python | Inconsistencies | Python cleans, SQL models; single source per rule |
| Agent-hallucinated insights | Memo contradicts data | `memo_facts.json` is the only source; human review |
| Human can't explain agent-written code | Interview failure | Rule 8 (readable code), learning notes, interview checklist |
| Committing licensed data or secrets | License/security issue | `.gitignore`; `git ls-files` check in Phase 8 |
| Windows vs Unix differences | Broken Makefile | CLI is source of truth; Makefile is optional |
| Time zone handling | Off-by-one-day delay metrics | Keep timestamps naive; compare dates for delay |

---

## 16. Definition of Done

- [ ] `make all` (or `python -m olist_analytics run-all`) runs from a clean clone on the real data without errors and produces every output in Sections 9.7 and 10.
- [ ] `ruff` and `pytest` pass; CI is green on the fixture dataset.
- [ ] Every reconciliation check in Section 7.6 passes; dashboard totals match SQL for at least three sample months.
- [ ] `audit.cleaning_log` accounts for every changed or removed row; `docs/04_data_quality_log.md` is complete.
- [ ] Every SQL construct in Section 8.3 is used; `docs/query_optimization.md` has two before/after plans.
- [ ] Statistical results include effect sizes, CIs, and correlation-vs-causation statements; sensitivity analysis is complete.
- [ ] Excel report, exports, dashboard (published link + screenshots), and the final human-written insight memo exist.
- [ ] README, metric dictionary, data dictionary, ER diagram, assumptions and limitations, learning notes, and resume/interview document are complete.
- [ ] No data files, secrets, or `.env` tracked in git.
- [ ] The owner has answered all Section 14.4 questions aloud without notes.

---

## Appendix A: `config/settings.yaml`

```yaml
database:
  url_env: DATABASE_URL            # read from environment / .env

paths:
  raw_dir: data/raw                # overridden by OLIST_DATA_DIR if set
  interim_dir: data/interim
  exports_dir: data/exports
  reports_dir: reports

cleaning:
  strict_category_groups: true     # fail build if a category has no group
  max_row_loss_pct:                # per-table tolerance for rule X1 (percent)
    orders: 1.0
    order_items: 1.0
    order_payments: 1.0
    order_reviews: 15.0            # review collapse legitimately removes rows
    customers: 0.0
    products: 0.0
    sellers: 0.0
    geolocation: 100.0             # collapsed to one row per zip prefix by design
  brazil_bbox:
    lat_min: -33.75
    lat_max: 5.27
    lng_min: -73.99
    lng_max: -34.79
  category_patches:                # categories missing from the translation file
    pc_gamer: pc_gaming
    portateis_cozinha_e_preparadores_de_alimentos: portable_kitchen_and_food_preparers

analysis:
  window_start: "2017-01-01"
  window_end: "2018-08-31"
  excluded_statuses: [canceled, unavailable]
  late_threshold_days: 0
  special_events:
    - { date: "2017-11-24", name: "Black Friday 2017" }
  focal_periods:
    top_n_declines: 3
    top_n_increases: 2
    manual:                        # verify these in the data before keeping them
      - { base: "2017-11", compare: "2017-12", label: "Post-Black-Friday month" }
      - { base: "2018-05", compare: "2018-06", label: "Mid-2018 slowdown" }
    yoy: { base_year: 2017, compare_year: 2018, months: [1, 2, 3, 4, 5, 6, 7, 8] }
  rfm:
    snapshot_offset_days: 1
  cohort:
    max_month_index: 12
  operations_tests:
    baseline_window: ["2017-08-01", "2017-10-31"]
    post_spike_window: ["2017-11-01", "2018-03-31"]

stats:
  alpha: 0.05
  bootstrap_resamples: 10000
  random_seed: 42
  outliers:
    method: iqr_log                # IQR on log1p(value)
    iqr_multiplier: 3.0

export:
  id_hash_salt_env: ID_HASH_SALT   # optional; defaults to a fixed project salt if unset
```

`config/brazil_regions.csv` (27 UFs; header `uf,region`):

- North: AC, AP, AM, PA, RO, RR, TO
- Northeast: AL, BA, CE, MA, PB, PE, PI, RN, SE
- Central-West: DF, GO, MT, MS
- Southeast: ES, MG, RJ, SP
- South: PR, RS, SC

---

## Appendix B: Category group mapping seed

Use the **exact English category spellings** from `product_category_name_translation.csv` (several contain source typos such as `fashio_female_clothing` and `costruction_tools_garden`). Generate `config/category_groups.csv` (`category_name_english,category_group`) from this seed, then assert that every category in the translation file (plus the two patched names and `unknown`) maps to exactly one group. The human should review the grouping.

| Group | Categories |
|---|---|
| Home and Furniture | bed_bath_table, furniture_bedroom, furniture_decor, furniture_living_room, furniture_mattress_and_upholstery, home_comfort_2, home_confort, housewares, kitchen_dining_laundry_garden_furniture, la_cuisine, office_furniture |
| Appliances | air_conditioning, home_appliances, home_appliances_2, small_appliances, small_appliances_home_oven_and_coffee, portable_kitchen_and_food_preparers |
| Electronics and Computing | audio, cine_photo, computers, computers_accessories, consoles_games, electronics, fixed_telephony, pc_gaming, tablets_printing_image, telephony |
| Health and Beauty | diapers_and_hygiene, health_beauty, perfumery |
| Fashion and Accessories | fashio_female_clothing, fashion_bags_accessories, fashion_male_clothing, fashion_shoes, fashion_sport, fashion_underwear_beach, luggage_accessories, watches_gifts |
| Sports, Leisure and Hobbies | art, arts_and_craftmanship, musical_instruments, sports_leisure |
| Toys, Baby and Kids | baby, fashion_childrens_clothes, toys |
| Garden, Tools and Construction | construction_tools_construction, construction_tools_lights, construction_tools_safety, costruction_tools_garden, costruction_tools_tools, garden_tools, home_construction |
| Auto | auto |
| Books, Media and Stationery | books_general_interest, books_imported, books_technical, cds_dvds_musicals, dvds_blu_ray, music, stationery |
| Food and Drink | drinks, food, food_drink |
| Pet | pet_shop |
| Gifts and Seasonal | christmas_supplies, flowers, party_supplies |
| Business and Services | agro_industry_and_commerce, industry_commerce_and_business, market_place, security_and_services, signaling_and_security |
| Unknown | unknown |

---

## Appendix C: Power BI DAX measures

Adapt to your table and column names. Flags `is_valid_revenue_order` and `in_analysis_window` come from the warehouse exports.

```dax
Revenue =
CALCULATE (
    SUM ( fact_order_items[price] ),
    fact_order_items[is_valid_revenue_order] = TRUE (),
    fact_order_items[in_analysis_window] = TRUE ()
)

Orders =
CALCULATE (
    DISTINCTCOUNT ( fact_order_items[order_id] ),
    fact_order_items[is_valid_revenue_order] = TRUE (),
    fact_order_items[in_analysis_window] = TRUE ()
)

Units =
CALCULATE (
    COUNTROWS ( fact_order_items ),
    fact_order_items[is_valid_revenue_order] = TRUE (),
    fact_order_items[in_analysis_window] = TRUE ()
)

AOV = DIVIDE ( [Revenue], [Orders] )
Items per Order = DIVIDE ( [Units], [Orders] )
Avg Item Price = DIVIDE ( [Revenue], [Units] )

Active Customers =
CALCULATE (
    DISTINCTCOUNT ( fact_orders[customer_key] ),
    fact_orders[is_valid_revenue_order] = TRUE (),
    fact_orders[in_analysis_window] = TRUE ()
)

Revenue PM = CALCULATE ( [Revenue], DATEADD ( dim_date[date], -1, MONTH ) )
Revenue MoM % = DIVIDE ( [Revenue] - [Revenue PM], [Revenue PM] )

Revenue 3M MA =
VAR _MaxDate = MAX ( dim_date[date] )
VAR _Window = DATESINPERIOD ( dim_date[date], _MaxDate, -3, MONTH )
RETURN
    DIVIDE ( CALCULATE ( [Revenue], _Window ), 3 )

On-Time % =
VAR _Eligible =
    CALCULATE (
        COUNTROWS ( fact_orders ),
        fact_orders[delivery_metrics_eligible] = TRUE (),
        fact_orders[in_analysis_window] = TRUE ()
    )
VAR _OnTime =
    CALCULATE (
        COUNTROWS ( fact_orders ),
        fact_orders[delivery_metrics_eligible] = TRUE (),
        fact_orders[in_analysis_window] = TRUE (),
        fact_orders[is_late] = FALSE ()
    )
RETURN
    DIVIDE ( _OnTime, _Eligible )

Avg Review Score =
CALCULATE (
    AVERAGE ( fact_orders[review_score] ),
    fact_orders[in_analysis_window] = TRUE ()
)

Freight Ratio = DIVIDE ( SUM ( fact_order_items[freight_value] ), SUM ( fact_order_items[price] ) )
```

Tableau equivalent pattern: `SUM(IF [is_valid_revenue_order] AND [in_analysis_window] THEN [price] END)` for Revenue; `COUNTD(IF [is_valid_revenue_order] AND [in_analysis_window] THEN [order_id] END)` for Orders; use a table calculation (`PREVIOUS_VALUE` / `LOOKUP(...,-1)`) for MoM and a window average (`WINDOW_AVG(SUM([Revenue]), -2, 0)`) for the 3-month moving average. Document each in `dashboard/tableau_calculations.md`.

---

## Appendix D: Insight memo template

```
# [Title that states the main finding]

**To:** [stakeholder]   **From:** [name]   **Date:** [date]   **Data:** Olist orders, Jan 2017 – Aug 2018

## 1. Question
One sentence: what the business wanted to know.

## 2. Bottom line (3–5 bullets)
- Revenue [rose/fell] [X]% between [period A] and [period B], driven mainly by [driver] ([Y]% of the change).
- [Second most important finding with a number.]
- [Customer finding: repeat rate / retention with a number and caution.]
- [Operations finding: lateness vs reviews, effect size and CI, with causal caveat.]
- Recommended action: [one sentence].

## 3. What happened
Trend in 2–3 sentences with the key chart. Mention seasonality (Black Friday) and the window choice.

## 4. Why (drivers)
Revenue bridge (orders effect, AOV effect), category price-volume-mix, regional and seller contributions, new vs returning customers. Quantify each; say which are large and which are noise.

## 5. What we tested
For each statistical test: plain-language question, result with effect size and 95% CI, what it does and does not prove.

## 6. Recommendations
Each recommendation: action, evidence (number), expected impact or next test, owner, and a risk.

## 7. Assumptions and limitations
Definitions (revenue, valid order, window), sampling caveat, no cost/marketing data, correlation vs causation, sensitivity results.

## Appendix
Metric definitions, data quality summary, link to dashboard and repository.
```