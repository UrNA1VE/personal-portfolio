select
    *,
    case
        when peak_utilization >= 0.95 then 'Critical'
        when peak_utilization >= 0.90 then 'Severe'
        when peak_utilization >= 0.85 then 'High'
        else 'Normal'
    end as pressure_level,
    (peak_utilization >= 0.85) as above_85_percent,
    (peak_utilization >= 0.90) as above_90_percent,
    (peak_utilization >= 0.95) as above_95_percent
from {{ ref('fct_daily_utilization') }}
