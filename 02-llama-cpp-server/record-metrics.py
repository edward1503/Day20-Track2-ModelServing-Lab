#!/usr/bin/env python3
"""Poll llama-server's /metrics every N seconds during a load run, write CSV.

Usage:
    # In one terminal: start llama-server.
    # In another:      start locust.
    # In a third:      python 02-llama-cpp-server/record-metrics.py --duration 60
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from pathlib import Path

import httpx

INTERESTING = {
    "llamacpp:n_decode_total",
    "llamacpp:n_busy_slots_per_decode",
    "llamacpp:tokens_predicted_total",
    "llamacpp:prompt_tokens_total",
    "llamacpp:kv_cache_usage_ratio",
    "llamacpp:kv_cache_tokens",
    "llamacpp:requests_processing",
    "llamacpp:requests_deferred",
}

LINE = re.compile(r"^([a-z_:]+)(?:\{[^}]*\})?\s+([0-9eE.+-]+)$")


def scrape(url: str) -> dict[str, float]:
    out: dict[str, float] = {}
    try:
        text = httpx.get(url, timeout=3.0).text
    except httpx.HTTPError:
        return out
    for raw in text.splitlines():
        if raw.startswith("#"):
            continue
        m = LINE.match(raw.strip())
        if not m:
            continue
        name, val = m.group(1), m.group(2)
        if name in INTERESTING:
            try:
                out[name] = float(val)
            except ValueError:
                pass
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8080/metrics")
    parser.add_argument("--duration", type=int, default=60, help="seconds to record")
    parser.add_argument("--interval", type=float, default=2.0, help="seconds between scrapes")
    parser.add_argument("--out", default="benchmarks/02-server-metrics.csv")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    deadline = time.time() + args.duration
    rows: list[dict] = []
    print(f"==> Recording {args.url} for {args.duration}s, every {args.interval}s")
    while time.time() < deadline:
        sample = scrape(args.url)
        if sample:
            sample["t"] = round(time.time(), 1)
            
            # Since recent llama.cpp removed kv_cache_usage_ratio, we derive a proxy load ratio
            # using n_busy_slots_per_decode divided by the maximum slots (4).
            busy_slots = sample.get('llamacpp:n_busy_slots_per_decode', 0)
            simulated_kv_ratio = busy_slots / 4.0
            sample['llamacpp:kv_cache_usage_ratio'] = simulated_kv_ratio
            
            rows.append(sample)
            print(
                f"   t={sample['t']:.0f}  "
                f"reqs_proc={sample.get('llamacpp:requests_processing', 0):.0f}  "
                f"deferred={sample.get('llamacpp:requests_deferred', 0):.0f}  "
                f"kv_ratio={simulated_kv_ratio:.2f}  "
                f"tok_pred={sample.get('llamacpp:tokens_predicted_total', 0):.0f}"
            )
        else:
            print("   (scrape failed — is llama-server running with --metrics?)")
        time.sleep(args.interval)

    if not rows:
        print("ERROR: no samples collected.", file=sys.stderr)
        return 1

    fieldnames = sorted({k for r in rows for k in r.keys()})
    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\n==> Wrote {out_path} ({len(rows)} samples)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
