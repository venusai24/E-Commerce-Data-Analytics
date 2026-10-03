CREATE TABLE IF NOT EXISTS audit.pipeline_runs (
    run_id SERIAL PRIMARY KEY,
    step VARCHAR(100) NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    status VARCHAR(50),
    rows_in INT,
    rows_out INT,
    message TEXT
);

CREATE TABLE IF NOT EXISTS audit.cleaning_log (
    log_id SERIAL PRIMARY KEY,
    run_id INT,
    rule_id VARCHAR(50),
    table_name VARCHAR(100),
    rows_affected INT,
    action VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit.dq_results (
    result_id SERIAL PRIMARY KEY,
    run_id INT,
    rule_id VARCHAR(50),
    table_name VARCHAR(100),
    rows_checked INT,
    rows_affected INT,
    pct_affected NUMERIC(6,2),
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
