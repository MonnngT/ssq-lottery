"""Generator script: converts compact text format to word_data.py + JSON files.

Compact format (pipe-delimited): word|phonetic|meaning|collocation|frequency
"""

import json
import os
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
COMPACT_FILE = Path(__file__).parent / "word_data_compact.txt"


def parse_compact(filepath: str | Path) -> list[dict]:
    """Parse compact pipe-delimited word data into list of dicts."""
    words = []
    seen = set()
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split("|")
            if len(parts) < 4:
                continue

            word = parts[0].strip()
            if not word or word in seen:
                continue
            seen.add(word)

            phonetic = parts[1].strip() if parts[1].strip() else ""
            meaning = parts[2].strip() if len(parts) > 2 else ""
            collocation = parts[3].strip() if len(parts) > 3 else ""
            frequency = parts[4].strip() if len(parts) > 4 else "medium"

            words.append({
                "word": word,
                "phonetic": phonetic,
                "meaning": meaning,
                "collocations": collocation,
                "frequency": frequency,
            })

    return words


def generate_json(words: list[dict], level: str) -> None:
    """Generate JSON files from parsed words, organized by level and frequency."""
    os.makedirs(DATA_DIR, exist_ok=True)

    # Tag words with level
    for w in words:
        w["level"] = level

    # Separate by frequency
    high_freq = [w for w in words if w["frequency"] == "high"]
    medium_freq = [w for w in words if w["frequency"] == "medium"]
    low_freq = [w for w in words if w["frequency"] == "low"]

    # If no frequency tags found, auto-tag: first ~1/3 as high, next ~1/3 as medium
    if not high_freq and not medium_freq and not low_freq:
        all_sorted = sorted(words, key=lambda w: w["word"])
        for i, w in enumerate(all_sorted):
            if i < len(all_sorted) * 0.3:
                w["frequency"] = "high"
                high_freq.append(w)
            elif i < len(all_sorted) * 0.6:
                w["frequency"] = "medium"
                medium_freq.append(w)
            else:
                w["frequency"] = "low"
                low_freq.append(w)
    elif not high_freq:
        # Use first 30% of medium as high
        cutoff = max(1, len(words) // 3)
        for i, w in enumerate(words):
            if i < cutoff and w["frequency"] != "high":
                w["frequency"] = "high"
        high_freq = [w for w in words if w["frequency"] == "high"]
        medium_freq = [w for w in words if w["frequency"] == "medium"]

    # Full list (ordered high -> medium -> low)
    full_sorted = high_freq + medium_freq + low_freq

    # CET-4 lists
    outfile = DATA_DIR / f"{level}_full.json"
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(full_sorted, f, ensure_ascii=False, indent=2)

    high_out = DATA_DIR / f"{level}_high_freq.json"
    with open(high_out, "w", encoding="utf-8") as f:
        json.dump(high_freq, f, ensure_ascii=False, indent=2)

    core_out = DATA_DIR / f"{level}_core.json"
    core_words = high_freq[:min(500, len(high_freq))]
    with open(core_out, "w", encoding="utf-8") as f:
        json.dump(core_words, f, ensure_ascii=False, indent=2)

    print(f"  {level.upper()} Full: {len(full_sorted)} words")
    print(f"  {level.upper()} High Frequency: {len(high_freq)} words")
    print(f"  {level.upper()} Core: {len(core_words)} words")


def main():
    print("Parsing word data from compact format...")

    # Parse all words
    all_words = parse_compact(COMPACT_FILE)

    if not all_words:
        print("ERROR: No words parsed!")
        return

    # Split by level tag — words ending with _cet6 are CET-6
    cet4 = []
    cet6 = []
    for w in all_words:
        if w["word"].endswith("_cet6"):
            w["word"] = w["word"].replace("_cet6", "")
            cet6.append(w)
        else:
            cet4.append(w)

    print(f"\nParsed {len(cet4)} CET-4 words and {len(cet6)} CET-6 words")
    print("\nGenerating JSON files...")
    generate_json(cet4, "cet4")
    generate_json(cet6, "cet6")
    print("\nDone! JSON files generated successfully.")


if __name__ == "__main__":
    main()
