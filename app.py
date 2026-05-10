import streamlit as st
import streamlit.components.v1 as components
import json
import os
import html as html_lib
import base64
from datetime import datetime, date, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

try:
    from supabase import create_client
    _SB_PKG = True
except ImportError:
    _SB_PKG = False

import anthropic

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sangchan's Board", page_icon="✦",
    layout="wide", initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# SECRETS  — env (.env for local) ▸ st.secrets (Streamlit Cloud)
# ─────────────────────────────────────────────────────────────────────────────
def _secret(key: str, default: str = "") -> str:
    val = os.getenv(key, "")
    if val:
        return val
    try:
        return str(st.secrets.get(key, default))
    except Exception:
        return default


API_KEY      = _secret("ANTHROPIC_API_KEY")
SUPABASE_URL = _secret("SUPABASE_URL")
SUPABASE_KEY = _secret("SUPABASE_KEY")
APP_PASSWORD = _secret("APP_PASSWORD")

# ─────────────────────────────────────────────────────────────────────────────
# PASSWORD GATE  — APP_PASSWORD 가 설정된 경우에만 활성화
# ─────────────────────────────────────────────────────────────────────────────
if APP_PASSWORD:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.markdown("""
        <div style="max-width:360px;margin:120px auto;text-align:center">
          <div style="font-size:48px;margin-bottom:12px">✦</div>
          <div style="font-size:22px;font-weight:700;color:#1e293b;margin-bottom:6px">나의 대시보드</div>
          <div style="font-size:13px;color:#64748b;margin-bottom:28px">비밀번호를 입력하세요</div>
        </div>
        """, unsafe_allow_html=True)

        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            pw = st.text_input("", type="password", placeholder="비밀번호",
                               label_visibility="collapsed")
            if st.button("입장", use_container_width=True, type="primary"):
                if pw == APP_PASSWORD:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("비밀번호가 틀렸습니다.")
        st.stop()


@st.cache_resource
def _db():
    """Supabase client, cached. Returns None when not configured."""
    if _SB_PKG and SUPABASE_URL and SUPABASE_KEY:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# LOCAL JSON FALLBACK  (used when Supabase is not configured)
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR  = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

QUOTES_F = DATA_DIR / "quotes.json"
GOALS_F  = DATA_DIR / "goals.json"
TASKS_F  = DATA_DIR / "tasks.json"
SAVED_F  = DATA_DIR / "translations.json"

def _jload(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text("utf-8"))
    except Exception:
        pass
    return default

