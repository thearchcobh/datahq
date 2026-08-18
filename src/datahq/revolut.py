from __future__ import annotations

from .database import finish_sync, set_sync_state, start_sync


def sync_revolut() -> None:
    """Entry point for Revolut Business ingestion.

    Authentication and API calls will be added once the Revolut Business API
    credentials are created. Keep this function as the scheduled-job interface.
    """
    run_id = start_sync("revolut")
    try:
        # TODO: add Revolut Business authentication and incremental retrieval.
        # Expected targets:
        #   revolut_accounts
        #   revolut_transactions
        #   revolut_balances
        set_sync_state("revolut")
        finish_sync(run_id, status="success")
    except Exception as exc:
        finish_sync(run_id, status="failed", error_message=str(exc))
        raise
