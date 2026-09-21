from __future__ import annotations

import argparse
import copy
import html
import os
import sys
import uuid
from typing import Any

from .square import request_json


WINE_METADATA: list[dict[str, Any]] = [
    {
        "menu_name": "Aromes De Celler Cava Brut",
        "aliases": ["Aromes De Celler Cava Brut"],
        "country": "Spain",
        "grape": "Macabeo, Parellada, Xarello",
        "tasting_notes": "White flowers, Pear, Baked Bread",
        "certifications": [],
        "style": "Sparkling",
        "buyer_facing_name": "Aromes De Celler Cava Brut",
    },
    {
        "menu_name": "Tuffeau Brut Rosé",
        "aliases": ["Tuffeau Brut Rosé"],
        "country": "France",
        "grape": "Gamay",
        "tasting_notes": "Raspberry, Pink Grapefruit",
        "certifications": ["HVE"],
        "style": "Sparkling",
        "buyer_facing_name": "Tuffeau Brut Rosé",
    },
    {
        "menu_name": "Peche Coquin 2025",
        "aliases": ["Peche Coquin"],
        "country": "France",
        "grape": "Cinsault, Syrah, Grenache",
        "tasting_notes": "Strawberry, Raspberry, Floral",
        "certifications": ["HVE"],
        "style": "Rosé",
        "buyer_facing_name": "Peche Coquin 2025",
    },
    {
        "menu_name": "Ovella Negra",
        "aliases": ["Ovella Negra"],
        "country": "Spain",
        "grape": "Garnacha Blanca, Malvasía de Sitges",
        "tasting_notes": "Peach juice, Orange Zest",
        "certifications": [],
        "style": "Orange / Skin Contact",
        "buyer_facing_name": "Ovella Negra",
    },
    {
        "menu_name": "Domaine de la Rochette, Sauvignon Blanc",
        "aliases": ["Domaine de La Rochette Sauvignon Blanc", "Domaine de la Rochette Sauvignon Blanc"],
        "country": "France",
        "grape": "Sauvignon Blanc",
        "tasting_notes": "Elderflower, Blackcurrant Leaf",
        "certifications": [],
        "style": "White",
        "buyer_facing_name": "Domaine de la Rochette",
    },
    {
        "menu_name": "Laxas Albarino",
        "aliases": ["Laxas Albarino"],
        "country": "Spain",
        "grape": "Albarino",
        "tasting_notes": "Green Apple, Pear, Lemon Zest",
        "certifications": [],
        "style": "White",
        "buyer_facing_name": "Laxas Albarino",
    },
    {
        "menu_name": "Maretti Langhe Rosso 2022",
        "aliases": ["Maretti Rosso 2022"],
        "country": "Italy",
        "grape": "Nebbiolo, Barbera",
        "tasting_notes": "Cherry, plum, dried herbs, anise, earthy, fresh acidity",
        "certifications": [],
        "style": "Red",
        "buyer_facing_name": "Maretti Langhe Rosso 2022",
    },
    {
        "menu_name": "Chateau Lyonnat Lussac Saint-Emilion",
        "aliases": ["Saint-Emilion 2016"],
        "country": "France",
        "grape": "Merlot, Cabernet Sauvignon",
        "tasting_notes": "Mature berry fruit, cassis, cedar, smooth fine tannins",
        "certifications": [],
        "style": "Red",
        "buyer_facing_name": "Chateau Lyonnat Lussac Saint-Emilion",
    },
    {
        "menu_name": "Masottina Prosecco Spumante DOCG",
        "aliases": ["Prosecco Masottina Contradagranda DOCG"],
        "country": "Italy",
        "grape": "Glera",
        "tasting_notes": "Citrus, Floral",
        "certifications": [],
        "style": "Sparkling",
        "buyer_facing_name": "Masottina Prosecco Spumante DOCG",
    },
    {
        "menu_name": "Josef Ehmoser",
        "aliases": ["Josef Ehmoser Rose"],
        "country": "Austria",
        "grape": "Zweigelt",
        "tasting_notes": "Tart Cherry, Raspberry, Crisp",
        "certifications": [],
        "style": "Rosé",
        "buyer_facing_name": "Josef Ehmoser",
    },
    {
        "menu_name": "Bedoba Orange",
        "aliases": ["Bedoba Orange"],
        "country": "Georgia",
        "grape": "Rkatsiteli",
        "tasting_notes": "Dried Apricots, Honey, Orange Peel",
        "certifications": [],
        "style": "Orange / Skin Contact",
        "buyer_facing_name": "Bedoba Orange",
    },
    {
        "menu_name": "Milan Nestarec OKR",
        "aliases": ["Milan Nestarec- OKR", "Milan Nestarec OKR"],
        "country": "Czech Republic",
        "grape": "Gruner Velt. Blend",
        "tasting_notes": "Rosewater, mandarin peel, white pepper and passionfruit",
        "certifications": [],
        "style": "Orange / Skin Contact",
        "buyer_facing_name": "Milan Nestarec OKR",
    },
    {
        "menu_name": "Boyante, Verdejo",
        "aliases": ["Boyante, Verdejo"],
        "country": "Spain",
        "grape": "Verdejo",
        "tasting_notes": "Citrus, Apple, Lychee, Mineral",
        "certifications": ["V"],
        "style": "White",
        "buyer_facing_name": "Boyante",
    },
    {
        "menu_name": "Insolia Assuli Carinda DOC",
        "aliases": ["Insolia Assuli Carinda DOC"],
        "country": "Italy",
        "grape": "Insolia",
        "tasting_notes": "Orange Blossom, Lemon, Marzipan",
        "certifications": [],
        "style": "White",
        "buyer_facing_name": "Insolia Assuli Carinda DOC",
    },
    {
        "menu_name": "Galets Dores",
        "aliases": ["Galets Dores, France"],
        "country": "France",
        "grape": "Roussanne, Grenache, Vermentino",
        "tasting_notes": "Honeysuckle, Clementine, well rounded",
        "certifications": [],
        "style": "White",
        "buyer_facing_name": "Galets Dores",
    },
    {
        "menu_name": "Jean Loron IGP Chardonnay",
        "aliases": ["Jean Loron IGP Chardonnay"],
        "country": "France",
        "grape": "Chardonnay",
        "tasting_notes": "Galia Melon, White Flowers, Citrus",
        "certifications": [],
        "style": "White",
        "buyer_facing_name": "Jean Loron IGP Chardonnay",
    },
    {
        "menu_name": "Baron de Badassiere Viognier IGP",
        "aliases": ["Baron de Badassiere Viognier IGP"],
        "country": "France",
        "grape": "Viognier",
        "tasting_notes": "Almond, Honey, Guava, Apricot",
        "certifications": [],
        "style": "White",
        "buyer_facing_name": "Baron de Badassiere Viognier IGP",
    },
    {
        "menu_name": "Coteaux du Giennois ‘Lombeline’ Sauvignon Blanc",
        "aliases": ["'Lombeline’ Sauvignon Blanc", "‘Lombeline’ Sauvignon Blanc"],
        "country": "France",
        "grape": "Sauvignon Blanc",
        "tasting_notes": "Gooseberry, Lemon, Lime",
        "certifications": [],
        "style": "White",
        "buyer_facing_name": "Coteaux du Giennois ‘Lombeline’ Sauvignon Blanc",
    },
    {
        "menu_name": "Domaine Zinck Pinot Blanc ‘Cuvee Portrait’",
        "aliases": ["Domaine Zinck Pinot Blanc"],
        "country": "France",
        "grape": "Pinot Blanc",
        "tasting_notes": "Yellow Pear, Apple, White Flowers",
        "certifications": ["Bio"],
        "style": "White",
        "buyer_facing_name": "Domaine Zinck Pinot Blanc ‘Cuvee Portrait’",
    },
    {
        "menu_name": "Muscadet Sèvre et Maine sur lie",
        "aliases": ["Muscadet Sèvre et Maine sur lie"],
        "country": "France",
        "grape": "Muscadet",
        "tasting_notes": "White blossoms, Pear, Almond",
        "certifications": ["O", "V"],
        "style": "White",
        "buyer_facing_name": "Muscadet Sèvre et Maine sur lie",
    },
    {
        "menu_name": "Azevedo Vinho Verde Loureiro/Alvarinho",
        "aliases": ["Azevedo Vinho Verde Loureiro/Alvarinho"],
        "country": "Portugal",
        "grape": "Loureiro/Alvarinho",
        "tasting_notes": "Nectarine, Lime Blossom, Fresh Mango",
        "certifications": [],
        "style": "White",
        "buyer_facing_name": "Azevedo Vinho Verde",
    },
    {
        "menu_name": "Domaine Grosbois ‘Marnay’ 2023",
        "aliases": ["Domaine Grosbois ‘Marnay’ 2023, Chenin Blanc", "Domaine Grosbois ‘Marnay’ 2023"],
        "country": "France",
        "grape": "Chenin Blanc",
        "tasting_notes": "Orchard Fruit, White Flowers, Graphite",
        "certifications": ["Bio"],
        "style": "White",
        "buyer_facing_name": "Domaine Grosbois ‘Marnay’ 2023",
    },
    {
        "menu_name": "El Olmo, Rioja Crianza",
        "aliases": ["El Olmo, Rioja"],
        "country": "Spain",
        "grape": "Tempranillo",
        "tasting_notes": "Red Cherry, Spice, Tobacco",
        "certifications": [],
        "style": "Red",
        "buyer_facing_name": "El Olmo, Rioja Crianza",
    },
    {
        "menu_name": "Terre Forti Nero D’Avola",
        "aliases": ["Terre Forti Nero D'Avola", "Terre Forti Nero D’Avola"],
        "country": "Italy",
        "grape": "Nero D'Avola",
        "tasting_notes": "Blackberries, Redcurrant, Cedar",
        "certifications": [],
        "style": "Red",
        "buyer_facing_name": "Terre Forti Nero D’Avola",
    },
    {
        "menu_name": "Willunga 100, McLaren Vale, Grenache",
        "aliases": ["Willunga 100"],
        "country": "Australia",
        "grape": "Grenache",
        "tasting_notes": "Strawberry, Black Pepper",
        "certifications": [],
        "style": "Red",
        "buyer_facing_name": "Willunga 100, McLaren Vale",
    },
    {
        "menu_name": "Primitivo Plantamua Giola del Colle",
        "aliases": ["Primitivo Plantamua Giola del Colle"],
        "country": "Italy",
        "grape": "Primitivo",
        "tasting_notes": "Plum, Blueberry, Red Cabbage, Spice",
        "certifications": [],
        "style": "Red",
        "buyer_facing_name": "Primitivo Plantamua Giola del Colle",
    },
    {
        "menu_name": "Jean Gamay Noir",
        "aliases": ["Jean Gamay Noir"],
        "country": "France",
        "grape": "Gamay Noir",
        "tasting_notes": "Ripe blackberry, blueberry, spicy, juicy",
        "certifications": [],
        "style": "Red",
        "buyer_facing_name": "Jean Gamay Noir",
    },
    {
        "menu_name": "La Griotte Malbec Cahors",
        "aliases": ["La Griotte Malbec Cahors"],
        "country": "France",
        "grape": "Malbec",
        "tasting_notes": "Sour Cherry, Blood Orange, Rose",
        "certifications": [],
        "style": "Red",
        "buyer_facing_name": "La Griotte Malbec Cahors",
    },
    {
        "menu_name": "Chateau Tayet",
        "aliases": ["Château Tayet Cuvée Prestige Bordeaux Supérior 2019"],
        "country": "France",
        "grape": "Merlot, Cabernet Sauvignon, Petit Verdot",
        "tasting_notes": "Black Plum, Vanilla, Spice",
        "certifications": [],
        "style": "Red",
        "buyer_facing_name": "Chateau Tayet",
    },
    {
        "menu_name": "Cantina Atzei, ‘Saragat’, Monica",
        "aliases": ["Cantina Atzei, ‘Saragat’, Monica"],
        "country": "Italy",
        "grape": "Monica",
        "tasting_notes": "Cherry, Plum, Spice",
        "certifications": ["Bio", "V"],
        "style": "Red",
        "buyer_facing_name": "Cantina Atzei, ‘Saragat’",
    },
    {
        "menu_name": "Dandelion Vineyards, ‘Lionheart of the Barossa’, Shiraz",
        "aliases": ["Dandelion Vineyards, ‘Lionheart of the Barossa’, Shiraz"],
        "country": "Australia",
        "grape": "Shiraz",
        "tasting_notes": "Rosemary, Dark Chocolate, Plums, White Pepper",
        "certifications": ["Bio", "V"],
        "style": "Red",
        "buyer_facing_name": "Dandelion Vineyards, ‘Lionheart of the Barossa’",
    },
    {
        "menu_name": "Clos du Gravillas, Muscat",
        "aliases": ["Clos du Gravillas, Muscat"],
        "country": "France",
        "grape": "Muscat",
        "tasting_notes": "Orange blossom, Honey, Almond",
        "certifications": [],
        "style": "Sweet / Fortified",
        "buyer_facing_name": "Clos du Gravillas",
    },
]


