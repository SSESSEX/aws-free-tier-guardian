select
    id as resource_pk,
    scan_run_id,
    service,
    resource_type,
    resource_id,
    region
from {{ source('guardian', 'resources') }}