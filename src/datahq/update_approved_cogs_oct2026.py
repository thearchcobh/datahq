"""One-time, guarded update of three user-approved Square unit costs.

Uses the same full-object Catalog upsert and live read-back technique as the
verified October Lombeline cost fix. Expected IDs, prices and initial costs are
checked before any update. Safe to rerun; leaves sale prices untouched.
"""
from __future__ import annotations

import copy
import os
import sys
import uuid

from .square import request_json, sync_catalog

TARGETS = (
    ("GFMBKHQ3M23PTKBEYUGT6YWW", "S'mores Hot Chocolate", "5Y6GFX45BBMNCIP7BCCLWSZE", 550, 207),
    ("M356GUWABYUGALEGHTO4OUI7", "Iced Pumpkin Spice Latte", "PFWE4AENYKWKZBRT4KZDTNEQ", 530, 97),
    ("4XSVTMBGCYYY2C44DDIDD67L", "Apple Pie Iced Latte", "2ZKQ4E2H7Z4YJMNZK6WK64IP", 550, 97),
)


def get_item(token: str, item_id: str, name: str) -> dict:
    obj = request_json("GET", f"/v2/catalog/object/{item_id}", token)["object"]
    details = obj.get("item_data") or {}
    if (obj.get("id") != item_id or obj.get("type") != "ITEM"
            or obj.get("is_deleted") or details.get("is_archived")
            or details.get("name") != name):
        raise RuntimeError(f"Unexpected live Square item for {item_id}: {details.get('name')!r}")
    return obj


def get_variation(obj: dict, variation_id: str) -> dict:
    matches = [
        v for v in ((obj.get("item_data") or {}).get("variations") or [])
        if v.get("id") == variation_id
        and (v.get("item_variation_data") or {}).get("name") == "Regular"
        and not v.get("is_deleted")
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one regular variation {variation_id}")
    return matches[0]


def validate(token: str, target: tuple) -> dict:
    item_id, name, variation_id, sale_price, cost_cents = target
    obj = get_item(token, item_id, name)
    variation = get_variation(obj, variation_id)
    data = variation["item_variation_data"]
    if (data.get("price_money") or {}).get("amount") != sale_price:
        raise RuntimeError(f"{name}: sale price unexpectedly changed; refusing to update")
    desired = {"amount": cost_cents, "currency": "EUR"}
    current = data.get("default_unit_cost") or {}
    vendor_info = data.get("vendor_information") or []
    if current and current != desired:
        raise RuntimeError(f"{name}: unit cost already differs from approved value: {current}")
    if vendor_info and (vendor_info[0].get("unit_cost_money") or {}) != desired:
        raise RuntimeError(f"{name}: existing vendor cost is unexpected: {vendor_info}")
    return obj


def main() -> int:
    token = os.getenv("SQUARE_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("SQUARE_ACCESS_TOKEN is not configured")
    # Preflight all three targets before making any changes.
    prepared = [(t, validate(token, t)) for t in TARGETS]
    for target, original in prepared:
        item_id, name, variation_id, sale_price, cost_cents = target
        desired = {"amount": cost_cents, "currency": "EUR"}
        data = get_variation(original, variation_id)["item_variation_data"]
        if data.get("default_unit_cost") == desired:
            print(f"ALREADY CORRECT: {name}: EUR {cost_cents / 100:.2f}")
        else:
            updated = copy.deepcopy(original)
            variation = get_variation(updated, variation_id)
            # Preserve the full catalog item, setting only the variation's vendor cost.
            variation["item_variation_data"]["vendor_information"] = [
                {"unit_cost_money": desired}
            ]
            result = request_json(
                "POST", "/v2/catalog/object", token,
                body={"idempotency_key": str(uuid.uuid4()), "object": updated},
            )
            returned = result.get("catalog_object") or {}
            if result.get("errors") or returned.get("id") != item_id:
                raise RuntimeError(f"Square upsert failed for {name}: {result.get('errors')}")
            print(f"UPDATED: {name}: EUR {cost_cents / 100:.2f}")
        # The API may accept a write without persisting the default cost.
        verified_obj = get_item(token, item_id, name)
        verified = get_variation(verified_obj, variation_id)["item_variation_data"]
        if verified.get("default_unit_cost") != desired:
            raise RuntimeError(f"{name}: live Square default unit cost read-back failed")
        vi = verified.get("vendor_information") or []
        if not vi or (vi[0].get("unit_cost_money") or {}) != desired:
            raise RuntimeError(f"{name}: live Square vendor cost read-back failed")
        if (verified.get("price_money") or {}).get("amount") != sale_price:
            raise RuntimeError(f"{name}: sale price unexpectedly changed")
        print(f"VERIFIED LIVE SQUARE: {name}: EUR {cost_cents / 100:.2f}; sale price unchanged")
    read, written = sync_catalog(token)
    print(f"Supabase catalogue refreshed: {read} objects read; {written} rows written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
