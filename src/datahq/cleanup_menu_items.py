from __future__ import annotations

import os
import sys
import uuid
from typing import Any

from .square import request_json, sync_catalog


WATERMELON_ID = "WGXXUYKVYKYMCXMHY3DSK65Q"
CONSULTATION_ID = "WGRU5JJIQJKMGDNCOERE7G5N"
SNACKS_PRIMARY_ID = "JS5ZZ5XQNAZRBDOPSWLLLQ5C"
SNACKS_SECONDARY_ID = "EFR5NKPO7JAAOHXWE4ZUHEUB"


def retrieve_item(token: str, item_id: str) -> dict[str, Any]:
    response = request_json("GET", f"/v2/catalog/object/{item_id}", token)
    return response["object"]


def upsert_item(token: str, item: dict[str, Any]) -> dict[str, Any]:
    response = request_json(
        "POST",
        "/v2/catalog/object",
        token,
        body={"idempotency_key": str(uuid.uuid4()), "object": item},
    )
    if response.get("errors"):
        raise RuntimeError(response["errors"])
    return response["catalog_object"]


def main() -> int:
    token = os.getenv("SQUARE_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("SQUARE_ACCESS_TOKEN is not configured")

    watermelon = retrieve_item(token, WATERMELON_ID)
    watermelon_data = watermelon.get("item_data") or {}
    watermelon_data["categories"] = [
        {"id": SNACKS_PRIMARY_ID},
        {"id": SNACKS_SECONDARY_ID},
    ]
    watermelon_data["reporting_category"] = {"id": SNACKS_PRIMARY_ID}
    watermelon["item_data"] = watermelon_data
    upsert_item(token, watermelon)
    print("UPDATED: Watermelon Feta -> Snacks")

    consultation = retrieve_item(token, CONSULTATION_ID)
    consultation_data = consultation.get("item_data") or {}
    consultation_data["is_archived"] = True
    consultation["item_data"] = consultation_data
    upsert_item(token, consultation)
    print("ARCHIVED: Consultation (example service)")

    # Refresh the Supabase mirror and verify against live Square.
    sync_catalog(token)

    watermelon_check = retrieve_item(token, WATERMELON_ID)
    wd = watermelon_check.get("item_data") or {}
    category_ids = {
        (entry or {}).get("id")
        for entry in (wd.get("categories") or [])
        if (entry or {}).get("id")
    }
    reporting_id = (wd.get("reporting_category") or {}).get("id")
    if SNACKS_PRIMARY_ID not in category_ids or reporting_id != SNACKS_PRIMARY_ID:
        raise RuntimeError("Watermelon Feta category verification failed")

    consultation_check = retrieve_item(token, CONSULTATION_ID)
    if not bool((consultation_check.get("item_data") or {}).get("is_archived")):
        raise RuntimeError("Consultation archive verification failed")

    print("VERIFIED: Watermelon Feta is in Snacks")
    print("VERIFIED: Consultation (example service) is archived")
    return 0


if __name__ == "__main__":
    sys.exit(main())
