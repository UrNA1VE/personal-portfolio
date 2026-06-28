with census as (
    select
        calendar_date,
        facility_id,
        facility_name,
        service_id,
        service_name,
        avg(census)::numeric(12, 2) as average_census,
        max(census) as peak_census
    from {{ ref('fct_hourly_census') }}
    group by 1, 2, 3, 4, 5
)

select
    c.calendar_date,
    c.facility_id,
    c.facility_name,
    c.service_id,
    c.service_name,
    c.average_census,
    c.peak_census,
    cap.staffed_beds,
    round(c.average_census / nullif(cap.staffed_beds, 0), 4) as average_utilization,
    round(c.peak_census::numeric / nullif(cap.staffed_beds, 0), 4) as peak_utilization
from census c
left join {{ ref('stg_capacity') }} cap
  on c.calendar_date = cap.capacity_date
 and c.facility_id = cap.facility_id
 and c.service_id = cap.service_id
