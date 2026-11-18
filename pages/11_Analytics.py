"""
FloraPulse Analytics — Streamlit version
Same layout as the original design: background image, Analytics Overview,
Predictive Soil Moisture Trend, Weather Analysis, Water vs. Energy Efficiency
and Cost Analysis. Moisture, rain and pump data come from the backend; the
two cards with no real data source are labelled "(sample data)".

Cards are rendered as self-contained HTML (own CSS + own copy of Plotly)
via st.components.v1.html, so the white background / green border always
look the same regardless of which Streamlit version renders the page.
"""

import base64
import json
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Analytics", page_icon="🌿", layout="wide")

BACKEND_URL = "http://localhost:8000"
TS_IS_UTC = False        # sensor readings are stored with datetime.now() (local time)
WATER_THRESHOLD = 35
LOCAL_TZ = "Asia/Kolkata"  # used only to convert pump events, which the backend stores in UTC
LOOKBACK_HOURS = 168       # 7 days

# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------
st.session_state.setdefault("auth_token", None)
if not st.session_state.get("auth_token"):
    st.warning("You must log in to view analytics.")
    if st.button("Go to Login", key="analytics_login"):
        st.switch_page("pages/2_Login.py")
    st.stop()


def api(path, **kw):
    """GET helper. Returns (json, error)."""
    try:
        r = requests.get(
            f"{BACKEND_URL}{path}", timeout=10,
            headers={"Authorization": f"Bearer {st.session_state.auth_token}"}, **kw,
        )
    except requests.exceptions.RequestException:
        return None, "Cannot reach backend. Is it running?"
    if r.status_code == 401:
        st.session_state.auth_token = None
        st.switch_page("pages/2_Login.py")
        st.stop()
    if r.status_code >= 400:
        return None, f"Backend error {r.status_code}"
    return r.json(), None


# ---------------------------------------------------------------------------
# Background image
# ---------------------------------------------------------------------------
APP_DIR = Path(__file__).parent
BG_CANDIDATES = [
    APP_DIR / "background.png",
    APP_DIR / "assets" / "background.png",
    APP_DIR / "static" / "background.png",
    APP_DIR / "images" / "background.png",
]
BG_PATH = next((p for p in BG_CANDIDATES if p.exists()), None)
bg_b64 = base64.b64encode(BG_PATH.read_bytes()).decode() if BG_PATH else ""
if BG_PATH is None:
    st.warning(
        "background.png not found — place it next to app.py, or in an "
        "assets/, static/, or images/ subfolder."
    )

