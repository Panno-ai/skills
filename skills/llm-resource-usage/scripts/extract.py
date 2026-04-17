#!/usr/bin/env python3
"""
llm-resource-usage/scripts/extract.py

Extracts token usage from local harness files.
Strategy:
  1. Try tokscale --json (covers 18+ harnesses natively)
  2. Fall back to direct Claude Code JSONL parsing
  3. Fall back to direct OpenCode JSON parsing
  4. Fall back to direct Goose SQLite parsing

Outputs a single JSON blob to stdout.
"""

import json
import os
import sys
import subprocess
import glob
import re
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

# ── helpers ──────────────────────────────────────────────────────────────────

def expand(p):
    return Path(p).expanduser()

def safe_load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None

def safe_load_jsonl(path):
    rows = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        pass
    except Exception:
        pass
    return rows

# ── tokscale ─────────────────────────────────────────────────────────────────

def try_tokscale(days=30):
    """
    Run `tokscale --json --days N` and return parsed output, or None.
    tokscale outputs a JSON object with totals + per-day/per-model breakdown.
    """
    for cmd in ["tokscale", "~/.cargo/bin/tokscale"]:
        full = str(expand(cmd))
        try:
            result = subprocess.run(
                [full, "--json", f"--days={days}"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                return {"source": "tokscale", "raw": data}
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            continue
    return None

def normalize_tokscale(raw):
    """
    Normalize tokscale JSON into our standard schema.
    tokscale schema (inferred from docs/source): varies by version.
    We handle the most common shapes.
    """
    records = []
    data = raw.get("raw", raw)

    # tokscale may output an array of daily records or a summary object
    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict):
        # Try common keys
        entries = (
            data.get("records") or
            data.get("sessions") or
            data.get("data") or
            []
        )
        # Also check for a flat top-level breakdown
        if not entries and "total" in data:
            # Single summary — synthesize one record
            t = data.get("total", {})
            entries = [{
                "date": datetime.now(timezone.utc).date().isoformat(),
                "provider": "unknown",
                "model": t.get("model", "unknown"),
                "input_tokens": t.get("input_tokens", 0),
                "output_tokens": t.get("output_tokens", 0),
                "cache_read": t.get("cache_read", 0),
                "cache_write": t.get("cache_write", 0),
                "cost_usd": t.get("cost", 0),
                "harness": t.get("harness", "unknown"),
            }]
    else:
        entries = []

    for e in entries:
        if not isinstance(e, dict):
            continue
        records.append({
            "date":          e.get("date", ""),
            "harness":       e.get("harness") or e.get("source") or "unknown",
            "provider":      e.get("provider") or e.get("providerID") or "unknown",
            "model":         e.get("model") or e.get("modelID") or "unknown",
            "input_tokens":  int(e.get("input_tokens")  or e.get("prompt_tokens")  or e.get("tokens", {}).get("input", 0)  or 0),
            "output_tokens": int(e.get("output_tokens") or e.get("completion_tokens") or e.get("tokens", {}).get("output", 0) or 0),
            "cache_read":    int(e.get("cache_read")    or e.get("tokens", {}).get("cache", {}).get("read", 0)  or 0),
            "cache_write":   int(e.get("cache_write")   or e.get("tokens", {}).get("cache", {}).get("write", 0) or 0),
            "reasoning_tokens": int(e.get("reasoning_tokens") or e.get("tokens", {}).get("reasoning", 0) or 0),
            "cost_usd":      float(e.get("cost_usd") or e.get("cost") or 0),
        })
    return records

# ── Claude Code fallback ──────────────────────────────────────────────────────

def parse_claude_code(days=30):
    """Parse ~/.claude/projects/**/*.jsonl for usage data."""
    base = expand("~/.claude/projects")
    if not base.exists():
        return []

    cutoff_ts = None
    if days:
        cutoff_ts = datetime.now(timezone.utc).timestamp() - days * 86400

    records = []
    for jsonl_file in base.rglob("*.jsonl"):
        # Skip non-session files
        if jsonl_file.stat().st_size == 0:
            continue
        for row in safe_load_jsonl(jsonl_file):
            if row.get("type") != "assistant":
                continue
            msg = row.get("message", {})
            usage = msg.get("usage", {})
            if not usage:
                continue

            ts = row.get("timestamp") or row.get("time", {}).get("created")
            if ts and cutoff_ts:
                try:
                    t = float(ts) / 1000 if float(ts) > 1e10 else float(ts)
                    if t < cutoff_ts:
                        continue
                except (ValueError, TypeError):
                    pass

            date_str = ""
            if ts:
                try:
                    t = float(ts) / 1000 if float(ts) > 1e10 else float(ts)
                    date_str = datetime.fromtimestamp(t, tz=timezone.utc).date().isoformat()
                except Exception:
                    pass

            model = msg.get("model", "unknown")
            records.append({
                "date":           date_str,
                "harness":        "claude_code",
                "provider":       "anthropic",
                "model":          model,
                "input_tokens":   int(usage.get("input_tokens", 0)),
                "output_tokens":  int(usage.get("output_tokens", 0)),
                "cache_read":     int(usage.get("cache_read_input_tokens", 0)),
                "cache_write":    int(usage.get("cache_creation_input_tokens", 0)),
                "reasoning_tokens": 0,
                "cost_usd":       0.0,  # calculated later
            })
    return records

# ── OpenCode fallback ─────────────────────────────────────────────────────────

def parse_opencode(days=30):
    """
    Parse ~/.local/share/opencode/storage/message/**/*.json
    Each file is a single message JSON with tokens breakdown.
    """
    base_env = os.environ.get("OPENCODE_DATA_DIR")
    base = expand(base_env) if base_env else expand("~/.local/share/opencode")
    msg_dir = base / "storage" / "message"

    if not msg_dir.exists():
        return []

    cutoff_ts = None
    if days:
        cutoff_ts = datetime.now(timezone.utc).timestamp() - days * 86400

    records = []
    for json_file in msg_dir.rglob("*.json"):
        data = safe_load_json(json_file)
        if not data or data.get("role") != "assistant":
            continue

        tokens = data.get("tokens", {})
        if not tokens:
            continue

        ts_ms = (data.get("time") or {}).get("created", 0)
        ts = ts_ms / 1000 if ts_ms > 1e10 else ts_ms

        if cutoff_ts and ts and ts < cutoff_ts:
            continue

        date_str = ""
        if ts:
            try:
                date_str = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
            except Exception:
                pass

        cache = tokens.get("cache", {})
        records.append({
            "date":           date_str,
            "harness":        "opencode",
            "provider":       data.get("providerID", "unknown"),
            "model":          data.get("modelID", "unknown"),
            "input_tokens":   int(tokens.get("input", 0)),
            "output_tokens":  int(tokens.get("output", 0)),
            "cache_read":     int(cache.get("read", 0)),
            "cache_write":    int(cache.get("write", 0)),
            "reasoning_tokens": int(tokens.get("reasoning", 0)),
            "cost_usd":       0.0,
        })
    return records

# ── Goose fallback ────────────────────────────────────────────────────────────

def parse_goose(days=30):
    """
    Parse ~/.local/share/goose/sessions/sessions.db (SQLite, v1.10+)
    Falls back to legacy .jsonl files.
    """
    db_path = expand("~/.local/share/goose/sessions/sessions.db")
    if not db_path.exists():
        return _parse_goose_jsonl(days)

    cutoff_ts = None
    if days:
        cutoff_ts = datetime.now(timezone.utc).timestamp() - days * 86400

    records = []
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        # Goose DB schema may vary — try common column names
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {r[0] for r in cur.fetchall()}

        if "messages" in tables:
            cur.execute("SELECT role, model, metadata, created_at FROM messages WHERE role='assistant'")
            for role, model, meta_raw, created_at in cur.fetchall():
                ts = 0
                if isinstance(created_at, (int, float)):
                    ts = float(created_at)
                elif isinstance(created_at, str):
                    try:
                        ts = datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
                    except Exception:
                        pass

                if cutoff_ts and ts and ts < cutoff_ts:
                    continue

                meta = {}
                if meta_raw:
                    try:
                        meta = json.loads(meta_raw)
                    except Exception:
                        pass

                usage = meta.get("usage", {})
                if not usage:
                    continue

                date_str = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat() if ts else ""
                records.append({
                    "date":           date_str,
                    "harness":        "goose",
                    "provider":       meta.get("provider", "unknown"),
                    "model":          model or "unknown",
                    "input_tokens":   int(usage.get("input_tokens", 0)),
                    "output_tokens":  int(usage.get("output_tokens", 0)),
                    "cache_read":     0,
                    "cache_write":    0,
                    "reasoning_tokens": 0,
                    "cost_usd":       0.0,
                })
        conn.close()
    except Exception:
        pass
    return records

def _parse_goose_jsonl(days):
    base = expand("~/.local/share/goose/sessions")
    if not base.exists():
        return []
    cutoff_ts = None
    if days:
        cutoff_ts = datetime.now(timezone.utc).timestamp() - days * 86400
    records = []
    for f in base.glob("*.jsonl"):
        for row in safe_load_jsonl(f):
            if row.get("role") != "assistant":
                continue
            usage = row.get("usage", {}) or (row.get("metadata") or {}).get("usage", {})
            if not usage:
                continue
            ts = row.get("created_at", 0) or row.get("timestamp", 0)
            if cutoff_ts and ts and float(ts) < cutoff_ts:
                continue
            date_str = ""
            if ts:
                try:
                    date_str = datetime.fromtimestamp(float(ts), tz=timezone.utc).date().isoformat()
                except Exception:
                    pass
            records.append({
                "date": date_str, "harness": "goose",
                "provider": row.get("provider", "unknown"),
                "model": row.get("model", "unknown"),
                "input_tokens": int(usage.get("input_tokens", 0)),
                "output_tokens": int(usage.get("output_tokens", 0)),
                "cache_read": 0, "cache_write": 0, "reasoning_tokens": 0, "cost_usd": 0.0,
            })
    return records

# ── OpenClaw fallback ─────────────────────────────────────────────────────────

def parse_openclaw(days=30):
    """
    Parse ~/.openclaw/agents/**/*.jsonl and *.jsonl.reset.*
    Looking for messages with usage.input / usage.output fields.
    """
    base = expand("~/.openclaw/agents")
    if not base.exists():
        return []

    cutoff_ts = None
    if days:
        cutoff_ts = datetime.now(timezone.utc).timestamp() - days * 86400

    records = []
    # Collect both active and reset files (bug workaround #42032)
    patterns = ["**/*.jsonl", "**/*.jsonl.reset.*"]
    seen_files = set()
    for pattern in patterns:
        for f in base.glob(pattern):
            if str(f) in seen_files:
                continue
            seen_files.add(str(f))
            for row in safe_load_jsonl(f):
                # Look for message entries with usage
                usage = None
                if "usage" in row and isinstance(row["usage"], dict):
                    usage = row["usage"]
                elif row.get("type") == "assistant" and "message" in row:
                    usage = row["message"].get("usage")

                if not usage:
                    continue

                ts = row.get("timestamp") or row.get("time") or 0
                if cutoff_ts and ts:
                    try:
                        t = float(ts) / 1000 if float(ts) > 1e10 else float(ts)
                        if t < cutoff_ts:
                            continue
                    except (ValueError, TypeError):
                        pass

                date_str = ""
                if ts:
                    try:
                        t = float(ts) / 1000 if float(ts) > 1e10 else float(ts)
                        date_str = datetime.fromtimestamp(t, tz=timezone.utc).date().isoformat()
                    except Exception:
                        pass

                records.append({
                    "date":     date_str,
                    "harness":  "openclaw",
                    "provider": row.get("provider") or "anthropic",
                    "model":    row.get("model") or "unknown",
                    "input_tokens":  int(usage.get("input", 0)),
                    "output_tokens": int(usage.get("output", 0)),
                    "cache_read":    int(usage.get("cacheRead", 0)),
                    "cache_write":   int(usage.get("cacheWrite", 0)),
                    "reasoning_tokens": 0,
                    "cost_usd": float((row.get("cost") or {}).get("total", 0)),
                })
    return records

# ── aggregation ───────────────────────────────────────────────────────────────

def aggregate(records):
    """Aggregate records into totals + per-day + per-model breakdowns."""
    totals = defaultdict(int)
    totals["cost_usd"] = 0.0

    by_date = defaultdict(lambda: defaultdict(int))
    by_model = defaultdict(lambda: defaultdict(int))
    by_harness = defaultdict(lambda: defaultdict(int))
    by_provider = defaultdict(lambda: defaultdict(int))
    timeline = []

    for r in records:
        for key in ["input_tokens", "output_tokens", "cache_read", "cache_write", "reasoning_tokens"]:
            totals[key] += r[key]
        totals["cost_usd"] += r["cost_usd"]
        totals["total_tokens"] = totals["input_tokens"] + totals["output_tokens"]

        d = r["date"] or "unknown"
        m = r["model"] or "unknown"
        h = r["harness"] or "unknown"
        p = r["provider"] or "unknown"

        for key in ["input_tokens", "output_tokens", "cache_read", "cache_write"]:
            by_date[d][key] += r[key]
            by_model[m][key] += r[key]
            by_harness[h][key] += r[key]
            by_provider[p][key] += r[key]
        by_date[d]["cost_usd"] += r["cost_usd"]
        by_model[m]["cost_usd"] += r["cost_usd"]
        by_harness[h]["cost_usd"] += r["cost_usd"]
        by_provider[p]["cost_usd"] += r["cost_usd"]
        by_model[m]["provider"] = p

    # Build sorted timeline
    for date in sorted(by_date.keys()):
        d = by_date[date]
        timeline.append({
            "date": date,
            "input_tokens": d["input_tokens"],
            "output_tokens": d["output_tokens"],
            "cache_read": d["cache_read"],
            "total_tokens": d["input_tokens"] + d["output_tokens"],
            "cost_usd": round(d["cost_usd"], 6),
        })

    return {
        "totals":      dict(totals),
        "by_date":     {k: dict(v) for k, v in by_date.items()},
        "by_model":    {k: dict(v) for k, v in by_model.items()},
        "by_harness":  {k: dict(v) for k, v in by_harness.items()},
        "by_provider": {k: dict(v) for k, v in by_provider.items()},
        "timeline":    timeline,
    }

# ── main ──────────────────────────────────────────────────────────────────────

def detect_harnesses():
    checks = {
        "claude_code": expand("~/.claude/projects").exists(),
        "opencode":    (expand("~/.local/share/opencode/storage").exists()
                        or (os.environ.get("OPENCODE_DATA_DIR") and
                            (expand(os.environ["OPENCODE_DATA_DIR"]) / "storage").exists())),
        "openclaw":    expand("~/.openclaw/agents").exists(),
        "pi":          expand("~/.pi/agent/sessions").exists(),
        "goose":       (expand("~/.local/share/goose/sessions/sessions.db").exists()
                        or expand("~/.local/share/goose/sessions").exists()),
        "tokscale":    any(
            Path(p).exists() for p in [
                "/usr/local/bin/tokscale",
                str(expand("~/.cargo/bin/tokscale")),
                "/usr/bin/tokscale",
            ]
        ),
    }
    return {k: v for k, v in checks.items() if v}

def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30

    detected = detect_harnesses()
    records = []
    extraction_method = "none"
    warnings = []

    # Strategy 1: tokscale
    ts_result = try_tokscale(days)
    if ts_result:
        records = normalize_tokscale(ts_result)
        extraction_method = "tokscale"
    else:
        # Strategy 2: direct file parsing
        if detected.get("claude_code"):
            r = parse_claude_code(days)
            records.extend(r)
            if r:
                extraction_method = "direct_files"

        if detected.get("opencode"):
            r = parse_opencode(days)
            records.extend(r)
            if r:
                extraction_method = "direct_files"

        if detected.get("openclaw"):
            r = parse_openclaw(days)
            records.extend(r)
            if r:
                extraction_method = "direct_files"

        if detected.get("goose"):
            r = parse_goose(days)
            records.extend(r)
            if r:
                extraction_method = "direct_files"

        if not detected.get("tokscale"):
            warnings.append(
                "tokscale not found — install from https://github.com/junhoyeo/tokscale "
                "for support across 18+ harnesses (Cursor, Codex, Gemini CLI, Amp, etc.)"
            )

    agg = aggregate(records)

    output = {
        "extraction_method": extraction_method,
        "days_analyzed": days,
        "detected_harnesses": list(detected.keys()),
        "record_count": len(records),
        "warnings": warnings,
        "aggregated": agg,
        "raw_records": records,  # kept for per-session detail if needed
    }

    print(json.dumps(output, indent=2, default=str))

if __name__ == "__main__":
    main()
