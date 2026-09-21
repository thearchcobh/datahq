from __future__ import annotations

import argparse
import os
import sys
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from .square import request_json, sync_catalog


SOURCE_NAMES = [
    "'Lombeline’ Sauvignon Blanc",
    "Azevedo Vinho Verde Loureiro/Alvarinho",
    "Cantina Atzei, ‘Saragat’, Monica",
    "Dandelion Vineyards, ‘Lionheart of the Barossa’, Shiraz",
    "Domaine Grosbois ‘Marnay’ 2023, Chenin Blanc",
    "Domaine Leon Boesch ‘La Cabane’, Pinot Blanc",
    "Domaine Zinck Pinot Blanc",
    "Horizon Pinot Noir",
    "La Griotte Malbec Cahors",
    "Maretti Rosso 2022",
    "Ovella Negra",
    "Peche Coquin",
    "Saint-Emilion 2016",
    "Torre Raone Montepulciano d’Abruzzo ‘Lucanto’",
    "Torreon Andes Collection Carmenere",
]

TAKEAWAY_CATEGORY_NAME = "Takeaway Wine"
VAT_MULTIPLIER = Decimal("1.23")
TARGET_GLASS_MARGIN = Decimal("0.70")
BOTTLE_DISCOUNT = Decimal("0.20")
TAKEAWAY_DISCOUNT = Decimal("15.00")
TENTH = Decimal("0.1")


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


def choose_bottle_variation(item: dict[str, Any]) -> dict[str, Any] | None:
    variations = [
        v for v in ((item.get("item_data") or {}).get("variations") or [])
        if not v.get("is_deleted")
    ]
    for variation in variations:
        name = (((variation.get("item_variation_data") or {}).get("name")) or "").strip().casefold()
        if name == "bottle":
            return variation
    if len(variations) == 1:
        return variations[0]

    fixed = [
        v for v in variations
        if ((v.get("item_variation_data") or {}).get("price_money") or {}).get("amount") is not None
    ]
    if fixed:
        return max(
            fixed,
            key=lambda v: int((((v.get("item_variation_data") or {}).get("price_money") or {}).get("amount")) or 0),
        )
    return None


def round_tenth(value: Decimal) -> Decimal:
    return value.quantize(TENTH, rounding=ROUND_HALF_UP)


def price_for_source(item: dict[str, Any]) -> tuple[Decimal, str, int | None]:
    variation = choose_bottle_variation(item)
    if variation is None:
        raise RuntimeError(f"No usable bottle/regular variation for {(item.get('item_data') or {}).get('name')}")

    data = variation.get("item_variation_data") or {}
    cost_money = data.get("default_unit_cost") or {}
    cost_cents = cost_money.get("amount")
    if cost_cents is not None:
        cost = Decimal(int(cost_cents)) / Decimal(100)
        glass = (cost / Decimal(5)) * VAT_MULTIPLIER / (Decimal(1) - TARGET_GLASS_MARGIN)
        bottle = glass * Decimal(5) * (Decimal(1) - BOTTLE_DISCOUNT)
        takeaway = round_tenth(bottle - TAKEAWAY_DISCOUNT)
        return takeaway, "70% glass GP -> 20% bottle discount -> €15 takeaway discount", int(cost_cents)

    price_money = data.get("price_money") or {}
    price_cents = price_money.get("amount")
    if price_cents is None:
        raise RuntimeError(f"No unit cost or dine-in price for {(item.get('item_data') or {}).get('name')}")
    dine_in = Decimal(int(price_cents)) / Decimal(100)
    return round_tenth(dine_in - TAKEAWAY_DISCOUNT), "fallback: current dine-in bottle/regular price minus €15 (unit cost missing)", None


