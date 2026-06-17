select
    id as finding_id,
    resource_id as resource_pk,
    check_name,
    status,
    severity,
    message
from {{ source('guardian', 'findings') }}