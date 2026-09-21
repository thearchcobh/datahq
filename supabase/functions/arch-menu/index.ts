import "jsr:@supabase/functions-js/edge-runtime.d.ts";

type Json = Record<string, any>;

const WEBSITE_MENU_NAME = "Website Menu";
const STYLE_UIDS: Record<string, string> = {
  PIINJMUPVL2I36YGBMMI6APH: "Sparkling",
  ABPHBWJAN5OPJ5QGT4VDGM4F: "Rosé",
  QTRYK4OUXZLPKX5XJEX66PH5: "Orange / Skin Contact",
  QE65K7TGORUC6TAGFZEXBUFX: "White",
  ODJ4BA3FX67GCMC6I5JN2MWP: "Red",
  WK7HQNGAMJCBCSCDOATT6J4T: "Sweet / Fortified",
};
const CERT_UIDS: Record<string, string> = {
  LAJL2GU4V4A6RY2CX62MXJ5B: "O",
  "5N5B5WTJBTY4PLXYYZGDSOZU": "V",
  SFJC5ANYJJSDKFDPMFTBFWNT: "HVE",
  F4JIA252UXHCNBRJLQQYQQBU: "Bio",
};

const ORDER: Record<string, string[]> = {
  aperitif: ["Strawberry Lime Spritz","Aperol Spritz Cocktail","White Port & Tonic / Soda","Valentia Island Vermouth"],
  beer: ["Moretti","Peroni","Kinsale Pale Ale","Stag Kolsch Lager","Peroni 0.0%","Stonewell Medium Dry Irish Cider","Stonewell 0% Irish Cider"],
  digestif: ["Clos du Gravillas, Muscat","Van Zeller Ruby Port","Van Zeller White Port","Baileys Coffee Cocktail"],
  soft: ["Cherry Soda - Three Cents","Sparkling Lemonade - Three Cents","Pineapple Soda - Three Cents","Pink Grapefruit Soda - Three Cents","Orange Juice","Sparkling Water - 330ml","Sparkling Water - 750ml","Still water - 330ml","Still water - 750ml"],
  snacks: ["Smoked Almonds","Sourdough, Glenilen Butter","Nocarella Olives","Keogh’s Crisps - Roe","Keogh’s Crisps - Gilda","Watermelon Feta","Marinated Courgette"],
  plates: ["Peach, Whipped Ricotta, Mint, Prosciutto","Irish Tapenade & Dips Mezze","Irish Burrata Heirloom Tomato Caprese","Irish Burrata & Mortadella","Mixed Meat & Cheese Board"],
};

const WINE_ORDER: Record<string, string[]> = {
  "Sparkling:glass": ["Aromes De Celler Cava Brut","Tuffeau Brut Rosé"],
  "Rosé:glass": ["Peche Coquin"],
  "Orange / Skin Contact:glass": ["Ovella Negra"],
  "White:glass": ["Domaine de La Rochette Sauvignon Blanc","Laxas Albarino"],
  "Red:glass": ["Maretti Rosso 2022","Saint-Emilion 2016"],
  "Sparkling:bottle": ["Prosecco Masottina Contradagranda DOCG"],
  "Rosé:bottle": ["Josef Ehmoser Rose"],
  "Orange / Skin Contact:bottle": ["Bedoba Orange","Milan Nestarec- OKR"],
  "White:bottle": ["Boyante, Verdejo","Insolia Assuli Carinda DOC","Galets Dores, France","Jean Loron IGP Chardonnay","Baron de Badassiere Viognier IGP","'Lombeline’ Sauvignon Blanc","Domaine Zinck Pinot Blanc","Muscadet Sèvre et Maine sur lie","Azevedo Vinho Verde Loureiro/Alvarinho","Domaine Grosbois ‘Marnay’ 2023, Chenin Blanc"],
  "Red:bottle": ["El Olmo, Rioja","Terre Forti Nero D'Avola","Willunga 100","Primitivo Plantamua Giola del Colle","Jean Gamay Noir","La Griotte Malbec Cahors","Château Tayet Cuvée Prestige Bordeaux Supérior 2019","Cantina Atzei, ‘Saragat’, Monica","Dandelion Vineyards, ‘Lionheart of the Barossa’, Shiraz"],
};

