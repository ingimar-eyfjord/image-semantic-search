#!/usr/bin/env python3
"""Fetch royalty-free demo images from Wikimedia Commons, verify each with PIL."""
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

# subject filename -> list of Commons search queries (tried in order)
SUBJECTS = {
    "dog": ["golden retriever dog", "labrador dog portrait", "dog"],
    "cat": ["domestic cat portrait", "tabby cat", "cat"],
    "sandy-beach": ["sandy tropical beach", "beach sand sea", "beach"],
    "snowy-mountains": ["snow covered mountains", "snowy mountain peak", "alps snow mountain"],
    "pizza": ["margherita pizza", "pizza food", "pizza"],
    "coffee-cup": ["cup of coffee latte", "coffee cup", "espresso cup"],
    "bicycle": ["bicycle bike", "bicycle parked", "classic bicycle"],
    "red-sports-car": ["red sports car ferrari", "red sports car", "red car automobile"],
    "sunflower": ["sunflower flower", "sunflower field", "sunflower"],
    "laptop-on-desk": ["laptop computer on desk", "laptop notebook computer", "laptop"],
    "city-skyline-night": ["city skyline at night", "city night skyline lights", "skyline night"],
    "forest-path": ["forest path trail", "forest trail woods", "forest path"],
    "sailboat": ["sailboat on water", "sailing boat sea", "sailboat"],
    "acoustic-guitar": ["acoustic guitar", "guitar acoustic instrument", "classical guitar"],
    "stack-of-books": ["stack of books", "pile of books", "books stack"],
    "waterfall": ["waterfall", "waterfall nature", "large waterfall"],
    "hot-air-balloon": ["hot air balloon", "hot air balloon sky", "balloon flight"],
    "sushi": ["sushi plate", "sushi nigiri", "sushi"],
    "train": ["passenger train locomotive", "train railway", "train"],
    "lighthouse": ["lighthouse coast", "lighthouse sea", "lighthouse"],
    "elephant": ["african elephant", "elephant wildlife", "elephant"],
    "violin": ["violin instrument", "violin", "violin music"],
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
    # verify
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
    print(f"valid: {len(results)}/{len(SUBJECTS)}")
    return results


if __name__ == "__main__":
    main()