def build_item(
    *,
    temp_id: str,
    name: str,
    price: Decimal,
    cost_cents: int | None,
    category_id: str,
    template_item: dict[str, Any],
) -> dict[str, Any]:
    template_data = template_item.get("item_data") or {}
    variation_data: dict[str, Any] = {
        "name": "Regular",
        "pricing_type": "FIXED_PRICING",
        "price_money": {"amount": int(price * Decimal(100)), "currency": "EUR"},
        "sellable": True,
        "stockable": True,
        "track_inventory": False,
    }
    if cost_cents is not None:
        variation_data["default_unit_cost"] = {"amount": cost_cents, "currency": "EUR"}

    channels = template_data.get("channels")
    if channels:
        variation_data["channels"] = channels

    item_data: dict[str, Any] = {
        "name": name,
        "tax_ids": list(template_data.get("tax_ids") or []),
        "categories": [{"id": category_id}],
        "reporting_category": {"id": category_id},
        "is_taxable": True,
        "variations": [
            {
                "type": "ITEM_VARIATION",
                "id": f"{temp_id}_variation",
                "present_at_all_locations": True,
                "item_variation_data": variation_data,
            }
        ],
        "product_type": template_data.get("product_type") or "FOOD_AND_BEV",
        "ecom_visibility": template_data.get("ecom_visibility") or "HIDDEN",
        "skip_modifier_screen": bool(template_data.get("skip_modifier_screen", True)),
    }
    if channels:
        item_data["channels"] = channels

    return {
        "type": "ITEM",
        "id": temp_id,
        "present_at_all_locations": True,
        "item_data": item_data,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    token = os.getenv("SQUARE_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("SQUARE_ACCESS_TOKEN is not configured")

    objects = list_catalog(token)
    categories = [obj for obj in objects if obj.get("type") == "CATEGORY" and not obj.get("is_deleted")]
    takeaway_categories = [
        obj for obj in categories
        if ((obj.get("category_data") or {}).get("name") or "").strip().casefold() == TAKEAWAY_CATEGORY_NAME.casefold()
    ]
    if not takeaway_categories:
        raise RuntimeError("Active Takeaway Wine category was not found in Square")
    category_id = takeaway_categories[0]["id"]

    active_items = [obj for obj in objects if is_active_item(obj)]
    by_name: dict[str, list[dict[str, Any]]] = {}
    for item in active_items:
        name = ((item.get("item_data") or {}).get("name") or "").strip()
        by_name.setdefault(name.casefold(), []).append(item)

    existing_takeaway_items = [item for item in active_items if category_id in category_ids(item)]
    existing_takeaway_names = {
        (((item.get("item_data") or {}).get("name")) or "").strip().casefold()
        for item in existing_takeaway_items
    }
    if not existing_takeaway_items:
        raise RuntimeError("No active takeaway wine item was available to use as a settings/tax template")
    template_item = existing_takeaway_items[0]
    if not (template_item.get("item_data") or {}).get("tax_ids"):
        raise RuntimeError("Takeaway wine template item has no tax_ids; refusing to create untaxed wine items")

    planned: list[dict[str, Any]] = []
    for index, source_name in enumerate(SOURCE_NAMES, start=1):
        matches = by_name.get(source_name.casefold(), [])
        if len(matches) != 1:
            raise RuntimeError(f"Expected exactly one active source item for {source_name!r}; found {len(matches)}")
        source = matches[0]
        target_name = f"{source_name} - Takeaway"
        if target_name.casefold() in existing_takeaway_names:
            print(f"SKIP: already active | {target_name}")
            continue

        price, basis, cost_cents = price_for_source(source)
        if price <= Decimal(0):
            raise RuntimeError(f"Calculated non-positive takeaway price for {source_name}: {price}")
        temp_id = f"#takeaway_{index}"
        planned.append(
            build_item(
                temp_id=temp_id,
                name=target_name,
                price=price,
                cost_cents=cost_cents,
                category_id=category_id,
                template_item=template_item,
            )
        )
        print(f"PLAN: {target_name} | €{price:.1f} | {basis}")

    if not planned:
        print("No missing takeaway wine entries remain.")
        return 0

    if not args.apply:
        print(f"Dry run complete: {len(planned)} item(s) would be created.")
        return 0

    response = request_json(
        "POST",
        "/v2/catalog/batch-upsert",
        token,
        body={
            "idempotency_key": str(uuid.uuid4()),
            "batches": [{"objects": planned}],
        },
    )
    if response.get("errors"):
        raise RuntimeError(f"Square returned catalog errors: {response['errors']}")

    created_names = {
        (((obj.get("item_data") or {}).get("name")) or "").strip()
        for obj in (response.get("objects") or [])
        if obj.get("type") == "ITEM"
    }
    expected_names = {
        (((obj.get("item_data") or {}).get("name")) or "").strip()
        for obj in planned
    }
    missing_from_response = expected_names - created_names
    if missing_from_response:
        raise RuntimeError("Square response did not confirm creation of: " + "; ".join(sorted(missing_from_response)))

    sync_catalog(token)

    refreshed = [obj for obj in list_catalog(token) if is_active_item(obj)]
    refreshed_names = {
        (((item.get("item_data") or {}).get("name")) or "").strip().casefold()
        for item in refreshed
        if category_id in category_ids(item)
    }
    not_visible = [name for name in expected_names if name.casefold() not in refreshed_names]
    if not_visible:
        raise RuntimeError("Created items were not visible in live Square verification: " + "; ".join(sorted(not_visible)))

    print(f"CREATED: {len(expected_names)} takeaway wine item(s)")
    for name in sorted(expected_names):
        print(f"VERIFIED: {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
