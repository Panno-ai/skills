#!/usr/bin/env python3
"""
llm-resource-usage/scripts/render.py

Reads enriched JSON (from stdin or file) and renders a standalone HTML report.
The HTML file is self-contained (Chart.js loaded from cdnjs CDN; everything else inline).

Usage:
  python scripts/run.py 30 | python scripts/render.py > report.html
  python scripts/render.py enriched.json report.html
  python scripts/render.py enriched.json          # writes enriched_report.html next to input
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

# ── entry point ───────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) >= 2 and sys.argv[1] != "-":
        input_path = Path(sys.argv[1])
        data = json.loads(input_path.read_text())
        if len(sys.argv) >= 3:
            out_path = Path(sys.argv[2])
        else:
            out_path = input_path.parent / (input_path.stem + "_report.html")
        html = render(data)
        out_path.write_text(html, encoding="utf-8")
        print(f"Report written to: {out_path}", file=sys.stderr)
    else:
        data = json.load(sys.stdin)
        html = render(data)
        print(html)


# ── main renderer ─────────────────────────────────────────────────────────────

def render(data: dict) -> str:
    meta   = data.get("meta", {})
    totals = data.get("totals", {})
    env    = data.get("environmental", {})
    eq     = data.get("equivalencies", {})
    cache  = data.get("cache", {})
    eff    = data.get("efficiency", {})
    models = data.get("by_model", [])
    harnesses = data.get("by_harness", {})
    timeline  = data.get("timeline", [])

    dc = env.get("primary_datacenter", {})

    days       = meta.get("days_analyzed", 30)
    gen_date   = datetime.now().strftime("%B %-d, %Y")
    warnings   = meta.get("warnings", [])
    harness_list = ", ".join(meta.get("detected_harnesses", []) or ["unknown"])

    # ── format helpers ──
    def fmt_tok(n):
        if n >= 1_000_000: return f"{n/1_000_000:.1f}M".replace(".0M","M")
        if n >= 1_000:     return f"{n/1_000:.0f}K"
        return str(n)

    def fmt_wh(n):
        if n >= 1000: return f"{n/1000:.2f} kWh"
        return f"{n:.1f} Wh"

    def fmt_co2(n):
        if n >= 1000: return f"{n/1000:.2f} kg CO₂"
        return f"{n:.1f} g CO₂"

    def fmt_water(n):
        if n >= 1000: return f"{n/1000:.2f} L"
        return f"{int(round(n))} mL"

    def fmt_cost(n):
        if n == 0: return "~$0.00"
        return f"${n:.2f}"

    def fmt_meters(n):
        if n >= 1000: return f"{n/1000:.2f} km"
        return f"{int(round(n))} meters"

    def pct(n): return f"{n:.0f}%"

    # ── model colors ──
    MODEL_COLORS = {
        "nano":   "#378ADD",
        "small":  "#EF9F27",
        "medium": "#1D9E75",
        "large":  "#D85A30",
        "local":  "#888780",
    }

    # ── stat cards ──
    total_tokens = totals.get("total_tokens", 0)
    in_tok  = totals.get("input_tokens", 0)
    out_tok = totals.get("output_tokens", 0)
    cr      = totals.get("cache_read", 0)

    stat_cards_html = f"""
    <div class="stat-grid">
      <div class="card stat-card">
        <div class="stat-label">tokens used</div>
        <div class="stat-value mono">{fmt_tok(total_tokens)}</div>
        <div class="stat-sub">{fmt_tok(in_tok)} in &middot; {fmt_tok(out_tok)} out</div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">estimated cost</div>
        <div class="stat-value mono">{fmt_cost(totals.get("cost_usd", 0))}</div>
        <div class="stat-sub">{days}-day period</div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">energy</div>
        <div class="stat-value mono">{fmt_wh(env.get("energy_wh", 0))}</div>
        <div class="stat-sub">incl. PUE&thinsp;{dc.get("pue", "–")} overhead</div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">CO₂</div>
        <div class="stat-value mono">{fmt_co2(env.get("co2_g", 0))}</div>
        <div class="stat-sub">location-based grid</div>
      </div>
    </div>"""

    # ── model breakdown ──
    model_rows = ""
    for m in models[:6]:
        name  = m.get("model", "unknown")
        cls   = m.get("model_class", "medium")
        color = MODEL_COLORS.get(cls, "#888")
        mt    = m.get("total_tokens", 0)
        share = (mt / total_tokens * 100) if total_tokens else 0
        wh    = m.get("energy_wh", 0)
        model_rows += f"""
        <div class="model-row">
          <div class="model-meta">
            <span class="model-dot" style="background:{color}"></span>
            <span class="model-name">{name}</span>
            <span class="model-class">{cls}</span>
          </div>
          <span class="model-stat mono">{share:.0f}%&ensp;·&ensp;{fmt_wh(wh)}</span>
        </div>
        <div class="bar-track">
          <div class="bar-fill" style="width:{min(share,100):.1f}%;background:{color}"></div>
        </div>"""

    model_section_html = f"""
    <div class="card section-card">
      <div class="section-label">by model &middot; token share</div>
      {model_rows}
    </div>"""

    # ── datacenter + cache ──
    carbon_intensity = env.get("carbon_intensity_g_per_kwh", 0)
    renewable = dc.get("renewable_claim", "Not disclosed")
    # Does the provider claim 100% annual renewable matching?
    claims_100pct = "100%" in renewable

    hit_rate   = cache.get("hit_rate", 0) * 100
    cost_saved = cache.get("cost_saved_pct", 0)

    market_note = (
        "Provider purchases RECs/PPAs matching 100% of electricity annually — "
        "but physical electrons still come from the regional grid."
        if claims_100pct else
        f"Renewable claim: {renewable[:60]}"
    )

    dc_html = f"""
    <div class="card section-card">
      <div class="section-label">inference location</div>
      <div class="dc-name">{dc.get("label", "Unknown provider")}</div>
      <div class="dc-region">{dc.get("location_label", "")}</div>
      <div class="dc-meta">PUE&thinsp;{dc.get("pue","–")} &middot; WUE&thinsp;{dc.get("wue_ml_per_kwh","–")}&thinsp;mL/kWh</div>
      <div class="dc-grid-row">
        <div class="dc-grid-col">
          <div class="dc-grid-val mono">{carbon_intensity}</div>
          <div class="dc-grid-lbl">gCO₂/kWh</div>
          <div class="dc-grid-method">location-based</div>
        </div>
        <div class="dc-grid-divider"></div>
        <div class="dc-grid-col dc-grid-faded">
          <div class="dc-grid-val mono">~0</div>
          <div class="dc-grid-lbl">gCO₂/kWh</div>
          <div class="dc-grid-method">market-based (RECs)</div>
        </div>
      </div>
      <div class="dc-accounting-note">{market_note} CO₂ in this report uses location-based intensity.</div>
    </div>"""

    cache_html = f"""
    <div class="card section-card">
      <div class="section-label">prompt cache</div>
      <div class="cache-row">
        <div class="cache-stat">
          <div class="cache-val mono teal">{pct(hit_rate)}</div>
          <div class="cache-lbl">hit rate</div>
        </div>
        <div class="cache-divider"></div>
        <div class="cache-stat">
          <div class="cache-val mono amber">{pct(cost_saved)}</div>
          <div class="cache-lbl">cost saved</div>
        </div>
        <div class="cache-bar-wrap">
          <div class="cache-bar-track">
            <div class="cache-bar-fill teal-bg" style="width:{min(hit_rate,100):.1f}%"></div>
          </div>
        </div>
      </div>
    </div>"""

    # ── equivalencies ──
    phone  = eq.get("phone_charges", 0)
    gsrch  = eq.get("equivalent_google_searches", 0)
    car_m  = eq.get("car_driving_meters", 0)
    water  = env.get("water_direct_ml", 0)
    trees  = eq.get("tree_absorption_days", 0)

    # SVG icons (16×16 viewBox, stroke=currentColor)
    ICON_PHONE  = '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="4.5" y="1" width="7" height="13.5" rx="1.5" stroke="currentColor" stroke-width="1.2"/><line x1="6.5" y1="12" x2="9.5" y2="12" stroke="currentColor" stroke-width="1.2"/><line x1="7.5" y1="2.5" x2="8.5" y2="2.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>'
    ICON_SEARCH = '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" stroke-width="1.2"/><line x1="10" y1="10" x2="14" y2="14" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>'
    ICON_CAR    = '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1.5" y="5.5" width="13" height="5" rx="1.5" stroke="currentColor" stroke-width="1.2"/><circle cx="4.5" cy="11" r="1.5" stroke="currentColor" stroke-width="1.2"/><circle cx="11.5" cy="11" r="1.5" stroke="currentColor" stroke-width="1.2"/><path d="M3.5 5.5L5 3H11L12.5 5.5" stroke="currentColor" stroke-width="1.2"/></svg>'
    ICON_WATER  = '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M8 1.5C8 1.5 3 6.5 3 10.5C3 13.261 5.239 15.5 8 15.5C10.761 15.5 13 13.261 13 10.5C13 6.5 8 1.5Z" stroke="currentColor" stroke-width="1.2"/></svg>'
    ICON_TREE   = '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M8 1L12 6H9.5V10H6.5V6H4L8 1Z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/><rect x="7" y="10" width="2" height="4" rx="0.5" stroke="currentColor" stroke-width="1.2"/></svg>'

    def eq_row(icon, value, label, sub=None):
        sub_html = f'<span class="eq-sub">{sub}</span>' if sub else ""
        return f'<div class="eq-row"><span class="eq-icon">{icon}</span><div class="eq-text"><span class="eq-num mono">{value}</span> <span class="eq-label">{label}</span>{sub_html}</div></div>'

    # Car: show distance + fraction-of-km context when < 1 km
    if car_m < 1000:
        car_label = f"driving (~{car_m/1000:.2f} km, CO₂)"
        car_sub = None
    else:
        car_label = "driving (CO₂)"
        car_sub = None

    # Water: show mL directly; note this is on-site cooling only
    water_label = "on-site cooling water"
    water_sub = "(excludes upstream electricity generation water)"

    eq_html = f"""
    <div class="card section-card">
      <div class="section-label">equivalent to&hellip;</div>
      {eq_row(ICON_PHONE,  f"{phone:.1f}",      "phone charges")}
      {eq_row(ICON_SEARCH, f"{int(gsrch):,}",   "Google searches (energy)")}
      {eq_row(ICON_CAR,    fmt_meters(car_m),    car_label, car_sub)}
      {eq_row(ICON_WATER,  fmt_water(water),     water_label, water_sub)}
      {eq_row(ICON_TREE,   f"{trees:.2f} days", "tree CO₂ absorption")}
    </div>"""

    # ── warnings ──
    warnings_html = ""
    if warnings:
        items = "".join(f"<li>{w}</li>" for w in warnings)
        warnings_html = f'<div class="warning-box"><strong>Notes</strong><ul>{items}</ul></div>'

    # ── timeline chart data ──
    tl_labels = json.dumps([r.get("date","") for r in timeline])
    tl_input  = json.dumps([r.get("input_tokens",0) for r in timeline])
    tl_output = json.dumps([r.get("output_tokens",0) for r in timeline])
    tl_cost   = json.dumps([r.get("cost_usd",0) for r in timeline])
    has_cost  = any(r.get("cost_usd",0) > 0 for r in timeline)
    has_tl    = len(timeline) >= 2

    timeline_section = ""
    if has_tl:
        cost_dataset = ""
        if has_cost:
            cost_dataset = f"""{{
              type: 'line',
              label: 'Cost (USD)',
              data: {tl_cost},
              borderColor: '#EF9F27',
              backgroundColor: 'transparent',
              borderWidth: 1.5,
              pointRadius: 3,
              pointBackgroundColor: '#EF9F27',
              yAxisID: 'yCost',
              tension: 0.3,
              order: 0
            }},"""
        cost_axis = ""
        if has_cost:
            cost_axis = """yCost: {
                position: 'right',
                grid: { drawOnChartArea: false },
                ticks: { color: isDark ? 'rgba(255,255,255,0.45)' : 'rgba(0,0,0,0.45)', font: {size:11},
                  callback: v => '$' + v.toFixed(2) }
              },"""
        timeline_section = f"""
    <div class="card section-card" style="margin-top:10px;">
      <div class="section-label">daily usage</div>
      <div class="chart-legend">
        <span class="legend-item"><span class="legend-dot" style="background:#B5D4F4"></span>input tokens</span>
        <span class="legend-item"><span class="legend-dot" style="background:#378ADD"></span>output tokens</span>
        {'<span class="legend-item"><span class="legend-dot" style="background:#EF9F27;border-radius:50%;"></span>cost</span>' if has_cost else ''}
      </div>
      <div style="position:relative;width:100%;height:220px;">
        <canvas id="timelineChart" role="img" aria-label="Daily token usage over time"></canvas>
      </div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
    <script>
    (function(){{
      const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      const gc = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.07)';
      const tc = isDark ? 'rgba(255,255,255,0.45)' : 'rgba(0,0,0,0.45)';
      const ctx = document.getElementById('timelineChart');
      if(!ctx || typeof Chart === 'undefined') return;
      new Chart(ctx, {{
        data: {{
          labels: {tl_labels},
          datasets: [
            {cost_dataset}
            {{
              type: 'bar', label: 'Output tokens', data: {tl_output},
              backgroundColor: '#378ADD', stack: 'tok', yAxisID: 'yTok', order: 1,
              borderRadius: {{topLeft:2,topRight:2,bottomLeft:0,bottomRight:0}}, borderSkipped:'top'
            }},
            {{
              type: 'bar', label: 'Input tokens', data: {tl_input},
              backgroundColor: '#B5D4F4', stack: 'tok', yAxisID: 'yTok', order: 2,
              borderRadius: {{topLeft:0,topRight:0,bottomLeft:2,bottomRight:2}}, borderSkipped:'bottom'
            }}
          ]
        }},
        options: {{
          responsive: true, maintainAspectRatio: false,
          plugins: {{ legend: {{ display: false }} }},
          scales: {{
            x: {{ stacked:true, grid:{{color:gc}}, ticks:{{color:tc,font:{{size:11}},autoSkip:false,maxRotation:45}} }},
            yTok: {{
              stacked:true, position:'left', grid:{{color:gc}},
              ticks:{{color:tc,font:{{size:11}},callback:v=>v>=1e6?(v/1e6).toFixed(1)+'M':v>=1e3?(v/1e3).toFixed(0)+'K':v}}
            }},
            {cost_axis}
          }}
        }}
      }});
    }})();
    </script>"""

    # ── sources appendix ──
    appendix_html = """
