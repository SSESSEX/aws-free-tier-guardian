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


-- Resource count by service
SELECT
    sr.id AS scan_run_id,
    r.service,
    r.resource_type,
    COUNT(*) AS resource_count
FROM resources r
JOIN scan_runs sr
    ON r.scan_run_id = sr.id
GROUP BY
    sr.id,
    r.service,
    r.resource_type
ORDER BY
    sr.id DESC,
    r.service;


-- Findings by severity
SELECT
    sr.id AS scan_run_id,
    f.severity,
    COUNT(*) AS finding_count
FROM findings f
JOIN resources r
    ON f.resource_id = r.id
JOIN scan_runs sr
    ON r.scan_run_id = sr.id
GROUP BY
    sr.id,
    f.severity
ORDER BY
    sr.id DESC,
    f.severity;


-- Findings by status
SELECT
    sr.id AS scan_run_id,
    f.status,
    COUNT(*) AS finding_count
FROM findings f
JOIN resources r
    ON f.resource_id = r.id
JOIN scan_runs sr
    ON r.scan_run_id = sr.id
GROUP BY
    sr.id,
    f.status
ORDER BY
    sr.id DESC,
    f.status;


-- Highest-risk findings
SELECT
    sr.id AS scan_run_id,
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
JOIN scan_runs sr
    ON r.scan_run_id = sr.id
WHERE f.status IN ('FAIL', 'WARN')
ORDER BY
    sr.id DESC,
    CASE f.severity
        WHEN 'CRITICAL' THEN 1
        WHEN 'HIGH' THEN 2
        WHEN 'MEDIUM' THEN 3
        WHEN 'LOW' THEN 4
        ELSE 5
    END;


-- Resources missing recommended tags
SELECT
    sr.id AS scan_run_id,
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
JOIN scan_runs sr
    ON r.scan_run_id = sr.id
WHERE f.check_name LIKE '%REQUIRED_TAGS%'
ORDER BY
    sr.id DESC,
    r.service;


-- Public exposure findings
SELECT
    sr.id AS scan_run_id,
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
JOIN scan_runs sr
    ON r.scan_run_id = sr.id
WHERE
    f.check_name ILIKE '%PUBLIC%'
    OR f.check_name ILIKE '%WORLD%'
    OR f.message ILIKE '%internet%'
ORDER BY
    sr.id DESC,
    f.severity;