"""
Smart Garden | Dashboard

Layout
------
Everything lives on ONE fixed 1366 x 768 design grid that is scaled to the window
(--u = screen pixels per design pixel) and centred. Cards, text blocks and every
Streamlit widget are pinned to rectangles on that grid, so alignment never depends
on Streamlit's own spacing:

    margin 28 | nav 232 | gutter 20 | content 1058 | margin 28
    header   y 22-86
    row 1    y 100-408  health | next watering | weather (weather spans rows 1-2)
    row 2    y 428-588  pump
    row 3    y 608-740  live sensor readings

All rectangles are defined once in the GEOMETRY section below.
"""
import base64
import html as _html
import re
from datetime import datetime, time
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="FloraPulse | Dashboard",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ==================================================
# BACKEND CONFIG
# ==================================================
BACKEND_URL = "http://localhost:8000"

# ==================================================
# AUTH GUARD
# ==================================================
if st.session_state.get("auth_token") is None:
    st.markdown(
        "<div style='text-align: center; padding: 50px;'><h2>You must login first</h2></div>",
        unsafe_allow_html=True,
    )
    if st.button("Go to Login"):
        st.switch_page("pages/2_Login.py")
    st.stop()

# ==================================================
# PATHS & CONSTANTS
# ==================================================
ASSETS = Path(__file__).parent / "assets"

# (label, widget key, icon)  - icons are drawn with CSS so every label lines up
NAV = [
    ("Dashboard", "nav_dashboard", "🏠"),
    ("My plants", "nav_plants", "🪴"),
    ("Weather Forecast", "nav_weather", "⛅"),
    ("Sensors", "nav_sensors", "📡"),
    ("Analytics", "nav_analytics", "📊"),
    ("About us", "nav_about", "ℹ️"),
    ("Settings", "nav_settings", "⚙️"),
]
PAGE_MAP = {
    "Settings": "pages/10_Settings.py",
    "Analytics": "pages/11_Analytics.py",
    "Sensors": "pages/9_Sensors.py",
    "Weather Forecast": "pages/12_Weather.py",
    "About us": "pages/7_About.py",
    "Profile": "pages/8_Profile.py",
}
ART = {"plant": "plant.png", "can": "watering_can.png"}
ART_SIZE = {"plant": (58, 56), "can": (54, 58)}
clamp = lambda v, lo, hi: max(lo, min(hi, v))
esc = lambda s: _html.escape(str(s))

# ==================================================
# GEOMETRY  (design pixels on the 1366 x 768 grid)
# ==================================================
GUT = 20                                   # gap between all cards
PAD = 22                                   # inner padding of a card (border included)

NAV_R = (28, 100, 232, 640)
HEALTH_R = (280, 100, 350, 308)
WATER_R = (650, 100, 350, 308)
WEATHER_R = (1020, 100, 318, 488)
PUMP_R = (280, 428, 720, 160)
SENS_R = (280, 608, 1058, 132)
PANEL_R = (280, 100, 1058, 640)


def inner(r, pad=PAD):
    x, y, w, h = r
    return x + pad, y + pad, w - 2 * pad, h - 2 * pad


# ---- header -----------------------------------------------------------------
GREET_R = (28, 22, 760, 60)
WHO_R = (1060, 28, 220, 42)
AVATAR_R = (1292, 26, 46, 46)

# ---- nav card (inner padding 14, so buttons are 204 wide) --------------------
_nx, _ny, _nw, _nh = NAV_R
NAV_IX, NAV_IW = _nx + 14, _nw - 28
BRAND_R = (_nx + 22, _ny + 20, _nw - 44, 40)
NAV_BTN_Y0, NAV_BTN_H, NAV_BTN_PITCH = _ny + 72, 44, 52
SNAP_R = (NAV_IX, _ny + 460, NAV_IW, 56)
LIVE_R = (NAV_IX + 8, _ny + 526, NAV_IW - 8, 30)
LOGOUT_R = (NAV_IX, _ny + 566, NAV_IW, 44)

# ---- plant health ------------------------------------------------------------
hx, hy, hw, hh = inner(HEALTH_R)
HEALTH_HDR_R = (hx, hy, hw, 54)
SEL_PLANT_R = (hx, hy + 62, hw, 40)
HEALTH_ROW_R = (hx, hy + 116, hw, 136)

# ---- next watering -----------------------------------------------------------
wx, wy, ww, wh = inner(WATER_R)
WATER_HDR_R = (wx, wy, ww, 54)
PILL_R = (wx, wy + 62, ww, 52)
MINI_R = (wx, wy + 122, ww, 20)
RULE_R = (wx, wy + 150, ww, 1)
SCHED_LBL_R = (wx, wy + 160, 150, 16)
SCHED_R = (wx, wy + 178, 150, 36)
AUTO_SCHED_R = (wx + 166, wy + 180, ww - 166, 32)
WATER_NOW_R = (wx, wy + 224, ww, 40)

# ---- weather -----------------------------------------------------------------
cx, cy, cw, ch = inner(WEATHER_R)
WEATHER_HDR_R = (cx, cy, cw, 26)
CITY_R = (cx, cy + 38, 160, 38)
UNIT_R = (cx + 170, cy + 38, cw - 170, 38)
WNOW_R = (cx, cy + 90, cw, 50)
CHIPS_R = (cx, cy + 152, cw, 46)
WLIST_R = (cx, cy + 212, cw, 150)
TIP_R = (cx, cy + 376, cw, 52)

# ---- pump --------------------------------------------------------------------
px_, py_, pw_, ph_ = inner(PUMP_R)
PUMP_TITLE_R = (px_, py_, pw_, 26)
PUMP_STATUS_R = (px_, py_ + 36, 228, 80)
PUMP_VR1_R = (px_ + 238, py_ + 40, 1, 72)
MODE_LBL_R = (px_ + 254, py_ + 38, 184, 16)
MODE_R = (px_ + 254, py_ + 54, 184, 30)
PUMP_ON_R = (px_ + 254, py_ + 88, 184, 28)
PUMP_VR2_R = (px_ + 454, py_ + 40, 1, 72)
THR_LBL_R = (px_ + 470, py_ + 38, 206, 18)
THR_R = (px_ + 470, py_ + 60, 206, 56)

