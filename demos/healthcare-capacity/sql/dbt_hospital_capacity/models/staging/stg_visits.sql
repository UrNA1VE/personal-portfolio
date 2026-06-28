select
    trim(visit_id)::varchar as visit_id,
    trim(patient_id)::varchar as patient_id,
    trim(facility_id)::varchar as facility_id,
    trim(service_id)::varchar as service_id,
    trim(diagnosis_code)::varchar as diagnosis_code,
    age::integer as age,
    trim(gender)::varchar as gender,
    admission_ts::timestamp as admission_ts,
    discharge_ts::timestamp as discharge_ts,
    trim(admission_type)::varchar as admission_type,
    alclos::numeric as alclos,
    elos::numeric as elos,
    trim(riwexcl)::varchar as riwexcl,
    trim_days::numeric as trim_days
from {{ source('raw', 'visits') }}