<details class="appendix">
  <summary class="appendix-toggle">Sources &amp; methodology</summary>
  <div class="appendix-body">

    <div class="appendix-section">
      <h3>Energy per token</h3>
      <ul>
        <li><a href="https://epoch.ai/gradient-updates/how-much-energy-does-chatgpt-use" target="_blank">Epoch AI — You, J. (Feb 2025): "How much energy does ChatGPT use?"</a> — GPT-4o typical query ~0.3 Wh at 500 output tokens. Basis for medium model class (500 Wh/MTok output).</li>
        <li><a href="https://towardsdatascience.com/lets-analyze-openais-claims-about-chatgpt-energy-use/" target="_blank">Towards Data Science — analysis of OpenAI/Altman (Jun 2025) disclosure</a> — average ChatGPT query ~0.34 Wh. Cross-check for large model class (700 Wh/MTok output).</li>
        <li><a href="https://llm-tracker.info/_TOORG/Power-Usage-and-Energy-Efficiency" target="_blank">LLM Tracker — Lin, L.H. (2025): Llama3-70B on 8×H100 FP8</a> — 0.39 J/total token at batch 128. Modern H100 high-concurrency baseline.</li>
        <li><a href="https://arxiv.org/pdf/2310.03003" target="_blank">Samsi et al. (Oct 2023): "From Words to Watts" (arXiv:2310.03003)</a> — LLaMA-65B on V100/A100: 3–4 J/output token = 833–1,111 Wh/MTok. Older hardware baseline.</li>
        <li><a href="https://arxiv.org/html/2512.03024v1" target="_blank">TokenPowerBench (Dec 2025, arXiv:2512.03024)</a> — LLM energy scales super-linearly with parameter count; basis for class scaling ratios.</li>
      </ul>
    </div>

    <div class="appendix-section">
      <h3>PUE (Power Usage Effectiveness)</h3>
      <ul>
        <li><a href="https://sustainability.aboutamazon.com/products-services/aws-cloud" target="_blank">Amazon 2024 Sustainability Report — AWS Cloud</a> — AWS global PUE 1.15 (2024). Best site: 1.04 (Europe).</li>
        <li><a href="https://datacenters.google/operating-sustainably/" target="_blank">Google Data Centers — Operating Sustainably</a> — Google global PUE 1.09 (2024); industry average 1.56.</li>
        <li><a href="https://thenewstack.io/cloud-pue-comparing-aws-azure-and-gcp-global-regions/" target="_blank">The New Stack — Cloud PUE: AWS, Azure and GCP compared (Jan 2025)</a> — Microsoft global average PUE ~1.18; best site 1.11 (Wyoming).</li>
      </ul>
    </div>

    <div class="appendix-section">
      <h3>WUE (Water Usage Effectiveness)</h3>
      <ul>
        <li><a href="https://sustainability.aboutamazon.com/natural-resources/water" target="_blank">Amazon Water Stewardship page</a> — AWS global WUE 0.15 L/kWh (150 mL/kWh) in 2024; 40% improvement since 2021. Industry average: 0.36 L/kWh (Berkeley Lab 2024).</li>
        <li><a href="https://www.microsoft.com/en-us/microsoft-cloud/blog/2024/12/09/sustainable-by-design-next-generation-datacenters-consume-zero-water-for-cooling/" target="_blank">Microsoft blog — "Sustainable by design: Next-generation datacenters consume zero water" (Dec 2024)</a> — Azure global WUE 0.30 L/kWh (300 mL/kWh) FY2024; 39% improvement since 2021.</li>
        <li>Google WUE is not publicly disclosed as a fleet-wide figure. Value estimated from reported 6.1 billion gallons cooling water (2023 Environmental Report) divided by estimated data center electricity. ±60% uncertainty.</li>
      </ul>
    </div>

    <div class="appendix-section">
      <h3>Grid carbon intensity</h3>
      <ul>
        <li><a href="https://www.epa.gov/system/files/documents/2025-06/summary_tables_rev2.pdf" target="_blank">EPA eGRID 2023 Summary Tables (published Mar 2025)</a> — US subregion CO₂ output emission rates in lb/MWh, converted via ×0.4536 to gCO₂/kWh. RFCE (N. Virginia) = 271, NWPP (Oregon) = 287, MROW (Iowa) = 417, CAMX (California) = 194 gCO₂/kWh.</li>
        <li><a href="https://ember-energy.org/countries-and-regions/the-netherlands/" target="_blank">Ember 2024 — Netherlands electricity data</a> — Netherlands 2023 annual carbon intensity = 268.5 gCO₂/kWh. Used for Azure West Europe and GCP europe-west4.</li>
        <li><a href="https://www.epa.gov/energy/greenhouse-gas-equivalencies-calculator-calculations-and-references" target="_blank">EPA GHG Equivalencies Calculator references</a> — US national average 823.1 lb/MWh (2022 data) = 373.4 gCO₂/kWh.</li>
        <li>Note: AWS, Azure, and GCP all claim 100% annual renewable-energy matching via RECs/PPAs. Location-based factors above reflect physical grid reality; market-based accounting would yield near-zero Scope 2 emissions for these providers.</li>
      </ul>
    </div>

    <div class="appendix-section">
      <h3>Equivalency baselines</h3>
      <ul>
        <li><a href="https://www.epa.gov/greenvehicles/greenhouse-gas-emissions-typical-passenger-vehicle" target="_blank">EPA — Greenhouse Gas Emissions from a Typical Passenger Vehicle (Jun 2023)</a> — 404 gCO₂/mile ÷ 1.60934 = 251 gCO₂/km. US fleet average at 22.2 mpg.</li>
        <li><a href="https://www.epa.gov/energy/greenhouse-gas-equivalencies-calculator-calculations-and-references" target="_blank">EPA GHG Equivalencies Calculator</a> — one tree sequesters ~48 lbs CO₂/year = 21,772 g/year.</li>
        <li>Phone charge: ~15 Wh based on typical flagship smartphone battery specs (iPhone 15 Pro: 12.7 Wh; Galaxy S24: ~15.4 Wh).</li>
        <li>Google search energy: ~0.3 Wh (= 0.0003 kWh), per Google's own published figure.</li>
      </ul>
    </div>

  </div>
