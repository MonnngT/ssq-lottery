"""Prediction strategies for 双色球."""

import random
from abc import ABC, abstractmethod
from collections import Counter, defaultdict

from .models import Draw, Prediction, RedBalls, AnalysisReport
from .analyzer import (
    analyze_frequency, analyze_missing, classify_hot_cold,
    RED_POOL, BLUE_POOL, ZONES,
)


class PredictionStrategy(ABC):
    name: str = "base"

    @abstractmethod
    def predict(self, draws: list[Draw], report: AnalysisReport | None = None) -> list[Prediction]:
        ...


# ── Hot Strategy ─────────────────────────────────────────────────────────────

class HotStrategy(PredictionStrategy):
    name = "hot"

    def __init__(self, window: int = 30):
        self.window = window

    def predict(self, draws: list[Draw], report: AnalysisReport | None = None) -> list[Prediction]:
        sample = draws[-self.window:]
        red_freq, blue_freq = analyze_frequency(sample)

        reds = tuple(sorted(r.number for r in red_freq[:6]))
        blue = blue_freq[0].number

        return [Prediction(
            reds=reds,
            blue=blue,
            strategy_name=self.name,
            confidence="基于最近热门号码",
            supporting_stats={"window": self.window, "top_reds": red_freq[:6], "top_blue": blue_freq[0]},
        )]


# ── Cold Strategy ────────────────────────────────────────────────────────────

class ColdStrategy(PredictionStrategy):
    name = "cold"

    def predict(self, draws: list[Draw], report: AnalysisReport | None = None) -> list[Prediction]:
        if report is None:
            from .analyzer import analyze_missing
            red_missing, blue_missing = analyze_missing(draws)
        else:
            red_missing = report.red_missing
            blue_missing = report.blue_missing

        reds = tuple(sorted(m.number for m in red_missing[:6]))
        blue = blue_missing[0].number

        return [Prediction(
            reds=reds,
            blue=blue,
            strategy_name=self.name,
            confidence="基于遗漏回补策略",
            supporting_stats={"top_missing_reds": red_missing[:6], "top_missing_blue": blue_missing[0]},
        )]


# ── Balanced Strategy (Default) ──────────────────────────────────────────────

