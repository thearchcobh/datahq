#!/usr/bin/env python3
import copy
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid

API_BASE = "https://connect.squareup.com"
SQUARE_VERSION = "2026-09-16"
TOKEN = os.environ.get("SQUARE_ACCESS_TOKEN", "").strip()
DRY_RUN = os.environ.get("DRY_RUN", "1").lower() not in {"0", "false", "no"}

VENDOR_KEY = "supplier_vendor"
VENDOR_NAME = "Supplier / Vendor"
SKU_KEY = "supplier_vendor_sku"
SKU_NAME = "Supplier / Vendor SKU"

MAPPINGS = [
    {"canonical":"Azevedo Vinho Verde Loureiro/Alvarinho","vendor":"Liberty Wines","sku":"QZ103B24","aliases":["Azevedo Vinho Verde Loureiro/Alvarinho"]},
    {"canonical":"Baron de Badassiere Viognier IGP","vendor":"Liberty Wines","sku":"BA602B24","aliases":["Baron de Badassiere Viognier IGP","Baron De Badassiere, Viognier IGP"]},
    {"canonical":"Bedoba Orange","vendor":"Liberty Wines","sku":"BD102B23","aliases":["Bedoba Orange"]},
    {"canonical":"Boyante Verdejo","vendor":"The Wine Buff Cork","sku":None,"aliases":["Boyante Verdejo","Boyante, Verdejo"]},
    {"canonical":"Cantina Atzei ‘Saragat’ Monica","vendor":"Liberty Wines","sku":"AT202B23","aliases":["Cantina Atzei ‘Saragat’ Monica","Cantina Atzei, ‘Saragat’, Monica","Cantina Atzei 'Saragat' Monica"]},
    {"canonical":"Château Tayet Cuvée Prestige Bordeaux Supérieur 2019","vendor":"WineMason","sku":None,"aliases":["Château Tayet Cuvée Prestige Bordeaux Supérieur 2019","Château Tayet Cuvée Prestige Bordeaux Supérior 2019","Chateau Tayet Cuvee Prestige Bordeaux Superieur 2019"]},
    {"canonical":"Clos du Gravillas, Muscat","vendor":"La Rousse Wines","sku":"B0001679","aliases":["Clos du Gravillas, Muscat"]},
    {"canonical":"Dandelion Vineyards ‘Lionheart of the Barossa’ Shiraz","vendor":"Liberty Wines","sku":"DA101A22","aliases":["Dandelion Vineyards ‘Lionheart of the Barossa’ Shiraz","Dandelion Vineyards, ‘Lionheart of the Barossa’, Shiraz","Dandelion Vineyards 'Lionheart of the Barossa' Shiraz"]},
    {"canonical":"Domaine de La Rochette Sauvignon Blanc","vendor":"The Wine Buff Cork","sku":None,"aliases":["Domaine de La Rochette Sauvignon Blanc","Domaine de la Rochette, Sauvignon Blanc"]},
    {"canonical":"Domaine Leon Boesch ‘La Cabane’ Pinot Blanc","vendor":"La Rousse Wines","sku":"B0000140","aliases":["Domaine Leon Boesch ‘La Cabane’ Pinot Blanc","Domaine Leon Boesch ‘La Cabane’, Pinot Blanc","Domaine Leon Boesch 'La Cabane' Pinot Blanc","La Cabane"]},
    {"canonical":"El Olmo Rioja","vendor":"La Rousse Wines","sku":"B0006466","aliases":["El Olmo Rioja","El Olmo, Rioja"]},
    {"canonical":"Eric Texier ‘Adele’","vendor":"La Rousse Wines","sku":"B0001805","aliases":["Eric Texier ‘Adele’","Eric Texier 'Adele'"]},
    {"canonical":"Extra Ball","vendor":"La Rousse Wines","sku":"B0000815","aliases":["Extra Ball"]},
    {"canonical":"Gaba do Xil Godello","vendor":"La Rousse Wines","sku":"B0001580","aliases":["Gaba do Xil Godello"]},
    {"canonical":"Galets Dores","vendor":"Classic Drinks","sku":"495737","aliases":["Galets Dores","Galets Dores, France"]},
    {"canonical":"Guerila Rebula","vendor":"La Rousse Wines","sku":"B0008697","aliases":["Guerila Rebula"]},
    {"canonical":"Hervé Mathelin Brut Première Champagne","vendor":"The Wine Buff Cork","sku":None,"aliases":["Hervé Mathelin Brut Première Champagne","Hervé Mathelin Brut Premiere champagne","Herve Mathelin Brut Premiere Champagne"]},
    {"canonical":"Horizon Pinot Noir","vendor":"WineMason","sku":None,"aliases":["Horizon Pinot Noir"]},
    {"canonical":"Insolia Assuli Carinda DOC","vendor":"Classic Drinks","sku":"499314","aliases":["Insolia Assuli Carinda DOC"]},
    {"canonical":"Jean Gamay Noir","vendor":"Classic Drinks","sku":"486548","aliases":["Jean Gamay Noir"]},
    {"canonical":"Jean Loron IGP Chardonnay","vendor":"Classic Drinks","sku":"486547","aliases":["Jean Loron IGP Chardonnay"]},
    {"canonical":"Josef Ehmoser Rosé","vendor":"La Rousse Wines","sku":"B0000898","aliases":["Josef Ehmoser Rosé","Josef Ehmoser Rose"]},
    {"canonical":"Laxas Albariño","vendor":"La Rousse Wines","sku":"B0000419","aliases":["Laxas Albariño","Laxas Albarino"]},
    {"canonical":"Les Silènes","vendor":"WineMason","sku":None,"aliases":["Les Silènes","Les Silenes"]},
    {"canonical":"Malbec Sur un G/R Gascon","vendor":"WineMason","sku":None,"aliases":["Malbec Sur un G/R Gascon","Malbec Sur un G Gascon"]},
    {"canonical":"Maretti Rosso 2022","vendor":"La Rousse Wines","sku":"B0000640","aliases":["Maretti Rosso 2022"]},
    {"canonical":"Mas Coutelou Vin des Amis","vendor":"La Rousse Wines","sku":"B0000600","aliases":["Mas Coutelou Vin des Amis","La Vin des Amis, Mas Coutelou, Cinsault / Syrah","Vin des Amis"]},
    {"canonical":"Muscadet Sèvre et Maine sur lie","vendor":"WineMason","sku":None,"aliases":["Muscadet Sèvre et Maine sur lie","Muscadet Sevre et Maine sur lie"]},
    {"canonical":"Oveja Naranja 2023","vendor":"WineMason","sku":None,"aliases":["Oveja Naranja 2023"]},
    {"canonical":"Picpoul de Pinet Duc de Morny","vendor":"WineMason","sku":None,"aliases":["Picpoul de Pinet Duc de Morny"]},
    {"canonical":"Primitivo Plantamura Gioia del Colle","vendor":"Classic Drinks","sku":"499311","aliases":["Primitivo Plantamura Gioia del Colle","Primitivo Plantamua Giola del Colle","Primitivo Plantamura Giola del Colle"]},
    {"canonical":"Prosecco Masottina Contradagranda DOCG","vendor":"Classic Drinks","sku":"495918","aliases":["Prosecco Masottina Contradagranda DOCG"]},
    {"canonical":"Terre Forti Nero d'Avola","vendor":"Classic Drinks","sku":"TA211","aliases":["Terre Forti Nero d'Avola","Terre Forti Nero D'Avola"]},
    {"canonical":"Torre Raone Montepulciano d’Abruzzo ‘Lucanto’","vendor":"Classic Drinks","sku":"RA201","aliases":["Torre Raone Montepulciano d’Abruzzo ‘Lucanto’","Torre Raone Montepulciano d'Abruzzo 'Lucanto'"]},
    {"canonical":"Torreon Andes Collection Carmenere","vendor":"Classic Drinks","sku":"VR205","aliases":["Torreon Andes Collection Carmenere"]},
    {"canonical":"Tuffeau Brut Rosé","vendor":"La Rousse Wines","sku":"B0000859","aliases":["Tuffeau Brut Rosé","Tuffeau Brut Rose"]},
    {"canonical":"Willunga 100","vendor":"Liberty Wines","sku":"WI101B22","aliases":["Willunga 100"]},
]

