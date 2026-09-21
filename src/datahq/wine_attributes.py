from __future__ import annotations

import argparse
import copy
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
    },
    {
        "menu_name": "Tuffeau Brut Rosé",
        "aliases": ["Tuffeau Brut Rosé"],
        "country": "France",
        "grape": "Gamay",
        "tasting_notes": "Raspberry, Pink Grapefruit",
        "certifications": ["HVE"],
    },
    {
        "menu_name": "Peche Coquin 2025",
        "aliases": ["Peche Coquin"],
        "country": "France",
        "grape": None,
        "tasting_notes": "Strawberry, Raspberry, Floral",
        "certifications": ["HVE"],
    },
    {
        "menu_name": "Ovella Negra",
        "aliases": ["Ovella Negra"],
        "country": "Spain",
        "grape": None,
        "tasting_notes": "Peach juice, Orange Zest",
        "certifications": [],
    },
    {
        "menu_name": "Domaine de la Rochette, Sauvignon Blanc",
        "aliases": ["Domaine de La Rochette Sauvignon Blanc", "Domaine de la Rochette Sauvignon Blanc"],
        "country": "France",
        "grape": "Sauvignon Blanc",
        "tasting_notes": "Elderflower, Blackcurrant Leaf",
        "certifications": [],
    },
    {
        "menu_name": "Laxas Albarino",
        "aliases": ["Laxas Albarino"],
        "country": "Spain",
        "grape": "Albarino",
        "tasting_notes": "Green Apple, Pear, Lemon Zest",
        "certifications": [],
    },
    {
        "menu_name": "Maretti Langhe Rosso 2022",
        "aliases": ["Maretti Rosso 2022"],
        "country": "Italy",
        "grape": None,
        "tasting_notes": "Cherry, plum, dried herbs, anise, earthy, fresh acidity",
        "certifications": [],
    },
    {
        "menu_name": "Chateau Lyonnat Lussac Saint-Emilion",
        "aliases": ["Saint-Emilion 2016"],
        "country": "France",
        "grape": None,
        "tasting_notes": "Mature berry fruit, cassis, cedar, smooth fine tannins",
        "certifications": [],
    },
    {
        "menu_name": "Masottina Prosecco Spumante DOCG",
        "aliases": ["Prosecco Masottina Contradagranda DOCG"],
        "country": "Italy",
        "grape": "Glera",
        "tasting_notes": "Citrus, Floral",
        "certifications": [],
    },
    {
        "menu_name": "Josef Ehmoser",
        "aliases": ["Josef Ehmoser Rose"],
        "country": "Austria",
        "grape": "Zweigelt",
        "tasting_notes": "Tart Cherry, Raspberry, Crisp",
        "certifications": [],
    },
    {
        "menu_name": "Bedoba Orange",
        "aliases": ["Bedoba Orange"],
        "country": "Georgia",
        "grape": None,
        "tasting_notes": "Dried Apricots, Honey, Orange Peel",
        "certifications": [],
    },
    {
        "menu_name": "Milan Nestarec OKR",
        "aliases": ["Milan Nestarec- OKR", "Milan Nestarec OKR"],
        "country": "Czech Republic",
        "grape": "Gruner Velt. Blend",
        "tasting_notes": "Rosewater, mandarin peel, white pepper and passionfruit",
        "certifications": [],
    },
    {
        "menu_name": "Boyante, Verdejo",
        "aliases": ["Boyante, Verdejo"],
        "country": "Spain",
        "grape": "Verdejo",
        "tasting_notes": "Citrus, Apple, Lychee, Mineral",
        "certifications": ["V"],
    },
    {
        "menu_name": "Insolia Assuli Carinda DOC",
        "aliases": ["Insolia Assuli Carinda DOC"],
        "country": "Italy",
        "grape": "Insolia",
        "tasting_notes": "Orange Blossom, Lemon, Marzipan",
        "certifications": [],
    },
    {
        "menu_name": "Galets Dores",
        "aliases": ["Galets Dores, France"],
        "country": "France",
        "grape": "Roussanne, Grenache, Vermentino",
        "tasting_notes": "Honeysuckle, Clementine, well rounded",
        "certifications": [],
    },
    {
        "menu_name": "Jean Loron IGP Chardonnay",
        "aliases": ["Jean Loron IGP Chardonnay"],
        "country": "France",
        "grape": "Chardonnay",
        "tasting_notes": "Galia Melon, White Flowers, Citrus",
        "certifications": [],
    },
    {
        "menu_name": "Baron de Badassiere Viognier IGP",
        "aliases": ["Baron de Badassiere Viognier IGP"],
        "country": "France",
        "grape": "Viognier",
        "tasting_notes": "Almond, Honey, Guava, Apricot",
        "certifications": [],
    },
    {
        "menu_name": "Coteaux du Giennois ‘Lombeline’ Sauvignon Blanc",
        "aliases": ["'Lombeline’ Sauvignon Blanc", "‘Lombeline’ Sauvignon Blanc"],
        "country": "France",
        "grape": "Sauvignon Blanc",
        "tasting_notes": "Gooseberry, Lemon, Lime",
        "certifications": [],
    },
    {
        "menu_name": "Domaine Zinck Pinot Blanc ‘Cuvee Portrait’",
        "aliases": ["Domaine Zinck Pinot Blanc"],
        "country": None,
        "grape": "Pinot Blanc",
        "tasting_notes": "Yellow Pear, Apple, White Flowers",
        "certifications": ["Bio"],
    },
    {
        "menu_name": "Muscadet Sèvre et Maine sur lie",
        "aliases": ["Muscadet Sèvre et Maine sur lie"],
        "country": "France",
        "grape": "Muscadet",
        "tasting_notes": "White blossoms, Pear, Almond",
        "certifications": ["O", "V"],
    },
    {
        "menu_name": "Azevedo Vinho Verde Loureiro/Alvarinho",
        "aliases": ["Azevedo Vinho Verde Loureiro/Alvarinho"],
        "country": "Portugal",
        "grape": "Loureiro/Alvarinho",
        "tasting_notes": "Nectarine, Lime Blossom, Fresh Mango",
        "certifications": [],
    },
    {
        "menu_name": "Domaine Grosbois ‘Marnay’ 2023",
        "aliases": ["Domaine Grosbois ‘Marnay’ 2023, Chenin Blanc", "Domaine Grosbois ‘Marnay’ 2023"],
        "country": "France",
        "grape": "Chenin Blanc",
        "tasting_notes": "Orchard Fruit, White Flowers, Graphite",
        "certifications": ["Bio"],
    },
    {
        "menu_name": "El Olmo, Rioja Crianza",
        "aliases": ["El Olmo, Rioja"],
        "country": "Spain",
        "grape": "Tempranillo",
        "tasting_notes": "Red Cherry, Spice, Tobacco",
        "certifications": [],
    },
    {
        "menu_name": "Terre Forti Nero D’Avola",
        "aliases": ["Terre Forti Nero D'Avola", "Terre Forti Nero D’Avola"],
        "country": "Italy",
        "grape": "Nero D'Avola",
        "tasting_notes": "Blackberries, Redcurrant, Cedar",
        "certifications": [],
    },
    {
        "menu_name": "Willunga 100, McLaren Vale, Grenache",
        "aliases": ["Willunga 100"],
        "country": "South Africa",
        "grape": "Grenache",
        "tasting_notes": "Strawberry, Black Pepper",
        "certifications": [],
    },
    {
        "menu_name": "Primitivo Plantamua Giola del Colle",
        "aliases": ["Primitivo Plantamua Giola del Colle"],
        "country": "Italy",
        "grape": "Primitivo",
        "tasting_notes": "Plum, Blueberry, Red Cabbage, Spice",
        "certifications": [],
    },
    {
        "menu_name": "Jean Gamay Noir",
        "aliases": ["Jean Gamay Noir"],
        "country": "France",
        "grape": "Gamay Noir",
        "tasting_notes": "Ripe blackberry, blueberry, spicy, juicy",
        "certifications": [],
    },
    {
        "menu_name": "La Griotte Malbec Cahors",
        "aliases": ["La Griotte Malbec Cahors"],
        "country": "France",
        "grape": "Malbec",
        "tasting_notes": "Sour Cherry, Blood Orange, Rose",
        "certifications": [],
    },
    {
        "menu_name": "Chateau Tayet",
        "aliases": ["Château Tayet Cuvée Prestige Bordeaux Supérior 2019"],
        "country": "France",
        "grape": None,
        "tasting_notes": "Black Plum, Vanilla, Spice",
        "certifications": [],
    },
    {
        "menu_name": "Cantina Atzei, ‘Saragat’, Monica",
        "aliases": ["Cantina Atzei, ‘Saragat’, Monica"],
        "country": "Italy",
        "grape": "Monica",
        "tasting_notes": "Cherry, Plum, Spice",
        "certifications": ["Bio", "V"],
    },
    {
        "menu_name": "Dandelion Vineyards, ‘Lionheart of the Barossa’, Shiraz",
        "aliases": ["Dandelion Vineyards, ‘Lionheart of the Barossa’, Shiraz"],
        "country": "South Australia",
        "grape": "Shiraz",
        "tasting_notes": "Rosemary, Dark Chocolate, Plums, White Pepper",
        "certifications": ["Bio", "V"],
    },
    {
        "menu_name": "Clos du Gravillas, Muscat",
        "aliases": ["Clos du Gravillas, Muscat"],
        "country": "France",
        "grape": "Muscat",
        "tasting_notes": "Orange blossom, Honey, Almond",
        "certifications": [],
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
                f"Certifications={','.join(meta['certifications']) or '-'}"
            )

    if not args.apply:
        print(f"Dry run complete: {len(planned)} active Square item record(s) matched.")
        if missing_items:
            print("Missing menu wines: " + "; ".join(missing_items))
        return 0

    if cert_def is None:
        raise RuntimeError("Certifications / Dietary definition is unavailable")

    updated = 0
    for match, meta in planned:
        item = retrieve_item(token, match["id"])
        item = copy.deepcopy(item)
        attrs = item.get("custom_attribute_values") or {}

        attrs[tasting_def["custom_attribute_definition_data"]["key"]] = custom_attribute_value(
            tasting_def, meta["tasting_notes"]
        )

        if meta["country"]:
            attrs[country_def["custom_attribute_definition_data"]["key"]] = custom_attribute_value(
                country_def, meta["country"]
            )

        if meta["grape"]:
            attrs[grape_def["custom_attribute_definition_data"]["key"]] = custom_attribute_value(
                grape_def, meta["grape"]
            )

        cert_key = cert_def["custom_attribute_definition_data"]["key"]
        if meta["certifications"]:
            attrs[cert_key] = custom_attribute_value(cert_def, meta["certifications"])
        else:
            attrs.pop(cert_key, None)

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
