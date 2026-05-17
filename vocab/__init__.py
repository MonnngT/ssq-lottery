"""CET-4/6 Vocabulary Package"""

import json
import os
import random
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

WORD_LISTS = {
    "cet4_full": {"file": "cet4_full.json", "label": "四级完整词表", "level": "cet4"},
    "cet4_high_freq": {"file": "cet4_high_freq.json", "label": "四级高频词汇", "level": "cet4"},
    "cet4_core": {"file": "cet4_core.json", "label": "四级核心词汇", "level": "cet4"},
    "cet6_full": {"file": "cet6_full.json", "label": "六级完整词表", "level": "cet6"},
    "cet6_high_freq": {"file": "cet6_high_freq.json", "label": "六级高频词汇", "level": "cet6"},
}


def load_words(list_name: str) -> list[dict]:
    """Load a word list by name. Returns list of word dicts."""
    if list_name not in WORD_LISTS:
        raise ValueError(f"Unknown word list: {list_name}. Available: {list(WORD_LISTS.keys())}")

    filepath = DATA_DIR / WORD_LISTS[list_name]["file"]
    if not filepath.exists():
        raise FileNotFoundError(
            f"Word list file not found: {filepath}. Run 'python -m vocab.builder' first."
        )

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def get_list_info() -> dict:
    """Get metadata about all available word lists."""
    info = {}
    for name, meta in WORD_LISTS.items():
        filepath = DATA_DIR / meta["file"]
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                words = json.load(f)
            info[name] = {**meta, "count": len(words)}
        else:
            info[name] = {**meta, "count": 0}
    return info


def sample_words(list_name: str, count: int = 10, seed: int | None = None) -> list[dict]:
    """Get random sample of words from a list."""
    words = load_words(list_name)
    if seed is not None:
        random.seed(seed)
    return random.sample(words, min(count, len(words)))


def daily_words(list_name: str, count: int = 10) -> list[dict]:
    """Get daily word recommendation based on today's date as seed."""
    from datetime import date
    today = date.today().toordinal()
    return sample_words(list_name, count, seed=today)
