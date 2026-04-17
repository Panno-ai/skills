#!/usr/bin/env python3
"""
llm-resource-usage/scripts/enrich.py

Reads extracted usage JSON (from stdin or file), adds:
  - Energy estimates (Wh)
  - Carbon footprint (gCO2)
  - Water consumption (ml)
  - Datacenter locations
  - Fun equivalencies
  - Cache efficiency metrics
  - Cost estimates (if not already present)

Outputs enriched JSON to stdout.

Usage:
  python extract.py 30 | python enrich.py
  python enrich.py usage.json
"""

import json
import sys
import re
import os
from pathlib import Path

# ── load data tables ──────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR.parent / "references" / "data.json"

def load_tables():
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    # Minimal inline fallback
    return {
        "model_energy_wh_per_m_tokens": {
            "input_multiplier": 0.2,
            "model_classes": {"medium": {"output_wh_per_m": 500}},
            "model_overrides": {},
        },
        "grid_carbon_intensity_g_per_kwh": {"default": 300, "global": 230},
        "providers": {},
        "equivalencies": {
            "phone_charge_wh": 15, "car_co2_g_per_km": 170,
            "water_glass_ml": 250, "water_bottle_ml": 500,
        },
    }

TABLES = load_tables()

# ── model classification ──────────────────────────────────────────────────────

MODEL_CLASSES = TABLES["model_energy_wh_per_m_tokens"]["model_classes"]
MODEL_OVERRIDES = TABLES["model_energy_wh_per_m_tokens"]["model_overrides"]
INPUT_MULT = TABLES["model_energy_wh_per_m_tokens"]["input_multiplier"]

