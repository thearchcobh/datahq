from __future__ import annotations

import os
import sys
import uuid
from typing import Any

from .square import request_json, sync_catalog


RENAMES = {
    "Gaba do Xil Godello": "Gaba do Xil Godello - Takeaway",
    "Galets Dores, France": "Galets Dores, France - Takeaway",
    "Jean Loron IGP Chardonnay": "Jean Loron IGP Chardonnay - Takeaway",
    "Blank Bottle, South Africa": "Blank Bottle, South Africa - Takeaway",
}

TAKEAWAY_CATEGORY_NAME = "Takeaway Wine"


def list_catalog(token: str) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        params: dict[str, Any] = {"types": "CATEGORY,ITEM"}
        if cursor:
            params["cursor"] = cursor
        data = request_json("GET", "/v2/catalog/list", token, params=params)
        objects.extend(data.get("objects") or [])
        cursor = data.get("cursor")
        if not cursor:
            return objects


def is_active_item(obj: dict[str, Any]) -> bool:
    if obj.get("type") != "ITEM" or obj.get("is_deleted"):
        return False
    return not bool((obj.get("item_data") or {}).get("is_archived"))


def category_ids(item: dict[str, Any]) -> set[str]:
    data = item.get("item_data") or {}
    result: set[str] = set()
    if data.get("category_id"):
        result.add(data["category_id"])
    for entry in data.get("categories") or []:
        cid = (entry or {}).get("id") or (entry or {}).get("category_id")
        if cid:
            result.add(cid)
    return result


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
    return response["catalog_object"]


def main() -> int:
    token = os.getenv("SQUARE_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("SQUARE_ACCESS_TOKEN is not configured")

    objects = list_catalog(token)
    categories = [o for o in objects if o.get("type") == "CATEGORY" and not o.get("is_deleted")]
    matches = [
        o for o in categories
        if ((o.get("category_data") or {}).get("name") or "").strip().casefold() == TAKEAWAY_CATEGORY_NAME.casefold()
    ]
    if not matches:
        raise RuntimeError("Takeaway Wine category not found")
    category_id = matches[0]["id"]

    active_takeaway = [
        o for o in objects
        if is_active_item(o) and category_id in category_ids(o)
    ]
    by_name = {
        (((o.get("item_data") or {}).get("name")) or "").strip(): o
        for o in active_takeaway
    }

    for old_name, new_name in RENAMES.items():
        if new_name in by_name:
            print(f"SKIP: already renamed | {new_name}")
            continue
        item = by_name.get(old_name)
        if item is None:
            raise RuntimeError(f"Expected active takeaway item not found: {old_name}")
        live = retrieve_item(token, item["id"])
        live["item_data"]["name"] = new_name
        upsert_item(token, live)
        print(f"RENAMED: {old_name} -> {new_name}")

    sync_catalog(token)

    refreshed = list_catalog(token)
    refreshed_takeaway_names = {
        (((o.get("item_data") or {}).get("name")) or "").strip()
        for o in refreshed
        if is_active_item(o) and category_id in category_ids(o)
    }
    missing = [new for new in RENAMES.values() if new not in refreshed_takeaway_names]
    if missing:
        raise RuntimeError("Verification failed for: " + "; ".join(missing))

    for new in RENAMES.values():
        print(f"VERIFIED: {new}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
