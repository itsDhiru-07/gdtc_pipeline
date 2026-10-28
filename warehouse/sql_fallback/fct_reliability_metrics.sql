-- Stored-procedure fallback for warehouse/models/marts/fct_reliability_metrics.sql
-- See docs/dbt-contingency.md. Same logic, no dbt: a plain versioned
-- Redshift stored procedure, called with an explicit cutoff parameter.
--
-- Versioning convention: this file's name never changes; its CONTENTS are
-- versioned by git history plus the `procedure_version` value written into
-- run_manifest below, which is a short hash of this file at execution time
-- (computed by scripts/sql_runner_fallback.py, not shown here). That hash,
-- not a human-chosen version string, is what the evidence pack pins --
-- it's harder to forget to bump than a manual version number.

CREATE OR REPLACE PROCEDURE sp_fct_reliability_metrics(run_as_of TIMESTAMP)
LANGUAGE plpgsql
AS $$
BEGIN

    CREATE TEMP TABLE tmp_outages AS
    SELECT
        o.outage_id,
        o.feeder_id,
        o.event_time,
        o.restored_at,
        o.customers_affected,
        DATEDIFF(minute, o.event_time, o.restored_at) AS outage_minutes,
        le.link_status
    FROM stg_outage_records o
    LEFT JOIN fct_link_exceptions le USING (outage_id)
    WHERE CAST(o.event_time AS DATE) NOT IN (SELECT storm_date FROM storm_days);

    CREATE TEMP TABLE tmp_customers AS
    SELECT state, feeder_id, customer_count
    FROM stg_customer_counts
    WHERE received_at <= run_as_of;

    -- All-links and undisputed-only bases, same honest-range logic as the
    -- dbt model: see warehouse/models/marts/fct_reliability_metrics.sql.
    INSERT INTO fct_reliability_metrics
    SELECT
        a.state,
        run_as_of AS run_as_of,
        ROUND(u.customer_outages::FLOAT / u.customers_served, 6) AS outage_frequency_undisputed,
        ROUND(a.customer_outages::FLOAT / a.customers_served, 6) AS outage_frequency_all_links,
        ROUND(u.customer_outage_minutes::FLOAT / u.customers_served, 4) AS outage_duration_minutes_undisputed,
        ROUND(a.customer_outage_minutes::FLOAT / a.customers_served, 4) AS outage_duration_minutes_all_links
    FROM (
        SELECT cs.state,
               SUM(o.customers_affected) AS customer_outages,
               SUM(o.customers_affected * o.outage_minutes) AS customer_outage_minutes,
               SUM(cs.customer_count) AS customers_served
        FROM tmp_outages o
        JOIN tmp_customers cs ON cs.feeder_id = o.feeder_id
        GROUP BY cs.state
    ) a
    JOIN (
        SELECT cs.state,
               SUM(o.customers_affected) AS customer_outages,
               SUM(o.customers_affected * o.outage_minutes) AS customer_outage_minutes,
               SUM(cs.customer_count) AS customers_served
        FROM tmp_outages o
        JOIN tmp_customers cs ON cs.feeder_id = o.feeder_id
        WHERE o.link_status != 'disputed_pending_review'
        GROUP BY cs.state
    ) u USING (state);

    INSERT INTO run_manifest (procedure_name, run_as_of, executed_at)
    VALUES ('sp_fct_reliability_metrics', run_as_of, GETDATE());

END;
$$;
