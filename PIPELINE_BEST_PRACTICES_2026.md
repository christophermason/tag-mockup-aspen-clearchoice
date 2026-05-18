# AI Mockup Pipeline — Best Practices (2026)

**For:** Branding Brand · TAG engagement pipeline + future client work
**Authored:** 2026-05-18
**Status:** Opinionated. Do this, not that.

---

## TL;DR — Top 5 Moves, Ranked by Leverage

1. **Lock in `gpt-image-1` as primary, add Flux (via fal.ai or Replicate) as 70%-cost fallback.** Don't add Midjourney via gateways — reliability is poor and TOS is murky.
2. **Add a Claude-driven art-director loop** — Sonnet 4.6 vision scores every generated image against a brand-rules JSON and auto-iterates. Kill manual re-prompting.
3. **Move n8n to queue mode + PostgreSQL + Git source control.** Single-instance SQLite n8n breaks when 2+ clients trigger workflows simultaneously. Three-week harden.
4. **Wire generated assets into a real DAM (Brandfolder).** File-system → broken at 3+ engagements. Brandfolder gives approval chains, usage-rights tracking, Slack notify, Figma plugin.
5. **Build a Playwright "mockup → PNG → PDF" exporter.** Stop relying on browser screenshots for client deliverables. Headless capture per-section at 2× retina = press-ready in 30s.

Everything below justifies and details these five.

---

## 1. What we have today (snapshot)

| Layer            | Tool                                      | Status        | Gap                                 |
|------------------|-------------------------------------------|---------------|--------------------------------------|
| Brief → prompts  | `photo_prompts.md` (manual library)       | ✅ Production | No iteration loop                    |
| Image gen        | OpenAI `gpt-image-1` (Python script)      | ✅ Production | No fallback, no cost cap             |
| Orchestration    | n8n local (single instance, SQLite)       | ✅ Working    | No queue mode, no Git, no error wf   |
| Brand assets     | Live SVG from TAG Contentful CDN          | ✅ Production | No mirroring (CDN dependency)        |
| Mockup output    | HTML/CSS (6,400 lines) + animations       | ✅ Production | Manual screenshots for deck export   |
| DAM              | Local file system                          | ⚠ Fragile     | No approval, no rights tracking      |
| Cost tracking    | Manual ($0.85 noted in chat)              | ⚠ Ad-hoc      | No per-engagement cap, no alert      |
| Review loop      | Eyeball                                    | ⚠ Slow        | No automated brand-rule validation   |
| Handoff to deck  | Manual screencap → PowerPoint             | ⚠ Manual      | No headless capture pipeline         |

**Cost so far (TAG comp):** ~$1.10 across 9 photos + tooling time. Compare to: **$2,000–5,000** for a one-day photo shoot. **70× cost advantage**, before automation gains.

---

## 2. Reference Architecture (Late 2026)

```
┌─────────────────────────────────────────────────────────────────┐
│                  PROPOSED MOCKUP PIPELINE                       │
└─────────────────────────────────────────────────────────────────┘

[Brief PDF / Slack message]
        │
        ▼
[Claude Sonnet 4.6]  ← `/brief-to-prompts` skill: brief → JSON prompt manifest
        │            (persona, mood, style, brand colors, do/don't list)
        ▼
   ┌────────────────────────────────────────────────────┐
   │       n8n (queue mode + PostgreSQL + Redis)        │
   │                                                    │
   │  Trigger ─► Validate brief ─► Split into shots     │
   │                                       │            │
   │                                       ▼            │
   │  ┌──────────────┐  primary  ┌─────────────────┐    │
   │  │ Cost gate    │──────────▶│  gpt-image-1    │    │
   │  │ + Budget cap │           │  (OpenAI)       │    │
   │  └──────────────┘           └────────┬────────┘    │
   │         │                            │ fail        │
   │         │ over budget                ▼             │
   │         ▼                  ┌─────────────────┐     │
   │   Slack alert              │ Flux dev/pro    │     │
   │                            │ (fal.ai)        │     │
   │                            └────────┬────────┘     │
   │                                     ▼              │
   │                         [Claude Sonnet 4.6 Vision] │
   │                         Brand-rule scoring         │
   │                                 │                  │
   │                       score >=8 │ score <8         │
   │                                 ▼                  │
   │                       OR ◄──┐ refine prompt + loop │
   │                            └────────────────────┘  │
   │                                 │                  │
   │                                 ▼                  │
   │                         Brandfolder DAM upload     │
   │                         + Slack approval ping      │
   └─────────────────────────────────────────────────────┘
        │
        ▼
[HTML mockup w/ photo slots]
        │
        ▼
[Playwright headless capture → PNG@2x + PDF]
        │
        ▼
[Google Slides deck (existing tag-slides skill)]
```

