import base64
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Smart Garden | Dashboard",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ==================================================
# CONFIG
# ==================================================
BACKEND_URL = "http://localhost:8000"
WATER_THRESHOLD = 35  # matches backend settings.moisture_threshold_dry

# Edit here if you rename pages (e.g. 9_Sensors.py -> 10_Sensors.py)
PAGES = {
    "Settings": "pages/10_Settings.py",
    "Analytics": "pages/11_Analytics.py",
    "Sensors": "pages/9_Sensors.py",
    "Weather Forecast": "pages/12_Weather.py",
    "About us": "pages/7_About.py",
    "Profile": "pages/8_Profile.py",
}

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
NAV = [
    ("Dashboard", "🏠"),
    ("My plants", "🪴"),
    ("Weather Forecast", "⛅"),
    ("Sensors", "📡"),
    ("Analytics", "📊"),
    ("About us", "ℹ️"),
    ("Settings", "⚙️"),
]
ART = {"plant": "plant.png", "can": "watering_can.png", "pump": "pump.png"}

LAYOUT = {
    "nav": (0, 0, 227, 697),
    "health": (268, 40, 380, 303),
    "water": (648, 40, 309, 303),
    "weather": (957, 40, 325, 503),
    "pump": (268, 372, 689, 171),
    "sensors": (268, 573, 1014, 124),
    "panel": (268, 40, 1014, 657),
}

# ==================================================
# BACKEND API
# ==================================================
def api(method: str, path: str, **kw):
    """Call the backend. Returns (json, error). A 401 sends the user to login."""
    token = st.session_state.get("auth_token")
    try:
        r = requests.request(
            method,
            f"{BACKEND_URL}{path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8,
            **kw,
        )
    except requests.exceptions.RequestException:
        return None, "Cannot reach backend. Is it running?"

    if r.status_code == 401:
        st.session_state.auth_token = None
        st.toast("Session expired, please log in again")
        st.switch_page("pages/2_Login.py")
        st.stop()

    if r.status_code >= 400:
        try:
            return None, r.json().get("detail", f"Error {r.status_code}")
        except ValueError:
            return None, f"Error {r.status_code}"

    try:
        return r.json(), None
    except ValueError:
        return None, "Bad response from backend"


def load_plants_from_backend() -> dict:
    data, err = api("GET", "/api/plants/my-plants")
    if err:
        st.error(f"Could not load plants: {err}")
        return {}
    plants = {}
    for p in data.get("plants", []):
        name = p.get("name", f"Plant {p.get('id')}")
        plants[name] = {
            "id": p.get("id"), "emoji": "🌱",
            "mlo": 30, "mhi": 70, "tlo": 16, "thi": 30,
            "moisture": 0, "temp": 0, "hum": 0, "rain": False,
            "has_data": False, "last_ts": None, "hist": [],
        }
    return plants


def load_sensor_history(plant_id: int, limit: int = 60) -> list:
    data, _ = api("GET", "/api/sensor-data/history",
                  params={"plant_id": plant_id, "limit": limit})
    readings = (data or {}).get("readings", [])
    # Oldest first, so readings[-1] is always the latest
    return sorted(readings, key=lambda r: str(r.get("timestamp", "")))


def load_prediction(plant_id: int) -> dict:
    data, _ = api("GET", f"/api/plants/{plant_id}/next-watering-prediction")
    return data or {}


def load_pump(plant_id: int) -> dict:
    data, _ = api("GET", f"/api/plants/{plant_id}/pump-status")
    return data or {}


def load_decision(plant_id: int) -> dict:
    data, _ = api("GET", f"/api/plants/{plant_id}/latest-decision")
    return data or {}


@st.cache_data(ttl=300, show_spinner=False)
def _weather_cached(token: str) -> dict:
    # token is only the cache key; the call itself reads it from session state
    data, _ = api("GET", "/api/weather/current")
    return data or {}


def load_weather() -> dict:
    w = _weather_cached(st.session_state.auth_token)
    if not w:
        _weather_cached.clear()  # don't keep a failed result for 5 minutes
    return w


@st.cache_data(ttl=300, show_spinner=False)
def get_current_user(token: str) -> str:
    data, _ = api("GET", "/api/auth/me")
    return (data or {}).get("username", "Gardener")

