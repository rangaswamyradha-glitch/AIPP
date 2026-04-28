# app.py — AI Picture Picker · Beta v1
import os
import uuid
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
# ══════════════════════════════════════════════════════════════════════════
# GLOBAL CONSTANTS
# ══════════════════════════════════════════════════════════════════════════
# Industry benchmarks (used by both Dashboard and Analytics)
INDUSTRY_BENCHMARKS = {
    "close_up_portrait":     {"avg": 68},
    "habitat_environmental": {"avg": 62},
    "action_flight":         {"avg": 58},
    "behaviour_interaction": {"avg": 65},
    "high_key":              {"avg": 60},
    "low_key_dramatic":      {"avg": 61},
    "abstract_detail":       {"avg": 63},
    "vertical_portrait":     {"avg": 66},
}

# Dimension config for Analytics
DIM_CONFIG = {
    "Eyes / Focus": {
        "color": "#2D5016",
        "note": "✓ Your strongest dimension",
        "note_color": "#2D5016",
    },
    "Subject Separation": {
        "color": "#C87020",
        "note": "Average — grass backgrounds reduce subject pop",
        "note_color": "#9A8870",
    },
    "Sharpness (local)": {
        "color": "#C87020",
        "note": "Average — ISO noise softens micro-detail in fur",
        "note_color": "#9A8870",
    },
    "Moment / Story": {
        "color": "#2060A0",
        "note": "Below benchmark — mostly walking shots, fewer decisive moments",
        "note_color": "#9A8870",
    },
    "Body Complete": {
        "color": "#2060A0",
        "note": "Below benchmark — tight closeups crop body; habitat shots too distant",
        "note_color": "#9A8870",
    },
    "Exposure": {
        "color": "#A83020",
        "note": "⚠ Weakest — muddy midtones at high ISO in dusk light",
        "note_color": "#A83020",
    },
}
# ── Environment ────────────────────────────────────────────────────────────
load_dotenv()
try:
    if "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass  # secrets.toml not found — will use .env instead

if not os.getenv("ANTHROPIC_API_KEY"):
    st.error("⛔ ANTHROPIC_API_KEY not found. Check your .env file.")
    st.stop()

# ── Page config — must be first Streamlit call ─────────────────────────────
st.set_page_config(
    page_title="AI Picture Picker",
    page_icon="🦁",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Local imports ──────────────────────────────────────────────────────────
from src.database import init_db, get_session, Trip, Photo
from src.services.ingestor import ingest_folder, discover_files
from src.services.scorer import (
    batch_score, CATEGORY_LABELS, assign_tier
)
from src.ui.styles import (
    inject_styles, html_header, tier_badge,
    score_bar, stat_card
)

# ── Init ───────────────────────────────────────────────────────────────────
init_db()
inject_styles()

# ── CSS variables shorthand ────────────────────────────────────────────────
FOREST = "#2D5016"
AMBER  = "#C87020"
RUST   = "#A83020"
SKY    = "#2060A0"
SAGE   = "#7A9E6A"
INK    = "#1A1610"

# ── Helper: load thumbnail as base64 for display ───────────────────────────
def thumb_src(path: str) -> str:
    import base64
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return f"data:image/jpeg;base64,{data}"
    except Exception:
        return ""

# ══════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════
st.markdown(html_header(), unsafe_allow_html=True)
st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# SIDEBAR — Navigation
# ══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style='padding:16px 0 8px;
                font-family:"Cormorant Garamond",serif;
                font-size:20px;font-weight:700;
                color:#1A1610;'>
        🦁 AI Picture Picker
    </div>
    <div style='font-family:"DM Mono",monospace;font-size:9px;
                letter-spacing:0.1em;text-transform:uppercase;
                color:#9A8870;margin-bottom:20px;'>
        Wildlife Photo Intelligence
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigate",
        ["🏠  Dashboard", "📁  New Trip",
         "🖼  Gallery", "📊  Analytics",
         "⭐  Rate Photos", "📝  Story Studio"],
        label_visibility="collapsed"
    )

    st.divider()

    # Trip selector
    session = get_session()
    trips = session.query(Trip).order_by(
        Trip.created_at.desc()
    ).all()
    session.close()

    if trips:
        trip_names  = [f"{t.name} ({t.photo_count} photos)"
                       for t in trips]
        trip_choice = st.selectbox("Active Trip", trip_names)
        active_trip = trips[
            trip_names.index(trip_choice)
        ] if trip_choice else None
    else:
        active_trip = None
        st.info("No trips yet — create your first trip!")

page = page.split("  ")[-1]

