"""One-time, guarded Square Catalog API fix for the Lombeline takeaway bottle COGS.

Reads the live dine-in bottle cost, changes only the default_unit_cost on the
existing takeaway Regular variation, then verifies live Square and refreshes
the Supabase catalogue mirror. Safe to re-run.
"""
from __future__ import annotations

import copy
import os
import sys
import uuid

from .square import request_json, sync_catalog

SOURCE_ITEM_ID = "2HQKHYNGGZDUB3NGID76LDTD"
SOURCE_VARIATION_ID = "D4FUWYZ67WBKIGD6LP4CK3RY"
SOURCE_ITEM_NAME = "'Lombeline’ Sauvignon Blanc"
TARGET_ITEM_ID = "NQ324RDAFFCH3TTOBWUP3V35"
TARGET_VARIATION_ID = "J4C5R2RLPLZEX5ATOHSVA2HJ"
TARGET_ITEM_NAME = "'Lombeline’ Sauvignon Blanc - Takeaway"
TARGET_PRICE_CENTS = 3190
EXPECTED_COST_CENTS = 1431


def get_item(token: str, item_id: str, expected_name: str) -> dict:
    result = request_json("GET", f"/v2/catalog/object/{item_id}", token)
    item = result["object"]
    data = item.get("item_data") or {}
    if (
        item.get("id") != item_id
        or item.get("type") != "ITEM"
        or item.get("is_deleted")
        or data.get("is_archived")
        or data.get("name") != expected_name
    ):
        raise RuntimeError(f"Unexpected live Square item for {item_id!r}: {data.get('name')!r}")
    return item


def get_variation(item: dict, variation_id: str, variation_name: str) -> dict:
    matches = [
        variation for variation in (item.get("item_data") or {}).get("variations") or []
        if variation.get("id") == variation_id
        and (variation.get("item_variation_data") or {}).get("name") == variation_name
        and not variation.get("is_deleted")
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one {variation_name} variation: {variation_id}")
    return matches[0]


def main() -> int:
    token = os.getenv("SQUARE_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("SQUARE_ACCESS_TOKEN is not configured")

    source = get_item(token, SOURCE_ITEM_ID, SOURCE_ITEM_NAME)
    source_variation = get_variation(source, SOURCE_VARIATION_ID, "Bottle")
    source_cost = ((source_variation.get("item_variation_data") or {}).get("default_unit_cost") or {})
    if source_cost != {"amount": EXPECTED_COST_CENTS, "currency": "EUR"}:
        raise RuntimeError(f"Source bottle unit cost has changed; refusing to guess: {source_cost}")

    target = get_item(token, TARGET_ITEM_ID, TARGET_ITEM_NAME)
    target_variation = get_variation(target, TARGET_VARIATION_ID, "Regular")
    data = target_variation.get("item_variation_data") or {}
    if ((data.get("price_money") or {}).get("amount")) != TARGET_PRICE_CENTS:
        raise RuntimeError("Takeaway price changed from €31.90; aborting to avoid wrong item")
    existing_cost = data.get("default_unit_cost")
    if existing_cost and existing_cost != source_cost:
        raise RuntimeError(f"Target already has a different unit cost: {existing_cost}")

    if existing_cost == source_cost:
        print("ALREADY CORRECT: Lombeline takeaway Regular unit COGS €14.31")
    else:
        updated = copy.deepcopy(target)
        updated_variation = get_variation(updated, TARGET_VARIATION_ID, "Regular")
        updated_variation["item_variation_data"]["vendor_information"] = [{"unit_cost_money": copy.deepcopy(source_cost)}]

        result = request_json(
            "POST", "/v2/catalog/object", token,
            body={"idempotency_key": str(uuid.uuid4()), "object": updated},
        )
        if result.get("errors"):
            raise RuntimeError(f"Square returned errors: {result['errors']}")
        returned = result.get("catalog_object") or {}
        if returned.get("id") != TARGET_ITEM_ID:
            raise RuntimeError("Square upsert response did not confirm target item")
        print("UPDATED live Square Lombeline takeaway Regular default unit cost to €14.31")

    live = get_item(token, TARGET_ITEM_ID, TARGET_ITEM_NAME)
    verified = get_variation(live, TARGET_VARIATION_ID, "Regular")["item_variation_data"]
    vendor_info = verified.get("vendor_information") or []
    if not vendor_info or (vendor_info[0].get("unit_cost_money") or {}) != source_cost:
        raise RuntimeError(f"Square vendor information read-back verification failed: {vendor_info}")
    if (verified.get("default_unit_cost") or {}) != source_cost:
        raise RuntimeError(f"Square default unit cost not reflected after vendor update: {verified.get('default_unit_cost')}")
    if ((verified.get("price_money") or {}).get("amount")) != TARGET_PRICE_CENTS:
        raise RuntimeError("Square read-back verification found an unexpected price change")
    print("VERIFIED live Square: cost €14.31, price €31.90")

    read, written = sync_catalog(token)
    print(f"REFRESHED Supabase catalogue mirror: read {read} objects, wrote {written} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
