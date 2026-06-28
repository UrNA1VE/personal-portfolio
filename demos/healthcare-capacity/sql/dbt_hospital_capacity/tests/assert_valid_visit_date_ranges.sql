select *
from {{ ref('stg_visits') }}
where discharge_ts <= admission_ts