# ══════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════
if page == "Dashboard":
    if not active_trip:
        st.markdown("""
        <div style='background:#FFFFFF;border:1px solid #E8E2D4;
                    border-radius:12px;padding:60px;text-align:center;
                    margin-top:24px;'>
            <div style='font-family:"Cormorant Garamond",serif;
                        font-size:32px;color:#1A1610;margin-bottom:8px;'>
                Welcome to AI Picture Picker 🦁
            </div>
            <div style='font-family:"DM Sans",sans-serif;font-size:14px;
                        color:#9A8870;'>
                Start by creating your first trip →
                click <strong>New Trip</strong> in the sidebar
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    # ═══ STEP 1: Load trip data FIRST ═══════════════════════════════════
    session = get_session()
    photos = session.query(Photo).filter(Photo.trip_id == active_trip.id).all()
    session.close()

    # ═══ STEP 2: Calculate all variables ════════════════════════════════
    total = len(photos)
    greats = sum(1 for p in photos if p.tier == "great")
    goods = sum(1 for p in photos if p.tier == "good")
    reviews = sum(1 for p in photos if p.tier == "review")
    deletes = sum(1 for p in photos if p.tier == "delete")
    pending = sum(1 for p in photos if p.tier == "pending")

    scored = [p for p in photos if p.composite_score and p.composite_score > 0]
    avg_score = sum(p.composite_score for p in scored) / len(scored) if scored else 0
    keep_rate = (greats + goods) / total * 100 if total > 0 else 0
    bench_keep = 35

    # Category breakdown
    cat_data = {}
    for p in photos:
        if not p.category:
            continue
        label = CATEGORY_LABELS.get(p.category, p.category)
        cat_data.setdefault(label, {"total": 0, "scores": [], "key": p.category})
        cat_data[label]["total"] += 1
        if p.composite_score:
            cat_data[label]["scores"].append(p.composite_score)

    best_photo = max(scored, key=lambda p: p.composite_score) if scored else None
    best_score = best_photo.composite_score if best_photo else 0

    # ═══ STEP 3: NOW render page with all variables available ═══════════
    st.markdown("""
    <h1 style='font-family:"Cormorant Garamond",serif;font-size:36px;
               font-weight:700;color:#1A1610;letter-spacing:-0.02em;
               margin-bottom:2px;'>
        Your Photo Intelligence Dashboard
    </h1>""", unsafe_allow_html=True)

    # Subtitle with trip info
    st.markdown(f"""
    <div style='font-family:"DM Mono",monospace;font-size:9px;
                letter-spacing:0.12em;text-transform:uppercase;
                color:#9A8870;margin-bottom:4px;'>
        {active_trip.name} · {active_trip.created_at.strftime('%B %Y')} · Nikon Z9 · {total} frames
    </div>
    <div style='font-family:"DM Mono",monospace;font-size:9px;
                color:#C8BEA8;margin-bottom:20px;'>
        ● Processed 25 Apr 2026
    </div>
    """, unsafe_allow_html=True)

    # ── ROW 1: Stat Strip ──────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    for col, val, label, note, color in [
        (c1, str(total), "Total Photos", "Nikon NEF · RAW files", "#1A1610"),
        (c2, str(greats + goods), "Good — Keepers", f"{keep_rate:.0f}% keep rate this trip", "#C87020"),
        (c3, str(reviews), "Need Your Review", "Borderline — your call", "#2060A0"),
        (c4, f"{avg_score:.1f}", "Session Average Score", "Out of 100", "#2D5016"),
    ]:
        with col:
            st.markdown(f"""
            <div style='background:#FFFFFF;border:1px solid #E8E2D4;
                        border-top:2px solid {color};border-radius:8px;
                        padding:18px 20px;'>
                <div style='font-family:"DM Mono",monospace;font-size:8px;
                            letter-spacing:0.12em;text-transform:uppercase;
                            color:#9A8870;margin-bottom:4px;'>{label}</div>
                <div style='font-family:"Cormorant Garamond",serif;
                            font-size:42px;font-weight:700;line-height:1;
                            color:{color};'>{val}</div>
                <div style='font-size:11px;color:#C8BEA8;margin-top:2px;'>{note}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # ── ROW 2: AI Session Summary ──────────────────────────────────────
    best_name = best_photo.filename.replace(".NEF", "").replace(".nef", "") if best_photo else "—"

    cat_summary = ""
    if len(cat_data) >= 2:
        sorted_cats = sorted(
            cat_data.items(),
            key=lambda x: sum(x[1]["scores"]) / len(x[1]["scores"]) if x[1]["scores"] else 0,
            reverse=True
        )
        best_cat_name = sorted_cats[0][0]
        best_cat_avg = round(sum(sorted_cats[0][1]["scores"]) / len(sorted_cats[0][1]["scores"]), 1) if sorted_cats[0][1]["scores"] else 0
        worst_cat_name = sorted_cats[-1][0]
        worst_cat_avg = round(sum(sorted_cats[-1][1]["scores"]) / len(sorted_cats[-1][1]["scores"]), 1) if sorted_cats[-1][1]["scores"] else 0
        cat_summary = f"Your <strong>{best_cat_name}</strong> averaged {best_cat_avg}, outperforming your <strong>{worst_cat_name}</strong> shots (avg {worst_cat_avg}) by {round(best_cat_avg - worst_cat_avg, 1)} points."

    iso_tip = ""
    if best_photo and best_photo.exif_iso and best_photo.exif_iso > 3200:
        iso_tip = f" Shooting at <strong>ISO 3200 or lower</strong> next time could push 6–8 photos into Great tier."

    summary_text = f"Your <strong>{active_trip.name}</strong> session produced <strong>{greats + goods} keepers</strong> from {total} frames — a {keep_rate:.0f}% keep rate{', typical for high-ISO conditions' if best_photo and best_photo.exif_iso and best_photo.exif_iso > 3200 else ''}. {cat_summary}{iso_tip}"

    st.markdown(f"""
    <div style='background:#FFFFFF;border:1px solid #E8E2D4;
                border-left:4px solid #2D5016;border-radius:6px;
                padding:14px 18px;margin-bottom:20px;
                display:flex;align-items:flex-start;gap:12px;'>
        <div style='font-size:18px;flex-shrink:0;margin-top:1px;'>🧠</div>
        <div style='font-size:12.5px;line-height:1.7;
                    color:#5C5040;font-style:italic;'>
            {summary_text}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── ROW 3: Top 10 Filmstrip + Donut ───────────────────────────────
    st.markdown(
        "<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
        "letter-spacing:0.14em;text-transform:uppercase;color:#C8BEA8;"
        "margin-bottom:10px;'>Top Shots from This Trip</div>",
        unsafe_allow_html=True
    )

    col_film, col_donut = st.columns([3, 1.2])

    with col_film:
        top_photos = sorted(
            [p for p in photos if p.thumbnail_path and os.path.exists(p.thumbnail_path or "") and p.tier in ["great", "good"]],
            key=lambda x: x.composite_score or 0,
            reverse=True
        )[:10]

        if top_photos:
            tier_colors = {"great": "#2D5016", "good": "#C87020", "review": "#2060A0", "delete": "#C8BEA8"}
            row1 = top_photos[:5]
            row2 = top_photos[5:10]

            def make_frame(photo):
                src = thumb_src(photo.thumbnail_path)
                score = photo.composite_score or 0
                t_color = tier_colors.get(photo.tier, "#C8BEA8")
                fname = photo.filename[:8]
                return (
                    f"<div style='flex:1;position:relative;border-radius:6px;"
                    f"overflow:hidden;border:1px solid #E8E2D4;aspect-ratio:3/2;'>"
                    f"<img src='{src}' style='width:100%;height:100%;object-fit:cover;display:block;'>"
                    f"<div style='position:absolute;top:6px;right:6px;"
                    f"background:rgba(255,255,255,0.93);backdrop-filter:blur(6px);"
                    f"border-radius:20px;padding:2px 8px;font-family:\"DM Mono\",monospace;"
                    f"font-size:11px;font-weight:500;color:{t_color};'>{score:.0f}</div>"
                    f"<div style='position:absolute;bottom:0;left:0;right:0;height:3px;"
                    f"background:{t_color};'></div>"
                    f"<div style='position:absolute;bottom:6px;left:6px;"
                    f"font-family:\"DM Mono\",monospace;font-size:9px;"
                    f"color:rgba(255,255,255,0.85);'>{fname}</div></div>"
                )

            row1_html = "".join(make_frame(p) for p in row1)
            row2_html = "".join(make_frame(p) for p in row2) if row2 else ""

            film_html = (
                f"<div style='background:#FFFFFF;border:1px solid #E8E2D4;"
                f"border-radius:8px;padding:18px;'>"
                f"<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
                f"letter-spacing:0.12em;text-transform:uppercase;"
                f"color:#9A8870;margin-bottom:12px;'>Top {len(top_photos)} · Sorted by Score</div>"
                f"<div style='display:flex;gap:8px;margin-bottom:8px;'>{row1_html}</div>"
            )
            if row2_html:
                film_html += f"<div style='display:flex;gap:8px;margin-bottom:8px;'>{row2_html}</div>"
            film_html += (
                f"<div style='margin-top:8px;font-size:11px;color:#C8BEA8;"
                f"font-style:italic;'>Colour bar = tier · Score badge top right</div></div>"
            )
            st.markdown(film_html, unsafe_allow_html=True)
        else:
            st.markdown(
                "<div style='background:#FFFFFF;border:1px solid #E8E2D4;"
                "border-radius:8px;padding:40px;text-align:center;"
                "color:#9A8870;font-size:13px;'>"
                "No scored photos yet — run AI Scoring in the Gallery first</div>",
                unsafe_allow_html=True
            )

    with col_donut:
        # IMPORTANT: Do NOT try to wrap Plotly chart in HTML div.
        # Use separate label + chart + legend approach.

        # Title
        st.markdown(
            "<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
            "letter-spacing:0.12em;text-transform:uppercase;"
            "color:#9A8870;margin-bottom:4px;'>Tier Distribution</div>",
            unsafe_allow_html=True
        )

        # Donut chart
        fig = go.Figure(data=[go.Pie(
            labels=['Great', 'Good', 'Review', 'Delete'],
            values=[greats, goods, reviews, deletes],
            hole=0.6,
            marker=dict(colors=['#2D5016', '#C87020', '#7AACCC', '#C8BEA8']),
            textposition='inside',
            textinfo='value',
            textfont=dict(size=12, color='white', family='DM Mono'),
        )])
        fig.update_layout(
            annotations=[dict(
                text=f'<b>{greats + goods}</b><br><span style="font-size:10px">Keepers</span>',
                x=0.5, y=0.5,
                font=dict(size=24, family='Cormorant Garamond', color='#C87020'),
                showarrow=False
            )],
            showlegend=True,
            legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5,
                        font=dict(size=10, family='DM Mono')),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=10, r=10, t=10, b=10),
            height=280,
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── ROW 4: 3 Health Cards ──────────────────────────────────────────
    st.markdown(
        "<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
        "letter-spacing:0.14em;text-transform:uppercase;color:#C8BEA8;"
        "margin-bottom:10px;'>Session Health</div>",
        unsafe_allow_html=True
    )

    h1, h2, h3 = st.columns(3)

    with h1:
        bar_color = "#2D5016" if keep_rate >= bench_keep else "#C87020"
        bench_note = "✓ Above average keep rate" if keep_rate >= bench_keep else "Typical for challenging light conditions"
        st.markdown(f"""
        <div style='background:#FFFFFF;border:1px solid #E8E2D4;
                    border-radius:8px;padding:18px;
                    display:flex;flex-direction:column;gap:8px;height:100%;'>
            <div style='display:flex;align-items:center;gap:8px;'>
                <span style='font-size:18px;'>📈</span>
                <span style='font-family:"DM Mono",monospace;font-size:8px;
                             letter-spacing:0.12em;text-transform:uppercase;
                             color:#9A8870;'>Keep Rate</span>
            </div>
            <div style='font-family:"Cormorant Garamond",serif;
                        font-size:30px;font-weight:700;
                        color:{bar_color};line-height:1;'>
                {keep_rate:.0f}%
            </div>
            <div style='height:6px;background:#F5F2EA;border-radius:3px;
                        border:1px solid #E8E2D4;overflow:hidden;'>
                <div style='width:{min(keep_rate,100):.0f}%;height:100%;
                            background:{bar_color};border-radius:3px;'></div>
            </div>
            <div style='display:flex;justify-content:space-between;
                        font-family:"DM Mono",monospace;font-size:9px;
                        color:#C8BEA8;'>
                <span>Your rate</span>
                <span>Benchmark {bench_keep}%</span>
            </div>
            <div style='font-size:11.5px;color:#9A8870;line-height:1.5;'>
                {bench_note}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with h2:
        top_cat_label = max(cat_data, key=lambda k: cat_data[k]["total"]) if cat_data else "—"
        sorted_cats = sorted(cat_data.items(), key=lambda x: x[1]["total"], reverse=True)
        
        # Build detail lines like mockup
        detail_lines = ""
        for lbl, data in sorted_cats:
            avg = round(sum(data["scores"]) / len(data["scores"]), 1) if data["scores"] else 0
            detail_lines += (
                f"<div style='font-size:12px;color:#5C5040;line-height:1.6;'>"
                f"{data['total']} {lbl}s · Average score {avg}</div>"
            )

        # Build proportional bar
        bar_segments = ""
        bar_labels = ""
        for i, (lbl, data) in enumerate(sorted_cats):
            color = "#7AACCC" if i == 0 else "#C87020"
            bar_segments += (
                f"<div style='height:6px;flex:{data['total']};"
                f"background:{color};border-radius:3px;opacity:0.7;'></div>"
            )
            align = "left" if i == 0 else "right"
            bar_labels += (
                f"<span style='text-align:{align};'>"
                f"{lbl[:12]} ({data['total']})</span>"
            )

        st.markdown(
            f"<div style='background:#FFFFFF;border:1px solid #E8E2D4;"
            f"border-radius:8px;padding:18px;"
            f"display:flex;flex-direction:column;gap:8px;height:100%;'>"
            f"<div style='display:flex;align-items:center;gap:8px;'>"
            f"<span style='font-size:18px;'>🏷️</span>"
            f"<span style='font-family:\"DM Mono\",monospace;font-size:8px;"
            f"letter-spacing:0.12em;text-transform:uppercase;"
            f"color:#9A8870;'>Top Category by Volume</span></div>"
            f"<div style='font-family:\"Cormorant Garamond\",serif;"
            f"font-size:22px;font-weight:700;color:#2060A0;"
            f"line-height:1.2;'>{top_cat_label}</div>"
            f"{detail_lines}"
            f"<div style='display:flex;gap:8px;align-items:center;"
            f"margin-top:4px;'>{bar_segments}</div>"
            f"<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
            f"color:#C8BEA8;display:flex;justify-content:space-between;"
            f"margin-top:2px;'>{bar_labels}</div></div>",
            unsafe_allow_html=True
        )

    with h3:
        if best_photo and best_photo.exif_iso and best_photo.exif_iso > 3200:
            tip_title = f"ISO {best_photo.exif_iso:,} → 3200"
            tip_body = f"Your compositions are already strong. Reducing ISO from {best_photo.exif_iso:,} → 3200 would push 6–8 photos into <strong>Great tier</strong> on your next session."
        elif keep_rate < bench_keep:
            tip_title = "Get Closer"
            tip_body = f"Your keep rate is {keep_rate:.0f}% vs the {bench_keep}% benchmark. Moving 10–20m closer to your subject typically adds 8–12 points to each frame."
        else:
            tip_title = "Wait for the Look"
            tip_body = "Your technical scores are strong. The next level is the decisive moment — wait for direct eye contact or peak action to push scores into <strong>Great tier</strong>."

        st.markdown(f"""
        <div style='background:#EEF5E8;border:1px solid #7A9E6A;
                    border-radius:8px;padding:18px;
                    display:flex;flex-direction:column;gap:8px;height:100%;'>
            <div style='display:flex;align-items:center;gap:8px;'>
                <span style='font-size:18px;'>💡</span>
                <span style='font-family:"DM Mono",monospace;font-size:8px;
                             letter-spacing:0.12em;text-transform:uppercase;
                             color:#2D5016;'>Next Trip Tip</span>
            </div>
            <div style='font-family:"Cormorant Garamond",serif;
                        font-size:18px;font-weight:700;
                        color:#2D5016;line-height:1.2;'>
                {tip_title}
            </div>
            <div style='font-size:12px;color:#2D5016;opacity:0.85;line-height:1.6;'>
                {tip_body}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── ROW 5: Quick Export ───────────────────────────────────────────
    st.markdown(
        "<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
        "letter-spacing:0.14em;text-transform:uppercase;color:#C8BEA8;"
        "margin-bottom:10px;margin-top:12px;'>Quick Export</div>",
        unsafe_allow_html=True
    )

    keeper_count = greats + goods
    keep_photos = [p for p in photos if p.tier in ["great", "good"]]
    export_rows = [{
        "Filename": p.filename, "Tier": p.tier, "Score": p.composite_score,
        "Category": CATEGORY_LABELS.get(p.category, ""),
        "ISO": p.exif_iso, "Aperture": p.exif_aperture,
        "Shutter": p.exif_shutter, "Focal Length": p.exif_focal_len,
        "LR Edit Notes": (p.edit_suggestions or {}).get("lightroom", ""),
        "Topaz Notes": (p.edit_suggestions or {}).get("topaz", ""),
    } for p in keep_photos]
    csv_data = pd.DataFrame(export_rows).to_csv(index=False)

    best_fname = best_photo.filename.replace(".NEF","").replace(".nef","") if best_photo else "—"

    # Export card with text on left, button on right
    col_exp_text, col_exp_btn = st.columns([3, 1])

    with col_exp_text:
        st.markdown(
            f"<div style='background:#FFFFFF;border:1px solid #E8E2D4;"
            f"border-radius:8px;padding:24px;height:100%;'>"
            f"<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
            f"letter-spacing:0.12em;text-transform:uppercase;"
            f"color:#9A8870;margin-bottom:8px;'>Quick Export</div>"
            f"<div style='font-family:\"Cormorant Garamond\",serif;"
            f"font-size:28px;font-weight:700;color:#2D5016;"
            f"margin-bottom:8px;'>{keeper_count} photos</div>"
            f"<div style='font-size:12px;color:#5C5040;line-height:1.5;'>"
            f"Good-tier keepers ready to export to Lightroom or Capture One. "
            f"Includes AI score, edit notes, and category per photo.</div></div>",
            unsafe_allow_html=True
        )

    with col_exp_btn:
        st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
        st.download_button(
            "⬇️  Export to Lightroom CSV",
            csv_data,
            f"picker_{active_trip.name.replace(' ','_')}_keepers.csv",
            "text/csv",
            use_container_width=True,
        )
        st.markdown(
            "<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
            "color:#C8BEA8;text-align:center;margin-top:6px;'>"
            "XMP · CSV · Capture One compatible</div>",
            unsafe_allow_html=True
        )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Editing Priority card
    st.markdown(
        f"<div style='background:#EEF5E8;border:1px solid #7A9E6A;"
        f"border-radius:6px;padding:16px;'>"
        f"<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
        f"letter-spacing:0.1em;text-transform:uppercase;"
        f"color:#2D5016;margin-bottom:8px;'>💡 Editing Priority</div>"
        f"<div style='font-size:12.5px;color:#2D5016;line-height:1.7;'>"
        f"Start with <strong>{best_fname}</strong> — your highest scorer at {best_score:.0f}.<br>"
        f"<strong>DeNoise AI (Low Light preset)</strong> — ISO 16000 detected; "
        f"use Auto settings then manually reduce Color Noise slider to 60, then "
        f"<strong>Exposure +0.8, Shadows +25, Highlights -15, Whites +10, Blacks +5, "
        f"Clarity +20, Vibrance +15, Noise Reduction Luminance 45, Color Noise 30, "
        f"Sharpening Amount 40 Radius 1.2</strong></div></div>",
        unsafe_allow_html=True
    )
# ══════════════════════════════════════════════════════════════════════════
# PAGE: NEW TRIP
# ══════════════════════════════════════════════════════════════════════════
elif page == "New Trip":
    st.markdown("<h1>Start a New Trip</h1>", unsafe_allow_html=True)

    st.markdown("""
    <div style='background:#FFFFFF;border:1px solid #E8E2D4;
                border-radius:8px;padding:28px;
                max-width:700px;margin-bottom:24px;'>
        <div style='font-family:"DM Mono",monospace;font-size:9px;
                    letter-spacing:0.12em;text-transform:uppercase;
                    color:#9A8870;margin-bottom:16px;'>
            Step 1 — Trip Details
        </div>
    """, unsafe_allow_html=True)

    trip_name = st.text_input(
        "Trip Name",
        placeholder="e.g. Corbett April 2026, Masai Mara Safari"
    )
    trip_location = st.text_input(
        "Location (optional)",
        placeholder="e.g. Rajasthan, India"
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Step 2: Upload Method ─────────────────────────────────────────
    st.markdown("""
    <div style='background:#FFFFFF;border:1px solid #E8E2D4;
                border-radius:8px;padding:28px;
                max-width:700px;margin-bottom:24px;'>
        <div style='font-family:"DM Mono",monospace;font-size:9px;
                    letter-spacing:0.12em;text-transform:uppercase;
                    color:#9A8870;margin-bottom:16px;'>
            Step 2 — Choose Upload Method
        </div>
    """, unsafe_allow_html=True)

    upload_method = st.radio(
        "Upload Method",
        ["📁 Folder Path (Local Only)", "📤 Upload Files (Cloud & Local)"],
        label_visibility="collapsed",
        horizontal=True
    )

    folder_path = None
    uploaded_files = None

    if "Folder Path" in upload_method:
        # ── Option 1: Folder Path (Local Deployment) ──────────────────
        st.markdown("""
        <div style='background:#FFF4E6;border:1px solid #C87020;
                    border-radius:6px;padding:12px;margin:16px 0;'>
            <div style='font-family:"DM Mono",monospace;font-size:10px;
                        color:#C87020;font-weight:500;'>
                ⚠️ Local Deployment Only
            </div>
            <div style='font-size:11px;color:#5C5040;margin-top:6px;
                        line-height:1.5;'>
                Folder paths only work when running AIPP on your own computer.
                For Streamlit Cloud, use 'Upload Files' instead.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        folder_path = st.text_input(
            "Photo Folder Path",
            placeholder=r"e.g. C:\Photos\Corbett2026  or  /Volumes/SD_CARD/DCIM"
        )

        # Preview folder
        if folder_path and os.path.isdir(folder_path):
            from src.services.ingestor import discover_files
            files = discover_files(folder_path)
            st.markdown(f"""
            <div style='background:#EEF5E8;border:1px solid {SAGE};
                        border-radius:6px;padding:14px 18px;
                        margin:16px 0;'>
                <span style='font-family:"DM Mono",monospace;
                             font-size:10px;color:{FOREST};font-weight:500;'>
                    ✓ Found {len(files)} photos in this folder
                </span>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("""
            <style>
            button[data-testid="baseButton-primary"] {
                background-color: #2D5016 !important;
                color: #FFFFFF !important;
                font-weight: 600 !important;
            }
            button[data-testid="baseButton-primary"] * {
                color: #FFFFFF !important;
            }
            </style>
            """, unsafe_allow_html=True)

            if st.button(
                f"🚀  Begin Processing {len(uploaded_files)} Photos",
                type="primary",
                key="process_upload_btn"
            ):
                if not trip_name or trip_name.strip() == "":
                    st.error("❌ Trip name is required. Please enter a trip name above.")
                    st.stop()

                # Create trip
                trip_id = str(uuid.uuid4())
                session = get_session()
                trip = Trip(
                    id=trip_id,
                    name=trip_name,
                    location=trip_location,
                    folder_path=None,
                    photo_count=len(uploaded_files),
                    created_at=datetime.now(),
                )
                session.add(trip)
                session.commit()
                session.close()

                # Create uploads directory
                uploads_dir = Path(os.getcwd()) / "uploads" / trip_id
                uploads_dir.mkdir(parents=True, exist_ok=True)

                # Process uploaded files
                st.markdown(
                    "<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
                    "letter-spacing:0.14em;text-transform:uppercase;color:#C8BEA8;"
                    "margin-top:16px;margin-bottom:10px;'>"
                    "Phase 1 — Processing Uploaded Photos</div>",
                    unsafe_allow_html=True
                )
                prog_bar = st.progress(0)
                status = st.empty()

                ingested = 0
                skipped = 0
                errors = []

                for idx, uploaded_file in enumerate(uploaded_files):
                    pct = (idx + 1) / len(uploaded_files)
                    prog_bar.progress(pct)
                    status.markdown(
                        f"<div style='font-family:\"DM Mono\",monospace;"
                        f"font-size:11px;color:#9A8870;'>"
                        f"Processing {idx + 1:,} / {len(uploaded_files):,} — "
                        f"{uploaded_file.name}</div>",
                        unsafe_allow_html=True
                    )

                    # Save file to uploads directory
                    file_path = uploads_dir / uploaded_file.name
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    # Ingest the file
                    from src.services.ingestor import ingest_single_file
                    try:
                        result = ingest_single_file(trip_id, str(file_path))
                        if result["success"] and not result["skipped"]:
                            ingested += 1
                        elif result["skipped"]:
                            skipped += 1
                            if result.get("reason"):
                                errors.append(f"{uploaded_file.name}: {result['reason']}")
                        else:
                            skipped += 1
                            errors.append(f"{uploaded_file.name}: {result.get('reason', 'Unknown error')}")
                    except Exception as e:
                        skipped += 1
                        errors.append(f"{uploaded_file.name}: {str(e)}")

                prog_bar.progress(1.0)
                status.empty()

                # Update trip count
                session = get_session()
                t = session.query(Trip).filter(Trip.id == trip_id).first()
                if t:
                    t.photo_count = ingested
                session.commit()
                session.close()

                # Show results
                if ingested > 0:
                    st.markdown(f"""
                    <div style='background:#EEF5E8;border:1px solid {SAGE};
                                border-radius:8px;padding:20px;margin:16px 0;'>
                        <div style='font-family:"Cormorant Garamond",serif;
                                    font-size:20px;color:{FOREST};margin-bottom:8px;'>
                            ✓ Upload Complete
                        </div>
                        <div style='font-size:13px;color:#5C5040;'>
                            <strong>{ingested:,}</strong> photos ready for AI scoring ·
                            <strong>{skipped:,}</strong> skipped
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    st.info(
                        "✦ Select this trip from **Active Trip** dropdown in the sidebar, "
                        "then go to **Gallery** → click **Run AI Scoring**"
                    )
                else:
                    st.error(
                        f"❌ All {len(uploaded_files)} photos were skipped. "
                        f"See errors below."
                    )

                # Show errors if any
                if errors:
                    with st.expander(f"⚠️ {len(errors)} photos had issues — click to see details"):
                        for err in errors:
                            st.text(err)
        elif folder_path and not os.path.isdir(folder_path):
            st.markdown("</div>", unsafe_allow_html=True)
            st.error("⚠️ Folder not found. Check the path and try again.")
        else:
            st.markdown("</div>", unsafe_allow_html=True)

    else:
        # ── Option 2: File Uploader (Cloud & Local) ───────────────────
        st.markdown("""
        <div style='background:#EEF5E8;border:1px solid #7A9E6A;
                    border-radius:6px;padding:12px;margin:16px 0;'>
            <div style='font-family:"DM Mono",monospace;font-size:10px;
                        color:#2D5016;font-weight:500;'>
                ✅ Recommended for Cloud Deployment
            </div>
            <div style='font-size:11px;color:#2D5016;margin-top:6px;
                        line-height:1.5;'>
                Upload JPG files (2-5MB each). Max 500MB total.
                Select multiple files: Ctrl+Click (Windows) or Cmd+Click (Mac)
            </div>
        </div>
        """, unsafe_allow_html=True)

        uploaded_files = st.file_uploader(
            "Choose photos to upload",
            type=["jpg", "jpeg", "png", "JPG", "JPEG", "PNG"],
            accept_multiple_files=True,
            label_visibility="collapsed"
        )

        if uploaded_files:
            st.markdown(f"""
            <div style='background:#EEF5E8;border:1px solid {SAGE};
                        border-radius:6px;padding:14px 18px;
                        margin:16px 0;'>
                <span style='font-family:"DM Mono",monospace;
                             font-size:10px;color:{FOREST};font-weight:500;'>
                    ✓ {len(uploaded_files)} photos ready to process
                </span>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

            # Validation check
            if not trip_name or trip_name.strip() == "":
                st.warning("⚠️ Please enter a trip name above before processing")
            
            # Button with white text CSS
            st.markdown("""
            <style>
            button[data-testid="baseButton-primary"] {
                background-color: #2D5016 !important;
                color: #FFFFFF !important;
                font-weight: 600 !important;
            }
            button[data-testid="baseButton-primary"]:hover {
                background-color: #3D6B20 !important;
            }
            button[data-testid="baseButton-primary"] p {
                color: #FFFFFF !important;
            }
            button[data-testid="baseButton-primary"] * {
                color: #FFFFFF !important;
            }
            </style>
            """, unsafe_allow_html=True)

            # Button is always visible, but only processes if trip_name exists
            if st.button(
                f"🚀  Begin Processing {len(uploaded_files)} Photos",
                type="primary",
                key="process_upload_btn"
            ):
                if not trip_name or trip_name.strip() == "":
                    st.error("❌ Trip name is required. Please enter a trip name above.")
                    st.stop()
                
                # [REST OF THE PROCESSING CODE STAYS THE SAME]
                # Create trip
                trip_id = str(uuid.uuid4())
                session = get_session()
                trip = Trip(
                    id=trip_id,
                    name=trip_name,
                    location=trip_location,
                    folder_path=None,
                    photo_count=len(uploaded_files),
                    created_at=datetime.now(),
                )
                session.add(trip)
                session.commit()
                session.close()

                # Create uploads directory if it doesn't exist
                uploads_dir = Path(os.getcwd()) / "uploads" / trip_id
                uploads_dir.mkdir(parents=True, exist_ok=True)

                # Save uploaded files and process
                st.markdown(
                    "<h3>Phase 1 — Processing Uploaded Photos</h3>",
                    unsafe_allow_html=True
                )
                prog_bar = st.progress(0)
                status = st.empty()

                ingested = 0
                skipped = 0

                for idx, uploaded_file in enumerate(uploaded_files):
                    # Update progress
                    pct = (idx + 1) / len(uploaded_files)
                    prog_bar.progress(pct)
                    status.markdown(
                        f"<div style='font-family:\"DM Mono\",monospace;"
                        f"font-size:11px;color:#9A8870;'>"
                        f"Processing {idx + 1:,} / {len(uploaded_files):,} photos…"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                    # Save file to uploads directory
                    file_path = uploads_dir / uploaded_file.name
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    # Ingest the file
                    from src.services.ingestor import ingest_single_file
                    try:
                        result = ingest_single_file(trip_id, str(file_path))
                        if result["success"] and not result["skipped"]:
                            ingested += 1
                        else:
                            skipped += 1
                    except Exception as e:
                        skipped += 1
                        st.warning(f"Skipped {uploaded_file.name}: {str(e)}")

                prog_bar.progress(1.0)
                status.empty()

                # Update trip count
                session = get_session()
                t = session.query(Trip).filter(
                    Trip.id == trip_id
                ).first()
                if t:
                    t.photo_count = ingested
                session.commit()
                session.close()

                st.markdown(f"""
                <div style='background:#EEF5E8;border:1px solid {SAGE};
                            border-radius:8px;padding:20px;
                            margin:16px 0;'>
                    <div style='font-family:"Cormorant Garamond",serif;
                                font-size:20px;color:{FOREST};
                                margin-bottom:8px;'>
                        ✓ Upload Complete
                    </div>
                    <div style='font-family:"DM Sans",sans-serif;
                                font-size:13px;color:#5C5040;'>
                        <strong>{ingested:,}</strong> photos ready
                        for AI scoring ·
                        <strong>{skipped:,}</strong> skipped
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.info(
                    "✦ Go to **Gallery** → click **Run AI Scoring** "
                    "to score photos with Claude vision."
                )
        else:
            st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# PAGE: GALLERY
# ══════════════════════════════════════════════════════════════════════════
elif page == "Gallery":
    st.markdown("<h1>Photo Gallery</h1>", unsafe_allow_html=True)

    if not active_trip:
        st.info("Select or create a trip first.")
        st.stop()

    session  = get_session()
    all_photos = session.query(Photo).filter(
        Photo.trip_id == active_trip.id
    ).all()
    session.close()

    pending_count = sum(
        1 for p in all_photos if p.tier == "pending"
    )

    # AI Scoring trigger
    # Count photos that need scoring (pending OR no composite_score)
    needs_scoring = [
        p for p in all_photos 
        if p.tier == "pending" or p.composite_score is None or p.composite_score == 0
    ]
    pending_count = len(needs_scoring)

    if pending_count > 0:
        st.markdown(f"""
        <div style='background:#FCF0E0;border:1px solid #E8B870;
                    border-radius:8px;padding:18px 22px;
                    margin-bottom:20px;'>
            <strong style='color:{AMBER};font-size:16px;'>
                {pending_count:,} photos ready for AI scoring
            </strong><br>
            <span style='color:#8A4C10;font-size:13px;margin-top:6px;display:block;'>
                Estimated cost: ${pending_count * 0.002:.2f} USD · 
                Estimated time: {max(1, pending_count // 40)} minutes
            </span>
        </div>
        """, unsafe_allow_html=True)

        # White text button
        st.markdown("""
        <style>
        button[data-testid="baseButton-primary"] {
            background-color: #2D5016 !important;
            color: #FFFFFF !important;
            font-weight: 600 !important;
        }
        button[data-testid="baseButton-primary"] * {
            color: #FFFFFF !important;
        }
        </style>
        """, unsafe_allow_html=True)

        if st.button(
            f"🧠  Run AI Scoring on {pending_count:,} Photos",
            type="primary",
            key="run_ai_scoring"
        ):
            prog = st.progress(0)
            info = st.empty()

            def score_progress(cur, tot):
                prog.progress(cur / tot)
                info.markdown(
                    f"<div style='font-family:\"DM Mono\",monospace;"
                    f"font-size:11px;color:#9A8870;'>"
                    f"Scoring {cur:,} / {tot:,} with Claude Vision…"
                    f"</div>",
                    unsafe_allow_html=True
                )

            result = batch_score(
                active_trip.id, score_progress
            )
            prog.progress(1.0)
            info.empty()
            st.success(
                f"✓ Scored {result['scored']:,} photos. "
                f"Reloading gallery..."
            )
            st.rerun()
    
    elif len(all_photos) == 0:
        st.info("📸 No photos in this trip yet. Go to **New Trip** to upload photos.")
        st.stop()
    
    else:
        # All photos are already scored
        st.markdown(f"""
        <div style='background:#EEF5E8;border:1px solid #7A9E6A;
                    border-radius:8px;padding:18px 22px;
                    margin-bottom:20px;'>
            <strong style='color:{FOREST};font-size:16px;'>
                ✓ All {len(all_photos):,} photos have been scored
            </strong><br>
            <span style='color:#2D5016;font-size:13px;margin-top:6px;display:block;'>
                Use the filters below to browse your photos
            </span>
        </div>
        """, unsafe_allow_html=True)

    # Filters
    col_f1, col_f2, col_f3 = st.columns([1, 1, 1])
    with col_f1:
        tier_filter = st.multiselect(
            "Tier", ["great", "good", "review", "delete"],
            default=["great", "good", "review"]
        )
    with col_f2:
        cats = list(set(
            p.category for p in all_photos if p.category
        ))
        cat_filter = st.multiselect(
            "Category",
            [CATEGORY_LABELS.get(c, c) for c in cats],
            default=[]
        )
    with col_f3:
        sort_by = st.selectbox(
            "Sort", ["Score (High→Low)", "Score (Low→High)",
                     "Filename", "Date"]
        )

    # Apply filters
    filtered = [p for p in all_photos if p.tier in tier_filter]
    if cat_filter:
        cat_keys = {v: k for k, v in CATEGORY_LABELS.items()}
        selected = [cat_keys.get(c, c) for c in cat_filter]
        filtered = [p for p in filtered
                    if p.category in selected]

    if sort_by == "Score (High→Low)":
        filtered.sort(
            key=lambda x: x.composite_score or 0, reverse=True
        )
    elif sort_by == "Score (Low→High)":
        filtered.sort(key=lambda x: x.composite_score or 0)
    elif sort_by == "Filename":
        filtered.sort(key=lambda x: x.filename)

    # Gallery grid — 4 columns
    st.markdown(
        f"<div style='font-family:\"DM Mono\",monospace;"
        f"font-size:10px;letter-spacing:0.1em;text-transform:uppercase;"
        f"color:#9A8870;margin-bottom:16px;'>"
        f"Showing {len(filtered):,} photos</div>",
        unsafe_allow_html=True
    )

    cols_per_row = 4
    rows = [filtered[i:i+cols_per_row]
            for i in range(0, len(filtered), cols_per_row)]

    # Check if a photo is selected for detail view
    if "selected_photo" in st.session_state and st.session_state.selected_photo:
        session = get_session()
        detail_photo = session.query(Photo).filter(
            Photo.id == st.session_state.selected_photo
        ).first()
        session.close()

        if detail_photo:
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            # Back button
            if st.button("← Back to Gallery"):
                st.session_state.selected_photo = None
                st.rerun()

            col_detail_img, col_detail_info = st.columns([1.5, 1])

            with col_detail_img:
                if detail_photo.thumbnail_path and os.path.exists(detail_photo.thumbnail_path):
                    src = thumb_src(detail_photo.thumbnail_path)
                    st.markdown(
                        f"<div style='border-radius:8px;overflow:hidden;"
                        f"box-shadow:0 4px 16px rgba(26,22,16,0.12);'>"
                        f"<img src='{src}' style='width:100%;display:block;'></div>",
                        unsafe_allow_html=True
                    )

            with col_detail_info:
                tier_color = {"great": FOREST, "good": AMBER, "review": SKY, "delete": "#C8BEA8"}.get(detail_photo.tier, "#C8BEA8")

                st.markdown(
                    f"<div style='background:#FFFFFF;border:1px solid #E8E2D4;"
                    f"border-radius:8px;padding:20px;margin-bottom:16px;'>"
                    f"<div style='font-family:\"Cormorant Garamond\",serif;"
                    f"font-size:24px;font-weight:700;color:#1A1610;"
                    f"margin-bottom:8px;'>{detail_photo.filename}</div>"
                    f"<div style='display:inline-block;background:{tier_color};"
                    f"color:white;border-radius:4px;padding:4px 12px;"
                    f"font-family:\"DM Mono\",monospace;font-size:11px;"
                    f"font-weight:600;text-transform:uppercase;"
                    f"margin-bottom:12px;'>{detail_photo.tier} · {detail_photo.composite_score:.0f}</div>"
                    f"<div style='display:grid;grid-template-columns:1fr 1fr;"
                    f"gap:6px;font-family:\"DM Mono\",monospace;font-size:10px;"
                    f"color:#5C5040;margin-bottom:12px;'>"
                    f"<div>ISO {detail_photo.exif_iso or '?'}</div>"
                    f"<div>f/{detail_photo.exif_aperture or '?'}</div>"
                    f"<div>{detail_photo.exif_shutter or '?'}s</div>"
                    f"<div>{detail_photo.exif_focal_len or '?'}mm</div>"
                    f"</div></div>",
                    unsafe_allow_html=True
                )

                # AI explanation
                if detail_photo.ai_explanation:
                    st.markdown(
                        f"<div style='background:#FAF8F3;border:1px solid #E8E2D4;"
                        f"border-radius:6px;padding:14px;font-size:12px;"
                        f"color:#5C5040;line-height:1.6;font-style:italic;"
                        f"margin-bottom:12px;'>{detail_photo.ai_explanation}</div>",
                        unsafe_allow_html=True
                    )

                # Score breakdown
                if detail_photo.score_breakdown:
                    breakdown_text = ""
                    for dim, val in detail_photo.score_breakdown.items():
                        color = "#2D5016" if val >= 15 else "#C87020" if val >= 8 else "#A83020"
                        breakdown_text += (
                            f"<div style='margin-bottom:8px;'>"
                            f"<div style='display:flex;justify-content:space-between;"
                            f"margin-bottom:3px;'>"
                            f"<span style='font-size:11px;color:#5C5040;'>{dim}</span>"
                            f"<span style='font-family:\"DM Mono\",monospace;"
                            f"font-size:10px;color:{color};font-weight:600;'>{val}/25</span></div>"
                            f"<div style='height:6px;background:#F5F2EA;border-radius:3px;"
                            f"overflow:hidden;'>"
                            f"<div style='width:{val/25*100:.0f}%;height:100%;"
                            f"background:{color};border-radius:3px;'></div></div></div>"
                        )
                    st.markdown(breakdown_text, unsafe_allow_html=True)

                # Edit suggestions
                if detail_photo.edit_suggestions:
                    edits = detail_photo.edit_suggestions
                    edit_parts = []
                    if edits.get("lightroom"):
                        edit_parts.append(f"<strong>Lightroom:</strong> {edits['lightroom']}")
                    if edits.get("topaz"):
                        edit_parts.append(f"<strong>Topaz:</strong> {edits['topaz']}")
                    if edits.get("crop"):
                        edit_parts.append(f"<strong>Crop:</strong> {edits['crop']}")
                    if edit_parts:
                        st.markdown(
                            f"<div style='background:#EEF5E8;border:1px solid #7A9E6A;"
                            f"border-radius:6px;padding:12px;font-size:11px;"
                            f"color:#2D5016;line-height:1.6;'>"
                            f"{'<br>'.join(edit_parts)}</div>",
                            unsafe_allow_html=True
                        )

            st.stop()

    # Gallery grid — 4 columns
    st.markdown(
        f"<div style='font-family:\"DM Mono\",monospace;"
        f"font-size:10px;letter-spacing:0.1em;text-transform:uppercase;"
        f"color:#9A8870;margin-bottom:16px;'>"
        f"Showing {len(filtered):,} photos</div>",
        unsafe_allow_html=True
    )

    cols_per_row = 4
    rows = [filtered[i:i+cols_per_row]
            for i in range(0, len(filtered), cols_per_row)]

    for row in rows:
        cols = st.columns(cols_per_row)
        for col, photo in zip(cols, row):
            with col:
                if (photo.thumbnail_path
                        and os.path.exists(photo.thumbnail_path)):
                    src = thumb_src(photo.thumbnail_path)
                    tier_color = {
                        "great": FOREST,
                        "good": AMBER,
                        "review": SKY,
                        "delete": "#C8BEA8",
                    }.get(photo.tier, "#C8BEA8")

                    st.markdown(f"""
                    <div class="photo-card">
                        <img src="{src}" alt="{photo.filename}">
                        <div class="photo-tier-strip tier-{photo.tier}">
                        </div>
                        <div style='position:absolute;top:8px;right:8px;
                                    background:rgba(255,255,255,0.92);
                                    backdrop-filter:blur(8px);
                                    border-radius:20px;padding:2px 9px;
                                    font-family:"DM Mono",monospace;
                                    font-size:11px;font-weight:500;
                                    color:{tier_color};'>
                            {photo.composite_score:.0f}
                        </div>
                        <div class="photo-meta">
                            <span class="photo-filename">
                                {photo.filename[:16]}
                            </span>
                            {tier_badge(photo.tier)}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # View button — opens detail view
                    if st.button(
                        "View →",
                        key=f"view_{photo.id}",
                        use_container_width=True
                    ):
                        st.session_state.selected_photo = photo.id
                        st.rerun()
# ══════════════════════════════════════════════════════════════════════════
# PAGE: ANALYTICS (existing code from your file - all sections complete)
# ══════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════
# PAGE: ANALYTICS (CORRECTED - MATCHES MOCKUP)
# ══════════════════════════════════════════════════════════════════════════
elif page == "Analytics":
    if not active_trip:
        st.info("Select a trip first.")
        st.stop()

    # ═══ STEP 1: Load trip data FIRST ═══════════════════════════════════
    session = get_session()
    photos = session.query(Photo).filter(Photo.trip_id == active_trip.id).all()
    session.close()

    scored_photos = [p for p in photos if p.composite_score is not None and p.composite_score > 0]

    if not scored_photos:
        st.info("No scored photos yet. Run AI scoring first.")
        st.stop()

    # ═══ STEP 2: Calculate all variables ════════════════════════════════
    total = len(photos)
    greats = sum(1 for p in photos if p.tier == "great")
    goods = sum(1 for p in photos if p.tier == "good")
    reviews = sum(1 for p in photos if p.tier == "review")
    deletes = sum(1 for p in photos if p.tier == "delete")
    avg_score = (sum(p.composite_score for p in scored_photos) / len(scored_photos)) if scored_photos else 0
    keep_rate = (greats + goods) / total * 100 if total > 0 else 0

    # Per-category data
    cat_data = {}
    for p in photos:
        if not p.category:
            continue
        label = CATEGORY_LABELS.get(p.category, p.category)
        if label not in cat_data:
            cat_data[label] = {"key": p.category, "total": 0, "great": 0, "good": 0, "review": 0, "delete": 0, "scores": [], "breakdown_sums": {}}
        cat_data[label]["total"] += 1
        if p.tier in ["great", "good", "review", "delete"]:
            cat_data[label][p.tier] += 1
        if p.composite_score:
            cat_data[label]["scores"].append(p.composite_score)
        if p.score_breakdown:
            for dim, val in p.score_breakdown.items():
                cat_data[label]["breakdown_sums"].setdefault(dim, []).append(val)

    # Dimension averages
    all_breakdown = {}
    for p in scored_photos:
        if p.score_breakdown:
            for dim, val in p.score_breakdown.items():
                all_breakdown.setdefault(dim, []).append(val)
    
    dim_avgs = {dim: round(sum(vals)/len(vals), 1) for dim, vals in all_breakdown.items() if vals}

    # ═══ STEP 3: NOW render page with all variables available ═══════════
    st.markdown("<h1>Trip Analytics</h1>", unsafe_allow_html=True)
    
    # Subtitle with trip info
    st.markdown(f"""
    <div style='font-family:"DM Mono",monospace;font-size:9px;
                letter-spacing:0.12em;text-transform:uppercase;
                color:#9A8870;margin-bottom:4px;'>
        {active_trip.name} · {active_trip.created_at.strftime('%B %Y')} · Nikon Z9 · {total} frames
    </div>
    <div style='font-family:"DM Mono",monospace;font-size:9px;
                color:#C8BEA8;margin-bottom:20px;'>
        ● Processed 25 Apr 2026
    </div>
    """, unsafe_allow_html=True)

    # ── SECTION 1: Stat Strip ──────────────────────────────────────────
    st.markdown(
        "<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
        "letter-spacing:0.14em;text-transform:uppercase;color:#C8BEA8;"
        "margin-bottom:10px;margin-top:4px;'>Session Overview</div>",
        unsafe_allow_html=True
    )

    c1, c2, c3, c4 = st.columns(4)
    for col, val, label, note, color in [
        (c1, str(total), "Total Photos", "All NEF RAW files", "#1A1610"),
        (c2, str(greats + goods), "Good — Keepers", f"{keep_rate:.0f}% keep rate", "#C87020"),
        (c3, str(reviews), "Need Review", "Your decision needed", "#2060A0"),
        (c4, f"{avg_score:.1f}", "Session Average", "Out of 100", "#2D5016"),
    ]:
        with col:
            st.markdown(f"""
            <div style='background:#FFFFFF;border:1px solid #E8E2D4;
                        border-top:2px solid {color};border-radius:8px;
                        padding:16px 18px;'>
                <div style='font-family:"DM Mono",monospace;font-size:8px;
                            letter-spacing:0.1em;text-transform:uppercase;
                            color:#9A8870;margin-bottom:4px;'>{label}</div>
                <div style='font-family:"Cormorant Garamond",serif;
                            font-size:36px;font-weight:700;line-height:1;
                            color:{color};'>{val}</div>
                <div style='font-size:11px;color:#C8BEA8;margin-top:3px;'>{note}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── SECTION 2: Score Definitions ──────────────────────────────────
    st.markdown(
        "<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
        "letter-spacing:0.14em;text-transform:uppercase;color:#C8BEA8;"
        "margin-bottom:10px;'>What the Scores Mean</div>",
        unsafe_allow_html=True
    )
    
    d1, d2, d3, d4 = st.columns(4)
    
    with d1:
        st.markdown("""
        <div style='background:#EEF5E8;border:1px solid #E8E2D4;border-top:3px solid #2D5016;border-radius:8px;padding:16px;height:145px;'>
            <div style='font-family:"DM Mono",monospace;font-size:9px;letter-spacing:0.1em;text-transform:uppercase;color:#2D5016;font-weight:700;margin-bottom:4px;'>✦ GREAT</div>
            <div style='font-family:"Cormorant Garamond",serif;font-size:28px;font-weight:700;color:#2D5016;line-height:1;margin-bottom:8px;'>72–100</div>
            <div style='font-size:11px;line-height:1.5;color:#5C5040;'>Publication ready. Technically excellent and emotionally compelling.</div>
        </div>
        """, unsafe_allow_html=True)
    
    with d2:
        st.markdown("""
        <div style='background:#FCF0E0;border:1px solid #E8E2D4;border-top:3px solid #C87020;border-radius:8px;padding:16px;height:145px;'>
            <div style='font-family:"DM Mono",monospace;font-size:9px;letter-spacing:0.1em;text-transform:uppercase;color:#C87020;font-weight:700;margin-bottom:4px;'>GOOD</div>
            <div style='font-family:"Cormorant Garamond",serif;font-size:28px;font-weight:700;color:#C87020;line-height:1;margin-bottom:8px;'>50–71</div>
            <div style='font-size:11px;line-height:1.5;color:#5C5040;'>Solid keeper. Minor flaws but worth editing and keeping.</div>
        </div>
        """, unsafe_allow_html=True)
    
    with d3:
        st.markdown("""
        <div style='background:#EEF4FC;border:1px solid #E8E2D4;border-top:3px solid #2060A0;border-radius:8px;padding:16px;height:145px;'>
            <div style='font-family:"DM Mono",monospace;font-size:9px;letter-spacing:0.1em;text-transform:uppercase;color:#2060A0;font-weight:700;margin-bottom:4px;'>REVIEW</div>
            <div style='font-family:"Cormorant Garamond",serif;font-size:28px;font-weight:700;color:#2060A0;line-height:1;margin-bottom:8px;'>30–49</div>
            <div style='font-size:11px;line-height:1.5;color:#5C5040;'>Borderline. AI uncertain — you decide.</div>
        </div>
        """, unsafe_allow_html=True)
    
    with d4:
        st.markdown("""
        <div style='background:#FDF0EE;border:1px solid #E8E2D4;border-top:3px solid #A83020;border-radius:8px;padding:16px;height:145px;'>
            <div style='font-family:"DM Mono",monospace;font-size:9px;letter-spacing:0.1em;text-transform:uppercase;color:#A83020;font-weight:700;margin-bottom:4px;'>DELETE</div>
            <div style='font-family:"Cormorant Garamond",serif;font-size:28px;font-weight:700;color:#A83020;line-height:1;margin-bottom:8px;'>0–29</div>
            <div style='font-size:11px;line-height:1.5;color:#5C5040;'>Technical issues make this unsuitable for keeping.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── SECTION 3: Photos by Category (PLOTLY - NO HTML ERRORS) ───────
    st.markdown(
        "<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
        "letter-spacing:0.14em;text-transform:uppercase;color:#C8BEA8;"
        "margin-bottom:10px;'>Photos by Category — Great / Good / Review / Delete</div>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
        "letter-spacing:0.12em;text-transform:uppercase;color:#9A8870;"
        "margin-bottom:12px;'>Count per Tier inside each Category</div>",
        unsafe_allow_html=True
    )

    if cat_data:
        for label, data in sorted(cat_data.items(), key=lambda x: x[1]["total"], reverse=True):
            st.markdown(f"**{label}** — {data['total']} photos")
            
            # Create horizontal stacked bar using Plotly
            fig = go.Figure()
            
            colors_map = {'great': '#2D5016', 'good': '#C87020', 'review': '#7AACCC', 'delete': '#C8BEA8'}
            
            for tier in ['great', 'good', 'review', 'delete']:
                if data[tier] > 0:
                    fig.add_trace(go.Bar(
                        name=tier.capitalize(),
                        y=[''],
                        x=[data[tier]],
                        orientation='h',
                        marker=dict(color=colors_map[tier]),
                        text=[str(data[tier])],
                        textposition='inside',
                        textfont=dict(color='white', size=12, family='DM Mono'),
                        hovertemplate=f'{tier.capitalize()}: {data[tier]}<extra></extra>',
                    ))
            
            fig.update_layout(
                barmode='stack',
                height=50,
                margin=dict(l=0, r=0, t=0, b=0),
                showlegend=False,
                xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                plot_bgcolor='#F5F2EA',
                paper_bgcolor='#FFFFFF',
            )
            
            st.plotly_chart(fig, use_container_width=True, key=f"cat_bar_{label}")
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        
        # Legend
        leg1, leg2, leg3, leg4 = st.columns(4)
        with leg1:
            st.markdown("🟢 **Great**")
        with leg2:
            st.markdown("🟠 **Good**")
        with leg3:
            st.markdown("🔵 **Review**")
        with leg4:
            st.markdown("⚪ **Delete**")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── SECTION 4: Score vs Benchmark (PLOTLY - NO HTML ERRORS) ───────
    st.markdown(
        "<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
        "letter-spacing:0.14em;text-transform:uppercase;color:#C8BEA8;"
        "margin-bottom:10px;'>Your Average Score vs Industry Benchmark</div>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
        "letter-spacing:0.12em;text-transform:uppercase;color:#9A8870;"
        "margin-bottom:12px;'>Grouped by Category — Your Score vs Benchmark</div>",
        unsafe_allow_html=True
    )

    if cat_data:
        for label, data in sorted(cat_data.items(), key=lambda x: sum(x[1]["scores"])/len(x[1]["scores"]) if x[1]["scores"] else 0, reverse=True):
            if not data["scores"]:
                continue
            
            your_avg = round(sum(data["scores"]) / len(data["scores"]), 1)
            bench = INDUSTRY_BENCHMARKS.get(data["key"], {"avg": 63})["avg"]
            delta = round(your_avg - bench, 1)
            
            st.markdown(f"**{label}**")
            
            # Create grouped bar chart using Plotly
            fig = go.Figure()
            
            bar_color = "#C87020" if your_avg >= 60 else "#7AACCC"
            
            fig.add_trace(go.Bar(
                name='Your avg',
                x=[your_avg],
                y=['Score'],
                orientation='h',
                marker=dict(color=bar_color),
                text=[f'{your_avg}'],
                textposition='outside',
                textfont=dict(color='#1A1610', size=11, family='DM Mono'),
                hovertemplate=f'Your avg: {your_avg}<extra></extra>',
            ))
            
            fig.add_trace(go.Bar(
                name='Benchmark',
                x=[bench],
                y=['Benchmark'],
                orientation='h',
                marker=dict(color='#E8E2D4'),
                text=[f'{bench}'],
                textposition='outside',
                textfont=dict(color='#9A8870', size=11, family='DM Mono'),
                hovertemplate=f'Benchmark: {bench}<extra></extra>',
            ))
            
            fig.update_layout(
                height=100,
                margin=dict(l=80, r=40, t=10, b=10),
                showlegend=False,
                xaxis=dict(range=[0, 100], showgrid=True, gridcolor='#F5F2EA'),
                yaxis=dict(showgrid=False),
                plot_bgcolor='#FFFFFF',
                paper_bgcolor='#FFFFFF',
            )
            
            st.plotly_chart(fig, use_container_width=True, key=f"bench_bar_{label}")
            
            # Delta
            sign = "▲" if delta >= 0 else "▼"
            d_color = "#2D5016" if delta >= 0 else "#A83020"
            st.markdown(
                f"<div style='text-align:right;font-family:\"DM Mono\",monospace;"
                f"font-size:10px;color:{d_color};margin-bottom:16px;'>"
                f"{sign} {abs(delta)} pts vs benchmark · {data['total']} photos"
                f"</div>",
                unsafe_allow_html=True
            )
        
        # Delta cards
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        
        cols = st.columns(len(cat_data))
        for idx, (label, data) in enumerate(sorted(cat_data.items())):
            if not data["scores"]:
                continue
            
            your_avg = round(sum(data["scores"]) / len(data["scores"]), 1)
            bench = INDUSTRY_BENCHMARKS.get(data["key"], {"avg": 63})["avg"]
            delta = round(your_avg - bench, 1)
            
            delta_bg = "#EEF5E8" if delta >= 0 else "#FDF0EE"
            delta_border = "#7A9E6A" if delta >= 0 else "#D89080"
            d_color = "#2D5016" if delta >= 0 else "#A83020"
            
            with cols[idx]:
                st.markdown(f"""
                <div style='background:{delta_bg};border:1px solid {delta_border};
                            border-radius:6px;padding:12px;text-align:center;'>
                    <div style='font-family:"DM Mono",monospace;font-size:8px;
                                letter-spacing:0.08em;text-transform:uppercase;
                                color:#9A8870;margin-bottom:4px;'>{label[:16]}</div>
                    <div style='font-family:"Cormorant Garamond",serif;font-size:24px;
                                font-weight:700;line-height:1;color:{d_color};'>
                        {'+' if delta >= 0 else ''}{delta}
                    </div>
                    <div style='font-size:10px;color:{d_color};margin-top:3px;'>
                        {"▲" if delta >= 0 else "▼"} vs benchmark
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── SECTION 5: Dimension Analysis ─────────────────────────────────
    # ── SECTION 5: Dimension Analysis ─────────────────────────────────
    st.markdown(
        "<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
        "letter-spacing:0.14em;text-transform:uppercase;color:#C8BEA8;"
        "margin-bottom:10px;'>What Drives Your Score — Dimension Analysis</div>",
        unsafe_allow_html=True
    )

    col_radar, col_dims = st.columns([1.1, 1])

    with col_radar:
        dims_ordered = list(DIM_CONFIG.keys())
        your_vals = [dim_avgs.get(d, 50) for d in dims_ordered]
        bench_vals = [68, 55, 52, 62, 62, 60]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=bench_vals + [bench_vals[0]],
            theta=dims_ordered + [dims_ordered[0]],
            fill=None, mode="lines",
            line=dict(color="#C8BEA8", width=1.5, dash="dot"),
            name="Benchmark",
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=your_vals + [your_vals[0]],
            theta=dims_ordered + [dims_ordered[0]],
            fill="toself", fillcolor="rgba(200,112,32,0.12)",
            mode="lines+markers",
            line=dict(color="#C87020", width=2.5),
            marker=dict(size=6, color="#C87020"),
            name="Your Score",
        ))
        fig_radar.update_layout(
            polar=dict(
                bgcolor="#FAF8F3",
                radialaxis=dict(visible=True, range=[0, 100],
                    showticklabels=True, tickfont=dict(size=9, color="#9A8870"),
                    gridcolor="#E8E2D4", linecolor="#E8E2D4"),
                angularaxis=dict(tickfont=dict(size=10, family="DM Mono", color="#5C5040"),
                    gridcolor="#E8E2D4", linecolor="#E8E2D4"),
            ),
            showlegend=True,
            legend=dict(font=dict(family="DM Mono", size=10, color="#5C5040"),
                orientation="h", yanchor="bottom", y=-0.08, xanchor="center", x=0.5),
            plot_bgcolor="#FAF8F3",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=30, r=30, t=20, b=40),
            height=400,
        )

        # Title ABOVE the chart (not wrapping it)
        st.markdown(
            "<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
            "letter-spacing:0.12em;text-transform:uppercase;"
            "color:#9A8870;margin-bottom:4px;'>"
            "Average Score per Dimension — This Session</div>",
            unsafe_allow_html=True
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with col_dims:
        # Build ALL dimension bars in ONE single st.markdown call
        sorted_dims = sorted(DIM_CONFIG.items(), key=lambda x: dim_avgs.get(x[0], 50), reverse=True)

        dims_content = ""
        for dim, cfg in sorted_dims:
            val = dim_avgs.get(dim, 50)
            dims_content += (
                f"<div style='margin-bottom:12px;'>"
                f"<div style='display:flex;justify-content:space-between;"
                f"align-items:baseline;margin-bottom:3px;'>"
                f"<span style='font-size:10.5px;font-weight:500;color:#1A1610;'>{dim}</span>"
                f"<span style='font-family:\"DM Mono\",monospace;font-size:10px;"
                f"color:{cfg['color']};font-weight:600;'>{val:.0f}/100</span></div>"
                f"<div style='height:8px;background:#F5F2EA;border-radius:4px;"
                f"border:1px solid #E8E2D4;overflow:hidden;'>"
                f"<div style='width:{val:.0f}%;height:100%;background:{cfg['color']};"
                f"border-radius:3px;'></div></div>"
                f"<div style='font-size:9px;color:{cfg['note_color']};"
                f"margin-top:2px;line-height:1.3;'>{cfg['note']}</div></div>"
            )

        st.markdown(
            f"<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
            f"letter-spacing:0.12em;text-transform:uppercase;"
            f"color:#9A8870;margin-bottom:12px;'>"
            f"Dimension Scores — What to Focus On</div>"
            f"{dims_content}",
            unsafe_allow_html=True
        )

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── SECTION 6: Detailed Table (COLOR-CODED LIKE MOCKUP) ───────────
    st.markdown(
        "<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
        "letter-spacing:0.14em;text-transform:uppercase;color:#C8BEA8;"
        "margin-bottom:10px;'>Detailed Breakdown — All Categories</div>",
        unsafe_allow_html=True
    )

    if cat_data:
        th = "padding:10px 14px;text-align:center;font-family:'DM Mono',monospace;font-size:9px;letter-spacing:0.08em;text-transform:uppercase;color:#5C5040;font-weight:600;border-bottom:2px solid #E8E2D4;"
        td = "padding:10px 14px;text-align:center;font-family:'DM Mono',monospace;font-size:11px;"

        table_html = (
            "<div style='background:#FFFFFF;border:1px solid #E8E2D4;border-radius:8px;"
            "padding:0;overflow:hidden;'>"
            "<table style='width:100%;border-collapse:collapse;'>"
            f"<thead><tr style='background:#F5F2EA;'>"
            f"<th style='{th}text-align:left;'>Category</th>"
            f"<th style='{th}'>Total</th>"
            f"<th style='{th}'>Great</th>"
            f"<th style='{th}'>Good</th>"
            f"<th style='{th}'>Review</th>"
            f"<th style='{th}'>Delete</th>"
            f"<th style='{th}'>Keep %</th>"
            f"<th style='{th}'>Avg Score</th>"
            f"<th style='{th}'>Benchmark</th>"
            f"<th style='{th}'>vs Bench</th>"
            f"</tr></thead><tbody>"
        )

        for label, data in cat_data.items():
            t = max(data["total"], 1)
            your_avg = round(sum(data["scores"]) / len(data["scores"]), 1) if data["scores"] else 0
            bench = INDUSTRY_BENCHMARKS.get(data["key"], {"avg": 63})["avg"]
            delta = round(your_avg - bench, 1)
            keep = round((data["great"] + data["good"]) / t * 100)
            dc = "#2D5016" if delta >= 0 else "#A83020"

            table_html += (
                f"<tr style='border-bottom:1px solid #F5F2EA;'>"
                f"<td style='{td}text-align:left;font-weight:500;color:#1A1610;'>{label}</td>"
                f"<td style='{td}color:#5C5040;'>{data['total']}</td>"
                f"<td style='{td}color:#2D5016;'>{data['great']}</td>"
                f"<td style='{td}color:#C87020;font-weight:600;'>{data['good']}</td>"
                f"<td style='{td}color:#2060A0;'>{data['review']}</td>"
                f"<td style='{td}color:#C8BEA8;'>{data['delete']}</td>"
                f"<td style='{td}color:#5C5040;'>{keep}%</td>"
                f"<td style='{td}color:#1A1610;font-weight:600;'>{your_avg}</td>"
                f"<td style='{td}color:#9A8870;'>{bench}</td>"
                f"<td style='{td}color:{dc};font-weight:600;'>{'+' if delta>=0 else ''}{delta}</td>"
                f"</tr>"
            )

        total_your = round(avg_score, 1)
        table_html += (
            f"<tr style='background:#F5F2EA;border-top:2px solid #E8E2D4;'>"
            f"<td style='{td}text-align:left;font-weight:700;color:#1A1610;'>Total / Session</td>"
            f"<td style='{td}font-weight:700;color:#1A1610;'>{total}</td>"
            f"<td style='{td}font-weight:700;color:#2D5016;'>{greats}</td>"
            f"<td style='{td}font-weight:700;color:#C87020;'>{goods}</td>"
            f"<td style='{td}font-weight:700;color:#2060A0;'>{reviews}</td>"
            f"<td style='{td}font-weight:700;color:#C8BEA8;'>{deletes}</td>"
            f"<td style='{td}font-weight:700;color:#1A1610;'>{keep_rate:.0f}%</td>"
            f"<td style='{td}font-weight:700;color:#1A1610;'>{total_your}</td>"
            f"<td style='{td}font-weight:700;color:#9A8870;'>–</td>"
            f"<td style='{td}font-weight:700;color:#9A8870;'>–</td>"
            f"</tr></tbody></table></div>"
        )

        st.markdown(table_html, unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── SECTION 7: Export (TEXT LEFT, BUTTON RIGHT, INSIDE SAME ROW) ──
    st.markdown(
        "<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
        "letter-spacing:0.14em;text-transform:uppercase;color:#C8BEA8;"
        "margin-bottom:10px;'>Export</div>",
        unsafe_allow_html=True
    )

    rows = [{
        "Filename": p.filename, "Tier": p.tier, "Score": p.composite_score,
        "Category": CATEGORY_LABELS.get(p.category, ""),
        "User Rating": p.user_rating or "",
        "ISO": p.exif_iso, "Aperture": p.exif_aperture,
        "Shutter": p.exif_shutter, "Focal Length": p.exif_focal_len,
        "AI Explanation": p.ai_explanation or "",
        "LR Edit Notes": (p.edit_suggestions or {}).get("lightroom", ""),
        "Topaz Notes": (p.edit_suggestions or {}).get("topaz", ""),
        "Crop Note": (p.edit_suggestions or {}).get("crop", ""),
    } for p in photos]

    df_export = pd.DataFrame(rows)
    csv = df_export.to_csv(index=False)

    col_exp_desc, col_exp_action = st.columns([3, 1])

    with col_exp_desc:
        st.markdown(
            "<div style='background:#FFFFFF;border:1px solid #E8E2D4;"
            "border-radius:8px;padding:24px;height:100%;'>"
            "<div style='font-size:13px;color:#5C5040;line-height:1.7;'>"
            "Export your full trip report — includes score, tier, category, "
            "edit recommendations, and EXIF data per photo. "
            "Compatible with Lightroom, Capture One, and darktable.</div></div>",
            unsafe_allow_html=True
        )

    with col_exp_action:
        # Button styling
        st.markdown("""
        <style>
        div.stDownloadButton > button {
            background-color: #2D5016 !important;
            color: #FFFFFF !important;
            border: none !important;
            padding: 14px 20px !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            letter-spacing: 0.04em !important;
            min-height: 60px !important;
        }
        div.stDownloadButton > button:hover {
            background-color: #3D6B20 !important;
            color: #FFFFFF !important;
        }
        div.stDownloadButton > button * {
            color: #FFFFFF !important;
        }
        </style>
        """, unsafe_allow_html=True)

        st.download_button(
            "⬇  Export Full Trip Report CSV",
            csv,
            f"picker_{active_trip.name.replace(' ','_')}.csv",
            "text/csv",
            use_container_width=True,
        )
# ══════════════════════════════════════════════════════════════════════════
# PAGE: RATE PHOTOS
# ══════════════════════════════════════════════════════════════════════════
elif page == "Rate Photos":
    st.markdown("<h1>Rate Your Photos</h1>", unsafe_allow_html=True)

    if not active_trip:
        st.info("Select a trip first.")
        st.stop()

    session = get_session()
    all_rateable = session.query(Photo).filter(
        Photo.trip_id == active_trip.id,
        Photo.tier.in_(["great", "good", "review"]),
    ).order_by(Photo.composite_score.desc()).all()

    unrated = [p for p in all_rateable if p.user_rating is None]
    already_rated = [p for p in all_rateable if p.user_rating is not None]
    session.close()

    total_rateable = len(all_rateable)
    total_unrated = len(unrated)
    total_rated = len(already_rated)

    # ── All photos rated — show summary + Review Again ────────────────
    if total_unrated == 0:
        # Count by rating
        great_count = sum(1 for p in already_rated if p.user_rating == "great")
        good_count = sum(1 for p in already_rated if p.user_rating == "good")
        delete_count = sum(1 for p in already_rated if p.user_rating == "delete")

        st.markdown(f"""
        <div style='background:#EEF5E8;border:1px solid {SAGE};
                    border-radius:8px;padding:24px;margin-bottom:20px;'>
            <div style='font-family:"Cormorant Garamond",serif;
                        font-size:22px;color:{FOREST};margin-bottom:12px;'>
                ✓ All {total_rateable} photos have been rated!
            </div>
            <div style='font-size:13px;color:#5C5040;line-height:1.8;'>
                <strong style='color:{FOREST};'>⭐ Great:</strong> {great_count} photos<br>
                <strong style='color:{AMBER};'>👍 Good:</strong> {good_count} photos<br>
                <strong style='color:#A83020;'>🗑 Delete:</strong> {delete_count} photos<br><br>
                <strong>{great_count + good_count} keepers</strong> ready for Story Studio
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Review Again button
        st.markdown("""
        <style>
        button[data-testid="baseButton-secondary"] {
            font-weight: 600 !important;
        }
        </style>
        """, unsafe_allow_html=True)

        if st.button("🔄  Review Again — Reset All Ratings", use_container_width=True):
            session = get_session()
            for p_id in [p.id for p in already_rated]:
                photo_obj = session.query(Photo).filter(Photo.id == p_id).first()
                if photo_obj:
                    photo_obj.user_rating = None
                    photo_obj.rated_at = None
                    photo_obj.tier = "review"
            session.commit()
            session.close()
            st.session_state.rate_idx = 0
            st.rerun()

        st.info("✦ Go to **Story Studio** to create social media posts from your keepers!")
        st.stop()

    # ── Progress bar and counter ──────────────────────────────────────
    if "rate_idx" not in st.session_state:
        st.session_state.rate_idx = 0

    idx = st.session_state.rate_idx
    idx = min(idx, total_unrated - 1)
    photo = unrated[idx]

    # Progress
    progress_pct = total_rated / max(total_rateable, 1)
    st.progress(progress_pct)

    # Clear progress counter
    st.markdown(
        f"<div style='display:flex;justify-content:space-between;"
        f"align-items:center;margin-bottom:20px;'>"
        f"<div style='font-family:\"DM Mono\",monospace;font-size:11px;"
        f"color:#9A8870;'>"
        f"📸 Reviewing photo <strong style='color:#1A1610;font-size:14px;'>"
        f"{total_rated + 1}</strong> of <strong style='color:#1A1610;font-size:14px;'>"
        f"{total_rateable}</strong>"
        f"</div>"
        f"<div style='font-family:\"DM Mono\",monospace;font-size:10px;"
        f"color:#C8BEA8;'>"
        f"✅ {total_rated} rated · ⏳ {total_unrated} remaining · "
        f"G = Great · O = Good · D = Delete"
        f"</div></div>",
        unsafe_allow_html=True
    )

    col_img, col_panel = st.columns([1.8, 1])

    with col_img:
        if photo.thumbnail_path and os.path.exists(photo.thumbnail_path):
            src = thumb_src(photo.thumbnail_path)
            st.markdown(
                f"<div style='border-radius:8px;overflow:hidden;"
                f"box-shadow:0 4px 16px rgba(26,22,16,0.12);'>"
                f"<img src='{src}' style='width:100%;display:block;'></div>",
                unsafe_allow_html=True
            )

    with col_panel:
        # Filename and score
        tier_color = {"great": FOREST, "good": AMBER, "review": SKY, "delete": "#C8BEA8"}.get(photo.tier, "#C8BEA8")
        st.markdown(
            f"<div style='background:#FFFFFF;border:1px solid #E8E2D4;"
            f"border-radius:8px;padding:16px;margin-bottom:12px;'>"
            f"<div style='font-family:\"Cormorant Garamond\",serif;"
            f"font-size:18px;font-weight:700;color:#1A1610;margin-bottom:6px;'>"
            f"{photo.filename}</div>"
            f"<div style='display:inline-block;background:{tier_color};"
            f"color:white;border-radius:4px;padding:3px 10px;"
            f"font-family:\"DM Mono\",monospace;font-size:10px;"
            f"text-transform:uppercase;'>{photo.tier} · {photo.composite_score:.0f}</div></div>",
            unsafe_allow_html=True
        )

        # EXIF strip
        st.markdown(
            f"<div style='background:#FFFFFF;border:1px solid #E8E2D4;"
            f"border-radius:8px;padding:14px;margin-bottom:12px;'>"
            f"<div style='display:grid;grid-template-columns:1fr 1fr;"
            f"gap:6px;font-family:\"DM Mono\",monospace;font-size:10px;color:#5C5040;'>"
            f"<div>ISO {photo.exif_iso or '?'}</div>"
            f"<div>f/{photo.exif_aperture or '?'}</div>"
            f"<div>{photo.exif_shutter or '?'}s</div>"
            f"<div>{photo.exif_focal_len or '?'}mm</div></div></div>",
            unsafe_allow_html=True
        )

        # AI scores
        if photo.score_breakdown:
            breakdown_html = ""
            for dim, val in photo.score_breakdown.items():
                color = "#2D5016" if val >= 15 else "#C87020" if val >= 8 else "#A83020"
                breakdown_html += (
                    f"<div style='margin-bottom:6px;'>"
                    f"<div style='display:flex;justify-content:space-between;margin-bottom:2px;'>"
                    f"<span style='font-size:10px;color:#5C5040;'>{dim}</span>"
                    f"<span style='font-family:\"DM Mono\",monospace;font-size:10px;"
                    f"color:{color};font-weight:600;'>{val}/25</span></div>"
                    f"<div style='height:6px;background:#F5F2EA;border-radius:3px;overflow:hidden;'>"
                    f"<div style='width:{val/25*100:.0f}%;height:100%;background:{color};"
                    f"border-radius:3px;'></div></div></div>"
                )
            st.markdown(breakdown_html, unsafe_allow_html=True)

        # AI explanation
        if photo.ai_explanation:
            st.markdown(
                f"<div style='background:#FAF8F3;border:1px solid #E8E2D4;"
                f"border-radius:6px;padding:12px;font-size:12px;color:#5C5040;"
                f"line-height:1.6;font-style:italic;margin-bottom:12px;'>"
                f"{photo.ai_explanation}</div>",
                unsafe_allow_html=True
            )

        # Edit suggestions
        if photo.edit_suggestions:
            with st.expander("✦ Editing Recommendations"):
                edits = photo.edit_suggestions
                if edits.get("lightroom"):
                    st.markdown(f"**Lightroom:** {edits['lightroom']}")
                if edits.get("topaz"):
                    st.markdown(f"**Topaz:** {edits['topaz']}")
                if edits.get("crop"):
                    st.markdown(f"**Crop:** {edits['crop']}")

    # Rating buttons
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    def rate(rating: str):
        session = get_session()
        p = session.query(Photo).filter(Photo.id == photo.id).first()
        if p:
            p.user_rating = rating
            p.rated_at = datetime.now()
            # ALSO update tier so Story Studio can find keepers
            if rating == "great":
                p.tier = "great"
            elif rating == "good":
                p.tier = "good"
            elif rating == "delete":
                p.tier = "delete"
        session.commit()
        session.close()
        st.session_state.rate_idx = idx + 1
        st.rerun()

    # Button CSS
    st.markdown("""
    <style>
    div[data-testid="column"]:nth-child(1) button {
        background-color: #2D5016 !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 600 !important;
        white-space: nowrap !important;
    }
    div[data-testid="column"]:nth-child(1) button * { color: #FFFFFF !important; }
    div[data-testid="column"]:nth-child(2) button {
        background-color: #C87020 !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 600 !important;
        white-space: nowrap !important;
    }
    div[data-testid="column"]:nth-child(2) button * { color: #FFFFFF !important; }
    div[data-testid="column"]:nth-child(3) button {
        background-color: #A83020 !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 600 !important;
        white-space: nowrap !important;
    }
    div[data-testid="column"]:nth-child(3) button * { color: #FFFFFF !important; }
    </style>
    """, unsafe_allow_html=True)

    r1, r2, r3, r4 = st.columns(4)
    with r1:
        if st.button("⭐ Great", use_container_width=True, key="btn_great"):
            rate("great")
    with r2:
        if st.button("👍 Good", use_container_width=True, key="btn_good"):
            rate("good")
    with r3:
        if st.button("🗑 Delete", use_container_width=True, key="btn_delete"):
            rate("delete")
    with r4:
        if st.button("→ Skip", use_container_width=True, key="btn_skip"):
            st.session_state.rate_idx = idx + 1
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# PAGE: STORY STUDIO
# ══════════════════════════════════════════════════════════════════════════
elif page == "Story Studio":
    st.markdown("<h1>Story Studio</h1>", unsafe_allow_html=True)

    if not active_trip:
        st.info("Select a trip first.")
        st.stop()

    session = get_session()
    from sqlalchemy import or_
    keepers = session.query(Photo).filter(
        Photo.trip_id == active_trip.id,
        or_(
            Photo.tier.in_(["great", "good"]),
            Photo.user_rating.in_(["great", "good"]),
        )
    ).order_by(Photo.composite_score.desc()).all()
    session.close()

    total_keepers = len(keepers)

    st.markdown(
        f"<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
        f"letter-spacing:0.12em;text-transform:uppercase;color:#9A8870;"
        f"margin-bottom:4px;'>"
        f"{active_trip.name} · {active_trip.created_at.strftime('%B %Y')} · "
        f"{total_keepers} keepers</div>"
        f"<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
        f"color:#C8BEA8;margin-bottom:24px;'>"
        f"● Create narratives for your best photos and publish to social media</div>",
        unsafe_allow_html=True
    )

    if not keepers:
        st.info("No keepers yet — score photos in the Gallery first, then rate some as Great or Good.")
        st.stop()

    # Step 1: Select Photos
    st.markdown(
        "<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
        "letter-spacing:0.14em;text-transform:uppercase;color:#C8BEA8;"
        "margin-bottom:10px;'>Step 1 — Select Your Photos</div>",
        unsafe_allow_html=True
    )

    if "story_selected" not in st.session_state:
        st.session_state.story_selected = []

    photo_cols = st.columns(min(len(keepers), 5))
    for i, kp in enumerate(keepers[:10]):
        col_idx = i % 5
        with photo_cols[col_idx]:
            if kp.thumbnail_path and os.path.exists(kp.thumbnail_path):
                src = thumb_src(kp.thumbnail_path)
                is_selected = kp.id in st.session_state.story_selected
                border_color = "#2D5016" if is_selected else "#E8E2D4"
                check = "✓ " if is_selected else ""
                st.markdown(
                    f"<div style='border:2px solid {border_color};border-radius:6px;"
                    f"overflow:hidden;margin-bottom:4px;'>"
                    f"<img src='{src}' style='width:100%;height:70px;object-fit:cover;display:block;'></div>",
                    unsafe_allow_html=True
                )
                if st.button(f"{check}{kp.filename[:10]} ({kp.composite_score:.0f})", key=f"sel_{kp.id}", use_container_width=True):
                    if kp.id in st.session_state.story_selected:
                        st.session_state.story_selected.remove(kp.id)
                    else:
                        st.session_state.story_selected.append(kp.id)
                    st.rerun()

    selected_count = len(st.session_state.story_selected)
    st.markdown(
        f"<div style='font-family:\"DM Mono\",monospace;font-size:11px;"
        f"color:#9A8870;margin:12px 0 24px;'>"
        f"{selected_count} of {min(total_keepers, 10)} photos selected · "
        f"Recommended: 5–10 for carousel</div>",
        unsafe_allow_html=True
    )

    # Step 2: Narrative Mode
    st.markdown(
        "<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
        "letter-spacing:0.14em;text-transform:uppercase;color:#C8BEA8;"
        "margin-bottom:10px;'>Step 2 — Choose Narrative Style</div>",
        unsafe_allow_html=True
    )

    narrative_mode = st.radio(
        "Narrative Style",
        ["🌿  Field Story", "📷  Hybrid (Story + Technical)", "⚙️  Technical"],
        horizontal=True, index=1, label_visibility="collapsed"
    )

    st.markdown(
        "<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
        "letter-spacing:0.1em;text-transform:uppercase;color:#9A8870;"
        "margin-top:16px;margin-bottom:6px;'>"
        "Your Field Notes (Optional — makes the story authentic)</div>",
        unsafe_allow_html=True
    )

    field_notes = st.text_area(
        "Field Notes",
        placeholder="e.g. 'Waited 3 hrs at Dhikala meadow, tigress emerged 4:47 PM...'",
        height=100, label_visibility="collapsed"
    )

    # Step 3: Generate
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    if selected_count == 0:
        st.warning("Select at least 1 photo above to generate a story.")
    else:
        st.markdown("""
        <style>
        button[data-testid="baseButton-primary"] {
            background-color: #2D5016 !important;
            color: #FFFFFF !important;
        }
        button[data-testid="baseButton-primary"] * { color: #FFFFFF !important; }
        </style>
        """, unsafe_allow_html=True)

        generate_clicked = st.button("🧠  Generate Story", type="primary")

        if generate_clicked or "story_output" in st.session_state:
            if generate_clicked:
                session = get_session()
                sel_photos = session.query(Photo).filter(
                    Photo.id.in_(st.session_state.story_selected)
                ).order_by(Photo.composite_score.desc()).all()
                session.close()

                photo_context = []
                for p in sel_photos:
                    photo_context.append({
                        "filename": p.filename, "score": p.composite_score,
                        "tier": p.tier,
                        "category": CATEGORY_LABELS.get(p.category, p.category or ""),
                        "explanation": p.ai_explanation or "",
                        "iso": p.exif_iso, "aperture": p.exif_aperture,
                        "shutter": p.exif_shutter, "focal": p.exif_focal_len,
                    })

                mode_name = narrative_mode.split("  ")[-1]
                prompt = f"""You are a wildlife photography storytelling assistant.
Generate social media content for {selected_count} selected photos.

Trip: {active_trip.name}
Date: {active_trip.created_at.strftime('%B %Y')}
Narrative style: {mode_name}
Field notes: {field_notes if field_notes else 'No notes provided.'}

Photos:
"""
                for i, ctx in enumerate(photo_context):
                    prompt += f"\nPhoto {i+1}: {ctx['filename']} Score:{ctx['score']:.0f} Tier:{ctx['tier']} Category:{ctx['category']}\n  EXIF: ISO {ctx['iso']}, f/{ctx['aperture']}, {ctx['shutter']}s, {ctx['focal']}mm\n  AI: {ctx['explanation']}\n"

                prompt += """
Generate ALL:
1. INSTAGRAM CAPTION (max 2000 chars)
2. INSTAGRAM HASHTAGS: 15 relevant hashtags
3. CAROUSEL ORDER: sequence recommendation
4. WHATSAPP STATUS: one punchy line under 100 chars
5. TWITTER/X POST: under 280 chars
6. FACEBOOK POST: 3-4 sentences

Format with headers: [INSTAGRAM CAPTION], [HASHTAGS], [CAROUSEL ORDER], [WHATSAPP], [TWITTER], [FACEBOOK]"""

                with st.spinner("🧠 Crafting your story..."):
                    try:
                        from anthropic import Anthropic
                        client = Anthropic()
                        response = client.messages.create(
                            model="claude-sonnet-4-6",
                            max_tokens=2000,
                            messages=[{"role": "user", "content": prompt}],
                        )
                        st.session_state.story_output = response.content[0].text
                    except Exception as e:
                        st.error(f"Error generating story: {e}")
                        st.session_state.story_output = None

            if st.session_state.get("story_output"):
                story = st.session_state.story_output
                st.markdown(
                    "<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
                    "letter-spacing:0.14em;text-transform:uppercase;color:#C8BEA8;"
                    "margin:24px 0 12px;'>Step 3 — Your Story</div>",
                    unsafe_allow_html=True
                )

                platform = st.radio(
                    "Platform",
                    ["📸 Instagram", "💬 WhatsApp", "𝕏 Twitter", "📘 Facebook"],
                    horizontal=True, label_visibility="collapsed"
                )

                import re
                def extract_section(text, header):
                    pattern = rf'\[{header}\](.*?)(\[|$)'
                    match = re.search(pattern, text, re.DOTALL)
                    return match.group(1).strip() if match else text

                if "Instagram" in platform:
                    caption = extract_section(story, "INSTAGRAM CAPTION")
                    hashtags = extract_section(story, "HASHTAGS")
                    carousel = extract_section(story, "CAROUSEL ORDER")

                    col_l, col_r = st.columns(2)
                    with col_l:
                        st.markdown("**Carousel Order**")
                        st.markdown(carousel)
                        st.markdown(
                            "<div style='background:#EEF5E8;border:1px solid #7A9E6A;"
                            "border-radius:8px;padding:14px;margin-top:12px;'>"
                            "<div style='font-size:11px;color:#2D5016;'>"
                            "💡 Lead with eye-contact portrait. Best time: 7-9 AM IST. "
                            "Carousels get 1.4× more reach.</div></div>",
                            unsafe_allow_html=True
                        )
                    with col_r:
                        st.markdown("**Caption**")
                        st.markdown(caption)
                        st.markdown("**Hashtags**")
                        st.code(hashtags, language=None)
                        c1, c2 = st.columns(2)
                        with c1:
                            st.download_button("📋 Copy Caption", caption, "caption.txt", "text/plain", use_container_width=True)
                        with c2:
                            st.download_button("📋 Copy Hashtags", hashtags, "hashtags.txt", "text/plain", use_container_width=True)

                elif "WhatsApp" in platform:
                    whatsapp = extract_section(story, "WHATSAPP")
                    st.markdown(f"<div style='background:#FFFFFF;border:1px solid #E8E2D4;border-radius:8px;padding:24px;'><div style='font-size:16px;color:#1A1610;font-weight:500;'>{whatsapp}</div></div>", unsafe_allow_html=True)
                    st.download_button("📋 Copy", whatsapp, "whatsapp.txt", "text/plain")

                elif "Twitter" in platform:
                    twitter = extract_section(story, "TWITTER")
                    st.markdown(f"<div style='background:#FFFFFF;border:1px solid #E8E2D4;border-radius:8px;padding:24px;'><div style='font-size:14px;color:#1A1610;'>{twitter}</div></div>", unsafe_allow_html=True)
                    st.download_button("📋 Copy", twitter, "twitter.txt", "text/plain")

                elif "Facebook" in platform:
                    facebook = extract_section(story, "FACEBOOK")
                    st.markdown(f"<div style='background:#FFFFFF;border:1px solid #E8E2D4;border-radius:8px;padding:24px;'><div style='font-size:14px;color:#1A1610;line-height:1.7;'>{facebook}</div></div>", unsafe_allow_html=True)
                    st.download_button("📋 Copy", facebook, "facebook.txt", "text/plain")

                st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
                if st.button("✏️  Regenerate Story", key="regen"):
                    del st.session_state.story_output
                    st.rerun()