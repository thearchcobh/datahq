from __future__ import annotations

import os
from datetime import timedelta
from typing import Any

from .database import finish_sync, set_sync_state, start_sync
from .square import (
    DEFAULT_LOCATION_ID,
    iso_utc,
    now_utc,
    request_json,
    sync_catalog,
    sync_orders,
    sync_payments,
    sync_team_members,
    sync_timecards,
    upsert,
)


def sync_scheduled_shifts(token: str, location_id: str) -> tuple[int, int]:
    start = now_utc() - timedelta(days=7)
    end = now_utc() + timedelta(days=120)
    cursor = None
    read = written = 0
    synced_at = iso_utc(now_utc())

    while True:
        body: dict[str, Any] = {
            "query": {
                "filter": {
                    "location_ids": [location_id],
                    "start": {"start_at": iso_utc(start), "end_at": iso_utc(end)},
                    "scheduled_shift_statuses": ["PUBLISHED", "DRAFT"],
                }
            },
            "limit": 50,
        }
        if cursor:
            body["cursor"] = cursor

        data = request_json("POST", "/v2/labor/scheduled-shifts/search", token, body=body)
        shifts = data.get("scheduled_shifts") or []
        read += len(shifts)
        rows = []

        for shift in shifts:
            draft = shift.get("draft_shift_details") or None
            published = shift.get("published_shift_details") or None

            # Prefer the latest non-deleted draft so newly entered/unpublished rota
            # changes are visible to planning analysis. Fall back to the published
            # version when there is no active draft.
            if draft and not draft.get("is_deleted"):
                details = draft
                status = "DRAFT" if draft != published else "PUBLISHED"
            else:
                details = published
                status = "PUBLISHED" if published else "DRAFT"

            if shift.get("id") and details:
                rows.append(
                    {
                        "id": shift.get("id"),
                        "team_member_id": details.get("team_member_id"),
                        "location_id": details.get("location_id") or location_id,
                        "job_id": details.get("job_id"),
                        "start_at": details.get("start_at"),
                        "end_at": details.get("end_at"),
                        "notes": details.get("notes"),
                        "status": status,
                        "version": shift.get("version"),
                        "created_at": shift.get("created_at"),
                        "updated_at": shift.get("updated_at"),
                        "raw_json": shift,
                        "synced_at": synced_at,
                    }
                )

        written += upsert("square_scheduled_shifts", rows)
        cursor = data.get("cursor")
        if not cursor:
            return read, written


def sync_square() -> None:
    token = os.getenv("SQUARE_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("SQUARE_ACCESS_TOKEN is not configured")

    location_id = os.getenv("SQUARE_LOCATION_ID") or DEFAULT_LOCATION_ID
    run_id = start_sync("square", {"location_id": location_id})
    read = written = 0

    try:
        r, w = sync_team_members(token, location_id)
        read += r
        written += w

        r, w = sync_catalog(token)
        read += r
        written += w

        for fn in (sync_orders, sync_payments, sync_timecards, sync_scheduled_shifts):
            r, w = fn(token, location_id)
            read += r
            written += w

        set_sync_state("square")
        finish_sync(run_id, status="success", records_read=read, records_written=written)
    except Exception as exc:
        finish_sync(
            run_id,
            status="failed",
            records_read=read,
            records_written=written,
            error_message=str(exc),
        )
        raise
