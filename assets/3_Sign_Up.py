"""
PlantPulse | Sign Up page.

Background: the leafy card artwork on a wider 2732 x 824 canvas with the card exactly
in the centre. It is read from assets/signup_wide.jpg, or - if that file is missing or
the wrong size - built automatically from assets/signup.png (see build_wide_canvas).
The canvas is scaled to the window HEIGHT, so the card, vines and grass are never
cropped and the card is centred on every screen; the extra width just fills the
sides. Every form element is pinned to a position on the card artwork.
"""
import base64
import re
import time
from io import BytesIO
from pathlib import Path

import requests
import streamlit as st

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
ASSET_DIR = Path(__file__).parent / "assets"
WIDE_PATH = ASSET_DIR / "signup_wide.jpg"      # prebuilt wide canvas (optional)
SOURCE_PATH = ASSET_DIR / "signup.png"         # original 1366 x 768 artwork
BACKEND_URL = "http://localhost:8000"

# Wide canvas = original 1366 x 768 artwork + padding (card ends up at the centre).
CANVAS_W, CANVAS_H = 2732, 824
PAD_X, PAD_Y = 700, 56              # artwork (0,0) sits at canvas (700, 56)
MIN_VISIBLE_W = 771                 # card width (691) + 40 px each side: never scale below this

