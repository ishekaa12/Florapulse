import base64
from datetime import datetime
import json
import math
import os
from pathlib import Path
import requests
import streamlit as st

try:
    st.set_page_config(page_title="Smart Irrigation System – Weather Forecast", page_icon="🌦️", layout="wide")
except st.errors.StreamlitAPIException:
    pass  # already set by app.py

BASE = Path(__file__).parent


# ---------- Load environment variables ----------
def get_env_var(key: str, default: str = "") -> str:
    val = os.getenv(key)
    if val:
        return val
    candidates = [
        BASE / ".env",
        BASE.parent / ".env",
        BASE.parent / "florapulse-backend" / ".env",
        Path.cwd() / ".env",
        Path.cwd() / "florapulse-backend" / ".env",
    ]
    for path in candidates:
        if path.exists():
            for line in path.read_text().splitlines():
                line = line.strip()
                if line.startswith(f"{key}=") or line.startswith(f"{key.lower()}="):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip('"').strip("'")
    return default


OPENWEATHER_API_KEY = get_env_var("OPENWEATHER_API_KEY")
DEFAULT_CITY = get_env_var("DEFAULT_CITY", "Mumbai")


# ---------- Background ----------
def find_background():
    for folder in (BASE / "assets", BASE.parent / "assets", BASE, BASE.parent):
        for name in ("background.png", "background.jpg", "background.jpeg"):
            if (folder / name).exists():
                return folder / name
    return None


@st.cache_data
def encode(path: str, mtime: float) -> str:
    f = Path(path)
    mime = "png" if f.suffix.lower() == ".png" else "jpeg"
    return f"data:image/{mime};base64," + base64.b64encode(f.read_bytes()).decode()


bg_file = find_background()
BG = f"url({encode(str(bg_file), bg_file.stat().st_mtime)}) center/cover fixed," if bg_file else ""

CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap');
:root{--ink:#1f3a17;--mute:#5d7455;--g:#5a8a2c;--g2:#7fb03a;--line:#6f9a3d;--field:#fff;--trk:#d3dfc9;--chip:#dff0bd;--sun:#e0a020}
html,body,.stApp,.stApp div,.stApp p,.stApp label,.stApp input,.stApp button{font-family:'Outfit',system-ui,sans-serif}
[data-testid="stIconMaterial"],[data-testid="stIconMaterial"] *{font-family:"Material Symbols Rounded","Material Symbols Outlined","Material Icons"!important}
.stApp{background:__BG__#eef8ea;color:var(--ink)}
header[data-testid="stHeader"]{background:transparent}
#MainMenu,footer{visibility:hidden}
.block-container{max-width:1100px;padding:1.8rem 1.2rem 3rem}
.t{font-size:clamp(1.7rem,4vw,2.6rem);font-weight:700;letter-spacing:-.02em;line-height:1.2;color:var(--ink)}
.mute{color:var(--mute)}
[data-testid="stSelectbox"]>:last-child,[data-testid="stTextInput"]>:last-child{background:#fff!important;border:2px solid var(--line)!important;border-radius:20px!important;overflow:hidden;box-shadow:none!important}
[data-testid="stSelectbox"]>:last-child *,[data-testid="stTextInput"]>:last-child *{background:transparent!important;border-color:transparent!important;box-shadow:none!important}
.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:20px;align-items:stretch;margin-top:8px}
.card{background:rgba(255,255,255,.72);backdrop-filter:blur(6px);border:2px solid var(--line);border-radius:26px;padding:22px 24px;box-shadow:0 6px 18px rgba(60,90,30,.12);color:var(--ink)}
.c7{grid-column:span 7}.c5{grid-column:span 5}.c8{grid-column:span 8}.c4{grid-column:span 4}.c12{grid-column:span 12}
.h2{display:flex;align-items:center;gap:12px;font-size:1.3rem;margin:0 0 16px;font-weight:600}
.h2 svg{width:28px;height:28px;stroke:var(--g);fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;flex:none}
.wi{stroke:var(--g);fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;flex:none}
.now{display:flex;align-items:center;gap:22px;flex-wrap:wrap}
.now .big{font-size:clamp(4rem,10vw,6rem);font-weight:700;line-height:1;letter-spacing:-.04em}
.now .cond{font-size:1.4rem;font-weight:600}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:20px}
.tile{background:var(--field);border:2px solid var(--line);border-radius:18px;padding:10px 12px}
.tile span{display:block;color:var(--mute);font-size:.85rem}.tile b{font-size:1.2rem;font-weight:600}
.adv{display:flex;flex-direction:column;gap:14px}
.verdict{background:var(--chip);border:2px solid var(--line);border-radius:20px;padding:14px 16px;font-size:1.15rem;font-weight:600}
.verdict small{display:block;font-weight:400;color:var(--mute);font-size:.92rem;margin-top:4px}
.kv{display:flex;justify-content:space-between;padding:10px 0;border-bottom:2px dotted var(--line)}.kv:last-child{border:0}
.hours{display:flex;gap:12px;overflow-x:auto;padding-bottom:8px}
.h{flex:0 0 84px;text-align:center;background:var(--field);border:2px solid var(--line);border-radius:22px;padding:12px 6px;display:flex;flex-direction:column;align-items:center;gap:6px}
.h.first{background:linear-gradient(#c9e68a,var(--g2))}
.h b{font-size:1.15rem;font-weight:600}.h span{font-size:.85rem;color:var(--mute)}.h.first span{color:var(--ink)}
.day{display:grid;grid-template-columns:70px 32px 46px 38px 1fr 38px;align-items:center;gap:10px;padding:10px 0;border-bottom:2px dotted var(--line)}.day:last-child{border:0}
.day .d{font-weight:600}.day .r{color:var(--mute);font-size:.9rem}.day .tt{text-align:right;font-weight:500}
.bar{height:8px;border-radius:8px;background:var(--trk);position:relative}.bar i{position:absolute;top:0;bottom:0;border-radius:8px;background:linear-gradient(90deg,var(--g2),var(--sun))}
.det{display:grid;grid-template-columns:1fr 1fr;gap:10px}.full{grid-column:1/-1}
.tile.ring{display:flex;align-items:center;gap:8px;padding:8px}.tile.ring span{font-size:.8rem}.tile.ring b{font-size:1rem}
.uv{height:10px;border-radius:10px;background:linear-gradient(90deg,#5fbf4a,#e6d23a,#f0a030,#e05a3a,#9a4bd0);position:relative;margin:12px 0 4px}
.uv i{position:absolute;top:-5px;width:6px;height:20px;background:var(--ink);border:2px solid var(--field);border-radius:4px;transform:translateX(-50%)}
.mini{height:6px;border-radius:6px;background:var(--trk);margin-top:8px}.mini i{display:block;height:100%;border-radius:6px;background:var(--g2)}
.note{color:var(--mute);font-size:.88rem;text-align:center;margin-top:22px;font-weight:500}
@media(max-width:820px){.c7,.c5,.c8,.c4{grid-column:span 12}.tiles{grid-template-columns:1fr 1fr}.day{grid-template-columns:56px 28px 40px 34px 1fr 34px;gap:6px}}
</style>""".replace("__BG__", BG)
st.markdown(CSS, unsafe_allow_html=True)

# ---------- SVG Icons ----------
ICONS = {
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M5 19l1.5-1.5M17.5 6.5L19 5"/>',
    "cloud": '<path d="M7 18h10a4 4 0 0 0 .5-8A6 6 0 0 0 6 11a3.5 3.5 0 0 0 1 7z"/>',
    "rain": '<path d="M7 15h10a4 4 0 0 0 .5-8A6 6 0 0 0 6 8a3.5 3.5 0 0 0 1 7z"/><path d="M8 18l-1 3M12 18l-1 3M16 18l-1 3"/>',
    "part": '<circle cx="8" cy="8" r="3"/><path d="M8 2v1M2 8h1M3.8 3.8l.7.7M12.2 3.8l-.7.7"/><path d="M9 20h8a3.5 3.5 0 0 0 .4-7A5 5 0 0 0 8 14a3 3 0 0 0 1 6z"/>',
    "storm": '<path d="M7 14h10a4 4 0 0 0 .5-8A6 6 0 0 0 6 7a3.5 3.5 0 0 0 1 7z"/><path d="M12 14l-2 4h3l-2 4"/>',
}
NAME = {"sun": "Sunny", "part": "Partly cloudy", "cloud": "Cloudy", "rain": "Rain showers", "storm": "Thunderstorms"}
PCT_DEFAULT = {"sun": 5, "part": 20, "cloud": 35, "rain": 75, "storm": 85}

HEAD = {
    "cur": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M5 19l1.5-1.5M17.5 6.5L19 5"/>',
    "adv": '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
    "hrs": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "days": '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/>',
    "det": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.01"/>',
}


def rnd(x):
    return int(math.floor(x + 0.5))


def ic(k, s=30):
    svg_body = ICONS.get(k, ICONS["sun"])
    return f'<svg class="wi" width="{s}" height="{s}" viewBox="0 0 24 24">{svg_body}</svg>'


def head(k, text):
    return f'<div class="h2"><svg viewBox="0 0 24 24">{HEAD[k]}</svg>{text}</div>'


def tile(a, b):
    return f'<div class="tile"><span>{a}</span><b>{b}</b></div>'


def kv(a, b):
    return f'<div class="kv"><span class="mute">{a}</span><b>{b}</b></div>'


def hr_str(dt: datetime) -> str:
    return dt.strftime("%I %p").lstrip("0")


def map_weather_icon(weather_id: int) -> str:
    if 200 <= weather_id < 300:
        return "storm"
    elif 300 <= weather_id < 600:
        return "rain"
    elif 600 <= weather_id < 700:
        return "rain"
    elif 700 <= weather_id < 800:
        return "cloud"
    elif weather_id == 800:
        return "sun"
    elif weather_id in (801, 802):
        return "part"
    else:
        return "cloud"


# ---------- Fetch Live Data from OpenWeather API ----------
@st.cache_data(ttl=300, show_spinner=False)
def fetch_openweather_data(city_name: str, api_key: str):
    if not api_key:
        return None, None, "OpenWeather API key not found in .env"

    current_url = "https://api.openweathermap.org/data/2.5/weather"
    forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"q": city_name, "appid": api_key, "units": "metric"}

    try:
        r_cur = requests.get(current_url, params=params, timeout=7)
        if r_cur.status_code == 401:
            return None, None, "Invalid OpenWeather API Key"
        if r_cur.status_code == 404:
            return None, None, f"City '{city_name}' not found"
        r_cur.raise_for_status()
        cur_data = r_cur.json()

        r_fore = requests.get(forecast_url, params=params, timeout=7)
        r_fore.raise_for_status()
        fore_data = r_fore.json()

        return cur_data, fore_data, None
    except Exception as e:
        return None, None, f"Connection error: {e}"


# ---------- Fallback data if API key missing or offline ----------
FALLBACK_CITIES = {
    "Mumbai": dict(t=30, h=78, w=14, d=["rain", "rain", "storm", "part", "rain", "cloud", "part"]),
    "Pune": dict(t=27, h=60, w=10, d=["part", "sun", "sun", "cloud", "rain", "part", "sun"]),
    "Delhi": dict(t=33, h=45, w=12, d=["sun", "sun", "part", "sun", "cloud", "part", "sun"]),
    "Bengaluru": dict(t=26, h=65, w=11, d=["cloud", "rain", "part", "rain", "cloud", "part", "sun"]),
}

# ---------- Header + Controls ----------
if st.button("← Back to Dashboard"):
    try:
        st.switch_page("pages/6_Dashboard.py")
    except Exception:
        st.switch_page("6_Dashboard.py")

now = datetime.now()
H0 = now.hour

left, mid, right = st.columns([5, 2.5, 1.3], vertical_alignment="center", gap="medium")
left.markdown(
    f'<div class="t">Weather Forecast</div><div class="mute">{now:%A}, {now.day} {now:%B}</div>',
    unsafe_allow_html=True,
)

CITIES_LIST = [DEFAULT_CITY] + [c for c in ["Mumbai", "Pune", "Delhi", "Bengaluru", "Kolkata", "Chennai", "Hyderabad", "London", "New York"] if c != DEFAULT_CITY] + ["Custom city..."]
selected_option = mid.selectbox("City", CITIES_LIST, index=0, key="weather_city", label_visibility="collapsed")

if selected_option == "Custom city...":
    custom_city = st.text_input("Enter City Name", placeholder="e.g. Jaipur, Tokyo, Berlin", key="custom_city_input")
    target_city = custom_city.strip() if custom_city.strip() else DEFAULT_CITY
else:
    target_city = selected_option

try:
    unit = right.segmented_control("Unit", ["°C", "°F"], default="°C", key="unit", label_visibility="collapsed") or "°C"
except AttributeError:
    unit = right.radio("Unit", ["°C", "°F"], horizontal=True, key="unit", label_visibility="collapsed")

UNIT_C = unit == "°C"


def T(c):
    if c is None:
        return "—"
    val = c if UNIT_C else c * 9 / 5 + 32
    return f"{rnd(val)}°"


# Fetch live data
cur_data, fore_data, fetch_err = fetch_openweather_data(target_city, OPENWEATHER_API_KEY)

# Soil moisture from user's active garden if available
soil_display = "42%"
plants_data = st.session_state.get("plants", {})
sel_p = st.session_state.get("sel_plant")
if sel_p and sel_p in plants_data and plants_data[sel_p].get("has_data"):
    soil_display = f"{plants_data[sel_p]['moisture']:.0f}%"
elif plants_data:
    active_m = [p["moisture"] for p in plants_data.values() if p.get("has_data")]
    if active_m:
        soil_display = f"{sum(active_m) / len(active_m):.0f}%"

if cur_data and fore_data:
    # ===== LIVE DATA PROCESSING =====
    cur_temp = cur_data["main"]["temp"]
    feels_like = cur_data["main"].get("feels_like", cur_temp)
    humidity = cur_data["main"].get("humidity", 50)
    wind_kmh = round(cur_data["wind"].get("speed", 0) * 3.6, 1)
    pressure = cur_data["main"].get("pressure", 1013)
    visibility_km = round(cur_data.get("visibility", 10000) / 1000, 1)

    w_info = cur_data.get("weather", [{}])[0]
    w_id = w_info.get("id", 800)
    k0 = map_weather_icon(w_id)
    cond_name = w_info.get("description", "Clear").title()

    # Next 12 hours from 3-hour forecast entries
    forecast_list = fore_data.get("list", [])
    hrs = []
    # First slot is "Now"
    hrs.append(
        dict(
            label="Now",
            t=cur_temp,
            p=round(forecast_list[0].get("pop", 0) * 100) if forecast_list else PCT_DEFAULT[k0],
            k=k0,
            mm=forecast_list[0].get("rain", {}).get("3h", 0) if forecast_list else 0,
        )
    )

    rain_6h = 0.0
    for i, item in enumerate(forecast_list[:4]):
        item_dt = datetime.fromtimestamp(item.get("dt", 0))
        item_pop = round(item.get("pop", 0) * 100)
        item_id = item.get("weather", [{}])[0].get("id", 800)
        item_k = map_weather_icon(item_id)
        item_mm = float(item.get("rain", {}).get("3h", 0.0))
        if i < 2:  # first 2 entries = 6 hours
            rain_6h += item_mm
        hrs.append(dict(label=hr_str(item_dt), t=item["main"]["temp"], p=item_pop, k=item_k, mm=item_mm))

    rain_6h = round(rain_6h, 1)
    max_forecast_temp = max([x["t"] for x in hrs], default=cur_temp)

    # Daily aggregation from 5-day forecast
    days_map = {}
    for item in forecast_list:
        item_dt = datetime.fromtimestamp(item.get("dt", 0))
        day_key = item_dt.strftime("%Y-%m-%d")
        if day_key not in days_map:
            days_map[day_key] = {"dt": item_dt, "temps": [], "pops": [], "weather_ids": []}
        days_map[day_key]["temps"].append(item["main"]["temp"])
        days_map[day_key]["pops"].append(item.get("pop", 0) * 100)
        days_map[day_key]["weather_ids"].append(item.get("weather", [{}])[0].get("id", 800))

    days = []
    for i, (day_key, dinfo) in enumerate(list(days_map.items())[:7]):
        day_date = dinfo["dt"]
        dname = "Today" if i == 0 else day_date.strftime("%a")
        hi = max(dinfo["temps"])
        lo = min(dinfo["temps"])
        p = round(max(dinfo["pops"], default=0))
        best_wid = max(dinfo["weather_ids"], key=dinfo["weather_ids"].count)
        k = map_weather_icon(best_wid)
        days.append(dict(name=dname, k=k, hi=hi, lo=lo, p=p))

    if not days:
        days = [dict(name="Today", k=k0, hi=cur_temp + 2, lo=cur_temp - 4, p=PCT_DEFAULT[k0])]

    mn = min(d["lo"] for d in days)
    mx = max(d["hi"] for d in days)
    spread = max(1.0, mx - mn)

    # Irrigation Advice verdict
    if rain_6h >= 5.0:
        verdict = "Pause watering"
        why = f"Heavy rainfall ({rain_6h} mm) expected within 6 hours. Save water and prevent over-saturation."
    elif rain_6h >= 2.0:
        verdict = "Shorten the cycle"
        why = f"Light rain ({rain_6h} mm) forecast soon. The soil will receive natural moisture."
    elif max_forecast_temp >= 32.0:
        verdict = "Water at dawn or dusk"
        why = f"High temperature ({T(max_forecast_temp)}) forecast today. Avoid midday watering to prevent evaporation."
    else:
        verdict = "Follow normal schedule"
        why = "No significant rain expected. Soil moisture determines irrigation needs."

    # Sunrise / Sunset / Sun arc
    sys_info = cur_data.get("sys", {})
    sunrise_ts = sys_info.get("sunrise")
    sunset_ts = sys_info.get("sunset")
    if sunrise_ts and sunset_ts:
        rise_dt = datetime.fromtimestamp(sunrise_ts)
        set_dt = datetime.fromtimestamp(sunset_ts)
        rise_str = rise_dt.strftime("%I:%M %p").lstrip("0")
        set_str = set_dt.strftime("%I:%M %p").lstrip("0")
        rise_h = rise_dt.hour + rise_dt.minute / 60
        set_h = set_dt.hour + set_dt.minute / 60
    else:
        rise_str, set_str = "6:30 AM", "6:30 PM"
        rise_h, set_h = 6.5, 18.5

    now_h = H0 + now.minute / 60
    daytime = rise_h <= now_h <= set_h
    day_len = max(0.5, set_h - rise_h)
    f = max(0.0, min(1.0, (now_h - rise_h) / day_len))
    sx, sy = 120 - 100 * math.cos(math.pi * f), 95 - 90 * math.sin(math.pi * f)
    sun_x, sun_y = (sx, sy) if daytime else ((20 if now_h < rise_h else 220), 95)
    rays = (
        "".join(
            f'<line x1="{sx + 11 * math.cos(math.radians(a)):.1f}" y1="{sy + 11 * math.sin(math.radians(a)):.1f}" '
            f'x2="{sx + 16 * math.cos(math.radians(a)):.1f}" y2="{sy + 16 * math.sin(math.radians(a)):.1f}"/>'
            for a in range(0, 360, 45)
        )
        if daytime
        else ""
    )

    # UV & Dew Point
    uv = 8 if k0 == "sun" else 6 if k0 == "part" else 3 if k0 == "cloud" else 2
    uv_name = "Low" if uv < 3 else "Moderate" if uv < 6 else "High" if uv < 8 else "Very high" if uv < 11 else "Extreme"
    dew = cur_temp - (100 - humidity) / 5
    ring = 163.4 * min(100, max(0, humidity)) / 100
    hum_word = "Humid" if humidity > 70 else "Comfortable" if humidity > 45 else "Dry"

    rain_prob_now = hrs[0]["p"]
    note_html = f'<div class="note">🟢 Live weather data provided by <b>OpenWeather API</b> for <b>{target_city}</b> · Refreshed at {now.strftime("%I:%M %p")}</div>'

else:
    # ===== FALLBACK MODE =====
    if fetch_err:
        st.warning(f"⚠️ Live OpenWeather: {fetch_err}. Displaying cached/fallback forecast for {target_city}.")

    c = FALLBACK_CITIES.get(target_city, FALLBACK_CITIES["Mumbai"])
    k0 = c["d"][0]
    cur_temp = c["t"]
    feels_like = cur_temp + (3 if c["h"] > 60 else 0)
    cond_name = NAME[k0]
    humidity = c["h"]
    wind_kmh = c["w"]
    pressure = 1010
    visibility_km = 10.0
    rain_prob_now = PCT_DEFAULT[k0]

    hrs = []
    for i in range(5):
        h = (H0 + i * 3) % 24
        p = max(2, min(95, PCT_DEFAULT[k0] + rnd(15 * math.sin(i / 2))))
        k = "rain" if p >= 60 else "cloud" if p >= 30 else "part" if p >= 15 else "sun"
        hrs.append(dict(label="Now" if i == 0 else f"{h % 12 or 12} {'AM' if h < 12 else 'PM'}", t=cur_temp + rnd(3 * math.sin(i)), p=p, k=k, mm=round(p / 100 * 2, 1) if p >= 60 else 0))

    rain_6h = round(sum(x["mm"] for x in hrs[:2]), 1)
    if rain_6h >= 5:
        verdict, why = "Pause watering", "Rain is expected in the next 6 hours."
    else:
        verdict, why = "Follow normal schedule", "No significant rain expected soon."

    days = []
    for i, k in enumerate(c["d"]):
        hi = c["t"] + (2 if k == "sun" else -2 if k in ("rain", "storm") else 0)
        days.append(dict(name="Today" if i == 0 else ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][(now.weekday() + 1 + i) % 7], k=k, hi=hi, lo=hi - 6, p=PCT_DEFAULT[k] + (i * 5) % 10))

    mn = min(d["lo"] for d in days)
    mx = max(d["hi"] for d in days)
    spread = max(1.0, mx - mn)

    rise_str, set_str = "6:32 AM", "6:41 PM"
    sun_x, sun_y = 120, 30
    rays = ""
    daytime = True
    uv = 6
    uv_name = "Moderate"
    dew = cur_temp - 5
    ring = 163.4 * humidity / 100
    hum_word = "Comfortable"
    note_html = f'<div class="note">⚠️ Live weather unavailable. Connect internet or check OPENWEATHER_API_KEY in .env.</div>'


# ---------- Cards Construction ----------
cur_card = (
    f'<div class="card c7">{head("cur", "Current Conditions")}<div class="now"><div>{ic(k0, 84)}</div>'
    f'<div class="big">{T(cur_temp)}</div><div><div class="cond">{cond_name}</div>'
    f'<div class="mute">Feels like {T(feels_like)}</div></div></div>'
    f'<div class="tiles">{tile("Humidity", f"{humidity}%")}{tile("Wind", f"{wind_kmh:.0f} km/h")}{tile("Rain chance", f"{rain_prob_now}%")}</div></div>'
)

adv_card = (
    f'<div class="card c5">{head("adv", "Irrigation Advice")}<div class="adv"><div class="verdict">{verdict}<small>{why}</small></div><div>'
    f'{kv("Rain in next 6 hours", f"{rain_6h} mm")}{kv("Rain threshold", "5.0 mm")}{kv("Forecast buffer", "6 hours")}{kv("Soil moisture now", soil_display)}</div></div></div>'
)

hour_cells = "".join(
    f'<div class="h{"" if i else " first"}"><span>{x["label"]}</span>{ic(x["k"], 32)}<b>{T(x["t"])}</b><span>{x["p"]}%</span></div>'
    for i, x in enumerate(hrs)
)
hours_card = f'<div class="card c12">{head("hrs", "Next 12 Hours")}<div class="hours">{hour_cells}</div></div>'

day_rows = "".join(
    f'<div class="day"><span class="d">{d["name"]}</span>{ic(d["k"], 28)}<span class="r">{d["p"]}%</span>'
    f'<span class="tt mute">{T(d["lo"])}</span><div class="bar"><i style="left:{(d["lo"] - mn) / spread * 100:.1f}%;right:{100 - (d["hi"] - mn) / spread * 100:.1f}%"></i></div>'
    f'<span class="tt">{T(d["hi"])}</span></div>'
    for d in days
)
days_card = f'<div class="card c8">{head("days", "5-Day / Daily Forecast")}<div>{day_rows}</div></div>'

sun_svg = (
    f'<svg viewBox="0 0 240 118" width="100%" role="img" aria-label="Sun position">'
    f'<path d="M20 95A100 90 0 0 1 220 95" fill="none" stroke="#6f9a3d" stroke-width="2" stroke-dasharray="4 6"/>'
    f'<line x1="8" y1="95" x2="232" y2="95" stroke="#6f9a3d" stroke-width="2"/>'
    f'<g stroke="#e0a020" stroke-width="2" stroke-linecap="round">{rays}</g>'
    f'<circle cx="{sun_x:.1f}" cy="{sun_y:.1f}" r="8" fill="{"#e0a020" if daytime else "#d3dfc9"}" stroke="#6f9a3d" stroke-width="2"/>'
    f'<text x="26" y="113" font-size="11" fill="#5d7455" text-anchor="middle">{rise_str}</text>'
    f'<text x="214" y="113" font-size="11" fill="#5d7455" text-anchor="middle">{set_str}</text>'
    f'<text x="120" y="80" font-size="12" fill="#5d7455" text-anchor="middle">Sunrise · Sunset</text></svg>'
)

ring_svg = (
    f'<svg width="62" height="62" viewBox="0 0 62 62"><circle cx="31" cy="31" r="26" fill="none" stroke="#d3dfc9" stroke-width="7"/>'
    f'<circle cx="31" cy="31" r="26" fill="none" stroke="#7fb03a" stroke-width="7" stroke-linecap="round" stroke-dasharray="{ring:.1f} 163.4" transform="rotate(-90 31 31)"/>'
    f'<text x="31" y="35" font-size="13" font-weight="600" fill="#1f3a17" text-anchor="middle">{humidity}%</text></svg>'
)

det_card = (
    f'<div class="card c4">{head("det", "Details")}<div class="det"><div class="full">{sun_svg}</div>'
    f'<div class="full tile"><span>UV index</span><b>{uv} · {uv_name}</b><div class="uv"><i style="left:{min(uv, 11) / 11 * 100:.1f}%"></i></div></div>'
    f'<div class="tile ring">{ring_svg}<div><span>Humidity</span><b>{hum_word}</b></div></div>'
    f'<div class="tile"><span>Visibility</span><b>{visibility_km} km</b><div class="mini"><i style="width:{min(100.0, visibility_km * 10)}%"></i></div></div>'
    f'{tile("Pressure", f"{pressure} hPa")}{tile("Dew point", T(dew))}</div></div>'
)

# Render main grid
st.markdown(
    f'<div class="grid">{cur_card}{adv_card}{hours_card}{days_card}{det_card}</div>{note_html}',
    unsafe_allow_html=True,
)
