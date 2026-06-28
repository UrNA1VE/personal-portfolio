with bounds as (
    select
        date_trunc('hour', min(capacity_date)) as first_hour,
        date_trunc('hour', max(capacity_date)) + interval '23 hour' as last_hour
    from {{ ref('stg_capacity') }}
)

select
    hour_ts,
    hour_ts::date as calendar_date,
    extract(hour from hour_ts)::integer as hour_of_day
from bounds
cross join lateral generate_series(first_hour, last_hour, interval '1 hour') as generated(hour_ts)