# ==================================================
# STYLES
# ==================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;500;600&family=Nunito:wght@400;600;700&display=swap');
:root{--u:min(100vw / 1366, 100vh / 768);--line:#6b9a22;--ink:#2b3f12;--mute:#68803a;--soft:#f3f9ec;
      --good:#6aaa4a;--warn:#e0a030;--bad:#d0583a;--head:'Fredoka','Nunito',sans-serif}
html,body,.stApp,.stApp *:not([data-testid="stIconMaterial"]),[data-baseweb="popover"] *{font-family:'Nunito','Segoe UI',sans-serif}
.h,.brand,.big,.mv,.ring b,.wnow b,.stt b,.pst b,.greet,.avatar-name,.chips b,.stats b,.snap b{font-family:var(--head)!important}
.stApp{background:%%BG%% center / cover no-repeat fixed;font-size:@{15}}
header,[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],footer,#MainMenu{display:none!important}
.block-container,[data-testid="stMainBlockContainer"]{max-width:100%!important;padding:@{38} 0 0!important}
.st-key-stage{position:relative;width:@{1282};height:@{697};margin:0 auto;gap:0}

:is(.st-key-nav,.st-key-health,.st-key-water,.st-key-weather,.st-key-pump,.st-key-sensors,.st-key-panel){
  position:absolute;box-sizing:border-box;background:#fff;color:var(--ink);overflow:hidden;
  border:max(2px,@{3}) solid var(--line);border-radius:@{36};padding:@{20} @{24};gap:@{8};
  box-shadow:@{9} @{11} @{16} rgba(0,0,0,.2)}
:is(.st-key-nav,.st-key-health,.st-key-water,.st-key-weather,.st-key-pump,.st-key-sensors,.st-key-panel)>*{flex-shrink:0}
.st-key-pump{padding:@{14} @{26}}
.st-key-sensors{justify-content:center;padding:@{12} @{26}}
.st-key-panel{overflow-y:auto}
.stApp [data-testid="stMarkdownContainer"] p{margin:0}
[data-testid="stHorizontalBlock"]{gap:@{14}}

.h{font-size:@{22};font-weight:500;line-height:1.15;color:var(--ink)}
.hdr{display:flex;align-items:center;justify-content:space-between;gap:@{10};min-height:@{56}}
.big{font-size:@{40};font-weight:500;line-height:1.05}
.sub{font-size:@{14};color:var(--mute)}
[data-testid="stWidgetLabel"] p{font-size:@{14};color:var(--mute)}
[data-baseweb="select"]>div{min-height:@{38};height:@{38};border-radius:@{12};background:var(--soft);border-color:#b9d98f}
[data-baseweb="select"] *{font-size:@{15}}
[data-testid="stCaptionContainer"] p,[data-testid="stToggle"] p,[data-testid="stRadio"] label p{font-size:@{14};color:var(--ink)}
[data-baseweb="checkbox"]:has(input:checked)>:is(div,span):first-child{background:var(--good)!important}
[data-baseweb="radio"]:has(input:checked)>:is(div,span):first-child{background:var(--good)!important;border-color:var(--good)!important}

.art{flex:none;background:center / contain no-repeat}
%%ART%%

.st-key-nav{gap:@{5}}
.brand{display:flex;align-items:center;gap:@{10};font-size:@{21};font-weight:500;white-space:nowrap;padding:@{2} 0 @{6}}
.brand i{width:@{38};height:@{38};border-radius:50%;display:grid;place-items:center;font-style:normal;font-size:@{20};
  background:linear-gradient(135deg,#dff2c6,#b9e08a)}
.st-key-nav button{justify-content:flex-start!important;gap:@{8};width:100%;min-height:0;height:@{42};padding:0 @{14};
  border:none!important;border-radius:@{21};background:transparent!important;box-shadow:none!important;
  transition:transform .15s ease,background .15s ease}
.st-key-nav button p{font-size:@{17};font-weight:600;color:var(--ink);white-space:nowrap}
.st-key-nav button:hover{background:#eaf5dc!important;transform:translateX(@{4})}
.st-key-nav button:is([kind=primary],[data-testid=stBaseButton-primary]){
  background:linear-gradient(90deg,#d9efc0,#eef8e2)!important;box-shadow:inset @{4} 0 0 var(--line)!important}
.st-key-nav button:is([kind=primary],[data-testid=stBaseButton-primary]) p{font-weight:700}
@media (prefers-reduced-motion:reduce){.st-key-nav button:hover{transform:none}}
.st-key-snapwrap{margin-top:auto}
.snap{background:var(--soft);border-radius:@{18};padding:@{10} @{14};font-size:@{14};color:var(--mute)}
.snap b{display:block;font-size:@{17};font-weight:500;color:var(--ink)}

.st-key-profile{position:fixed;top:@{14};right:@{26};z-index:1000;flex-direction:row;align-items:center;gap:@{10};width:auto}
.greet{font-size:@{17};font-weight:500;color:var(--ink);white-space:nowrap}
.st-key-profile [data-testid="stPopover"] button{width:@{46};height:@{46};min-height:0;padding:0;border-radius:50%;
  border:max(2px,@{3}) solid #fff;background:linear-gradient(135deg,#8fdc55,#5fa83a);
  box-shadow:@{3} @{5} @{10} rgba(0,0,0,.25)}
.st-key-profile [data-testid="stPopover"] button p{font-family:var(--head);font-size:@{20};color:#fff;font-weight:500}
.st-key-profile [data-testid="stPopover"] button [data-testid="stIconMaterial"]{display:none}
.avatar-name{font-size:@{18};font-weight:500}

:is(.st-key-water,.st-key-panel) button{width:100%;border:none;border-radius:999px;min-height:0;height:@{40};
  background:linear-gradient(90deg,#8fdc55,#c9e25f);box-shadow:@{4} @{6} @{8} rgba(0,0,0,.2)}
:is(.st-key-water,.st-key-panel) button p{font-size:@{17};font-weight:700;color:#fff}

.hrow{display:flex;align-items:center;gap:@{18}}
.ring{flex:none;width:@{104};height:@{104};border-radius:50%;display:flex;flex-direction:column;align-items:center;
  justify-content:center;background:radial-gradient(closest-side,#fff 76%,transparent 78%),conic-gradient(var(--c) calc(var(--s) * 1%),#e4efd3 0)}
.ring b{font-size:@{30};font-weight:500;line-height:1}.ring span{font-size:@{12};color:var(--mute)}
.stats{flex:1;display:flex;flex-direction:column;gap:@{6}}
.stats div{display:flex;justify-content:space-between;align-items:center;background:var(--soft);border-radius:@{12};padding:@{6} @{12};font-size:@{14};color:var(--mute)}
.stats b{font-size:@{17};font-weight:500;color:var(--ink)}

.wtop{display:flex;align-items:center;justify-content:space-between;min-height:@{60}}
.pbox{background:var(--soft);border-radius:@{14};padding:@{8} @{12};font-size:@{15};font-weight:700;line-height:1.25}
.pbox small{display:block;font-weight:400;font-size:@{13};color:var(--mute)}
.pmini{display:grid;grid-template-columns:1fr 1fr;gap:@{8};margin-top:@{6}}
.pmini div{background:var(--soft);border-radius:@{12};padding:@{6} @{10};font-size:@{13};color:var(--mute);text-align:center}
.pmini b{display:block;font-size:@{17};font-weight:500;color:var(--ink);font-family:var(--head)}

.wnow{display:flex;align-items:center;justify-content:center;gap:@{12};min-height:@{54}}
.wnow span{font-size:@{40}}.wnow b{font-size:@{38};font-weight:500}
.chips{display:grid;grid-template-columns:repeat(3,1fr);gap:@{8}}
.chips div{text-align:center;font-size:@{13};color:var(--mute);background:var(--soft);border-radius:@{12};padding:@{5} 0}
.chips b{display:block;font-size:@{17};font-weight:500;color:var(--ink)}
.tip{font-size:@{14};background:#fff6dc;border-radius:@{12};padding:@{7} @{12};line-height:1.3}
.src{font-size:@{12};color:var(--mute);text-align:center}

.pst{display:flex;align-items:center;gap:@{14}}.pst b{font-size:@{26};font-weight:500;display:block;line-height:1.1}
.pst small{font-size:@{14};color:var(--mute)}
.dot{flex:none;width:@{40};height:@{40};border-radius:50%;background:#cfd8c3}
.dot.on{background:var(--good);animation:pulse 1.6s infinite}
.dot.q{background:var(--warn)}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(106,170,74,.55)}100%{box-shadow:0 0 0 @{16} rgba(106,170,74,0)}}
@media (prefers-reduced-motion:reduce){.dot.on{animation:none}}
.dec{font-size:@{14};line-height:1.3}
.dec b{font-family:var(--head);font-size:@{18};font-weight:500}
.dec small{display:block;color:var(--mute);font-size:@{12}}
.badge{display:inline-block;background:var(--soft);border-radius:999px;padding:@{3} @{12};font-size:@{13};color:var(--ink);margin-top:@{4}}

.sens{display:grid;grid-template-columns:@{160} repeat(5,1fr);gap:@{22};align-items:center}
.stt b{display:block;font-size:@{20};font-weight:500;line-height:1.1}
.stt span{font-size:@{13};color:var(--mute)}
.ml{font-size:@{14};color:var(--mute);display:flex;align-items:center;gap:@{6}}
.ml i{width:@{9};height:@{9};border-radius:50%}
.mv{font-size:@{30};font-weight:500;line-height:1.15}.mv small{font-size:@{14};font-family:'Nunito'!important;color:var(--mute);margin-left:@{3}}
.m svg,.bar{width:100%;height:@{20};display:block;margin-top:@{2}}
.bar{background:#e4efd3;border-radius:@{10};position:relative;height:@{10};margin-top:@{9}}
.bar i{position:absolute;inset:0 auto 0 0;border-radius:@{10}}
.pcard{background:var(--soft);border-radius:@{18};padding:@{12};text-align:center;font-size:@{18};font-weight:600}
.pcard span{font-size:@{34};display:block}.pcard i{display:block;font-style:normal;font-size:@{15};font-weight:400}
</style>
"""


def inject_css():
    rules = "".join(
        f".st-key-{k}{{left:@{{{x}}};top:@{{{y}}};width:@{{{w}}};height:@{{{h}}}}}"
        for k, (x, y, w, h) in LAYOUT.items()
    )
    css = (CSS.replace("%%BG%%", bg_uri()).replace("%%ART%%", art_css())
              .replace("</style>", rules + "</style>"))
    css = re.sub(r"@\{(\d+(?:\.\d+)?)\}", r"calc(var(--u) * \1)", css)
    st.markdown(css, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def art_css() -> str:
    size = {"plant": (68, 65), "can": (84, 90), "pump": (118, 88)}
    out = ""
    for key, fname in ART.items():
        p = ASSETS / fname
        if p.exists():
            w, h = size[key]
            out += (f".art-{key}{{width:@{{{w}}};height:@{{{h}}};"
                    f"background-image:url(data:image/png;base64,{base64.b64encode(p.read_bytes()).decode()})}}")
    return out


@st.cache_data(show_spinner=False)
def bg_uri() -> str:
    for name in ("garden_bg.png", "background.jpg"):
        p = ASSETS / name
        if p.exists():
            mime = "image/png" if p.suffix == ".png" else "image/jpeg"
            return f'url("data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}")'
    return "linear-gradient(160deg,#e9f7df,#f3fbee 50%,#d8f0c4)"

# ==================================================
# HELPERS
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
    if score >= 60:
        return ("Doing okay", "var(--warn)")
    return ("Needs care", "var(--bad)")


def T(c: float) -> str:
    if st.session_state.get("unit", "°C") == "°F":
        return f"{c * 9 / 5 + 32:.0f}°F"
    return f"{c:.0f}°C"



def html(s: str) -> None:
    st.markdown(s, unsafe_allow_html=True)

def placeholder(key: str, title: str) -> None:
    with st.container(key=key):
        html(f'<div class="h">{title}</div><div class="sub">Select a plant to see this.</div>')    


def pick(d: dict, *keys, default=None):
    """First key present in d with a non-None value (tolerates backend key naming)."""
    for k in keys:
        if d.get(k) is not None:
            return d[k]
    return default


def current_plant_id():
    ss = st.session_state
    return (ss.plants.get(ss.sel_plant) or {}).get("id")

# ==================================================
# CALLBACKS
# ==================================================
def go(view: str) -> None:
    st.session_state.view = view
    if view in PAGES:
        st.switch_page(PAGES[view])


def open_plant(name: str) -> None:
    st.session_state.sel_plant = name
    st.session_state.view = "Dashboard"


def water_now() -> None:
    pid = current_plant_id()
    if not pid:
        st.toast("⚠️ No plant selected")
        return
    _, err = api("POST", f"/api/plants/{pid}/water-now")
    if err:
        st.toast(f"⚠️ {err}")
    else:
        st.toast("✅ Queued. Pump starts at the device's next check-in (≤30s)")


def logout() -> None:
    st.session_state.auth_token = None
    st.toast("Logged out")
    st.switch_page("pages/2_Login.py")

# ==================================================
# CARDS
# ==================================================
def nav() -> None:
    ss = st.session_state
    with st.container(key="nav"):
        html('<div class="brand"><i>🌱</i>Smart Garden</div>')
        for n, icon in NAV:
            if st.button(n, key=f"nav_{n}", icon=icon,
                         type="primary" if ss.view == n else "secondary"):
                go(n)
        with st.container(key="snapwrap"):
            html(f'<div class="snap"><b>{datetime.now():%a, %d %b}</b>{len(ss.plants)} plants linked</div>')
        st.toggle("Live updates", key="live")
        if st.button("Log out", key="logout", icon="🚪"):
            logout()


def profile() -> None:
    name = get_current_user(st.session_state.auth_token)
    with st.container(key="profile"):
        html(f'<div class="greet">Hi, {name}</div>')
        with st.popover(name[0].upper(), help="Your profile"):
            html(f'<div class="avatar-name">{name}</div>')
            st.caption("Signed in to Smart Garden")
            if st.button("Settings", key="pf_settings", icon="⚙️"):
                go("Settings")
            if st.button("Log out", key="pf_logout", icon="🚪"):
                logout()


def card_health() -> None:
    ss = st.session_state
    with st.container(key="health"):
        html('<div class="hdr"><div><div class="h">Plant health</div>'
             '<div class="sub">Pick a plant to inspect</div></div>'
             '<div class="art art-plant"></div></div>')
        name = st.selectbox("Plant", list(ss.plants), key="sel_plant", index=None,
                            placeholder="Select a plant", label_visibility="collapsed")
        if name is None:
            html('<div class="sub">Choose a plant to see its readings.</div>')
            return
        p = ss.plants[name]
        if not p["has_data"]:
            html('<div class="sub">Waiting for the first sensor reading…</div>')
            return
        s = health(p)
        lab, col = status(s)
        html(
            f'<div class="hrow"><div class="ring" style="--s:{s};--c:{col}"><b>{s}</b><span>{lab}</span></div>'
            f'<div class="stats"><div>Soil<b>{p["moisture"]:.0f}%</b></div>'
            f'<div>Air<b>{T(p["temp"])}</b></div>'
            f'<div>Humidity<b>{p["hum"]:.0f}%</b></div></div></div>'
        )


def card_water() -> None:
    plant_id = current_plant_id()
    pred = load_prediction(plant_id) if plant_id else {}

    with st.container(key="water"):
        html('<div class="wtop"><div class="h">Next watering</div><div class="art art-can"></div></div>')

        if pred:
            st_val = pred.get("status")
            hours = pred.get("next_watering_in_hours")
            when = pred.get("estimated_time_friendly")
            if st_val == "WATER_NOW":
                st.error("💧 Water now")
            elif hours is None:
                st.info("🌱 Moisture stable, no watering needed soon")
            elif st_val == "WATER_SOON" or hours < 4:
                st.error(f"🔴 In {hours:.1f} h" + (f" · {when}" if when else ""))
            elif hours < 8:
                st.warning(f"💧 In {hours:.1f} h" + (f" · {when}" if when else ""))
            else:
                st.success(f"🌱 In {hours:.1f} h" + (f" · {when}" if when else ""))

            rate = pred.get("depletion_rate_per_hour")
            conf = pred.get("confidence")
            if conf is not None and conf <= 1:
                conf *= 100
            html(
                '<div class="pmini">'
                f'<div><b>{rate:.2f}%/h</b>drying rate</div>' if rate is not None else '<div><b>–</b>drying rate</div>'
            )
            html(f'<div><b>{conf:.0f}%</b>confidence</div></div>' if conf is not None
                 else '<div><b>–</b>confidence</div></div>')
        else:
            st.info("Waiting for enough sensor data to predict watering.")

        st.button("Water now", key="water_now", icon="💧", on_click=water_now)


def card_weather() -> None:
    w = load_weather()
    with st.container(key="weather"):
        html('<div class="h">Weather forecast</div>')
        st.radio("Unit", ["°C", "°F"], key="unit", horizontal=True, label_visibility="collapsed")

        if not w or not w.get("available", True):
            html('<div class="tip">⚠️ Weather unavailable. Irrigation falls back to the sensor-only rule.</div>')
            return

        rain_p = pick(w, "rain_probability", default=0)
        temp = pick(w, "temp", "temperature")
        clouds = pick(w, "cloud_coverage", "clouds")
        rain_mm = pick(w, "rainfall_mm", "rain_mm")
        icon = "🌧️" if rain_p >= 60 else "⛅" if rain_p >= 30 else "☀️"
        fmt = lambda v, suf: f"{v:.0f}{suf}" if isinstance(v, (int, float)) else "–"

        html(
            f'<div class="wnow"><span>{icon}</span><b>{T(temp) if isinstance(temp, (int, float)) else "–"}</b></div>'
            f'<div class="chips"><div><b>{rain_p:.0f}%</b>rain (24h)</div>'
            f'<div><b>{fmt(clouds, "%")}</b>clouds</div>'
            f'<div><b>{fmt(rain_mm, " mm")}</b>rainfall</div></div>'
        )
        if rain_p > 50:
            tip = "Rain likely in the next 24 h. Automatic watering will skip."
        else:
            tip = "Low rain chance. Automatic watering will follow soil moisture."
        html(f'<div class="tip">💡 {tip}</div>')
        html(f'<div class="src">Live · OpenWeather · {w.get("city", "Mumbai")} · updates every ~10 min</div>')


def card_pump() -> None:
    plant_id = current_plant_id()
    pump = load_pump(plant_id) if plant_id else {}
    dec = load_decision(plant_id) if plant_id else {}

    if not pump:
        state, sub, dot = "–", "Pump status unavailable", ""
    elif pump.get("active"):
        state, sub, dot = "ON", "Watering now", "on"
    elif pump.get("pending_manual"):
        state, sub, dot = "QUEUED", "Waiting for device check-in", "q"
    else:
        state = "OFF"
        sub = f"Cooldown {pump['cooldown_minutes']} min" if pump.get("cooldown_minutes") else "Idle"
        dot = ""

    last = "Never"
    if pump.get("last_run"):
        last = (pd.to_datetime(pump["last_run"], utc=True)
                .tz_convert("Asia/Kolkata").strftime("%d %b, %I:%M %p"))

    with st.container(key="pump"):
        art, a, b, c = st.columns([.75, 1.25, 1.15, 1.6], vertical_alignment="center")
        with art:
            html('<div class="art art-pump"></div>')
        with a:
            html('<div class="h">Pump status</div>'
                 f'<div class="pst"><div class="dot {dot}"></div><div>'
                 f'<b>{state}</b><small>{sub}</small></div></div>')
        with b:
            html(f'<div class="sub">Last run</div><div class="dec"><b>{last}</b>'
                 f'<small>{(pump.get("last_reason") or "")[:40]}</small></div>'
                 f'<div class="badge">Auto-irrigation ON · threshold {WATER_THRESHOLD}%</div>')
        with c:
            if dec.get("decision"):
                conf = dec.get("confidence")
                if conf is not None and conf <= 1:
                    conf *= 100
                conf_txt = f" · {conf:.0f}% confidence" if conf is not None else ""
                reason = (dec.get("reason") or "")[:120]
                html(f'<div class="sub">Last decision</div><div class="dec"><b>{dec["decision"]}</b>{conf_txt}'
                     f'<small>{reason}</small></div>')
            else:
                html('<div class="sub">Last decision</div><div class="dec"><small>No decisions yet</small></div>')


def spark(vals: list, col: str) -> str:
    if len(vals) < 2:
        return '<svg viewBox="0 0 100 28"></svg>'
    lo, r = min(vals), (max(vals) - min(vals)) or 1
    pts = " ".join(f"{i * 100 / (len(vals) - 1):.1f},{27 - (v - lo) / r * 25:.1f}"
                   for i, v in enumerate(vals))
    return (f'<svg viewBox="0 0 100 28" preserveAspectRatio="none"><polyline points="{pts}" '
            f'fill="none" stroke="{col}" stroke-width="2" vector-effect="non-scaling-stroke"/></svg>')


def card_sensors() -> None:
    ss = st.session_state
    p = ss.plants[ss.sel_plant]
    if not p["has_data"]:
        with st.container(key="sensors"):
            html('<div class="stt"><b>Live sensor readings</b><span>No readings yet. Is the device or simulator running?</span></div>')
        return

    series = lambda k: [float(h[k]) for h in p["hist"] if h.get(k) is not None]
    last_time = str(p["last_ts"])[11:19] if p["last_ts"] else "–"
    rain_txt = "Raining" if p["rain"] else "Dry"

    rows = [
        ("Soil moisture", f'{p["moisture"]:.0f}', "%", p["mlo"] <= p["moisture"] <= p["mhi"], series("moisture")),
        ("Temperature", T(p["temp"])[:-2], T(p["temp"])[-2:], p["tlo"] <= p["temp"] <= p["thi"], series("temperature")),
        ("Humidity", f'{p["hum"]:.0f}', "%", 35 <= p["hum"] <= 85, series("humidity")),
        ("Rain sensor", rain_txt, "", not p["rain"], None),
        ("Last reading", last_time, "", True, None),
    ]
    cells = ""
    for label, val, unit, ok, s in rows:
        col = "var(--good)" if ok else "var(--warn)"
        extra = spark(s, col) if s is not None else ""
        cells += (f'<div class="m"><div class="ml">{label}<i style="background:{col}"></i></div>'
                  f'<div class="mv">{val}<small>{unit}</small></div>{extra}</div>')
    stamp = f"{p['emoji']} {ss.sel_plant} · live" if ss.live else "Updates paused"
    with st.container(key="sensors"):
        html(f'<div class="sens"><div class="stt"><b>Live sensor readings</b><span>{stamp}</span></div>{cells}</div>')

# ==================================================
# PANEL (My plants only; other views are separate pages)
# ==================================================
def panel() -> None:
    ss = st.session_state
    with st.container(key="panel"):
        html('<div class="h">My plants</div>')
        if st.button("＋ Add a plant", key="add_plant"):
            st.switch_page("pages/5_Garden.py")
        items = list(ss.plants.items())
        for i in range(0, len(items), 3):
            for col, (n, p) in zip(st.columns(3), items[i:i + 3]):
                with col:
                    if p["has_data"]:
                        s = health(p)
                        lab, c = status(s)
                        sub = f'<i style="color:{c}">{s}% · {lab}</i>'
                    else:
                        sub = '<i style="color:var(--mute)">No data yet</i>'
                    html(f'<div class="pcard"><span>{p["emoji"]}</span>{n}{sub}</div>')
                    st.button("Open on dashboard", key=f"open_{n}",
                              on_click=open_plant, args=(n,), width="stretch")

# ==================================================
# SESSION STATE
# ==================================================
def init_session_state():
    ss = st.session_state
    if ss.get("view") in PAGES:  # returned from a separate page
        ss.view = "Dashboard"
    ss.setdefault("view", "Dashboard")
    ss.setdefault("sel_plant", None)
    ss.setdefault("unit", "°C")
    ss.setdefault("live", True)
    ss.setdefault("plants", {})

    if not ss.plants:
        ss.plants = load_plants_from_backend()
    if ss.get("sel_plant") not in ss.plants:
        ss.sel_plant = None

# ==================================================
# MAIN
# ==================================================
def refresh_selected_plant() -> None:
    ss = st.session_state
    plant_id = current_plant_id()
    if not plant_id:
        return
    readings = load_sensor_history(plant_id, limit=60)
    if not readings:
        return
    latest, p = readings[-1], ss.plants[ss.sel_plant]
    p.update(
        moisture=latest.get("moisture") or 0,
        temp=latest.get("temperature") or 0,
        hum=latest.get("humidity") or 0,
        rain=bool(latest.get("rain_detected")),
        last_ts=latest.get("timestamp"),
        has_data=True,
        hist=readings,
    )

def dashboard_body() -> None:
    ss = st.session_state
    if ss.view == "My plants":
        panel()
        return
    refresh_selected_plant()
    card_health()
    card_weather()
    if ss.sel_plant:
        card_water()
        card_pump()
        card_sensors()
    else:
        placeholder("water", "Next watering")
        placeholder("pump", "Pump status")
        placeholder("sensors", "Live sensor readings")


init_session_state()
inject_css()
profile()
with st.container(key="stage"):
    nav()
    if not st.session_state.plants:
        with st.container(key="panel"):
            html('<div class="h">No plants yet</div>')
            if st.button("＋ Add your first plant", key="add_first"):
                st.switch_page("pages/5_Garden.py")
    else:
        run_every = 10 if st.session_state.live else None
        st.fragment(run_every=run_every)(dashboard_body)()