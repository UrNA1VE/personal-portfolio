select
    vh.visit_id,
    vh.hour_ts,
    vh.calendar_date,
    vh.hour_of_day,
    vh.facility_id,
    f.facility_name,
    f.region,
    vh.service_id,
    s.service_name,
    s.service_group
from {{ ref('int_visit_hours') }} vh
join {{ ref('stg_facilities') }} f using (facility_id)
join {{ ref('stg_services') }} s using (service_id)
