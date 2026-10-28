"""Live, per-incident lookup of the medical/life-support flag (C7).

This is NOT a batch connector and has no `run()` land-to-S3 function on
purpose — it is the one path in this codebase that touches C7, and it is
designed so that path can never silently turn into a batch extract.

Every call is logged (incident ID, requesting workflow, timestamp) on the
customer-system side, per the governance register. This stub shows the
shape of that call for a design review; it does not call a real system.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DispatchFlagLookup:
    incident_id: str
    service_address_id: str
    has_medical_life_support_flag: bool
    looked_up_at: datetime
    requested_by_workflow: str = "outage_dispatch"


def lookup_for_incident(incident_id: str, service_address_id: str) -> DispatchFlagLookup:
    """Stand-in for an audited, direct API call to the customer system.

    Real implementation: synchronous HTTPS call to the customer system's
    dispatch-support endpoint, authenticated via the corporate IdP service
    identity (SEC-03), never cached, never written to S3 or Redshift. The
    customer system logs the call itself — this function does not need its
    own audit table because the source of truth already logs access.
    """
    raise NotImplementedError(
        "Stub only — a design-review repo does not call a real customer "
        "system. Wiring this to a live system is a release-3 integration "
        "task, scoped to the outage-dispatch workflow only."
    )