class BalancedStrategy(PredictionStrategy):
    name = "balanced"

    def __init__(self, weights: dict = None):
        self.weights = weights or {"freq": 0.30, "missing": 0.25, "zone": 0.25, "oddeven": 0.20}

    def predict(self, draws: list[Draw], report: AnalysisReport | None = None) -> list[Prediction]:
        if report is None:
            from .analyzer import run_full_analysis
            report = run_full_analysis(draws)

        n = len(draws)

        # Normalize frequency scores to [0, 1]
        red_freq_map = {r.number: r.weighted_score for r in report.red_frequency}
        max_freq = max(red_freq_map.values()) if red_freq_map else 1
        freq_score = {num: red_freq_map.get(num, 0) / max_freq for num in RED_POOL}

        # Missing scores: prefer slightly overdue numbers
        red_miss_map = {m.number: m.missing_ratio for m in report.red_missing}
        miss_score = {}
        for num in RED_POOL:
            ratio = red_miss_map.get(num, 0)
            # Highest score for ratio around 1.5-2.0, lower for very late or very frequent
            if ratio < 0.5:
                miss_score[num] = 0.3  # appeared recently
            elif ratio < 1.5:
                miss_score[num] = ratio / 2.0
            elif ratio < 3.0:
                miss_score[num] = 1.0 - (ratio - 1.5) / 3.0
            else:
                miss_score[num] = 0.5  # too cold

        # Zone balance: target recent zone distribution
        recent_zone_counts = defaultdict(int)
        for d in draws[-30:]:
            for zid, lo, hi in ZONES:
                recent_zone_counts[zid] += sum(1 for r in d.reds if lo <= r <= hi)
        total_zone = sum(recent_zone_counts.values()) or 1
        zone_target = {zid: recent_zone_counts[zid] / total_zone for zid in [1, 2, 3]}

        # Odd/even: prefer numbers that help maintain 3:3 balance
        odd_even_target = 0.5  # 3/6 = 50% odd

        # Composite scoring
        scores = {}
        for num in RED_POOL:
            zid = 1 if num <= 11 else 2 if num <= 22 else 3
            zscore = zone_target.get(zid, 0.33)
            oescore = 1.0 - abs((num % 2) - odd_even_target) * 2  # closer to 50% parity = higher score
            scores[num] = (
                self.weights["freq"] * freq_score[num]
                + self.weights["missing"] * miss_score[num]
                + self.weights["zone"] * zscore
                + self.weights["oddeven"] * oescore
            )

        ranked = sorted(scores, key=scores.get, reverse=True)

        candidates = ranked[:9]  # pick from top 9 for variety
        predictions = []
        for combo_idx in range(5):
            if combo_idx == 0:
                reds = tuple(sorted(ranked[:6]))
            else:
                random.shuffle(candidates)
                reds = tuple(sorted(candidates[:6]))
            reds = self._validate_reds(reds, draws)
            blue = self._pick_blue(draws)
            predictions.append(Prediction(
                reds=reds,
                blue=blue,
                strategy_name=self.name,
                confidence=f"综合加权预测 #{combo_idx + 1}",
                supporting_stats={"composite_scores": {n: round(scores[n], 4) for n in reds}},
            ))

        return predictions

    def _validate_reds(self, reds: RedBalls, draws: list[Draw]) -> RedBalls:
        """Ensure the combination meets reasonable constraints."""
        # Check odd/even ratio is between 2:4 and 4:2
        odd = sum(1 for r in reds if r % 2 == 1)
        if odd < 2 or odd > 4:
            # Too imbalanced, try to fix
            ranked_all = sorted(RED_POOL, key=lambda n: random.random())
            for alt in ranked_all:
                if alt not in reds:
                    # Replace the worst fitting number
                    candidates = list(reds)
                    candidates.sort(key=lambda r: abs((r % 2) * 2 - 1))
                    if odd < 2:
                        # Need more odd numbers, replace an even
                        for i, r in enumerate(candidates):
                            if r % 2 == 0:
                                candidates[i] = alt if alt % 2 == 1 else alt
                                break
                    else:
                        for i, r in enumerate(candidates):
                            if r % 2 == 1:
                                candidates[i] = alt if alt % 2 == 0 else alt
                                break
                    reds = tuple(sorted(candidates))
                    break

        # Check sum is in reasonable range (80-150)
        s = sum(reds)
        ranked_all = sorted(RED_POOL, key=lambda n: random.random())
        if s < 80:
            new = list(reds)
            new.sort()
            for alt in ranked_all:
                if alt not in new and alt > new[-1]:
                    new[0] = alt
                    break
            reds = tuple(sorted(new))
        elif s > 150:
            new = list(reds)
            new.sort()
            for alt in ranked_all:
                if alt not in new and alt < new[0]:
                    new[-1] = alt
                    break
            reds = tuple(sorted(new))

        return reds

    def _pick_blue(self, draws: list[Draw]) -> int:
        blue_count = Counter(d.blue for d in draws[-50:])
        # Weight by recency
        scores = defaultdict(float)
        for i in range(16):
            scores[i + 1] = blue_count.get(i + 1, 0)
        return max(scores, key=scores.get)


# ── Pattern Match Strategy ───────────────────────────────────────────────────

