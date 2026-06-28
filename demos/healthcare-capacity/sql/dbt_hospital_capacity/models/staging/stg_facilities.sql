select
    trim(facility_id)::varchar as facility_id,
    trim(facility_name)::varchar as facility_name,
    trim(region)::varchar as region
from {{ source('raw', 'facilities') }}
