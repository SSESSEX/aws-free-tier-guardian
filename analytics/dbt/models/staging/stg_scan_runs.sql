select
    id as scan_run_id,
    scan_time,
    aws_profile,
    aws_region
from {{ source('guardian', 'scan_runs') }}