</details>"""

    # ── assemble ──
    return HTML_TEMPLATE.format(
        gen_date        = gen_date,
        days            = days,
        harness_list    = harness_list,
        warnings_html   = warnings_html,
        stat_cards_html = stat_cards_html,
        model_section   = model_section_html,
        dc_html         = dc_html,
        cache_html      = cache_html,
        eq_html         = eq_html,
        timeline_section= timeline_section,
        appendix_html   = appendix_html,
    )


# ── HTML template ─────────────────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LLM Resource Usage Report</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#ffffff;
  --bg-card:#f5f4f1;
  --bg-card2:#edecea;
  --text:#1a1a1a;
  --text2:#555;
  --text3:#888;
  --border:rgba(0,0,0,0.10);
  --border2:rgba(0,0,0,0.06);
  --teal:#1D9E75;
  --blue:#378ADD;
  --amber:#EF9F27;
  --coral:#D85A30;
  --teal-light:#E1F5EE;
  --teal-dark:#085041;
  --r:8px;
}}
@media(prefers-color-scheme:dark){{
  :root{{
    --bg:#141414;--bg-card:#1e1e1e;--bg-card2:#252525;
    --text:#e8e8e8;--text2:#aaa;--text3:#666;
    --border:rgba(255,255,255,0.10);--border2:rgba(255,255,255,0.06);
    --teal-light:#0d3326;--teal-dark:#9FE1CB;
  }}
}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
  background:var(--bg);color:var(--text);font-size:14px;line-height:1.5;padding:24px;}}
.mono{{font-family:ui-monospace,'SF Mono','Cascadia Code','Fira Code',monospace}}
.container{{max-width:860px;margin:0 auto}}
.header{{margin-bottom:20px;padding-bottom:16px;border-bottom:0.5px solid var(--border)}}
.header h1{{font-size:18px;font-weight:500;color:var(--text);margin-bottom:4px}}
.header .meta{{font-size:12px;color:var(--text3)}}
.warning-box{{background:#fff8e1;border:0.5px solid #f59e0b;border-radius:var(--r);
  padding:10px 14px;margin-bottom:12px;font-size:12px;color:#78350f}}
.warning-box ul{{margin:4px 0 0 16px}}
@media(prefers-color-scheme:dark){{
  .warning-box{{background:#2a1e05;border-color:#78350f;color:#fde68a}}
}}
.card{{background:var(--bg-card);border-radius:var(--r);padding:14px 16px}}
.section-card{{margin-bottom:10px}}
.stat-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-bottom:10px}}
.stat-card{{text-align:left}}
.stat-label{{font-size:11px;color:var(--text3);letter-spacing:.06em;text-transform:uppercase;
  font-weight:500;margin-bottom:3px}}
.stat-value{{font-size:22px;font-weight:500;color:var(--text);line-height:1.15;margin-bottom:2px}}
.stat-sub{{font-size:11px;color:var(--text3)}}
.section-label{{font-size:11px;color:var(--text3);letter-spacing:.06em;text-transform:uppercase;
  font-weight:500;margin-bottom:10px}}
.model-row{{display:flex;justify-content:space-between;align-items:center;margin-bottom:5px}}
.model-meta{{display:flex;align-items:center;gap:6px}}
.model-dot{{width:8px;height:8px;border-radius:2px;flex-shrink:0}}
.model-name{{font-size:13px;color:var(--text)}}
.model-class{{font-size:11px;color:var(--text3)}}
.model-stat{{font-size:12px;color:var(--text2)}}
.bar-track{{background:var(--border);border-radius:3px;height:7px;overflow:hidden;margin-bottom:10px}}
.bar-fill{{height:7px;border-radius:3px;transition:width .3s}}
.bottom-grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:0}}
.left-col,.right-col{{display:flex;flex-direction:column;gap:8px}}
.dc-name{{font-size:14px;font-weight:500;color:var(--text);margin-bottom:2px}}
.dc-region{{font-size:11px;color:var(--text2);margin-bottom:1px}}
.dc-meta{{font-size:11px;color:var(--text3);margin-bottom:9px}}
.dc-grid-row{{display:flex;align-items:stretch;gap:0;margin-bottom:8px;
  background:var(--bg-card2);border-radius:6px;overflow:hidden}}
.dc-grid-col{{flex:1;padding:8px 10px;text-align:center}}
.dc-grid-divider{{width:0.5px;background:var(--border)}}
.dc-grid-faded{{opacity:0.55}}
.dc-grid-val{{font-size:18px;font-weight:500;color:var(--text);line-height:1.1}}
.dc-grid-lbl{{font-size:11px;color:var(--text2);margin:1px 0}}
.dc-grid-method{{font-size:10px;color:var(--text3);font-style:italic}}
.dc-accounting-note{{font-size:10px;color:var(--text3);line-height:1.5}}
.dc-note{{font-size:10px;color:var(--text3);margin-top:4px}}
.cache-row{{display:flex;align-items:center;gap:14px}}
.cache-stat{{flex-shrink:0}}
.cache-val{{font-size:20px;font-weight:500;line-height:1.1}}
.cache-lbl{{font-size:11px;color:var(--text3);margin-top:1px}}
.cache-divider{{width:0.5px;height:32px;background:var(--border)}}
.cache-bar-wrap{{flex:1}}
.cache-bar-track{{background:var(--border);border-radius:3px;height:6px;overflow:hidden}}
.cache-bar-fill{{height:6px;border-radius:3px}}
.teal{{color:var(--teal)}}
.amber{{color:var(--amber)}}
.teal-bg{{background:var(--teal)}}
.eq-row{{display:flex;align-items:flex-start;gap:10px;padding:6px 0;
  border-bottom:0.5px solid var(--border2)}}
.eq-row:last-child{{border-bottom:none}}
.eq-icon{{color:var(--text3);flex-shrink:0;width:16px;height:16px;margin-top:2px}}
.eq-text{{display:flex;flex-direction:column;gap:1px}}
.eq-num{{font-size:15px;font-weight:500;color:var(--text)}}
.eq-label{{font-size:12px;color:var(--text2)}}
.eq-sub{{font-size:10px;color:var(--text3);font-style:italic}}
.chart-legend{{display:flex;flex-wrap:wrap;gap:14px;margin-bottom:10px;font-size:12px;color:var(--text2)}}
.legend-item{{display:flex;align-items:center;gap:5px}}
.legend-dot{{width:10px;height:10px;border-radius:2px}}
.footer{{font-size:10px;color:var(--text3);margin-top:14px;line-height:1.6;
  border-top:0.5px solid var(--border);padding-top:10px}}
@media(max-width:600px){{
  .stat-grid{{grid-template-columns:repeat(2,1fr)}}
  .bottom-grid{{grid-template-columns:1fr}}
}}
@media print{{
  body{{padding:16px}}
  .card{{break-inside:avoid}}
  .appendix{{break-inside:avoid}}
}}
.appendix{{margin-top:20px;border-top:0.5px solid var(--border);padding-top:14px}}
.appendix-toggle{{font-size:12px;font-weight:500;color:var(--text2);cursor:pointer;
  list-style:none;padding:2px 0;user-select:none}}
.appendix-toggle::-webkit-details-marker{{display:none}}
.appendix-toggle::before{{content:"+ ";color:var(--text3)}}
details[open] .appendix-toggle::before{{content:"− ";color:var(--text3)}}
.appendix-body{{margin-top:12px;display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:16px}}
.appendix-section h3{{font-size:11px;font-weight:500;color:var(--text3);letter-spacing:.06em;
  text-transform:uppercase;margin-bottom:8px}}
.appendix-section ul{{list-style:none;display:flex;flex-direction:column;gap:6px}}
.appendix-section li{{font-size:11px;color:var(--text2);line-height:1.55;
  padding-left:10px;border-left:2px solid var(--border)}}
.appendix-section a{{color:var(--blue);text-decoration:none}}
.appendix-section a:hover{{text-decoration:underline}}
</style>
</head>
<body>
<div class="container">

<div class="header">
  <h1>LLM resource usage report</h1>
  <div class="meta">Generated {gen_date} &middot; {days}-day window &middot; {harness_list}</div>
</div>

{warnings_html}

{stat_cards_html}
{model_section}

<div class="bottom-grid">
  <div class="left-col">
    {dc_html}
    {cache_html}
  </div>
  <div class="right-col">
    {eq_html}
  </div>
</div>

{timeline_section}

{appendix_html}

<div class="footer">
  ~Estimates. Energy: Epoch AI (2025), OpenAI disclosure (2025), Samsi et al. (2023). PUE/WUE: provider sustainability reports (AWS 2024, Azure FY2024, Google 2024). Grid carbon: EPA eGRID 2023 (US), Ember 2024 (EU). All figures carry ±30&ndash;50% uncertainty depending on hardware generation and server utilization.
</div>

</div>
</body>
</html>"""


if __name__ == "__main__":
    main()
