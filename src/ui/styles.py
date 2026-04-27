# src/ui/styles.py
"""
Editorial light UI — National Geographic meets Capture One.
Warm cream, deep forest green accents, elegant serif typography.
All CSS injected once at app startup.
"""

EDITORIAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

/* ── Reset & Base ─────────────────────────────────────────── */
:root {
    --cream:      #FAF8F3;
    --warm-white: #FFFFFF;
    --paper:      #F5F2EA;
    --ink:        #1A1610;
    --ink-mid:    #5C5040;
    --ink-light:  #9A8870;
    --ink-muted:  #C8BEA8;
    --rule:       #E8E2D4;

    --forest:     #2D5016;
    --forest-l:   #3D6B20;
    --sage:       #7A9E6A;
    --sage-l:     #EEF5E8;

    --amber:      #C87020;
    --amber-l:    #FCF0E0;
    --amber-d:    #8A4C10;

    --rust:       #A83020;
    --rust-l:     #FDF0EE;

    --sky:        #2060A0;
    --sky-l:      #EEF4FC;

    --gold:       #B89040;
    --gold-l:     #FBF6E8;

    --shadow-sm:  0 1px 3px rgba(26,22,16,0.08);
    --shadow-md:  0 4px 16px rgba(26,22,16,0.10);
    --shadow-lg:  0 8px 32px rgba(26,22,16,0.12);

    --radius:     6px;
    --radius-lg:  12px;
}

/* ── App Shell ────────────────────────────────────────────── */
.stApp {
    background-color: var(--cream) !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* Remove default Streamlit padding */
.block-container {
    padding-top: 0 !important;
    max-width: 1280px !important;
}

/* ── Typography ───────────────────────────────────────────── */
h1 {
    font-family: 'Cormorant Garamond', serif !important;
    font-size: 42px !important;
    font-weight: 700 !important;
    color: var(--ink) !important;
    letter-spacing: -0.02em !important;
    line-height: 1.1 !important;
}
h2 {
    font-family: 'Cormorant Garamond', serif !important;
    font-size: 26px !important;
    font-weight: 600 !important;
    color: var(--ink) !important;
}
h3 {
    font-family: 'DM Mono', monospace !important;
    font-size: 10px !important;
    font-weight: 500 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: var(--ink-light) !important;
}
p, .stMarkdown {
    font-family: 'DM Sans', sans-serif !important;
    color: var(--ink-mid) !important;
    font-size: 13px !important;
    line-height: 1.75 !important;
}

/* ── Header Bar ───────────────────────────────────────────── */
.app-header {
    background: var(--warm-white);
    border-bottom: 1px solid var(--rule);
    padding: 0 40px;
    position: sticky;
    top: 0;
    z-index: 100;
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 64px;
    box-shadow: var(--shadow-sm);
}
.app-logo {
    font-family: 'Cormorant Garamond', serif;
    font-size: 22px;
    font-weight: 700;
    color: var(--ink);
    letter-spacing: -0.01em;
}
.app-logo span {
    color: var(--forest);
}

/* ── Cards ────────────────────────────────────────────────── */
.editorial-card {
    background: var(--warm-white);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    padding: 24px;
    box-shadow: var(--shadow-sm);
    transition: box-shadow 0.2s;
}
.editorial-card:hover {
    box-shadow: var(--shadow-md);
}
.editorial-card-accent-forest {
    border-top: 3px solid var(--forest);
}
.editorial-card-accent-amber {
    border-top: 3px solid var(--amber);
}
.editorial-card-accent-rust {
    border-top: 3px solid var(--rust);
}

/* ── Photo Thumbnail Cards ────────────────────────────────── */
.photo-card {
    position: relative;
    border-radius: var(--radius);
    overflow: hidden;
    background: var(--warm-white);
    box-shadow: var(--shadow-sm);
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
}
.photo-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
}
.photo-card img {
    width: 100%;
    display: block;
    aspect-ratio: 3/2;
    object-fit: cover;
}
.photo-score-badge {
    position: absolute;
    top: 8px;
    right: 8px;
    background: rgba(255,255,255,0.92);
    backdrop-filter: blur(8px);
    border-radius: 20px;
    padding: 3px 10px;
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    font-weight: 500;
    color: var(--ink);
    box-shadow: var(--shadow-sm);
}
.photo-tier-strip {
    height: 3px;
    width: 100%;
}
.tier-great  { background: var(--forest); }
.tier-good   { background: var(--amber); }
.tier-review { background: var(--sky); }
.tier-delete { background: var(--rule); }

