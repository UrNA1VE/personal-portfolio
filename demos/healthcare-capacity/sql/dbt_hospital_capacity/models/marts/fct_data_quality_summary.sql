with checks as (
    select
        'visits_missing_required_fields' as check_name,
        count(*)::integer as issue_count,
        'error' as severity
    from {{ ref('stg_visits') }}
    where visit_id is null
       or facility_id is null
       or service_id is null
       or admission_ts is null
       or discharge_ts is null

    union all

    select
        'visits_with_invalid_date_range',
        count(*)::integer,
        'error'
    from {{ ref('stg_visits') }}
    where discharge_ts <= admission_ts

    union all

    select
        'capacity_missing_or_nonpositive',
        count(*)::integer,
        'warning'
    from {{ ref('stg_capacity') }}
    where staffed_beds is null or staffed_beds <= 0

    union all

    select
        'utilization_rows_without_capacity',
        count(*)::integer,
        'warning'
    from {{ ref('fct_daily_utilization') }}
    where staffed_beds is null
)

select
    check_name,
    issue_count,
    severity,
    case when issue_count = 0 then 'pass' else 'warn' end as status
from checks
