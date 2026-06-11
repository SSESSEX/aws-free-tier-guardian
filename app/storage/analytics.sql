-- ============================================================
-- AWS Free-Tier Guardian Analytics Queries
-- ============================================================

-- Latest scan runs
SELECT
    id,
    scan_time,
    aws_profile,
    aws_region,
    created_at
FROM scan_runs
ORDER BY id DESC
LIMIT 10;


-- Latest scan resource count by service
WITH latest_scan AS (
    SELECT MAX(id) AS scan_run_id
    FROM scan_runs
)
SELECT
    r.service,
    r.resource_type,
    COUNT(*) AS resource_count
FROM resources r
JOIN latest_scan ls
    ON r.scan_run_id = ls.scan_run_id
GROUP BY
    r.service,
    r.resource_type
ORDER BY
    r.service,
    r.resource_type;


-- Latest scan findings by status
WITH latest_scan AS (
    SELECT MAX(id) AS scan_run_id
    FROM scan_runs
)
SELECT
    f.status,
    COUNT(*) AS finding_count
FROM findings f
JOIN resources r
    ON f.resource_id = r.id
JOIN latest_scan ls
    ON r.scan_run_id = ls.scan_run_id
GROUP BY
    f.status
ORDER BY
    f.status;


-- Latest scan findings by severity
WITH latest_scan AS (
    SELECT MAX(id) AS scan_run_id
    FROM scan_runs
)
SELECT
    f.severity,
    COUNT(*) AS finding_count
FROM findings f
JOIN resources r
    ON f.resource_id = r.id
JOIN latest_scan ls
    ON r.scan_run_id = ls.scan_run_id
GROUP BY
    f.severity
ORDER BY
    CASE f.severity
        WHEN 'CRITICAL' THEN 1
        WHEN 'HIGH' THEN 2
        WHEN 'MEDIUM' THEN 3
        WHEN 'LOW' THEN 4
        ELSE 5
    END;


-- Latest scan highest-risk findings
WITH latest_scan AS (
    SELECT MAX(id) AS scan_run_id
    FROM scan_runs
)
SELECT
    r.service,
    r.resource_type,
    r.resource_id,
    f.check_name,
    f.status,
    f.severity,
    f.message
FROM findings f
JOIN resources r
    ON f.resource_id = r.id
JOIN latest_scan ls
    ON r.scan_run_id = ls.scan_run_id
WHERE f.status IN ('FAIL', 'WARN')
ORDER BY
    CASE f.severity
        WHEN 'CRITICAL' THEN 1
        WHEN 'HIGH' THEN 2
        WHEN 'MEDIUM' THEN 3
        WHEN 'LOW' THEN 4
        ELSE 5
    END,
    r.service,
    r.resource_id;


-- Latest scan resources missing recommended tags
WITH latest_scan AS (
    SELECT MAX(id) AS scan_run_id
    FROM scan_runs
)
SELECT
    r.service,
    r.resource_type,
    r.resource_id,
    f.status,
    f.severity,
    f.message
FROM findings f
JOIN resources r
    ON f.resource_id = r.id
JOIN latest_scan ls
    ON r.scan_run_id = ls.scan_run_id
WHERE f.check_name LIKE '%REQUIRED_TAGS%'
ORDER BY
    r.service,
    r.resource_type;


-- Latest scan public exposure findings
WITH latest_scan AS (
    SELECT MAX(id) AS scan_run_id
    FROM scan_runs
)
SELECT
    r.service,
    r.resource_type,
    r.resource_id,
    f.check_name,
    f.status,
    f.severity,
    f.message
FROM findings f
JOIN resources r
    ON f.resource_id = r.id
JOIN latest_scan ls
    ON r.scan_run_id = ls.scan_run_id
WHERE
    f.check_name ILIKE '%PUBLIC%'
    OR f.check_name ILIKE '%WORLD%'
    OR f.message ILIKE '%internet%'
ORDER BY
    CASE f.severity
        WHEN 'CRITICAL' THEN 1
        WHEN 'HIGH' THEN 2
        WHEN 'MEDIUM' THEN 3
        WHEN 'LOW' THEN 4
        ELSE 5
    END,
    r.service;


-- Finding trend across scan runs
SELECT
    sr.id AS scan_run_id,
    sr.scan_time,
    f.status,
    COUNT(*) AS finding_count
FROM findings f
JOIN resources r
    ON f.resource_id = r.id
JOIN scan_runs sr
    ON r.scan_run_id = sr.id
GROUP BY
    sr.id,
    sr.scan_time,
    f.status
ORDER BY
    sr.id DESC,
    f.status;