const DISPLAY_NAMES: Record<string, string> = {
  "Aperol Spritz Cocktail": "Aperol Spritz",
  "White Port & Tonic / Soda": "White Port & Tonic",
  "Moretti": "Moretti — draught",
  "Peroni": "Peroni, Italian Lager — 330ml bottle",
  "Kinsale Pale Ale": "Blacks Kinsale Pale Ale — 500ml bottle",
  "Stag Kolsch Lager": "Stag Kölsch Lager — Gluten Free, 500ml bottle",
  "Peroni 0.0%": "Peroni 0.0% — 330ml bottle",
  "Stonewell Medium Dry Irish Cider": "Stonewell Irish Cider — 500ml bottle",
  "Stonewell 0% Irish Cider": "Stonewell 0% Irish Cider — 330ml bottle",
  "Van Zeller White Port": "White Port",
  "Baileys Coffee Cocktail": "Bailey’s Coffee",
  "Cherry Soda - Three Cents": "Cherry Soda",
  "Sparkling Lemonade - Three Cents": "Sparkling Lemonade",
  "Pineapple Soda - Three Cents": "Pineapple Soda",
  "Pink Grapefruit Soda - Three Cents": "Pink Grapefruit Soda",
  "Orange Juice": "Fresh Orange Juice",
  "Sparkling Water - 330ml": "WB Yeats Sparkling Water — 330ml",
  "Sparkling Water - 750ml": "WB Yeats Sparkling Water — 750ml",
  "Still water - 330ml": "WB Yeats Still Water — 330ml",
  "Still water - 750ml": "WB Yeats Still Water — 750ml",
  "Keogh’s Crisps - Roe": "Keogh’s Sea Salt Crisps — Roe, Crème Fraiche & Dill",
  "Keogh’s Crisps - Gilda": "Keogh’s Sea Salt Crisps — “The Gilda”",
  "Watermelon Feta": "Watermelon, Cucumber, Feta, Fennel, Chives",
  "Marinated Courgette": "Marinated Courgette, Ricotta, Hazelnut, Tarragon",
};

