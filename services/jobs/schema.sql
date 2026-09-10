-- Nightly orchestration (scripts/nightly_export.py). Not pipeline_runs.
-- Postgres: reporting.job_runs. SQLite fallback uses job_runs (no schema).
-- ensure_job_runs_schema() applies this shape at process start.

CREATE SCHEMA IF NOT EXISTS reporting;

CREATE TABLE IF NOT EXISTS reporting.job_runs (
    id uuid PRIMARY KEY,
    job_name text NOT NULL,
    target_date date NOT NULL,
    status text NOT NULL,
    started_at timestamptz,
    finished_at timestamptz,
    error_message text,
    created_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_job_runs_job_name_target_date
    ON reporting.job_runs (job_name, target_date);
