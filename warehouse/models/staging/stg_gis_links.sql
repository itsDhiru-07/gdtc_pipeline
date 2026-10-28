-- Staging: GIS meter-to-equipment links, as-of filtered on the nightly
-- snapshot date. Source map is never edited — every nightly snapshot is
-- kept, so this is a straight pass-through selecting the snapshot that was
-- current as of the cutoff.

select
    meter_id,
    equipment_id,
    feeder_id,
    is_wrong_link,
    snapshot_date,
    received_at,
    source_file_hash
from {{ ref('raw_gis_network_map') }}
where {{ as_of_filter('received_at', var('run_as_of')) }}
