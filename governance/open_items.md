# Open governance items

Carried over verbatim from the architecture review's honest-residual-risk framing.
These are not bugs to silently fix in code — they are decisions that need a human
owner before go-live. Listed here so the codebase doesn't quietly assert a precision
it doesn't have.

## LEG-01 — aggregation floor of 15 customers

`governance/data_classification.yaml` (C4) hard-codes `aggregation_floor_15_customers`
as the default suppression threshold for any customer-level aggregate. This value is
**a starting point, not a validated k-anonymity threshold** for the actual feeder
density across the three states this platform would serve. Rural, low-density feeders
may re-identify individual customers well above 15.

**Action before go-live:** Legal + the method owner validate the floor against real
feeder-level customer counts, per state, and set a higher floor where density requires
it. `warehouse/macros/aggregation_floor.sql` takes the floor as a parameter for this
reason — it is not meant to stay a single global constant.

## SEC-01 — "security-tested" OT gateway

The deck's answer to SEC-01 now specifies what testing means (a physical penetration
test of the one-way gateway, plus a tabletop exercise with OT security, re-run after
any firmware change) and separates two different risks:

- **Command/control risk** — solved by the hardware one-way gateway. Nothing in the
  cloud can send a command or acknowledgement back into OT.
- **Data-integrity risk** — a compromised edge collector could send false summary
  data. This is **not** solved by the one-way gateway, and is explicitly OT security's
  responsibility, not this platform's. This repo has no OT ingestion code at all
  (release 1 uses no telemetry), so there is nothing here to harden against this —
  flagging it so nobody assumes release 3 inherits a solved problem.

## EA-01 — dbt Core is not yet an approved tool

See `docs/dbt-contingency.md`. The warehouse models in this repo are written as dbt
models because that's the clearest way to show lineage and tests for a design review.
If dbt Core doesn't clear the enterprise architecture exception process, the fallback
is versioned stored procedures with a hand-rolled run manifest — same evidence, more
maintenance. `warehouse/sql_fallback/` shows the shape of that fallback for one model
so it isn't just an assertion.
