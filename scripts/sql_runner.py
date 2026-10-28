"""Minimal dbt-style runner: resolves ref()/var() and the macros in
warehouse/macros/ via Jinja, then executes each model as a DuckDB view/table
in dependency order.

This is NOT a dbt reimplementation -- it is just enough templating to prove
the SQL in warehouse/models/ actually runs, in the actual dependency order
ref() implies, against real (synthetic) data. DuckDB stands in for Redshift:
same ANSI-SQL-family dialect, zero infrastructure for a take-home review.
If dbt Core is approved for real, warehouse/models/ ports to it directly --
the SQL doesn't change, only the runner around it does.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import duckdb
from jinja2 import Environment

WAREHOUSE_ROOT = Path(__file__).resolve().parents[1] / "warehouse"
MACROS_DIR = WAREHOUSE_ROOT / "macros"
MODELS_DIR = WAREHOUSE_ROOT / "models"

_REF_RE = re.compile(r"\{\{\s*ref\(\s*['\"]([a-zA-Z0-9_]+)['\"]\s*\)\s*\}\}")


def _load_macros() -> str:
    """Concatenate every macro file so {% macro %} blocks are available to
    every model's Jinja render.
    """
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(MACROS_DIR.glob("*.sql")))


def _find_model_files() -> dict[str, Path]:
    models = {}
    for p in MODELS_DIR.rglob("*.sql"):
        models[p.stem] = p
    return models


def _referenced_models(sql_text: str) -> list[str]:
    return _REF_RE.findall(sql_text)


class SqlRunner:
    def __init__(self, con: duckdb.DuckDBPyConnection, run_as_of: str):
        self.con = con
        self.run_as_of = run_as_of
        self.models = _find_model_files()
        self.macro_source = _load_macros()
        self.env = Environment()
        self._rendered_cache: dict[str, str] = {}

    def _var(self, name: str) -> str:
        if name == "run_as_of":
            return f"TIMESTAMP '{self.run_as_of}'"
        raise KeyError(f"unknown var: {name}")

    def _ref(self, name: str) -> str:
        # Every ref() resolves to a DuckDB view/table of the same name --
        # build() creates it before any model that refs it is rendered,
        # same ordering guarantee dbt's DAG gives.
        return name

    def render(self, model_name: str) -> str:
        if model_name in self._rendered_cache:
            return self._rendered_cache[model_name]

        path = self.models[model_name]
        raw_sql = path.read_text(encoding="utf-8")
        template_source = self.macro_source + "\n" + raw_sql
        template = self.env.from_string(template_source)
        rendered = template.render(
            ref=self._ref,
            var=self._var,
            as_of_filter=lambda col, cutoff: f"{col} <= {cutoff}",
            exclude_storm_days=lambda col: f"{col} not in (select storm_date from storm_days)",
            aggregation_floor=lambda col, floor_value=15: (
                f"case when {col} >= {floor_value} then {col} else null end"
            ),
        )
        self._rendered_cache[model_name] = rendered
        return rendered

    def build(self, model_name: str, _building: set[str] | None = None, _built: set[str] | None = None) -> None:
        _building = _building if _building is not None else set()
        _built = _built if _built is not None else set()
        if model_name in _built:
            return
        if model_name in _building:
            raise RuntimeError(f"circular ref() detected at {model_name}")
        _building.add(model_name)

        raw_sql = self.models[model_name].read_text(encoding="utf-8")
        for dep in _referenced_models(raw_sql):
            if dep not in self.models:
                continue  # seed table (e.g. raw_meter_reads), loaded separately
            self.build(dep, _building, _built)

        select_sql = self.render(model_name)
        self.con.execute(f"CREATE OR REPLACE VIEW {model_name} AS {select_sql}")

        _building.discard(model_name)
        _built.add(model_name)

    def fetch_df(self, model_name: str):
        self.build(model_name)
        return self.con.execute(f"select * from {model_name}").fetchdf()