st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{bg_b64}");
        background-size: cover;
        background-position: center top;
        background-repeat: no-repeat;
        background-attachment: scroll;
    }}
    h1.app-title {{ text-align:center; color:#1f4d3a; margin-bottom:0; }}
    p.app-sub {{ text-align:center; color:#66786f; margin-top:4px; font-size:14px; }}
    iframe {{ border: none !important; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
if st.button("← Back to Dashboard"):
    st.switch_page("pages/6_Dashboard.py")

st.markdown("<h1 class='app-title'>🌿Analytics</h1>", unsafe_allow_html=True)
st.markdown(
    "<p class='app-sub'>Sense. Analyze. Irrigate.</p>",
    unsafe_allow_html=True,
)
st.write("")

# ---------------------------------------------------------------------------
# Card shell — every card is one fully self-contained HTML document.
# ---------------------------------------------------------------------------
CARD_CSS = """
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: 'Segoe UI', Roboto, -apple-system, sans-serif;
    background: transparent;
  }
  .card {
    background: #ffffff;
    border: 3px solid #5fa93a;
    border-radius: 24px;
    box-shadow: 5px 6px 0 rgba(60,110,30,0.12);
    padding: 18px 20px;
    height: calc(100vh - 6px);
    overflow: hidden;
  }
  .title {
    display: flex; align-items: center; gap: 8px;
    font-weight: 600; font-size: 15px; color: #1f4d3a; margin-bottom: 10px;
  }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: #5fa93a; }
  .stat-row { display: flex; justify-content: space-between; gap: 12px; margin-top: 14px; }
  .stat { flex: 1; text-align: left; }
  .stat label { display: block; font-size: 12px; color: #66786f; margin-bottom: 6px; }
  .stat .val { font-size: 26px; font-weight: 700; color: #2e7d54; }
  #chart { width: 100%; height: calc(100% - 34px); }
</style>
"""

PLOTLY_CDN = "https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"


def render_chart_card(title: str, fig_data: list, layout: dict, height: int = 340) -> None:
    """Render a card containing a Plotly chart as one self-contained HTML doc."""
    layout = {
        "margin": dict(l=10, r=10, t=6, b=6),
        "plot_bgcolor": "rgba(0,0,0,0)",
        "paper_bgcolor": "rgba(0,0,0,0)",
        "font": {"size": 12, "color": "#66786f"},
        "legend": {"orientation": "h", "y": -0.25, "x": 0.5, "xanchor": "center"},
        "xaxis": {"showgrid": False},
        "yaxis": {"gridcolor": "#eef4f0"},
        **layout,
    }
    html = f"""
    <html><head>{CARD_CSS}</head>
    <body>
      <div class="card">
        <div class="title"><span class="dot"></span>{title}</div>
        <div id="chart"></div>
      </div>
      <script src="{PLOTLY_CDN}"></script>
      <script>
        Plotly.newPlot(
          document.getElementById('chart'),
          {json.dumps(fig_data)},
          {json.dumps(layout)},
          {{displayModeBar: false, responsive: true}}
        );
      </script>
    </body></html>
    """
    components.html(html, height=height)


def render_overview_card(stats: list, height: int = 190) -> None:
    stat_html = "".join(
        f"<div class='stat'><label>{label}</label><div class='val'>{value}</div></div>"
        for label, value in stats
    )
    html = f"""
    <html><head>{CARD_CSS}</head>
    <body>
      <div class="card">
        <div class="title"><span class="dot"></span>Analytics Overview</div>
        <div class="stat-row">{stat_html}</div>
      </div>
    </body></html>
    """
    components.html(html, height=height)


# ---------------------------------------------------------------------------
# Load real data
# ---------------------------------------------------------------------------
def clean(series) -> list:
    return [None if pd.isna(v) else round(float(v), 1) for v in series]


def labels(idx) -> list:
    return [t.strftime("%a %H:%M") for t in idx]


plants_resp, err = api("/api/plants/my-plants")
if err:
    st.error(err)
    st.stop()
plants = (plants_resp or {}).get("plants", [])
if not plants:
    st.info("🌱 No plants yet. Add a plant and start a sensor to see analytics.")
    st.stop()

frames = {}      # plant name -> DataFrame indexed by timestamp
pump_times = []  # all pump ON timestamps (local time)
no_data = []
for p in plants:
    hist, _ = api("/api/sensor-data/history",
                  params={"plant_id": p["id"], "hours": LOOKBACK_HOURS, "limit": 5000})
    rows = (hist or {}).get("readings", [])
    if rows:
        df = pd.DataFrame(rows)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=TS_IS_UTC)
        if TS_IS_UTC:
            df["timestamp"] = df["timestamp"].dt.tz_convert(LOCAL_TZ).dt.tz_localize(None)
        for c in ("moisture", "temperature", "humidity"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["rain_detected"] = df["rain_detected"].fillna(False).astype(int)
        frames[p["name"]] = df.sort_values("timestamp").set_index("timestamp")
    else:
        no_data.append(p["name"])

    act, _ = api(f"/api/plants/{p['id']}/activity", params={"hours": LOOKBACK_HOURS})
    
    for ev in (act or {}).get("pump_events", []):
        pump_times.append(
            pd.to_datetime(ev["timestamp"], utc=True).tz_convert(LOCAL_TZ).tz_localize(None)
        )

if not frames:
    st.info("Not enough readings yet. Start the simulator or ESP32 and check back in a few minutes.")
    st.stop()
if no_data:
    st.caption("⏳ Waiting for first sensor reading: " + ", ".join(no_data))
all_df = pd.concat(frames.values())
BUCKET = "6h"   # 7 days -> 28 points per line

# ---------------------------------------------------------------------------
# Analytics Overview
# ---------------------------------------------------------------------------
below = (all_df["moisture"] < WATER_THRESHOLD).mean() * 100
render_overview_card([
    ("Readings Analysed", f"{len(all_df):,}"),
    ("Average Soil Moisture", f"{all_df['moisture'].mean():.0f}%"),
    (f"Time Below {WATER_THRESHOLD}%", f"{below:.0f}%"),
    ("Pump Runs (7 days)", str(len(pump_times))),
])

st.write("")

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"]

# ---------------------------------------------------------------------------
# Row 1: Moisture trend | Weather analysis
# ---------------------------------------------------------------------------
row1_left, row1_right = st.columns(2)

PALETTE = [
    ("#2e7d54", "rgba(46,125,84,0.15)"),
    ("#4CAF7D", "rgba(76,175,125,0.12)"),
    ("#9ccc9a", "rgba(156,204,154,0.1)"),
]

with row1_left:
    traces = []
    for i, (name, df) in enumerate(frames.items()):
        rs = df["moisture"].resample(BUCKET).mean()
        line, fill = PALETTE[i % len(PALETTE)]
        traces.append({
            "x": labels(rs.index), "y": clean(rs), "name": name,
            "mode": "lines", "connectgaps": True,
            "line": {"color": line, "shape": "spline"},
            "fill": "tozeroy", "fillcolor": fill,
        })
    render_chart_card(
        "Predictive Soil Moisture Trend",
        traces,
        {"yaxis": {"range": [0, 100], "gridcolor": "#eef4f0"}},
    )

with row1_right:
    rain_pct = all_df["rain_detected"].resample(BUCKET).mean() * 100
    moist = all_df["moisture"].resample(BUCKET).mean()
    render_chart_card(
        "Weather Analysis",
        [
            {"x": labels(rain_pct.index), "y": clean(rain_pct), "name": "Rain detected (%)",
             "mode": "lines", "connectgaps": True,
             "line": {"color": "#3a9668", "shape": "spline"}},
            {"x": labels(moist.index), "y": clean(moist), "name": "Soil Moisture (%)",
             "mode": "lines", "connectgaps": True,
             "line": {"color": "#e0a530", "dash": "dash", "shape": "spline"}},
        ],
        {},
    )

st.write("")

# ---------------------------------------------------------------------------
# Row 2: Water vs. Energy | Cost analysis  (no real source — sample data)
# ---------------------------------------------------------------------------
row2_left, row2_right = st.columns(2)

with row2_left:
    render_chart_card(
        "Water vs. Energy Efficiency (sample data)",
        [
            {"x": MONTHS, "y": [1200, 900, 1350, 1000, 1500, 1100, 1600, 1250],
             "name": "Water Used (L)", "type": "bar", "marker": {"color": "#3a9668"}},
            {"x": MONTHS, "y": [300, 220, 340, 260, 380, 290, 400, 310],
             "name": "Energy Cost ($)", "type": "bar", "marker": {"color": "#bfe8cf"}},
        ],
        {"barmode": "group"},
    )

with row2_right:
    render_chart_card(
        "Cost Analysis (sample data)",
        [
            {
                "type": "pie",
                "labels": ["Water Saved", "Energy Used", "Maintenance"],
                "values": [55, 30, 15],
                "hole": 0.6,
                "marker": {"colors": ["#2e7d54", "#e0a530", "#bfe8cf"]},
            }
        ],
        {"legend": {"orientation": "h", "y": -0.15, "x": 0.5, "xanchor": "center"}},
    )