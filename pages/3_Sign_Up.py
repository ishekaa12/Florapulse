"""
PlantPulse | Sign Up page.

Friend's responsive wide-canvas UI integrated with the existing registration
validation and backend API logic.
Expected project layout:
    project/
      assets/signup_wide.jpg   (optional prebuilt 2732 x 824 background)
      assets/signup.png        (fallback source artwork)
      pages/2_Login.py
      pages/3_Sign_Up.py
"""

import base64
import re
import time
from io import BytesIO
from pathlib import Path

import requests
import streamlit as st

# ----------------------------------------------------------------------------
# PAGE CONFIGURATION
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="PlantPulse | Sign Up",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
# This page is in project/pages/, while assets/ is at the project root.
PROJECT_DIR = Path(__file__).resolve().parent.parent
ASSET_DIR = PROJECT_DIR / "assets"
WIDE_PATH = ASSET_DIR / "signup_wide.jpg"
SOURCE_PATH = ASSET_DIR / "signup.png"
BACKEND_URL = "http://localhost:8000"

CANVAS_W, CANVAS_H = 2732, 824
PAD_X, PAD_Y = 700, 56
MIN_VISIBLE_W = 771

st.session_state.setdefault("signup_success", False)

# ----------------------------------------------------------------------------
# LAYOUT (positions on original 1366 x 768 artwork)
# ----------------------------------------------------------------------------
CARD_CX = 666
FIELD_W = 480
FIELD_X = CARD_CX - FIELD_W // 2
TEXT_X = FIELD_X + 10
LABEL_H, LABEL_GAP = 23, 5
FIRST_Y = 121
GROUP_PITCH = 83
SIGNUP_W, GOOGLE_W = 254, 300

FIELDS = [
    ("username", "Username", False),
    ("email", "Email", False),
    ("pw", "Set Password", True),
    ("confirm", "Confirm Password", True),
]

LAYOUT = {}
for index, (key, _label, _secret) in enumerate(FIELDS):
    y = FIRST_Y + index * GROUP_PITCH
    LAYOUT[f"su_l_{key}"] = (TEXT_X, y, None)
    LAYOUT[f"su_f_{key}"] = (
        FIELD_X,
        y + LABEL_H + LABEL_GAP,
        FIELD_W,
    )

