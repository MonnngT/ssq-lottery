"""Data models for 双色球 analysis."""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Tuple

RedBalls = Tuple[int, int, int, int, int, int]


class HotCold(Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


@dataclass
class Draw:
    issue: str
    date: str
    reds: RedBalls
    blue: int

    def __post_init__(self):
        assert len(self.reds) == 6, f"Expected 6 red balls, got {len(self.reds)}"
        assert len(set(self.reds)) == 6, "Red balls must be unique"
        assert all(1 <= n <= 33 for n in self.reds), "Red balls must be 1-33"
        assert 1 <= self.blue <= 16, "Blue ball must be 1-16"


@dataclass
class FrequencyResult:
    number: int
    count: int
    weighted_score: float
    percentage: float


@dataclass
class MissingResult:
    number: int
    current_missing: int
    average_missing: float
    max_missing: int
    missing_ratio: float


@dataclass
class HotColdResult:
    number: int
    classification: HotCold
    recent_appearances: int
    score: float


@dataclass
class ZoneResult:
    zone_id: int
    zone_range: Tuple[int, int]
    count_distribution: dict  # count_of_balls_in_zone -> frequency


@dataclass
class OddEvenResult:
    odd_count: int
    even_count: int
    frequency: int
    percentage: float


@dataclass
class ConsecutiveResult:
    pair_count: int
    frequency: int
    percentage: float


@dataclass
class SumResult:
    min_sum: int
    max_sum: int
    mean_sum: float
    common_low: int
    common_high: int


@dataclass
class Prediction:
    reds: RedBalls
    blue: int
    strategy_name: str
    confidence: str
    supporting_stats: dict = field(default_factory=dict)


@dataclass
class AnalysisReport:
    draw_count: int
    date_range: Tuple[str, str]
    red_frequency: list = field(default_factory=list)
    blue_frequency: list = field(default_factory=list)
    red_missing: list = field(default_factory=list)
    blue_missing: list = field(default_factory=list)
    hot_cold: list = field(default_factory=list)
    zone_distribution: list = field(default_factory=list)
    odd_even: list = field(default_factory=list)
    consecutive: list = field(default_factory=list)
    sum_stats: SumResult = None
