import urllib.request
import re
import json
import sys
import unicodedata

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Designer paths on Fragrantica
designers = {
    "tom_ford": "Tom-Ford.html",
    "mfk": "Maison-Francis-Kurkdjian.html",
    "creed": "Creed.html",
    "kilian": "By-Kilian.html",
    "jo_malone": "Jo-Malone-London.html",
    "byredo": "Byredo.html",
    "le_labo": "Le-Labo.html",
    "ysl": "Yves-Saint-Laurent.html",
    "dior": "Dior.html",
    "chanel": "Chanel.html",
    "tiziana_terenzi": "Tiziana-Terenzi.html",
    "montale": "Montale.html",
    "mancera": "Mancera.html",
    "ex_nihilo": "Ex-Nihilo.html",
    "zarkoperfume": "Zarkoperfume.html"
}

scraped_brand_perfumes = {}

print("Step 1: Scraping all designer perfume catalogs...")
for brand_id, filename in designers.items():
    url = f"https://www.fragrantica.com/designers/{filename}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, timeout=8) as r:
            html = r.read().decode('utf-8', errors='ignore')
            cards = re.findall(r'/perfume/[^/]+/([a-zA-Z0-9\-]+)-(\d+)\.html', html)
            scraped_brand_perfumes[brand_id] = cards
            print(f"  {brand_id}: found {len(cards)} perfumes")
    except Exception as e:
        print(f"  Error scraping {brand_id}: {e}")

# Load our 90 perfumes
db = json.load(open("parfyme_bot/perfumes_data.json", encoding="utf-8"))
perfumes = db["perfumes"]

print("\nStep 2: Matching each of our 90 perfumes to real bottles...")

def strip_accents(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')

def clean_str(s):
    s = strip_accents(s)
    return re.sub(r'[^a-zA-Z0-9]', '', s.lower())

# Manual accurate overrides for special editions / subnames
MANUAL_OVERRIDES = {
    "mfk_baccarat_extrait": "46066",            # Baccarat Rouge 540 Extrait de Parfum
    "creed_millesime_imperial": "466",          # Millesime Imperial
    "creed_aventus_for_her": "38497",           # Aventus for Her
    "kilian_apple_brandy": "68579",             # Apple Brandy on the Rocks
    "jm_peony_blush": "18400",                  # Peony & Blush Suede
    "byredo_rose_of_no_mans": "31931",          # Rose of No Man's Land
    "ysl_y_edp": "50757",                       # Y Eau de Parfum
    "dior_sauvage_elixir": "68405",             # Sauvage Elixir
    "chanel_sycomore": "4688",                  # Sycomore
    "chanel_coromandel": "7145",                # Coromandel
    "terenzi_spirito_fiorentino": "53782",      # Spirito Fiorentino
    "montale_vanilla_cake": "48995",            # Vanilla Cake
    "mancera_amore_caffe": "87550",             # Amore Caffe
    "zarko_pink_molecule": "25424",             # Pink Molecule 090.09
    "zarko_molecule_234_38": "14490",           # Molecule 234.38
    "zarko_the_muse": "64157",                  # The Muse
    "zarko_purple_molecule": "58611",           # Purple Molecule 070.07
    "zarko_quantum_molecule": "68351",          # Quantum Molecule
    "zarko_inception": "25425",                 # Inception
}

matched = {}
unmatched = []

for pid, item in perfumes.items():
    b_id = item["brand_id"]
    p_name = item["name"]
    clean_p_name = clean_str(p_name)
    
    candidates = scraped_brand_perfumes.get(b_id, [])
    best_id = MANUAL_OVERRIDES.get(pid)
    
    # 1. Exact match on slug
    if not best_id:
        for slug, f_id in candidates:
            clean_slug = clean_str(slug)
            if clean_p_name == clean_slug:
                best_id = f_id
                break
            
    # 2. Substring / starts with
    if not best_id:
        for slug, f_id in candidates:
            clean_slug = clean_str(slug)
            if clean_p_name in clean_slug or clean_slug in clean_p_name:
                best_id = f_id
                break

    # 3. Token overlap match
    if not best_id:
        p_tokens = set(clean_str(t) for t in re.findall(r'[a-zA-Z0-9]+', strip_accents(p_name)))
        p_tokens = {t for t in p_tokens if len(t) > 2}
        max_overlap = 0
        for slug, f_id in candidates:
            s_tokens = set(clean_str(t) for t in slug.lower().split('-'))
            overlap = len(p_tokens.intersection(s_tokens))
            if overlap > max_overlap:
                max_overlap = overlap
                best_id = f_id

    if best_id:
        img_url = f"https://fimgs.net/mdimg/perfume/375x500.{best_id}.jpg"
        item["image_url"] = img_url
        matched[pid] = (p_name, best_id, img_url)
        print(f"  MATCH: {item['brand']} — {p_name} -> ID {best_id} ({img_url})")
    else:
        unmatched.append((pid, item['brand'], p_name))
        print(f"  UNMATCHED: {item['brand']} — {p_name}")

print(f"\n==========================================")
print(f"Total matched: {len(matched)} / {len(perfumes)}")
print(f"==========================================")

if unmatched:
    print("Unmatched items:", unmatched)

# Save back to perfumes_data.json
with open("parfyme_bot/perfumes_data.json", "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print("Saved updated perfumes_data.json successfully!")
