-- macro: exclude_storm_days(date_column)
--
-- Storm days are excluded from the regulatory number per the deck (part 4)
-- and the standard SAIFI/SAIDI convention this platform follows. "Storm day"
-- is defined by the storm_days reference table (built from the weather feed,
-- C2, internal-analytics-only license) and set once per declared event by
-- the method owner — this macro never infers a storm day from outage volume
-- alone, which would let the platform quietly redefine the regulatory
-- standard without a human decision behind it.

{% macro exclude_storm_days(date_column) %}
    {{ date_column }} not in (select storm_date from {{ ref('storm_days') }})
{% endmacro %}