# ---- sensors -----------------------------------------------------------------
SENS_IN_R = inner(SENS_R)

# widgets pinned on the grid: Streamlit key -> rectangle
WIDGETS = {
    "profile": AVATAR_R,
    "live": LIVE_R,
    "logout": LOGOUT_R,
    "sel_plant": SEL_PLANT_R,
    "sched": SCHED_R,
    "auto_sched": AUTO_SCHED_R,
    "water_now": WATER_NOW_R,
    "dash_city": CITY_R,
    "dash_unit": UNIT_R,
    "mode": MODE_R,
    "pump_on": PUMP_ON_R,
    "thr": THR_R,
}
for _i, (_label, _key, _icon) in enumerate(NAV):
    WIDGETS[_key] = (NAV_IX, NAV_BTN_Y0 + _i * NAV_BTN_PITCH, NAV_IW, NAV_BTN_H)


# ==================================================
# BACKEND API
# ==================================================
WATER_THRESHOLD = 35

def api(method: str, path: str, **kwargs):
    """Authenticated backend request. Returns (JSON, error)."""
    token = st.session_state.get("auth_token")
    if not token:
        return None, "You are not logged in."
    try:
        response = requests.request(
            method, f"{BACKEND_URL}{path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10, **kwargs
        )
    except requests.exceptions.RequestException:
        return None, "Cannot reach backend. Is it running?"

    if response.status_code == 401:
        st.session_state.auth_token = None
        st.toast("Session expired. Please log in again.")
        st.switch_page("pages/2_Login.py")
        st.stop()
    if response.status_code >= 400:
        try:
            return None, response.json().get("detail", f"Error {response.status_code}")
        except ValueError:
            return None, f"Backend error {response.status_code}"
    try:
        return response.json(), None
    except ValueError:
        return {}, None


def load_plants_from_backend() -> dict:
    data, err = api("GET", "/api/plants/my-plants")
    if err:
        st.error(f"Could not load plants: {err}")
        return {}
    plants = {}
    for item in (data or {}).get("plants", []):
        name = item.get("name") or f"Plant {item.get('id')}"
        plants[name] = {
            "id": item.get("id"), "emoji": "🌱",
            "mlo": 30, "mhi": 70, "tlo": 16, "thi": 30,
            "moisture": 0, "temp": 0, "hum": 0, "light": 0,
            "rain": False, "has_data": False, "last_ts": None, "hist": [],
        }
    return plants


def load_sensor_history(plant_id: int, limit: int = 60) -> list:
    data, err = api("GET", "/api/sensor-data/history",
                    params={"plant_id": plant_id, "limit": limit})
    if err:
        st.warning(f"Could not load sensor history: {err}")
        return []
    readings = (data or {}).get("readings", [])
    return sorted(readings, key=lambda item: str(item.get("timestamp", "")))


def load_prediction(plant_id: int) -> dict:
    data, _ = api("GET", f"/api/plants/{plant_id}/next-watering-prediction")
    return data or {}


def load_pump(plant_id: int) -> dict:
    data, _ = api("GET", f"/api/plants/{plant_id}/pump-status")
    return data or {}


def load_decision(plant_id: int) -> dict:
    data, _ = api("GET", f"/api/plants/{plant_id}/latest-decision")
    return data or {}


def load_weather() -> dict:
    data, err = api("GET", "/api/weather/current")
    return {} if err else (data or {})


def get_current_user(token: str) -> str:
    data, _ = api("GET", "/api/auth/me")
    return (data or {}).get("username", "Gardener")


