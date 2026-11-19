import base64
import re
from pathlib import Path

import requests
import streamlit as st

# ----------------------------------------------------------------------------
# PAGE CONFIGURATION
# ----------------------------------------------------------------------------
# set_page_config must be the first Streamlit command on the page.
st.set_page_config(
    page_title="FloraPulse | Login",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.session_state.setdefault("auth_token", None)
st.session_state.setdefault("page", "login")

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
ASSET_DIR = Path(__file__).parent / "assets"
BG_STEM = "login_bg"  # assets/login_bg.png (card + vines + title)
REF_W, REF_H = 1366, 768

# Backend configuration
BACKEND_URL = "http://localhost:8000"

# name: (x, y, width) -> pixels on the 1366 x 768 design, top-left origin
CARD_CX = 666
FIELD_W = 480
FIELD_X = CARD_CX - FIELD_W // 2
TEXT_X = FIELD_X + 10
LOGIN_W, SIGNUP_W = 254, 298

LAYOUT = {
    "lbl_user": (TEXT_X, 189, None),
    "login_user": (FIELD_X, 223, FIELD_W),
    "lbl_pwd": (TEXT_X, 291, None),
    "login_pwd": (FIELD_X, 325, FIELD_W),
    "forgot_btn": (TEXT_X, 391, None),
    "login_btn": (CARD_CX - LOGIN_W // 2, 433, LOGIN_W),
    "signup_btn": (CARD_CX - SIGNUP_W // 2, 510, SIGNUP_W),
}


# ----------------------------------------------------------------------------
# ASSET HELPERS
# ----------------------------------------------------------------------------
def find_background():
    """Find the login background in assets/ or beside this Python file."""
    for folder in (ASSET_DIR, Path(__file__).parent):
        for ext in ("png", "jpg", "jpeg", "webp"):
            path = folder / f"{BG_STEM}.{ext}"
            if path.exists():
                return path
    return None


@st.cache_data(show_spinner=False)
def image_data_uri(path_str: str) -> str:
    path = Path(path_str)
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    mime = mime_types.get(path.suffix.lower())
    if mime is None:
        raise ValueError(f"Unsupported background image type: {path.suffix}")
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


# ----------------------------------------------------------------------------
# STYLES
# ----------------------------------------------------------------------------
# "@{N}" means N pixels in the 1366px reference design, converted to cqw.
BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Patrick+Hand&display=swap');

:root {
    --leaf: #8fd44f;
    --leaf-soft: #72b062;
    --leaf-dark: #2d5a12;
    --paper: #ecf8e9;
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

.st-key-stage {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: min(max(100vw, calc(100vh * 1366 / 768)), 179vw);
    aspect-ratio: 1366 / 768;
    margin: 0;
    gap: 0;
    background-image: %%BG%%;
    background-size: 100% 100%;
    background-repeat: no-repeat;
    container-type: inline-size;
}

.st-key-stage .pp-label {
    font-family: var(--hand);
    font-size: @{26};
    line-height: 1;
    white-space: nowrap;
    color: var(--leaf-soft);
}
.st-key-lbl_user [data-testid="stMarkdownContainer"],
.st-key-lbl_pwd [data-testid="stMarkdownContainer"] {
    margin: 0;
    padding: 0;
}

.st-key-login_user, .st-key-login_pwd {
    box-sizing: border-box;
    height: @{50};
    display: flex;
    align-items: center;
    background: var(--paper);
    border: max(2px, @{2.5}) solid var(--leaf);
    border-radius: @{16};
    box-shadow: @{9} @{10} @{12} rgba(0, 0, 0, 0.22);
    transition: border-color 0.15s;
}
.st-key-login_user:focus-within, .st-key-login_pwd:focus-within {
    border-color: #5fb82c;
}

:is(.st-key-login_user, .st-key-login_pwd) :is(
    [data-testid="stTextInput"],
    [data-testid="stTextInputRootElement"],
    [data-baseweb="input"],
    [data-baseweb="base-input"]
) {
    width: 100%;
    height: @{44};
    min-height: 0;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    background: transparent !important;
    border-radius: @{14};
}
:is(.st-key-login_user, .st-key-login_pwd) input {
    height: 100%;
    padding: 0 @{16};
    font-family: var(--hand);
    font-size: @{21};
    color: var(--leaf-dark);
}
:is(.st-key-login_user, .st-key-login_pwd) [data-testid="stWidgetLabel"] {
    position: absolute;
    width: 1px;
    height: 1px;
    margin: 0;
    padding: 0;
    overflow: hidden;
    clip: rect(0 0 0 0);
}
:is(.st-key-login_user, .st-key-login_pwd) button,
:is(.st-key-login_user, .st-key-login_pwd) [data-testid="InputInstructions"] {
    display: none !important;
}

.st-key-forgot_btn button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    min-height: 0 !important;
}
.st-key-forgot_btn button p {
    margin: 0;
    font-family: var(--hand);
    font-size: @{22};
    line-height: 1;
    font-weight: 700;
    color: var(--leaf-dark);
}
.st-key-forgot_btn button:hover p {
    text-decoration: underline;
}

.st-key-login_btn [data-testid="stButton"],
.st-key-signup_btn [data-testid="stButton"] {
    width: 100%;
}
.st-key-login_btn button {
    width: 100%;
    height: @{57};
    min-height: 0;
    padding: 0;
    border: none !important;
    border-radius: 999px;
    background: linear-gradient(90deg, #8fdc55 0%, #c9e25f 100%) !important;
    box-shadow: @{8} @{10} @{14} rgba(0, 0, 0, 0.26);
}
.st-key-login_btn button p {
    margin: 0;
    font-family: var(--hand);
    font-size: @{29};
    line-height: 1;
    color: #fff;
}
.st-key-login_btn button:hover {
    filter: brightness(1.06);
}
.st-key-login_btn button:active {
    transform: translateY(1px);
}

.st-key-signup_btn button {
    width: 100%;
    height: @{49};
    min-height: 0;
    padding: 0;
    border: max(2px, @{3}) solid var(--leaf) !important;
    border-radius: 0;
    background: var(--paper) !important;
    box-shadow: @{8} @{10} @{14} rgba(0, 0, 0, 0.22);
}
.st-key-signup_btn button p {
    margin: 0;
    font-family: var(--hand);
    font-size: @{22};
    line-height: 1;
    color: var(--leaf-soft);
    white-space: nowrap;
}
.st-key-signup_btn button:hover {
    background: #e0f4da !important;
}

.st-key-plain {
    max-width: 560px;
    margin: 12vh auto 0;
    padding: 0 1rem;
}
</style>
"""


def layout_css() -> str:
    """Position each widget as a percentage of the responsive background stage."""
    rules = []
    for name, (x, y, width_px) in LAYOUT.items():
        width_rule = (
            f"width: {width_px / REF_W * 100:.4f}%;"
            if width_px is not None
            else ""
        )
        rules.append(
            f".st-key-{name} {{ position: absolute; margin: 0; "
            f"left: {x / REF_W * 100:.4f}%; "
            f"top: {y / REF_H * 100:.4f}%; {width_rule} }}"
        )
    return "<style>" + "\n".join(rules) + "</style>"


def inject_styles(bg_uri=None) -> None:
    background = f'url("{bg_uri}")' if bg_uri else "none"
    css = BASE_CSS.replace("%%BG%%", background)
    css = re.sub(
        r"@\{(\d+(?:\.\d+)?)\}",
        lambda match: (
            f"{float(match.group(1)) / REF_W * 100:.4f}cqw"
        ),
        css,
    )
    st.markdown(css + layout_css(), unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# ACTIONS / AUTHENTICATION
# ----------------------------------------------------------------------------
def go(page: str) -> None:
    st.session_state.page = page


def handle_login() -> None:
    """Authenticate using the existing FloraPulse backend API."""
    user = st.session_state.get("login_user", "").strip()
    password = st.session_state.get("login_pwd", "")

    if not user or not password:
        st.toast("Please enter credentials", icon="⚠️")
        return

    try:
        response = requests.post(
            f"{BACKEND_URL}/api/auth/login",
            json={"username": user, "password": password},
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")

            if not token:
                st.toast("Login failed: No token received.", icon="⚠️")
                return

            # Keep the original backend/session contract unchanged.
            st.session_state.user = user
            st.session_state.auth_token = token
            st.session_state.is_admin = data.get("is_admin", False)
            st.session_state.username = data.get("username", "")
            st.session_state.pop("plants", None)

            st.toast("Login successful! ✅", icon="✅")
            # Streamlit reruns after the button callback. The authenticated
            # redirect below then sends the user to pages/4_Create.py.
        else:
            try:
                error_data = response.json()
                error_message = error_data.get("detail", response.text)
            except (ValueError, requests.exceptions.JSONDecodeError):
                error_message = response.text

            st.toast(f"Login error: {error_message}", icon="❌")

    except requests.RequestException as error:
        st.toast(f"Login request failed: {error}", icon="❌")


# If a valid token is already in the session, skip the login screen.
if st.session_state.get("auth_token"):
    st.switch_page("pages/4_Create.py")


# ----------------------------------------------------------------------------
# PAGES
# ----------------------------------------------------------------------------
def login_page() -> None:
    background = find_background()
    if background is None:
        st.error(
            f"Background image not found. Save it as '{BG_STEM}.png' in: "
            f"{ASSET_DIR}"
        )
        st.stop()

    inject_styles(image_data_uri(str(background)))

    with st.container(key="stage"):
        with st.container(key="lbl_user"):
            st.markdown(
                '<div class="pp-label">Enter Username or Email</div>',
                unsafe_allow_html=True,
            )

        st.text_input(
            "Username or email",
            key="login_user",
            label_visibility="collapsed",
        )

        with st.container(key="lbl_pwd"):
            st.markdown(
                '<div class="pp-label">Enter Password</div>',
                unsafe_allow_html=True,
            )

        st.text_input(
            "Password",
            type="password",
            key="login_pwd",
            label_visibility="collapsed",
        )

        st.button(
            "Forgot password?",
            key="forgot_btn",
            on_click=go,
            args=("forgot",),
        )
        st.button("Login", key="login_btn", on_click=handle_login)
        if st.button("Create Account", key="signup_btn"):
            st.switch_page("pages/3_Sign_Up.py")


def simple_page(title: str, message: str) -> None:
    inject_styles()
    with st.container(key="plain"):
        st.title(title)
        st.write(message)
        st.button(
            "← Back to login",
            key="back_btn",
            on_click=go,
            args=("login",),
        )


# ----------------------------------------------------------------------------
# ROUTER
# ----------------------------------------------------------------------------
page = st.session_state.page

if page == "forgot":
    simple_page("Reset your password", "Password-reset form goes here.")
else:
    login_page()
