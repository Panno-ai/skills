---
name: llm-resource-usage
description: >
  Analyzes the user's LLM/AI usage across all local harnesses and coding agents
  (Claude Code, OpenClaw, OpenCode, Goose, Codex CLI, Gemini CLI, Cursor, Amp, etc.),
  then enriches that data with environmental impact (energy, CO₂, water), likely
  datacenter locations, and fun equivalency comparisons — and produces a visual
  infographic + narrative report. Use this skill whenever the user asks about:
  their AI usage, token consumption, LLM costs, energy footprint of AI, how much
  they've spent on AI, carbon footprint of their coding agent, usage stats, "how
  many tokens have I used", AI environmental impact, "what's my AI bill", or
  wants to see charts/visuals of their LLM activity. Also trigger when they ask
  to "track", "analyze", "visualize", or "report" on AI or token usage.
---

# LLM Resource Usage

A skill that extracts a user's real LLM usage from local harness files, enriches
it with environmental and datacenter data, and produces an infographic + narrative.

---

## Step 1: Run the extraction + enrichment pipeline

```bash
python scripts/run.py [DAYS]
```

Default is 30 days. The script auto-detects available harnesses and tries
tokscale first (covers 18+ tools), then falls back to direct file parsing for
Claude Code, OpenCode, OpenClaw, and Goose.

Capture the JSON output into a variable. If there's an error or no data, tell
the user what harnesses were detected and what's missing. If `record_count` is 0,
suggest they install tokscale: `cargo install tokscale` or check
https://github.com/junhoyeo/tokscale for other install methods.

---

## Step 2: Parse the enriched JSON

The JSON has these top-level keys:

| Key | Contents |
|---|---|
| `meta` | Days analyzed, extraction method, detected harnesses, warnings |
| `totals` | input_tokens, output_tokens, cache_read, total_tokens, cost_usd |
| `environmental` | energy_wh, co2_g, water_direct_ml, datacenter info, renewable claim |
| `equivalencies` | phone charges, car km, water glasses, tree days, Google searches |
| `cache` | hit_rate, tokens_saved, cost_saved_pct |
| `efficiency` | tokens_per_dollar, avg_daily, dominant model/provider |
| `by_model` | Per-model breakdown with env data and datacenter info |
| `by_harness` | Per-harness token counts |
| `timeline` | Daily usage array [{date, input_tokens, output_tokens, cost_usd}] |

---

## Step 3: Generate the HTML report

Run the renderer to produce a standalone HTML file that works in any browser:

```bash
python scripts/run.py [DAYS] | python scripts/render.py > report.html
```

Then present `report.html` to the user with the `present_files` tool so they can download and open it. The file includes:
- Stat cards (tokens, cost, energy, CO₂)
- Horizontal model breakdown bars with energy per model
- Datacenter location card + cache efficiency
- Equivalency comparisons (phone charges, Google searches, driving, water, tree days)
- Stacked daily timeline chart (Chart.js loaded from CDN)
- Light and dark mode via `prefers-color-scheme`, print-friendly styles

**If running in claude.ai** (the `visualize:show_widget` tool is available), also call it to render the summary inline — use the design spec below. Do both: the HTML file for the user to keep, the widget for immediate in-chat display.

### Inline widget spec (claude.ai only)

Call `visualize:show_widget` twice — once for the summary infographic, once for the timeline.

### Design system rules
- No emoji. Use inline SVG icons for phone, car, water, search, tree.
- No dark backgrounds. Use `var(--color-background-secondary)` for cards.
- Use `var(--font-mono)` for all numbers.
- Teal `#1D9E75` for environmental metrics (energy, CO₂, cache hit). Blue `#378ADD` for tokens. Amber `#EF9F27` for cost.
- Renewable badge: background `#E1F5EE`, text `#085041`.
- Card style: `background: var(--color-background-secondary); border-radius: var(--border-radius-md); padding: 14px 16px;`
- All labels: `font-size: 11px; color: var(--color-text-tertiary); letter-spacing: .06em; text-transform: uppercase; margin: 0 0 3px; font-weight: 500;`

### Visualization A — Summary infographic

Structure (stacked vertically):

**Row 1 — 4 metric cards** in a `grid-template-columns: repeat(4, minmax(0,1fr)); gap: 8px` grid:
- Tokens: format large numbers as `1M`, `2.4M`, `847K` etc. Sub-label: "Xk in · Yk out"
- Estimated cost: `$X.XX` — note "(estimated)" if cost_usd was 0 in raw data
- Energy: show in Wh if <1000, else kWh to 2dp. Sub-label "incl. PUE overhead"
- CO₂: show in g if <1000, else kg. Sub-label "location-based grid"

**Row 2 — Model breakdown card** (full width):
For each model in `by_model` (sorted by token share descending), show:
- Color swatch (8×8px rounded) — teal=medium, blue=nano, purple=large, amber=small
- Model name, class label in tertiary, and right-aligned "XX% · YYY Wh"
- A CSS progress bar: grey background `var(--color-border-tertiary)`, colored fill, height 7px, border-radius 3px
- Bar width = `(model_tokens / total_tokens) * 100%`

**Row 3 — Two columns** (`grid-template-columns: 1fr 1fr; gap: 8px`):

Left column (stacked):
- Datacenter card: provider/cloud/city, PUE and WUE on one line, renewable claim badge
- Cache card: hit_rate % in teal + cost_saved_pct % in amber, side by side with a thin divider. Add a small visual bar showing the hit rate.