function getAttr(raw: Json, name: string): Json | null {
  const attrs = raw?.custom_attribute_values ?? {};
  for (const value of Object.values(attrs) as Json[]) {
    if (value?.name === name) return value;
  }
  return null;
}
function websiteFlag(raw: Json): boolean {
  return getAttr(raw, WEBSITE_MENU_NAME)?.boolean_value === true;
}
function stringAttr(raw: Json, name: string): string {
  return getAttr(raw, name)?.string_value ?? "";
}
function styleAttr(raw: Json): string {
  const attr = raw?.custom_attribute_values?.wine_style ?? getAttr(raw, "Wine Style");
  const uid = attr?.selection_uid_values?.[0];
  return uid ? (STYLE_UIDS[uid] ?? "") : "";
}
function certsAttr(raw: Json): string[] {
  const attr = raw?.custom_attribute_values?.certifications_dietary ?? getAttr(raw, "Certifications / Dietary");
  return (attr?.selection_uid_values ?? []).map((uid: string) => CERT_UIDS[uid]).filter(Boolean);
}
function rank(name: string, list: string[]): number {
  const idx = list.indexOf(name);
  return idx === -1 ? 9999 : idx;
}
async function rest(path: string): Promise<any[]> {
  const base = Deno.env.get("SUPABASE_URL")!;
  let key = "";
  let legacy = false;
  const newKeys = Deno.env.get("SUPABASE_SECRET_KEYS");
  if (newKeys) {
    try { key = JSON.parse(newKeys)?.default ?? ""; } catch { key = ""; }
  }
  if (!key) {
    key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
    legacy = true;
  }
  if (!key) throw new Error("No Supabase server key is available.");
  const headers: Record<string,string> = { apikey: key };
  if (legacy) headers.Authorization = `Bearer ${key}`;
  const response = await fetch(`${base}/rest/v1/${path}`, { headers });
  if (!response.ok) throw new Error(`Database request failed: ${response.status} ${await response.text()}`);
  return await response.json();
}
function cors(): Record<string,string> {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "content-type",
  };
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors() });
  if (req.method !== "GET") return new Response("Method not allowed", { status: 405, headers: { ...cors(), Allow: "GET, OPTIONS" } });

  try {
    const [itemsRaw, variationsRaw, categoriesRaw] = await Promise.all([
      rest("square_catalogue_items?select=id,name,category_id,raw_json,is_deleted"),
      rest("square_catalogue_variations?select=id,item_id,name,price_amount,raw_json,is_deleted"),
      rest("square_catalogue_categories?select=id,name"),
    ]);

    const categories = new Map(categoriesRaw.map((c:any) => [c.id,c.name]));
    const variationsByItem = new Map<string,any[]>();
    for (const v of variationsRaw) {
      if (v.is_deleted === true || !websiteFlag(v.raw_json)) continue;
      const list = variationsByItem.get(v.item_id) ?? [];
      list.push({
        id: v.id,
        name: v.name || "",
        price_amount: v.price_amount,
        ordinal: v.raw_json?.item_variation_data?.ordinal ?? 999,
      });
      variationsByItem.set(v.item_id, list);
    }

    const items:any[] = [];
    for (const row of itemsRaw) {
      const raw = row.raw_json ?? {};
      if (row.is_deleted === true || raw?.item_data?.is_archived === true || !websiteFlag(raw)) continue;
      const variations = (variationsByItem.get(row.id) ?? []).sort((a,b) => a.ordinal - b.ordinal);
      if (!variations.length) continue;
      const data = raw.item_data ?? {};
      items.push({
        id: row.id,
        name: row.name,
        display_name: DISPLAY_NAMES[row.name] ?? data.buyer_facing_name ?? row.name,
        category: categories.get(row.category_id) ?? "",
        description: data.description_plaintext ?? data.description ?? "",
        country: stringAttr(raw, "Country"),
        grape: stringAttr(raw, "Grape Variety"),
        tasting_notes: stringAttr(raw, "Tasting Notes") || data.description_plaintext || data.description || "",
        style: styleAttr(raw),
        certifications: certsAttr(raw),
        variations,
      });
    }

    const byName = new Map(items.map((x:any) => [x.name,x]));
    const ordered = (key:string) => (ORDER[key] ?? []).map((name) => byName.get(name)).filter(Boolean);
    const wines = items.filter((x:any) => x.style && x.style !== "Sweet / Fortified");

    const wineGlass = wines
      .filter((x:any) => x.variations.some((v:any) => /glass/i.test(v.name || "")))
      .sort((a:any,b:any) => {
        const ak = `${a.style}:glass`, bk = `${b.style}:glass`;
        if (a.style !== b.style) return Object.values(STYLE_UIDS).indexOf(a.style) - Object.values(STYLE_UIDS).indexOf(b.style);
        return rank(a.name,WINE_ORDER[ak] ?? []) - rank(b.name,WINE_ORDER[bk] ?? []);
      });

    const wineBottle = wines
      .filter((x:any) => {
        const hasGlass = x.variations.some((v:any) => /glass/i.test(v.name || ""));
        const hasBottle = x.variations.some((v:any) => /bottle/i.test(v.name || "")) || x.variations.length === 1;
        return !hasGlass && hasBottle;
      })
      .sort((a:any,b:any) => {
        const ak = `${a.style}:bottle`, bk = `${b.style}:bottle`;
        if (a.style !== b.style) return Object.values(STYLE_UIDS).indexOf(a.style) - Object.values(STYLE_UIDS).indexOf(b.style);
        return rank(a.name,WINE_ORDER[ak] ?? []) - rank(b.name,WINE_ORDER[bk] ?? []);
      });

    return Response.json({
      generated_at: new Date().toISOString(),
      sections: {
        aperitif: ordered("aperitif"),
        wine_glass: wineGlass,
        wine_bottle: wineBottle,
        beer: ordered("beer"),
        digestif: ordered("digestif"),
        soft: ordered("soft"),
        snacks: ordered("snacks"),
        plates: ordered("plates"),
      }
    }, {
      headers: {
        ...cors(),
        "Cache-Control": "public, max-age=60, s-maxage=300",
      }
    });
  } catch (error) {
    console.error(error);
    return Response.json({ error: "Menu temporarily unavailable" }, {
      status: 500,
      headers: { ...cors(), "Cache-Control": "no-store" },
    });
  }
});
