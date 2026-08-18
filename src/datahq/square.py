from __future__ import annotations

from .database import finish_sync, set_sync_state, start_sync


def sync_square() -> None:
    """Entry point for Square ingestion.

    Replace the placeholder body with the existing local Square logic, keeping
    this function as the stable scheduled-job interface.
    """
    run_id = start_sync("square")
    try:
        # TODO: migrate the existing local Square API code here.
        # Expected targets:
        #   square_orders
        #   square_order_items
        #   square_catalogue_items
        #   square_team_members
        #   square_timecards
        set_sync_state("square")
        finish_sync(run_id, status="success")
    except Exception as exc:
        finish_sync(run_id, status="failed", error_message=str(exc))
        raise