# Anthropic pricing $/MTok (April 2026)
ANTHROPIC_PRICES = {
    "claude-opus-4-6":   {"input": 5.00, "output": 25.00},
    "claude-opus-4-5":   {"input": 5.00, "output": 25.00},
    "claude-opus-4":     {"input": 5.00, "output": 25.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4":   {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5":  {"input": 1.00, "output": 5.00},
    "claude-haiku-4":    {"input": 0.80, "output": 4.00},
}

OPENAI_PRICES = {
    "gpt-4o":       {"input": 2.50, "output": 10.00},
    "gpt-4.1":      {"input": 2.00, "output":  8.00},
    "gpt-4o-mini":  {"input": 0.15, "output":  0.60},
    "gpt-4.1-mini": {"input": 0.40, "output":  1.60},
    "gpt-4.1-nano": {"input": 0.10, "output":  0.40},
    "o3":           {"input":10.00, "output": 40.00},
    "o3-mini":      {"input": 1.10, "output":  4.40},
}

def get_model_class(model: str) -> str:
    """Return energy class for a model name (fuzzy match)."""
    m = model.lower().strip()
    # Direct override
    for key, cls in MODEL_OVERRIDES.items():
        if key in m:
            return cls
    # Heuristic
    if any(x in m for x in ["haiku", "mini", "nano", "flash", "small", "phi-"]):
        return "nano"
    if any(x in m for x in ["sonnet", "medium", "pro"]):
        return "medium"
    if any(x in m for x in ["opus", "large", "ultra", "o1", "o3", "4o", "gpt-4"]):
        return "large"
    if any(x in m for x in ["llama", "mistral", "qwen", "deepseek", "gemma", "phi", "orca"]):
        return "local"
    return "medium"  # safe default

def get_output_wh_per_m(model: str) -> float:
    cls = get_model_class(model)
    return MODEL_CLASSES.get(cls, MODEL_CLASSES["medium"])["output_wh_per_m"]

def get_input_wh_per_m(model: str) -> float:
    return get_output_wh_per_m(model) * INPUT_MULT

def estimate_cost(input_tokens, output_tokens, model, provider="unknown"):
    """Estimate cost in USD using public pricing tables."""
    m = model.lower()
    prices = None
    for key, p in {**ANTHROPIC_PRICES, **OPENAI_PRICES}.items():
        if key in m:
            prices = p
            break
    if not prices:
        # Rough defaults by provider
        if "anthropic" in provider.lower():
            prices = {"input": 3.00, "output": 15.00}
        elif "openai" in provider.lower():
            prices = {"input": 2.50, "output": 10.00}
        else:
            prices = {"input": 2.00, "output": 8.00}
    return (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000

# ── provider/datacenter resolution ───────────────────────────────────────────

PROVIDERS = TABLES["providers"]

def infer_provider(model: str, harness: str) -> str:
    m = model.lower()
    if any(x in m for x in ["claude", "anthropic"]):
        return "anthropic"
    if any(x in m for x in ["gpt", "o1", "o3", "codex"]):
        return "openai"
    if any(x in m for x in ["gemini", "gemma", "bard"]):
        return "google"
    if any(x in m for x in ["llama", "mistral", "qwen", "deepseek", "phi", "gemma", "orca"]):
        return "local"
    return "unknown"

def get_datacenter_info(provider: str, inference_geo: str = None) -> dict:
    p = PROVIDERS.get(provider) or PROVIDERS.get("anthropic")
    geo_map = p.get("inference_geo_map", {})
    key = inference_geo or p.get("default_region_key", "global")
    info = geo_map.get(key) or geo_map.get(list(geo_map.keys())[0] if geo_map else "global", {})
    return {
        "provider_label": p.get("label", provider),
        "cloud":          p.get("cloud", "Unknown"),
        "region":         info.get("region", "unknown"),
        "location_label": info.get("label", "Unknown"),
        "city":           info.get("city", "Unknown"),
        "renewable_claim":p.get("renewable_claim", "Not disclosed"),
        "pue":            p.get("pue", 1.2),
        "wue_ml_per_kwh": p.get("wue_ml_per_kwh", 1500),
    }

def get_carbon_intensity(region: str) -> float:
    ci = TABLES["grid_carbon_intensity_g_per_kwh"]
    return ci.get(region, ci.get("default", 300))

# ── environmental calculations ────────────────────────────────────────────────

def calc_env(input_tokens, output_tokens, model, provider="unknown", inference_geo=None):
    dc = get_datacenter_info(provider, inference_geo)
    pue = dc["pue"]
    wue = dc["wue_ml_per_kwh"]
    carbon_intensity = get_carbon_intensity(dc["region"])

    in_m  = input_tokens  / 1_000_000
    out_m = output_tokens / 1_000_000

    # Raw inference energy
    energy_input_wh  = get_input_wh_per_m(model)  * in_m
    energy_output_wh = get_output_wh_per_m(model) * out_m
    inference_wh = energy_input_wh + energy_output_wh

    # Apply PUE (datacenter overhead: cooling, networking, etc.)
    total_wh = inference_wh * pue

    # Carbon
    co2_g = total_wh * carbon_intensity / 1000  # kWh = Wh/1000

    # Water (direct cooling: WUE = liters per kWh)
    water_direct_ml = (total_wh / 1000) * wue  # wue is ml/kWh; total_wh/1000 converts Wh→kWh

    return {
        "datacenter": dc,
        "inference_wh": round(inference_wh, 4),
        "total_wh_with_pue": round(total_wh, 4),
        "carbon_intensity_g_per_kwh": carbon_intensity,
        "co2_g": round(co2_g, 4),
        "water_direct_ml": round(water_direct_ml, 2),
        "energy_breakdown": {
            "input_wh": round(energy_input_wh, 4),
            "output_wh": round(energy_output_wh, 4),
        },
    }

# ── equivalencies ─────────────────────────────────────────────────────────────

EQ = TABLES["equivalencies"]

def make_equivalencies(total_wh, co2_g, water_ml):
    phone_charges = total_wh / EQ["phone_charge_wh"]
    microwave_mins = total_wh / (EQ.get("microwave_1min_wh", 17))
    car_meters = (co2_g / EQ["car_co2_g_per_km"]) * 1000  # km → meters
    water_glasses = water_ml / EQ["water_glass_ml"]
    water_bottles = water_ml / EQ["water_bottle_ml"]
    tree_days = (co2_g / EQ.get("tree_absorbs_co2_g_per_yr", 22000)) * 365
    google_searches_equiv = total_wh / EQ.get("google_search_wh", 0.0003)

    return {
        "phone_charges":           round(phone_charges, 2),
        "microwave_minutes":       round(microwave_mins, 2),
        "car_driving_meters":      round(car_meters, 1),
        "water_glasses":           round(water_glasses, 2),
        "water_bottles":           round(water_bottles, 3),
        "tree_absorption_days":    round(tree_days, 2),
        "equivalent_google_searches": round(google_searches_equiv),
    }

# ── per-model enrichment ──────────────────────────────────────────────────────

def enrich_by_model(by_model: dict) -> list:
    results = []
    for model, stats in sorted(by_model.items(), key=lambda x: -(x[1].get("output_tokens", 0))):
        inp = stats.get("input_tokens", 0)
        out = stats.get("output_tokens", 0)
        provider = stats.get("provider", infer_provider(model, ""))
        if not provider or provider == "unknown":
            provider = infer_provider(model, "")

        env = calc_env(inp, out, model, provider)
        cost = stats.get("cost_usd", 0)
        if cost == 0:
            cost = estimate_cost(inp, out, model, provider)

        cache_read = stats.get("cache_read", 0)
        cache_eff = round(cache_read / inp, 3) if inp > 0 else 0

        results.append({
            "model":            model,
            "provider":         provider,
            "model_class":      get_model_class(model),
            "input_tokens":     inp,
            "output_tokens":    out,
            "cache_read":       cache_read,
            "cache_efficiency": cache_eff,
            "total_tokens":     inp + out,
            "cost_usd":         round(cost, 4),
            "energy_wh":        env["total_wh_with_pue"],
            "co2_g":            env["co2_g"],
            "water_ml":         env["water_direct_ml"],
            "datacenter":       env["datacenter"],
        })
    return results

# ── cache efficiency ──────────────────────────────────────────────────────────

def cache_metrics(totals):
    inp = totals.get("input_tokens", 0)
    cache_read = totals.get("cache_read", 0)
    cache_write = totals.get("cache_write", 0)
    if inp == 0:
        return {"hit_rate": 0, "tokens_saved": 0, "cost_saved_pct": 0}
    hit_rate = cache_read / inp
    # Cache hits save ~90% of input cost (Anthropic cache hit = 10% of input price)
    cost_saved_pct = hit_rate * 0.90
    return {
        "hit_rate":       round(hit_rate, 3),
        "cache_read":     cache_read,
        "cache_write":    cache_write,
        "cost_saved_pct": round(cost_saved_pct * 100, 1),
        "tokens_saved":   cache_read,
    }

# ── main enrichment ───────────────────────────────────────────────────────────

def enrich(data: dict) -> dict:
    agg = data.get("aggregated", {})
    totals = agg.get("totals", {})

    total_inp = totals.get("input_tokens", 0)
    total_out = totals.get("output_tokens", 0)
    total_cost = totals.get("cost_usd", 0)

    # Determine dominant model/provider
    by_model = agg.get("by_model", {})
    dominant_model = max(by_model, key=lambda m: by_model[m].get("output_tokens", 0)) if by_model else "unknown"
    dominant_provider = by_model.get(dominant_model, {}).get("provider", "unknown")
    if not dominant_provider or dominant_provider == "unknown":
        dominant_provider = infer_provider(dominant_model, "")

    # Total environmental impact
    env = calc_env(total_inp, total_out, dominant_model, dominant_provider)

    # Re-estimate cost if not present
    if total_cost == 0:
        total_cost = sum(
            estimate_cost(
                by_model[m].get("input_tokens", 0),
                by_model[m].get("output_tokens", 0),
                m,
                by_model[m].get("provider", dominant_provider)
            )
            for m in by_model
        )

    # Equivalencies
    equivs = make_equivalencies(env["total_wh_with_pue"], env["co2_g"], env["water_direct_ml"])

    # Per-model enriched
    enriched_models = enrich_by_model(by_model)

    # Cache metrics
    cache = cache_metrics(totals)

    # Timeline (carry through)
    timeline = agg.get("timeline", [])

    # By-harness summary
    by_harness = agg.get("by_harness", {})

    # Efficiency score (tokens per dollar)
    tok_per_dollar = ((total_inp + total_out) / total_cost) if total_cost > 0 else 0

    # Interesting derived stats
    days = data.get("days_analyzed", 30)
    avg_daily_tokens = (total_inp + total_out) / days if days > 0 else 0
    avg_daily_cost   = total_cost / days if days > 0 else 0

    return {
        "meta": {
            "days_analyzed":      data.get("days_analyzed", 30),
            "extraction_method":  data.get("extraction_method"),
            "detected_harnesses": data.get("detected_harnesses", []),
            "warnings":           data.get("warnings", []),
            "record_count":       data.get("record_count", 0),
        },
        "totals": {
            "input_tokens":   total_inp,
            "output_tokens":  total_out,
            "cache_read":     totals.get("cache_read", 0),
            "total_tokens":   total_inp + total_out,
            "cost_usd":       round(total_cost, 4),
        },
        "environmental": {
            "primary_datacenter": env["datacenter"],
            "energy_wh":          env["total_wh_with_pue"],
            "energy_kwh":         round(env["total_wh_with_pue"] / 1000, 6),
            "co2_g":              env["co2_g"],
            "co2_kg":             round(env["co2_g"] / 1000, 4),
            "water_direct_ml":    env["water_direct_ml"],
            "carbon_intensity_g_per_kwh": env["carbon_intensity_g_per_kwh"],
            "renewable_claim":    env["datacenter"]["renewable_claim"],
        },
        "equivalencies": equivs,
        "cache": cache,
        "efficiency": {
            "tokens_per_dollar":  round(tok_per_dollar),
            "avg_daily_tokens":   round(avg_daily_tokens),
            "avg_daily_cost_usd": round(avg_daily_cost, 4),
            "dominant_model":     dominant_model,
            "dominant_provider":  dominant_provider,
            "num_models_used":    len(by_model),
            "num_harnesses_used": len(by_harness),
        },
        "by_model":   enriched_models,
        "by_harness": {k: dict(v) for k, v in by_harness.items()},
        "timeline":   timeline,
    }

# ── entry point ───────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) > 1 and sys.argv[1] != "-":
        with open(sys.argv[1]) as f:
            raw = json.load(f)
    else:
        raw = json.load(sys.stdin)

    result = enrich(raw)
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    main()
