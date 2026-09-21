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
  aperitif: [
    "Strawberry Lime Spritz",
    "Aperol Spritz Cocktail",
    "White Port & Tonic / Soda",
    "Valentia Island Vermouth",
  ],
  beer: [
    "Moretti",
    "Peroni",
    "Kinsale Pale Ale",
    "Stag Kolsch Lager",
    "Peroni 0.0%",
    "Stonewell Medium Dry Irish Cider",
    "Stonewell 0% Irish Cider",
  ],
  digestif: [
    "Clos du Gravillas, Muscat",
    "Van Zeller Ruby Port",
    "Van Zeller White Port",
    "Baileys Coffee Cocktail",
  ],
  soft: [
    "Cherry Soda - Three Cents",
    "Sparkling Lemonade - Three Cents",
    "Pineapple Soda - Three Cents",
    "Pink Grapefruit Soda - Three Cents",
    "Orange Juice",
    "Sparkling Water - 330ml",
    "Sparkling Water - 750ml",
    "Still water - 330ml",
    "Still water - 750ml",
  ],
  snacks: [
    "Smoked Almonds",
    "Sourdough, Glenilen Butter",
    "Nocarella Olives",
    "Keogh’s Crisps - Roe",
    "Keogh’s Crisps - Gilda",
    "Watermelon Feta",
    "Marinated Courgette",
  ],
  plates: [
    "Peach, Whipped Ricotta, Mint, Prosciutto",
    "Irish Tapenade & Dips Mezze",
    "Irish Burrata Heirloom Tomato Caprese",
    "Irish Burrata & Mortadella",
    "Mixed Meat & Cheese Board",
  ],
};

