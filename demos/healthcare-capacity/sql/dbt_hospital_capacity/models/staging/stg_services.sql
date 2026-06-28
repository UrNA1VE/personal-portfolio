select
    trim(service_id)::varchar as service_id,
    trim(service_name)::varchar as service_name,
    trim(service_group)::varchar as service_group
from {{ source('raw', 'services') }}
