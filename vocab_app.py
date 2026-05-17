"""CET-4/6 Vocabulary Learning App — Streamlit"""

import streamlit as st
import random
from datetime import date

from vocab import load_words, get_list_info, daily_words, WORD_LISTS

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="四六级单词学习",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS Styles ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Global */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Word card */
    .word-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        padding: 24px 32px;
        margin: 8px 0;
        color: #fff;
        cursor: pointer;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .word-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
    }
    .word-card .word { font-size: 28px; font-weight: 700; }
    .word-card .phonetic { font-size: 16px; opacity: 0.85; margin-left: 12px; }
    .word-card .meaning { font-size: 16px; margin-top: 8px; opacity: 0.95; }

    /* Flashcard */
    .flashcard {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 2px solid #667eea;
        border-radius: 20px;
        padding: 60px 40px;
        text-align: center;
        cursor: pointer;
        min-height: 300px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        transition: transform 0.3s, box-shadow 0.3s;
        user-select: none;
    }
    .flashcard:hover {
        transform: scale(1.02);
        box-shadow: 0 12px 40px rgba(102, 126, 234, 0.3);
    }
    .flashcard .en-word { font-size: 48px; font-weight: 700; color: #fff; }
    .flashcard .phonetic { font-size: 20px; color: #a0a0c0; margin-top: 8px; }
    .flashcard .cn-meaning { font-size: 28px; color: #f0c040; margin-top: 16px; }
    .flashcard .collocation { font-size: 16px; color: #80b0ff; margin-top: 8px; }
    .flashcard .flip-hint { font-size: 14px; color: #888; margin-top: 24px; }

    /* Speak button */
    .speak-btn {
        display: inline-block;
        width: 36px; height: 36px;
        line-height: 36px; text-align: center;
        background: #667eea; color: #fff;
        border-radius: 50%; cursor: pointer;
        font-size: 18px; margin-left: 8px;
        transition: background 0.2s;
    }
    .speak-btn:hover { background: #764ba2; }

    /* Stats */
    .stat-box {
        background: #f8f9fa; border-radius: 12px;
        padding: 16px; text-align: center;
    }
    .stat-box .num { font-size: 32px; font-weight: 700; color: #667eea; }
    .stat-box .label { font-size: 14px; color: #666; margin-top: 4px; }

    /* Quiz */
    .quiz-option {
        background: #f8f9fa; border: 2px solid #e0e0e0;
        border-radius: 12px; padding: 16px 20px;
        margin: 6px 0; cursor: pointer;
        transition: all 0.2s;
    }
    .quiz-option:hover {
        border-color: #667eea;
        background: #f0f0ff;
    }

    /* Daily words */
    .daily-word {
        display: inline-block;
        background: #667eea; color: #fff;
        border-radius: 20px; padding: 6px 16px;
        margin: 4px; font-size: 15px;
        cursor: pointer;
        transition: background 0.2s;
    }
    .daily-word:hover { background: #764ba2; }

    /* Progress */
    .progress-text { font-size: 14px; color: #666; text-align: center; margin-top: 8px; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 12px 24px;
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

# ── Pronunciation Helper ───────────────────────────────────────────────────────
def speak_button(word: str, key_suffix: str = ""):
    """Render a clickable pronunciation button using browser SpeechSynthesis API.

    Uses st.components.v1.html to bypass Streamlit's HTML sanitization
    which strips inline onclick handlers from st.markdown output.
    """
    clean_word = word.replace("'", "\\'").replace('"', '\\"')
    st.components.v1.html(f"""
    <button onclick="
        (function() {{
            var u = new SpeechSynthesisUtterance('{clean_word}');
            u.lang = 'en-US';
            u.rate = 0.85;
            speechSynthesis.cancel();
            speechSynthesis.speak(u);
        }})();
    " style="
        padding: 6px 16px;
        border: none;
        background: #667eea;
        color: #fff;
        border-radius: 8px;
        font-size: 14px;
        cursor: pointer;
        transition: background 0.2s;
    " onmouseover="this.style.background='#764ba2'"
       onmouseout="this.style.background='#667eea'"
    >🔊 发音</button>
    """, height=45)


# ── Session State Init ─────────────────────────────────────────────────────────
if "flashcard_index" not in st.session_state:
    st.session_state.flashcard_index = 0
if "flashcard_show_cn" not in st.session_state:
    st.session_state.flashcard_show_cn = False
if "flashcard_words" not in st.session_state:
    st.session_state.flashcard_words = []
if "flashcard_known" not in st.session_state:
    st.session_state.flashcard_known = set()
if "quiz_started" not in st.session_state:
    st.session_state.quiz_started = False
if "quiz_questions" not in st.session_state:
    st.session_state.quiz_questions = []
if "quiz_current" not in st.session_state:
    st.session_state.quiz_current = 0
if "quiz_score" not in st.session_state:
    st.session_state.quiz_score = 0
if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = []
if "quiz_tested_words" not in st.session_state:
    st.session_state.quiz_tested_words = set()
if "quiz_history" not in st.session_state:
    st.session_state.quiz_history = []
if "browse_shuffle" not in st.session_state:
    st.session_state.browse_shuffle = False


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📚 四六级单词")

    # Get available word lists
    info = get_list_info()

    st.markdown("### 🎯 词库选择")

    level = st.radio("考试级别", ["cet4", "cet6"],
                     format_func=lambda x: "四级 (CET-4)" if x == "cet4" else "六级 (CET-6)")

    # Filter lists by level
    level_lists = {k: v for k, v in WORD_LISTS.items() if v["level"] == level}
    list_names = list(level_lists.keys())
    list_labels = [level_lists[k]["label"] for k in list_names]

    selected_list = st.selectbox("词库类型", list_names, format_func=lambda x: level_lists[x]["label"])

    # Load words for the selected list
    try:
        words = load_words(selected_list)
        word_count = len(words)
        st.success(f"✅ 已加载 {word_count} 个单词")
    except Exception as e:
        st.error(f"加载失败: {e}")
        words = []
        word_count = 0

    st.divider()

    # Search
    st.markdown("### 🔍 搜索单词")
    search_term = st.text_input("输入单词", placeholder="例如: abandon")

    st.divider()

    # Quick nav
    st.markdown("### 📋 快速导航")
    st.caption(f"共 {word_count} 个单词")

    st.divider()

    # Info
    st.markdown("### ℹ️ 关于")
    st.caption(
        "发音功能使用浏览器内置语音引擎。"
        "点击 🔊 按钮即可听到标准美式发音。"
    )

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📖 浏览单词",
    "🃏 闪卡模式",
    "📝 测验模式",
    "📅 每日单词",
])

# =============================================================
# TAB 1: Word Browser
# =============================================================
with tab1:
    st.markdown("## 📖 单词浏览")

    if not words:
        st.warning("请先在侧边栏选择词库。")
    else:
        # Filter by search
        col_a, col_b, col_c, col_d = st.columns([1.5, 1, 1, 1])
        with col_a:
            if search_term:
                filtered = [w for w in words if search_term.lower() in w["word"].lower()]
                st.info(f"搜索 \"{search_term}\" — 找到 {len(filtered)} 个结果")
            else:
                filtered = words

        with col_b:
            letter = st.selectbox("按字母筛选", ["全部"] + [chr(i) for i in range(65, 91)], key="browse_letter")

        if letter != "全部":
            filtered = [w for w in filtered if w["word"].upper().startswith(letter)]

        with col_c:
            page_size = st.selectbox("每页显示", [20, 50, 100], index=0, key="browse_page_size")

        with col_d:
            shuffle = st.checkbox("🔀 乱序展示", value=st.session_state.browse_shuffle, key="browse_shuffle_cb")
            if shuffle != st.session_state.browse_shuffle:
                st.session_state.browse_shuffle = shuffle
                st.rerun()
            if st.session_state.browse_shuffle:
                random.seed(42)  # consistent shuffle within session
                random.shuffle(filtered)

        # Pagination
        total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
        page = st.number_input("页码", min_value=1, max_value=total_pages, value=1, label_visibility="collapsed")
        start = (page - 1) * page_size
        end = start + page_size
        page_words = filtered[start:end]

        st.caption(f"第 {page}/{total_pages} 页，显示第 {start + 1}-{min(end, len(filtered))} 个")

        # Word list
        for i, w in enumerate(page_words):
            idx = start + i + 1
            with st.expander(f"**{idx}. {w['word']}**  {w['phonetic']}  —  {w['meaning'][:40]}", expanded=False):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"### {w['word']}")
                    st.markdown(f"**音标**: {w['phonetic']}")
                    st.markdown(f"**释义**: {w['meaning']}")
                    if w.get("collocations"):
                        st.markdown(f"**搭配**: {w['collocations']}")
                    st.caption(f"级别: {w['level'].upper()} | 词频: {w['frequency']}")
                with col2:
                    speak_button(w['word'], key_suffix=f"browse_{idx}")

# =============================================================
# TAB 2: Flashcard Mode
# =============================================================
with tab2:
    st.markdown("## 🃏 闪卡模式")

    if not words:
        st.warning("请先在侧边栏选择词库。")
    else:
        # Init flashcards
        if not st.session_state.flashcard_words:
            shuffled = words.copy()
            random.shuffle(shuffled)
            st.session_state.flashcard_words = shuffled
            st.session_state.flashcard_index = 0
            st.session_state.flashcard_show_cn = False
            st.session_state.flashcard_known = set()

        total = len(st.session_state.flashcard_words)
        current_idx = st.session_state.flashcard_index

        if current_idx >= total:
            # Completed all words
            st.balloons()
            st.success(f"🎉 已完成全部 {total} 个单词！")

            known_count = len(st.session_state.flashcard_known)
            st.markdown(f"### 统计: 认识 {known_count}/{total} 个单词")

            if st.button("🔄 重新开始", use_container_width=True):
                st.session_state.flashcard_words = []
                st.session_state.flashcard_index = 0
                st.session_state.flashcard_show_cn = False
                st.session_state.flashcard_known = set()
                st.rerun()
        else:
            w = st.session_state.flashcard_words[current_idx]

            # Progress
            progress_pct = current_idx / total
            st.progress(progress_pct)
            st.caption(f"进度: {current_idx + 1} / {total}")

            # Flashcard
            show_cn = st.session_state.flashcard_show_cn
            known_words = st.session_state.flashcard_known

            card_col1, card_col2, card_col3 = st.columns([1, 3, 1])

            with card_col2:
                if not show_cn:
                    # Front of card (English)
                    st.markdown(f"""
                    <div class="flashcard" id="flashcard">
                        <div class="en-word">{w['word']}</div>
                        <div class="phonetic">{w['phonetic']}</div>
                        <div class="flip-hint">👆 点击下方按钮翻转</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # Back of card (Chinese + details)
                    st.markdown(f"""
                    <div class="flashcard" id="flashcard">
                        <div class="en-word">{w['word']}</div>
                        <div class="phonetic">{w['phonetic']}</div>
                        <div class="cn-meaning">{w['meaning']}</div>
                        {f'<div class="collocation">{w["collocations"]}</div>' if w.get('collocations') else ''}
                    </div>
                    """, unsafe_allow_html=True)

            # Buttons
            btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)

            with btn_col1:
                speak_button(w['word'], key_suffix="fc")

            with btn_col2:
                if not show_cn:
                    if st.button("🔄 翻转查看", key="fc_flip", use_container_width=True):
                        st.session_state.flashcard_show_cn = True
                        st.rerun()

            with btn_col3:
                if show_cn:
                    if st.button("✅ 认识了", key="fc_know", use_container_width=True):
                        st.session_state.flashcard_known.add(w['word'])
                        st.session_state.flashcard_index += 1
                        st.session_state.flashcard_show_cn = False
                        st.rerun()

            with btn_col4:
                if show_cn:
                    if st.button("❌ 不认识", key="fc_unknown", use_container_width=True):
                        # Add back to the end for review
                        st.session_state.flashcard_words.append(w)
                        st.session_state.flashcard_index += 1
                        st.session_state.flashcard_show_cn = False
                        st.rerun()

            # Stats
            known_count = len(known_words)
            st.markdown(f"✅ 认识: **{known_count}** | 📝 剩余: **{total - current_idx - 1}**")

# =============================================================
# TAB 3: Quiz Mode
# =============================================================
with tab3:
    st.markdown("## 📝 测验模式")

    if not words:
        st.warning("请先在侧边栏选择词库。")
    else:
        # ── Quiz History (always visible) ──
        if st.session_state.quiz_history:
            with st.expander(f"📊 测验记录 ({len(st.session_state.quiz_history)} 次)", expanded=False):
                for j, record in enumerate(reversed(st.session_state.quiz_history)):
                    rcol1, rcol2, rcol3 = st.columns([2, 1, 1])
                    with rcol1:
                        st.markdown(f"**{len(st.session_state.quiz_history) - j}. {record['date']}** — {record['quiz_type']}")
                        st.markdown(f"得分: {record['score']}/{record['total']} ({record['percentage']}%)")
                    with rcol2:
                        correct_count = sum(1 for a in record['answers'] if a['correct'])
                        wrong_count = len(record['answers']) - correct_count
                        st.markdown(f"✅ {correct_count}  |  ❌ {wrong_count}")
                    with rcol3:
                        # Show wrong words preview
                        wrongs = [a for a in record['answers'] if not a['correct']]
                        if wrongs:
                            wrong_words = ", ".join(a['word']['word'] for a in wrongs[:5])
                            st.caption(f"错词: {wrong_words}{'...' if len(wrongs) > 5 else ''}")
                    st.divider()

        quiz_col1, quiz_col2 = st.columns([2, 1])

        with quiz_col1:
            quiz_type = st.selectbox("题型", ["看英文选中文", "看中文选英文"], key="quiz_type")

        with quiz_col2:
            quiz_count = st.selectbox("题目数量", [10, 20, 30], index=0)

        # Show tested count and remaining
        tested_count = len(st.session_state.quiz_tested_words)
        remaining = max(0, len(words) - tested_count)
        st.caption(f"📊 已测: {tested_count} 个 | 剩余: {remaining} 个")

        if not st.session_state.quiz_started:
            if st.button("🚀 开始测验", use_container_width=True, type="primary"):
                # Generate questions — exclude previously tested words
                tested = st.session_state.quiz_tested_words
                available = [w for w in words if w['word'] not in tested]

                if len(available) < quiz_count:
                    # Not enough new words — offer to reset
                    if len(available) == 0:
                        st.warning("🎉 词库中所有单词都已测过！请先重置测验记录。")
                        if st.button("🔄 重置测验记录", use_container_width=True):
                            st.session_state.quiz_tested_words = set()
                            st.rerun()
                        st.stop()
                    else:
                        st.info(f"只有 {len(available)} 个新单词可用，将全部使用。")
                        quiz_count_actual = len(available)
                else:
                    quiz_count_actual = quiz_count

                pool = available.copy()
                random.shuffle(pool)
                pool = pool[:quiz_count_actual]

                # Mark these words as tested
                for w in pool:
                    st.session_state.quiz_tested_words.add(w['word'])

                questions = []
                for w in pool:
                    wrongs = [x for x in words if x['word'] != w['word']]
                    wrong_pool = random.sample(wrongs, min(3, len(wrongs)))

                    if quiz_type == "看英文选中文":
                        correct = w['meaning']
                        options = [correct] + [x['meaning'] for x in wrong_pool]
                    else:
                        correct = w['word']
                        options = [correct] + [x['word'] for x in wrong_pool]

                    random.shuffle(options)
                    correct_idx = options.index(correct)

                    questions.append({
                        "word": w,
                        "options": options,
                        "correct_idx": correct_idx,
                    })

                st.session_state.quiz_questions = questions
                st.session_state.quiz_current = 0
                st.session_state.quiz_score = 0
                st.session_state.quiz_answers = []
                st.session_state.quiz_started = True
                st.rerun()

        else:
            # Quiz in progress
            qs = st.session_state.quiz_questions
            cur = st.session_state.quiz_current

            if cur >= len(qs):
                # Quiz finished — save to history
                score = st.session_state.quiz_score
                total_q = len(qs)
                pct = score / total_q * 100 if total_q > 0 else 0

                # Save result to history (only if not already saved from this run)
                result = {
                    "date": date.today().isoformat(),
                    "score": score,
                    "total": total_q,
                    "percentage": round(pct, 1),
                    "quiz_type": quiz_type,
                    "answers": st.session_state.quiz_answers.copy(),
                }

                # Avoid duplicate saves on rerun
                if not st.session_state.get("_quiz_result_saved", False):
                    st.session_state.quiz_history.append(result)
                    st.session_state._quiz_result_saved = True

                st.balloons()
                st.markdown(f"## 🎉 测验完成！")
                st.markdown(f"### 得分: {score}/{total_q} ({pct:.0f}%)")

                if pct >= 80:
                    st.success("太棒了！继续保持！")
                elif pct >= 60:
                    st.info("不错！还有进步空间！")
                else:
                    st.warning("继续加油！多复习一下！")

                # Review wrong answers
                wrong_answers = [a for a in st.session_state.quiz_answers if not a["correct"]]
                if wrong_answers:
                    st.markdown("### 🔴 错题回顾")
                    for i, a in enumerate(wrong_answers):
                        w = a["word"]
                        st.markdown(f"""
                        **{i + 1}. {w['word']}** — {w['meaning']}
                        > 你的答案: {a['user_choice']}
                        > 正确答案: {a['correct_answer']}
                        """)
                        speak_button(w['word'], key_suffix=f"quiz_review_{i}")

                btn_r1, btn_r2 = st.columns(2)
                with btn_r1:
                    if st.button("🔄 继续测验(新单词)", use_container_width=True):
                        st.session_state.quiz_started = False
                        st.session_state.quiz_questions = []
                        st.session_state.quiz_current = 0
                        st.session_state.quiz_score = 0
                        st.session_state.quiz_answers = []
                        st.session_state._quiz_result_saved = False
                        st.rerun()
                with btn_r2:
                    if st.button("🔁 重置所有记录", use_container_width=True):
                        st.session_state.quiz_tested_words = set()
                        st.session_state.quiz_history = []
                        st.session_state.quiz_started = False
                        st.session_state.quiz_questions = []
                        st.session_state.quiz_current = 0
                        st.session_state.quiz_score = 0
                        st.session_state.quiz_answers = []
                        st.session_state._quiz_result_saved = False
                        st.rerun()
            else:
                # Current question
                q = qs[cur]
                w = q["word"]

                # Progress
                st.progress(cur / len(qs))
                st.caption(f"第 {cur + 1}/{len(qs)} 题 | 得分: {st.session_state.quiz_score}")

                # Question
                st.markdown("---")
                if quiz_type == "看英文选中文":
                    col_q, col_s = st.columns([4, 1])
                    with col_q:
                        st.markdown(f"## {w['word']}")
                        st.markdown(f"*{w['phonetic']}*")
                    with col_s:
                        speak_button(w['word'], key_suffix=f"quiz_q_{cur}")
                    st.markdown("### 请选择正确的中文释义:")
                else:
                    st.markdown(f"## {w['meaning']}")
                    st.markdown("### 请选择正确的英文单词:")

                # Options
                for i, opt in enumerate(q["options"]):
                    if st.button(f"{chr(65 + i)}. {opt}", key=f"quiz_opt_{cur}_{i}", use_container_width=True):
                        correct = i == q["correct_idx"]
                        if correct:
                            st.session_state.quiz_score += 1
                        st.session_state.quiz_answers.append({
                            "word": w,
                            "user_choice": opt,
                            "correct_answer": q["options"][q["correct_idx"]],
                            "correct": correct,
                        })
                        st.session_state.quiz_current += 1
                        st.rerun()

                # Quit button
                st.divider()
                if st.button("⏹ 结束测验", key="quiz_quit"):
                    # Save partial result to history
                    if st.session_state.quiz_answers and not st.session_state.get("_quiz_result_saved", False):
                        partial_result = {
                            "date": date.today().isoformat(),
                            "score": st.session_state.quiz_score,
                            "total": len(st.session_state.quiz_answers),
                            "percentage": round(st.session_state.quiz_score / max(1, len(st.session_state.quiz_answers)) * 100, 1),
                            "quiz_type": quiz_type,
                            "answers": st.session_state.quiz_answers.copy(),
                        }
                        st.session_state.quiz_history.append(partial_result)
                    st.session_state.quiz_started = False
                    st.session_state.quiz_questions = []
                    st.session_state.quiz_current = 0
                    st.session_state.quiz_score = 0
                    st.session_state.quiz_answers = []
                    st.session_state._quiz_result_saved = False
                    st.rerun()

# =============================================================
# TAB 4: Daily Words
# =============================================================
with tab4:
    st.markdown("## 📅 每日单词")

    if not words:
        st.warning("请先在侧边栏选择词库。")
    else:
        today = date.today()

        st.markdown(f"### {today.strftime('%Y年%m月%d日')} — 今日推荐")

        daily_count = st.slider("单词数量", 5, 30, 15)

        # Generate daily words based on today's date as seed
        today_seed = today.toordinal()
        daily = daily_words(selected_list, count=daily_count)

        # Display as cards in grid
        cols = st.columns(3)
        for i, w in enumerate(daily):
            with cols[i % 3]:
                st.markdown(f"""
                <div class="word-card">
                    <div class="word">{w['word']}</div>
                    <div class="phonetic">{w['phonetic']}</div>
                    <div class="meaning">{w['meaning'][:60]}</div>
                    {f'<div style="font-size:13px;opacity:0.7;margin-top:4px;">{w["collocations"]}</div>' if w.get('collocations') else ''}
                </div>
                """, unsafe_allow_html=True)
                speak_button(w['word'], key_suffix=f"daily_{i}")

        # Yesterday's words
        st.divider()
        st.markdown(f"### 📆 昨日单词回顾")
        yesterday_seed = today.toordinal() - 1
        from vocab import sample_words
        yesterday_words = sample_words(selected_list, count=min(10, len(words)), seed=yesterday_seed)

        review_cols = st.columns(5)
        for i, w in enumerate(yesterday_words):
            with review_cols[i % 5]:
                st.markdown(f"""
                <div style="text-align:center;padding:8px;">
                    <div style="font-weight:600;">{w['word']}</div>
                    <div style="font-size:12px;color:#888;">{w['meaning'][:20]}</div>
                </div>
                """, unsafe_allow_html=True)
                speak_button(w['word'], key_suffix=f"yesterday_{i}")

# ── Footer ─────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<div style='text-align:center;color:#999;font-size:0.85em;padding:20px;'>"
    "📚 CET-4/6 Vocabulary Learning App | Powered by Streamlit | "
    "Pronunciation via Web Speech API<br>"
    "好好学习，天天向上！💪"
    "</div>",
    unsafe_allow_html=True,
)