st.set_page_config(
    page_title="PlantPulse | Sign Up",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.session_state.setdefault("auth_token", None)
st.session_state.setdefault("signup_success", False)

# ----------------------------------------------------------------------------
# LAYOUT  (pixels on the ORIGINAL 1366 x 768 artwork, top-left origin;
#          PAD_X / PAD_Y are added later to get canvas positions)
# ----------------------------------------------------------------------------
# The card spans x 321-1011 (centre x = 666). Between the top vine (ends
# y = 104) and the bottom vine (starts y = 607) there are 502 px of free space;
# everything below is built from these few numbers.
CARD_CX = 666                       # horizontal centre of the card
FIELD_W = 480                       # width of every input box
FIELD_X = CARD_CX - FIELD_W // 2    # 426 -> left edge shared by all inputs
TEXT_X = FIELD_X + 10               # labels + checkbox line up here
LABEL_H, LABEL_GAP = 23, 5          # label height, gap label -> input
FIRST_Y = 121                       # top of the first label
GROUP_PITCH = 83                    # distance from one label to the next
SIGNUP_W, GOOGLE_W = 254, 300       # button widths

# (key, label, hidden-text?)
FIELDS = [
    ("username", "Username", False),
    ("email", "Email", False),
    ("pw", "Set Password", True),
    ("confirm", "Confirm Password", True),
]

LAYOUT = {}
for _i, (_key, _label, _secret) in enumerate(FIELDS):
    _y = FIRST_Y + _i * GROUP_PITCH
    LAYOUT[f"su_l_{_key}"] = (TEXT_X, _y, None)                         # label
    LAYOUT[f"su_f_{_key}"] = (FIELD_X, _y + LABEL_H + LABEL_GAP, FIELD_W)  # input
LAYOUT["su_terms"] = (TEXT_X, 454, None)
LAYOUT["su_submit"] = (CARD_CX - SIGNUP_W // 2, 490, SIGNUP_W)
LAYOUT["su_google"] = (CARD_CX - GOOGLE_W // 2, 550, GOOGLE_W)


# ----------------------------------------------------------------------------
# STYLES
# ----------------------------------------------------------------------------
# "@{N}" = N pixels of the artwork, converted to cqw (1cqw = 1% of the stage
# width) so fonts, borders and sizes scale together with the background.
BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Patrick+Hand&display=swap');

:root {
    --leaf: #8fd44f;
    --leaf-soft: #72b062;
    --paper: #ecf8e9;
    --terms: #4f7a00;
    --forest: #006400;
    --check: #6aaa4a;
    --hand: 'Patrick Hand', 'Comic Sans MS', cursive;
}

/* ---------- page shell ---------- */
.stApp, [data-testid="stAppViewContainer"] { background: #ecf8e9; font-family: var(--hand); }
header[data-testid="stHeader"], [data-testid="stToolbar"],
[data-testid="stDecoration"], footer, #MainMenu { display: none !important; }
.block-container, [data-testid="stMainBlockContainer"] {
    max-width: 100% !important;
    padding: 0 !important;
}

/* ---------- stage: the wide canvas, scaled to the window HEIGHT (nothing is cropped) ---------- */
/* --u = screen pixels per canvas pixel. It is capped by the width too, so on a narrow
   window the card still fits. The canvas is centred, and the card is the canvas centre. */
.st-key-stage {
    --u: min(100vh / %%CH%%, 100vw / %%MINW%%);
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: calc(var(--u) * %%CW%%) !important;
    height: calc(var(--u) * %%CH%%) !important;
    max-width: none !important;     /* Streamlit would otherwise cap the stage at 100% of the window */
    min-width: 0 !important;
    max-height: none !important;
    flex: 0 0 auto !important;
    margin: 0;
    gap: 0;
    background-image: %%BG%%;
    background-size: 100% 100%;
    background-repeat: no-repeat;
    container-type: inline-size;
}

/* ---------- labels ---------- */
.st-key-stage .pp-label {
    font-family: var(--hand);
    font-size: @{23};
    line-height: 1;
    white-space: nowrap;
    color: var(--leaf-soft);
}
[class*="st-key-su_l_"] [data-testid="stMarkdownContainer"] { margin: 0; padding: 0; }

/* ---------- inputs: green rounded border ---------- */
[class*="st-key-su_f_"] {
    box-sizing: border-box;
    height: @{44};
    display: flex;
    align-items: center;
    background: var(--paper);
    border: max(2px, @{2.5}) solid var(--leaf);
    border-radius: @{15};
    box-shadow: @{8} @{9} @{11} rgba(0, 0, 0, 0.22);
    transition: border-color 0.15s;
}
[class*="st-key-su_f_"]:focus-within { border-color: #5fb82c; }

/* strip Streamlit's own field chrome so only the green border shows */
[class*="st-key-su_f_"] :is([data-testid="stTextInput"],
    [data-testid="stTextInputRootElement"], [data-baseweb="input"], [data-baseweb="base-input"]) {
    width: 100%;
    height: @{38};
    min-height: 0;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    background: transparent !important;
    border-radius: @{13};
}
[class*="st-key-su_f_"] input {
    height: 100%;
    padding: 0 @{14};
    font-family: var(--hand);
    font-size: @{20};
    color: #3d6b1f;
}
/* keep the (visually hidden) labels for screen readers */
[class*="st-key-su_f_"] [data-testid="stWidgetLabel"] {
    position: absolute; width: 1px; height: 1px; margin: 0; padding: 0;
    overflow: hidden; clip: rect(0 0 0 0);
}
[class*="st-key-su_f_"] button,                              /* password "eye" icon */
[class*="st-key-su_f_"] [data-testid="InputInstructions"] { display: none !important; }

/* ---------- checkbox: green square with white tick ---------- */
.st-key-su_terms [data-testid="stCheckbox"] { min-height: 0; }
.st-key-su_terms label { align-items: center; gap: @{8}; }
.st-key-su_terms label > span:first-child {
    width: @{26};
    height: @{26};
    border-radius: @{6};
    background-color: var(--paper) !important;
    border: 2px solid var(--check) !important;
}
.st-key-su_terms label:has(input:checked) > span:first-child {
    background-color: var(--check) !important;
    border-color: var(--check) !important;
}
.st-key-su_terms label p {
    margin: 0;
    font-family: var(--hand);
    font-size: @{21};
    line-height: 1.1;
    color: var(--terms);
    white-space: nowrap;
}

/* ---------- buttons ---------- */
.st-key-su_submit [data-testid="stButton"],
.st-key-su_google [data-testid="stButton"] { width: 100%; }

.st-key-su_submit button {
    width: 100%;
    height: @{56};
    min-height: 0;
    padding: 0;
    border: none !important;
    border-radius: 999px;
    background: linear-gradient(90deg, #8fdc55 0%, #c9e25f 100%) !important;
    box-shadow: @{7} @{9} @{12} rgba(0, 0, 0, 0.26);
}
.st-key-su_submit button p {
    margin: 0;
    font-family: var(--hand);
    font-size: @{28};
    line-height: 1;
    color: #fff;
}
.st-key-su_submit button:hover { filter: brightness(1.06); }
.st-key-su_submit button:active { transform: translateY(1px); }

.st-key-su_google button {
    width: 100%;
    height: @{38};
    min-height: 0;
    padding: 0;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
.st-key-su_google button p {
    margin: 0;
    font-family: var(--hand);
    font-size: @{25};
    font-weight: 700;
    line-height: 1;
    color: var(--forest);
    white-space: nowrap;
}
.st-key-su_google button:hover p { text-decoration: underline; }
</style>
"""


def build_wide_canvas(src: Path):
    """Build the 2732 x 824 canvas from the original 1366 x 768 artwork.

    The card (x 321-1011, y 64-649 on the original) is moved to the canvas centre.
    Left/right: the card-free margins are mirrored, blurred and faded to the flat page
    colour. Top: 56 px pad (mirrored art at the sides, flat colour above the vine).
    """
    import numpy as np
    from PIL import Image, ImageFilter

    a = np.array(Image.open(src).convert("RGB")).astype(np.float32)
    a[:2] = a[2]; a[-2:] = a[-3]; a[:, :2] = a[:, 2:3]; a[:, -2:] = a[:, -3:-2]  # lighter 2px frame
    h, w = a.shape[:2]
    flat = np.array([238, 248, 235], np.float32)
    smooth = lambda t: (lambda t: t * t * (3 - 2 * t))(np.clip(t, 0, 1))

    # top padding
    x = np.arange(w, dtype=np.float32)
    centre = (smooth((x - 318) / 24) * (1 - smooth((x - 1000) / 24)))[None, :, None]
    mirrored = a[:PAD_Y][::-1]
    top = mirrored * (1 - centre) + np.broadcast_to(flat, mirrored.shape) * centre
    a = np.concatenate([top, a], axis=0)

    # left / right
    mir_l, mir_r, fade = 300, 266, 400
    m = np.pad(a, ((0, 0), (mir_l, mir_r), (0, 0)), mode="symmetric")
    wm = m.shape[1]
    pe = np.pad(m, ((0, 0), (fade, fade), (0, 0)), mode="edge")
    blur = np.array(Image.fromarray(np.clip(pe, 0, 255).astype(np.uint8))
                    .filter(ImageFilter.GaussianBlur(38))).astype(np.float32)
    xc = np.arange(pe.shape[1], dtype=np.float32)
    dist = np.maximum(fade - xc, xc - (fade + wm - 1)).clip(min=0)
    inside = np.minimum(xc - fade, fade + wm - 1 - xc).clip(min=0)
    wb = np.where(dist > 0, 1.0, 1 - smooth(inside / 90))[None, :, None]
    out = pe * (1 - wb) + blur * wb
    alpha = smooth(dist / fade)[None, :, None]
    out = out * (1 - alpha) + flat * alpha
    return Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8))


def _stamp(path: Path) -> float:
    return path.stat().st_mtime if path.exists() else 0.0


@st.cache_data(show_spinner=False)
def background_data_uri(wide_stamp: float, src_stamp: float) -> str | None:
    """data: URI of the wide canvas, or None if no artwork could be found.
    The stamps are the files' modified times, so replacing a file refreshes the cache."""
    from PIL import Image

    if WIDE_PATH.exists():
        with Image.open(WIDE_PATH) as im:
            if im.size == (CANVAS_W, CANVAS_H):          # correct prebuilt file
                data = WIDE_PATH.read_bytes()
                return "data:image/jpeg;base64," + base64.b64encode(data).decode()
    if SOURCE_PATH.exists():                              # otherwise build it
        buf = BytesIO()
        build_wide_canvas(SOURCE_PATH).save(buf, "JPEG", quality=92, optimize=True, subsampling=0)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    return None


def layout_css() -> str:
    """Absolute position of every element, as % of the stage (the wide canvas)."""
    rules = []
    for name, (x, y, w) in LAYOUT.items():
        width = f"width: {w / CANVAS_W * 100:.4f}%;" if w else ""
        rules.append(
            f".st-key-{name} {{ position: absolute; margin: 0; "
            f"left: {(x + PAD_X) / CANVAS_W * 100:.4f}%; "
            f"top: {(y + PAD_Y) / CANVAS_H * 100:.4f}%; {width} }}"
        )
    return "<style>" + "\n".join(rules) + "</style>"


def inject_styles() -> None:
    uri = background_data_uri(_stamp(WIDE_PATH), _stamp(SOURCE_PATH))
    if uri is None:
        st.error(f"Background image not found. Put signup.png in: {ASSET_DIR}")
    css = (BASE_CSS
           .replace("%%BG%%", f'url("{uri}")' if uri else "none")
           .replace("%%CW%%", str(CANVAS_W))
           .replace("%%CH%%", str(CANVAS_H))
           .replace("%%MINW%%", str(MIN_VISIBLE_W)))
    # "@{N}" = N artwork pixels -> cqw (1cqw = 1% of the stage width)
    css = re.sub(
        r"@\{(\d+(?:\.\d+)?)\}",
        lambda m: f"{float(m.group(1)) / CANVAS_W * 100:.4f}cqw",
        css,
    )
    st.markdown(css + layout_css(), unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# VALIDATION + ACTIONS
# ----------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_signup(username: str, email: str, password: str,
                    confirm: str, accepted: bool) -> str | None:
    """Return an error message, or None when the form is valid."""
    if not all([username, email, password, confirm]):
        return "Please fill in all fields"
    if len(username) < 3:
        return "Username must be at least 3 characters"
    if not EMAIL_RE.match(email):
        return "Enter a valid email address"
    if len(password) < 6:
        return "Password must be at least 6 characters"
    if password != confirm:
        return "Passwords don't match"
    if not accepted:
        return "Please accept the terms and conditions"
    return None


def handle_signup() -> None:
    ss = st.session_state
    username = ss.get("su_f_username", "").strip()
    email = ss.get("su_f_email", "").strip()
    password = ss.get("su_f_pw", "")
    confirm = ss.get("su_f_confirm", "")

    error = validate_signup(username, email, password, confirm, ss.get("su_terms", False))
    if error:
        st.toast(error, icon="⚠️")
        return

    try:
        response = requests.post(
            f"{BACKEND_URL}/api/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password,
                # the backend still requires a full_name; use the username
                "full_name": username,
            },
            timeout=10,
        )
        if response.status_code == 200:
            ss.signup_success = True
        else:
            try:
                err_msg = response.json().get("detail", response.text)
            except Exception:
                err_msg = response.text
            st.toast(f"Sign up error: {err_msg}", icon="❌")
    except requests.RequestException as e:
        st.toast(f"Sign up error: {e}", icon="❌")


def handle_google() -> None:
    st.toast("Google sign-in isn't connected yet.", icon="ℹ️")


# ----------------------------------------------------------------------------
# PAGE
# ----------------------------------------------------------------------------
def signup_page() -> None:
    inject_styles()

    with st.container(key="stage"):
        for key, label, secret in FIELDS:
            with st.container(key=f"su_l_{key}"):
                st.markdown(f'<div class="pp-label">{label}</div>', unsafe_allow_html=True)
            st.text_input(
                label,
                key=f"su_f_{key}",
                type="password" if secret else "default",
                label_visibility="collapsed",
            )

        st.checkbox("I have accepted all terms and conditions.", value=True, key="su_terms")
        st.button("Sign Up", key="su_submit", on_click=handle_signup)
        st.button("Continue with Google", key="su_google", on_click=handle_google)


signup_page()

# Account created -> confirm, then send the user to the login page.
if st.session_state.pop("signup_success", False):
    st.toast("Account created! Please log in ✅", icon="✅")
    time.sleep(1.2)
    st.switch_page("pages/2_Login.py")
