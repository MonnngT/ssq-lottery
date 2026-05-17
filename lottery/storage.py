"""Local JSON cache for historical lottery data."""

import json
import os
import time
from pathlib import Path
from .models import Draw, RedBalls


def _get_cache_dir() -> Path:
    base = os.environ.get("APPDATA", os.path.expanduser("~"))
    cache_dir = Path(base) / ".lottery_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_cache_path() -> Path:
    return _get_cache_dir() / "ssq_draws.json"


def save_draws(draws: list[Draw], filepath: Path = None) -> None:
    if filepath is None:
        filepath = get_cache_path()
    data = [{"issue": d.issue, "date": d.date, "reds": list(d.reds), "blue": d.blue} for d in draws]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({"count": len(data), "draws": data}, f, ensure_ascii=False, indent=2)


def load_draws(filepath: Path = None) -> list[Draw]:
    if filepath is None:
        filepath = get_cache_path()
    if not filepath.exists():
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        raw = json.load(f)
    draws = []
    for item in raw["draws"]:
        reds = tuple(sorted(item["reds"]))
        draws.append(Draw(issue=item["issue"], date=item["date"], reds=reds, blue=item["blue"]))
    return draws


def is_cache_stale(filepath: Path = None, max_age_hours: int = 24) -> bool:
    if filepath is None:
        filepath = get_cache_path()
    if not filepath.exists():
        return True
    age_seconds = time.time() - filepath.stat().st_mtime
    return age_seconds > max_age_hours * 3600


def merge_draws(existing: list[Draw], new: list[Draw]) -> list[Draw]:
    seen = {d.issue for d in existing}
    for d in new:
        if d.issue not in seen:
            existing.append(d)
            seen.add(d.issue)
    existing.sort(key=lambda d: d.issue)
    return existing