def _jsave(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# DATA LAYER  — identical API for local and Supabase modes
# Items always carry {"id": ..., ...} so the UI code doesn't branch.
# ─────────────────────────────────────────────────────────────────────────────
DEF_QUOTES = [
    {"text": "오늘 할 수 있는 일에 최선을 다하라. 그러면 내일은 더 잘 할 수 있을 것이다.", "author": "H. Jackson Brown Jr."},
    {"text": "The secret of getting ahead is getting started.", "author": "Mark Twain"},
    {"text": "성공은 최종 목적지가 아니다. 실패는 치명적이지 않다. 계속하는 용기가 중요하다.", "author": "Winston Churchill"},
    {"text": "In the middle of every difficulty lies opportunity.", "author": "Albert Einstein"},
    {"text": "자신을 믿어라. 당신은 생각보다 훨씬 용감하고, 보이는 것보다 훨씬 강하다.", "author": "A.A. Milne"},
]

# ── QUOTES ───────────────────────────────────────────────────────────────────
def quotes_load():
    db = _db()
    if db:
        rows = db.table("quotes").select("*").order("id").execute().data
        return [{"id": r["id"], "text": r["text"], "author": r.get("author","")} for r in rows]
    raw = _jload(QUOTES_F, DEF_QUOTES)
    return [{"id": i, "text": d.get("text",""), "author": d.get("author","")} for i, d in enumerate(raw)]

def quotes_add(text, author):
    db = _db()
    if db:
        db.table("quotes").insert({"text": text, "author": author}).execute()
    else:
        raw = _jload(QUOTES_F, DEF_QUOTES)
        raw.append({"text": text, "author": author})
        _jsave(QUOTES_F, raw)

def quotes_update(item_id, text, author):
    db = _db()
    if db:
        db.table("quotes").update({"text": text, "author": author}).eq("id", item_id).execute()
    else:
        raw = _jload(QUOTES_F, DEF_QUOTES)
        if 0 <= item_id < len(raw):
            raw[item_id] = {"text": text, "author": author}
            _jsave(QUOTES_F, raw)

def quotes_delete(item_id):
    db = _db()
    if db:
        db.table("quotes").delete().eq("id", item_id).execute()
    else:
        raw = _jload(QUOTES_F, DEF_QUOTES)
        if 0 <= item_id < len(raw):
            raw.pop(item_id)
            _jsave(QUOTES_F, raw)

# ── GOALS ────────────────────────────────────────────────────────────────────
def goals_load(year):
    db = _db()
    if db:
        rows = db.table("goals").select("*").eq("year", year).order("id").execute().data
        return [{"id": r["id"], "text": r["text"], "done": r["done"]} for r in rows]
    all_g = _jload(GOALS_F, {"2026": [], "2030": []})
    return [{"id": i, "text": d.get("text",""), "done": d.get("done", False)}
            for i, d in enumerate(all_g.get(year, []))]

def goals_add(year, text):
    db = _db()
    if db:
        db.table("goals").insert({"year": year, "text": text, "done": False}).execute()
    else:
        all_g = _jload(GOALS_F, {"2026": [], "2030": []})
        all_g.setdefault(year, []).append({"text": text, "done": False})
        _jsave(GOALS_F, all_g)

def goals_toggle(item_id, current_done, year):
    db = _db()
    if db:
        db.table("goals").update({"done": not current_done}).eq("id", item_id).execute()
    else:
        all_g = _jload(GOALS_F, {"2026": [], "2030": []})
        lst = all_g.get(year, [])
        if 0 <= item_id < len(lst):
            lst[item_id]["done"] = not current_done
        _jsave(GOALS_F, all_g)

def goals_delete(item_id, year):
    db = _db()
    if db:
        db.table("goals").delete().eq("id", item_id).execute()
    else:
        all_g = _jload(GOALS_F, {"2026": [], "2030": []})
        lst = all_g.get(year, [])
        if 0 <= item_id < len(lst):
            lst.pop(item_id)
        _jsave(GOALS_F, all_g)

# ── TASKS ────────────────────────────────────────────────────────────────────
def tasks_load(day_key):
    db = _db()
    if db:
        rows = db.table("tasks").select("*").eq("day_key", day_key).order("id").execute().data
        return [{"id": r["id"], "text": r["text"], "done": r["done"]} for r in rows]
    all_t = _jload(TASKS_F, {})
    return [{"id": i, "text": d.get("text",""), "done": d.get("done", False)}
            for i, d in enumerate(all_t.get(day_key, []))]

def tasks_add(day_key, text):
    db = _db()
    if db:
        db.table("tasks").insert({"day_key": day_key, "text": text, "done": False}).execute()
    else:
        all_t = _jload(TASKS_F, {})
        all_t.setdefault(day_key, []).append({"text": text, "done": False})
        _jsave(TASKS_F, all_t)

def tasks_toggle(item_id, current_done, day_key):
    db = _db()
    if db:
        db.table("tasks").update({"done": not current_done}).eq("id", item_id).execute()
    else:
        all_t = _jload(TASKS_F, {})
        lst = all_t.get(day_key, [])
        if 0 <= item_id < len(lst):
            lst[item_id]["done"] = not current_done
        _jsave(TASKS_F, all_t)

def tasks_delete(item_id, day_key):
    db = _db()
    if db:
        db.table("tasks").delete().eq("id", item_id).execute()
    else:
        all_t = _jload(TASKS_F, {})
        lst = all_t.get(day_key, [])
        if 0 <= item_id < len(lst):
            lst.pop(item_id)
        _jsave(TASKS_F, all_t)

def tasks_update(item_id, day_key, text):
    db = _db()
    if db:
        db.table("tasks").update({"text": text}).eq("id", item_id).execute()
    else:
        all_t = _jload(TASKS_F, {})
        lst = all_t.get(day_key, [])
        if 0 <= item_id < len(lst):
            lst[item_id]["text"] = text
        _jsave(TASKS_F, all_t)

# ── TRANSLATIONS ──────────────────────────────────────────────────────────────
def tr_load():
    db = _db()
    if db:
        return db.table("translations").select("*").order("id", desc=True).limit(30).execute().data
    return _jload(SAVED_F, [])

def tr_add(src, result, mode, date_str):
    db = _db()
    if db:
        db.table("translations").insert(
            {"src": src, "result": result, "mode": mode, "date": date_str}
        ).execute()
    else:
        saved = _jload(SAVED_F, [])
        saved.insert(0, {"src": src, "result": result, "mode": mode, "date": date_str})
        if len(saved) > 30:
            saved.pop()
        _jsave(SAVED_F, saved)

# ── IMAGE (3장 슬롯 지원) ──────────────────────────────────────────────────────
def image_load(slot: int = 0):
    """Returns image bytes or None for the given slot (0-2)."""
    key = f"image_b64_{slot}"
    db = _db()
    if db:
        rows = db.table("settings").select("value").eq("key", key).execute().data
        if rows:
            val = rows[0]["value"]
            _, b64 = (val.split(":", 1) if ":" in val else ("png", val))
            return base64.b64decode(b64)
        return None
    for ext in ["png", "jpg", "jpeg", "gif", "webp"]:
        p = DATA_DIR / f"dashboard_img_{slot}.{ext}"
        if p.exists():
            return p.read_bytes()
    return None

def image_save(img_bytes: bytes, ext: str = "png", slot: int = 0):
    key = f"image_b64_{slot}"
    db = _db()
    if db:
        val = f"{ext}:{base64.b64encode(img_bytes).decode()}"
        rows = db.table("settings").select("key").eq("key", key).execute().data
        if rows:
            db.table("settings").update({"value": val}).eq("key", key).execute()
        else:
            db.table("settings").insert({"key": key, "value": val}).execute()
    else:
        for e in ["png", "jpg", "jpeg", "gif", "webp"]:
            old = DATA_DIR / f"dashboard_img_{slot}.{e}"
            if old.exists():
                old.unlink()
        (DATA_DIR / f"dashboard_img_{slot}.{ext}").write_bytes(img_bytes)


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
for k, v in [("quote_idx", 0), ("wk_off", 0), ("tr_result", ""), ("photo_slot", 0)]:
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden }
.block-container { padding-top: 0 !important; padding-bottom: 2rem !important }
* { font-family: 'Malgun Gothic','Noto Sans KR','Segoe UI',sans-serif }

