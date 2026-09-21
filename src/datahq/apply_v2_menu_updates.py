from __future__ import annotations

import os
import sys
import uuid
from typing import Any

from .square import request_json, sync_catalog


# Existing Square IDs / category structure
COCKTAILS_CATEGORY_ID = "XQLC4U3HZOJQDXAVFQBV3B2R"
PLATES_PRIMARY_ID = "22IEH7XIE25RJSK4E3VTF5P2"
PLATES_SECONDARY_ID = "GO2KUDZJVTYCGP2Y7Q4K5PJK"
ALCOHOL_TAX_ID = "LQPKLI6D5ZNOUJ7QXOLBKKOS"
FOOD_TAX_ID = "HZMGN7P223PQMEFSMIZVUHP4"

Rhubarb_NAME = "Rhubarb Spritz"
FOOD_TEMPLATE_NAME = "Irish Burrata & Prosciutto"

NEW_ITEMS = [
    {
        "name": "Strawberry Lime Spritz",
        "price_cents": 1300,
        "description": None,
        "category_ids": [COCKTAILS_CATEGORY_ID],
        "reporting_category_id": COCKTAILS_CATEGORY_ID,
        "tax_ids": [ALCOHOL_TAX_ID],
        "is_alcoholic": True,
        "template_name": Rhubarb_NAME,
    },
    {
        "name": "Peach, Whipped Ricotta, Mint, Prosciutto",
        "price_cents": 1400,
        "description": "Sliced Peach, Whipped Lemon Ricotta, Pistacchio, Mint, Sourdough",
        "category_ids": [PLATES_PRIMARY_ID, PLATES_SECONDARY_ID],
        "reporting_category_id": PLATES_PRIMARY_ID,
        "tax_ids": [FOOD_TAX_ID],
        "is_alcoholic": False,
        "template_name": FOOD_TEMPLATE_NAME,
    },
    {
        "name": "Irish Burrata Heirloom Tomato Caprese",
        "price_cents": 1600,
        "description": "Macroom Burrata, Heirloom Tomato, Basil Pesto, Sourdough",
        "category_ids": [PLATES_PRIMARY_ID, PLATES_SECONDARY_ID],
        "reporting_category_id": PLATES_PRIMARY_ID,
        "tax_ids": [FOOD_TAX_ID],
        "is_alcoholic": False,
        "template_name": FOOD_TEMPLATE_NAME,
    },
    {
        "name": "Irish Burrata & Mortadella",
        "price_cents": 1800,
        "description": "Macroom Burrata, Mortadella, Pistachio, Lemon, Sourdough",
        "category_ids": [PLATES_PRIMARY_ID, PLATES_SECONDARY_ID],
        "reporting_category_id": PLATES_PRIMARY_ID,
        "tax_ids": [FOOD_TAX_ID],
        "is_alcoholic": False,
        "template_name": FOOD_TEMPLATE_NAME,
    },
]

DESCRIPTION_UPDATES = {
    "Watermelon Feta": "Watermelon, Cucumber, Feta, Fennel, Chives",
    "Marinated Courgette": "Marinated Courgette, Ricotta, Hazelnut, Tarragon",
}

SMOKED_ALMONDS_NAME = "Smoked Almonds"


def list_catalog(token: str) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        params: dict[str, Any] = {"types": "ITEM"}
        if cursor:
            params["cursor"] = cursor
        data = request_json("GET", "/v2/catalog/list", token, params=params)
        objects.extend(data.get("objects") or [])
        cursor = data.get("cursor")
        if not cursor:
            return objects


def active_items(objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        o for o in objects
        if o.get("type") == "ITEM"
        and not o.get("is_deleted")
        and not bool((o.get("item_data") or {}).get("is_archived"))
    ]


def retrieve_item(token: str, item_id: str) -> dict[str, Any]:
    return request_json("GET", f"/v2/catalog/object/{item_id}", token)["object"]


def upsert_existing(token: str, item: dict[str, Any]) -> None:
    response = request_json(
        "POST",
        "/v2/catalog/object",
        token,
        body={"idempotency_key": str(uuid.uuid4()), "object": item},
    )
    if response.get("errors"):
        raise RuntimeError(response["errors"])


def build_new_item(spec: dict[str, Any], template: dict[str, Any], index: int) -> dict[str, Any]:
    td = template.get("item_data") or {}
    temp_id = f"#menu_item_{index}"
    variation_id = f"{temp_id}_variation"

    variation_data: dict[str, Any] = {
        "name": "Regular",
        "pricing_type": "FIXED_PRICING",
        "price_money": {"amount": spec["price_cents"], "currency": "EUR"},
        "sellable": True,
        "stockable": True,
        "track_inventory": False,
    }
    channels = td.get("channels")
    if channels:
        variation_data["channels"] = channels

    item_data: dict[str, Any] = {
        "name": spec["name"],
        "tax_ids": spec["tax_ids"],
        "categories": [{"id": cid} for cid in spec["category_ids"]],
        "reporting_category": {"id": spec["reporting_category_id"]},
        "is_taxable": True,
        "is_alcoholic": spec["is_alcoholic"],
        "product_type": "FOOD_AND_BEV",
        "ecom_visibility": "HIDDEN",
        "skip_modifier_screen": True,
        "kitchen_name": spec["name"],
        "variations": [
            {
                "type": "ITEM_VARIATION",
                "id": variation_id,
                "present_at_all_locations": True,
                "item_variation_data": variation_data,
            }
        ],
    }
    if channels:
        item_data["channels"] = channels
    if spec["description"]:
        item_data["description"] = spec["description"]

    return {
        "type": "ITEM",
        "id": temp_id,
        "present_at_all_locations": True,
        "item_data": item_data,
    }


