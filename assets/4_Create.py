import base64
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Create Your Garden", layout="wide")

st.session_state.setdefault("auth_token", None)

# Guard: ensure user is logged in
if not st.session_state.get("auth_token"):
    st.warning("You must log in to access the Create page.")
    if st.button("Go to Login"):
        st.switch_page("pages/2_Login.py")
    st.stop()

# Auto-redirect for admin
if st.session_state.get("is_admin"):
    st.switch_page("pages/9_Admin.py")

import requests

BACKEND_URL = "http://localhost:8000"
token = st.session_state.get("auth_token")


# Step 1 & 2: Check if user has plants
def check_user_plants():
    try:
        res = requests.get(
            f"{BACKEND_URL}/api/plants/my-plants",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if res.status_code == 200:
            plants = res.json().get("plants", [])
            return len(plants) > 0
    except Exception:
        pass
    return False


st.session_state.has_plants = check_user_plants()
has_plants = st.session_state.has_plants

# ---- Path to the background image (lives in the "assets" folder) ----
# If your farm picture has a different file name, change it here.
BG_IMAGE_PATH = Path(__file__).parent / "assets" / "create.png"


@st.cache_data(show_spinner=False)
def get_base64(path_str: str) -> str:
    return base64.b64encode(Path(path_str).read_bytes()).decode()


bg_base64 = get_base64(str(BG_IMAGE_PATH))

# ----------------------------------------------------------------------------
# LAYOUT
# ----------------------------------------------------------------------------
# Everything is centred on the middle of the window (left: 50% + translateX(-50%)),
# sizes use min(vw, vh) so nothing overlaps on short windows, and the two button
# widths / the gap between them come from the variables below.
#
#   heading ........ 72px, letters start ~68px from the top   (top: 6vh)
#   tagline ........ 30px, just under the heading
#   lead text ...... 26px, ~36px higher than before          (top: 73.2vh)
#   buttons ........ ~36px higher than before                (top: 79.6vh)
# (px values above are for a 1910 x 915 window; they scale with the window)
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;0,700;0,800;1,600;1,700;1,800&display=swap');

    :root {{
        --serif: 'Playfair Display', Georgia, 'Times New Roman', serif;
        --ink: #3f6b17;              /* heading + lead text */
        --ink-soft: #4b7f2a;         /* tagline */
        --btn-w: min(22.2vw, 46.3vh);    /* width of each button */
        --btn-gap: min(1.68vw, 3.5vh);   /* gap between the two buttons */
        --btn-h: min(2.55vw, 5.3vh);     /* height of each button */
    }}

    #MainMenu, header, footer {{visibility: hidden;}}

    html, body {{
        margin: 0;
        padding: 0;
        overflow: hidden;
        height: 100%;
    }}

    [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
        overflow: hidden !important;
        height: 100vh !important;
    }}

    .block-container {{
        padding: 0 !important;
        max-width: 100% !important;
        height: 100vh !important;
        overflow: hidden !important;
    }}

    .stApp {{
        background-image: url("data:image/png;base64,{bg_base64}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        height: 100vh;
        width: 100vw;
        overflow: hidden;
        position: fixed;
        top: 0;
        left: 0;
    }}

    /* ---------- heading block (title + tagline) ---------- */
    .garden-head {{
        position: fixed;
        top: 6vh;
        left: 50%;
        transform: translateX(-50%);
        width: 100%;
        text-align: center;
        z-index: 20;
        pointer-events: none;
    }}
    .garden-title {{
        margin: 0;
        font-family: var(--serif);
        font-weight: 800;
        font-size: min(3.77vw, 7.9vh);
        line-height: 1.1;
        color: var(--ink);
    }}
    .garden-tagline {{
        margin: 1.7vh 0 0;
        font-family: var(--serif);
        font-style: italic;
        font-weight: 600;
        font-size: min(1.57vw, 3.3vh);
        line-height: 1.2;
        color: var(--ink-soft);
    }}

    /* ---------- lead text above the buttons ---------- */
    .garden-lead {{
        position: fixed;
        top: 73.2vh;
        left: 50%;
        transform: translateX(-50%);
        width: 100%;
        text-align: center;
        font-family: var(--serif);
        font-weight: 700;
        font-size: min(1.36vw, 2.85vh);
        line-height: 1.2;
        color: var(--ink);
        z-index: 20;
        pointer-events: none;
    }}

    /* ---------- buttons: pinned, centred, same size ---------- */
    .st-key-btn_dashboard, .st-key-btn_add_another, .st-key-btn_first_plant {{
        position: fixed;
        top: 79.6vh;
        width: var(--btn-w);
        margin: 0;
        z-index: 10;
    }}
    .st-key-btn_dashboard    {{ left: calc(50% - var(--btn-gap) / 2 - var(--btn-w)); }}
    .st-key-btn_add_another  {{ left: calc(50% + var(--btn-gap) / 2); }}
    .st-key-btn_first_plant  {{ left: calc(50% - var(--btn-w) / 2); }}

    :is(.st-key-btn_dashboard, .st-key-btn_add_another, .st-key-btn_first_plant) [data-testid="stButton"] {{
        width: 100%;
    }}

    /* slightly darker green than before: #9ace56 -> #77b435  now  #84b848 -> #5f9a2b */
    :is(.st-key-btn_dashboard, .st-key-btn_add_another, .st-key-btn_first_plant) button {{
        width: 100%;
        height: var(--btn-h);
        min-height: 0;
        padding: 0;
        color: #ffffff;
        background: linear-gradient(180deg, #84b848 0%, #5f9a2b 100%);
        border: none;
        border-radius: 999px;
        box-shadow: 0 6px 0 rgba(58, 100, 24, 0.75), 0 10px 18px rgba(0, 0, 0, 0.18);
        cursor: pointer;
        transition: transform 0.15s ease, filter 0.15s ease;
    }}
    :is(.st-key-btn_dashboard, .st-key-btn_add_another, .st-key-btn_first_plant) button p {{
        margin: 0;
        font-family: var(--serif) !important;
        font-style: italic !important;
        font-weight: 800 !important;
        font-size: min(1.37vw, 2.9vh) !important;
        line-height: 1 !important;
        letter-spacing: 0.5px;
        white-space: nowrap !important;
        color: #ffffff;
    }}
    :is(.st-key-btn_dashboard, .st-key-btn_add_another, .st-key-btn_first_plant) button:hover {{
        transform: translateY(-2px);
        filter: brightness(0.94);
        color: #ffffff;
    }}
    :is(.st-key-btn_dashboard, .st-key-btn_add_another, .st-key-btn_first_plant) button:active {{
        transform: translateY(2px);
        box-shadow: 0 3px 0 rgba(58, 100, 24, 0.75), 0 6px 10px rgba(0, 0, 0, 0.18);
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# TEXT
# ----------------------------------------------------------------------------
if has_plants:
    title, lead = "Welcome back!", "Go to your dashboard to monitor your plants."
else:
    title, lead = "Welcome! Ready to grow?", "Set up your first plant to get started."

st.markdown(
    f"""
    <div class="garden-head">
        <div class="garden-title">{title}</div>
        <div class="garden-tagline">Listening to your plants, byte by byte...</div>
    </div>
    <div class="garden-lead">{lead}</div>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# BUTTONS  (Step 3: different buttons depending on has_plants)
# ----------------------------------------------------------------------------
if has_plants:
    if st.button("📊 Go to Dashboard", key="btn_dashboard"):
        st.switch_page("pages/6_Dashboard.py")
    if st.button("🌱 Add Another Plant", key="btn_add_another"):
        st.switch_page("pages/5_Garden.py")
else:
    if st.button("🌱 Add Your First Plant", key="btn_first_plant"):
        st.switch_page("pages/5_Garden.py")