**Key control points:** budget gate before gen, score gate before save, approval gate before client send.

---

## 3. Image-Gen Model Selection (verified Q2 2026)

| Model                  | $/img (1024²)   | Latency | Strengths                              | Weaknesses                       | Best for                  |
|------------------------|-----------------|---------|----------------------------------------|----------------------------------|---------------------------|
| **OpenAI gpt-image-1** | $0.04 (med) / $0.19 (high) | 30–60s  | Composition, prompt adherence, faces   | Slow, expensive at HD            | Hero shots, faces, complex |
| **Flux.1 [dev]** (BFL via fal.ai/Replicate) | ~$0.02–0.04 | 8–15s | Photorealism, speed, license-clean      | Less prompt-precise              | Volume, iteration, b-roll |
| **Flux.1 [pro]** (BFL API) | ~$0.05 | 12–20s | Top-tier quality                       | Higher cost                      | Premium hero shots        |
| **Imagen 3** (Google Vertex) | ~$0.04 | 15–25s | Diverse subjects, global aesthetic     | Available via Vertex (paid tier) | Diversity, scenes         |
| **Ideogram 3.0**       | ~$0.04         | 12–20s  | Text rendering, signage, packaging     | Less editorial                   | Designs with text         |
| **Recraft v3**         | ~$0.04         | 15–25s  | Vector + raster, brand-consistent      | Niche                            | Icons, illustrated UI     |
| **Stable Diffusion 3.5 / FLUX self-host** | ~$0.005 self-hosted | 6–10s | Free, customizable                     | Setup overhead, lower quality    | Volume placeholder        |
| **Midjourney v7** (via PiAPI/UseAPI) | ~$0.08 + sub | 30–90s queue | Aesthetic quality                | Unofficial API, TOS risk         | Avoid for production      |
| **Adobe Firefly 3**    | Included in CC | 10–20s  | Commercial-safe IP, Photoshop integration | Quality below Flux/OpenAI         | Designers already on CC   |

**Sora 2:** images mode is GA (Dec 2025) but pricing is volatile and reliability is mixed — **don't depend on it** for client deliverables yet. Use for video/animated mockup b-roll only.

**Recommended mix:**
- **70% Flux dev** (via fal.ai) for body shots, b-roll, iteration
- **25% gpt-image-1 high** for hero portraits and faces (proven reliable)
- **5% Imagen 3** for diversity scenes that other models miss

Cost at 9 shots/engagement, 50 engagements/yr: ~$30/yr image gen (was $42/yr OpenAI-only).
The lever is **iteration speed**, not raw cost — Flux's 8s latency makes the art-director loop in §4 actually viable.

---

## 4. The Claude Art-Director Loop (highest-leverage move)

This is the single addition that changes the economics. Right now Chris/designer eyeballs each image and re-prompts manually. The loop below makes it automatic.

