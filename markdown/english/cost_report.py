#!/usr/bin/env python3
"""Summarize Gemini API cost from gemini_usage.jsonl.
Usage: cost_report.py [usage_log_file]
"""
import json
import sys

PRICING = {
    # per 1M tokens, paid tier, USD
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "gemini-3.1-flash-lite": {"input": 0.25, "output": 1.50},
    "gemini-3-flash-preview": {"input": 0.50, "output": 3.00},
    "gemini-3.5-flash": {"input": 1.50, "output": 9.00},
}

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "gemini_usage.jsonl"
    totals = {}
    call_count = 0
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                model = rec.get("model", "unknown")
                t = totals.setdefault(model, {"input": 0, "output": 0, "calls": 0})
                t["input"] += rec.get("prompt_tokens", 0)
                t["output"] += rec.get("output_tokens", 0)
                t["calls"] += 1
                call_count += 1
    except FileNotFoundError:
        print(f"No usage log found at {path}")
        return

    grand_total = 0.0
    for model, t in totals.items():
        price = PRICING.get(model)
        print(f"Model: {model}")
        print(f"  Calls: {t['calls']}")
        print(f"  Input tokens:  {t['input']:,}")
        print(f"  Output tokens: {t['output']:,}")
        if price:
            cost = (t["input"] / 1_000_000 * price["input"]) + (t["output"] / 1_000_000 * price["output"])
            print(f"  Estimated cost: ${cost:.4f}")
            grand_total += cost
        else:
            print("  (no pricing known for this model)")
        print()

    print(f"Total calls: {call_count}")
    print(f"TOTAL ESTIMATED COST: ${grand_total:.4f}")

if __name__ == "__main__":
    main()
