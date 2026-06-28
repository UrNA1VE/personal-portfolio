select
    capacity_date::date as capacity_date,
    trim(facility_id)::varchar as facility_id,
    trim(service_id)::varchar as service_id,
    staffed_beds::integer as staffed_beds
from {{ source('raw', 'capacity') }}
