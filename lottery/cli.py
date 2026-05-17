"""Command-line interface for 双色球 analysis and prediction."""

import argparse
import logging
import sys
import json
from datetime import datetime

from .fetcher import fetch_draws
from .analyzer import run_full_analysis, analyze_repeats, analyze_span, analyze_ac_value
from .predictor import generate_predictions, STRATEGIES

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DISCLAIMER = "彩票开奖为随机事件，本工具仅提供统计分析，不保证中奖结果，请理性购彩。"


def _print_report(report):
    """Pretty-print analysis report."""
    print(f"\n{'=' * 60}")
    print(f"  双色球统计分析报告")
    print(f"{'=' * 60}")
    print(f"  数据范围: {report.date_range[0]} ~ {report.date_range[1]}")
    print(f"  总期数:   {report.draw_count}")
    print()

    # Red frequency top 10
    print("  【红球频率 TOP 10】")
    print(f"  {'号码':<6}{'次数':<8}{'占比':<10}{'加权分'}")
    for r in report.red_frequency[:10]:
        print(f"  {r.number:<6}{r.count:<8}{r.percentage:<10}%{r.weighted_score:>8}")
    print()

    print("  【蓝球频率 TOP 5】")
    print(f"  {'号码':<6}{'次数':<8}{'占比'}")
    for b in report.blue_frequency[:5]:
        print(f"  {b.number:<6}{b.count:<8}{b.percentage}%")
    print()

    # Missing
    print("  【红球遗漏排行 — 最冷号码】")
    print(f"  {'号码':<6}{'当前遗漏':<10}{'平均遗漏':<10}{'最大遗漏':<10}{'遗漏比'}")
    for m in report.red_missing[:10]:
        print(f"  {m.number:<6}{m.current_missing:<10}{m.average_missing:<10}{m.max_missing:<10}{m.missing_ratio}")
    print()

    # Hot/Cold summary
    hot = [r for r in report.hot_cold if r.classification.value == "hot"]
    cold = [r for r in report.hot_cold if r.classification.value == "cold"]
    print(f"  【冷热号】 热号({len(hot)}个): {[r.number for r in hot]}")
    print(f"            冷号({len(cold)}个): {[r.number for r in cold]}")
    print()

    # Sum stats
    s = report.sum_stats
    print(f"  【和值】 最小:{s.min_sum}  最大:{s.max_sum}  均值:{s.mean_sum}  常见范围:{s.common_low}-{s.common_high}")
    print()

    # Odd/Even
    print("  【奇偶比分布】")
    for oe in report.odd_even:
        if oe.percentage > 0.5:
            print(f"    {oe.odd_count}:{oe.even_count}  → {oe.percentage}%")
    print()

    # Consecutive
    print("  【连号分布】")
    for c in report.consecutive:
        print(f"    {c.pair_count}对连号 → {c.percentage}%")
    print()

    # Zone
    print("  【区间分布】")
    for z in report.zone_distribution:
        total_z = sum(z.count_distribution.values())
        print(f"    区间{z.zone_id} ({z.zone_range[0]}-{z.zone_range[1]}): ", end="")
        parts = [f"{k}个球: {v}次({v / total_z * 100:.1f}%)" for k, v in sorted(z.count_distribution.items())]
        print(", ".join(parts))
    print()


def _print_predictions(predictions):
    """Pretty-print prediction results."""
    print(f"\n{'=' * 60}")
    print(f"  预测号码")
    print(f"{'=' * 60}")
    for i, p in enumerate(predictions, 1):
        reds_str = " ".join(f"{r:02d}" for r in p.reds)
        print(f"\n  #{i}  红球: {reds_str}   蓝球: {p.blue:02d}")
        print(f"  策略: {p.strategy_name}  |  {p.confidence}")
    print(f"\n  {DISCLAIMER}")
    print()


def _predictions_to_json(predictions) -> str:
    """Serialize predictions to JSON."""
    data = []
    for p in predictions:
        data.append({
            "reds": list(p.reds),
            "blue": p.blue,
            "strategy": p.strategy_name,
            "confidence": p.confidence,
            "stats": {k: (v if isinstance(v, (int, float, str)) else str(v)) for k, v in p.supporting_stats.items()},
        })
    return json.dumps(data, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="双色球彩票分析与预测工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"示例:\n  python -m lottery.cli --predict\n  python -m lottery.cli --fetch --analyze --predict\n\n{DISCLAIMER}",
    )
    parser.add_argument("--fetch", action="store_true", help="强制重新获取数据")
    parser.add_argument("--analyze", action="store_true", help="显示统计分析")
    parser.add_argument("--predict", action="store_true", help="生成预测号码")
    parser.add_argument("--strategy", choices=list(STRATEGIES), default="balanced", help="预测策略 (默认: balanced)")
    parser.add_argument("--count", type=int, default=5, help="生成预测数量 (默认: 5)")
    parser.add_argument("--no-cache", action="store_true", help="不使用缓存")
    parser.add_argument("--output", choices=["text", "json"], default="text", help="输出格式")
    parser.add_argument("--recent", type=int, default=0, help="仅分析最近N期")
    parser.add_argument("--weights", nargs=4, type=float, metavar=("FREQ", "MISS", "ZONE", "OE"),
                        help="综合策略权重 (频率 遗漏 区间 奇偶)")

    args = parser.parse_args()

    # Default: if no action specified, do predict
    if not args.fetch and not args.analyze and not args.predict:
        args.predict = True
        args.fetch = True  # Need data to predict

    # Step 1: Fetch data
    logger.info("正在获取历史数据...")
    try:
        draws = fetch_draws(force=args.fetch, use_cache=not args.no_cache)
    except Exception as e:
        logger.error("获取数据失败: %s", e)
        sys.exit(1)

    logger.info("共 %d 期数据", len(draws))
    if not draws:
        logger.error("没有可用数据")
        sys.exit(1)

    # Step 2: Analyze
    report = None
    if args.analyze or args.predict:
        recent_n = args.recent if args.recent > 0 else None
        report = run_full_analysis(draws, recent_n=recent_n)

    if args.analyze:
        _print_report(report)

    # Step 3: Predict
    if args.predict:
        kwargs = {}
        if args.strategy == "balanced" and args.weights:
            kwargs["weights"] = {
                "freq": args.weights[0],
                "missing": args.weights[1],
                "zone": args.weights[2],
                "oddeven": args.weights[3],
            }

        predictions = generate_predictions(draws, strategy_name=args.strategy, count=args.count, **kwargs)

        if args.output == "json":
            print(_predictions_to_json(predictions))
        else:
            _print_predictions(predictions)


if __name__ == "__main__":
    main()
