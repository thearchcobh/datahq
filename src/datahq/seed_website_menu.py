from __future__ import annotations

import copy
import os
import sys
import uuid
from typing import Any

from .square import request_json, sync_catalog


ATTR_NAME = "Website Menu"
ATTR_KEY = "website_menu"

# Every explicitly listed non-wine item on the current v2 printed menus.
# For these items, all current active variations shown by Square are part of the menu.
NON_WINE_MENU_ALIASES: list[list[str]] = [
    ["Strawberry Lime Spritz"],
    ["Aperol Spritz Cocktail"],
    ["White Port & Tonic / Soda"],
    ["Valentia Island Vermouth"],
    ["Moretti"],
    ["Peroni"],
    ["Kinsale Pale Ale"],
    ["Stag Kolsch Lager"],
    ["Peroni 0.0%"],
    ["Stonewell Medium Dry Irish Cider"],
    ["Stonewell 0% Irish Cider"],
    ["Van Zeller Ruby Port"],
    ["Van Zeller White Port"],
    ["Baileys Coffee Cocktail"],
    ["Cherry Soda - Three Cents"],
    ["Sparkling Lemonade - Three Cents"],
    ["Pineapple Soda - Three Cents"],
    ["Pink Grapefruit Soda - Three Cents"],
    ["Orange Juice"],
    ["Sparkling Water - 330ml"],
    ["Sparkling Water - 750ml"],
    ["Still water - 330ml"],
    ["Still water - 750ml"],
    ["Smoked Almonds"],
    ["Sourdough, Glenilen Butter"],
    ["Nocarella Olives"],
    ["Keogh’s Crisps - Roe"],
    ["Keogh’s Crisps - Gilda"],
    ["Watermelon Feta"],
    ["Marinated Courgette"],
    ["Peach, Whipped Ricotta, Mint, Prosciutto"],
    ["Irish Tapenade & Dips Mezze"],
    ["Irish Burrata Heirloom Tomato Caprese"],
    ["Irish Burrata & Mortadella"],
    ["Mixed Meat & Cheese Board"],
]

