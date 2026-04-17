#!/usr/bin/env python3
"""
llm-resource-usage/scripts/run.py

One-shot runner: extract + enrich in a single call.
Outputs the final enriched JSON that Claude reads and visualizes.

Usage:
  python run.py [days=30]
"""
import sys
import json
import subprocess
from pathlib import Path

SCRIPTS = Path(__file__).parent

def main():
    days = sys.argv[1] if len(sys.argv) > 1 else "30"

    # Run extract.py
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "extract.py"), days],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(json.dumps({"error": "extract failed", "stderr": result.stderr}))
        sys.exit(1)

    extracted = json.loads(result.stdout)

    # Run enrich.py
    result2 = subprocess.run(
        [sys.executable, str(SCRIPTS / "enrich.py")],
        input=result.stdout,
        capture_output=True, text=True
    )
    if result2.returncode != 0:
        print(json.dumps({"error": "enrich failed", "stderr": result2.stderr, "extracted": extracted}))
        sys.exit(1)

    print(result2.stdout)

if __name__ == "__main__":
    main()
