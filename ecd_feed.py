#!/usr/bin/env python3
"""
ECD Germany -> JSON feed
Cikkszam (Artikelnummer / Shopify SKU) alapu ar- es keszletfigyeleshez.

Adatforras: https://www.ecdgermany.de/products.json  (publikus Shopify vegpont,
API kulcs nem kell, nincs scraping, nincs blokkolasi kockazat)

Futtatas:  python3 ecd_feed.py [kimeneti_fajl.json]
"""

import json
import sys
import time
import urllib.request
from datetime import datetime, timezone

BASE = "https://www.ecdgermany.de"
LIMIT = 250
MAX_PAGES = 60
SLEEP = 0.4  # kimeletes tempo a szerverhez
UA = "Mozilla/5.0 (compatible; PriceFeedBot/1.0)"


def fetch_page(page):
    url = f"{BASE}/products.json?limit={LIMIT}&page={page}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))["products"]
        except Exception as e:
            if attempt == 2:
                raise
            print(f"  ! hiba a {page}. lapon ({e}), ujraprobalas...", file=sys.stderr)
            time.sleep(2 * (attempt + 1))


def to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def build():
    items = []
    seen_skus = set()
    page = 1

    while page <= MAX_PAGES:
        products = fetch_page(page)
        if not products:
            break
        print(f"  {page}. lap: {len(products)} termek", file=sys.stderr)

        for p in products:
            handle = p.get("handle", "")
            product_url = f"{BASE}/products/{handle}" if handle else None
            images = p.get("images") or []
            main_image = images[0]["src"] if images else None

            for v in p.get("variants", []):
                sku = (v.get("sku") or "").strip()
                if not sku:
                    continue  # cikkszam nelkul nem azonosithato

                price = to_float(v.get("price"))
                compare = to_float(v.get("compare_at_price"))
                available = bool(v.get("available"))

                # akcios-e: van eredeti ar es magasabb a mostaninal
                on_sale = bool(compare and price and compare > price)
                discount_pct = round((1 - price / compare) * 100, 1) if on_sale else 0.0

                var_title = v.get("title") or ""
                name = p.get("title", "")
                if var_title and var_title != "Default Title":
                    name = f"{name} - {var_title}"

                item = {
                    "cikkszam": sku,
                    "nev": name,
                    "ar_eur": price,
                    "listaar_eur": compare,
                    "akcios": on_sale,
                    "kedvezmeny_szazalek": discount_pct,
                    "keszleten": available,
                    "keszlet_szoveg": "készleten" if available else "elfogyott",
                    "penznem": "EUR",
                    "suly_gramm": v.get("grams"),
                    "gyarto": p.get("vendor"),
                    "kategoria": p.get("product_type") or None,
                    "url": product_url,
                    "kep": main_image,
                    "shopify_variant_id": v.get("id"),
                    "utolso_modositas": v.get("updated_at"),
                }

                if sku in seen_skus:
                    item["duplikalt_cikkszam"] = True
                seen_skus.add(sku)
                items.append(item)

        if len(products) < LIMIT:
            break
        page += 1
        time.sleep(SLEEP)

    items.sort(key=lambda x: x["cikkszam"])
    return items


def dedupe(items):
    """Cikkszam szerint egyedi lista. Utkozesnel a keszleten levo / dragabb
    (nem hibasan nullazott) valtozat nyer, hogy ne alulbecsuljuk az arat."""
    best = {}
    for i in items:
        sku = i["cikkszam"]
        prev = best.get(sku)
        if prev is None:
            best[sku] = dict(i)
            best[sku].pop("duplikalt_cikkszam", None)
            best[sku]["valtozatok_szama"] = 1
            continue
        prev["valtozatok_szama"] += 1
        # keszleten levo nyer; ha egyezik, a magasabb ar nyer
        better = (i["keszleten"], i["ar_eur"] or 0) > (prev["keszleten"], prev["ar_eur"] or 0)
        if better:
            cnt = prev["valtozatok_szama"]
            new = dict(i)
            new.pop("duplikalt_cikkszam", None)
            new["valtozatok_szama"] = cnt
            best[sku] = new
    return sorted(best.values(), key=lambda x: x["cikkszam"])


