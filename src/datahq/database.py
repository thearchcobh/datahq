from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client


def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SECRET_KEY"]
    return create_client(url, key)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_sync(source: str, metadata: dict[str, Any] | None = None) -> str:
    client = get_client()
    result = (
        client.table("sync_runs")
        .insert({"source": source, "metadata": metadata or {}})
        .execute()
    )
    return result.data[0]["id"]


def finish_sync(
    run_id: str,
    *,
    status: str,
    records_read: int = 0,
    records_written: int = 0,
    error_message: str | None = None,
) -> None:
    client = get_client()
    client.table("sync_runs").update(
        {
            "status": status,
            "finished_at": utc_now_iso(),
            "records_read": records_read,
            "records_written": records_written,
            "error_message": error_message,
        }
    ).eq("id", run_id).execute()


def get_sync_state(source: str) -> dict[str, Any] | None:
    client = get_client()
    result = client.table("sync_state").select("*").eq("source", source).execute()
    return result.data[0] if result.data else None


def set_sync_state(source: str, *, last_cursor: str | None = None) -> None:
    client = get_client()
    now = utc_now_iso()
    client.table("sync_state").upsert(
        {
            "source": source,
            "last_cursor": last_cursor,
            "last_synced_at": now,
            "updated_at": now,
        },
        on_conflict="source",
    ).execute()