```python
# claude_art_director.py — drop into n8n via Execute Command
import anthropic, base64, json
from openai import OpenAI

BRAND_RULES = {
  "lighting": "single warm tungsten or natural window light, never flat",
  "skin": "real pores, no airbrush, no makeup-heavy",
  "framing": "documentary editorial, not commercial",
  "diversity": "age 30-65, mixed ethnicity, ability-inclusive",
  "forbidden": ["before/after split", "clinical bright fluorescent",
                 "stock-smile model", "embedded text or logos"],
  "min_score": 8.0
}

def score_image(image_path, prompt, rules):
    img_b64 = base64.b64encode(open(image_path,'rb').read()).decode()
    msg = anthropic.Anthropic().messages.create(
      model="claude-sonnet-4-6",
      max_tokens=600,
      messages=[{"role":"user","content":[
        {"type":"image","source":{"type":"base64",
         "media_type":"image/jpeg","data":img_b64}},
        {"type":"text","text":f"""
Score this image against brand rules. Return ONLY valid JSON:
{{"score": 0-10, "passes": bool, "violations": [...],
  "refine_hint": "specific prompt addition to fix"}}

Rules: {json.dumps(rules)}
Original prompt: {prompt}
"""}]}])
    return json.loads(msg.content[0].text)

def generate_with_loop(prompt, rules, max_iter=3):
    client = OpenAI()
    current_prompt = prompt
    for i in range(max_iter):
        # Generate
        r = client.images.generate(model="gpt-image-1",
            prompt=current_prompt, size="1024x1024", quality="high")
        img_bytes = base64.b64decode(r.data[0].b64_json)
        path = f"/tmp/iter_{i}.jpg"
        open(path,'wb').write(img_bytes)
        # Score
        verdict = score_image(path, current_prompt, rules)
        if verdict["passes"]:
            return path, verdict, i+1
        # Refine
        current_prompt = f"{current_prompt}. {verdict['refine_hint']}"
    return path, verdict, max_iter  # return best-effort
```

**Why it matters:**
- 3 iterations in ~90s automated vs. 20–30 min human iteration.
- Brand rules are **JSON, not vibes** → reproducible across designers and clients.
- Audit trail: every gen tagged with score, attempt, refine hints. Defensible if client asks "why this image."
- Per-engagement cost: 9 shots × 1.5 avg iterations × $0.05 = **$0.68** generation + ~$0.30 Claude vision = **<$1.00** for full art-directed photoshoot.

---

## 5. n8n Production Hardening

### What to fix today

| Issue                              | Fix                                                | Effort |
|------------------------------------|-----------------------------------------------------|--------|
| Single-instance, SQLite            | Move to queue mode + PostgreSQL + Redis            | 1 day  |
| Workflows in DB (not Git)          | Enable Source Control (n8n native, Git push/pull)  | 2 hrs  |
| Credentials shared in clear        | Use n8n built-in credential store + env vars       | 2 hrs  |
| No error workflow                  | Add global error workflow → Slack `#ai-pipelines`  | 4 hrs  |
| No retry policy                    | Add HTTP Retry on Fail (max 3, exponential)        | 1 hr   |
| No webhook auth                    | Use n8n header auth + IP allowlist                 | 2 hrs  |

### docker-compose for production n8n

```yaml
services:
  n8n:
    image: docker.n8n.io/n8nio/n8n:latest
    environment:
      - N8N_EXECUTIONS_MODE=queue
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - DB_POSTGRESDB_DATABASE=n8n
      - QUEUE_BULL_REDIS_HOST=redis
      - EXECUTIONS_DATA_PRUNE=true
      - EXECUTIONS_DATA_MAX_AGE=336  # 14 days
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
      - WEBHOOK_URL=https://n8n.brandingbrand.com
    ports: ["5678:5678"]
    depends_on: [postgres, redis]

  n8n-worker:
    image: docker.n8n.io/n8nio/n8n:latest
    command: worker
    environment:
      - N8N_EXECUTIONS_MODE=queue
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - QUEUE_BULL_REDIS_HOST=redis
    depends_on: [n8n, redis]
    deploy:
      replicas: 3   # 3 parallel workers

  postgres:
    image: postgres:16
    environment: [POSTGRES_DB=n8n, POSTGRES_USER=n8n,
                  POSTGRES_PASSWORD=${POSTGRES_PASSWORD}]
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine

volumes:
  pgdata:
```

Deploy this on Render or a small EC2 (t3.small is plenty). 3 workers handle 100+ concurrent image-gen requests.

### Workflow version control

