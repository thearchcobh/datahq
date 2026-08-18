from __future__ import annotations

from datetime import datetime, timezone

from .database import get_client


def retention_start() -> datetime:
    """Return 1 January of the previous calendar year in UTC."""
    now = datetime.now(timezone.utc)
    return datetime(now.year - 1, 1, 1, tzinfo=timezone.utc)


def prune_source(source: str) -> None:
    """Keep detailed operational history to current + previous calendar year."""
    client = get_client()
    cutoff = retention_start()
    cutoff_iso = cutoff.isoformat()
    cutoff_date = cutoff.date().isoformat()

    if source == "square":
        # square_order_items are removed by ON DELETE CASCADE from square_orders.
        client.table("square_orders").delete().lt("created_at", cutoff_iso).execute()
        client.table("square_timecards").delete().lt("start_at", cutoff_iso).execute()
    elif source == "revolut":
        # revolut_transaction_legs are removed by ON DELETE CASCADE.
        client.table("revolut_transactions").delete().lt("created_at", cutoff_iso).execute()
        client.table("revolut_balances").delete().lt("balance_date", cutoff_date).execute()
    else:
        raise ValueError(f"Unknown retention source: {source}")
