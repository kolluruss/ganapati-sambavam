import os
import re
import yaml
from pathlib import Path

BASE = Path("telugu")
YAML_PATH = BASE / "meta_data" / "chapter_topics.yaml"

with open(YAML_PATH, encoding="utf-8") as f:
    data = yaml.safe_load(f)

def read_shloka(path: Path) -> str:
    """Return shloka content with the top ## heading stripped."""
    text = path.read_text(encoding="utf-8").strip()
    lines = text.split("\n")
    # Drop first line if it's a ## heading
    if lines and lines[0].startswith("##"):
        lines = lines[1:]
    return "\n".join(lines).strip()

def get_shloka_num(filename: str):
    """Extract integer shloka number from filenames like '1.5.md'."""
    m = re.match(r"^\d+\.(\d+)\.md$", filename)
    return int(m.group(1)) if m else None

for sarga in data["sargas"]:
    sarga_num = sarga["number"]
    sarga_dir = BASE / f"sarga-{sarga_num}"

    if not sarga_dir.exists():
        print(f"  SKIP (dir missing): {sarga_dir}")
        continue

    # Collect all shloka files → {shloka_int: Path}
    shloka_files: dict[int, Path] = {}
    for fname in os.listdir(sarga_dir):
        n = get_shloka_num(fname)
        if n is not None:
            shloka_files[n] = sarga_dir / fname

    if not shloka_files:
        print(f"  SKIP (no shloka files): sarga-{sarga_num}")
        continue

    topics = sarga["topics"]

    # Build shloka→topic mapping from YAML ranges
    shloka_to_topic: dict[int, int] = {}
    for topic in topics:
        start = topic["shloka_range"]["start"]
        end = topic["shloka_range"]["end"]
        for i in range(start, end + 1):
            shloka_to_topic[i] = topic["number"]

    # Assign any gap shlokas to the preceding topic
    last_topic = topics[0]["number"]
    for num in sorted(shloka_files.keys()):
        if num in shloka_to_topic:
            last_topic = shloka_to_topic[num]
        else:
            shloka_to_topic[num] = last_topic

    # Group shloka numbers by topic (preserving order)
    topic_shlokas: dict[int, list[int]] = {t["number"]: [] for t in topics}
    for num in sorted(shloka_files.keys()):
        t = shloka_to_topic[num]
        topic_shlokas.setdefault(t, []).append(num)

    print(f"\nSarga {sarga_num}: {sarga['name']}")

    # Create one file per topic
    for topic in topics:
        t_num = topic["number"]
        t_name = topic["name"]
        t_desc = topic["description"]
        t_start = topic["shloka_range"]["start"]
        t_end = topic["shloka_range"]["end"]
        nums = topic_shlokas.get(t_num, [])

        lines = [
            f"# {t_name}",
            "",
            f"**శ్లోకాల పరిధి:** {t_start} – {t_end}",
            "",
            t_desc,
            "",
            "---",
            "",
        ]

        for num in nums:
            lines.append(f"## {sarga_num}.{num}")
            lines.append("")
            lines.append(read_shloka(shloka_files[num]))
            lines.append("")
            lines.append("---")
            lines.append("")

        out_name = f"topic_{t_num:02d}.md"
        out_path = sarga_dir / out_name
        out_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"  {out_name}  ({len(nums)} shlokas, {t_start}–{t_end})")

    # Delete individual shloka files
    for fpath in shloka_files.values():
        fpath.unlink()

    print(f"  Deleted {len(shloka_files)} individual shloka files")

print("\nDone.")