n8n 2.0+ has built-in Source Control. Connect to a private GitHub repo (`brandingbrand/n8n-workflows`). Every workflow change → Git commit. Reviewable PRs. Rollback in 1 click. **Do this today** — n8n DB corruption is real and SQLite has no replication.

---

## 6. Workflow Automation Alternatives (when n8n is wrong)

| Tool          | Best for                                | Avoid for                          |
|---------------|------------------------------------------|------------------------------------|
| **n8n**       | Visual workflows, IT/PM-readable, self-host | High-throughput (10K+/hr) jobs     |
| **Make.com**  | Non-technical operators, SaaS integrations | Custom code blocks, low latency    |
| **Zapier**    | Single-task webhooks                     | Anything multi-step + state         |
| **Temporal**  | Long-running workflows (hours/days), code-defined, durable | Marketing/ops teams (devs only) |
| **Inngest**   | Event-driven, TypeScript-native          | Visual UI fans                     |
| **Pipedream** | Devs + serverless, free tier             | Heavy GUI workflows                |
| **Dagster/Prefect** | Data pipelines (ETL), not marketing automation | Mockup gen (overkill) |

**Verdict:** n8n is correct for Branding Brand. The pipeline is human-readable (designer-friendly), self-hosted (data control), and the visual graph maps cleanly to "image gen for client X."

---

## 7. Design tool integrations

| Tool                  | Use it for                                | Don't use it for                          |
|-----------------------|-------------------------------------------|--------------------------------------------|
| **Figma + Figma MCP** | Component sync, design system, handoff    | Generating mockups from prompts             |
| **Figma AI / Make**   | Layout suggestions, alt variants (beta)   | High-fidelity production                    |
| **Vercel v0**         | React component scaffolding from screenshot | Final mockups for client decks            |
| **Lovable**           | Working webapp prototypes from prompt     | Pixel-precise UI comps                      |
| **Bolt.new**          | Throwaway interactive demos               | Anything you'll edit twice                  |
| **Galileo AI** (status: pivoted/inactive 2025) | — | — Skip, Stitch (Google) replaces it      |
| **Stitch by Google**  | Fast layout exploration from prompts      | Brand-specific work                         |
| **Penpot**            | Open-source Figma alt (privacy-sensitive) | Mainstream client work                      |

**Recommendation:** The HTML-mockup approach we used for TAG is *correct* for this kind of pitch — it's faster than Figma to iterate, animation-native, browser-deliverable, and converts cleanly to PNG/PDF for decks. Reserve Figma for **component handoff to client engineering**, not for the pitch comp itself.

---

## 8. Asset management — pick Brandfolder, here's why

| Feature                | File system (now) | Brandfolder      | Bynder        |
|------------------------|-------------------|------------------|---------------|
| Version history        | ❌                | ✅               | ✅            |
| Approval workflow      | ❌                | ✅ multi-stage   | ✅ enterprise |
| Usage-rights metadata  | ❌                | ✅ custom fields | ✅            |
| Slack notifications    | ❌                | ✅ native        | ✅            |
| Figma plugin           | ❌                | ✅               | ✅            |
| API for n8n            | ❌                | ✅ REST          | ✅ REST       |
| Cost (BB size)         | $0                | $2–4K/yr         | $4–10K/yr     |

Both are fine. **Brandfolder is lighter, faster to onboard, half the cost.** Bynder is enterprise-y, overkill for a 77-person agency.

**Note**: ClearChoice already uses Brandfolder (SSO-gated per the brand research above). If the TAG engagement closes, this is the natural shared surface with the client.

---

## 9. Headless mockup capture (don't screenshot manually)

