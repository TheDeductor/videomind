"""Theme tokens and the single CSS block that styles the whole app.

Why a Python module instead of a .css file? So we can substitute palette
values into CSS variables on the fly when the user toggles dark/light mode,
without needing a build step.

LIGHT-MODE BUG FIX
------------------
The original version had several places where Streamlit's default white text
leaked through onto the light background, making text invisible:

* `[data-testid="stMarkdownContainer"]` and its descendants weren't getting
  an explicit `color: var(--tx)`, so Streamlit's compiled default — which
  is locked to a dark theme in some builds — won. We now set the color
  explicitly on every text container.
* `st.text()` renders into a `<pre>` that inherits from its parent and was
  also missing an override.
* Tab content (`[data-testid="stTabContent"]`) needed its own rule because
  Streamlit scopes some defaults there.
* The gradient page-title used `-webkit-text-fill-color: transparent` which
  silently fails in some browsers; we now provide a solid colour fallback
  via `color` set ahead of the gradient.
"""

from __future__ import annotations

from .models import Theme


def palette(theme: Theme) -> dict[str, str]:
    """Return the colour tokens for a given theme."""
    is_dark = theme == Theme.DARK
    return {
        # Layered surfaces
        "bg":       "#0a0a0c" if is_dark else "#f8f8fa",
        "surface":  "#141416" if is_dark else "#ffffff",
        "elevated": "#1c1c1f" if is_dark else "#f0f0f2",
        # Borders
        "border":   "#27272a" if is_dark else "#e2e2e5",
        "border_s": "#1e1e21" if is_dark else "#eeeef0",
        # Text — three tiers for hierarchy
        "text":  "#ededef" if is_dark else "#111113",
        "text2": "#8b8b8f" if is_dark else "#4b4b52",  # bumped contrast in light mode
        "text3": "#5c5c63" if is_dark else "#71717a",  # bumped contrast in light mode
        # Accent (blue family)
        "accent":   "#3b82f6" if is_dark else "#2563eb",
        "accent_h": "#2563eb" if is_dark else "#1d4ed8",
        "accent_m": "rgba(59,130,246,0.10)" if is_dark else "rgba(37,99,235,0.06)",
        "accent_b": "rgba(59,130,246,0.22)" if is_dark else "rgba(37,99,235,0.14)",
        # Semantic colours
        "ok":      "#22c55e" if is_dark else "#16a34a",
        "ok_bg":   "#0a1a0f" if is_dark else "#f0fdf4",
        "warn":    "#f59e0b" if is_dark else "#d97706",
        "warn_bg": "#1a140a" if is_dark else "#fffbeb",
        "err":     "#ef4444" if is_dark else "#dc2626",
        "err_bg":  "#1a0a0a" if is_dark else "#fef2f2",
        # Code blocks
        "code_bg": "#1a1a22" if is_dark else "#f4f4f6",
        "code_tx": "#a5b4fc" if is_dark else "#4338ca",
        # Inputs and scrollbars
        "input_bg": "#0f0f12" if is_dark else "#ffffff",
        "sb":       "#27272a" if is_dark else "#d4d4d8",
        "sb_h":     "#3b82f6" if is_dark else "#2563eb",
    }


def build_css(theme: Theme) -> str:
    """Compose the full CSS block for the chosen theme."""
    p = palette(theme)
    return _CSS_TEMPLATE.format(**p)