CSV_COLS = [
    "cikkszam", "nev", "ar_eur", "listaar_eur", "akcios", "kedvezmeny_szazalek",
    "keszleten", "keszlet_szoveg", "suly_gramm", "gyarto", "url", "kep",
    "utolso_modositas",
]

# Ha ennyi termek ala esik a feed, valami elromlott -> nem irjuk felul a jo adatot.
MIN_EXPECTED = 3000


def write_csv(items, path):
    import csv
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS, delimiter=";", extrasaction="ignore")
        w.writeheader()
        for i in items:
            w.writerow(i)


def sanity_check(items, out_path):
    """Csendes hiba elleni vedelem: ha a katalogus gyanusan osszezsugorodott,
    inkabb hibaval leallunk, mint hogy szemetet irjunk a feedbe."""
    if len(items) < MIN_EXPECTED:
        print(f"HIBA: csak {len(items)} termek jott le (minimum {MIN_EXPECTED}). "
              "A feed NEM lett felulirva.", file=sys.stderr)
        return False

    no_price = sum(1 for i in items if i["ar_eur"] is None)
    if no_price > len(items) * 0.2:
        print(f"HIBA: {no_price} termeknek nincs ara. A feed NEM lett felulirva.",
              file=sys.stderr)
        return False

    # Osszehasonlitas az elozo futassal, ha van
    try:
        with open(out_path, encoding="utf-8") as f:
            prev = json.load(f)
        prev_count = prev.get("osszesen", 0)
        if prev_count and len(items) < prev_count * 0.7:
            print(f"HIBA: a termekszam {prev_count} -> {len(items)} ra esett "
                  "(30%+ zuhanas). A feed NEM lett felulirva.", file=sys.stderr)
            return False
        if prev_count:
            print(f"  elozo futas: {prev_count} termek -> most: {len(items)}",
                  file=sys.stderr)
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass

    return True


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "ecd_feed.json"

    print("ECD Germany katalogus letoltese...", file=sys.stderr)
    raw = build()
    items = dedupe(raw)

    if not sanity_check(items, out_path):
        sys.exit(1)

    in_stock = sum(1 for i in items if i["keszleten"])
    on_sale = sum(1 for i in items if i["akcios"])
    prices = [i["ar_eur"] for i in items if i["ar_eur"] is not None]

    feed = {
        "forras": BASE,
        "generalva": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "penznem": "EUR",
        "azonosito_mezo": "cikkszam",
        "megjegyzes": "A cikkszam (Artikelnummer) egyedi ebben a feedben. "
                      "Az ECD nehany terméket duplan listaz; ilyenkor a keszleten "
                      "levo valtozat kerult be, a valtozatok_szama jelzi a duplumokat.",
        "osszesen": len(items),
        "nyers_sorok": len(raw),
        "keszleten": in_stock,
        "elfogyott": len(items) - in_stock,
        "akcios": on_sale,
        "atlagar_eur": round(sum(prices) / len(prices), 2) if prices else None,
        "termekek": items,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=2)

    csv_path = out_path.rsplit(".", 1)[0] + ".csv"
    write_csv(items, csv_path)

    print(f"\nKESZ: {out_path} + {csv_path}", file=sys.stderr)
    print(f"  egyedi cikkszam: {len(items)}  (nyers sorok: {len(raw)})", file=sys.stderr)
    print(f"  keszleten:       {in_stock}", file=sys.stderr)
    print(f"  elfogyott:       {len(items) - in_stock}", file=sys.stderr)
    print(f"  akcios:          {on_sale}", file=sys.stderr)


if __name__ == "__main__":
    main()