# Current v2 wine menu. variation_names are the specific Square variations that
# are represented in print. An empty list with sole_variation=True means the
# active Square item has one unnamed/regular bottle variation.
WINE_MENU: list[dict[str, Any]] = [
    # By-the-glass sections: the printed line includes both glass and bottle prices.
    {"aliases": ["Aromes De Celler Cava Brut"], "variation_names": ["Glass", "Bottle"]},
    {"aliases": ["Tuffeau Brut Rosé"], "variation_names": ["Glass", "Bottle"]},
    {"aliases": ["Peche Coquin"], "variation_names": ["Glass", "Bottle"]},
    {"aliases": ["Ovella Negra"], "variation_names": ["Glass", "Bottle"]},
    {"aliases": ["Domaine de La Rochette Sauvignon Blanc", "Domaine de la Rochette Sauvignon Blanc"], "variation_names": ["Glass", "Bottle"]},
    {"aliases": ["Laxas Albarino"], "variation_names": ["Glass", "Bottle"]},
    {"aliases": ["Maretti Rosso 2022"], "variation_names": ["Bottle - Glass", "Bottle"]},
    {"aliases": ["Saint-Emilion 2016"], "variation_names": ["Glass", "Bottle"]},

    # Bottle-only sections.
    {"aliases": ["Prosecco Masottina Contradagranda DOCG"], "variation_names": ["Bottle"]},
    {"aliases": ["Josef Ehmoser Rose"], "variation_names": ["Bottle"]},
    {"aliases": ["Bedoba Orange"], "sole_variation": True},
    {"aliases": ["Milan Nestarec- OKR", "Milan Nestarec OKR"], "sole_variation": True},
    {"aliases": ["Boyante, Verdejo"], "variation_names": ["Bottle"]},
    {"aliases": ["Insolia Assuli Carinda DOC"], "variation_names": ["Bottle"]},
    {"aliases": ["Galets Dores, France"], "variation_names": ["Bottle"]},
    {"aliases": ["Jean Loron IGP Chardonnay"], "variation_names": ["Bottle"]},
    {"aliases": ["Baron de Badassiere Viognier IGP"], "sole_variation": True},
    {"aliases": ["'Lombeline’ Sauvignon Blanc", "‘Lombeline’ Sauvignon Blanc"], "variation_names": ["Bottle"]},
    {"aliases": ["Domaine Zinck Pinot Blanc"], "sole_variation": True},
    {"aliases": ["Muscadet Sèvre et Maine sur lie"], "variation_names": ["Bottle"]},
    {"aliases": ["Azevedo Vinho Verde Loureiro/Alvarinho"], "variation_names": ["Bottle"]},
    {"aliases": ["Domaine Grosbois ‘Marnay’ 2023, Chenin Blanc", "Domaine Grosbois ‘Marnay’ 2023"], "sole_variation": True},
    {"aliases": ["El Olmo, Rioja"], "variation_names": ["Bottle"]},
    {"aliases": ["Terre Forti Nero D'Avola", "Terre Forti Nero D’Avola"], "sole_variation": True},
    {"aliases": ["Willunga 100"], "sole_variation": True},
    {"aliases": ["Primitivo Plantamua Giola del Colle"], "variation_names": ["Bottle"]},
    {"aliases": ["Jean Gamay Noir"], "variation_names": ["Bottle"]},
    {"aliases": ["La Griotte Malbec Cahors"], "sole_variation": True},
    {"aliases": ["Château Tayet Cuvée Prestige Bordeaux Supérior 2019"], "variation_names": ["Bottle"]},
    {"aliases": ["Cantina Atzei, ‘Saragat’, Monica"], "sole_variation": True},
    {"aliases": ["Dandelion Vineyards, ‘Lionheart of the Barossa’, Shiraz"], "sole_variation": True},

    # Digestif: only the glass price is printed.
    {"aliases": ["Clos du Gravillas, Muscat"], "variation_names": ["Glass"]},
]


def list_catalog(token: str, object_type: str) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        params: dict[str, Any] = {"types": object_type}
        if cursor:
            params["cursor"] = cursor
        response = request_json("GET", "/v2/catalog/list", token, params=params)
        objects.extend(response.get("objects") or [])
        cursor = response.get("cursor")
        if not cursor:
            return objects


def is_active_item(obj: dict[str, Any]) -> bool:
    if obj.get("type") != "ITEM" or obj.get("is_deleted"):
        return False
    return not bool((obj.get("item_data") or {}).get("is_archived"))


