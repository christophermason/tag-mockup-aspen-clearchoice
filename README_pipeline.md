# TAG Mockup — Photo Generation Pipeline

Two paths to generate photography for the Aspen Dental & ClearChoice mockup:
**(A) immediate Python script** and **(B) n8n visual workflow**.

Both call OpenAI's `gpt-image-1` (the successor to DALL-E 3, ~$0.04–0.19 per image depending on size/quality).

---

## A · Python script (immediate, already run)

**Location:** `generate_photos.py`
**Status:** ✅ Ran in this session. 7 images live in `brand/photos/` (~13MB total).

```bash
cd /Users/chrismason/Documents/TAG/Mockups/aspen_clearchoice

# List available shots
python3 generate_photos.py --list

# Generate everything
python3 generate_photos.py

# Generate one
python3 generate_photos.py drchen

# Regenerate (delete existing)
python3 generate_photos.py drchen --force
```

Reads `OPENAI_API_KEY` from `~/business-command-center/.env`. Parallelizes up to 6 calls.
Generated photos:
- `A2_drpatel.jpg` — Aspen comp-exam video card (Dr. Patel)
- `A3a_intake.jpg` — Aspen "What to bring" card (wallet still life)
- `A3b_after_exam.jpg` — Aspen "After your exam" card (hands + water)
- `B1_cc_hero.jpg` — ClearChoice documentary hero (hands + iPhone)
- `B2_drchen.jpg` — CC Dreamstream featured (Dr. Chen portrait)
- `B3_maria.jpg` — Maria patient story (golden-hour candid)
- `B6_applewatch.jpg` — CC Apple Watch wrist hero

---

## B · n8n workflow (visual, ongoing pipeline)

**Location:** `n8n_workflow.json`
**Status:** ✅ n8n running at http://localhost:5678

### Import

1. Open http://localhost:5678 in Chrome
2. Click **Workflows** → top-right **⋯** menu → **Import from File**
3. Pick `/Users/chrismason/Documents/TAG/Mockups/aspen_clearchoice/n8n_workflow.json`

### Add OpenAI credential (one-time)

1. In n8n: **Settings** (left nav) → **Credentials** → **+ Add credential**
2. Pick **OpenAI account**
3. Paste your `OPENAI_API_KEY` (same one in `~/business-command-center/.env`)
4. Save

### Run

1. Open the imported workflow
2. Click **▶ Test workflow** (top-right)
3. ~3–4 minutes — images land in `brand/photos/`

### Workflow nodes

```
Trigger ▶
   │
Define Shots          ← JSON array of 9 shots (prompt + size + filename)
   │
Split Shots           ← one item per shot
   │
Batch of 4 (parallel) ← 4 concurrent requests
   │
OpenAI · gpt-image-1  ← POST /v1/images/generations
   │
Base64 → Binary       ← decode the b64_json field
   │
Write to Disk         ← /brand/photos/{filename}
   │
Log Result            ← timestamped manifest entry
   │
   └─→ back to Batch (until all done)
```

### Modify prompts

Edit the **Define Shots** node — it's a single JSON array. Add/remove/edit shots, rerun.

---

## Cost / Time

| Quality | Size       | $ / image | Time / image |
|---------|------------|-----------|--------------|
| medium  | 1024×1024  | ~$0.04    | ~20s         |
| high    | 1024×1024  | ~$0.07    | ~35s         |
| high    | 1536×1024  | ~$0.12    | ~50s         |

Full 9-shot run ≈ **$0.85** and **~4 minutes** with parallelism.

---

## Wire generated photos into the mockup

The HTML already references the file paths — once a JPG lands in `brand/photos/X.jpg`, hard-reload Chrome (`Cmd+Shift+R`) and it appears.

| HTML selector                                | Photo file              |
|---------------------------------------------- |-------------------------|
| `.aspen-content-feed .feed-hero`              | `A2_drpatel.jpg`        |
| `.aspen-content-feed .fr-card.warm .fc-img`   | `A3a_intake.jpg`        |
| `.aspen-content-feed .fr-card.blue .fc-img`   | `A3b_after_exam.jpg`    |
| `.cc-dream .featured .img-wrap`               | `B2_drchen.jpg`         |
| `.ipad-dream .ipd-img`                        | `B2_drchen.jpg`         |
| `.cc-dream .saved .saved-row .timg`           | `B3_maria.jpg`          |
| `.cc-story .story-img`                        | `B3_maria.jpg`          |
| `.ipad-dream .ipd-story.s1 .ipd-story-img`    | `B3_maria.jpg`          |

`B1_cc_hero.jpg` and `B6_applewatch.jpg` are bonus assets — drop them into new hero blocks at the top of the CC chapter (HTML edits TBD).

---

## Generating new shots

Add a new entry to either:
- `generate_photos.py` `SHOTS` dict, OR
- the n8n workflow's **Define Shots** JSON

Follow the prompt style in `photo_prompts.md` — that's the canonical style guide (documentary, one light source, real skin, no "before/after" framing).