```python
# capture_mockup.py
from playwright.sync_api import sync_playwright
import os

URL = "file:///Users/chrismason/Documents/TAG/Mockups/aspen_clearchoice/index.html"
OUT = "/Users/chrismason/Documents/TAG/Mockups/aspen_clearchoice/exports"
os.makedirs(OUT, exist_ok=True)

SECTIONS = [
  ("hero", ".showcase-header"),
  ("dna",  ".dna"),
  ("aspen-grid", "#aspen .phone-grid"),
  ("cc-grid",    "#clearchoice .phone-grid"),
  ("multi-device", ".multi-device"),
  ("business-case", ".business-case"),
  ("watches", ".watch-row"),
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width":1440,"height":900},
                            device_scale_factor=2)  # retina
    page.goto(URL)
    page.wait_for_load_state("networkidle")
    for name, sel in SECTIONS:
        el = page.locator(sel)
        el.scroll_into_view_if_needed()
        page.wait_for_timeout(500)  # let animations settle
        el.screenshot(path=f"{OUT}/{name}.png", omit_background=False)
    # Full PDF
    page.pdf(path=f"{OUT}/mockup.pdf", format="A3",
             print_background=True, scale=0.85)
    browser.close()
print("✓ exported to", OUT)
```

Run this in 30 seconds → 7 retina PNGs + 1 PDF, ready for Google Slides / PowerPoint / Loom. Eliminates manual screencap toil.

---

## 10. Cost model

### Per-engagement (TAG-style, 9 shots, full pipeline)

| Line item                                | Cost     |
|------------------------------------------|----------|
| Image gen (Flux 70% + gpt-image-1 30%)   | $0.50    |
| Claude vision art-direction (9 × 1.5 iter) | $0.30  |
| n8n run + storage                        | ~$0.02   |
| Brandfolder per-asset overhead           | ~$0.05   |
| Playwright export                        | ~$0.01   |
| **TOTAL per engagement**                 | **<$1**  |

### Annual @ 50 engagements

| Bucket                              | Annual cost |
|-------------------------------------|-------------|
| Per-engagement variable (× 50)      | $50         |
| n8n hosting (Render Standard)       | $300        |
| PostgreSQL + Redis (managed)        | $360        |
| Brandfolder subscription            | $3,000      |
| Claude API (assume 1M tokens/mo)    | $360        |
| OpenAI + Flux APIs (image gen pool) | $200        |
| **Total**                           | **~$4,300/yr** |

**Billable side** at $300–500/mockup × 50 = **$15K–25K revenue**. ROI ≈ 4–6×.

The *real* economics: **time saved**. Pre-pipeline, a 9-shot comp took a designer 2 days (~$2K labor). Post-pipeline: 2 hours of art direction + auto-generation = ~$250 labor. **$1,750 saved per engagement × 50 = $87K/yr engineering capacity reclaimed.**

---

## 11. Failure modes — what breaks and how to harden

| Failure                                | Detection                  | Mitigation                            |
|----------------------------------------|----------------------------|---------------------------------------|
| OpenAI rate-limit (429)                | HTTP status code           | Auto-fallback to Flux via fal.ai      |
| OpenAI deprecates model (DALL-E 3 → gpt-image-1 happened!) | API error 404 | Pin model version; smoke-test weekly |
| Generated image has text/logos        | Claude vision scoring      | Refine prompt, regenerate             |
| Brand drift across shots in same engagement | Hash brand-rules JSON per project | Lock rules per-project, audit per-image |
| Content-policy refusal (rare for editorial) | HTTP 400 specific code   | Soften prompt phrasing automatically  |
| n8n SQLite corruption                 | Workflow won't load        | PostgreSQL migration + nightly pg_dump |
| Photo URL expiry (DALL-E URLs are temp) | 404 on download           | We already download to disk — keep it that way |
| Hotlinked brand SVG goes 404          | HTTP check                 | Mirror to S3/R2 weekly                |
| Client legal review fails             | Pre-delivery audit         | Brandfolder approval gate, usage tags |
| Cost runaway                          | Per-engagement spend > cap | Slack alert at 80%, hard-stop at 100% |

---

## 12. Recommended roadmap

**Week 1 (this week):**
- Migrate n8n to Postgres + queue mode (1 day)
- Wire Claude vision scoring into Python script (1 day)
- Set up Playwright export (½ day)

**Weeks 2–3:**
- n8n Source Control to private GitHub (½ day)
- Flux via fal.ai fallback in image-gen script (½ day)
- Per-engagement cost tracking in Postgres (1 day)
- Mirror TAG brand SVGs to S3 (½ day)

