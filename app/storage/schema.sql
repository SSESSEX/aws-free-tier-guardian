CREATE TABLE IF NOT EXISTS scan_runs (
    id SERIAL PRIMARY KEY,
    scan_time TIMESTAMPTZ NOT NULL,
    aws_profile TEXT NOT NULL,
    aws_region TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS resources (
    id SERIAL PRIMARY KEY,
    scan_run_id INTEGER NOT NULL REFERENCES scan_runs(id) ON DELETE CASCADE,
    service TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    region TEXT NOT NULL,
    raw_json JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS findings (
    id SERIAL PRIMARY KEY,
    resource_id INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_resources_scan_run_id
ON resources(scan_run_id);

CREATE INDEX IF NOT EXISTS idx_resources_service
ON resources(service);

CREATE INDEX IF NOT EXISTS idx_findings_resource_id
ON findings(resource_id);

CREATE INDEX IF NOT EXISTS idx_findings_status
ON findings(status);

CREATE INDEX IF NOT EXISTS idx_findings_severity
ON findings(severity);