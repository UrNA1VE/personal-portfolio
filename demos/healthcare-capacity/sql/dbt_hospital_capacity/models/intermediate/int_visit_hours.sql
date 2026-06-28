with visits as (
    select
        *,
        date_trunc('hour', admission_ts)
            + case
                when admission_ts = date_trunc('hour', admission_ts) then interval '0 hour'
                else interval '1 hour'
              end as first_snapshot_hour
    from {{ ref('stg_visits') }}
),
capacity_window as (
    select
        date_trunc('hour', min(capacity_date)) as first_hour,
        date_trunc('hour', max(capacity_date)) + interval '1 day' as last_hour
    from {{ ref('stg_capacity') }}
)

select
    v.visit_id,
    v.facility_id,
    v.service_id,
    c.hour_ts,
    c.calendar_date,
    c.hour_of_day
from visits v
cross join capacity_window w
join {{ ref('int_hourly_calendar') }} c
  on c.hour_ts >= greatest(v.first_snapshot_hour, w.first_hour)
 and c.hour_ts < least(v.discharge_ts, w.last_hour)
