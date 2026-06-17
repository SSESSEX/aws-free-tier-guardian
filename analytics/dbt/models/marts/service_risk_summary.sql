select
    r.scan_run_id,
    r.service,
    count(distinct r.resource_pk) as resources_scanned,
    count(f.finding_id) as total_findings,
    sum(case when f.status = 'PASS' then 1 else 0 end) as passes,
    sum(case when f.status = 'WARN' then 1 else 0 end) as warnings,
    sum(case when f.status = 'FAIL' then 1 else 0 end) as failures,
    sum(case when f.severity = 'HIGH' then 1 else 0 end) as high_severity_findings,
    sum(case when f.severity = 'MEDIUM' then 1 else 0 end) as medium_severity_findings,
    sum(case when f.severity = 'LOW' then 1 else 0 end) as low_severity_findings
from {{ ref('stg_resources') }} r
left join {{ ref('stg_findings') }} f
    on r.resource_pk = f.resource_pk
group by
    r.scan_run_id,
    r.service