def definition_by_name(definitions: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for obj in definitions:
        if obj.get("is_deleted"):
            continue
        data = obj.get("custom_attribute_definition_data") or {}
        if data.get("name") == name:
            return obj
    return None


def create_definition(token: str) -> dict[str, Any]:
    response = request_json(
        "POST",
        "/v2/catalog/object",
        token,
        body={
            "idempotency_key": str(uuid.uuid4()),
            "object": {
                "type": "CUSTOM_ATTRIBUTE_DEFINITION",
                "id": "#website_menu",
                "custom_attribute_definition_data": {
                    "type": "BOOLEAN",
                    "name": ATTR_NAME,
                    "key": ATTR_KEY,
                    "allowed_object_types": ["ITEM", "ITEM_VARIATION"],
                    "seller_visibility": "SELLER_VISIBILITY_READ_WRITE_VALUES",
                    "app_visibility": "APP_VISIBILITY_READ_WRITE_VALUES",
                },
            },
        },
    )
    if response.get("errors"):
        raise RuntimeError(response["errors"])
    return response["catalog_object"]


def website_value(definition: dict[str, Any], value: bool) -> dict[str, Any]:
    data = definition["custom_attribute_definition_data"]
    return {
        "key": data["key"],
        "custom_attribute_definition_id": definition["id"],
        "name": data["name"],
        "type": data["type"],
        "boolean_value": value,
    }


def remove_definition_value(attrs: dict[str, Any], definition_id: str) -> None:
    for key, value in list(attrs.items()):
        if (value or {}).get("custom_attribute_definition_id") == definition_id:
            attrs.pop(key, None)


def set_definition_value(obj: dict[str, Any], definition: dict[str, Any], enabled: bool) -> None:
    attrs = copy.deepcopy(obj.get("custom_attribute_values") or {})
    remove_definition_value(attrs, definition["id"])
    if enabled:
        attrs[ATTR_KEY] = website_value(definition, True)
    if attrs:
        obj["custom_attribute_values"] = attrs
    else:
        obj.pop("custom_attribute_values", None)


def upsert_item(token: str, item: dict[str, Any]) -> None:
    response = request_json(
        "POST",
        "/v2/catalog/object",
        token,
        body={"idempotency_key": str(uuid.uuid4()), "object": item},
    )
    if response.get("errors"):
        raise RuntimeError(response["errors"])


def normalize(value: str | None) -> str:
    return (value or "").strip().casefold()


def main() -> int:
    token = os.getenv("SQUARE_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("SQUARE_ACCESS_TOKEN is not configured")

    definitions = list_catalog(token, "CUSTOM_ATTRIBUTE_DEFINITION")
    definition = definition_by_name(definitions, ATTR_NAME)

    if definition is not None:
        data = definition.get("custom_attribute_definition_data") or {}
        allowed = set(data.get("allowed_object_types") or [])
        if data.get("type") != "BOOLEAN":
            raise RuntimeError(f"{ATTR_NAME} already exists but is not BOOLEAN")
        if not {"ITEM", "ITEM_VARIATION"}.issubset(allowed):
            raise RuntimeError(
                f"{ATTR_NAME} already exists but is not allowed on both ITEM and ITEM_VARIATION"
            )

    items = [obj for obj in list_catalog(token, "ITEM") if is_active_item(obj)]
    by_name: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        name = normalize((item.get("item_data") or {}).get("name"))
        by_name.setdefault(name, []).append(item)

    target_item_ids: set[str] = set()
    target_variation_ids: set[str] = set()
    resolved: list[str] = []

    def resolve_aliases(aliases: list[str]) -> dict[str, Any]:
        matches: list[dict[str, Any]] = []
        seen: set[str] = set()
        for alias in aliases:
            for item in by_name.get(normalize(alias), []):
                if item["id"] not in seen:
                    seen.add(item["id"])
                    matches.append(item)
        if len(matches) != 1:
            raise RuntimeError(
                f"Expected exactly one active Square item for {aliases}; found "
                f"{[(m['id'], (m.get('item_data') or {}).get('name')) for m in matches]}"
            )
        return matches[0]

    # Non-wines: parent item + all current variations are visible.
    for aliases in NON_WINE_MENU_ALIASES:
        item = resolve_aliases(aliases)
        target_item_ids.add(item["id"])
        variations = [
            v for v in ((item.get("item_data") or {}).get("variations") or [])
            if not v.get("is_deleted")
        ]
        if not variations:
            raise RuntimeError(f"No active variations for {(item.get('item_data') or {}).get('name')}")
        for variation in variations:
            target_variation_ids.add(variation["id"])
        resolved.append(
            f"{(item.get('item_data') or {}).get('name')} -> ALL ({len(variations)})"
        )

    # Wines: parent item + only the variations represented in v2 print.
    for spec in WINE_MENU:
        item = resolve_aliases(spec["aliases"])
        target_item_ids.add(item["id"])
        variations = [
            v for v in ((item.get("item_data") or {}).get("variations") or [])
            if not v.get("is_deleted")
        ]
        if not variations:
            raise RuntimeError(f"No active variations for {(item.get('item_data') or {}).get('name')}")

        selected: list[dict[str, Any]] = []
        if spec.get("sole_variation"):
            if len(variations) != 1:
                raise RuntimeError(
                    f"Expected one active variation for {(item.get('item_data') or {}).get('name')}; "
                    f"found {[((v.get('item_variation_data') or {}).get('name'), v['id']) for v in variations]}"
                )
            selected = variations
        else:
            wanted = {normalize(name) for name in spec["variation_names"]}
            selected = [
                v for v in variations
                if normalize((v.get("item_variation_data") or {}).get("name")) in wanted
            ]
            found = {
                normalize((v.get("item_variation_data") or {}).get("name"))
                for v in selected
            }
            if found != wanted:
                raise RuntimeError(
                    f"Variation mismatch for {(item.get('item_data') or {}).get('name')}: "
                    f"wanted={spec['variation_names']} found="
                    f"{[((v.get('item_variation_data') or {}).get('name'), v['id']) for v in variations]}"
                )

        for variation in selected:
            target_variation_ids.add(variation["id"])
        resolved.append(
            f"{(item.get('item_data') or {}).get('name')} -> "
            + ", ".join((v.get("item_variation_data") or {}).get("name") or "(unnamed)" for v in selected)
        )

    print(f"RESOLVED: {len(target_item_ids)} menu items")
    print(f"RESOLVED: {len(target_variation_ids)} menu variations")
    for line in resolved:
        print(f"  {line}")

    if definition is None:
        print(f"Creating custom attribute definition: {ATTR_NAME}")
        definition = create_definition(token)
        definitions = list_catalog(token, "CUSTOM_ATTRIBUTE_DEFINITION")
        definition = definition_by_name(definitions, ATTR_NAME)
        if definition is None:
            raise RuntimeError(f"Created {ATTR_NAME} but could not retrieve it")

    # Make the seed exact: Website Menu exists only on current v2 targets.
    # We update active parent items and their nested variations in one object write.
    updated = 0
    for original in items:
        item = copy.deepcopy(original)
        before = repr(item.get("custom_attribute_values")) + repr(
            [
                (v.get("id"), v.get("custom_attribute_values"))
                for v in ((item.get("item_data") or {}).get("variations") or [])
            ]
        )

        set_definition_value(item, definition, item["id"] in target_item_ids)

        for variation in ((item.get("item_data") or {}).get("variations") or []):
            if variation.get("is_deleted"):
                continue
            set_definition_value(
                variation,
                definition,
                variation.get("id") in target_variation_ids,
            )

        after = repr(item.get("custom_attribute_values")) + repr(
            [
                (v.get("id"), v.get("custom_attribute_values"))
                for v in ((item.get("item_data") or {}).get("variations") or [])
            ]
        )
        if before != after:
            upsert_item(token, item)
            updated += 1

    print(f"UPDATED: {updated} active Square item object(s)")

    sync_catalog(token)

    # Verify against live Square rather than relying only on the mirror.
    refreshed_items = [obj for obj in list_catalog(token, "ITEM") if is_active_item(obj)]
    flagged_items: set[str] = set()
    flagged_variations: set[str] = set()
    definition_id = definition["id"]

    def is_flagged(obj: dict[str, Any]) -> bool:
        for value in (obj.get("custom_attribute_values") or {}).values():
            if (
                (value or {}).get("custom_attribute_definition_id") == definition_id
                and (value or {}).get("boolean_value") is True
            ):
                return True
        return False

    for item in refreshed_items:
        if is_flagged(item):
            flagged_items.add(item["id"])
        for variation in ((item.get("item_data") or {}).get("variations") or []):
            if not variation.get("is_deleted") and is_flagged(variation):
                flagged_variations.add(variation["id"])

    if flagged_items != target_item_ids:
        raise RuntimeError(
            f"Item verification mismatch: missing={target_item_ids - flagged_items}, "
            f"extra={flagged_items - target_item_ids}"
        )
    if flagged_variations != target_variation_ids:
        raise RuntimeError(
            f"Variation verification mismatch: missing={target_variation_ids - flagged_variations}, "
            f"extra={flagged_variations - target_variation_ids}"
        )

    print(f"VERIFIED: {len(flagged_items)} Website Menu items")
    print(f"VERIFIED: {len(flagged_variations)} Website Menu variations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
