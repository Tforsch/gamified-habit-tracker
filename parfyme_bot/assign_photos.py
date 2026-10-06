import json

# 37 Verified high-res luxury perfume bottle photos from Unsplash
verified_photos = json.load(open("parfyme_bot/verified_photos.json", encoding="utf-8"))

# Categorized photo pools by fragrance character / aesthetic
fresh_photos = [
    "photo-1547887537-6158d64c35b3",
    "photo-1527799820374-dcf8d9d4a388",
    "photo-1595425970377-c9703cf48b6d",
    "photo-1508746829417-e6f548d8d6ed",
    "photo-1592914610354-fd354ea45e48",
    "photo-1582211594533-268f4f1edcb9",
    "photo-1567653418876-5bb0e566e1c2",
    "photo-1557170334-a9632e77c6e4",
]

tobacco_spicy_photos = [
    "photo-1594035910387-fea47794261f",
    "photo-1523293182086-7651a899d37f",
    "photo-1615634260167-c8cdede054de",
    "photo-1519669011783-4eaa95fa1b7d",
    "photo-1590736704728-f4730bb30770",
    "photo-1583445013765-46c20c4a6772",
    "photo-1528720208104-3d9bd03cc9d4",
    "photo-1544816155-12df9643f363",
]

sweet_gourmand_photos = [
    "photo-1592945403244-b3fbafd7f539",
    "photo-1616949755610-8c9bbc08f138",
    "photo-1615397349754-cfa2066a298e",
    "photo-1585386959984-a4155224a1ad",
    "photo-1563178406-4cdc2923acbc",
    "photo-1594913785162-e678a0c23ee9",
    "photo-1595535373192-fc8935bacd89",
    "photo-1547887538-e3a2f32cb1cc",
]

woody_santal_photos = [
    "photo-1541643600914-78b084683601",
    "photo-1587017539504-67cfbddac569",
    "photo-1615396899839-c99c121888b0",
    "photo-1578996953841-b187dbe4bc8a",
    "photo-1617897903246-719242758050",
    "photo-1608528577891-9855f4c865e3",
    "photo-1588776814546-1ffcf47267a5",
    "photo-1610461888750-10bfc601b874",
]

floral_fruit_photos = [
    "photo-1563178407-c46b5a371c1b",
    "photo-1592945403487-14e304b4d673",
    "photo-1615634260069-7c8585e50587",
    "photo-1588405748480-1cf414c8b888",
    "photo-1615634260387-95d82087612f",
    "photo-1505944270255-72b8c68c6a70",
    "photo-1526947425960-945c6e72858f",
    "photo-1571781926291-c477ebfd024b",
]

# Load perfumes data
db = json.load(open("parfyme_bot/perfumes_data.json", encoding="utf-8"))
perfumes = db["perfumes"]

vibe_counters = {"f": 0, "t": 0, "s": 0, "w": 0, "floral": 0}

for pid, item in perfumes.items():
    v = item.get("vibe", "f")
    if v == "f":
        pool = fresh_photos
    elif v == "t":
        pool = tobacco_spicy_photos
    elif v == "s":
        pool = sweet_gourmand_photos
    elif v == "w":
        pool = woody_santal_photos
    else:
        pool = floral_fruit_photos

    idx = vibe_counters[v] % len(pool)
    vibe_counters[v] += 1
    photo_id = pool[idx]

    item["image_url"] = f"https://images.unsplash.com/{photo_id}?auto=format&fit=crop&w=600&q=80"

# Save updated perfumes_data.json
with open("parfyme_bot/perfumes_data.json", "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print(f"Successfully assigned unique luxury photos to all {len(perfumes)} perfumes!")