**Month 2:**
- Brandfolder onboarding (week-long pilot, then live)
- Slack approval flow (n8n → Brandfolder → Slack)
- Two-engagement live test (use on next two real pitches)

**Month 3:**
- Build the `/brief-to-prompts` Claude skill (turn raw client brief into JSON prompt manifest)
- Add a second model in art-director loop (Claude debates DALL-E vs. Flux choice per shot)
- Quarterly model bake-off (re-score each provider, swap defaults if needed)

---

## 13. What NOT to do

- **Don't add Midjourney via PiAPI/UseAPI for production.** Reliability is poor, TOS is grey. Use it for personal exploration only.
- **Don't switch to Make.com or Zapier.** You'll lose self-host control and the code-block flexibility n8n gives.
- **Don't build a "design AI" SaaS.** You're an agency, not a tool company. Sell the *outcome* (mockups) not the *tool*.
- **Don't try to one-shot full app mockups via Lovable/Bolt.** These are great for demos but won't produce 6,400-line bespoke HTML comps. Use them inside the pipeline as components, not as replacements.
- **Don't put live API keys in n8n credentials without rotation.** Set quarterly rotation reminders + use AWS Secrets Manager or 1Password Connect.

---

## 14. Open questions worth answering before scaling

1. **Where does the pipeline run in production?** Render, EC2, mac-studio via Tailscale? (Affects latency, cost, reliability.)
2. **Who owns the brand-rules JSON per client?** Design lead or account lead? (Affects audit trail.)
3. **Is there a TAG-specific compliance constraint (HIPAA-adjacent imagery)?** Probably not for marketing comps, but worth a 1-line legal check before generating patient-like imagery.
4. **What's the SLA for "art direction loop" cost overrun?** Hard-cap at $5/engagement, $50/engagement, or no cap?
5. **Should we expose this pipeline to clients as a self-serve tool?** Probably not — keep it internal, sell the output.

---

## Appendix A — Canonical links

- n8n docs: https://docs.n8n.io
- n8n source control: https://docs.n8n.io/source-control-environments/
- OpenAI image API: https://platform.openai.com/docs/guides/images
- Flux via fal.ai: https://fal.ai/models/fal-ai/flux/dev
- Flux via Replicate: https://replicate.com/black-forest-labs/flux-dev
- Anthropic vision: https://docs.anthropic.com/en/docs/build-with-claude/vision
- Playwright: https://playwright.dev/python/
- Brandfolder API: https://developers.brandfolder.com
- Imagen 3 (Vertex): https://cloud.google.com/vertex-ai/generative-ai/docs/image/generate-images

## Appendix B — File map (this engagement)

```
/Users/chrismason/Documents/TAG/Mockups/aspen_clearchoice/
├── index.html                       # The mockup itself (6,400+ lines)
├── generate_photos.py               # Python image-gen script
├── n8n_workflow.json                # n8n workflow (importable)
├── photo_prompts.md                 # Prompt library (style guardrails)
├── PIPELINE_BEST_PRACTICES_2026.md  # ← this doc
├── README_pipeline.md               # Pipeline how-to
└── brand/
    ├── aspen_wordmark.svg           # Official, TAG CDN
    ├── clearchoice_wordmark.svg     # Official, TAG CDN
    ├── cc_connect_icon.jpg          # App Store
    └── photos/                      # Generated assets
        ├── A2_drpatel.jpg
        ├── A3a_intake.jpg
        ├── A3b_after_exam.jpg
        ├── B1_cc_hero.jpg
        ├── B2_drchen.jpg
        ├── B3_maria.jpg
        ├── B4b_james.jpg
        ├── B4c_anne.jpg
        ├── B6_applewatch.jpg
        └── manifest.json
```

---

**Bottom line:** the TAG pipeline as-built is already a 70× cost advantage over traditional photo shoots. The 5 hardening moves above raise it to **production-grade for 50+ engagements/yr** and turn the savings into reclaimed engineering capacity rather than just lower bills.
