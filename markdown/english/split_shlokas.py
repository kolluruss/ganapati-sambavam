#!/usr/bin/env python3
"""Split a Telugu topic markdown file into chunks of N shlokas each.
A shloka boundary is the point right after a '**భావము**' section's
paragraph content ends (i.e. right before the next bold verse line, or EOF).
Prints chunk file paths, one per line, to stdout.
"""
import re
import sys
import os

def find_boundaries(text):
    boundaries = []
    for m in re.finditer(r'\*\*భావము', text):
        pos = m.end()
        if text[pos:pos + 2] == '**':
            # isolated format: "**భావము**" followed by plain-text content,
            # ending right before the next bold verse line.
            start = pos + 2
            next_bold = re.search(r'\n\*\*', text[start:])
            if next_bold:
                boundaries.append(start + next_bold.start())
            else:
                boundaries.append(len(text))
        else:
            # bundled format: "**భావము <content>**" all in one bold span;
            # the span's own closing ** is the boundary.
            close = text.find('**', pos)
            if close == -1:
                boundaries.append(len(text))
            else:
                boundaries.append(close + 2)
    return boundaries

def chunk_text(text, chunk_size):
    boundaries = find_boundaries(text)
    if not boundaries:
        return [text]
    chunks = []
    prev = 0
    for i in range(0, len(boundaries), chunk_size):
        group_end = boundaries[min(i + chunk_size, len(boundaries)) - 1]
        chunks.append(text[prev:group_end])
        prev = group_end
    if prev < len(text):
        chunks.append(text[prev:])
    return chunks, len(boundaries)

def main():
    src_path = sys.argv[1]
    out_dir = sys.argv[2]
    chunk_size = int(sys.argv[3]) if len(sys.argv) > 3 else 4

    text = open(src_path, encoding='utf-8').read()
    chunks, n_shlokas = chunk_text(text, chunk_size)

    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for idx, c in enumerate(chunks, 1):
        p = os.path.join(out_dir, f"chunk_{idx:02d}.md")
        with open(p, 'w', encoding='utf-8') as f:
            f.write(c)
        paths.append(p)

    print(f"# shlokas={n_shlokas} chunks={len(chunks)}", file=sys.stderr)
    for p in paths:
        print(p)

if __name__ == '__main__':
    main()
