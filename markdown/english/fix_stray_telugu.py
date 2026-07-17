#!/usr/bin/env python3
"""Fix stray Telugu-script runs left inside translated English/Devanagari
topic files. The translation model occasionally fails to transliterate a rare
or complex Sanskrit conjunct and leaves the original Telugu glyphs in place
mid-word (e.g. 'पక్ష్माऽऽకారमिलिन्दबृन्दमिलितौ'). Since Telugu and Devanagari
are both systematic Brahmic scripts, these runs can be algorithmically
transliterated rather than requiring a full re-translation.

Usage:
  fix_stray_telugu.py <file.md> [file2.md ...]
  fix_stray_telugu.py --flagged   # process every file in flagged_for_review.txt

For each file: finds contiguous runs of Telugu-block characters, converts each
run to Devanagari in place, and reports whether the file is now clean (no
stray Telugu chars, shloka count matches). In --flagged mode, files that are
now clean are removed from flagged_for_review.txt; files still failing (e.g.
due to shloka-count mismatch, which this script cannot fix) are left listed.
"""
import re
import sys
import os

from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FLAGGED_LOG = os.path.join(SCRIPT_DIR, "flagged_for_review.txt")

TELUGU_RUN = re.compile(r'[ఀ-౿]+')


def fix_text(text):
    return TELUGU_RUN.sub(
        lambda m: transliterate(m.group(0), sanscript.TELUGU, sanscript.DEVANAGARI),
        text,
    )


def has_stray_telugu(text):
    return bool(TELUGU_RUN.search(text))


def shloka_count_ok(telugu_src_path, out_text):
    if not telugu_src_path or not os.path.exists(telugu_src_path):
        return True  # can't check without the source; don't block on it
    src_text = open(telugu_src_path, encoding='utf-8').read()
    src_count = len(re.findall(r'\*\*పదచ్ఛేదము', src_text))
    out_count = len(re.findall(r'^### Shloka:', out_text, re.MULTILINE))
    return src_count == out_count


def telugu_src_for(out_path):
    # <...>/english/sarga-N/topic_NN.md -> <...>/telugu/sarga-N/topic_NN.md
    abs_path = os.path.abspath(out_path)
    parts = abs_path.split(os.sep)
    if 'english' not in parts:
        return None
    idx = len(parts) - 1 - parts[::-1].index('english')
    parts[idx] = 'telugu'
    return os.sep.join(parts)


def process(path):
    text = open(path, encoding='utf-8').read()
    fixed = fix_text(text)
    changed = fixed != text
    if changed:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(fixed)

    still_stray = has_stray_telugu(fixed)
    count_ok = shloka_count_ok(telugu_src_for(path), fixed)
    clean = not still_stray and count_ok

    if not changed and clean:
        print(f"  OK (no stray chars found): {path}")
    elif clean:
        print(f"  FIXED: {path}")
    else:
        reasons = []
        if still_stray:
            reasons.append("stray Telugu chars remain")
        if not count_ok:
            reasons.append("shloka count mismatch")
        print(f"  STILL FLAGGED ({', '.join(reasons)}): {path}")
    return clean


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)

    if sys.argv[1] == '--flagged':
        if not os.path.exists(FLAGGED_LOG):
            print("No flagged_for_review.txt found; nothing to do.")
            return
        entries = [l.rstrip('\n') for l in open(FLAGGED_LOG, encoding='utf-8') if l.strip()]
        remaining = []
        for entry in entries:
            rel = entry.split(' — ')[0].strip()
            path = os.path.join(SCRIPT_DIR, rel)
            if not os.path.exists(path):
                print(f"  SKIP (missing): {path}")
                remaining.append(entry)
                continue
            clean = process(path)
            if not clean:
                remaining.append(entry)
        with open(FLAGGED_LOG, 'w', encoding='utf-8') as f:
            for entry in remaining:
                f.write(entry + '\n')
        print(f"\n{len(entries) - len(remaining)} file(s) fixed, {len(remaining)} still flagged.")
    else:
        for path in sys.argv[1:]:
            process(path)


if __name__ == '__main__':
    main()
