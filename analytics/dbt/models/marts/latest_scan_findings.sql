with latest_scan as (
    select max(scan_run_id) as scan_run_id
    from {{ ref('stg_scan_runs') }}
)

select
    sr.scan_run_id,
    sr.scan_time,
    r.service,
    r.resource_type,
    r.resource_id,
    f.check_name,
    f.status,
    f.severity,
    f.message
from {{ ref('stg_scan_runs') }} sr
join latest_scan ls
    on sr.scan_run_id = ls.scan_run_id
join {{ ref('stg_resources') }} r
    on sr.scan_run_id = r.scan_run_id
left join {{ ref('stg_findings') }} f
    on r.resource_pk = f.resource_pk