# Triple braces because str.format treats `{` specially and we need literal CSS braces.
_CSS_TEMPLATE = """\
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

:root {{
    --bg:{bg};--sf:{surface};--el:{elevated};
    --bd:{border};--bds:{border_s};
    --tx:{text};--t2:{text2};--t3:{text3};
    --ac:{accent};--ah:{accent_h};--am:{accent_m};--ab:{accent_b};
    --ok:{ok};--okbg:{ok_bg};
    --wn:{warn};--wnbg:{warn_bg};
    --er:{err};--erbg:{err_bg};
    --cbg:{code_bg};--ctx:{code_tx};
    --ibg:{input_bg};--sb:{sb};--sbh:{sb_h};
}}

/* ─── RESET ──────────────────────────────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stApp"] {{
    background: var(--bg) !important;
    color: var(--tx) !important;
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}}

#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] {{ display: none !important; }}

/* ─── LIGHT-MODE FIX: force text colour onto every container Streamlit ─────
   leaves as inherited. Without these, the body bg is light but Streamlit's
   default text stays white and disappears. ───────────────────────────────── */
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] strong,
[data-testid="stMarkdownContainer"] em,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4,
[data-testid="stMarkdownContainer"] h5,
[data-testid="stMarkdownContainer"] h6,
[data-testid="stText"],
[data-testid="stCaptionContainer"],
[data-testid="stTabContent"],
[data-testid="stTabContent"] *,
.stMarkdown, .stMarkdown * {{
    color: var(--tx) !important;
}}

[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] * {{
    color: var(--t3) !important;
}}

/* ─── SIDEBAR ────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    background: var(--sf) !important;
    border-right: 1px solid var(--bd) !important;
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
}}

[data-testid="stSidebar"] > div {{ padding: 1.6rem 1.2rem !important; }}

.sb-brand {{
    margin-bottom: 1.8rem;
    padding-bottom: 1.4rem;
    border-bottom: 1px solid var(--bd);
    animation: slideDown .4s ease-out;
}}

.sb-brand h1 {{
    font-size: 1.15rem; font-weight: 700;
    letter-spacing: -0.02em; line-height: 1; margin: 0;
    /* Solid colour fallback BEFORE the gradient, so unsupported browsers
       still see the title. */
    color: var(--ac);
    background: linear-gradient(135deg, var(--ac), var(--ah));
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent;
}}

.sb-brand p {{
    font-size: 0.7rem; color: var(--t3);
    margin: 4px 0 0; letter-spacing: 0.02em;
}}

.sb-label {{
    font-size: 0.68rem; color: var(--t3);
    text-transform: uppercase; letter-spacing: 0.1em;
    font-weight: 600; margin: 1.5rem 0 0.5rem;
    display: block;
}}

[data-testid="stSidebar"] label {{
    color: var(--t2) !important;
    font-size: 0.8rem !important; font-weight: 500 !important;
    margin-bottom: 0.3rem !important;
}}

[data-testid="stSidebar"] input,
[data-testid="stSidebar"] select,
[data-testid="stSidebar"] [data-baseweb="select"] {{
    background: var(--ibg) !important;
    border: 1px solid var(--bd) !important;
    border-radius: 8px !important;
    color: var(--tx) !important;
    font-family: inherit !important; font-size: 0.86rem !important;
    transition: all .2s ease !important;
}}

[data-testid="stSidebar"] [data-baseweb="select"] * {{
    color: var(--tx) !important; background: var(--ibg) !important;
}}

[data-testid="stSidebar"] input:focus {{
    border-color: var(--ac) !important;
    box-shadow: 0 0 0 3px var(--am) !important;
    outline: none !important;
}}

/* ─── MAIN CONTAINER ─────────────────────────────────────────────────────── */
[data-testid="stMainBlockContainer"] {{
    padding: 2.5rem 3rem !important;
    max-width: 900px !important; margin: 0 auto !important;
}}

.pg-h {{ margin-bottom: 2rem; animation: fadeIn .5s ease-out; }}

.pg-h h1 {{
    font-size: 2rem; font-weight: 700;
    letter-spacing: -0.03em; line-height: 1.1; margin: 0;
    color: var(--tx);
    background: linear-gradient(135deg, var(--tx), var(--t2));
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent;
}}

.pg-h p {{
    color: var(--t3); font-size: 0.92rem;
    margin: 6px 0 0; font-weight: 400;
}}

/* ─── TEXT INPUTS ────────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {{
    background: var(--ibg) !important;
    border: 1px solid var(--bd) !important;
    border-radius: 10px !important;
    color: var(--tx) !important;
    font-family: inherit !important;
    transition: all .2s ease !important;
}}

[data-testid="stTextInput"] input {{ font-size: .92rem !important; padding: .7rem 1rem !important; }}
[data-testid="stTextArea"] textarea {{ font-size: .88rem !important; line-height: 1.6 !important; }}

[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {{
    border-color: var(--ac) !important;
    box-shadow: 0 0 0 3px var(--am) !important;
    outline: none !important;
}}

[data-testid="stTextInput"] input:focus {{ transform: translateY(-1px); }}

[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label {{
    color: var(--t3) !important;
    font-size: .78rem !important; font-weight: 500 !important;
}}

/* ─── BUTTONS ────────────────────────────────────────────────────────────── */
.stButton button {{
    font-family: inherit !important; font-weight: 500 !important;
    border-radius: 8px !important; border: none !important;
    transition: all .2s ease !important;
    font-size: .88rem !important; cursor: pointer !important;
}}

.stButton button[kind="primary"] {{
    background: linear-gradient(135deg, var(--ac), var(--ah)) !important;
    color: #fff !important; padding: .6rem 1.4rem !important;
    box-shadow: 0 2px 8px rgba(59, 130, 246, 0.25);
}}

.stButton button[kind="primary"]:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.35) !important;
}}

.stButton button[kind="primary"]:active {{ transform: translateY(0) !important; }}

.stButton button[kind="secondary"] {{
    background: var(--sf) !important;
    color: var(--ac) !important;
    border: 1px solid var(--bd) !important;
    padding: .5rem 1.1rem !important;
}}

.stButton button[kind="secondary"]:hover {{
    border-color: var(--ac) !important;
    background: var(--am) !important;
    transform: translateY(-1px) !important;
}}

/* ─── FORM WRAPPER ───────────────────────────────────────────────────────── */
[data-testid="stForm"] {{
    background: var(--sf) !important;
    border: 1px solid var(--bd) !important;
    border-radius: 12px !important;
    padding: .4rem !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}}

/* ─── VIDEO CARD ─────────────────────────────────────────────────────────── */
.vcard {{
    background: var(--sf);
    border: 1px solid var(--bd);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 1.5rem;
    display: flex; align-items: center; gap: 14px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    animation: slideUp .4s ease-out;
}}

.vcard-thumb {{
    width: 96px; height: 54px;
    border-radius: 6px; object-fit: cover;
    flex-shrink: 0;
    border: 1px solid var(--bd);
}}

.vcard-dot {{
    width: 10px; height: 10px;
    border-radius: 50%; background: var(--ok);
    flex-shrink: 0; box-shadow: 0 0 8px var(--ok);
    animation: pulse 2s ease-in-out infinite;
}}

@keyframes pulse {{
    0%, 100% {{ opacity: 1; transform: scale(1); }}
    50%      {{ opacity: 0.7; transform: scale(0.95); }}
}}

.vcard-info {{ flex: 1; min-width: 0; }}

.vcard-info h3 {{
    font-size: .9rem; font-weight: 600;
    color: var(--tx); margin: 0 0 4px 0;
}}

.vcard-info p {{
    font-size: .75rem; color: var(--t3);
    margin: 0; line-height: 1.5;
}}

.vcard-stat {{
    display: inline-block;
    font-size: .72rem; color: var(--t2);
    background: var(--el);
    padding: 3px 9px; border-radius: 5px;
    margin-right: 7px; font-weight: 500;
}}

/* ─── SENTIMENT BADGES ───────────────────────────────────────────────────── */
.sent-badge {{
    display: inline-block;
    font-size: .72rem; font-weight: 600;
    padding: 3px 9px; border-radius: 5px;
    margin-right: 7px;
}}

.sent-pos {{ color: var(--ok); background: var(--okbg); }}
.sent-neg {{ color: var(--er); background: var(--erbg); }}
.sent-mix {{ color: var(--wn); background: var(--wnbg); }}

/* ─── CHAT TURNS ─────────────────────────────────────────────────────────── */
.uq {{
    color: var(--t2);
    font-size: .9rem; font-weight: 500;
    padding: .7rem 0 .2rem;
    user-select: text;
}}
.uq::before {{
    content: ""; display: inline-block;
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--ac); margin-right: 8px;
    transform: translateY(-2px);
}}

.aa {{
    background: var(--sf);
    border: 1px solid var(--bd);
    border-radius: 10px;
    padding: 1.2rem 1.4rem;
    margin: .2rem 0 1rem;
    font-size: .9rem; line-height: 1.7;
    color: var(--tx);
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
    animation: fadeInUp .3s ease-out;
}}

.aa.err {{ border-color: var(--er) !important; background: var(--erbg) !important; }}

.aa p {{ margin: 0 0 .6rem; color: var(--tx); }}
.aa p:last-child {{ margin-bottom: 0; }}
.aa strong {{ color: var(--tx); font-weight: 600; }}
.aa em {{ color: var(--t2); font-style: italic; }}

.aa a {{
    color: var(--ac); text-decoration: none;
    border-bottom: 1px solid var(--am);
    transition: all .2s ease;
}}
.aa a:hover {{ border-bottom-color: var(--ac); }}

.aa code {{
    background: var(--cbg); color: var(--ctx);
    padding: .15rem .4rem; border-radius: 5px;
    font-size: .84em;
    font-family: 'JetBrains Mono', monospace; font-weight: 500;
}}

.aa pre {{
    background: var(--bg);
    border: 1px solid var(--bd);
    border-radius: 8px;
    padding: 1rem 1.2rem; overflow-x: auto;
    margin: .6rem 0;
}}

.aa pre code {{ background: none; padding: 0; color: var(--tx); font-size: .84em; }}

.aa ul, .aa ol {{ padding-left: 1.4rem; margin: .4rem 0; }}
.aa li {{ margin-bottom: .25rem; color: var(--tx); }}
.aa li strong {{ color: var(--tx); }}

.aa h2, .aa h3 {{
    font-weight: 600; color: var(--tx);
    margin: .9rem 0 .4rem; font-size: 1rem;
}}

.aa table {{
    width: 100%; border-collapse: collapse;
    margin: .6rem 0; font-size: .84rem;
    border-radius: 8px; overflow: hidden;
}}

.aa th {{
    background: var(--el); color: var(--t2);
    padding: .5rem .75rem; text-align: left;
    border-bottom: 1px solid var(--bd); font-weight: 600;
}}

.aa td {{
    padding: .5rem .75rem;
    border-bottom: 1px solid var(--bds);
    color: var(--tx);
}}

.aa td strong {{ color: var(--tx); }}

.aa blockquote {{
    border-left: 3px solid var(--ac);
    background: var(--am);
    padding: .5rem .8rem;
    border-radius: 0 6px 6px 0;
    margin: .5rem 0;
    color: var(--t2);
    font-style: italic;
}}

.tsep {{ height: 1px; background: var(--bds); margin: .3rem 0; }}

/* ─── SUGGESTION CHIPS ───────────────────────────────────────────────────── */
.chip-btn button {{
    background: var(--sf) !important;
    border: 1px solid var(--bd) !important;
    color: var(--t2) !important;
    border-radius: 20px !important;
    padding: .4rem 1rem !important;
    font-size: .78rem !important; font-weight: 500 !important;
    transition: all .2s ease !important;
    white-space: normal !important;  /* lets long chips wrap on narrow screens */
}}

.chip-btn button:hover {{
    background: var(--am) !important;
    border-color: var(--ab) !important;
    color: var(--ac) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08) !important;
}}

/* ─── CHAPTERS & TRANSCRIPT VIEWERS ──────────────────────────────────────── */
.ch-item {{
    display: flex; align-items: center; gap: 12px;
    padding: .6rem .8rem; border-radius: 8px;
    font-size: .84rem; color: var(--t2);
    transition: all .2s ease;
}}
.ch-item:hover {{ background: var(--el); transform: translateX(4px); }}

.ch-time {{
    color: var(--ac); font-weight: 600;
    font-variant-numeric: tabular-nums;
    min-width: 60px; font-size: .8rem;
}}
.ch-title {{ color: var(--tx); font-weight: 500; }}

.ts-viewer {{
    font-size: .82rem; line-height: 1.8;
    max-height: 400px; overflow-y: auto;
    padding: .5rem 0;
    color: var(--tx);
}}
.ts-viewer .t {{
    color: var(--ac); font-weight: 600;
    font-variant-numeric: tabular-nums;
    margin-right: .5rem;
}}

/* ─── MISC STREAMLIT WIDGETS ─────────────────────────────────────────────── */
[data-testid="stExpander"] {{
    background: var(--sf) !important;
    border: 1px solid var(--bd) !important;
    border-radius: 10px !important;
}}
[data-testid="stExpander"] summary {{
    color: var(--t2) !important;
    font-size: .82rem !important; font-weight: 500 !important;
}}
[data-testid="stExpander"] > div > div {{ padding: 0 1rem .8rem !important; }}

[data-testid="stAlert"] {{
    border-radius: 10px !important;
    font-family: inherit !important; font-size: .86rem !important;
}}

[data-testid="stSelectbox"] > div > div {{ background: var(--ibg) !important; }}
[data-testid="stSelectbox"] label {{ font-size: .78rem !important; }}

[data-testid="stToggle"] > label > div {{ background: var(--el) !important; }}
[data-testid="stToggle"] > label > div[aria-checked="true"] > div {{ background: var(--ac) !important; }}

[data-testid="stSlider"] [role="slider"] {{ background: var(--ac) !important; }}

[data-testid="stTabs"] {{ margin-top: .5rem; }}
[data-testid="stTabs"] button {{
    font-size: .84rem !important; font-weight: 500 !important;
    color: var(--t3) !important;
    transition: all .2s ease !important;
}}
[data-testid="stTabs"] button[aria-selected="true"] {{ color: var(--ac) !important; }}
[data-testid="stTabs"] button:hover {{ color: var(--ac) !important; }}

[data-testid="column"] {{ padding: 0 !important; }}

[data-testid="stDownloadButton"] button {{
    background: var(--sf) !important;
    border: 1px solid var(--bd) !important;
    color: var(--t2) !important;
    border-radius: 8px !important;
    font-size: .8rem !important;
    transition: all .2s ease !important;
}}
[data-testid="stDownloadButton"] button:hover {{
    border-color: var(--ac) !important;
    color: var(--ac) !important;
    transform: translateY(-1px) !important;
}}

[data-testid="stSpinner"] > div {{ border-color: var(--ac) !important; }}

/* ─── SCROLLBARS ─────────────────────────────────────────────────────────── */
::-webkit-scrollbar      {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track{{ background: transparent; }}
::-webkit-scrollbar-thumb{{ background: var(--sb); border-radius: 10px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--sbh); }}

/* ─── WELCOME + ACTION HELPERS ───────────────────────────────────────────── */
.welcome {{
    text-align: center;
    padding: 2.5rem 0 1.5rem;
    animation: fadeIn .6s ease-out;
}}
.welcome-icon {{ font-size: 2.5rem; margin-bottom: .8rem; opacity: .6; }}
.welcome p {{ color: var(--t3); font-size: .92rem; }}

.sb-act button {{
    background: transparent !important;
    color: var(--t3) !important;
    border: 1px solid var(--bds) !important;
    font-size: .76rem !important;
    padding: .3rem .8rem !important;
    transition: all .2s ease !important;
}}
.sb-act button:hover {{
    color: var(--er) !important;
    border-color: var(--er) !important;
    background: var(--erbg) !important;
}}

/* ─── ANIMATIONS ─────────────────────────────────────────────────────────── */
@keyframes fadeIn   {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
@keyframes fadeInUp {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
@keyframes slideUp  {{ from {{ opacity: 0; transform: translateY(20px); }} to {{ opacity: 1; transform: translateY(0); }} }}
@keyframes slideDown{{ from {{ opacity: 0; transform: translateY(-10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
</style>
"""
