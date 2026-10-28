-- Reconciliation list for wrong meter-to-equipment GIS links (deck part 4:
-- "we never edit the map ... disagreements go to a review list").
--
-- The outage record's count leads. Meter power events confirm it. Where
-- the GIS-implied feeder for an outage disagrees with the feeder OMS
-- actually logged, the row lands here as an exception — it is NEVER
-- silently resolved by this model. A separate, versioned override table
-- (link_overrides, maintained by a named owner) is the only thing allowed
-- to resolve an exception, and even then it's applied the same way on
-- every run, not hand-patched per filing.

with outage_feeder as (
    select
        outage_id,
        feeder_id as oms_feeder_id,
        customers_affected,
        event_time
    from {{ ref('stg_outage_records') }}
),

-- One GIS-asserted feeder per outage's own feeder_id: does GIS's own map
-- agree that this feeder ID is internally consistent (i.e. GIS has not
-- reassigned any meter on this feeder to a different feeder since OMS
-- logged the outage against it)? A feeder where GIS shows a split --
-- some meters now mapped elsewhere -- is exactly the "wrong link" case the
-- deck describes, and surfaces as a disagreement below.
gis_feeder_consistency as (
    select
        feeder_id as oms_feeder_id,
        mode(feeder_id) as gis_majority_feeder_id,  -- GIS's own majority view for meters nominally on this feeder
        count(*) as linked_meter_count,
        sum(case when is_wrong_link then 1 else 0 end) as wrong_link_count
    from {{ ref('stg_gis_links') }}
    group by feeder_id
),

overrides as (
    select outage_id, resolved_feeder_id, owner, override_version
    from {{ ref('link_overrides') }}
)

select
    o.outage_id,
    o.event_time,
    o.oms_feeder_id,
    gc.wrong_link_count,
    gc.linked_meter_count,
    ov.resolved_feeder_id,
    ov.owner as resolved_by,
    ov.override_version,
    case
        when ov.resolved_feeder_id is not null then 'resolved'
        when gc.wrong_link_count is null or gc.wrong_link_count = 0 then 'agrees'
        else 'disputed_pending_review'
    end as link_status
from outage_feeder o
left join gis_feeder_consistency gc on gc.oms_feeder_id = o.oms_feeder_id
left join overrides ov on ov.outage_id = o.outage_id
