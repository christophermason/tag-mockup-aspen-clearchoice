#!/usr/bin/env python3
"""
TAG Mockup — Photo Generation Pipeline
======================================
Generates photography for the Aspen Dental & ClearChoice mockup using DALL-E 3
(via OpenAI) and Imagen 3 (via Google Generative AI). Saves into ./brand/photos/.

Run:
  python3 generate_photos.py            # generate all
  python3 generate_photos.py drchen     # generate just the dr-chen shot
  python3 generate_photos.py --list     # show available shots

Reads OPENAI_API_KEY and GOOGLE_AI_API_KEY from ~/business-command-center/.env
"""

import os
import sys
import json
import time
import base64
import pathlib
import argparse
import urllib.request
import urllib.parse
import urllib.error
import ssl
import concurrent.futures
from typing import Dict, Optional

HERE = pathlib.Path(__file__).parent.resolve()
PHOTOS_DIR = HERE / "brand" / "photos"
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

ENV_PATH = pathlib.Path.home() / "business-command-center" / ".env"


def load_env() -> Dict[str, str]:
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    env.update(os.environ)
    return env


# ─────────────────────────────────────────────────────────────
# Shot definitions — each maps to one image slot in the mockup
# ─────────────────────────────────────────────────────────────

SHOTS: Dict[str, Dict] = {
    "drpatel": {
        "model": "gpt-image-1",
        "size": "1536x1024",
        "quality": "hd",
        "prompt": (
            "Documentary editorial portrait of a mid-40s Indian-American dentist "
            "named Dr. Patel, wearing modern dental scrubs in pale blue. He is "
            "smiling warmly while gesturing toward an out-of-focus dental chair. "
            "Natural daylight from a large window left-frame, warm and gentle. "
            "Modern dental office with warm-wood accents — NOT clinical white. "
            "Subject sharp focus, shallow depth of field, background gently blurred. "
            "Editorial portrait feel, like a profile in The New York Times Style "
            "section. Shot on Leica Q3, 28mm, f/2.8. Real skin, no airbrush. "
            "Realistic. No text, no logos."
        ),
        "filename": "A2_drpatel.jpg",
    },
    "drchen": {
        "model": "gpt-image-1",
        "size": "1024x1024",
        "quality": "hd",
        "prompt": (
            "Editorial portrait of a 48-year-old Asian-American oral surgeon "
            "(composite character, not a real person), short black hair with grey "
            "at temples, wearing dark navy medical scrubs (NOT a white coat). "
            "Photographed in a softly-lit consultation room — warm gold and "
            "shadow, like a Wes Anderson kitchen interior. He is mid-explanation, "
            "hands gesturing softly, looking just past the camera. Eyes warm and "
            "steady. Background intentionally dark navy. Single warm tungsten "
            "light source above and left. Reference: Annie Leibovitz portraits "
            "of working professionals. Realistic, real skin, no airbrush. "
            "No text, no logos."
        ),
        "filename": "B2_drchen.jpg",
    },
    "maria": {
        "model": "gpt-image-1",
        "size": "1024x1024",
        "quality": "hd",
        "prompt": (
            "Candid documentary photograph of a 52-year-old Latina woman named "
            "Maria, laughing genuinely — eyes crinkled, mouth open. NOT a clinical "
            "after-photo. She is at a backyard dinner table, evening golden-hour "
            "light slanting through nearby trees. Plates and a glass of wine "
            "softly visible at frame edge. The smile is NOT the focal subject — "
            "the life around her is. Shot at f/2.8, eye-level, medium-format "
            "documentary style. The viewer should feel they walked up on a "
            "private moment. Real skin, no airbrush, no makeup-heavy styling. "
            "No text, no logos."
        ),
        "filename": "B3_maria.jpg",
    },
    "intake_wallet": {
        "model": "gpt-image-1",
        "size": "1024x1024",
        "quality": "standard",
        "prompt": (
            "Still-life photograph: a worn leather wallet on a wooden countertop, "
            "an insurance card peeking out from a pocket, a driver's license "
            "resting next to it. Warm morning light from window left, slight "
            "shadow play. Real, lived-in objects — not styled. Kinfolk magazine "
            "aesthetic. Tight composition, top-down angle. Realistic. "
            "No text on the cards (anonymized), no logos."
        ),
        "filename": "A3a_intake.jpg",
    },
    "after_exam": {
        "model": "gpt-image-1",
        "size": "1024x1024",
        "quality": "standard",
        "prompt": (
            "Close-up still-life of two hands holding a clear glass of water, "
            "softly out of focus. Cool morning light, neutral palette. Kinfolk "
            "magazine aesthetic. The hands are mid-tone skin, age 30s-40s, "
            "natural and lived-in. Realistic. No text, no logos."
        ),
        "filename": "A3b_after_exam.jpg",
    },
    "applewatch": {
        "model": "gpt-image-1",
        "size": "1024x1024",
        "quality": "hd",
        "prompt": (
            "Close-up of a 52-year-old woman's wrist wearing an Apple Watch in "
            "stainless steel with a milanese-loop band. Photographed at 6:30 AM "
            "in soft pre-dawn window light. Her sleeve is a soft cream knit. "
            "The hand is at rest on a wooden bedside table — a glass of water "
            "and a book visible at frame edge. Mood: a private moment of waking. "
            "Macro lifestyle editorial — reference: Apple's macro iPhone campaign. "
            "Realistic skin, natural light, shallow depth of field. No text "
            "visible on the watch screen (will be composited later). No logos."
        ),
        "filename": "B6_applewatch.jpg",
    },
    "cc_hero": {
        "model": "gpt-image-1",
        "size": "1536x1024",
        "quality": "hd",
        "prompt": (
            "A 52-year-old Latina woman's hands (no manicure, no wedding ring, "
            "soft natural skin) holding an iPhone in her lap. The screen is "
            "intentionally blank/black (will be composited later). Setting: "
            "she is sitting on the edge of a bed at evening, warm side-light "
            "from a lamp out of frame to the right. Cream sheets crumpled at "
            "bottom of frame. Her face is intentionally out of frame — only "
            "hands and phone visible. Intimate, premium, editorial. Hasselblad "
            "medium format aesthetic, f/2.8. NOT a healthcare ad — closer to "
            "an Apple product film. Realistic. No text, no logos."
        ),
        "filename": "B1_cc_hero.jpg",
    },
    "patient_james": {
        "model": "gpt-image-1",
        "size": "1024x1024",
        "quality": "standard",
        "prompt": (
            "Close-up documentary photo of a 60-year-old white man's hands "
            "holding a ceramic coffee mug, slight smile visible at upper frame "
            "edge. Morning light, on a wooden porch. Real skin, weathered "
            "natural hands. Kinfolk magazine aesthetic. No text, no logos."
        ),
        "filename": "B4b_james.jpg",
    },
    "patient_anne": {
        "model": "gpt-image-1",
        "size": "1024x1024",
        "quality": "standard",
        "prompt": (
            "Profile shot of a 58-year-old Black woman speaking to someone "
            "off-camera, soft afternoon light, restaurant or living-room "
            "setting. She is mid-laugh, leaning forward. Natural skin, real "
            "person — NOT a stock model. Documentary editorial. No text, "
            "no logos."
        ),
        "filename": "B4c_anne.jpg",
    },
}