# ==================================================
# STYLES
# ==================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;500;600&family=Nunito:wght@400;600;700;800&display=swap');
:root{--u:min(100vw / 1366, 100vh / 768);--line:#6b9a22;--ink:#2b3f12;--mute:#68803a;--soft:#f3f9ec;
      --good:#6aaa4a;--warn:#e0a030;--bad:#d0583a;--head:'Fredoka','Nunito',sans-serif}
html,body{overflow:hidden!important}
html,body,.stApp,.stApp *:not([data-testid="stIconMaterial"]),[data-baseweb="popover"] *{font-family:'Nunito','Segoe UI',sans-serif}
.h,.gt,.brand,.who b,.ring b,.wnow b,.pst b,.stt b,.mv,.chips b,.stats b,.snap b,.avatar-name{font-family:var(--head)!important}

/* ---------- page shell: no scrolling, one fixed stage ---------- */
.stApp{background:%%BG%% center / cover no-repeat fixed}
header,[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],footer,#MainMenu{display:none!important}
[data-testid="stAppViewContainer"],[data-testid="stMain"]{overflow:hidden!important}
.block-container,[data-testid="stMainBlockContainer"]{max-width:100%!important;padding:0!important}
.stApp [data-testid="stMarkdownContainer"] p{margin:0}
.st-key-stage{position:fixed!important;top:50%;left:50%;transform:translate(-50%,-50%);
  width:@{1366}!important;height:@{768}!important;max-width:none!important;min-width:0!important;
  margin:0;gap:0;display:block!important}
.st-key-shells{position:absolute;inset:0;margin:0;pointer-events:none}

/* ---------- cards + text blocks (all absolutely positioned on the grid) ---------- */
.card{position:absolute;box-sizing:border-box;background:#fff;border:max(2px,@{3}) solid var(--line);
  border-radius:@{32};box-shadow:@{8} @{10} @{16} rgba(0,0,0,.18)}
.blk{position:absolute;box-sizing:border-box;color:var(--ink)}
.h{font-size:@{22};font-weight:500;line-height:1.15;color:var(--ink)}
.sub{font-size:@{14};line-height:1.3;color:var(--mute);margin-top:@{3}}
.lbl{font-size:@{13};line-height:1.2;font-weight:600;color:var(--mute)}
.rule{background:#e3eed3}
.vr{background:#e3eed3;width:100%;height:100%}
.hdr{display:flex;align-items:flex-start;justify-content:space-between;gap:@{10};height:100%}
.art{flex:none;background:center / contain no-repeat}
%%ART%%
.tag{flex:none;font-size:@{11};font-weight:700;color:var(--mute);background:var(--soft);border-radius:999px;padding:@{3} @{9}}

/* ---------- header: greeting + profile ---------- */
.gt{font-size:@{30};font-weight:500;line-height:1.15;color:var(--ink)}
.gs{font-size:@{15};line-height:1.3;color:var(--mute);margin-top:@{4}}
.who{height:100%;display:flex;flex-direction:column;justify-content:center;text-align:right;line-height:1.2}
.who b{font-size:@{17};font-weight:500}
.who span{font-size:@{13};color:var(--mute)}
.st-key-profile{height:@{46};width:@{46}}
.st-key-profile [data-testid="stPopover"]{width:100%}
.st-key-profile button{width:@{46}!important;height:@{46}!important;min-height:0!important;min-width:0!important;
  padding:0!important;margin:0;display:flex!important;align-items:center;justify-content:center;
  border-radius:50%!important;border:max(2px,@{3}) solid #fff!important;overflow:hidden;
  background:linear-gradient(135deg,#8fdc55,#5fa83a)!important;box-shadow:@{3} @{5} @{10} rgba(0,0,0,.25)!important}
.st-key-profile button>*{margin:0!important;padding:0!important;display:flex;align-items:center;justify-content:center}
.st-key-profile button p{font-family:var(--head)!important;font-size:@{20};font-weight:500;line-height:1;color:#fff}
.st-key-profile button [data-testid="stIconMaterial"],.st-key-profile button svg{display:none!important}
[data-testid="stPopoverBody"]{border-radius:@{18}}
.avatar-name{font-size:@{18};font-weight:500}

/* ---------- navigation ---------- */
.brand{display:flex;align-items:center;gap:@{10};font-size:@{21};font-weight:500;white-space:nowrap;height:100%}
.brand i{width:@{38};height:@{38};border-radius:50%;display:grid;place-items:center;font-style:normal;font-size:@{20};
  background:linear-gradient(135deg,#dff2c6,#b9e08a)}
.snap{height:100%;display:flex;flex-direction:column;justify-content:center;background:var(--soft);
  border-radius:@{16};padding:0 @{14};font-size:@{14};line-height:1.3;color:var(--mute)}
.snap b{font-size:@{17};font-weight:500;color:var(--ink)}
%%NAVBTN%%
@media (prefers-reduced-motion:reduce){:is(%%NAVSEL%%) button:hover{transform:none}}

/* ---------- native widgets: pinned + sized in design pixels ---------- */
:is(%%WSEL%%){position:absolute;margin:0;display:flex;flex-direction:column;justify-content:center;z-index:3}
:is(.st-key-sel_plant,.st-key-dash_city) [data-baseweb="select"]>div,
.st-key-sched [data-baseweb="select"]>div{min-height:@{38};height:@{38};border-radius:@{12};background:var(--soft);border-color:#b9d98f}
.st-key-sched [data-baseweb="select"]>div,.st-key-sched [data-baseweb="input"]{min-height:@{36};height:@{36}}
:is(.st-key-sel_plant,.st-key-dash_city,.st-key-sched) [data-baseweb="select"] *,.st-key-sched input{font-size:@{15}}
.st-key-sched [data-baseweb="input"]{border-radius:@{12};background:var(--soft)}
.st-key-sched input{height:@{36};background:var(--soft)}
[data-testid="stToggle"] p,[data-testid="stRadio"] label p{font-size:@{14};color:var(--ink)}
[data-testid="stRadio"] [role="radiogroup"]{gap:@{14}}
[data-baseweb="radio"]:has(input:checked)>:is(div,span):first-child{background:var(--good)!important;border-color:var(--good)!important}
[data-baseweb="slider"] [role="slider"]{background:var(--good)!important;box-shadow:none!important}
[data-testid="stSliderTickBarMin"],[data-testid="stSliderTickBarMax"],[data-testid="stThumbValue"]{font-size:@{12}}

/* ---------- plant health ---------- */
.hrow{display:flex;align-items:center;gap:@{18};height:100%}
.ring{flex:none;width:@{116};height:@{116};border-radius:50%;display:flex;flex-direction:column;align-items:center;justify-content:center;
  background:radial-gradient(closest-side,#fff 76%,transparent 78%),conic-gradient(var(--c) calc(var(--s) * 1%),#e4efd3 0)}
.ring b{font-size:@{32};font-weight:500;line-height:1}
.ring span{font-size:@{12};color:var(--mute)}
.stats{flex:1;min-width:0;display:flex;flex-direction:column;gap:@{8}}
.stats div{height:@{40};box-sizing:border-box;display:flex;justify-content:space-between;align-items:center;
  background:var(--soft);border-radius:@{12};padding:0 @{12};font-size:@{14};color:var(--mute)}
.stats b{font-size:@{17};font-weight:500;color:var(--ink)}

/* ---------- next watering ---------- */
.pill{height:100%;box-sizing:border-box;display:flex;flex-direction:column;justify-content:center;gap:@{2};
  border-radius:@{14};padding:0 @{16}}
.pill b{font-size:@{16};font-weight:700;line-height:1.2}
.pill span{font-size:@{13};line-height:1.2;opacity:.85}
.pill.good{background:#e8f4d9;color:#2e5a14}
.pill.warn{background:#fff3d6;color:#7a5410}
.pill.bad{background:#fde4dd;color:#8a2f18}
.pill.info{background:#e9f2fb;color:#24506e}
.mini{display:flex;justify-content:space-between;font-size:@{13};line-height:1.4;color:var(--mute)}
.mini b{color:var(--ink);font-weight:700}
:is(.st-key-water_now,.st-key-panel) button{width:100%;border:none;border-radius:999px;min-height:0;height:@{40};
  background:linear-gradient(90deg,#6fb23f,#93c548);box-shadow:@{3} @{5} @{8} rgba(0,0,0,.2);transition:filter .15s ease,transform .15s ease}
:is(.st-key-water_now,.st-key-panel) button p{font-size:@{16};font-weight:700;color:#fff}
:is(.st-key-water_now,.st-key-panel) button:hover{filter:brightness(.94);transform:translateY(-1px)}

/* ---------- weather ---------- */
.wnow{height:100%;display:flex;align-items:center;justify-content:center;gap:@{12}}
.wnow span{font-size:@{38}}
.wnow b{font-size:@{38};font-weight:500}
.chips{height:100%;display:grid;grid-template-columns:repeat(3,1fr);gap:@{8}}
.chips div{box-sizing:border-box;display:flex;flex-direction:column;justify-content:center;text-align:center;
  font-size:@{13};line-height:1.25;color:var(--mute);background:var(--soft);border-radius:@{12}}
.chips b{font-size:@{16};font-weight:500;color:var(--ink)}
.wlist{display:flex;flex-direction:column}
.wrow{display:grid;grid-template-columns:@{54} @{30} 1fr @{62};align-items:center;font-size:@{14};height:@{30};
  padding:0 @{8};border-radius:@{10}}
.wrow:nth-child(odd){background:var(--soft)}
.tip{height:100%;box-sizing:border-box;display:flex;align-items:center;font-size:@{14};line-height:1.3;
  background:#fff6dc;border-radius:@{12};padding:0 @{12}}

/* ---------- pump ---------- */
.pst{height:100%;display:flex;align-items:center;gap:@{14}}
.pst b{font-size:@{28};font-weight:500;display:block;line-height:1.1}
.pst small{font-size:@{14};color:var(--mute)}
.dot{flex:none;width:@{44};height:@{44};border-radius:50%;background:#cfd8c3}
.dot.on{background:var(--good);animation:pulse 1.6s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(106,170,74,.55)}100%{box-shadow:0 0 0 @{16} rgba(106,170,74,0)}}
@media (prefers-reduced-motion:reduce){.dot.on{animation:none}}

/* ---------- live sensor readings ---------- */
.sens{height:100%;display:grid;grid-template-columns:@{170} repeat(5,1fr);gap:@{22};align-items:center}
.stt b{display:block;font-size:@{20};font-weight:500;line-height:1.15}
.stt span{display:block;font-size:@{13};line-height:1.3;color:var(--mute);margin-top:@{3};white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.m{min-width:0}
.ml{font-size:@{14};line-height:1.2;color:var(--mute);display:flex;align-items:center;gap:@{6};white-space:nowrap}
.ml i{width:@{9};height:@{9};border-radius:50%}
.mv{font-size:@{30};font-weight:500;line-height:1.15}
.mv small{font-size:@{14};font-family:'Nunito'!important;color:var(--mute);margin-left:@{3}}
.m svg{width:100%;height:@{20};display:block;margin-top:@{3}}
.bar{width:100%;background:#e4efd3;border-radius:@{10};position:relative;height:@{10};margin-top:@{9}}
.bar i{position:absolute;inset:0 auto 0 0;border-radius:@{10}}

/* ---------- "My plants" panel (flowing content inside one card) ---------- */
.st-key-panel{position:absolute;box-sizing:border-box;background:#fff;color:var(--ink);overflow-y:auto;
  border:max(2px,@{3}) solid var(--line);border-radius:@{32};padding:@{22} @{26};gap:@{12};
  box-shadow:@{8} @{10} @{16} rgba(0,0,0,.18);z-index:3}
.st-key-add_plant{width:@{220}!important}
.pcard{background:var(--soft);border-radius:@{18};padding:@{12};text-align:center;font-size:@{18};font-weight:600}
.pcard span{font-size:@{34};display:block}
.pcard i{display:block;font-style:normal;font-size:@{15};font-weight:400}
</style>
"""


def U(s: str) -> str:
    """'@{N}' = N design pixels -> calc(var(--u) * N)."""
    return re.sub(r"@\{(\d+(?:\.\d+)?)\}", r"calc(var(--u) * \1)", s)


def rect_css(r) -> str:
    x, y, w, h = r
    return f"left:@{{{x}}};top:@{{{y}}};width:@{{{w}}};height:@{{{h}}}"


@st.cache_data(show_spinner=False)
def art_css() -> str:
    out = ""
    for key, fname in ART.items():
        p = ASSETS / fname
        if p.exists():
            w, h = ART_SIZE[key]
            out += (
                f".art-{key}{{width:@{{{w}}};height:@{{{h}}};"
                f"background-image:url(data:image/png;base64,{base64.b64encode(p.read_bytes()).decode()})}}"
            )
    return out


@st.cache_data(show_spinner=False)
def bg_uri() -> str:
    for name in ("garden_bg.png", "background.jpg"):
        p = ASSETS / name
        if p.exists():
            mime = "image/png" if p.suffix == ".png" else "image/jpeg"
            return f'url("data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}")'
    return "linear-gradient(160deg,#e9f7df,#f3fbee 50%,#d8f0c4)"


def build_css(bg: str = None, art: str = None) -> str:
    nav_keys = [k for _, k, _ in NAV] + ["logout"]
    nav_sel = ",".join(f".st-key-{k}" for k in nav_keys)
    nav_btn = (
        f":is({nav_sel}) button{{justify-content:flex-start!important;gap:@{{10}};width:100%;height:@{{44}};min-height:0;"
        f"padding:0 @{{14}}!important;border:none!important;border-radius:@{{22}};background:transparent!important;"
        f"box-shadow:none!important;transition:transform .15s ease,background .15s ease}}"
        f":is({nav_sel}) button::before{{display:inline-flex;justify-content:center;flex:none;width:@{{26}};font-size:@{{18}}}}"
        f":is({nav_sel}) button p{{font-size:@{{17}};font-weight:600;color:var(--ink);white-space:nowrap}}"
        f":is({nav_sel}) button:hover{{background:#eaf5dc!important;transform:translateX(@{{4}})}}"
        f":is({nav_sel}) button:is([kind=primary],[data-testid=stBaseButton-primary]){{"
        f"background:linear-gradient(90deg,#d9efc0,#eef8e2)!important;box-shadow:inset @{{4}} 0 0 var(--line)!important}}"
        f":is({nav_sel}) button:is([kind=primary],[data-testid=stBaseButton-primary]) p{{font-weight:700}}"
        + "".join(f'.st-key-{k} button::before{{content:"{icon}"}}' for _, k, icon in NAV)
        + '.st-key-logout button::before{content:"🚪"}'
    )
    widget_sel = ",".join(f".st-key-{k}" for k in WIDGETS)
    rules = "".join(f".st-key-{k}{{{rect_css(r)}}}" for k, r in WIDGETS.items())
    rules += f".st-key-panel{{{rect_css(PANEL_R)}}}"
    css = (
        CSS.replace("%%BG%%", bg if bg is not None else bg_uri())
        .replace("%%ART%%", art if art is not None else art_css())
        .replace("%%NAVBTN%%", nav_btn)
        .replace("%%NAVSEL%%", nav_sel)
        .replace("%%WSEL%%", widget_sel)
        .replace("</style>", rules + "</style>")
    )
    return U(css)


def inject_css() -> None:
    st.markdown(build_css(), unsafe_allow_html=True)


def pick(data: dict, *keys, default=None):
    for key in keys:
        if data.get(key) is not None:
            return data[key]
    return default


def current_plant_id():
    plant = st.session_state.plants.get(st.session_state.get("sel_plant")) or {}
    return plant.get("id")


# ==================================================
# HELPER FUNCTIONS
# ==================================================
def health(p: dict) -> int:
    fit = lambda v, lo, hi, tol: 1 - min(1, max(lo - v, v - hi, 0) / tol)
    return round(100 * (
        .6 * fit(p["moisture"], p["mlo"], p["mhi"], 25)
        + .25 * fit(p["temp"], p["tlo"], p["thi"], 10)
        + .15 * fit(p["hum"], 35, 85, 30)
    ))


def status(score: int):
    if score >= 80:
        return ("Thriving", "var(--good)")
    elif score >= 60:
        return ("Doing okay", "var(--warn)")
    else:
        return ("Needs care", "var(--bad)")


def T(c: float) -> str:
    if st.session_state.get("dash_unit", "°C") == "°F":
        return f"{c * 9 / 5 + 32:.0f}°F"
    return f"{c:.0f}°C"


def html(s: str) -> None:
    st.markdown(U(s), unsafe_allow_html=True)


# ==================================================
# CALLBACKS
# ==================================================
def nav_to(page: str) -> None:
    try:
        st.switch_page(page)
    except Exception:
        if page.startswith("pages/"):
            st.switch_page(page[len("pages/"):])
        else:
            st.switch_page(f"pages/{page}")


def go(view: str) -> None:
    st.session_state.view = view
    if view in PAGE_MAP:
        nav_to(PAGE_MAP[view])


def open_plant(name: str) -> None:
    st.session_state.sel_plant = name
    st.session_state.view = "Dashboard"


def water_now() -> None:
    plant_id = current_plant_id()
    if not plant_id:
        st.toast("⚠️ Select a plant first.")
        return
    _, err = api("POST", f"/api/plants/{plant_id}/water-now")
    if err:
        st.toast(f"⚠️ {err}")
    else:
        st.toast("💧 Watering command queued. The pump starts at the device's next check-in (up to 30 seconds).")


def logout() -> None:
    st.session_state.auth_token = None
    st.session_state.pop("plants", None)
    st.session_state.pop("sel_plant", None)
    st.toast("Logged out")
    nav_to("pages/2_Login.py")


# ==================================================
# HTML BUILDERS  (pure functions: data in, markup out)
# ==================================================
def card(r, cls: str = "") -> str:
    return f'<div class="card {cls}" style="{rect_css(r)}"></div>'


def blk(r, body: str, cls: str = "") -> str:
    return f'<div class="blk {cls}" style="{rect_css(r)}">{body}</div>'


def greeting_parts(name: str, now: datetime):
    h = now.hour
    part, icon = ("morning", "☀️") if h < 12 else ("afternoon", "🌤️") if h < 17 else ("evening", "🌙")
    return f"Good {part}, {esc(name)} {icon}", f"{now:%A}, {now.day} {now:%B} · Here’s how your garden is doing today"


def header_html(name: str, now: datetime) -> str:
    title, sub = greeting_parts(name, now)
    return (
        blk(GREET_R, f'<div class="gt">{title}</div><div class="gs">{sub}</div>')
        + blk(WHO_R, f'<div class="who"><b>{esc(name)}</b><span>Gardener</span></div>')
    )


def nav_html(plant_count: int, now: datetime) -> str:
    plural = "plant" if plant_count == 1 else "plants"
    return (
        card(NAV_R)
        + blk(BRAND_R, '<div class="brand"><i>🌱</i>FloraPulse</div>')
        + blk(SNAP_R, f'<div class="snap"><b>{now:%a, %d %b}</b>{plant_count} {plural} linked</div>')
    )


def health_html(p: dict | None) -> str:
    hdr = (
        '<div class="hdr"><div><div class="h">Plant health</div><div class="sub">Pick a plant to inspect</div></div>'
        '<div class="art art-plant"></div></div>'
    )
    if not p:
        row = (
            '<div class="hrow"><div class="ring" style="--s:0;--c:#cfd8c3"><b>—</b><span>No plant</span></div>'
            '<div class="stats"><div>Soil<b>—</b></div>'
            '<div>Air<b>—</b></div>'
            '<div>Humidity<b>—</b></div></div></div>'
        )
        return card(HEALTH_R) + blk(HEALTH_HDR_R, hdr) + blk(HEALTH_ROW_R, row)

    if not p.get("has_data"):
        row = (
            '<div class="hrow"><div class="ring" style="--s:0;--c:#cfd8c3"><b>—</b><span>No data</span></div>'
            '<div class="stats"><div>Soil<b>—</b></div>'
            '<div>Air<b>—</b></div>'
            '<div>Humidity<b>—</b></div></div></div>'
        )
        return card(HEALTH_R) + blk(HEALTH_HDR_R, hdr) + blk(HEALTH_ROW_R, row)

    s = health(p)
    lab, col = status(s)
    row = (
        f'<div class="hrow"><div class="ring" style="--s:{s};--c:{col}"><b>{s}</b><span>{lab}</span></div>'
        f'<div class="stats"><div>Soil<b>{p["moisture"]:.0f}%</b></div>'
        f'<div>Air<b>{T(p["temp"])}</b></div>'
        f'<div>Humidity<b>{p["hum"]:.0f}%</b></div></div></div>'
    )
    return card(HEALTH_R) + blk(HEALTH_HDR_R, hdr) + blk(HEALTH_ROW_R, row)


def prediction_view(pred: dict):
    """-> (kind, title, subtitle) for the status pill."""
    if not pred:
        return "info", "⏳ Collecting data", "Waiting for enough sensor readings"
    status_value = pred.get("status")
    hours = pred.get("next_watering_in_hours")
    friendly = pred.get("estimated_time_friendly")
    sub = f"Estimated: {friendly}" if friendly else "Based on the recent drying trend"
    if status_value == "WATER_NOW":
        return "bad", "💧 Water now", sub
    if status_value == "WATER_SOON":
        return "warn", "💧 Water soon" + (f" — {hours:.1f} h" if hours is not None else ""), sub
    if hours is not None:
        if hours > 8:
            return "good", f"🌱 Next watering in {hours:.1f} h", sub
        if hours >= 4:
            return "warn", f"💧 Next watering in {hours:.1f} h", sub
        return "bad", f"🔴 Watering in {hours:.1f} h", sub
    return "info", "🌱 Plant is stable", sub if friendly else "No watering needed right now"


def water_html(pred: dict, has_plant: bool = True) -> str:
    hdr = (
        '<div class="hdr"><div><div class="h">Next watering</div><div class="sub">Predicted from moisture trend</div></div>'
        '<div class="art art-can"></div></div>'
    )
    if not has_plant:
        mini = (
            '<div class="mini"><span>Moisture <b>—</b></span>'
            '<span>Drying <b>—</b></span>'
            '<span>Confidence <b>—</b></span></div>'
        )
        return (
            card(WATER_R)
            + blk(WATER_HDR_R, hdr)
            + blk(PILL_R, '<div class="pill info"><b>🌱 No plant selected</b><span>Pick a plant above to view predictions</span></div>')
            + blk(MINI_R, mini)
            + blk(RULE_R, "", "rule")
            + blk(SCHED_LBL_R, '<div class="lbl">Water daily at</div>')
        )

    kind, title, sub = prediction_view(pred)
    pred = pred or {}
    fmt = lambda v, f: "—" if v is None else f.format(v)
    confidence = pred.get("confidence")
    if confidence is not None and confidence <= 1:
        confidence *= 100
    confidence_text = f"{confidence:.0f}%" if confidence is not None else "—"
    mini = (
        f'<div class="mini"><span>Moisture <b>{fmt(pred.get("current_moisture"), "{:.0f}%")}</b></span>'
        f'<span>Drying <b>{fmt(pred.get("depletion_rate_per_hour"), "{:.2f}%/h")}</b></span>'
        f'<span>Confidence <b>{confidence_text}</b></span></div>'
    )
    return (
        card(WATER_R)
        + blk(WATER_HDR_R, hdr)
        + blk(PILL_R, f'<div class="pill {kind}"><b>{title}</b><span>{esc(sub)}</span></div>')
        + blk(MINI_R, mini)
        + blk(RULE_R, "", "rule")
        + blk(SCHED_LBL_R, '<div class="lbl">Water daily at</div>')
    )


def weather_html(w: dict) -> str:
    w = w or {}
    if not w or not w.get("available", True):
        body = '<div class="tip">⚠️ Live weather unavailable. Irrigation will use sensor-based decisions.</div>'
        return card(WEATHER_R) + blk(WEATHER_HDR_R, '<div class="h">Weather forecast</div>') + blk(TIP_R, body)

    rain_p = pick(w, "rain_probability", default=0) or 0
    temp = pick(w, "temp", "temperature")
    clouds = pick(w, "cloud_coverage", "clouds")
    rain_mm = pick(w, "rainfall_mm", "rain_mm")
    icon = "🌧️" if rain_p >= 60 else "⛅" if rain_p >= 30 else "☀️"
    fmt = lambda value, suffix: f"{value:.0f}{suffix}" if isinstance(value, (int, float)) else "—"
    current = f'<div class="wnow"><span>{icon}</span><b>{T(temp) if isinstance(temp, (int, float)) else "—"}</b></div>'
    chips = (
        f'<div class="chips"><div><b>{fmt(rain_p, "%")}</b>rain (24h)</div>'
        f'<div><b>{fmt(clouds, "%")}</b>clouds</div>'
        f'<div><b>{fmt(rain_mm, " mm")}</b>rainfall</div></div>'
    )
    tip = ("Rain likely in the next 24 h. Automatic irrigation may be skipped."
           if rain_p > 50 else "Low rain chance. Irrigation follows soil moisture.")
    city = esc(w.get("city", ""))
    return (
        card(WEATHER_R)
        + blk(WEATHER_HDR_R, f'<div class="hdr"><div class="h">Weather forecast</div><div class="tag">LIVE</div></div>')
        + blk(WNOW_R, current)
        + blk(CHIPS_R, chips)
        + blk(TIP_R, f'<div class="tip">💡 {tip}</div>')
        + blk(WLIST_R, f'<div class="src">OpenWeather · {city} · refreshed by backend</div>')
    )


def pump_html(pump: dict, decision: dict, has_plant: bool = True) -> str:
    if not has_plant:
        status_body = (
            '<div class="pst"><div class="dot"></div><div>'
            '<b>—</b><small>No plant selected</small></div></div>'
        )
        return (
            card(PUMP_R)
            + blk(PUMP_TITLE_R, '<div class="h">Pump status</div>')
            + blk(PUMP_STATUS_R, status_body)
            + blk(PUMP_VR1_R, "", "vr")
            + blk(MODE_LBL_R, '<div class="lbl">Last run</div><div class="dec"><b>—</b></div>')
            + blk(PUMP_VR2_R, "", "vr")
            + blk(THR_LBL_R, '<div class="lbl">Latest decision</div><div class="dec"><b>Select a plant</b><small>Pick a plant above to inspect status</small></div>')
        )

    pump = pump or {}
    decision = decision or {}
    if pump.get("active"):
        state, sub, dot = "ON", "Watering now", "on"
    elif pump.get("pending_manual"):
        state, sub, dot = "QUEUED", "Waiting for device check-in", "q"
    elif pump:
        state, sub, dot = "OFF", (
            f"Cooldown {pump.get('cooldown_minutes')} min"
            if pump.get("cooldown_minutes") else "Idle"
        ), ""
    else:
        state, sub, dot = "—", "Pump status unavailable", ""

    last = "Never"
    if pump.get("last_run"):
        try:
            last = pd.to_datetime(pump["last_run"], utc=True).tz_convert(
                "Asia/Kolkata"
            ).strftime("%d %b, %I:%M %p")
        except (ValueError, TypeError):
            last = str(pump["last_run"])

    reason = esc((decision.get("reason") or pump.get("last_reason") or "")[:110])
    decision_name = esc(decision.get("decision") or "No decisions yet")
    conf = decision.get("confidence")
    if conf is not None and conf <= 1:
        conf *= 100
    conf_text = f" · {conf:.0f}% confidence" if conf is not None else ""
    status_body = (
        f'<div class="pst"><div class="dot {dot}"></div><div>'
        f'<b>{state}</b><small>{esc(sub)}</small></div></div>'
    )
    return (
        card(PUMP_R)
        + blk(PUMP_TITLE_R, '<div class="h">Pump status</div>')
        + blk(PUMP_STATUS_R, status_body)
        + blk(PUMP_VR1_R, "", "vr")
        + blk(MODE_LBL_R, f'<div class="lbl">Last run</div><div class="dec"><b>{last}</b></div>')
        + blk(PUMP_VR2_R, "", "vr")
        + blk(THR_LBL_R, f'<div class="lbl">Latest decision</div><div class="dec"><b>{decision_name}</b>{conf_text}<small>{reason}</small></div>')
    )

def spark(vals: list, col: str) -> str:
    # Remove missing or invalid sensor readings
    vals = [v for v in vals if isinstance(v, (int, float))]

    # No valid history: show a faint dashed baseline
    if len(vals) < 2:
        return (
            '<svg viewBox="0 0 100 28" preserveAspectRatio="none">'
            '<line x1="0" y1="14" x2="100" y2="14" '
            'stroke="#d5e6bd" stroke-width="2" stroke-dasharray="4 4" '
            'vector-effect="non-scaling-stroke"/></svg>'
        )

    lo = min(vals)
    r = (max(vals) - lo) or 1

    pts = " ".join(
        f"{i * 100 / (len(vals) - 1):.1f},{27 - (v - lo) / r * 25:.1f}"
        for i, v in enumerate(vals)
    )

    return (
        f'<svg viewBox="0 0 100 28" preserveAspectRatio="none">'
        f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2" '
        f'vector-effect="non-scaling-stroke"/></svg>'
    )

def sensors_html(p: dict | None, plant_name: str | None, live: bool, now: datetime) -> str:
    if not p or not plant_name:
        rows = [
            ("Soil moisture", "—", "%", True, None),
            ("Temperature", "—", "°C", True, None),
            ("Humidity", "—", "%", True, None),
            #("Light", "—", "klux", True, None),
            #("Water tank", "—", "%", True, None),
        ]
        cells = ""
        for label, val, unit, ok, series in rows:
            extra = '<svg viewBox="0 0 100 28" preserveAspectRatio="none"><line x1="0" y1="14" x2="100" y2="14" stroke="#d5e6bd" stroke-width="2" stroke-dasharray="4 4" vector-effect="non-scaling-stroke"/></svg>'
            cells += (
                f'<div class="m"><div class="ml">{label}</div>'
                f'<div class="mv">{val}<small>{unit}</small></div>{extra}</div>'
            )
        stamp = "Select a plant above to view readings"
        body = f'<div class="sens"><div class="stt"><b>Live sensor readings</b><span>{stamp}</span></div>{cells}</div>'
        return card(SENS_R) + blk(SENS_IN_R, body)

    if not p.get("has_data"):
        rows = [
            ("Soil moisture", "—", "%", True, None),
            ("Temperature", "—", "°C", True, None),
            ("Humidity", "—", "%", True, None),
            #("Light", "—", "klux", True, None),
            #("Water tank", "100", "%", True, None),
        ]
        cells = ""
        for label, val, unit, ok, series in rows:
            extra = '<svg viewBox="0 0 100 28" preserveAspectRatio="none"><line x1="0" y1="14" x2="100" y2="14" stroke="#d5e6bd" stroke-width="2" stroke-dasharray="4 4" vector-effect="non-scaling-stroke"/></svg>'
            cells += (
                f'<div class="m"><div class="ml">{label}</div>'
                f'<div class="mv">{val}<small>{unit}</small></div>{extra}</div>'
            )
        stamp = f"{p['emoji']} {esc(plant_name)} · Waiting for sensor readings..."
        body = f'<div class="sens"><div class="stt"><b>Live sensor readings</b><span>{stamp}</span></div>{cells}</div>'
        return card(SENS_R) + blk(SENS_IN_R, body)

    hist = lambda k: [h.get(k, 0) for h in p["hist"]]
    rows = [
        ("Soil moisture", f'{p["moisture"]:.0f}', "%", p["mlo"] <= p["moisture"] <= p["mhi"], hist("moisture")),
        ("Temperature", T(p["temp"])[:-2], T(p["temp"])[-2:], p["tlo"] <= p["temp"] <= p["thi"], hist("temperature")),
        ("Humidity", f'{p["hum"]:.0f}', "%", 35 <= p["hum"] <= 85, hist("humidity")),
       # ("Light", f'{p["light"] / 1000:.1f}', "klux", p["light"] <= 45000, hist("light")),
        #("Water tank", "100", "%", True, None),
    ]
    cells = ""
    for label, val, unit, ok, series in rows:
        col = "var(--good)" if ok else "var(--warn)"
        extra = spark(series, col) if series is not None else '<div class="bar"><i style="width:100%;background:var(--good)"></i></div>'
        cells += (
            f'<div class="m"><div class="ml">{label}<i style="background:{col}"></i></div>'
            f'<div class="mv">{val}<small>{unit}</small></div>{extra}</div>'
        )
    stamp = f"{p['emoji']} {esc(plant_name)} · {now:%H:%M:%S}" if live else "Updates paused"
    body = f'<div class="sens"><div class="stt"><b>Live sensor readings</b><span>{stamp}</span></div>{cells}</div>'
    return card(SENS_R) + blk(SENS_IN_R, body)


# ==================================================
# WIDGETS  (pinned by key, see WIDGETS above)
# ==================================================
def display_name() -> str:
    ss = st.session_state
    if ss.get("_name_token") != ss.auth_token:      # ask the backend once per login
        ss.user_name = get_current_user(ss.auth_token)
        ss._name_token = ss.auth_token
    name = (ss.get("user_name") or "Gardener").strip() or "Gardener"
    return name[:1].upper() + name[1:]


def profile_widget(name: str) -> None:
    with st.container(key="profile"):
        with st.popover(name[:1].upper(), help="Your profile"):
            html(f'<div class="avatar-name">{esc(name)}</div>')
            st.caption("Signed in to Smart Garden")
            if st.button("Profile", key="pf_profile", icon="👤"):
                nav_to("pages/8_Profile.py")
            if st.button("Log out", key="pf_logout", icon="🚪"):
                logout()


def nav_widgets() -> None:
    ss = st.session_state
    for label, key, _icon in NAV:
        if st.button(label, key=key, type="primary" if ss.view == label else "secondary"):
            go(label)
    st.toggle("Live updates", key="live")
    if st.button("Log out", key="logout"):
        logout()


def dashboard_widgets() -> None:
    ss = st.session_state
    options = list(ss.plants)
    kw = {"placeholder": "Select a plant...", "key": "sel_plant"}
    if ss.sel_plant is None:
        kw["index"] = None
    st.selectbox("Plant", options, label_visibility="collapsed", **kw)
    st.time_input("Water daily at", key="sched", step=300, label_visibility="collapsed")
    st.toggle("Follow schedule", key="auto_sched")
    st.button("Water now", key="water_now", icon="💧", on_click=water_now)
    st.caption("Weather is provided by your backend location.")
    st.radio("Unit", ["°C", "°F"], key="dash_unit", horizontal=True, label_visibility="collapsed")


# ==================================================
# "MY PLANTS" PANEL
# ==================================================
def panel() -> None:
    ss = st.session_state
    with st.container(key="panel"):
        html('<div class="h">My plants</div>')
        if st.button("＋ Add a plant", key="add_plant"):
            nav_to("pages/5_Garden.py")
        if not ss.plants:
            html('<div class="sub">No plants yet. Add your first one to start monitoring.</div>')
            return
        items = list(ss.plants.items())
        for i in range(0, len(items), 3):
            for col, (n, p) in zip(st.columns(3), items[i:i + 3]):
                s = health(p)
                lab, c = status(s)
                with col:
                    html(f'<div class="pcard"><span>{p["emoji"]}</span>{esc(n)}<i style="color:{c}">{s}% · {lab}</i></div>')
                    st.button("Open on dashboard", key=f"open_{n}", on_click=open_plant, args=(n,), width="stretch")


# ==================================================
# INIT SESSION STATE
# ==================================================
def init_session_state() -> None:
    ss = st.session_state

    # If the user navigated back from an external page, reset view to Dashboard
    if ss.get("view") in PAGE_MAP:
        ss.view = "Dashboard"

    ss.setdefault("view", "Dashboard")
    ss.setdefault("sel_plant", None)
    ss.setdefault("sched", time(18, 30))
    ss.setdefault("auto_sched", True)
    ss.setdefault("dash_unit", "°C")
    ss.setdefault("live", True)
    ss.setdefault("plants", {})

    # Load plants from backend if empty
    if not ss.plants:
        ss.plants = load_plants_from_backend()
    if ss.sel_plant is not None and ss.sel_plant not in ss.plants:
        ss.sel_plant = None


def refresh_selected_plant() -> None:
    plant_id = current_plant_id()
    if not plant_id:
        return
    plant = st.session_state.plants.get(st.session_state.sel_plant)
    if not plant:
        return
    readings = load_sensor_history(plant_id, limit=60)
    if not readings:
        plant["has_data"] = False
        plant["hist"] = []
        plant["moisture"] = 0
        plant["temp"] = 0
        plant["hum"] = 0
        plant["light"] = 0
        return
    latest = readings[-1]
    plant.update(
        moisture=float(latest.get("moisture")) if latest.get("moisture") is not None else 0.0,
        temp=float(latest.get("temperature")) if latest.get("temperature") is not None else 0.0,
        hum=float(latest.get("humidity")) if latest.get("humidity") is not None else 0.0,
        light=float(latest.get("light")) if latest.get("light") is not None else 0.0,
        rain=bool(latest.get("rain_detected")),
        last_ts=latest.get("timestamp"),
        has_data=True,
        hist=readings,
    )


# ==================================================
# RUN PAGE
# ==================================================
init_session_state()
inject_css()

ss = st.session_state
name = display_name()
now = datetime.now()
show_cards = ss.view == "Dashboard" and bool(ss.plants)

if show_cards:
    plant = ss.plants.get(ss.sel_plant)
    if plant:
        refresh_selected_plant()
        plant = ss.plants.get(ss.sel_plant)
        pid = plant.get("id")
        prediction = load_prediction(pid) if pid else {}
        pump_data = load_pump(pid) if pid else {}
        decision_data = load_decision(pid) if pid else {}
        markup = (
            header_html(name, now)
            + nav_html(len(ss.plants), now)
            + health_html(plant)
            + water_html(prediction, has_plant=True)
            + weather_html(load_weather())
            + pump_html(pump_data, decision_data, has_plant=True)
            + sensors_html(plant, ss.sel_plant, ss.live, now)
        )
    else:
        markup = (
            header_html(name, now)
            + nav_html(len(ss.plants), now)
            + health_html(None)
            + water_html({}, has_plant=False)
            + weather_html(load_weather())
            + pump_html({}, {}, has_plant=False)
            + sensors_html(None, None, ss.live, now)
        )
else:
    markup = header_html(name, now) + nav_html(len(ss.plants), now)

with st.container(key="stage"):
    with st.container(key="shells"):
        html(markup)
    profile_widget(name)
    nav_widgets()
    if show_cards:
        dashboard_widgets()
    else:
        panel()