Right column:
- Equivalencies card: for each equivalency, one row with SVG icon + number + label.
  Show: phone charges, Google searches, car meters (as "X m" or "X km"), water in mL or L, tree absorption days.
  Rows separated by `border-bottom: 0.5px solid var(--color-border-tertiary)`.

**Footer**: `font-size: 10px; color: var(--color-text-tertiary)` — one line: "~Estimates. Sources: [provider] sustainability report (PUE/WUE), EPA eGRID 2023 (grid carbon), Epoch AI 2025 (model energy)."

### Visualization B — Usage timeline

Use Chart.js 4.4.1 from `cdnjs.cloudflare.com`. Stacked bar chart. Canvas wrapper: `position:relative; width:100%; height:220px`.

```js
// Color scheme — hardcoded hex (Canvas cannot resolve CSS variables)
// Input tokens: #B5D4F4 (blue-200), Output tokens: #378ADD (blue-400)
// isDark check: const isDark = matchMedia('(prefers-color-scheme: dark)').matches;
// gridColor: isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.07)'
// tickColor: isDark ? 'rgba(255,255,255,0.45)' : 'rgba(0,0,0,0.45)'
```

Config:
- `type: 'bar'`, two datasets both with `stack: 'tokens'`
- Input dataset: `backgroundColor: '#B5D4F4'`, border-radius on bottom corners
- Output dataset: `backgroundColor: '#378ADD'`, border-radius on top corners
- Y-axis ticks: `callback: v => v >= 1000000 ? (v/1000000).toFixed(1)+'M' : v >= 1000 ? (v/1000).toFixed(0)+'K' : v`
- Tooltip: show both datasets in K or M format
- Custom HTML legend (not Chart.js built-in): two squares above the canvas
- `scales.x.ticks: { autoSkip: false }` — show all date labels
- Only render if `timeline.length >= 2`. If fewer than 2 data points, skip this visualization with a note.

Skip the cost line overlay if all `cost_usd` values in the timeline are 0.

---

## Step 4: Write the narrative

After the visuals, write a **3–4 paragraph narrative** covering:

1. **What they used**: Total numbers in plain English. Which harnesses and models.
   Most active days. How diverse their model use was.

2. **What it cost the planet**: Energy (with a memorable comparison — e.g. "enough
   to charge your phone X times"), CO₂ (with driving equivalent), water (with glass/
   bottle equivalent). Note the datacenter location and renewable energy claim.
   Be accurate but put things in perspective — individual use is generally small.

3. **Efficiency insights**: Cache hit rate and what it saved them. Tokens-per-dollar
   efficiency. Whether they're using the right model sizes for the work. If they
   have a high proportion of Opus/GPT-4 usage, gently note that Haiku/Sonnet would
   be more energy-efficient for simpler tasks.

4. **One interesting or surprising fact**: Something specific to their data —
   e.g. "Your cache efficiency of 34% means you avoided X tokens of redundant
   processing", or "Your output-to-input ratio of 1:4 is unusually high, suggesting
   long generative tasks rather than Q&A", or mention the specific AWS facility
   their tokens likely ran through.

---

## Formatting and tone

- Lead with the visuals, then the narrative
- Use specific numbers, not vague descriptions
- Be honest about uncertainty in environmental estimates — prefix with "~" and
  note at the end: *"Environmental figures are estimates based on published research
  (Samsi et al 2023, Jehham et al 2025) and provider sustainability reports.
  Actual values vary with hardware generation, server utilization, and grid mix."*
- Don't be preachy about environmental impact — present it as interesting
  context, not guilt
- If no data was found, clearly explain which harnesses were checked and how
  to get tokscale installed

---

## Handling edge cases

**No data found**: Check `meta.record_count == 0`. Tell the user which paths
were checked. Suggest installing tokscale or checking if the harness stores
data in a non-default location.

**Only one model**: Skip the model breakdown chart; instead make the summary
infographic larger and more detailed.

**Very large numbers** (>1B tokens): Format as "X.XB". Convert energy to kWh,
CO₂ to kg, water to liters.

**Very small numbers** (<10k tokens): Still produce the output but note it's a
small sample. The timeline chart won't be interesting — skip it and just show
the summary infographic.

**Warnings in meta.warnings**: Surface them clearly above the visuals. The most
common warning is "tokscale not installed" — display this with the install command.

**Missing cost data**: The enrich script estimates cost from public pricing tables.
Note this with "~$X (estimated from public pricing)".

---

## Reference data (don't load unless needed)

The `references/data.json` file has complete lookup tables for provider datacenter
info, model energy classes, grid carbon intensity, and equivalency constants.
The enrich script embeds these automatically — you don't need to read this file
unless you want to add a custom calculation or override a value.

---

## Quick test (no real harness needed)

To verify the pipeline works, run:
```bash
echo '{"extraction_method":"test","days_analyzed":30,"detected_harnesses":["claude_code"],
"record_count":150,"warnings":[],"aggregated":{"totals":{"input_tokens":800000,
"output_tokens":200000,"cache_read":240000,"cache_write":80000,"total_tokens":1000000,
"cost_usd":0},"by_date":{},"by_model":{"claude-sonnet-4-6":{"input_tokens":650000,
"output_tokens":160000,"cache_read":240000,"provider":"anthropic","cost_usd":0},
"claude-haiku-4-5":{"input_tokens":150000,"output_tokens":40000,"provider":"anthropic","cost_usd":0}},
"by_harness":{"claude_code":{"input_tokens":1000000}},"by_provider":{},"timeline":[]}}' \
| python scripts/enrich.py
```