def list_catalog_objects(token: str, object_type: str) -> list[dict[str, Any]]:
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


def active_item(obj: dict[str, Any]) -> bool:
    if obj.get("type") != "ITEM" or obj.get("is_deleted"):
        return False
    data = obj.get("item_data") or {}
    return not bool(data.get("is_archived"))


def definition_by_name(definitions: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for obj in definitions:
        data = obj.get("custom_attribute_definition_data") or {}
        if data.get("name") == name and not obj.get("is_deleted"):
            return obj
    return None


def create_certification_definition(token: str) -> dict[str, Any]:
    body = {
        "idempotency_key": str(uuid.uuid4()),
        "object": {
            "type": "CUSTOM_ATTRIBUTE_DEFINITION",
            "id": "#certifications_dietary",
            "custom_attribute_definition_data": {
                "type": "SELECTION",
                "name": "Certifications / Dietary",
                "key": "certifications_dietary",
                "allowed_object_types": ["ITEM"],
                "seller_visibility": "SELLER_VISIBILITY_READ_WRITE_VALUES",
                "app_visibility": "APP_VISIBILITY_READ_WRITE_VALUES",
                "selection_config": {
                    "max_allowed_selections": 4,
                    "allowed_selections": [
                        {"uid": "#o", "name": "O"},
                        {"uid": "#v", "name": "V"},
                        {"uid": "#hve", "name": "HVE"},
                        {"uid": "#bio", "name": "Bio"},
                    ],
                },
            },
        },
    }
    response = request_json("POST", "/v2/catalog/object", token, body=body)
    return response["catalog_object"]



def create_wine_style_definition(token: str) -> dict[str, Any]:
    body = {
        "idempotency_key": str(uuid.uuid4()),
        "object": {
            "type": "CUSTOM_ATTRIBUTE_DEFINITION",
            "id": "#wine_style",
            "custom_attribute_definition_data": {
                "type": "SELECTION",
                "name": "Wine Style",
                "key": "wine_style",
                "allowed_object_types": ["ITEM"],
                "seller_visibility": "SELLER_VISIBILITY_READ_WRITE_VALUES",
                "app_visibility": "APP_VISIBILITY_READ_WRITE_VALUES",
                "selection_config": {
                    "max_allowed_selections": 1,
                    "allowed_selections": [
                        {"uid": "#sparkling", "name": "Sparkling"},
                        {"uid": "#rose", "name": "Rosé"},
                        {"uid": "#orange", "name": "Orange / Skin Contact"},
                        {"uid": "#white", "name": "White"},
                        {"uid": "#red", "name": "Red"},
                        {"uid": "#sweet_fortified", "name": "Sweet / Fortified"},
                    ],
                },
            },
        },
    }
    response = request_json("POST", "/v2/catalog/object", token, body=body)
    return response["catalog_object"]


def custom_attribute_value(definition: dict[str, Any], value: Any) -> dict[str, Any]:
    data = definition["custom_attribute_definition_data"]
    result: dict[str, Any] = {
        "key": data["key"],
        "custom_attribute_definition_id": definition["id"],
        "name": data["name"],
        "type": data["type"],
    }
    if data["type"] == "STRING":
        result["string_value"] = value
    elif data["type"] == "SELECTION":
        allowed = (data.get("selection_config") or {}).get("allowed_selections") or []
        by_name = {entry.get("name"): entry.get("uid") for entry in allowed}
        missing = [name for name in value if not by_name.get(name)]
        if missing:
            raise RuntimeError(f"Missing selection UID(s) for {missing} in {data['name']}")
        result["selection_uid_values"] = [by_name[name] for name in value]
    else:
        raise RuntimeError(f"Unsupported custom attribute type {data['type']} for {data['name']}")
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write changes to Square. Without this flag, only print the planned updates.")
    args = parser.parse_args()

    token = os.getenv("SQUARE_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("SQUARE_ACCESS_TOKEN is not configured")

    definitions = list_catalog_objects(token, "CUSTOM_ATTRIBUTE_DEFINITION")
    tasting_def = definition_by_name(definitions, "Tasting Notes")
    country_def = definition_by_name(definitions, "Country")
    grape_def = definition_by_name(definitions, "Grape Variety")
    cert_def = definition_by_name(definitions, "Certifications / Dietary")
    style_def = definition_by_name(definitions, "Wine Style")

    required = {
        "Tasting Notes": tasting_def,
        "Country": country_def,
        "Grape Variety": grape_def,
    }
    missing_defs = [name for name, obj in required.items() if obj is None]
    if missing_defs:
        raise RuntimeError(
            "Required existing Square custom attribute definitions were not visible to the API: "
            + ", ".join(missing_defs)
        )

    if cert_def is None:
        if not args.apply:
            print("PLAN: create SELECTION custom attribute 'Certifications / Dietary' with O, V, HVE, Bio")
        else:
            print("Creating custom attribute definition: Certifications / Dietary")
            create_certification_definition(token)
            definitions = list_catalog_objects(token, "CUSTOM_ATTRIBUTE_DEFINITION")
            cert_def = definition_by_name(definitions, "Certifications / Dietary")
            if cert_def is None:
                raise RuntimeError("Created Certifications / Dietary but could not retrieve it afterwards")

    if style_def is None:
        if not args.apply:
            print("PLAN: create SELECTION custom attribute 'Wine Style'")
        else:
            print("Creating custom attribute definition: Wine Style")
            create_wine_style_definition(token)
            definitions = list_catalog_objects(token, "CUSTOM_ATTRIBUTE_DEFINITION")
            style_def = definition_by_name(definitions, "Wine Style")
            if style_def is None:
                raise RuntimeError("Created Wine Style but could not retrieve it afterwards")

    items = [obj for obj in list_catalog_objects(token, "ITEM") if active_item(obj)]
    items_by_name: dict[str, list[dict[str, Any]]] = {}
    for obj in items:
        name = ((obj.get("item_data") or {}).get("name") or "").strip()
        items_by_name.setdefault(name.casefold(), []).append(obj)

    planned: list[tuple[dict[str, Any], dict[str, Any]]] = []
    missing_items: list[str] = []

    for meta in WINE_METADATA:
        matches: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for alias in meta["aliases"]:
            for obj in items_by_name.get(alias.strip().casefold(), []):
                if obj["id"] not in seen_ids:
                    matches.append(obj)
                    seen_ids.add(obj["id"])

        if not matches:
            missing_items.append(meta["menu_name"])
            print(f"MISSING: {meta['menu_name']}")
            continue

        if len(matches) > 1:
            print(
                f"NOTE: {meta['menu_name']} matched {len(matches)} active Square items; "
                "the same menu metadata will be applied to each."
            )

        for match in matches:
            planned.append((match, meta))
            print(
                f"PLAN: {match['id']} | {(match.get('item_data') or {}).get('name')} | "
                f"Country={meta['country'] or '-'} | Grape={meta['grape'] or '-'} | "
                f"Tasting Notes={meta['tasting_notes']} | "
                f"Certifications={','.join(meta['certifications']) or '-'} | "
                f"Style={meta['style']} | "
                f"Buyer Name={meta.get('buyer_facing_name') or '-'}"
            )

    if not args.apply:
        print(f"Dry run complete: {len(planned)} active Square item record(s) matched.")
        if missing_items:
            print("Missing menu wines: " + "; ".join(missing_items))
        return 0

    if cert_def is None:
        raise RuntimeError("Certifications / Dietary definition is unavailable")
    if style_def is None:
        raise RuntimeError("Wine Style definition is unavailable")

    updated = 0
    for match, meta in planned:
        item = retrieve_item(token, match["id"])
        item = copy.deepcopy(item)
        attrs = item.get("custom_attribute_values") or {}

        def replace_attribute_value(definition: dict[str, Any], value: Any | None) -> None:
            definition_id = definition["id"]
            # A seller-visible Square-defined attribute can already be stored under a
            # qualified map key (for example "Square:..."). Remove any existing value
            # that points at the same definition before adding the canonical value.
            for existing_key, existing_value in list(attrs.items()):
                if (existing_value or {}).get("custom_attribute_definition_id") == definition_id:
                    attrs.pop(existing_key, None)

            if value is not None:
                key = definition["custom_attribute_definition_data"]["key"]
                attrs[key] = custom_attribute_value(definition, value)

        replace_attribute_value(tasting_def, meta["tasting_notes"])

        if meta["country"]:
            replace_attribute_value(country_def, meta["country"])

        if meta["grape"]:
            replace_attribute_value(grape_def, meta["grape"])

        if meta["certifications"]:
            replace_attribute_value(cert_def, meta["certifications"])
        else:
            replace_attribute_value(cert_def, None)

        replace_attribute_value(style_def, [meta["style"]])

        item_data = item.get("item_data") or {}
        item_data["description"] = meta["tasting_notes"]
        item_data["description_html"] = f"<p>{html.escape(meta['tasting_notes'])}</p>"
        item_data.pop("description_plaintext", None)

        if meta.get("buyer_facing_name"):
            item_data["buyer_facing_name"] = meta["buyer_facing_name"]

        item["item_data"] = item_data
        item["custom_attribute_values"] = attrs
        upsert_item(token, item)
        updated += 1
        print(f"UPDATED: {item['id']} | {(item.get('item_data') or {}).get('name')}")

    print(f"Complete: updated {updated} active Square item record(s).")
    if missing_items:
        print("Menu wines not matched (left unchanged): " + "; ".join(missing_items))
    return 0


if __name__ == "__main__":
    sys.exit(main())