class PatternMatchStrategy(PredictionStrategy):
    name = "pattern"

    def __init__(self, lookback: int = 5):
        self.lookback = lookback

    def predict(self, draws: list[Draw], report: AnalysisReport | None = None) -> list[Prediction]:
        if len(draws) < self.lookback + 2:
            return []

        # Build feature vectors for each draw
        def feature(d: Draw) -> list:
            vec = [0] * 33
            for r in d.reds:
                vec[r - 1] = 1
            odd = sum(1 for r in d.reds if r % 2)
            vec.extend([odd / 6, sum(d.reds) / 183, (d.reds[-1] - d.reds[0]) / 32])
            return vec

        # Build recent pattern from last lookback draws
        recent_pattern = []
        for d in draws[-self.lookback:]:
            recent_pattern.extend(feature(d))

        # Slide window across history to find most similar pattern
        best_sim = -1
        best_idx = -1
        for i in range(len(draws) - self.lookback * 2):
            hist_pattern = []
            for j in range(self.lookback):
                hist_pattern.extend(feature(draws[i + j]))
            # Cosine similarity
            dot = sum(a * b for a, b in zip(recent_pattern, hist_pattern))
            norm1 = sum(a * a for a in recent_pattern) ** 0.5
            norm2 = sum(a * a for a in hist_pattern) ** 0.5
            sim = dot / (norm1 * norm2) if norm1 and norm2 else 0
            if sim > best_sim:
                best_sim = sim
                best_idx = i + self.lookback  # The draw that followed

        if best_idx < 0 or best_idx >= len(draws):
            return []

        matched = draws[best_idx]
        return [Prediction(
            reds=matched.reds,
            blue=matched.blue,
            strategy_name=self.name,
            confidence=f"历史走势匹配 (相似度: {best_sim:.4f}, 参考期号: {matched.issue})",
            supporting_stats={"similarity": round(best_sim, 4), "matched_issue": matched.issue},
        )]


# ── Monte Carlo Strategy ─────────────────────────────────────────────────────

class MonteCarloStrategy(PredictionStrategy):
    name = "monte-carlo"

    def __init__(self, simulations: int = 10000):
        self.simulations = simulations

    def predict(self, draws: list[Draw], report: AnalysisReport | None = None) -> list[Prediction]:
        # Build weighted distribution from recent frequency
        red_weights = defaultdict(float)
        blue_weights = defaultdict(float)

        alpha = 0.97
        n = len(draws)
        for idx, d in enumerate(draws):
            w = alpha ** (n - idx)
            for r in d.reds:
                red_weights[r] += w
            blue_weights[d.blue] += w

        red_pop = list(RED_POOL)
        blue_pop = list(BLUE_POOL)
        rw = [red_weights[i] for i in red_pop]
        bw = [blue_weights[i] for i in blue_pop]

        # Run simulations
        combo_counter = Counter()
        blue_counter = Counter()

        for _ in range(self.simulations):
            reds = tuple(sorted(random.choices(red_pop, weights=rw, k=6)))
            # Ensure uniqueness by resampling if duplicate
            if len(set(reds)) < 6:
                while len(set(reds)) < 6:
                    reds = tuple(sorted(random.choices(red_pop, weights=rw, k=6)))
            blue = random.choices(blue_pop, weights=bw, k=1)[0]
            combo_counter[reds] += 1
            blue_counter[blue] += 1

        predictions = []
        for (reds, cnt), _ in zip(combo_counter.most_common(5), range(5)):
            blue = blue_counter.most_common(1)[0][0]
            predictions.append(Prediction(
                reds=reds,
                blue=blue,
                strategy_name=self.name,
                confidence=f"蒙特卡洛模拟 {self.simulations}次, 出现{cnt}次 ({cnt / self.simulations * 100:.2f}%)",
                supporting_stats={"frequency": cnt, "total_sims": self.simulations},
            ))

        return predictions


# ── Factory ──────────────────────────────────────────────────────────────────

STRATEGIES = {
    "hot": HotStrategy,
    "cold": ColdStrategy,
    "balanced": BalancedStrategy,
    "pattern": PatternMatchStrategy,
    "monte-carlo": MonteCarloStrategy,
    "montecarlo": MonteCarloStrategy,
}


def generate_predictions(draws: list[Draw], strategy_name: str = "balanced", count: int = 5, **kwargs) -> list[Prediction]:
    """Factory: generate predictions using the named strategy."""
    cls = STRATEGIES.get(strategy_name)
    if cls is None:
        raise ValueError(f"Unknown strategy: {strategy_name}. Available: {list(STRATEGIES)}")

    strategy = cls(**kwargs)
    predictions = strategy.predict(draws)
    return predictions[:count]
