"""双色球预测 — Streamlit Web App"""

import streamlit as st
from lottery.fetcher import fetch_draws
from lottery.analyzer import run_full_analysis
from lottery.predictor import generate_predictions, STRATEGIES

st.set_page_config(
    page_title="双色球预测",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Style ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .stButton > button {
    width: 100%; background: #e74c3c; color: #fff; border: none; font-size: 18px;
    font-weight: bold; border-radius: 10px; padding: 12px;
  }
  .stButton > button:hover { background: #c0392b; }
  .ball-red {
    display: inline-block; width: 44px; height: 44px; border-radius: 50%;
    background: linear-gradient(135deg, #ff6b6b, #c0392b);
    color: #fff; text-align: center; line-height: 44px; font-weight: bold;
    font-size: 18px; margin: 3px;
  }
  .ball-blue {
    display: inline-block; width: 44px; height: 44px; border-radius: 50%;
    background: linear-gradient(135deg, #5b9cf5, #1e3799);
    color: #fff; text-align: center; line-height: 44px; font-weight: bold;
    font-size: 18px; margin: 3px;
  }
  .pred-card {
    background: #1a1a2e; border-radius: 12px; padding: 16px; margin: 8px 0;
    color: #e0e0e0;
  }
  .disclaimer {
    text-align: center; color: #666; font-size: 0.8em; margin-top: 30px;
  }
</style>
""", unsafe_allow_html=True)

# ── Title ────────────────────────────────────────────────────────────────────
st.title("🔮 双色球预测")
st.caption("基于 3451 期历史数据的统计分析预测")

# ── Load Data ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_data():
    return fetch_draws()

with st.spinner("加载历史数据..."):
    draws = load_data()

# ── Controls ─────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    strategy = st.selectbox(
        "预测策略",
        ["balanced", "hot", "cold", "pattern", "monte-carlo"],
        format_func=lambda x: {
            "balanced": "综合加权", "hot": "热号策略",
            "cold": "冷号策略", "pattern": "走势匹配",
            "monte-carlo": "蒙特卡洛",
        }[x],
    )
with col2:
    count = st.selectbox("生成组数", [1, 3, 5, 10], index=1)
with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    predict_btn = st.button("🎲 生成预测", use_container_width=True)

# ── Predict ──────────────────────────────────────────────────────────────────
if predict_btn:
    with st.spinner("计算中..."):
        predictions = generate_predictions(draws, strategy_name=strategy, count=count)

    st.divider()
    st.subheader("📊 预测结果")

    cols = st.columns(min(count, 3))
    for i, p in enumerate(predictions):
        with cols[i % 3]:
            reds_html = "".join(f'<span class="ball-red">{r:02d}</span>' for r in p.reds)
            blue_html = f'<span class="ball-blue">{p.blue:02d}</span>'
            st.markdown(f"""
            <div class="pred-card">
              <div style="font-size:12px;color:#999;margin-bottom:4px">第 {i+1} 组</div>
              {reds_html} {blue_html}
              <div style="font-size:12px;color:#999;margin-top:6px">{p.confidence}</div>
            </div>
            """, unsafe_allow_html=True)

# ── Analysis ─────────────────────────────────────────────────────────────────
st.divider()

with st.expander("📈 查看统计分析", expanded=False):
    with st.spinner("分析中..."):
        report = run_full_analysis(draws)

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### 红球频率 TOP 10")
        data = [(r.number, r.count, f"{r.percentage}%") for r in report.red_frequency[:10]]
        st.dataframe(
            {"号码": [d[0] for d in data], "次数": [d[1] for d in data], "占比": [d[2] for d in data]},
            hide_index=True, use_container_width=True,
        )

        st.markdown("#### 红球遗漏排行")
        data = [(m.number, m.current_missing, m.average_missing, m.max_missing, m.missing_ratio)
                for m in report.red_missing[:10]]
        st.dataframe(
            {"号码": [d[0] for d in data], "当前遗漏": [d[1] for d in data],
             "平均遗漏": [d[2] for d in data], "最大遗漏": [d[3] for d in data],
             "遗漏比": [d[4] for d in data]},
            hide_index=True, use_container_width=True,
        )

    with col_b:
        st.markdown("#### 蓝球频率 TOP 5")
        data = [(b.number, b.count, f"{b.percentage}%") for b in report.blue_frequency[:5]]
        st.dataframe(
            {"号码": [d[0] for d in data], "次数": [d[1] for d in data], "占比": [d[2] for d in data]},
            hide_index=True, use_container_width=True,
        )

        st.markdown("#### 冷热号")
        hot = [r.number for r in report.hot_cold if r.classification.value == "hot"]
        cold = [r.number for r in report.hot_cold if r.classification.value == "cold"]
        warm = [r.number for r in report.hot_cold if r.classification.value == "warm"]
        hot_html = " ".join(f'<span class="ball-red" style="width:32px;height:32px;line-height:32px;font-size:13px">{n}</span>' for n in hot[:12])
        cold_html = " ".join(f'<span class="ball-blue" style="width:32px;height:32px;line-height:32px;font-size:13px">{n}</span>' for n in cold[:12])
        st.markdown(f"🔥 热号: {hot_html if hot else '无'}", unsafe_allow_html=True)
        st.markdown(f"🧊 冷号: {cold_html if cold else '无'}", unsafe_allow_html=True)

        st.markdown("#### 奇偶比分布")
        data = [(f"{oe.odd_count}:{oe.even_count}", f"{oe.percentage}%")
                for oe in report.odd_even if oe.percentage > 0.5]
        st.dataframe(
            {"奇:偶": [d[0] for d in data], "占比": [d[1] for d in data]},
            hide_index=True, use_container_width=True,
        )

    # Full-width stats
    s = report.sum_stats
    st.markdown("#### 和值 & 区间")
    st.text(f"和值范围: {s.min_sum}~{s.max_sum}  均值: {s.mean_sum}  常见: {s.common_low}~{s.common_high}")

    zone_text = ""
    for z in report.zone_distribution:
        total_z = sum(z.count_distribution.values())
        parts = ", ".join(f"{k}球:{v}次({v / total_z * 100:.1f}%)" for k, v in sorted(z.count_distribution.items()))
        zone_text += f"区间{z.zone_id}({z.zone_range[0]}-{z.zone_range[1]}): {parts}\n"
    st.text(zone_text)

st.markdown('<div class="disclaimer">彩票开奖为随机事件，本工具仅提供统计分析，不保证中奖结果，请理性购彩。</div>', unsafe_allow_html=True)