# ─────────────────────────────────────────────────────────────
# OpenAI DALL-E 3 generator
# ─────────────────────────────────────────────────────────────

def call_openai_image(prompt: str, size: str, quality: str, model: str, api_key: str) -> Optional[bytes]:
    """Call OpenAI Images API. Returns raw image bytes."""
    url = "https://api.openai.com/v1/images/generations"
    # gpt-image-1 always returns base64. dall-e-3 returns URL by default.
    payload = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
    }
    if model == "dall-e-3":
        payload["quality"] = quality  # "standard" | "hd"
    else:
        # gpt-image-1 uses different quality vocab
        payload["quality"] = {"hd": "high", "standard": "medium"}.get(quality, "medium")
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode())
        item = data["data"][0]
        if "b64_json" in item:
            return base64.b64decode(item["b64_json"])
        if "url" in item:
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(item["url"], timeout=60, context=ctx) as r:
                return r.read()
        return None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  ✗ OpenAI HTTP {e.code} ({model}): {body[:500]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  ✗ OpenAI error ({model}): {e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────
# Worker — generate one shot
# ─────────────────────────────────────────────────────────────

def generate_one(name: str, shot: Dict, env: Dict[str, str]) -> Dict:
    out_path = PHOTOS_DIR / shot["filename"]
    if out_path.exists() and out_path.stat().st_size > 50_000:
        return {"name": name, "status": "skipped", "path": str(out_path), "reason": "exists"}

    started = time.time()
    model = shot["model"]
    print(f"  → {name} ({shot['filename']}) — generating via {model}...")
    img_bytes = call_openai_image(
        prompt=shot["prompt"],
        size=shot["size"],
        quality=shot.get("quality", "standard"),
        model=model,
        api_key=env.get("OPENAI_API_KEY", ""),
    )
    if not img_bytes:
        return {"name": name, "status": "failed", "reason": "API"}
    out_path.write_bytes(img_bytes)
    dur = time.time() - started
    size_kb = out_path.stat().st_size / 1024
    print(f"  ✓ {name} → {out_path.name}  ({size_kb:.0f} KB · {dur:.1f}s)")
    return {"name": name, "status": "ok", "path": str(out_path), "duration": dur}


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser()
    p.add_argument("shots", nargs="*", help="shot names (default: all)")
    p.add_argument("--list", action="store_true", help="list available shots")
    p.add_argument("--parallel", type=int, default=4, help="concurrency (default 4)")
    p.add_argument("--force", action="store_true", help="re-generate even if file exists")
    args = p.parse_args()

    if args.list:
        for k, v in SHOTS.items():
            print(f"  {k:18}  {v['filename']:28}  {v['size']:>10}  {v.get('quality','standard')}")
        return

    env = load_env()
    if not env.get("OPENAI_API_KEY"):
        print("✗ OPENAI_API_KEY missing — check ~/business-command-center/.env", file=sys.stderr)
        sys.exit(1)

    targets = args.shots if args.shots else list(SHOTS.keys())
    invalid = [t for t in targets if t not in SHOTS]
    if invalid:
        print(f"✗ unknown shots: {invalid}", file=sys.stderr)
        print(f"  available: {list(SHOTS.keys())}", file=sys.stderr)
        sys.exit(1)

    if args.force:
        for t in targets:
            f = PHOTOS_DIR / SHOTS[t]["filename"]
            if f.exists():
                f.unlink()

    print(f"\n▶ Generating {len(targets)} shot(s) with concurrency={args.parallel}")
    print(f"  Output: {PHOTOS_DIR}")
    print()

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as ex:
        futures = {ex.submit(generate_one, name, SHOTS[name], env): name for name in targets}
        for fut in concurrent.futures.as_completed(futures):
            results.append(fut.result())

    print()
    ok = sum(1 for r in results if r["status"] == "ok")
    sk = sum(1 for r in results if r["status"] == "skipped")
    fa = sum(1 for r in results if r["status"] == "failed")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  ✓ {ok} generated   ⊝ {sk} skipped   ✗ {fa} failed")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    manifest = PHOTOS_DIR / "manifest.json"
    manifest.write_text(json.dumps({
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "results": results,
    }, indent=2))


if __name__ == "__main__":
    main()