.photo-meta {
    padding: 8px 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.photo-filename {
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    color: var(--ink-light);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 120px;
}

/* ── Tier Badges ──────────────────────────────────────────── */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-family: 'DM Mono', monospace;
    font-size: 9px;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.badge-great  { background: var(--sage-l);  color: var(--forest); border: 1px solid var(--sage); }
.badge-good   { background: var(--amber-l); color: var(--amber-d); border: 1px solid #E8B870; }
.badge-review { background: var(--sky-l);   color: var(--sky); border: 1px solid #90B8E0; }
.badge-delete { background: var(--rust-l);  color: var(--rust); border: 1px solid #D89080; }

/* ── Score Bar ────────────────────────────────────────────── */
.score-bar-container {
    margin-bottom: 10px;
}
.score-bar-label {
    display: flex;
    justify-content: space-between;
    margin-bottom: 3px;
    font-family: 'DM Sans', sans-serif;
    font-size: 12px;
    color: var(--ink-mid);
}
.score-bar-track {
    height: 6px;
    background: var(--paper);
    border-radius: 3px;
    overflow: hidden;
    border: 1px solid var(--rule);
}
.score-bar-fill-forest { background: var(--forest); }
.score-bar-fill-amber  { background: var(--amber); }
.score-bar-fill-rust   { background: var(--rust); }
.score-bar-fill-sky    { background: var(--sky); }

/* ── Stat Cards ───────────────────────────────────────────── */
.stat-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1px;
    background: var(--rule);
    border-radius: var(--radius);
    overflow: hidden;
    margin-bottom: 28px;
}
.stat-cell {
    background: var(--warm-white);
    padding: 20px 16px;
    text-align: center;
}
.stat-value {
    font-family: 'Cormorant Garamond', serif;
    font-size: 36px;
    font-weight: 700;
    line-height: 1;
    margin-bottom: 4px;
}
.stat-label {
    font-family: 'DM Mono', monospace;
    font-size: 9px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--ink-light);
}

/* ── Streamlit overrides ──────────────────────────────────── */
.stButton > button {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    border-radius: var(--radius) !important;
    transition: all 0.2s !important;
}
.stButton > button[kind="primary"] {
    background: var(--forest) !important;
    border: none !important;
    color: white !important;
    padding: 10px 24px !important;
}
.stButton > button[kind="primary"]:hover {
    background: var(--forest-l) !important;
    box-shadow: var(--shadow-md) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    background: var(--warm-white) !important;
    border: 1px solid var(--rule) !important;
    color: var(--ink) !important;
}
.stSelectbox > div > div {
    border-color: var(--rule) !important;
    border-radius: var(--radius) !important;
}
.stProgress > div > div > div {
    background: var(--forest) !important;
}
div[data-testid="stMetric"] {
    background: var(--warm-white);
    border: 1px solid var(--rule);
    border-radius: var(--radius);
    padding: 16px;
}
div[data-testid="stMetricValue"] {
    font-family: 'Cormorant Garamond', serif !important;
    font-size: 28px !important;
    color: var(--ink) !important;
}

/* ── Sidebar ──────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: var(--warm-white) !important;
    border-right: 1px solid var(--rule) !important;
}
section[data-testid="stSidebar"] .stMarkdown {
    color: var(--ink-mid) !important;
}

/* ── Divider ──────────────────────────────────────────────── */
hr {
    border-color: var(--rule) !important;
    margin: 24px 0 !important;
}

/* ── Expander ─────────────────────────────────────────────── */
.streamlit-expanderHeader {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 13px !important;
    color: var(--ink-mid) !important;
    background: var(--paper) !important;
    border-radius: var(--radius) !important;
}
</style>
"""


def inject_styles():
    """Call this once at the top of app.py."""
    import streamlit as st
    st.markdown(EDITORIAL_CSS, unsafe_allow_html=True)


def html_header():
    """Render the app header."""
    return """
    <div class="app-header">
        <div class="app-logo">AI Picture Picker <span>🦁</span></div>
        <div style="font-family:'DM Mono',monospace;font-size:10px;
                    color:#9A8870;letter-spacing:0.08em;">
            WILDLIFE PHOTO INTELLIGENCE ENGINE · BETA
        </div>
    </div>
    """


def tier_badge(tier: str) -> str:
    return f'<span class="badge badge-{tier}">{tier}</span>'


def score_bar(label: str, value: float,
              max_val: float = 100,
              color: str = "forest") -> str:
    pct = min(100, (value / max_val) * 100)
    return f"""
    <div class="score-bar-container">
        <div class="score-bar-label">
            <span>{label}</span>
            <span style="font-family:'DM Mono',monospace;
                         font-size:11px;">{value:.1f}</span>
        </div>
        <div class="score-bar-track">
            <div class="score-bar-fill-{color}"
                 style="width:{pct}%;height:100%;
                        border-radius:3px;"></div>
        </div>
    </div>"""


def stat_card(value: str, label: str,
              color: str = "#1A1610") -> str:
    return f"""
    <div class="stat-cell">
        <div class="stat-value" style="color:{color};">{value}</div>
        <div class="stat-label">{label}</div>
    </div>"""