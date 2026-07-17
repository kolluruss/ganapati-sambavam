#!/usr/bin/env python3
"""Direct Gemini REST API call (no CLI/agentic overhead).
Usage: call_gemini.py <prompt_file> <content_file> <output_file> <usage_log_file>
Writes the model's text output to output_file, and appends a JSON line with
token usage to usage_log_file. Exits non-zero on failure (output_file will not
be written in that case).

Throttled to stay within the Gemini API free tier for gemini-3.1-flash-lite
(15 requests/minute, ~250K tokens/minute, 1000 requests/day). Enforces a
rolling-window request cap and retries with backoff on HTTP 429.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error

MODEL = "gemini-3.1-flash-lite"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

# Free-tier limits for gemini-3.1-flash-lite are 15 RPM / 500 RPD (confirmed
# from the API's own RESOURCE_EXHAUSTED error, which cites a hard 500/day cap —
# the previously assumed 1000 RPD was wrong and let real usage blow past quota).
# Stay comfortably under both with margin for retries across the batch.
RPM_LIMIT = 10
RPD_LIMIT = 460
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RATE_STATE_FILE = os.path.join(SCRIPT_DIR, ".rate_limit_state.jsonl")
MAX_429_RETRIES = 5


def _prune_and_load_timestamps():
    now = time.time()
    today_start = now - (now % 86400)
    minute_ts = []
    day_ts = []
    if os.path.exists(RATE_STATE_FILE):
        with open(RATE_STATE_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    t = float(line)
                except ValueError:
                    continue
                if now - t < 60:
                    minute_ts.append(t)
                if t >= today_start:
                    day_ts.append(t)
    return minute_ts, day_ts


def throttle():
    minute_ts, day_ts = _prune_and_load_timestamps()

    if len(day_ts) >= RPD_LIMIT:
        sys.stderr.write(f"Daily request cap ({RPD_LIMIT}) reached. Refusing to call API until tomorrow.\n")
        sys.exit(2)

    if len(minute_ts) >= RPM_LIMIT:
        oldest = min(minute_ts)
        wait = 60 - (time.time() - oldest) + 0.5
        if wait > 0:
            sys.stderr.write(f"  (throttling: waiting {wait:.1f}s to stay under {RPM_LIMIT} req/min)\n")
            time.sleep(wait)


def record_request():
    with open(RATE_STATE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{time.time()}\n")
    # opportunistically trim the file so it doesn't grow forever
    minute_ts, day_ts = _prune_and_load_timestamps()
    with open(RATE_STATE_FILE, "w", encoding="utf-8") as f:
        for t in day_ts:
            f.write(f"{t}\n")


def call_with_retries(req):
    attempt = 0
    while True:
        throttle()
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                record_request()
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            record_request()
            body = e.read().decode("utf-8", "ignore")
            if e.code == 429 and attempt < MAX_429_RETRIES:
                attempt += 1
                backoff = min(60, 5 * (2 ** attempt))
                sys.stderr.write(f"  HTTP 429 (rate limited), backing off {backoff}s (attempt {attempt}/{MAX_429_RETRIES})\n")
                time.sleep(backoff)
                continue
            sys.stderr.write(f"HTTP {e.code}: {body}\n")
            sys.exit(1)


def main():
    prompt_file, content_file, output_file, usage_log_file = sys.argv[1:5]
    api_key = os.environ["GEMINI_API_KEY"]

    prompt = open(prompt_file, encoding="utf-8").read()
    content = open(content_file, encoding="utf-8").read()
    full_text = prompt + "\n\n" + content

    body = {
        "contents": [{"parts": [{"text": full_text}]}],
        "generationConfig": {
            "temperature": 0.2,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    req = urllib.request.Request(
        f"{API_URL}?key={api_key}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        data = call_with_retries(req)
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"Request failed: {e}\n")
        sys.exit(1)

    candidates = data.get("candidates", [])
    if not candidates or "content" not in candidates[0]:
        sys.stderr.write(f"No content in response: {json.dumps(data)[:2000]}\n")
        sys.exit(1)

    parts = candidates[0]["content"].get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    if not text.strip():
        sys.stderr.write(f"Empty text in response: {json.dumps(data)[:2000]}\n")
        sys.exit(1)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)

    usage = data.get("usageMetadata", {})
    candidates_tokens = usage.get("candidatesTokenCount", 0)
    thoughts_tokens = usage.get("thoughtsTokenCount", 0)
    usage_record = {
        "model": MODEL,
        "prompt_tokens": usage.get("promptTokenCount", 0),
        "output_tokens": candidates_tokens + thoughts_tokens,
        "candidates_tokens": candidates_tokens,
        "thoughts_tokens": thoughts_tokens,
        "total_tokens": usage.get("totalTokenCount", 0),
        "content_file": content_file,
    }
    with open(usage_log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(usage_record) + "\n")

if __name__ == "__main__":
    main()