LAYOUT["su_terms"] = (TEXT_X, 454, None)
LAYOUT["su_submit"] = (CARD_CX - SIGNUP_W // 2, 490, SIGNUP_W)
LAYOUT["su_google"] = (CARD_CX - GOOGLE_W // 2, 550, GOOGLE_W)

# ----------------------------------------------------------------------------
# STYLES
# ----------------------------------------------------------------------------
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

.stApp, [data-testid="stAppViewContainer"] {
    background: #ecf8e9;
    font-family: var(--hand);
}
header[data-testid="stHeader"], [data-testid="stToolbar"],
[data-testid="stDecoration"], footer, #MainMenu {
    display: none !important;
}
.block-container, [data-testid="stMainBlockContainer"] {
    max-width: 100% !important;
    padding: 0 !important;
}
[data-testid="stVerticalBlock"] { gap: 0 !important; }

.st-key-stage {
    --u: min(100vh / %%CH%%, 100vw / %%MINW%%);
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: calc(var(--u) * %%CW%%) !important;
    height: calc(var(--u) * %%CH%%) !important;
    max-width: none !important;
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

.st-key-stage .pp-label {
    font-family: var(--hand);
    font-size: @{23};
    line-height: 1;
    white-space: nowrap;
    color: var(--leaf-soft);
}
[class*="st-key-su_l_"] [data-testid="stMarkdownContainer"] {
    margin: 0;
    padding: 0;
}

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
[class*="st-key-su_f_"] :is(
    [data-testid="stTextInput"],
    [data-testid="stTextInputRootElement"],
    [data-baseweb="input"],
    [data-baseweb="base-input"]
) {
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
[class*="st-key-su_f_"] [data-testid="stWidgetLabel"] {
    position: absolute;
    width: 1px;
    height: 1px;
    margin: 0;
    padding: 0;
    overflow: hidden;
    clip: rect(0 0 0 0);
}
[class*="st-key-su_f_"] button,
[class*="st-key-su_f_"] [data-testid="InputInstructions"] {
    display: none !important;
}

.st-key-su_terms [data-testid="stCheckbox"] { min-height: 0; }
.st-key-su_terms label {
    align-items: center;
    gap: @{8};
}
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

.st-key-success_message {
    position: fixed;
    left: 50%;
    top: 90%;
    transform: translateX(-50%);
}
</style>
"""


def build_wide_canvas(src: Path):
    """Create the wide canvas from the original 1366 x 768 artwork."""
    import numpy as np
    from PIL import Image, ImageFilter

    image = np.array(Image.open(src).convert("RGB")).astype(np.float32)
    image[:2] = image[2]
    image[-2:] = image[-3]
    image[:, :2] = image[:, 2:3]
    image[:, -2:] = image[:, -3:-2]

    height, width = image.shape[:2]
    flat = np.array([238, 248, 235], np.float32)

    def smoothstep(values):
        values = np.clip(values, 0, 1)
        return values * values * (3 - 2 * values)

    x = np.arange(width, dtype=np.float32)
    centre = (
        smoothstep((x - 318) / 24)
        * (1 - smoothstep((x - 1000) / 24))
    )[None, :, None]

    mirrored_top = image[:PAD_Y][::-1]
    top = (
        mirrored_top * (1 - centre)
        + np.broadcast_to(flat, mirrored_top.shape) * centre
    )
    image = np.concatenate([top, image], axis=0)

    mirror_left, mirror_right, fade = 300, 266, 400
    mirrored = np.pad(
        image,
        ((0, 0), (mirror_left, mirror_right), (0, 0)),
        mode="symmetric",
    )
    padded = np.pad(mirrored, ((0, 0), (fade, fade), (0, 0)), mode="edge")

    blurred = np.array(
        Image.fromarray(np.clip(padded, 0, 255).astype(np.uint8))
        .filter(ImageFilter.GaussianBlur(38))
    ).astype(np.float32)

    x_coords = np.arange(padded.shape[1], dtype=np.float32)
    mirrored_width = mirrored.shape[1]
    distance = np.maximum(
        fade - x_coords,
        x_coords - (fade + mirrored_width - 1),
    ).clip(min=0)
    inside = np.minimum(
        x_coords - fade,
        fade + mirrored_width - 1 - x_coords,
    ).clip(min=0)

    blend = np.where(distance > 0, 1.0, 1 - smoothstep(inside / 90))
    blend = blend[None, :, None]
    output = padded * (1 - blend) + blurred * blend

    alpha = smoothstep(distance / fade)[None, :, None]
    output = output * (1 - alpha) + flat * alpha

    return Image.fromarray(np.clip(output + 0.5, 0, 255).astype(np.uint8))


def file_stamp(path: Path) -> float:
    return path.stat().st_mtime if path.exists() else 0.0


@st.cache_data(show_spinner=False)
def background_data_uri(wide_stamp: float, source_stamp: float):
    """Load the correctly sized wide image or build it from signup.png."""
    from PIL import Image

    if WIDE_PATH.exists():
        try:
            with Image.open(WIDE_PATH) as image:
                if image.size == (CANVAS_W, CANVAS_H):
                    data = WIDE_PATH.read_bytes()
                    return "data:image/jpeg;base64," + base64.b64encode(data).decode()
        except OSError:
            pass

    if SOURCE_PATH.exists():
        buffer = BytesIO()
        build_wide_canvas(SOURCE_PATH).save(
            buffer,
            "JPEG",
            quality=92,
            optimize=True,
            subsampling=0,
        )
        encoded = base64.b64encode(buffer.getvalue()).decode()
        return "data:image/jpeg;base64," + encoded

    return None


def layout_css() -> str:
    rules = []
    for name, (x, y, width_px) in LAYOUT.items():
        width_rule = (
            f"width: {width_px / CANVAS_W * 100:.4f}%;"
            if width_px is not None
            else ""
        )
        rules.append(
            f".st-key-{name} {{ position: absolute; margin: 0; "
            f"left: {(x + PAD_X) / CANVAS_W * 100:.4f}%; "
            f"top: {(y + PAD_Y) / CANVAS_H * 100:.4f}%; "
            f"{width_rule} }}"
        )
    return "<style>" + "\n".join(rules) + "</style>"


def inject_styles() -> bool:
    uri = background_data_uri(file_stamp(WIDE_PATH), file_stamp(SOURCE_PATH))
    if uri is None:
        st.error(
            f"Sign-up background not found. Add signup.png or signup_wide.jpg "
            f"to: {ASSET_DIR}"
        )
        return False

    css = (
        BASE_CSS
        .replace("%%BG%%", f'url("{uri}")')
        .replace("%%CW%%", str(CANVAS_W))
        .replace("%%CH%%", str(CANVAS_H))
        .replace("%%MINW%%", str(MIN_VISIBLE_W))
    )
    css = re.sub(
        r"@\{(\d+(?:\.\d+)?)\}",
        lambda match: (
            f"{float(match.group(1)) / CANVAS_W * 100:.4f}cqw"
        ),
        css,
    )
    st.markdown(css + layout_css(), unsafe_allow_html=True)
    return True


# ----------------------------------------------------------------------------
# VALIDATION + REGISTRATION
# ----------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_signup_form(
    username: str,
    email: str,
    password: str,
    password_confirm: str,
    accepted_terms: bool,
) -> tuple[bool, str]:
    """Preserve the original registration checks and validate the terms box."""
    if not all([username.strip(), email.strip(), password, password_confirm]):
        return False, "All fields required"
    if len(username.strip()) < 3:
        return False, "Username must be at least 3 characters"
    if not EMAIL_RE.match(email.strip()):
        return False, "Invalid email format"
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    if password != password_confirm:
        return False, "Passwords don't match"
    if not accepted_terms:
        return False, "Accept the terms and conditions to continue"
    return True, "Valid"


def handle_signup() -> None:
    session = st.session_state
    username = session.get("su_f_username", "").strip()
    email = session.get("su_f_email", "").strip()
    password = session.get("su_f_pw", "")
    password_confirm = session.get("su_f_confirm", "")
    accepted_terms = session.get("su_terms", False)

    valid, message = validate_signup_form(
        username,
        email,
        password,
        password_confirm,
        accepted_terms,
    )
    if not valid:
        st.toast(message, icon="⚠️")
        return

    try:
        response = requests.post(
            f"{BACKEND_URL}/api/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password,
                # The friend's four-field UI has no separate full-name field.
                # Preserve the backend's required full_name field by using username.
                "full_name": username,
            },
            timeout=10,
        )

        if response.status_code == 200:
            session.signup_success = True
        else:
            try:
                error_message = response.json().get("detail", response.text)
            except (ValueError, requests.exceptions.JSONDecodeError):
                error_message = response.text
            st.toast(f"Sign up error: {error_message}", icon="❌")

    except requests.RequestException as error:
        st.toast(f"Sign up error: {error}", icon="❌")


def handle_google() -> None:
    st.toast("Google sign-in isn't connected yet.", icon="ℹ️")


# ----------------------------------------------------------------------------
# PAGE
# ----------------------------------------------------------------------------
def signup_page() -> None:
    if not inject_styles():
        st.stop()

    with st.container(key="stage"):
        for key, label, secret in FIELDS:
            with st.container(key=f"su_l_{key}"):
                st.markdown(
                    f'<div class="pp-label">{label}</div>',
                    unsafe_allow_html=True,
                )

            st.text_input(
                label,
                key=f"su_f_{key}",
                type="password" if secret else "default",
                label_visibility="collapsed",
            )

        st.checkbox(
            "I have accepted all terms and conditions.",
            value=True,
            key="su_terms",
        )
        st.button("Sign Up", key="su_submit", on_click=handle_signup)
        st.button(
            "Continue with Google",
            key="su_google",
            on_click=handle_google,
        )


# ----------------------------------------------------------------------------
# ROUTING
# ----------------------------------------------------------------------------
if st.session_state.get("signup_success", False):
    st.toast("Account created! Please log in ✅", icon="✅")
    time.sleep(1.2)
    st.session_state.signup_success = False
    st.switch_page("pages/2_Login.py")
else:
    signup_page()
