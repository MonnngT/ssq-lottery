"""Statistical analysis engine for 双色球 data."""

from collections import Counter, defaultdict
from .models import (
    Draw, FrequencyResult, MissingResult, HotColdResult, HotCold,
    ZoneResult, OddEvenResult, ConsecutiveResult, SumResult, AnalysisReport,
)

RED_POOL = range(1, 34)
BLUE_POOL = range(1, 17)
ZONES = [(1, 1, 11), (2, 12, 22), (3, 23, 33)]


# ── Frequency ────────────────────────────────────────────────────────────────

def analyze_frequency(draws: list[Draw], recent_n: int = None) -> tuple[list[FrequencyResult], list[FrequencyResult]]:
    """Compute absolute and weighted frequency for red and blue balls."""
    sample = draws if recent_n is None else draws[-recent_n:]
    total = len(sample)

    red_count = Counter()
    blue_count = Counter()
    red_weighted = defaultdict(float)
    blue_weighted = defaultdict(float)

    alpha = 0.95
    for idx, d in enumerate(sample):
        w = alpha ** (total - idx)
        for r in d.reds:
            red_count[r] += 1
            red_weighted[r] += w
        blue_count[d.blue] += 1
        blue_weighted[d.blue] += w

    red_freq = [FrequencyResult(num, red_count[num], round(red_weighted[num], 3), round(red_count[num] / total * 100, 2)) for num in RED_POOL]
    blue_freq = [FrequencyResult(num, blue_count[num], round(blue_weighted[num], 3), round(blue_count[num] / total * 100, 2)) for num in BLUE_POOL]
    red_freq.sort(key=lambda x: x.count, reverse=True)
    blue_freq.sort(key=lambda x: x.count, reverse=True)
    return red_freq, blue_freq


# ── Missing / Loss ───────────────────────────────────────────────────────────

def analyze_missing(draws: list[Draw]) -> tuple[list[MissingResult], list[MissingResult]]:
    """Compute missing/gap statistics for each number."""
    total = len(draws)

    def compute(pool, get_nums):
        results = []
        for num in pool:
            positions = [i for i, d in enumerate(draws) if num in get_nums(d)]
            if not positions:
                results.append(MissingResult(num, total, total, total, 1.0))
                continue
            gaps = []
            prev = -1
            for pos in positions:
                gaps.append(pos - prev - 1)
                prev = pos
            current = total - 1 - positions[-1]
            avg = sum(gaps) / len(gaps) if gaps else current
            max_gap = max(gaps) if gaps else current
            ratio = current / avg if avg > 0 else current
            results.append(MissingResult(num, current, round(avg, 2), max_gap, round(ratio, 2)))
        results.sort(key=lambda x: x.missing_ratio, reverse=True)
        return results

    red_missing = compute(RED_POOL, lambda d: d.reds)
    blue_missing = compute(BLUE_POOL, lambda d: [d.blue])
    return red_missing, blue_missing


# ── Hot / Cold ───────────────────────────────────────────────────────────────

def classify_hot_cold(draws: list[Draw], hot_window: int = 10, cold_threshold: int = 15) -> list[HotColdResult]:
    """Classify each red ball as hot, warm, or cold."""
    results = []
    recent = draws[-hot_window:]
    total = len(draws)

    for num in RED_POOL:
        recent_count = sum(1 for d in recent if num in d.reds)
        # Find last appearance
        last_app = max((i for i, d in enumerate(draws) if num in d.reds), default=-1)
        current_missing = total - 1 - last_app if last_app >= 0 else total

        if recent_count >= 3:
            cls = HotCold.HOT
            score = recent_count
        elif current_missing >= cold_threshold:
            cls = HotCold.COLD
            score = -current_missing
        else:
            cls = HotCold.WARM
            score = recent_count - current_missing * 0.1

        results.append(HotColdResult(num, cls, recent_count, round(score, 2)))

    results.sort(key=lambda x: x.score, reverse=True)
    return results


# ── Zone Distribution ────────────────────────────────────────────────────────

def analyze_zone_distribution(draws: list[Draw]) -> list[ZoneResult]:
    """Analyze how red balls distribute across 3 zones."""
    results = []
    for zid, lo, hi in ZONES:
        dist = Counter()
        for d in draws:
            count = sum(1 for r in d.reds if lo <= r <= hi)
            dist[count] += 1
        results.append(ZoneResult(zid, (lo, hi), dict(dist)))
    return results


# ── Odd/Even ─────────────────────────────────────────────────────────────────

