"""Quiz record persistence — Google Sheets primary, local JSON fallback."""

import json
from pathlib import Path

JSON_FILE = Path(__file__).parent / "data" / "quiz_records.json"


def _load_from_json():
    if JSON_FILE.exists():
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("quiz_history", []), set(data.get("quiz_tested_words", []))
        except (json.JSONDecodeError, OSError):
            pass
    return [], set()


def _save_to_json(quiz_history, tested_words):
    JSON_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "quiz_history": quiz_history,
        "quiz_tested_words": sorted(tested_words),
    }
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _gsheet_client():
    """Return (worksheet_records, worksheet_words) for Google Sheets backend."""
    import streamlit as st
    from google.oauth2.service_account import Credentials
    import gspread

    creds_info = st.secrets["gcp_service_account"]
    sheet_name = st.secrets.get("gsheet_name", "cet_vocab_quiz_records")

    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(dict(creds_info), scopes=scope)
    client = gspread.authorize(creds)

    sheet = client.open(sheet_name)
    return sheet


def _load_from_gsheets():
    sheet = _gsheet_client()

    # --- quiz_records sheet ---
    try:
        ws = sheet.worksheet("quiz_records")
    except Exception:
        ws = sheet.add_worksheet("quiz_records", 1000, 8)
        ws.append_row(["date", "score", "total", "planned_total",
                        "percentage", "quiz_type", "completed", "answers_json"])

    records = ws.get_all_records()
    quiz_history = []
    for row in records:
        if not row.get("date"):
            continue
        quiz_history.append({
            "date": str(row["date"]),
            "score": int(row["score"]),
            "total": int(row["total"]),
            "planned_total": int(row["planned_total"]),
            "percentage": float(row["percentage"]),
            "quiz_type": str(row["quiz_type"]),
            "completed": str(row["completed"]).lower() == "true",
            "answers": json.loads(str(row["answers_json"])),
        })

    # --- tested_words sheet ---
    try:
        ws_words = sheet.worksheet("tested_words")
    except Exception:
        ws_words = sheet.add_worksheet("tested_words", 10000, 1)
        ws_words.append_row(["word"])

    words = ws_words.col_values(1)[1:]  # skip header
    tested_words = set(w for w in words if w.strip())

    return quiz_history, tested_words


def _save_to_gsheets(quiz_history, tested_words):
    sheet = _gsheet_client()

    # --- quiz_records sheet: full rewrite (avoids dedup complexity) ---
    try:
        ws = sheet.worksheet("quiz_records")
    except Exception:
        ws = sheet.add_worksheet("quiz_records", 1000, 8)

    ws.clear()
    ws.append_row(["date", "score", "total", "planned_total",
                    "percentage", "quiz_type", "completed", "answers_json"])
    for r in quiz_history:
        ws.append_row([
            r["date"],
            r["score"],
            r["total"],
            r["planned_total"],
            r["percentage"],
            r["quiz_type"],
            str(r["completed"]),
            json.dumps(r["answers"], ensure_ascii=False),
        ])

    # --- tested_words sheet: full rewrite ---
    try:
        ws_words = sheet.worksheet("tested_words")
    except Exception:
        ws_words = sheet.add_worksheet("tested_words", 10000, 1)

    ws_words.clear()
    ws_words.append_row(["word"])
    for w in sorted(tested_words):
        ws_words.append_row([w])


# ── Public API ───────────────────────────────────────────────────────────────────

def load_quiz_records():
    """Load quiz history + tested words. Google Sheets if configured, else JSON."""
    try:
        import streamlit as st
        if "gcp_service_account" in st.secrets:
            return _load_from_gsheets()
    except Exception:
        pass
    return _load_from_json()


def save_quiz_records():
    """Persist quiz history + tested words. Google Sheets if configured, else JSON."""
    import streamlit as st
    history = list(st.session_state.quiz_history)
    tested = set(st.session_state.quiz_tested_words)

    try:
        if "gcp_service_account" in st.secrets:
            _save_to_gsheets(history, tested)
            return
    except Exception:
        pass
    _save_to_json(history, tested)