def normalize_name(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().replace("&", " and ")
    value = re.sub(r"\s*-\s*takeaway\s*$", "", value, flags=re.I)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()

for row in MAPPINGS:
    row["_norm_aliases"] = {normalize_name(a) for a in row["aliases"]}

def api_request(method, path, body=None, query=None, retries=4):
    if not TOKEN:
        raise RuntimeError("SQUARE_ACCESS_TOKEN is not available")
    url = API_BASE + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    headers = {
        "Authorization": "Bearer " + TOKEN,
        "Square-Version": SQUARE_VERSION,
        "Content-Type": "application/json",
    }
    data = None if body is None else json.dumps(body).encode("utf-8")
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = resp.read().decode("utf-8")
                return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as exc:
            payload = exc.read().decode("utf-8", errors="replace")
            if exc.code == 429 and attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise RuntimeError(f"{method} {path} failed HTTP {exc.code}: {payload}") from exc

def list_catalog(types):
    out = []
    cursor = None
    while True:
        query = {"types": types}
        if cursor:
            query["cursor"] = cursor
        payload = api_request("GET", "/v2/catalog/list", query=query)
        out.extend(payload.get("objects", []))
        cursor = payload.get("cursor")
        if not cursor:
            return out

def make_writable(obj):
    obj = copy.deepcopy(obj)
    def clean(node):
        if isinstance(node, dict):
            node.pop("updated_at", None)
            node.pop("is_deleted", None)
            for value in list(node.values()):
                clean(value)
        elif isinstance(node, list):
            for value in node:
                clean(value)
    clean(obj)
    return obj

def find_matches(items):
    matches = []
    matched_canonicals = set()
    for item in items:
        if item.get("type") != "ITEM" or item.get("is_deleted"):
            continue
        name = (item.get("item_data") or {}).get("name") or ""
        n = normalize_name(name)
        hit = None
        for row in MAPPINGS:
            if n in row["_norm_aliases"]:
                hit = row
                break
        if hit:
            matches.append((item, hit))
            matched_canonicals.add(hit["canonical"])
    return matches, matched_canonicals

def get_definition(defs, key):
    for obj in defs:
        data = obj.get("custom_attribute_definition_data") or {}
        if data.get("key") == key:
            return obj
    return None

def create_definition(key, name, description):
    payload = api_request("POST", "/v2/catalog/object", {
        "idempotency_key": str(uuid.uuid4()),
        "object": {
            "type": "CUSTOM_ATTRIBUTE_DEFINITION",
            "id": "#" + key,
            "custom_attribute_definition_data": {
                "type": "STRING",
                "name": name,
                "description": description,
                "allowed_object_types": ["ITEM"],
                "seller_visibility": "SELLER_VISIBILITY_READ_WRITE_VALUES",
                "app_visibility": "APP_VISIBILITY_READ_WRITE_VALUES",
                "key": key,
            },
        },
    })
    return payload["catalog_object"]

def ensure_definitions():
    defs = list_catalog("CUSTOM_ATTRIBUTE_DEFINITION")
    vendor_def = get_definition(defs, VENDOR_KEY)
    sku_def = get_definition(defs, SKU_KEY)
    if vendor_def is None:
        vendor_def = create_definition(VENDOR_KEY, VENDOR_NAME, "Supplier or vendor for this catalogue item.")
        print(f"CREATED DEFINITION | {VENDOR_NAME} | {vendor_def['id']}")
    if sku_def is None:
        sku_def = create_definition(SKU_KEY, SKU_NAME, "Supplier or vendor's own SKU/code for this catalogue item.")
        print(f"CREATED DEFINITION | {SKU_NAME} | {sku_def['id']}")
    return vendor_def, sku_def

def set_string_attribute(item, key, name, definition_id, value):
    attrs = item.setdefault("custom_attribute_values", {})
    attrs[key] = {
        "key": key,
        "name": name,
        "type": "STRING",
        "custom_attribute_definition_id": definition_id,
        "string_value": value,
    }

def retrieve_item(item_id):
    payload = api_request("GET", "/v2/catalog/object/" + urllib.parse.quote(item_id, safe=""))
    return payload["object"]

def main():
    items = list_catalog("ITEM")
    matches, matched_canonicals = find_matches(items)

    print(f"DRY_RUN={DRY_RUN}")
    print(f"Active catalog items read: {len(items)}")
    print(f"Matched Square items: {len(matches)}")

    for item, row in matches:
        print("MATCH | " + " | ".join([
            row["canonical"],
            (item.get("item_data") or {}).get("name", ""),
            item.get("id", ""),
            row["vendor"],
            row["sku"] or "",
        ]))

    unmatched = [r["canonical"] for r in MAPPINGS if r["canonical"] not in matched_canonicals]
    for canonical in unmatched:
        print(f"UNMATCHED MAPPING | {canonical}")

    if DRY_RUN:
        return

    vendor_def, sku_def = ensure_definitions()
    vendor_def_id = vendor_def["id"]
    sku_def_id = sku_def["id"]

    updated = []
    for item, row in matches:
        writable = make_writable(item)
        set_string_attribute(writable, VENDOR_KEY, VENDOR_NAME, vendor_def_id, row["vendor"])
        if row["sku"]:
            set_string_attribute(writable, SKU_KEY, SKU_NAME, sku_def_id, row["sku"])

        payload = api_request("POST", "/v2/catalog/object", {
            "idempotency_key": str(uuid.uuid4()),
            "object": writable,
        })
        saved = payload["catalog_object"]
        updated.append((saved["id"], row))
        print(f"UPDATED | {(saved.get('item_data') or {}).get('name','')} | {row['vendor']} | {row['sku'] or ''}")
        time.sleep(0.20)

    failures = []
    for item_id, row in updated:
        current = retrieve_item(item_id)
        attrs = current.get("custom_attribute_values") or {}
        vendor_val = (attrs.get(VENDOR_KEY) or {}).get("string_value")
        sku_val = (attrs.get(SKU_KEY) or {}).get("string_value")
        if vendor_val != row["vendor"]:
            failures.append(f"{item_id}: vendor expected={row['vendor']!r} got={vendor_val!r}")
        if row["sku"] and sku_val != row["sku"]:
            failures.append(f"{item_id}: sku expected={row['sku']!r} got={sku_val!r}")

    print(f"VERIFIED UPDATED ITEMS: {len(updated) - len(failures)}/{len(updated)}")
    if failures:
        for failure in failures:
            print("VERIFY FAILURE | " + failure)
        raise RuntimeError("Verification failed for one or more Square items")

if __name__ == "__main__":
    main()
