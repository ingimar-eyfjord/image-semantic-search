#!/usr/bin/env python3
"""Fetch MORE royalty-free demo images from Wikimedia Commons, verify each with PIL.

Adapted from fetch_images.py. Adds new subjects only; never overwrites existing files.
"""
import io
import json
import os
import time
import urllib.parse
import urllib.request

from PIL import Image

OUT = "/Users/ingimareyfjord/Projects/simply-tv-challenge/data/images"
os.makedirs(OUT, exist_ok=True)

UA = "demo-image-fetcher/1.0 (https://ingimar.dk; ingimareys93@gmail.com)"

# Existing filenames that must NOT be collided with.
EXISTING = {
    "acoustic-guitar", "bicycle", "cat", "city-skyline-night", "coffee-cup",
    "dog", "elephant", "forest-path", "hot-air-balloon", "laptop-on-desk",
    "lighthouse", "pizza", "red-sports-car", "sailboat", "sandy-beach",
    "snowy-mountains", "stack-of-books", "sunflower", "sushi", "train",
    "violin", "waterfall",
}

# subject filename -> list of Commons search queries (tried in order)
SUBJECTS = {
    # FOOD (heavy)
    "hamburger": ["hamburger cheeseburger", "hamburger food", "burger sandwich"],
    "salad": ["green salad bowl", "vegetable salad plate", "salad food"],
    "ice-cream": ["ice cream cone", "ice cream scoop dessert", "ice cream"],
    "pasta": ["spaghetti pasta dish", "pasta italian food", "pasta plate"],
    "tacos": ["mexican tacos", "taco food plate", "tacos"],
    "chocolate-cake": ["chocolate cake slice", "chocolate cake dessert", "chocolate cake"],
    "sandwich": ["sandwich food", "club sandwich", "sandwich bread"],
    "ramen": ["ramen noodle soup", "ramen bowl japanese", "ramen"],
    "steak": ["grilled steak meat", "beef steak plate", "steak"],
    "pancakes": ["pancakes stack syrup", "pancakes breakfast", "pancakes"],
    "bread-loaf": ["bread loaf bakery", "loaf of bread", "bread"],
    "fruit-bowl": ["bowl of fruit", "fruit basket assortment", "fruit bowl"],
    # ANIMALS (heavy)
    "horse": ["horse portrait", "brown horse animal", "horse"],
    "lion": ["lion male portrait", "lion wildlife", "lion"],
    "penguin": ["penguin antarctica", "penguin bird", "penguin"],
    "owl": ["owl bird portrait", "owl wildlife", "owl"],
    "butterfly": ["butterfly insect colorful", "monarch butterfly", "butterfly"],
    "goldfish": ["goldfish aquarium", "goldfish fish", "goldfish"],
    "rabbit": ["rabbit bunny portrait", "rabbit animal", "rabbit"],
    "bear": ["brown bear wildlife", "grizzly bear", "bear animal"],
    # NATURE / SCENES
    "desert": ["sand desert dunes", "desert landscape", "desert"],
    "autumn-forest": ["autumn forest foliage", "fall forest trees", "autumn forest"],
    "river": ["river landscape water", "mountain river", "river"],
    "volcano": ["volcano eruption", "volcano mountain", "volcano"],
    "tropical-beach": ["tropical beach palm", "tropical island beach", "tropical beach"],
    "field-of-tulips": ["tulip field flowers", "field of tulips netherlands", "tulip field"],
    # OBJECTS
    "camera": ["camera dslr photography", "vintage camera", "camera"],
    "headphones": ["headphones audio", "over ear headphones", "headphones"],
    "wristwatch": ["wristwatch analog", "wrist watch close up", "wristwatch"],
    "telescope": ["telescope astronomy", "telescope instrument", "telescope"],
    "umbrella": ["umbrella open", "colorful umbrella", "umbrella"],
    # VEHICLES
    "motorcycle": ["motorcycle motorbike", "motorcycle parked", "motorcycle"],
    "airplane": ["airplane aircraft flying", "passenger airplane", "airplane"],
    "bus": ["city bus public transport", "double decker bus", "bus vehicle"],
    "helicopter": ["helicopter flying", "helicopter aircraft", "helicopter"],
}


def commons_candidates(query, limit=8):
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
        "gsrlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|mime|size",
        "iiurlwidth": "900",
        "format": "json",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    pages = data.get("query", {}).get("pages", {})
    out = []
    for p in pages.values():
        ii = p.get("imageinfo")
        if not ii:
            continue
        info = ii[0]
        if info.get("mime") != "image/jpeg":
            continue
        thumb = info.get("thumburl")
        if thumb:
            out.append(thumb)
    return out


def try_download(thumb_url, dest):
    req = urllib.request.Request(thumb_url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    if len(data) < 8192:
        return None, f"too small ({len(data)} bytes)"
    try:
        Image.open(io.BytesIO(data)).verify()
        im = Image.open(io.BytesIO(data))
        size = im.size
    except Exception as e:
        return None, f"PIL fail: {e}"
    with open(dest, "wb") as f:
        f.write(data)
    return size, None


def main():
    results = {}
    for name, queries in SUBJECTS.items():
        if name in EXISTING:
            print(f"SKIP {name}: collides with existing file, refusing")
            continue
        dest = os.path.join(OUT, f"{name}.jpg")
        if os.path.exists(dest) and os.path.getsize(dest) >= 8192:
            try:
                im = Image.open(dest)
                im.verify()
                results[name] = (Image.open(dest).size, "exists")
                print(f"SKIP {name}: already valid {results[name][0]}")
                continue
            except Exception:
                pass
        got = False
        for q in queries:
            try:
                cands = commons_candidates(q)
            except Exception as e:
                print(f"  query err '{q}': {e}")
                continue
            for url in cands:
                try:
                    size, err = try_download(url, dest)
                except Exception as e:
                    print(f"  dl err: {e} [{url[:80]}]")
                    continue
                if size:
                    results[name] = (size, url)
                    print(f"OK   {name}: {size} <- {url[:90]}")
                    got = True
                    break
                else:
                    print(f"  reject {name}: {err}")
            if got:
                break
            time.sleep(0.3)
        if not got:
            print(f"FAIL {name}: no valid image found")
    print("\n=== SUMMARY ===")
    print(f"valid new: {len(results)}/{len(SUBJECTS)}")
    return results


if __name__ == "__main__":
    main()