const WINE_ORDER: Record<string, string[]> = {
  "Sparkling:glass": ["Aromes De Celler Cava Brut", "Tuffeau Brut Rosé"],
  "Rosé:glass": ["Peche Coquin"],
  "Orange / Skin Contact:glass": ["Ovella Negra"],
  "White:glass": ["Domaine de La Rochette Sauvignon Blanc", "Laxas Albarino"],
  "Red:glass": ["Maretti Rosso 2022", "Saint-Emilion 2016"],
  "Sparkling:bottle": ["Prosecco Masottina Contradagranda DOCG"],
  "Rosé:bottle": ["Josef Ehmoser Rose"],
  "Orange / Skin Contact:bottle": ["Bedoba Orange", "Milan Nestarec- OKR"],
  "White:bottle": [
    "Boyante, Verdejo",
    "Insolia Assuli Carinda DOC",
    "Galets Dores, France",
    "Jean Loron IGP Chardonnay",
    "Baron de Badassiere Viognier IGP",
    "'Lombeline’ Sauvignon Blanc",
    "Domaine Zinck Pinot Blanc",
    "Muscadet Sèvre et Maine sur lie",
    "Azevedo Vinho Verde Loureiro/Alvarinho",
    "Domaine Grosbois ‘Marnay’ 2023, Chenin Blanc",
  ],
  "Red:bottle": [
    "El Olmo, Rioja",
    "Terre Forti Nero D'Avola",
    "Willunga 100",
    "Primitivo Plantamua Giola del Colle",
    "Jean Gamay Noir",
    "La Griotte Malbec Cahors",
    "Château Tayet Cuvée Prestige Bordeaux Supérior 2019",
    "Cantina Atzei, ‘Saragat’, Monica",
    "Dandelion Vineyards, ‘Lionheart of the Barossa’, Shiraz",
  ],
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

const WINE_STYLE_ORDER = ["Sparkling", "Rosé", "Orange / Skin Contact", "White", "Red"];

function escapeHtml(value: unknown): string {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function getAttr(raw: Json, name: string): Json | null {
  const attrs = raw?.custom_attribute_values ?? {};
  for (const value of Object.values(attrs) as Json[]) {
    if (value?.name === name) return value;
  }
  return null;
}

function websiteFlag(raw: Json): boolean {
  const attr = getAttr(raw, WEBSITE_MENU_NAME);
  return attr?.boolean_value === true;
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
  const uids: string[] = attr?.selection_uid_values ?? [];
  return uids.map((uid) => CERT_UIDS[uid]).filter(Boolean);
}

function price(amount: number | null | undefined): string {
  if (amount == null) return "";
  return new Intl.NumberFormat("en-IE", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: amount % 100 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(amount / 100);
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
    try {
      key = JSON.parse(newKeys)?.default ?? "";
    } catch {
      key = "";
    }
  }
  if (!key) {
    key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
    legacy = true;
  }
  if (!key) throw new Error("No Supabase server key is available.");

  const headers: Record<string, string> = { apikey: key };
  if (legacy) headers.Authorization = `Bearer ${key}`;

  const response = await fetch(`${base}/rest/v1/${path}`, { headers });
  if (!response.ok) {
    throw new Error(`Database request failed: ${response.status} ${await response.text()}`);
  }
  return await response.json();
}

function renderSimpleItem(item: any): string {
  const vars = item.variations;
  const prices = vars.map((v: any) => {
    const label = vars.length > 1 ? `<span class="var-label">${escapeHtml(v.name || "Regular")}</span>` : "";
    return `<span class="price-piece">${label}<strong>${escapeHtml(price(v.price_amount))}</strong></span>`;
  }).join("");

  const shownName = DISPLAY_NAMES[item.name] ?? item.displayName;
  const desc = (item.description || "").trim();
  const suppressDesc = desc.toLocaleLowerCase() === shownName.toLocaleLowerCase();

  return `
    <article class="menu-item">
      <div class="item-copy">
        <h3>${escapeHtml(shownName)}</h3>
        ${desc && !suppressDesc ? `<p>${escapeHtml(desc)}</p>` : ""}
      </div>
      <div class="item-price">${prices}</div>
    </article>`;
}

function renderWine(item: any, mode: "glass" | "bottle"): string {
  const glass = item.variations.find((v: any) => /glass/i.test(v.name || ""));
  const bottle = item.variations.find((v: any) => /bottle/i.test(v.name || "") && !/glass/i.test(v.name || ""))
    ?? (item.variations.length === 1 && !/glass/i.test(item.variations[0].name || "") ? item.variations[0] : null);

  let prices = "";
  if (mode === "glass" && glass) {
    prices = `<strong>${escapeHtml(price(glass.price_amount))}</strong>`;
    if (bottle) prices += `<span class="slash">/</span><strong>${escapeHtml(price(bottle.price_amount))}</strong>`;
  } else if (mode === "bottle" && bottle) {
    prices = `<strong>${escapeHtml(price(bottle.price_amount))}</strong>`;
  }

  const meta = [item.grape, item.country ? `(${item.country})` : ""].filter(Boolean).join(" ");
  const badges = item.certs.map((c: string) => `<span class="badge">${escapeHtml(c)}</span>`).join("");
  return `
    <article class="menu-item wine-item">
      <div class="item-copy">
        <h3>${escapeHtml(item.displayName)} ${badges}</h3>
        ${meta ? `<p class="meta">${escapeHtml(meta)}</p>` : ""}
        ${item.tasting ? `<p class="tasting">${escapeHtml(item.tasting)}</p>` : ""}
      </div>
      <div class="item-price wine-price">${prices}</div>
    </article>`;
}

function renderWinePanel(items: any[], mode: "glass" | "bottle"): string {
  const groups = WINE_STYLE_ORDER.map((style) => {
    const matches = items
      .filter((x) => x.style === style)
      .sort((a, b) => {
        const key = `${style}:${mode}`;
        return rank(a.name, WINE_ORDER[key] ?? []) - rank(b.name, WINE_ORDER[key] ?? []);
      });
    if (!matches.length) return "";
    return `
      <section class="wine-group">
        <h2>${escapeHtml(style === "Orange / Skin Contact" ? "Orange / Skin Contact" : style)}</h2>
        ${matches.map((x) => renderWine(x, mode)).join("")}
      </section>`;
  }).join("");

  return groups || `<p class="empty">Nothing currently listed in this section.</p>`;
}

function pageHtml(menu: any): string {
  const sections = [
    ["aperitif", "Aperitif"],
    ["wine-glass", "Wine by the Glass"],
    ["wine-bottle", "Wine by the Bottle"],
    ["beer", "Beer & Cider"],
    ["digestif", "Digestif"],
    ["soft", "Best of the Rest"],
    ["snacks", "Snacks & Small Bites"],
    ["plates", "Sharing Plates"],
  ];

  const simple = (key: string) => menu[key].map(renderSimpleItem).join("") || '<p class="empty">Nothing currently listed in this section.</p>';

  const panels = `
    <section class="panel active" data-panel="aperitif">
      <header class="section-head"><p class="eyebrow">Drinks</p><h1>Aperitif</h1></header>
      ${simple("aperitif")}
    </section>
    <section class="panel" data-panel="wine-glass">
      <header class="section-head"><p class="eyebrow">Wine</p><h1>By the Glass</h1></header>
      ${renderWinePanel(menu.wineGlass, "glass")}
      <p class="legend">O = Organic · HVE = High Environmental Value · Bio = Biodynamic · V = Vegan</p>
    </section>
    <section class="panel" data-panel="wine-bottle">
      <header class="section-head"><p class="eyebrow">Wine</p><h1>By the Bottle</h1></header>
      ${renderWinePanel(menu.wineBottle, "bottle")}
      <p class="legend">O = Organic · HVE = High Environmental Value · Bio = Biodynamic · V = Vegan</p>
    </section>
    <section class="panel" data-panel="beer">
      <header class="section-head"><p class="eyebrow">Drinks</p><h1>Beer & Cider</h1></header>
      ${simple("beer")}
    </section>
    <section class="panel" data-panel="digestif">
      <header class="section-head"><p class="eyebrow">Drinks</p><h1>Digestif</h1></header>
      ${simple("digestif")}
    </section>
    <section class="panel" data-panel="soft">
      <header class="section-head"><p class="eyebrow">Drinks</p><h1>Best of the Rest</h1></header>
      ${simple("soft")}
      <p class="availability-note">Full range of teas & coffees available.</p>
    </section>
    <section class="panel" data-panel="snacks">
      <header class="section-head"><p class="eyebrow">Food · from 2pm</p><h1>Snacks & Small Bites</h1></header>
      ${simple("snacks")}
    </section>
    <section class="panel" data-panel="plates">
      <header class="section-head"><p class="eyebrow">Food · from 2pm</p><h1>Sharing Plates</h1></header>
      ${simple("plates")}
    </section>`;

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Arch Menu</title>
<style>
  :root{--paper:#fbfaf7;--ink:#22211e;--muted:#766f66;--line:#ded9d0;--accent:#6e263a;--chip:#f0ece5}
  *{box-sizing:border-box}
  html,body{margin:0;padding:0;background:transparent;color:var(--ink)}
  body{font-family:Arial,Helvetica,sans-serif;-webkit-font-smoothing:antialiased}
  .menu-shell{max-width:980px;margin:0 auto;padding:8px 18px 26px}
  .tabs-wrap{position:sticky;top:0;z-index:5;background:rgba(251,250,247,.97);backdrop-filter:blur(8px);padding:10px 0 12px;border-bottom:1px solid var(--line)}
  .tabs{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;padding:0 1px}
  .tabs::-webkit-scrollbar{display:none}
  .tab{flex:0 0 auto;border:1px solid var(--line);background:white;color:var(--ink);border-radius:999px;padding:9px 13px;font-size:13px;font-weight:600;cursor:pointer}
  .tab.active{background:var(--ink);border-color:var(--ink);color:white}
  .panel{display:none;padding-top:28px}
  .panel.active{display:block}
  .section-head{margin:0 0 18px}
  .eyebrow{text-transform:uppercase;letter-spacing:.13em;font-size:11px;font-weight:700;color:var(--muted);margin:0 0 5px}
  h1{font-family:Georgia,'Times New Roman',serif;font-size:34px;line-height:1.05;font-weight:500;margin:0}
  .wine-group{margin:27px 0 0}
  .wine-group:first-of-type{margin-top:0}
  .wine-group>h2{font-family:Georgia,'Times New Roman',serif;font-size:21px;font-weight:500;margin:0;padding:0 0 8px;border-bottom:1px solid var(--ink)}
  .menu-item{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:20px;padding:14px 0;border-bottom:1px solid var(--line)}
  .item-copy h3{font-size:15px;line-height:1.35;margin:0;font-weight:650}
  .item-copy p{font-size:13px;line-height:1.45;color:var(--muted);margin:5px 0 0}
  .item-copy .tasting{font-family:Georgia,'Times New Roman',serif;font-style:italic}
  .item-price{display:flex;gap:10px;align-items:flex-start;white-space:nowrap;text-align:right;font-size:14px}
  .price-piece{display:flex;flex-direction:column;align-items:flex-end;gap:2px}
  .var-label{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
  .wine-price{align-items:center;gap:6px}
  .slash{color:var(--muted)}
  .badge{display:inline-block;vertical-align:1px;border:1px solid var(--line);border-radius:4px;padding:1px 4px;margin-left:4px;font-size:9px;letter-spacing:.04em;color:var(--muted)}
  .legend,.availability-note,.empty{font-size:12px;line-height:1.45;color:var(--muted);margin:18px 0 0}
  @media(max-width:600px){
    .menu-shell{padding:6px 13px 22px}
    .tabs-wrap{padding-top:7px}
    h1{font-size:29px}
    .menu-item{gap:12px;padding:13px 0}
    .item-copy h3{font-size:14px}
    .item-copy p{font-size:12.5px}
    .item-price{font-size:13px}
    .wine-group>h2{font-size:19px}
  }
</style>
</head>
<body>
<div class="menu-shell">
  <nav class="tabs-wrap" aria-label="Menu sections">
    <div class="tabs">
      ${sections.map(([key,label],i) => `<button class="tab ${i===0?"active":""}" type="button" data-tab="${key}">${escapeHtml(label)}</button>`).join("")}
    </div>
  </nav>
  <main>${panels}</main>
</div>
<script>
(() => {
  const tabs=[...document.querySelectorAll('.tab')];
  const panels=[...document.querySelectorAll('.panel')];

  function sendHeight(){
    const height=Math.ceil(document.documentElement.scrollHeight);
    parent.postMessage({type:'arch-menu-height',height}, '*');
  }

  function select(key){
    tabs.forEach(t=>t.classList.toggle('active',t.dataset.tab===key));
    panels.forEach(p=>p.classList.toggle('active',p.dataset.panel===key));
    window.scrollTo({top:0,behavior:'instant'});
    requestAnimationFrame(()=>requestAnimationFrame(sendHeight));
  }

  tabs.forEach(t=>t.addEventListener('click',()=>select(t.dataset.tab)));
  new ResizeObserver(sendHeight).observe(document.body);
  window.addEventListener('load',sendHeight);
  sendHeight();
})();
</script>
</body>
</html>`;
}

Deno.serve(async (req: Request) => {
  if (req.method !== "GET" && req.method !== "HEAD") {
    return new Response("Method not allowed", { status: 405, headers: { Allow: "GET, HEAD" } });
  }

  try {
    const [itemsRaw, variationsRaw, categoriesRaw] = await Promise.all([
      rest("square_catalogue_items?select=id,name,category_id,raw_json,is_deleted"),
      rest("square_catalogue_variations?select=id,item_id,name,price_amount,raw_json,is_deleted"),
      rest("square_catalogue_categories?select=id,name"),
    ]);

    const categories = new Map(categoriesRaw.map((c: any) => [c.id, c.name]));
    const variationsByItem = new Map<string, any[]>();
    for (const v of variationsRaw) {
      if (v.is_deleted === true || !websiteFlag(v.raw_json)) continue;
      const list = variationsByItem.get(v.item_id) ?? [];
      list.push(v);
      variationsByItem.set(v.item_id, list);
    }

    const items: any[] = [];
    for (const row of itemsRaw) {
      const raw = row.raw_json ?? {};
      if (row.is_deleted === true || raw?.item_data?.is_archived === true || !websiteFlag(raw)) continue;
      const vars = variationsByItem.get(row.id) ?? [];
      if (!vars.length) continue;

      const data = raw.item_data ?? {};
      items.push({
        id: row.id,
        name: row.name,
        displayName: data.buyer_facing_name || row.name,
        category: categories.get(row.category_id) ?? "",
        description: data.description_plaintext || data.description || "",
        country: stringAttr(raw, "Country"),
        grape: stringAttr(raw, "Grape Variety"),
        tasting: stringAttr(raw, "Tasting Notes") || data.description_plaintext || data.description || "",
        style: styleAttr(raw),
        certs: certsAttr(raw),
        variations: vars.sort((a,b) => (a.raw_json?.item_variation_data?.ordinal ?? 999) - (b.raw_json?.item_variation_data?.ordinal ?? 999)),
      });
    }

    const byName = new Map(items.map((x) => [x.name, x]));
    const ordered = (key: string) => (ORDER[key] ?? []).map((n) => byName.get(n)).filter(Boolean);

    const wineItems = items.filter((x) => x.style && x.style !== "Sweet / Fortified");
    const wineGlass = wineItems.filter((x) => x.variations.some((v:any) => /glass/i.test(v.name || "")));
    const wineBottle = wineItems.filter((x) => {
      const hasGlass = x.variations.some((v:any) => /glass/i.test(v.name || ""));
      const hasBottle = x.variations.some((v:any) => /bottle/i.test(v.name || "")) || x.variations.length === 1;
      return !hasGlass && hasBottle;
    });

    const menu = {
      aperitif: ordered("aperitif"),
      beer: ordered("beer"),
      digestif: ordered("digestif"),
      soft: ordered("soft"),
      snacks: ordered("snacks"),
      plates: ordered("plates"),
      wineGlass,
      wineBottle,
    };

    const html = pageHtml(menu);
    if (req.method === "HEAD") {
      return new Response(null, {
        status: 200,
        headers: {
          "Content-Type": "text/html; charset=utf-8",
          "Cache-Control": "public, max-age=60, s-maxage=300",
        },
      });
    }
    return new Response(html, {
      status: 200,
      headers: {
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": "public, max-age=60, s-maxage=300",
      },
    });
  } catch (error) {
    console.error(error);
    return new Response(
      `<!doctype html><html><body style="font-family:Arial,sans-serif;padding:24px"><p>Menu temporarily unavailable. Please try again shortly.</p></body></html>`,
      { status: 500, headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" } },
    );
  }
});
