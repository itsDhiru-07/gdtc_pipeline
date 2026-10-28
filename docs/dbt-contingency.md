# If dbt Core is not approved

EA-01: the approved warehouse standard is Redshift; open table formats on S3
are not yet approved, and dbt Core is a new tool this team would be
introducing. The warehouse models in `warehouse/models/` are written in
dbt's style (Jinja macros, `ref()`, `{{ var() }}`) because it's the clearest
way to show lineage and tests in a design review.

**This is a build-time tooling decision, not a go-live blocker.** If dbt
Core doesn't clear the enterprise-architecture exception process in time,
the fallback is:

1. **Versioned stored procedures** in Redshift, one per model, checked into
   this same repo under `warehouse/sql_fallback/`. `fct_reliability_metrics.sql`
   there shows the shape: the same logic as the dbt model, written as a
   plain parameterized stored procedure.
2. **A hand-rolled run manifest** replacing dbt's built-in run metadata:
   a table (`run_manifest`) with one row per execution recording source file
   hashes, procedure version, row counts in and out, and the cutoff
   parameter used. This is the same evidence dbt's `manifest.json` + test
   results would give — more maintenance to keep current, same auditability.
3. **A generated lineage graph** built from the manifest table instead of
   dbt's dependency graph — a script that walks `run_manifest` rows and
   renders which procedure read which source hash, satisfying EA-03's
   lineage requirement without dbt.

## The same logic the team already used to reject Spark, applied honestly to dbt

The architecture's own decision record rejects Spark for release 1 because
nobody on the team knows it (2 strong SQL, 1 Python, 0 Spark — see the
client team shape in the deck). dbt Core is also new to this team. That's
the same adoption-risk logic, and it should be said plainly rather than
quietly exempting dbt from it:

- dbt's learning curve is shallower than Spark's for a SQL-strong team —
  a dbt model is still just a SQL `select`, with Jinja templating on top,
  not a new execution paradigm.
- The fallback above exists specifically so the lineage and reproducibility
  story doesn't collapse if that bet is wrong or if EA simply says no.

If EA rejects the exception, switch to the fallback path before release 1
ships — don't let the fallback be a release-3 cleanup item while release 1
ships on an unapproved tool.
