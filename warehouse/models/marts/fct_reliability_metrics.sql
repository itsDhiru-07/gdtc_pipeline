-- THE regulatory number. Outage frequency and outage duration, computed
-- "as of" a frozen cutoff, storm days excluded, reported BOTH with and
-- without disputed GIS links (the deck's "honest range" rule — this model
-- never silently picks a side on a link dispute).
--
-- outage_frequency = customer outages / customers served
-- outage_duration  = customer outage minutes / customers served
--
-- Run this model twice with the same `run_as_of` var against the same
-- landed files and every column is byte-identical. That's the whole
-- contract this file exists to prove: see scripts/run_pipeline.py, which
-- runs it twice and diffs the output.

with outages as (
    select
        o.outage_id,
        o.feeder_id,
        o.event_time,
        o.restored_at,
        o.customers_affected,
        datediff('minute', o.event_time, o.restored_at) as outage_minutes,
        le.link_status
    from {{ ref('stg_outage_records') }} o
    left join {{ ref('fct_link_exceptions') }} le using (outage_id)
    where {{ exclude_storm_days('cast(o.event_time as date)') }}
),

customers_served as (
    select state, feeder_id, customer_count
    from {{ ref('stg_customer_counts') }}
    where {{ as_of_filter('received_at', var('run_as_of')) }}
),

-- "all links" basis: every outage counted regardless of GIS dispute status
agg_all as (
    select
        cs.state,
        sum(o.customers_affected) as customer_outages,
        sum(o.customers_affected * o.outage_minutes) as customer_outage_minutes,
        sum(cs.customer_count) as customers_served
    from outages o
    join customers_served cs on cs.feeder_id = o.feeder_id
    group by cs.state
),

-- "undisputed only" basis: excludes outages whose GIS link is still in
-- disputed_pending_review — the conservative end of the honest range
agg_undisputed as (
    select
        cs.state,
        sum(o.customers_affected) as customer_outages,
        sum(o.customers_affected * o.outage_minutes) as customer_outage_minutes,
        sum(cs.customer_count) as customers_served
    from outages o
    join customers_served cs on cs.feeder_id = o.feeder_id
    where o.link_status != 'disputed_pending_review'
    group by cs.state
)

select
    a.state,
    {{ var('run_as_of') }} as run_as_of,
    -- reported range: undisputed-only (lower bound on frequency inflation)
    -- through all-links (upper bound) -- see deck: "we cannot make wrong
    -- source links right, so we show the board a range."
    round(u.customer_outages::double / u.customers_served, 6) as outage_frequency_undisputed,
    round(a.customer_outages::double / a.customers_served, 6) as outage_frequency_all_links,
    round(u.customer_outage_minutes::double / u.customers_served, 4) as outage_duration_minutes_undisputed,
    round(a.customer_outage_minutes::double / a.customers_served, 4) as outage_duration_minutes_all_links
from agg_all a
join agg_undisputed u using (state)
order by a.state
