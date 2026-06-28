select
    hour_ts,
    calendar_date,
    hour_of_day,
    facility_id,
    facility_name,
    service_id,
    service_name,
    count(distinct visit_id) as census
from {{ ref('int_patient_hourly_snapshot') }}
group by 1, 2, 3, 4, 5, 6, 7
