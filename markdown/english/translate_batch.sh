#!/bin/bash
# Translates Telugu topic markdown files to English/Devanagari via Gemini CLI.
# Splits large files into shloka-chunks to avoid output-length truncation,
# then reassembles. Resumable: skips topic files whose output already exists.
# If QA (stray Telugu chars / shloka-count mismatch) fails, retries the whole
# file once before giving up and logging it to flagged_for_review.txt.
# Usage: ./translate_batch.sh <sarga-N> [topic_NN.md ...]
# If no topic files given, processes all topic_*.md in that sarga.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TELUGU_DIR="$PROJECT_ROOT/markdown/telugu"
ENGLISH_DIR="$PROJECT_ROOT/markdown/english"
PROMPT_FILE="$SCRIPT_DIR/translate_prompt.txt"
FLAGGED_LOG="$ENGLISH_DIR/flagged_for_review.txt"
USAGE_LOG="$ENGLISH_DIR/gemini_usage.jsonl"
CHUNK_SIZE="${CHUNK_SIZE:-4}"
MAX_CHUNK_RETRIES=2
MAX_FILE_ATTEMPTS=2

if [ -z "${GEMINI_API_KEY:-}" ]; then
  echo "ERROR: GEMINI_API_KEY is not set in this shell." >&2
  exit 1
fi

SARGA="$1"
shift
SRC_DIR="$TELUGU_DIR/$SARGA"
OUT_DIR="$ENGLISH_DIR/$SARGA"
mkdir -p "$OUT_DIR"

if [ "$#" -gt 0 ]; then
  FILES=("$@")
else
  FILES=($(cd "$SRC_DIR" && ls topic_*.md | sort))
fi

call_gemini() {
  local src="$1" out="$2"
  local attempt=1
  while [ $attempt -le $MAX_CHUNK_RETRIES ]; do
    if python3 "$SCRIPT_DIR/call_gemini.py" "$PROMPT_FILE" "$src" "$out" "$USAGE_LOG" 2>"$out.err"; then
      rm -f "$out.err"
      return 0
    fi
    echo "    attempt $attempt failed, retrying..." >&2
    attempt=$((attempt + 1))
  done
  return 1
}

# Attempts one full translate+assemble pass for a topic file.
# Writes result to $2 on success. Returns 1 on hard failure (a chunk never
# generated) or 2 on QA failure (stray Telugu chars / shloka count mismatch).
translate_file_once() {
  local src="$1" out="$2" sarga="$3" f="$4"
  local work_dir
  work_dir="$(mktemp -d)"
  local chunks=()
  while IFS= read -r line; do
    chunks+=("$line")
  done < <(python3 "$SCRIPT_DIR/split_shlokas.py" "$src" "$work_dir/chunks" "$CHUNK_SIZE" 2>"$work_dir/split.log")
  cat "$work_dir/split.log" >&2

  local failed=0
  : > "$work_dir/assembled.md"
  local i
  for i in "${!chunks[@]}"; do
    local chunk_src="${chunks[$i]}"
    local chunk_out="$work_dir/out_$(printf '%02d' "$i").md"
    echo "  chunk $((i+1))/${#chunks[@]} ..."
    if ! call_gemini "$chunk_src" "$chunk_out"; then
      echo "  FAILED chunk $((i+1)) of $sarga/$f" >&2
      cat "$chunk_out.err" 2>/dev/null >&2
      failed=1
      continue
    fi
    if [ "$i" -gt 0 ]; then
      # strip a leading duplicate level-1 heading from continuation chunks
      sed -i '' '1{/^# /d;}' "$chunk_out"
    fi
    cat "$chunk_out" >> "$work_dir/assembled.md"
    printf '\n' >> "$work_dir/assembled.md"
  done

  if [ "$failed" -eq 1 ]; then
    rm -rf "$work_dir"
    return 1
  fi

  mv "$work_dir/assembled.md" "$out"
  rm -rf "$work_dir"

  local qa_bad=0

  if python3 -c "
import sys
text = open('$out', encoding='utf-8').read()
sys.exit(0 if any('ఀ' <= ch <= '౿' for ch in text) else 1)
"; then
    echo "  QA: stray Telugu characters found in $sarga/$f" >&2
    qa_bad=1
  fi

  local src_count out_count
  src_count=$(grep -o "\*\*పదచ్ఛేదము" "$src" | wc -l | tr -d ' ')
  out_count=$(grep -c "^### Shloka:" "$out")
  if [ "$src_count" != "$out_count" ]; then
    echo "  QA: shloka count mismatch (source=$src_count output=$out_count) in $sarga/$f" >&2
    qa_bad=1
  fi

  [ "$qa_bad" -eq 1 ] && return 2
  return 0
}

for f in "${FILES[@]}"; do
  SRC="$SRC_DIR/$f"
  OUT="$OUT_DIR/$f"
  if [ ! -f "$SRC" ]; then
    echo "SKIP (missing): $SRC" >&2
    continue
  fi
  if [ -s "$OUT" ]; then
    echo "SKIP (already done): $SARGA/$f"
    continue
  fi

  echo "Translating $SARGA/$f ..."
  ATTEMPT=1
  STATUS=2
  while [ $ATTEMPT -le $MAX_FILE_ATTEMPTS ]; do
    rm -f "$OUT"
    if [ $ATTEMPT -gt 1 ]; then
      echo "  Retrying whole file (attempt $ATTEMPT) for $SARGA/$f ..."
    fi
    translate_file_once "$SRC" "$OUT" "$SARGA" "$f"
    STATUS=$?
    [ $STATUS -eq 0 ] && break
    ATTEMPT=$((ATTEMPT + 1))
  done

  case $STATUS in
    0)
      echo "  OK: $SARGA/$f"
      ;;
    1)
      echo "  FAILED (generation) after $MAX_FILE_ATTEMPTS attempts: $SARGA/$f" >&2
      rm -f "$OUT"
      echo "$SARGA/$f — generation failed after $MAX_FILE_ATTEMPTS attempts" >> "$FLAGGED_LOG"
      ;;
    2)
      echo "  FLAGGED (QA) after $MAX_FILE_ATTEMPTS attempts: $SARGA/$f" >&2
      echo "$SARGA/$f — QA issues persisted after $MAX_FILE_ATTEMPTS attempts (stray Telugu chars or shloka count mismatch)" >> "$FLAGGED_LOG"
      ;;
  esac
done

echo "Done with $SARGA."