.dash-hdr {
    background: linear-gradient(120deg,#4361ee 0%,#7c3aed 55%,#a855f7 100%);
    padding: 16px 32px; border-radius: 0 0 20px 20px; color: white;
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 22px; box-shadow: 0 4px 24px rgba(67,97,238,.28);
}
.dash-logo { font-size: 21px; font-weight: 700; letter-spacing: -.5px }
.dash-sub  { font-size: 12px; opacity: .75; margin-top: 3px }
.dash-time { font-size: 23px; font-weight: 700; text-align: right }
.dash-date { font-size: 12px; opacity: .82; text-align: right; margin-top: 2px }
.sec-lbl {
    font-size: 11px; font-weight: 700; color: #64748b;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px;
}
.q-card {
    background: linear-gradient(135deg,#4361ee,#7c3aed);
    border-radius: 16px; padding: 26px 30px; color: white;
    position: relative; overflow: hidden; min-height: 160px;
}
.q-card::before {
    content:'"'; position: absolute; top:-28px; left:18px;
    font-size:190px; opacity:.07; font-family:Georgia,serif; line-height:1;
    pointer-events:none;
}
.q-text   { font-size:18px; font-weight:300; line-height:1.8; font-style:italic; margin-bottom:14px }
.q-author { font-size:13px; opacity:.73; text-align:right }
.img-ph {
    background:linear-gradient(135deg,#f0f4ff,#e8f4f8); border-radius:12px;
    min-height:190px; display:flex; align-items:center; justify-content:center;
    flex-direction:column; color:#94a3b8; gap:8px;
}
.tr-result {
    background:#f8fafc; border:1.5px solid #e2e8f0; border-radius:10px;
    padding:14px 16px; min-height:148px; font-size:14px; line-height:1.75;
    color:#1e293b; white-space:pre-wrap;
}
.tr-empty { color:#94a3b8; font-style:italic }
.day-hd { text-align:center; padding:8px 4px 6px; border-radius:9px; margin-bottom:5px }
.day-hd.td { background:#eef2ff; border:1.5px solid #4361ee }
.day-hd.nd { background:#f8fafc; border:1.5px solid #e2e8f0 }
.d-nm { font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.4px }
.d-nm.td { color:#4361ee } .d-nm.nd { color:#64748b }
.d-dt { font-size:19px; font-weight:700; color:#1e293b }
.d-dt-today {
    width:30px; height:30px; background:#4361ee; color:white;
    border-radius:50%; display:inline-flex; align-items:center;
    justify-content:center; font-size:14px;
}
.sum-row { margin-top:12px; padding:10px 18px; background:#f8fafc; border-radius:9px; font-size:13px; color:#64748b }
.sum-badge { background:#4361ee; color:white; border-radius:12px; padding:2px 11px; font-size:11px; font-weight:700; margin:0 6px }
div[data-testid="stProgress"] > div > div { background:linear-gradient(90deg,#4361ee,#7c3aed) !important }
.stCheckbox label { font-size:13px !important }
div[data-testid="column"] { padding-left:4px !important; padding-right:4px !important }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# HEADER  — components.html 로 실시간 JS 시계 구현
# ─────────────────────────────────────────────────────────────────────────────
components.html("""
<style>
*{margin:0;padding:0;box-sizing:border-box;
  font-family:'Malgun Gothic','Noto Sans KR','Segoe UI',sans-serif}
.hdr{
  background:linear-gradient(120deg,#4361ee 0%,#7c3aed 55%,#a855f7 100%);
  padding:14px 28px;border-radius:0 0 18px 18px;color:#fff;
  display:flex;justify-content:space-between;align-items:center;
  box-shadow:0 4px 24px rgba(67,97,238,.28);
}
.logo{font-size:20px;font-weight:700;letter-spacing:-.5px}
.sub {font-size:12px;opacity:.75;margin-top:3px}
.clk{font-size:26px;font-weight:700;text-align:right;
     font-feature-settings:'tnum';letter-spacing:.5px}
.dt {font-size:12px;opacity:.82;text-align:right;margin-top:2px}
</style>
<div class="hdr">
  <div>
    <div class="logo">✦ Sangchan's Board</div>
    <div class="sub">Dream it. Plan it. Do it. 🚀</div>
  </div>
  <div>
    <div class="clk" id="clk">--:--:--</div>
    <div class="dt"  id="dt"></div>
  </div>
</div>
<script>
function tick(){
  var n=new Date(), p=function(x){return String(x).padStart(2,'0')};
  document.getElementById('clk').textContent=p(n.getHours())+':'+p(n.getMinutes())+':'+p(n.getSeconds());
  var D=['일','월','화','수','목','금','토'];
  document.getElementById('dt').textContent=n.getFullYear()+'.'+p(n.getMonth()+1)+'.'+p(n.getDate())+' ('+D[n.getDay()]+')';
}
tick(); setInterval(tick,500);
document.addEventListener('visibilitychange',function(){if(!document.hidden)tick()});
</script>
""", height=88)

now = datetime.now()   # 번역 날짜 등 하단 섹션에서 사용

# Mode indicator
if _db():
    st.caption("☁️ 클라우드 모드 — 모든 데이터가 어디서나 동기화됩니다")
else:
    st.caption("💻 로컬 모드 — 이 컴퓨터에서만 저장됩니다")


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 — QUOTE  (전체 너비)
# ═════════════════════════════════════════════════════════════════════════════
quotes = quotes_load()
if not quotes:
    quotes_add(DEF_QUOTES[0]["text"], DEF_QUOTES[0]["author"])
    st.rerun()

st.session_state.quote_idx = min(st.session_state.quote_idx, len(quotes) - 1)
q = quotes[st.session_state.quote_idx]

st.markdown(f"""
<div class="q-card">
  <div style="font-size:11px;font-weight:700;color:rgba(255,255,255,.65);
              text-transform:uppercase;letter-spacing:1px;margin-bottom:14px">
    💬 오늘의 글귀
  </div>
  <div class="q-text">{html_lib.escape(q['text'])}</div>
  <div class="q-author">{'— ' + html_lib.escape(q['author']) if q.get('author') else ''}</div>
</div>
""", unsafe_allow_html=True)

nc1, nc2, nc3 = st.columns([1, 2, 1])
with nc1:
    if st.button("◀ 이전", key="q_prev"):
        st.session_state.quote_idx = (st.session_state.quote_idx - 1) % len(quotes)
        st.rerun()
with nc2:
    st.markdown(
        f'<p style="text-align:center;color:#64748b;font-size:12px;margin-top:6px">'
        f'{st.session_state.quote_idx + 1} / {len(quotes)}</p>',
        unsafe_allow_html=True,
    )
with nc3:
    if st.button("다음 ▶", key="q_next"):
        st.session_state.quote_idx = (st.session_state.quote_idx + 1) % len(quotes)
        st.rerun()

with st.expander("✏️ 글귀 편집"):
    for qi in quotes:
        ec1, ec2, ec3 = st.columns([5, 3, 1])
        with ec1:
            st.text_input("", value=qi["text"], key=f"qt_{qi['id']}",
                          label_visibility="collapsed")
        with ec2:
            st.text_input("", value=qi.get("author",""), key=f"qa_{qi['id']}",
                          placeholder="출처/작가", label_visibility="collapsed")
        with ec3:
            if st.button("✕", key=f"qdel_{qi['id']}"):
                quotes_delete(qi["id"])
                st.rerun()

    if st.button("💾 편집 내용 저장", key="qsave"):
        for qi in quotes:
            t = st.session_state.get(f"qt_{qi['id']}", "").strip()
            a = st.session_state.get(f"qa_{qi['id']}", "").strip()
            if t:
                quotes_update(qi["id"], t, a)
        st.success("저장되었습니다!")
        st.rerun()

    st.divider()
    with st.form("add_quote", clear_on_submit=True):
        ac1, ac2, ac3 = st.columns([5, 3, 1])
        with ac1:
            nqt = st.text_input("", placeholder="새 글귀 내용", label_visibility="collapsed")
        with ac2:
            nqa = st.text_input("", placeholder="출처/작가", label_visibility="collapsed")
        with ac3:
            if st.form_submit_button("+ 추가") and nqt.strip():
                quotes_add(nqt.strip(), nqa.strip())
                st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1-B — 꿈 갤러리 (사진 3장 나란히)
# ═════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec-lbl" style="margin-top:18px">🌠 나의 꿈 갤러리</div>',
            unsafe_allow_html=True)

ph_cols = st.columns(3, gap="medium")
for slot, ph_col in enumerate(ph_cols):
    with ph_col:
        img_bytes = image_load(slot)
        if img_bytes:
            st.image(img_bytes, use_container_width=True)
        else:
            st.markdown(f"""
            <div class="img-ph" style="min-height:160px">
              <span style="font-size:36px">🌄</span>
              <span style="font-size:11px">사진 {slot+1} 업로드</span>
            </div>
            """, unsafe_allow_html=True)

        uploaded = st.file_uploader(
            f"사진 {slot + 1}",
            type=["jpg","jpeg","png","gif","webp"],
            key=f"img_up_{slot}",
            label_visibility="collapsed",
        )
        if uploaded is not None:
            ext = uploaded.name.rsplit(".", 1)[-1].lower()
            if ext not in {"png","jpg","jpeg","gif","webp"}:
                ext = "png"
            image_save(uploaded.getvalue(), ext, slot)
            st.rerun()

st.divider()


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — GOALS
# ═════════════════════════════════════════════════════════════════════════════
col_26, col_30 = st.columns(2, gap="medium")


def render_goals(year: str, col, icon: str):
    with col:
        st.markdown(f'<div class="sec-lbl">{icon} {year}년 목표</div>', unsafe_allow_html=True)
        g_list = goals_load(year)
        done_n  = sum(1 for g in g_list if g.get("done"))
        total_n = len(g_list)
        if total_n:
            st.progress(done_n / total_n)
            st.caption(f"{done_n} / {total_n} 달성")

        for g in g_list:
            rc, rd = st.columns([10, 1])
            with rc:
                new_val = st.checkbox(g["text"], value=g.get("done", False),
                                      key=f"g_{year}_{g['id']}")
                if new_val != g.get("done", False):
                    goals_toggle(g["id"], g["done"], year)
                    st.rerun()
            with rd:
                if st.button("✕", key=f"gd_{year}_{g['id']}"):
                    goals_delete(g["id"], year)
                    st.rerun()

        with st.form(f"add_goal_{year}", clear_on_submit=True):
            gc1, gc2 = st.columns([5, 1])
            with gc1:
                ng = st.text_input("", placeholder=f"{year}년 목표를 입력하세요",
                                   label_visibility="collapsed")
            with gc2:
                if st.form_submit_button("+") and ng.strip():
                    goals_add(year, ng.strip())
                    st.rerun()


render_goals("2026", col_26, "🎯")
render_goals("2030", col_30, "🌟")

st.divider()


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 — TRANSLATION & ENGLISH STUDY
# ═════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec-lbl">🌐 번역 &amp; 영어 학습</div>', unsafe_allow_html=True)

if not API_KEY:
    st.warning("⚠️ ANTHROPIC_API_KEY가 없습니다. Streamlit Cloud Secrets 또는 .env 파일을 확인해주세요.")

mc1, mc2 = st.columns([3, 2])
with mc1:
    tr_mode = st.radio("모드", ["번역","해석 / 설명","어휘 분석"],
                        horizontal=True, label_visibility="collapsed", key="tr_mode")
with mc2:
    lang_dir = st.selectbox("언어", ["🇰🇷 한국어 → 🇬🇧 영어","🇬🇧 영어 → 🇰🇷 한국어"],
                             label_visibility="collapsed", key="tr_lang")

ic1, ic2, ic3 = st.columns([8, 1, 8], gap="small")

with ic1:
    src_lbl = "🇰🇷 한국어 입력" if "한국어" in lang_dir.split("→")[0] else "🇬🇧 영어 입력"
    st.caption(src_lbl)
    src_text = st.text_area("", placeholder="번역할 텍스트를 입력하세요...",
                             height=155, label_visibility="collapsed", key="tr_src")

with ic2:
    st.markdown("<div style='height:42px'></div>", unsafe_allow_html=True)
    do_tr = st.button("▶▶", key="do_tr", use_container_width=True)
    if st.button("✕", key="clear_tr", use_container_width=True):
        st.session_state.tr_result = ""
        st.rerun()

with ic3:
    tgt_lbl = "🇬🇧 영어 결과" if "한국어" in lang_dir.split("→")[0] else "🇰🇷 한국어 결과"
    st.caption(tgt_lbl)
    res = st.session_state.get("tr_result", "")
    if res:
        st.markdown(f'<div class="tr-result">{html_lib.escape(res)}</div>', unsafe_allow_html=True)
        sc1, sc2 = st.columns(2)
        with sc1:
            if st.button("💾 저장", key="tr_save"):
                tr_add(src_text, res, tr_mode, now.strftime("%Y-%m-%d"))
                st.success("저장됨!")
        with sc2:
            st.caption("결과를 드래그하여 복사")
    else:
        st.markdown('<div class="tr-result tr-empty">번역 결과가 여기에 표시됩니다...</div>',
                    unsafe_allow_html=True)

if do_tr:
    if not src_text.strip():
        st.warning("텍스트를 입력해주세요.")
    elif not API_KEY:
        st.error("API 키가 필요합니다.")
    else:
        sl = "한국어" if "한국어" in lang_dir.split("→")[0] else "영어"
        tl = "영어" if sl == "한국어" else "한국어"
        prompts = {
            "번역": f"다음 {sl} 텍스트를 {tl}로 번역해주세요. 번역문만 출력하세요.\n\n{src_text}",
            "해석 / 설명": f"다음 텍스트를 분석해주세요:\n1. 의미 설명\n2. 뉘앙스/문화적 맥락\n3. {tl} 번역\n\n텍스트: {src_text}",
            "어휘 분석": f"다음 텍스트의 주요 어휘를 분석해주세요:\n1. 핵심 단어/표현 (원문→번역→예문)\n2. 유용한 관용 표현이나 문법 포인트\n\n텍스트: {src_text}",
        }
        with st.spinner("Claude가 번역 중입니다..."):
            try:
                client = anthropic.Anthropic(api_key=API_KEY)
                msg = client.messages.create(
                    model="claude-haiku-4-5-20251001", max_tokens=1500,
                    messages=[{"role": "user", "content": prompts[tr_mode]}],
                )
                st.session_state.tr_result = msg.content[0].text
                st.rerun()
            except Exception as e:
                st.error(f"번역 오류: {e}")

saved_tr = tr_load()
if saved_tr:
    with st.expander(f"📚 저장된 번역 / 학습 기록  ({len(saved_tr)}건)"):
        for i, item in enumerate(saved_tr[:10]):
            sa, sb = st.columns([7, 1])
            with sa:
                prev = item["src"][:80] + ("..." if len(item["src"]) > 80 else "")
                st.markdown(
                    f'<div style="padding:8px;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:6px">'
                    f'<span style="font-size:11px;color:#94a3b8">{item["date"]} · {item["mode"]}</span><br>'
                    f'<span style="font-size:13px">{html_lib.escape(prev)}</span></div>',
                    unsafe_allow_html=True,
                )
            with sb:
                if st.button("불러오기", key=f"load_tr_{i}"):
                    st.session_state.tr_result = item["result"]
                    st.rerun()

st.divider()


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 — WEEKLY PLANNER
# ═════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec-lbl">📅 주간 계획</div>', unsafe_allow_html=True)

today_d    = date.today()
week_start = today_d - timedelta(days=today_d.weekday()) + timedelta(weeks=st.session_state.wk_off)
week_end   = week_start + timedelta(days=4)   # 금요일까지 (5일)

wc1, wc2, wc3, wc4, wc5 = st.columns([1, 1, 4, 1, 1])
with wc1:
    if st.button("◀", key="wk_prev"): st.session_state.wk_off -= 1; st.rerun()
with wc3:
    st.markdown(
        f'<div style="text-align:center;font-weight:700;font-size:14px;padding:7px 0">'
        f'{week_start.year}년 {week_start.month}/{week_start.day}'
        f' ~ {week_end.month}/{week_end.day}  (월~금)</div>',
        unsafe_allow_html=True,
    )
with wc4:
    if st.button("▶", key="wk_next"): st.session_state.wk_off += 1; st.rerun()
with wc5:
    if st.button("오늘", key="wk_today"): st.session_state.wk_off = 0; st.rerun()

DAY_NAMES = ["월", "화", "수", "목", "금"]   # 토·일 제외
day_cols  = st.columns(5, gap="small")
total_t   = done_t = 0

for i, dc in enumerate(day_cols):
    cur_day   = week_start + timedelta(days=i)
    dk        = cur_day.strftime("%Y-%m-%d")
    is_today  = (cur_day == today_d)
    # 오름차순(가나다) 정렬
    day_tasks = sorted(tasks_load(dk), key=lambda x: x["text"])
    total_t  += len(day_tasks)
    done_t   += sum(1 for t in day_tasks if t.get("done"))

    with dc:
        cls = "td" if is_today else "nd"
        dt_html = (f'<div class="d-dt-today">{cur_day.day}</div>'
                   if is_today else f'<div class="d-dt">{cur_day.day}</div>')
        st.markdown(
            f'<div class="day-hd {cls}"><div class="d-nm {cls}">{DAY_NAMES[i]}</div>'
            f'{dt_html}</div>',
            unsafe_allow_html=True,
        )

        for task in day_tasks:
            edit_key = f"editing_{dk}_{task['id']}"
            if st.session_state.get(edit_key):
                # ── 수정 모드 ──
                new_text = st.text_input(
                    "", value=task["text"],
                    key=f"edit_inp_{dk}_{task['id']}",
                    label_visibility="collapsed",
                )
                sv1, sv2 = st.columns(2)
                with sv1:
                    if st.button("✓ 저장", key=f"save_{dk}_{task['id']}",
                                 use_container_width=True):
                        if new_text.strip():
                            tasks_update(task["id"], dk, new_text.strip())
                        st.session_state[edit_key] = False
                        st.rerun()
                with sv2:
                    if st.button("✕ 취소", key=f"cancel_{dk}_{task['id']}",
                                 use_container_width=True):
                        st.session_state[edit_key] = False
                        st.rerun()
            else:
                # ── 일반 표시 모드 ──
                tc, te, td2 = st.columns([4, 1, 1])
                with tc:
                    disp = task["text"][:13] + ("…" if len(task["text"]) > 13 else "")
                    new_done = st.checkbox(disp, value=task.get("done", False),
                                           key=f"t_{dk}_{task['id']}", help=task["text"])
                    if new_done != task.get("done", False):
                        tasks_toggle(task["id"], task["done"], dk)
                        st.rerun()
                with te:
                    if st.button("✏️", key=f"te_{dk}_{task['id']}",
                                 help="수정"):
                        st.session_state[edit_key] = True
                        st.rerun()
                with td2:
                    if st.button("✕", key=f"td_{dk}_{task['id']}"):
                        tasks_delete(task["id"], dk)
                        st.rerun()

        with st.form(key=f"tf_{dk}", clear_on_submit=True):
            nt = st.text_input("", placeholder="업무 추가", label_visibility="collapsed")
            if st.form_submit_button("+ 추가", use_container_width=True) and nt.strip():
                tasks_add(dk, nt.strip())
                st.rerun()

st.markdown(
    f'<div class="sum-row">이번 주 진행:'
    f'<span class="sum-badge">{done_t}/{total_t}</span>업무 완료</div>',
    unsafe_allow_html=True,
)
