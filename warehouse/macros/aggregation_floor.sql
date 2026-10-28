-- macro: aggregation_floor(customer_count_column, floor_value)
--
-- LEG-01 control: any customer-level aggregate below the floor is suppressed
-- (returned as NULL) rather than shown. floor_value is a parameter, not a
-- hard-coded constant, because governance/open_items.md flags the default
-- (15) as a starting value that Legal + the method owner must validate
-- against real per-state feeder density before go-live — a flat national
-- floor may be too low for low-density rural feeders.

{% macro aggregation_floor(customer_count_column, floor_value=15) %}
    case when {{ customer_count_column }} >= {{ floor_value }}
         then {{ customer_count_column }}
         else null
    end
{% endmacro %}
