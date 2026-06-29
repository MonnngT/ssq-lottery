"""Flask web interface for 双色球 analysis and prediction."""

from flask import Flask, jsonify, request, render_template_string

try:
    from .predictor import STRATEGIES
except ImportError:
    from predictor import STRATEGIES

app = Flask(__name__)


def _fetch_draws():
    try:
        from .fetcher import fetch_draws
    except ImportError:
        from fetcher import fetch_draws
    return fetch_draws()


def _run_analysis(draws):
    try:
        from .analyzer import run_full_analysis
    except ImportError:
        from analyzer import run_full_analysis
    return run_full_analysis(draws)


def _generate(draws, strategy_name, count):
    try:
        from .predictor import generate_predictions
    except ImportError:
        from predictor import generate_predictions
    return generate_predictions(draws, strategy_name=strategy_name, count=count)


PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>双色球预测</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: -apple-system, "Microsoft YaHei", sans-serif; background: #0f0f1a; color: #e0e0e0; min-height: 100vh; }
  .container { max-width: 720px; margin: 0 auto; padding: 20px; }
  h1 { text-align: center; font-size: 1.8em; margin: 20px 0; color: #fff; }
  .card { background: #1a1a2e; border-radius: 12px; padding: 20px; margin: 16px 0; box-shadow: 0 2px 12px rgba(0,0,0,.3); }
  .controls { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
  select, input, button { padding: 10px 16px; border-radius: 8px; border: 1px solid #333; font-size: 15px; background: #16213e; color: #e0e0e0; cursor: pointer; }
  button { background: #e74c3c; border-color: #e74c3c; color: #fff; font-weight: bold; transition: .2s; }
  button:hover { background: #c0392b; }
  button:disabled { opacity: .5; cursor: not-allowed; }

  .balls { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; }
  .ball { width: 42px; height: 42px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 17px; color: #fff; }
  .ball.red { background: radial-gradient(circle at 35% 35%, #ff6b6b, #c0392b); }
  .ball.blue { background: radial-gradient(circle at 35% 35%, #5b9cf5, #1e3799); }

  .prediction-row { display: flex; align-items: center; gap: 16px; padding: 12px 0; border-bottom: 1px solid #2a2a3e; flex-wrap: wrap; }
  .prediction-row:last-child { border-bottom: none; }
  .pred-meta { font-size: .85em; color: #999; }
  .pred-meta span { display: block; }

  table { width: 100%; border-collapse: collapse; font-size: .9em; }
  th, td { padding: 6px 10px; text-align: center; border-bottom: 1px solid #2a2a3e; }
  th { color: #f39c12; font-weight: 600; }
  .tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: .75em; font-weight: bold; }
  .tag.hot { background: #c0392b; color: #fff; }
  .tag.warm { background: #e67e22; color: #fff; }
  .tag.cold { background: #2980b9; color: #fff; }

  details { margin: 10px 0; }
  summary { cursor: pointer; color: #f39c12; font-size: 1.1em; padding: 8px 0; }
  summary:hover { color: #e67e22; }
  .disclaimer { text-align: center; color: #666; font-size: .8em; margin: 20px 0; }
  .section-title { font-size: 1em; color: #f39c12; margin: 16px 0 8px; font-weight: bold; }

  .spinner { display: none; width: 20px; height: 20px; border: 3px solid #333; border-top: 3px solid #e74c3c; border-radius: 50%; animation: spin .6s linear infinite; }
  .spinner.show { display: inline-block; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="container">
  <h1>双色球预测</h1>

  <div class="card">
    <div class="controls">
      <select id="strategy">
        <option value="balanced">综合加权</option>
        <option value="hot">热号策略</option>
        <option value="cold">冷号策略</option>
        <option value="pattern">走势匹配</option>
        <option value="monte-carlo">蒙特卡洛</option>
      </select>
      <select id="count">
        <option value="1">1组</option>
        <option value="3" selected>3组</option>
        <option value="5">5组</option>
        <option value="10">10组</option>
      </select>
      <button id="predictBtn" onclick="generate()">生成预测</button>
      <div class="spinner" id="spinner"></div>
    </div>
  </div>

  <div class="card" id="resultBox" style="display:none;">
    <div id="resultContent"></div>
  </div>

  <div class="card" id="analysisBox">
    <details>
      <summary>查看统计分析</summary>
      <div id="analysisContent"></div>
    </details>
  </div>

  <div class="disclaimer">彩票开奖为随机事件，本工具仅提供统计分析，不保证中奖结果，请理性购彩。</div>
</div>

<script>
  function generate() {
    const btn = document.getElementById('predictBtn');
    const spinner = document.getElementById('spinner');
    const resultBox = document.getElementById('resultBox');
    btn.disabled = true;
    spinner.classList.add('show');

    const strategy = document.getElementById('strategy').value;
    const count = document.getElementById('count').value;

    fetch(`/api/predict?strategy=${strategy}&count=${count}`)
      .then(r => r.json())
      .then(data => {
        spinner.classList.remove('show');
        btn.disabled = false;
        resultBox.style.display = 'block';
        let html = '';
        data.predictions.forEach((p, i) => {
          html += '<div class="prediction-row">';
          html += '<div class="balls">';
          p.reds.forEach(r => { html += `<div class="ball red">${String(r).padStart(2,'0')}</div>`; });
          html += '</div>';
          html += '<div class="ball blue">' + String(p.blue).padStart(2,'0') + '</div>';
          html += '<div class="pred-meta"><span>' + p.strategy + '</span><span>' + p.confidence + '</span></div>';
          html += '</div>';
        });
        document.getElementById('resultContent').innerHTML = html;
      });

    // Also load analysis
    fetch('/api/analysis')
      .then(r => r.json())
      .then(data => {
        document.getElementById('analysisContent').innerHTML = data.html;
      });
  }

  // Load analysis on page load
  fetch('/api/analysis')
    .then(r => r.json())
    .then(data => {
      document.getElementById('analysisContent').innerHTML = data.html;
    });
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/api/predict")
def api_predict():
    strategy = request.args.get("strategy", "balanced")
    if strategy not in STRATEGIES:
        return jsonify({"error": f"Unknown strategy: {strategy}"}), 400

    try:
        count = int(request.args.get("count", 5))
    except (TypeError, ValueError):
        return jsonify({"error": "count must be an integer"}), 400

    if not 1 <= count <= 10:
        return jsonify({"error": "count must be between 1 and 10"}), 400

    draws = _fetch_draws()
    predictions = _generate(draws, strategy_name=strategy, count=count)

    result = []
    for p in predictions:
        result.append({
            "reds": list(p.reds),
            "blue": p.blue,
            "strategy": p.strategy_name,
            "confidence": p.confidence,
        })
    return {"predictions": result}


@app.route("/api/analysis")
def api_analysis():
    draws = _fetch_draws()
    report = _run_analysis(draws)

    hot_nums = [r.number for r in report.hot_cold if r.classification.value == "hot"]
    cold_nums = [r.number for r in report.hot_cold if r.classification.value == "cold"]
    s = report.sum_stats

    def freq_rows(freq_list, top=10):
        rows = ""
        for r in freq_list[:top]:
            rows += f"<tr><td>{r.number}</td><td>{r.count}</td><td>{r.percentage}%</td></tr>"
        return rows

    def missing_rows(miss_list, top=10):
        rows = ""
        for m in miss_list[:top]:
            rows += f"<tr><td>{m.number}</td><td>{m.current_missing}</td><td>{m.average_missing}</td><td>{m.max_missing}</td><td>{m.missing_ratio}</td></tr>"
        return rows

    def hotcold_tags(nums, cls):
        return " ".join(f'<span class="tag {cls}">{n}</span>' for n in nums[:15])

    oe_rows = ""
    for oe in report.odd_even:
        if oe.percentage > 0.5:
            oe_rows += f"<tr><td>{oe.odd_count}:{oe.even_count}</td><td>{oe.percentage}%</td></tr>"

    zone_rows = ""
    for z in report.zone_distribution:
        total_z = sum(z.count_distribution.values())
        parts = ", ".join(f"{k}球:{v}次({v / total_z * 100:.1f}%)" for k, v in sorted(z.count_distribution.items()))
        zone_rows += f"<tr><td>区间{z.zone_id} ({z.zone_range[0]}-{z.zone_range[1]})</td><td>{parts}</td></tr>"

    html = f"""
    <div class="section-title">数据范围: {report.date_range[1]} ~ {report.date_range[0]} | 共 {report.draw_count} 期</div>

    <div class="section-title">红球频率 TOP 10</div>
    <table><tr><th>号码</th><th>次数</th><th>占比</th></tr>{freq_rows(report.red_frequency)}</table>

    <div class="section-title">蓝球频率 TOP 5</div>
    <table><tr><th>号码</th><th>次数</th><th>占比</th></tr>{freq_rows(report.blue_frequency, 5)}</table>

    <div class="section-title">红球遗漏排行（最冷号码）</div>
    <table><tr><th>号码</th><th>当前遗漏</th><th>平均遗漏</th><th>最大遗漏</th><th>遗漏比</th></tr>{missing_rows(report.red_missing)}</table>

    <div class="section-title">冷热号</div>
    <p>热号: {hotcold_tags(hot_nums, 'hot')}</p>
    <p style="margin-top:6px">冷号: {hotcold_tags(cold_nums, 'cold')}</p>

    <div class="section-title">奇偶比</div>
    <table><tr><th>奇:偶</th><th>占比</th></tr>{oe_rows}</table>

    <div class="section-title">和值</div>
    <p>最小:{s.min_sum} | 最大:{s.max_sum} | 均值:{s.mean_sum} | 常见:{s.common_low}-{s.common_high}</p>

    <div class="section-title">区间分布</div>
    <table><tr><th>区间</th><th>分布</th></tr>{zone_rows}</table>
    """
    return {"html": html}


def _get_local_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("114.114.114.114", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def main():
    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    local_ip = _get_local_ip()
    print("双色球预测 Web 服务启动中...")
    print(f"  电脑访问: http://127.0.0.1:5000")
    print(f"  手机访问: http://{local_ip}:5000  (需同一WiFi)")
    print("按 Ctrl+C 停止服务")
    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # Also allow running directly via `python lottery/web.py`
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
