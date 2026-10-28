-- macro: as_of_filter(received_at_column, cutoff_param)
--
-- The deck's reproducibility rule: a report asks "as of" a time, so the same
-- question always gets the same answer. This macro is the single place that
-- rule is implemented — every mart that computes a regulatory number applies
-- it, rather than each model re-deriving its own cutoff logic.
--
-- Usage (dbt-style Jinja, also valid as a plain SQL template string in the
-- DuckDB reference runner — see scripts/sql_runner.py):
--
--   where {{ as_of_filter('received_at', var('run_as_of')) }}

{% macro as_of_filter(received_at_column, cutoff_param) %}
    {{ received_at_column }} <= {{ cutoff_param }}
{% endmacro %}

-- settling macro: month-end numbers settle after 5 days (72-hour late-read
-- window + margin). A filing cutoff should never fall inside the settling
-- window for the period it's filing.
{% macro settling_cutoff(period_end_date) %}
    ({{ period_end_date }} + INTERVAL 5 DAY)
{% endmacro %}
