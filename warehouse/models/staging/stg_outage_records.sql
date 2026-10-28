-- Staging: outage records, as-of filtered. Hand-entered restore times pass
-- through unmodified — correction/review happens in the mart layer as a
-- visible exception list, never as a silent edit here.

select
    outage_id,
    feeder_id,
    event_time,
    restored_at,
    customers_affected,
    cause_code,
    received_at,
    source_file_hash
from {{ ref('raw_outage_records') }}
where {{ as_of_filter('received_at', var('run_as_of')) }}