def main() -> int:
    token = os.getenv("SQUARE_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("SQUARE_ACCESS_TOKEN is not configured")

    objects = list_catalog(token)
    all_by_name: dict[str, list[dict[str, Any]]] = {}
    for obj in objects:
        name = ((obj.get("item_data") or {}).get("name") or "").strip()
        if name:
            all_by_name.setdefault(name.casefold(), []).append(obj)

    current = active_items(objects)
    active_by_name = {
        ((obj.get("item_data") or {}).get("name") or "").strip().casefold(): obj
        for obj in current
    }

    # Create the four menu items only if they do not already exist.
    templates = {}
    for template_name in {spec["template_name"] for spec in NEW_ITEMS}:
        obj = active_by_name.get(template_name.casefold())
        if not obj:
            raise RuntimeError(f"Template item not found: {template_name}")
        templates[template_name] = obj

    new_objects: list[dict[str, Any]] = []
    expected_new: dict[str, int] = {}
    for idx, spec in enumerate(NEW_ITEMS, start=1):
        key = spec["name"].casefold()
        if key in active_by_name:
            print(f"SKIP CREATE: already active | {spec['name']}")
            expected_new[spec["name"]] = spec["price_cents"]
            continue
        archived_same_name = [
            o for o in all_by_name.get(key, [])
            if bool((o.get("item_data") or {}).get("is_archived"))
        ]
        if archived_same_name:
            raise RuntimeError(f"Archived item with exact name already exists; refusing duplicate: {spec['name']}")
        new_objects.append(build_new_item(spec, templates[spec["template_name"]], idx))
        expected_new[spec["name"]] = spec["price_cents"]
        print(f"PLAN CREATE: {spec['name']} | €{spec['price_cents']/100:.2f}")

    if new_objects:
        response = request_json(
            "POST",
            "/v2/catalog/batch-upsert",
            token,
            body={
                "idempotency_key": str(uuid.uuid4()),
                "batches": [{"objects": new_objects}],
            },
        )
        if response.get("errors"):
            raise RuntimeError(response["errors"])
        print(f"CREATED: {len(new_objects)} menu item(s)")

    # Update missing menu descriptions exactly from the v2 menu wording.
    for name, description in DESCRIPTION_UPDATES.items():
        obj = active_by_name.get(name.casefold())
        if not obj:
            # Newly created list is irrelevant here; both are existing items.
            raise RuntimeError(f"Description target not found: {name}")
        live = retrieve_item(token, obj["id"])
        data = live.get("item_data") or {}
        data["description"] = description
        live["item_data"] = data
        upsert_existing(token, live)
        print(f"DESCRIPTION UPDATED: {name}")

    # Remove only the incorrect NUT_FREE preference from Smoked Almonds.
    almonds = active_by_name.get(SMOKED_ALMONDS_NAME.casefold())
    if not almonds:
        raise RuntimeError("Smoked Almonds item not found")
    live_almonds = retrieve_item(token, almonds["id"])
    ad = live_almonds.get("item_data") or {}
    food_details = dict(ad.get("food_and_beverage_details") or {})
    prefs = list(food_details.get("dietary_preferences") or [])
    filtered = [
        p for p in prefs
        if not (
            (p or {}).get("type") == "STANDARD"
            and (p or {}).get("standard_name") == "NUT_FREE"
        )
    ]
    food_details["dietary_preferences"] = filtered
    ad["food_and_beverage_details"] = food_details
    live_almonds["item_data"] = ad
    upsert_existing(token, live_almonds)
    print("UPDATED: Smoked Almonds NUT_FREE removed")

    # Refresh Supabase mirror after live Square changes.
    sync_catalog(token)

    # Verify live Square.
    refreshed = active_items(list_catalog(token))
    refreshed_by_name = {
        ((obj.get("item_data") or {}).get("name") or "").strip().casefold(): obj
        for obj in refreshed
    }

    for name, expected_price in expected_new.items():
        obj = refreshed_by_name.get(name.casefold())
        if not obj:
            raise RuntimeError(f"Verification failed: missing {name}")
        variations = (obj.get("item_data") or {}).get("variations") or []
        prices = [
            ((v.get("item_variation_data") or {}).get("price_money") or {}).get("amount")
            for v in variations if not v.get("is_deleted")
        ]
        if expected_price not in prices:
            raise RuntimeError(f"Verification failed: wrong price for {name}: {prices}")
        print(f"VERIFIED CREATE: {name}")

    for name, expected_description in DESCRIPTION_UPDATES.items():
        obj = refreshed_by_name.get(name.casefold())
        actual = (obj.get("item_data") or {}).get("description")
        if actual != expected_description:
            raise RuntimeError(f"Verification failed: description mismatch for {name}")
        print(f"VERIFIED DESCRIPTION: {name}")

    almonds_check = refreshed_by_name.get(SMOKED_ALMONDS_NAME.casefold())
    details = ((almonds_check or {}).get("item_data") or {}).get("food_and_beverage_details") or {}
    prefs = details.get("dietary_preferences") or []
    if any((p or {}).get("standard_name") == "NUT_FREE" for p in prefs):
        raise RuntimeError("Verification failed: Smoked Almonds still marked NUT_FREE")
    ingredients = details.get("ingredients") or []
    if not any((p or {}).get("standard_name") == "TREE_NUTS" for p in ingredients):
        raise RuntimeError("Verification failed: Smoked Almonds TREE_NUTS ingredient marking was lost")
    print("VERIFIED: Smoked Almonds is not NUT_FREE and still contains TREE_NUTS")

    return 0


if __name__ == "__main__":
    sys.exit(main())
