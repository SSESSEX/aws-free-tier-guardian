select
    date(sr.scan_time) as scan_date,
    count(distinct sr.scan_run_id) as scan_runs,
    count(distinct r.resource_pk) as resources_scanned,
    count(f.finding_id) as total_findings,
    sum(case when f.status = 'WARN' then 1 else 0 end) as warnings,
    sum(case when f.status = 'FAIL' then 1 else 0 end) as failures,
    sum(case when f.severity = 'HIGH' then 1 else 0 end) as high_severity_findings
from {{ ref('stg_scan_runs') }} sr
left join {{ ref('stg_resources') }} r
    on sr.scan_run_id = r.scan_run_id
left join {{ ref('stg_findings') }} f
    on r.resource_pk = f.resource_pk
group by
    date(sr.scan_time)