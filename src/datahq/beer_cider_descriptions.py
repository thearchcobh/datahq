from __future__ import annotations

import copy
import html
import os
import sys
import uuid

from .square import request_json


DESCRIPTION_UPDATES = {
    "NAPYELUYY5M5GKBQRCEPLGIC": ("Kinsale Pale Ale", "500ml bottle"),
    "A6U3E5YBDSQHCYMI45WQOBNN": ("Peroni", "330ml bottle"),
    "75QW4PVMHPB6KS2D7HI3ODWE": ("Peroni 0.0%", "330ml bottle, 0% ABV"),
    "MSQJT334ZRAZ3MZ2OSVS2DWS": ("Stag Kolsch Lager", "500ml bottle, Gluten Free"),
    "N7G7Z6GCT676COHESXUSY7VA": ("Stonewell 0% Irish Cider", "330ml bottle, 0% Alcohol"),
    "52AC3EIGM6FKGHM4EMZMEQQP": ("Stonewell Medium Dry Irish Cider", "500ml bottle"),
    "6M6RLQHLMHLO4WBS37S2YUPA": ("Lucky Saint", "500ml bottle, 0% ABV"),
}


def retrieve_item(token: str, item_id: str) -> dict:
    response = request_json("GET", f"/v2/catalog/object/{item_id}", token)
    return response["object"]


def upsert_item(token: str, item: dict) -> dict:
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

    for item_id, (expected_name, description) in DESCRIPTION_UPDATES.items():
        item = copy.deepcopy(retrieve_item(token, item_id))
        item_data = item.get("item_data") or {}
        actual_name = item_data.get("name")
        if actual_name != expected_name:
            raise RuntimeError(
                f"Safety check failed for {item_id}: expected {expected_name!r}, got {actual_name!r}"
            )

        # Keep the item name unchanged; bottle/can size belongs in the description.
        item_data["description"] = description
        item_data["description_html"] = f"<p>{html.escape(description)}</p>"
        item_data.pop("description_plaintext", None)
        item["item_data"] = item_data

        upsert_item(token, item)
        print(f"UPDATED: {expected_name} -> {description}")

    print(f"Complete: updated {len(DESCRIPTION_UPDATES)} beer/cider descriptions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