def analyze_odd_even(draws: list[Draw]) -> list[OddEvenResult]:
    """Tabulate odd/even ratio frequency across all draws."""
    n = len(draws)
    counter = Counter()
    for d in draws:
        odd = sum(1 for r in d.reds if r % 2 == 1)
        counter[odd] += 1

    results = []
    for odd in range(7):
        cnt = counter[odd]
        results.append(OddEvenResult(odd, 6 - odd, cnt, round(cnt / n * 100, 2)))
    return results


# ── Consecutive ──────────────────────────────────────────────────────────────

def analyze_consecutive(draws: list[Draw]) -> list[ConsecutiveResult]:
    """Count consecutive number pairs per draw."""
    n = len(draws)
    counter = Counter()
    for d in draws:
        pairs = sum(1 for i in range(5) if d.reds[i + 1] - d.reds[i] == 1)
        counter[pairs] += 1

    results = []
    for pc in sorted(counter):
        results.append(ConsecutiveResult(pc, counter[pc], round(counter[pc] / n * 100, 2)))
    return results


# ── Sum ──────────────────────────────────────────────────────────────────────

def analyze_sum(draws: list[Draw]) -> SumResult:
    """Analyze sum of red balls statistics."""
    sums = [sum(d.reds) for d in draws]
    sorted_sums = sorted(sums)
    mean_s = sum(sums) / len(sums)
    # Common range: 25th to 75th percentile
    idx_lo = len(sorted_sums) // 4
    idx_hi = len(sorted_sums) * 3 // 4
    return SumResult(
        min_sum=min(sums),
        max_sum=max(sums),
        mean_sum=round(mean_s, 1),
        common_low=sorted_sums[idx_lo],
        common_high=sorted_sums[idx_hi],
    )


# ── Repeats ──────────────────────────────────────────────────────────────────

def analyze_repeats(draws: list[Draw]) -> dict:
    """Analyze how often numbers repeat from the previous draw."""
    counter = Counter()
    for i in range(1, len(draws)):
        prev_reds = set(draws[i - 1].reds)
        curr_reds = set(draws[i].reds)
        repeats = len(prev_reds & curr_reds)
        counter[repeats] += 1
    return {"per_draw": dict(sorted(counter.items())), "total": sum(k * v for k, v in counter.items()) / max(sum(counter.values()), 1)}


# ── Span ─────────────────────────────────────────────────────────────────────

def analyze_span(draws: list[Draw]) -> dict:
    """Analyze span (max - min) of red balls."""
    spans = [d.reds[-1] - d.reds[0] for d in draws]
    return {
        "min": min(spans),
        "max": max(spans),
        "mean": round(sum(spans) / len(spans), 1),
        "most_common_range": f"{sorted(spans)[len(spans)//4]}-{sorted(spans)[len(spans)*3//4]}",
    }


# ── AC Value ─────────────────────────────────────────────────────────────────

def analyze_ac_value(draws: list[Draw]) -> dict:
    """Arithmetic Complexity: measure diversity of differences between numbers."""
    def ac(reds):
        diffs = set()
        for i in range(6):
            for j in range(i + 1, 6):
                diffs.add(abs(reds[j] - reds[i]))
        return len(diffs) - 5  # subtract (r-1) where r=6

    ac_vals = [ac(d.reds) for d in draws]
    counter = Counter(ac_vals)
    return {
        "min": min(ac_vals),
        "max": max(ac_vals),
        "mean": round(sum(ac_vals) / len(ac_vals), 2),
        "distribution": dict(sorted(counter.items())),
    }


# ── Full Report ──────────────────────────────────────────────────────────────

def run_full_analysis(draws: list[Draw], recent_n: int = None) -> AnalysisReport:
    """Run all analysis methods and return a consolidated report."""
    sample = draws if recent_n is None else draws[-recent_n:]
    if not sample:
        raise ValueError("No draws available for analysis")

    red_freq, blue_freq = analyze_frequency(sample)
    red_missing, blue_missing = analyze_missing(sample)
    hot_cold = classify_hot_cold(sample)
    zones = analyze_zone_distribution(sample)
    odd_even = analyze_odd_even(sample)
    consecutive = analyze_consecutive(sample)
    sum_stats = analyze_sum(sample)

    return AnalysisReport(
        draw_count=len(sample),
        date_range=(sample[0].date, sample[-1].date),
        red_frequency=red_freq,
        blue_frequency=blue_freq,
        red_missing=red_missing,
        blue_missing=blue_missing,
        hot_cold=hot_cold,
        zone_distribution=zones,
        odd_even=odd_even,
        consecutive=consecutive,
        sum_stats=sum_stats,
    )
