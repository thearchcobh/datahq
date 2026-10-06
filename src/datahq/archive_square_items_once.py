from __future__ import annotations

import os
import sys
import uuid
from typing import Any

from .square import request_json, sync_catalog


ITEMS = {
    "F65IWDIJWDV5PL4672XYZJX5": "Bedoba Orange",
    "QHFQNXLEPLPGYYZ6OREUBN7U": "Domaine Zinck Pinot Blanc",
    "Q3EFBSLRPEOTTYQMUEFGZJ5O": "Gift Bag",
    "CWAM5D2I3LG3RE72B5YRJGUW": "Tip / Gratuity",
    "A4W2DBMT2Q67CTRMWDVXAMXL": "Vin des Amis",
}


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

    for item_id, expected_name in ITEMS.items():
        item = retrieve_item(token, item_id)
        data = item.get("item_data") or {}
        actual_name = (data.get("name") or "").strip()
        if actual_name != expected_name:
            raise RuntimeError(
                f"Safety check failed for {item_id}: expected {expected_name!r}, got {actual_name!r}"
            )

        if bool(data.get("is_archived")):
            print(f"SKIP: already archived | {expected_name}")
            continue

        data["is_archived"] = True
        item["item_data"] = data
        upsert_item(token, item)
        print(f"ARCHIVED: {expected_name}")

    for item_id, expected_name in ITEMS.items():
        check = retrieve_item(token, item_id)
        if not bool((check.get("item_data") or {}).get("is_archived")):
            raise RuntimeError(f"Verification failed: {expected_name} is not archived")
        print(f"VERIFIED: {expected_name}")

    sync_catalog(token)
    print("SYNCED: Square catalogue -> Supabase")
    return 0


if __name__ == "__main__":
    sys.exit(main())
