-- Staging: meter reads, deduplicated per the "as of" rule.
--
-- Two clocks: event_time (when the read happened) and received_at (when we
-- saw it). A correction lands as a NEW row with the same event_time and a
-- later received_at — nothing upstream ever overwrites a row. This model
-- picks, for a given cutoff, the latest received_at per (meter_id,
-- event_time) that is still <= the cutoff. Re-run with the same cutoff
-- against the same landed files and you get the same rows, in the same
-- order, every time.

with ranked as (
    select
        meter_id,
        event_time,
        received_at,
        read_value,
        source_file_hash,
        row_number() over (
            partition by meter_id, event_time
            order by received_at desc
        ) as rn
    from {{ ref('raw_meter_reads') }}
    where {{ as_of_filter('received_at', var('run_as_of')) }}
)

select
    meter_id,
    event_time,
    received_at,
    read_value,
    source_file_hash,
    (received_at - event_time) as lag_at_landing
from ranked
where rn = 1
