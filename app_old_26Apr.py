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
         "⭐  Rate Photos"],
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
    st.markdown("""
    <h1 style='font-family:"Cormorant Garamond",serif;font-size:36px;
               font-weight:700;color:#1A1610;letter-spacing:-0.02em;
               margin-bottom:2px;'>
        Your Photo Intelligence Dashboard
    </h1>""", unsafe_allow_html=True)

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

    # Load trip data
    session = get_session()
    photos = session.query(Photo).filter(Photo.trip_id == active_trip.id).all()
    session.close()

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

    # ── ROW 1: Stat Strip ──────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    for col, val, label, note, color in [
        (c1, str(total), "Total Photos", "Nikon NEF · RAW files", INK),
        (c2, str(greats + goods), "Good — Keepers", f"{keep_rate:.0f}% keep rate this trip", AMBER),
        (c3, str(reviews), "Need Your Review", "Borderline — your call", SKY),
        (c4, f"{avg_score:.1f}", "Session Average Score", "Out of 100", FOREST),
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
    best_photo = max(scored, key=lambda p: p.composite_score) if scored else None
    best_name = best_photo.filename.replace(".NEF", "").replace(".nef", "") if best_photo else "—"
    best_score = best_photo.composite_score if best_photo else 0

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
    elif len(cat_data) == 1:
        cat_name = list(cat_data.keys())[0]
        cat_avg = round(sum(cat_data[cat_name]["scores"]) / len(cat_data[cat_name]["scores"]), 1) if cat_data[cat_name]["scores"] else 0
        cat_summary = f"All photos are <strong>{cat_name}</strong> · average score {cat_avg}."

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

    # ── ROW 3: Top 5 Filmstrip + Donut ────────────────────────────────
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
        )[:5]

        if top_photos:
            tier_colors = {"great": "#2D5016", "good": "#C87020", "review": "#2060A0", "delete": "#C8BEA8"}
            frames_html = ""
            for photo in top_photos:
                src = thumb_src(photo.thumbnail_path)
                score = photo.composite_score or 0
                t_color = tier_colors.get(photo.tier, "#C8BEA8")
                fname = photo.filename[:8]
                frames_html += f"""
                <div style='flex:1;position:relative;border-radius:6px;
                            overflow:hidden;border:1px solid #E8E2D4;
                            aspect-ratio:3/2;'>
                    <img src="{src}" style='width:100%;height:100%;object-fit:cover;display:block;'>
                    <div style='position:absolute;top:6px;right:6px;
                                background:rgba(255,255,255,0.93);
                                backdrop-filter:blur(6px);border-radius:20px;
                                padding:2px 8px;font-family:"DM Mono",monospace;
                                font-size:11px;font-weight:500;color:{t_color};'>
                        {score:.0f}
                    </div>
                    <div style='position:absolute;bottom:0;left:0;right:0;
                                height:3px;background:{t_color};'></div>
                    <div style='position:absolute;bottom:6px;left:6px;
                                font-family:"DM Mono",monospace;font-size:9px;
                                color:rgba(255,255,255,0.85);'>{fname}</div>
                </div>"""

            st.markdown(f"""
            <div style='background:#FFFFFF;border:1px solid #E8E2D4;
                        border-radius:8px;padding:18px;'>
                <div style='font-family:"DM Mono",monospace;font-size:9px;
                            letter-spacing:0.12em;text-transform:uppercase;
                            color:#9A8870;margin-bottom:12px;'>
                    Top {len(top_photos)} · Sorted by Score
                </div>
                <div style='display:flex;gap:8px;'>{frames_html}</div>
                <div style='margin-top:8px;font-size:11px;
                            color:#C8BEA8;font-style:italic;'>
                    Colour bar = tier · Score badge top right
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='background:#FFFFFF;border:1px solid #E8E2D4;
                        border-radius:8px;padding:40px;text-align:center;
                        color:#9A8870;font-size:13px;'>
                No scored photos yet — run AI Scoring in the Gallery first
            </div>
            """, unsafe_allow_html=True)

    with col_donut:
        # Build donut using Plotly
        labels = ['Great', 'Good', 'Review', 'Delete']
        values = [greats, goods, reviews, deletes]
        colors = ['#2D5016', '#C87020', '#7AACCC', '#C8BEA8']
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.6,
            marker=dict(colors=colors),
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
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.05,
                font=dict(size=10, family='DM Mono')
            ),
            paper_bgcolor='#FFFFFF',
            margin=dict(l=20, r=80, t=20, b=20),
            height=300,
        )
        
        st.markdown("**Tier Distribution**")
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
        top_cat_count = cat_data[top_cat_label]["total"] if cat_data else 0
        top_cat_avg = round(sum(cat_data[top_cat_label]["scores"]) / len(cat_data[top_cat_label]["scores"]), 1) if cat_data and cat_data[top_cat_label]["scores"] else 0

        cat_detail_html = " · ".join([
            f'<span style="color:#C8BEA8;">{lbl[:14]} ({data["total"]}) · avg {round(sum(data["scores"])/len(data["scores"]),1) if data["scores"] else 0}</span>'
            for lbl, data in cat_data.items()
        ])

        st.markdown(f"""
        <div style='background:#FFFFFF;border:1px solid #E8E2D4;
                    border-radius:8px;padding:18px;
                    display:flex;flex-direction:column;gap:8px;height:100%;'>
            <div style='display:flex;align-items:center;gap:8px;'>
                <span style='font-size:18px;'>🏷️</span>
                <span style='font-family:"DM Mono",monospace;font-size:8px;
                             letter-spacing:0.12em;text-transform:uppercase;
                             color:#9A8870;'>Top Category by Volume</span>
            </div>
            <div style='font-family:"Cormorant Garamond",serif;
                        font-size:18px;font-weight:700;
                        color:#2060A0;line-height:1.2;'>
                {top_cat_label}
            </div>
            <div style='font-size:11.5px;color:#9A8870;line-height:1.5;'>
                {cat_detail_html}
            </div>
        </div>
        """, unsafe_allow_html=True)

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

    # ── ROW 5: Category vs Benchmark + Export ─────────────────────────
    st.markdown(
        "<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
        "letter-spacing:0.14em;text-transform:uppercase;color:#C8BEA8;"
        "margin-bottom:10px;'>Category Performance vs Benchmark</div>",
        unsafe_allow_html=True
    )

    col_bench, col_export = st.columns([3, 1.2])

    with col_bench:
        st.markdown("""
        <div style='font-family:"DM Mono",monospace;font-size:9px;
                    letter-spacing:0.12em;text-transform:uppercase;
                    color:#9A8870;margin-bottom:14px;'>
            Your Average Score vs Wildlife Photography Benchmark
        </div>
        """, unsafe_allow_html=True)

        for label, data in cat_data.items():
            if not data["scores"]:
                continue
            your_avg = round(sum(data["scores"]) / len(data["scores"]), 1)
            bench = INDUSTRY_BENCHMARKS.get(data["key"], {"avg": 63})["avg"]
            delta = round(your_avg - bench, 1)
            sign = "▲" if delta >= 0 else "▼"
            d_color = "#2D5016" if delta >= 0 else "#A83020"
            count = data["total"]

            st.markdown(f"**{label}** — You: `{your_avg}` · Benchmark: `{bench}`")
            col_y, col_b = st.columns(2)
            with col_y:
                st.progress(int(your_avg))
            with col_b:
                st.progress(int(bench))
            st.markdown(
                f"<div style='text-align:right;font-family:\"DM Mono\","
                f"monospace;font-size:10px;color:{d_color};"
                f"margin-bottom:16px;'>"
                f"{sign} {abs(delta)} pts vs benchmark · {count} photos"
                f"</div>",
                unsafe_allow_html=True
            )

        st.markdown(
            "<div style='font-size:10px;color:#C8BEA8;font-style:italic;'>"
            "Progress bar top = your score · bottom = benchmark (out of 100)"
            "</div>",
            unsafe_allow_html=True
        )

    with col_export:
        edit_tip_html = ""
        if best_photo:
            lr_note = ""
            topaz_note = ""
            if best_photo.edit_suggestions:
                lr_note = best_photo.edit_suggestions.get("lightroom", "")
                topaz_note = best_photo.edit_suggestions.get("topaz", "")
            elif best_photo.exif_iso and best_photo.exif_iso > 3200:
                topaz_note = f"Topaz DeNoise AI (ISO {best_photo.exif_iso:,} detected)"
                lr_note = "Exposure +0.6, Clarity +15"

            edit_tip_html = f"""
            <div style='background:#EEF5E8;border:1px solid #7A9E6A;
                        border-radius:8px;padding:14px;'>
                <div style='font-family:"DM Mono",monospace;font-size:9px;
                            letter-spacing:0.1em;text-transform:uppercase;
                            color:#2D5016;margin-bottom:6px;'>
                    💡 Editing Priority
                </div>
                <div style='font-size:12px;color:#2D5016;line-height:1.6;'>
                    Start with
                    <strong>{best_photo.filename.replace(".NEF","").replace(".nef","")}</strong>
                    — your highest scorer at {best_score:.0f}.<br>
                    {f"<strong>{topaz_note}</strong> first, then " if topaz_note else ""}
                    {lr_note or "Apply standard edits."}
                </div>
            </div>"""

        keeper_count = greats + goods
        keep_photos = [p for p in photos if p.tier in ["great", "good"]]
        
        export_rows = [{
            "Filename": p.filename,
            "Tier": p.tier,
            "Score": p.composite_score,
            "Category": CATEGORY_LABELS.get(p.category, ""),
            "ISO": p.exif_iso,
            "Aperture": p.exif_aperture,
            "Shutter": p.exif_shutter,
            "Focal Length": p.exif_focal_len,
            "LR Edit Notes": (p.edit_suggestions or {}).get("lightroom", ""),
            "Topaz Notes": (p.edit_suggestions or {}).get("topaz", ""),
            "Crop Note": (p.edit_suggestions or {}).get("crop", ""),
        } for p in keep_photos]

        csv_data = pd.DataFrame(export_rows).to_csv(index=False)

        st.markdown(f"""
        <div style='display:flex;flex-direction:column;gap:14px;height:100%;'>
            <div style='background:#FFFFFF;border:1px solid #E8E2D4;
                        border-radius:8px;padding:18px;
                        display:flex;flex-direction:column;gap:10px;'>
                <div style='font-family:"DM Mono",monospace;font-size:9px;
                            letter-spacing:0.12em;text-transform:uppercase;
                            color:#9A8870;'>Quick Export</div>
                <div style='font-family:"Cormorant Garamond",serif;
                            font-size:28px;font-weight:700;color:#2D5016;'>
                    {keeper_count} photos
                </div>
                <div style='font-size:12px;color:#5C5040;line-height:1.5;'>
                    Good-tier keepers ready for Lightroom or Capture One.
                    Includes AI score, edit notes, and category per photo.
                </div>
            </div>
            {edit_tip_html}
        </div>
        """, unsafe_allow_html=True)

        st.download_button(
            "⬇️  Export to Lightroom CSV",
            csv_data,
            f"picker_{active_trip.name.replace(' ','_')}_keepers.csv",
            "text/csv",
            use_container_width=True,
        )

        st.markdown(
            "<div style='font-family:\"DM Mono\",monospace;font-size:9px;"
            "color:#C8BEA8;text-align:center;margin-top:4px;'>"
            "XMP · CSV · Capture One compatible</div>",
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
                max-width:600px;margin-bottom:24px;'>
        <div style='font-family:"DM Mono",monospace;font-size:9px;
                    letter-spacing:0.12em;text-transform:uppercase;
                    color:#9A8870;margin-bottom:16px;'>
            Step 1 of 2 — Trip Details
        </div>
    """, unsafe_allow_html=True)

    trip_name     = st.text_input(
        "Trip Name",
        placeholder="e.g. Ranthambore Tiger Reserve — April 2026"
    )
    trip_location = st.text_input(
        "Location (optional)",
        placeholder="e.g. Rajasthan, India"
    )
    folder_path   = st.text_input(
        "Photo Folder Path",
        placeholder=(
            r"e.g. C:\Photos\Ranthambore2026  or  /Volumes/SD_CARD/DCIM"
        )
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # Preview folder
    if folder_path and os.path.isdir(folder_path):
        from src.services.ingestor import discover_files
        files = discover_files(folder_path)
        st.markdown(f"""
        <div style='background:#EEF5E8;border:1px solid {SAGE};
                    border-radius:6px;padding:14px 18px;
                    max-width:600px;margin-bottom:20px;'>
            <span style='font-family:"DM Mono",monospace;
                         font-size:10px;color:{FOREST};font-weight:500;'>
                ✓ Found {len(files)} photos in this folder
            </span>
        </div>
        """, unsafe_allow_html=True)

        if st.button(
            f"🚀  Begin Processing {len(files)} Photos",
            type="primary"
        ) and trip_name:
            trip_id = str(uuid.uuid4())
            session = get_session()
            trip = Trip(
                id=trip_id,
                name=trip_name,
                location=trip_location,
                folder_path=folder_path,
                photo_count=len(files),
                created_at=datetime.now(),
            )
            session.add(trip)
            session.commit()
            session.close()

            # Ingest
            st.markdown(
                "<h3>Phase 1 — Local Analysis</h3>",
                unsafe_allow_html=True
            )
            prog_bar = st.progress(0)
            status   = st.empty()

            def update_progress(current, total):
                pct = current / total
                prog_bar.progress(pct)
                status.markdown(
                    f"<div style='font-family:\"DM Mono\",monospace;"
                    f"font-size:11px;color:#9A8870;'>"
                    f"Analysing {current:,} / {total:,} photos…"
                    f"</div>",
                    unsafe_allow_html=True
                )

            result = ingest_folder(
                trip_id, folder_path, update_progress
            )
            prog_bar.progress(1.0)
            status.empty()

            # Update trip
            session = get_session()
            t = session.query(Trip).filter(
                Trip.id == trip_id
            ).first()
            if t:
                t.photo_count = result["total"]
            session.commit()
            session.close()

            st.markdown(f"""
            <div style='background:#EEF5E8;border:1px solid {SAGE};
                        border-radius:8px;padding:20px;
                        max-width:600px;margin:16px 0;'>
                <div style='font-family:"Cormorant Garamond",serif;
                            font-size:20px;color:{FOREST};
                            margin-bottom:8px;'>
                    ✓ Local Analysis Complete
                </div>
                <div style='font-family:"DM Sans",sans-serif;
                            font-size:13px;color:#5C5040;'>
                    <strong>{result['ingested']:,}</strong> photos ready
                    for AI scoring ·
                    <strong>{result['skipped']:,}</strong> auto-removed
                    (blurry or duplicate)
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.info(
                "✦ Go to **Gallery** → click **Run AI Scoring** "
                "to score the remaining photos with Claude vision. "
                "This is the slow step — best run overnight for large trips."
            )

    elif folder_path and not os.path.isdir(folder_path):
        st.error("⚠️ Folder not found. Check the path and try again.")

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
    if pending_count > 0:
        st.markdown(f"""
        <div style='background:#FCF0E0;border:1px solid #E8B870;
                    border-radius:8px;padding:18px 22px;
                    margin-bottom:20px;'>
            <strong style='color:{AMBER};'>
                {pending_count:,} photos ready for AI scoring
            </strong>
            <span style='color:#8A4C10;font-size:13px;'>
                — estimated cost: ${pending_count * 0.002:.2f}
                · estimated time: {pending_count // 40} mins
            </span>
        </div>
        """, unsafe_allow_html=True)

        if st.button(
            f"🧠  Run AI Scoring on {pending_count:,} Photos",
            type="primary"
        ):
            prog  = st.progress(0)
            info  = st.empty()

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
                f"Reload the gallery to see results."
            )
            st.rerun()

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

                    # Click to view detail
                    if st.button(
                        "View →",
                        key=f"view_{photo.id}",
                        use_container_width=True
                    ):
                        st.session_state.selected_photo = photo.id
                        st.session_state.page = "Detail"

# ══════════════════════════════════════════════════════════════════════════
# PAGE: RATE PHOTOS (Human Review Queue)
# ══════════════════════════════════════════════════════════════════════════
elif page == "Rate Photos":
    st.markdown(
        "<h1>Rate Your Photos</h1>",
        unsafe_allow_html=True
    )

    if not active_trip:
        st.info("Select a trip first.")
        st.stop()

    session = get_session()
    # Show unrated photos first, then review queue
    to_rate = session.query(Photo).filter(
        Photo.trip_id == active_trip.id,
        Photo.user_rating == None,
        Photo.tier.in_(["great", "good", "review"]),
    ).order_by(Photo.composite_score.desc()).all()
    session.close()

    if not to_rate:
        st.success("✓ All photos rated for this trip!")
        st.stop()

    # Show first unrated photo
    if "rate_idx" not in st.session_state:
        st.session_state.rate_idx = 0

    idx   = st.session_state.rate_idx
    idx   = min(idx, len(to_rate) - 1)
    photo = to_rate[idx]

    # Progress
    rated = len([p for p in to_rate if p.user_rating])
    total = len(to_rate)
    st.progress(idx / max(total, 1))
    st.markdown(
        f"<div style='font-family:\"DM Mono\",monospace;"
        f"font-size:10px;letter-spacing:0.1em;"
        f"text-transform:uppercase;color:#9A8870;"
        f"margin-bottom:20px;'>"
        f"Photo {idx+1:,} of {total:,} · "
        f"Use keyboard: G = Great · O = Good · D = Delete"
        f"</div>",
        unsafe_allow_html=True
    )

    col_img, col_panel = st.columns([1.8, 1])

    with col_img:
        if (photo.thumbnail_path
                and os.path.exists(photo.thumbnail_path)):
            src = thumb_src(photo.thumbnail_path)
            st.markdown(f"""
            <div style='border-radius:8px;overflow:hidden;
                        box-shadow:0 4px 16px rgba(26,22,16,0.12);'>
                <img src="{src}" style='width:100%;display:block;'>
            </div>
            """, unsafe_allow_html=True)

    with col_panel:
        # EXIF strip
        st.markdown(f"""
        <div style='background:#FFFFFF;border:1px solid #E8E2D4;
                    border-radius:8px;padding:16px;margin-bottom:16px;'>
            <div style='font-family:"DM Mono",monospace;font-size:9px;
                        letter-spacing:0.1em;text-transform:uppercase;
                        color:#9A8870;margin-bottom:10px;'>EXIF Data</div>
            <div style='display:grid;grid-template-columns:1fr 1fr;
                        gap:6px;font-family:"DM Mono",monospace;
                        font-size:10px;color:#5C5040;'>
                <div>ISO {photo.exif_iso or "?"}</div>
                <div>f/{photo.exif_aperture or "?"}</div>
                <div>{photo.exif_shutter or "?"}s</div>
                <div>{photo.exif_focal_len or "?"}mm</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # AI scores
        if photo.score_breakdown:
            st.markdown(
                "<div style='font-family:\"DM Mono\",monospace;"
                "font-size:9px;letter-spacing:0.1em;"
                "text-transform:uppercase;color:#9A8870;"
                "margin-bottom:10px;'>AI Score Breakdown</div>",
                unsafe_allow_html=True
            )
            breakdown_html = ""
            for dim, val in photo.score_breakdown.items():
                color = (
                    "forest" if val >= 15 else
                    "amber" if val >= 8 else "rust"
                )
                breakdown_html += score_bar(dim, val, 25, color)
            st.markdown(breakdown_html, unsafe_allow_html=True)

        # AI explanation
        if photo.ai_explanation:
            st.markdown(f"""
            <div style='background:#FAF8F3;border:1px solid #E8E2D4;
                        border-radius:6px;padding:12px;
                        font-family:"DM Sans",sans-serif;
                        font-size:12px;color:#5C5040;
                        line-height:1.6;font-style:italic;
                        margin-bottom:14px;'>
                {photo.ai_explanation}
            </div>
            """, unsafe_allow_html=True)

        # Edit suggestions
        if photo.edit_suggestions:
            with st.expander("✦ Editing Recommendations"):
                edits = photo.edit_suggestions
                if edits.get("lightroom"):
                    st.markdown(
                        f"**Lightroom:** {edits['lightroom']}"
                    )
                if edits.get("topaz"):
                    st.markdown(f"**Topaz:** {edits['topaz']}")
                if edits.get("crop"):
                    st.markdown(f"**Crop:** {edits['crop']}")

        # Rating buttons
        st.markdown("<div style='height:8px'></div>",
                    unsafe_allow_html=True)
        r1, r2, r3, r4 = st.columns(4)

        def rate(rating: str):
            session = get_session()
            p = session.query(Photo).filter(
                Photo.id == photo.id
            ).first()
            if p:
                p.user_rating = rating
                p.rated_at    = datetime.now()
            session.commit()
            session.close()
            st.session_state.rate_idx = idx + 1
            st.rerun()

        with r1:
            if st.button("⭐ Great", use_container_width=True,
                         type="primary"):
                rate("great")
        with r2:
            if st.button("👍 Good", use_container_width=True):
                rate("good")
        with r3:
            if st.button("🗑 Delete", use_container_width=True):
                rate("delete")
        with r4:
            if st.button("→ Skip", use_container_width=True):
                st.session_state.rate_idx = idx + 1
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# PAGE: ANALYTICS (existing code from your file - all sections complete)
# ══════════════════════════════════════════════════════════════════════════
elif page == "Analytics":
    st.markdown("<h1>Trip Analytics</h1>", unsafe_allow_html=True)

    if not active_trip:
        st.info("Select a trip first.")
        st.stop()

    session = get_session()
    photos = session.query(Photo).filter(Photo.trip_id == active_trip.id).all()
    session.close()

    scored_photos = [p for p in photos if p.composite_score is not None and p.composite_score > 0]

    if not scored_photos:
        st.info("No scored photos yet. Run AI scoring first.")
        st.stop()

    # Aggregate data
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

    # ── SECTION 1: Stat Strip ──────────────────────────────────────────
    st.markdown("<div style='font-family:\"DM Mono\",monospace;font-size:9px;letter-spacing:0.14em;text-transform:uppercase;color:#C8BEA8;margin-bottom:10px;'>Session Overview</div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    for col, val, label, note, color in [
        (c1, str(total), "Total Photos", "All NEF RAW files", INK),
        (c2, str(greats + goods), "Good — Keepers", f"{keep_rate:.0f}% keep rate", AMBER),
        (c3, str(reviews), "Need Review", "Your decision needed", SKY),
        (c4, f"{avg_score:.1f}", "Session Average", "Out of 100", FOREST),
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

    st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)

    # ── SECTION 2: Score Definitions ──────────────────────────────────
    st.markdown("<div style='font-family:\"DM Mono\",monospace;font-size:9px;letter-spacing:0.14em;text-transform:uppercase;color:#C8BEA8;margin-bottom:10px;'>What the Scores Mean</div>", unsafe_allow_html=True)
    
    d1, d2, d3, d4 = st.columns(4)
    
    with d1:
        st.markdown("""
        <div style='background:#EEF5E8;border:1px solid #E8E2D4;border-top:3px solid #2D5016;border-radius:8px;padding:16px;height:150px;'>
            <div style='font-family:"DM Mono",monospace;font-size:9px;letter-spacing:0.1em;text-transform:uppercase;color:#2D5016;font-weight:700;margin-bottom:4px;'>✦ GREAT</div>
            <div style='font-family:"Cormorant Garamond",serif;font-size:28px;font-weight:700;color:#2D5016;line-height:1;margin-bottom:8px;'>72–100</div>
            <div style='font-size:11.5px;line-height:1.5;color:#5C5040;'>Publication ready. Technically excellent and emotionally compelling.</div>
        </div>
        """, unsafe_allow_html=True)
    
    with d2:
        st.markdown("""
        <div style='background:#FCF0E0;border:1px solid #E8E2D4;border-top:3px solid #C87020;border-radius:8px;padding:16px;height:150px;'>
            <div style='font-family:"DM Mono",monospace;font-size:9px;letter-spacing:0.1em;text-transform:uppercase;color:#C87020;font-weight:700;margin-bottom:4px;'>GOOD</div>
            <div style='font-family:"Cormorant Garamond",serif;font-size:28px;font-weight:700;color:#C87020;line-height:1;margin-bottom:8px;'>50–71</div>
            <div style='font-size:11.5px;line-height:1.5;color:#5C5040;'>Solid keeper. Minor flaws but worth editing and keeping.</div>
        </div>
        """, unsafe_allow_html=True)
    
    with d3:
        st.markdown("""
        <div style='background:#EEF4FC;border:1px solid #E8E2D4;border-top:3px solid #2060A0;border-radius:8px;padding:16px;height:150px;'>
            <div style='font-family:"DM Mono",monospace;font-size:9px;letter-spacing:0.1em;text-transform:uppercase;color:#2060A0;font-weight:700;margin-bottom:4px;'>REVIEW</div>
            <div style='font-family:"Cormorant Garamond",serif;font-size:28px;font-weight:700;color:#2060A0;line-height:1;margin-bottom:8px;'>30–49</div>
            <div style='font-size:11.5px;line-height:1.5;color:#5C5040;'>Borderline. AI uncertain — you decide.</div>
        </div>
        """, unsafe_allow_html=True)
    
    with d4:
        st.markdown("""
        <div style='background:#FDF0EE;border:1px solid #E8E2D4;border-top:3px solid #A83020;border-radius:8px;padding:16px;height:150px;'>
            <div style='font-family:"DM Mono",monospace;font-size:9px;letter-spacing:0.1em;text-transform:uppercase;color:#A83020;font-weight:700;margin-bottom:4px;'>DELETE</div>
            <div style='font-family:"Cormorant Garamond",serif;font-size:28px;font-weight:700;color:#A83020;line-height:1;margin-bottom:8px;'>0–29</div>
            <div style='font-size:11.5px;line-height:1.5;color:#5C5040;'>Technical issues make this unsuitable for keeping.</div>
        </div>
        """, unsafe_allow_html=True)
    # ── SECTION 4: Score vs Benchmark ─────────────────────────────────
    st.markdown("<div style='font-family:\"DM Mono\",monospace;font-size:9px;letter-spacing:0.14em;text-transform:uppercase;color:#C8BEA8;margin-bottom:10px;'>Your Average Score vs Industry Benchmark</div>", unsafe_allow_html=True)

    if cat_data:
        for label, data in cat_data.items():
            if not data["scores"]:
                continue
            your_avg = round(sum(data["scores"]) / len(data["scores"]), 1)
            bench = INDUSTRY_BENCHMARKS.get(data["key"], {"avg": 63})["avg"]
            delta = round(your_avg - bench, 1)

            st.markdown(f"**{label}** — You: `{your_avg}` · Benchmark: `{bench}`")
            col_y, col_b = st.columns(2)
            with col_y:
                st.progress(int(your_avg))
            with col_b:
                st.progress(int(bench))
            
            sign = "▲" if delta >= 0 else "▼"
            d_color = "#2D5016" if delta >= 0 else "#A83020"
            st.markdown(f"<div style='text-align:right;font-family:\"DM Mono\",monospace;font-size:10px;color:{d_color};margin-bottom:16px;'>{sign} {abs(delta)} pts vs benchmark · {data['total']} photos</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)

    # ── SECTION 5: Dimension Analysis ─────────────────────────────────
    st.markdown("<div style='font-family:\"DM Mono\",monospace;font-size:9px;letter-spacing:0.14em;text-transform:uppercase;color:#C8BEA8;margin-bottom:10px;'>What Drives Your Score — Dimension Analysis</div>", unsafe_allow_html=True)

    col_radar, col_dims = st.columns(2)

    with col_radar:
        dims_ordered = list(DIM_CONFIG.keys())
        your_vals = [dim_avgs.get(d, 50) for d in dims_ordered]
        bench_vals = [68, 55, 52, 62, 62, 60]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=bench_vals + [bench_vals[0]],
            theta=dims_ordered + [dims_ordered[0]],
            fill=None,
            mode="lines",
            line=dict(color="#C8BEA8", width=1.5, dash="dot"),
            name="Benchmark",
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=your_vals + [your_vals[0]],
            theta=dims_ordered + [dims_ordered[0]],
            fill="toself",
            fillcolor="rgba(200,112,32,0.15)",
            mode="lines+markers",
            line=dict(color="#C87020", width=2),
            marker=dict(size=5, color="#C87020"),
            name="Your Score",
        ))
        fig_radar.update_layout(
            polar=dict(
                bgcolor="#FAF8F3",
                radialaxis=dict(visible=True, range=[0, 100], showticklabels=True, tickfont=dict(size=8, color="#9A8870"), gridcolor="#E8E2D4", linecolor="#E8E2D4"),
                angularaxis=dict(tickfont=dict(size=9, family="DM Mono", color="#5C5040"), gridcolor="#E8E2D4", linecolor="#E8E2D4"),
            ),
            showlegend=True,
            legend=dict(font=dict(family="DM Mono", size=10, color="#5C5040"), orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
            plot_bgcolor="#FAF8F3",
            paper_bgcolor="#FFFFFF",
            margin=dict(l=40, r=40, t=20, b=40),
            height=340,
        )
        st.markdown("<div style='background:#FFFFFF;border:1px solid #E8E2D4;border-radius:8px;padding:16px 16px 4px;'><div style='font-family:\"DM Mono\",monospace;font-size:9px;letter-spacing:0.12em;text-transform:uppercase;color:#9A8870;margin-bottom:4px;'>Average Score per Dimension — This Session</div>", unsafe_allow_html=True)
        st.plotly_chart(fig_radar, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_dims:
        st.markdown("<div style='background:#FFFFFF;border:1px solid #E8E2D4;border-radius:8px;padding:20px;'><div style='font-family:\"DM Mono\",monospace;font-size:9px;letter-spacing:0.12em;text-transform:uppercase;color:#9A8870;margin-bottom:14px;'>Dimension Scores — What to Focus On</div>", unsafe_allow_html=True)
        
        sorted_dims = sorted(DIM_CONFIG.items(), key=lambda x: dim_avgs.get(x[0], 50), reverse=True)
        for dim, cfg in sorted_dims:
            val = dim_avgs.get(dim, 50)
            st.markdown(f"**{dim}** — `{val:.0f}/100`")
            st.progress(int(val))
            st.markdown(f"<div style='font-size:10px;color:{cfg['note_color']};margin-bottom:12px;'>{cfg['note']}</div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)

    # ── SECTION 6: Detailed Table ──────────────────────────────────────
    st.markdown("<div style='font-family:\"DM Mono\",monospace;font-size:9px;letter-spacing:0.14em;text-transform:uppercase;color:#C8BEA8;margin-bottom:10px;'>Detailed Breakdown — All Categories</div>", unsafe_allow_html=True)

    if cat_data:
        table_rows = []
        for label, data in cat_data.items():
            t = max(data["total"], 1)
            your_avg = round(sum(data["scores"]) / len(data["scores"]), 1) if data["scores"] else 0
            bench = INDUSTRY_BENCHMARKS.get(data["key"], {"avg": 63})["avg"]
            delta = round(your_avg - bench, 1)
            keep = round((data["great"] + data["good"]) / t * 100)
            table_rows.append({
                "Category": label,
                "Total": data["total"],
                "Great ✦": data["great"],
                "Good": data["good"],
                "Review": data["review"],
                "Delete": data["delete"],
                "Keep %": f"{keep}%",
                "Avg Score": f"{your_avg}",
                "Benchmark": str(bench),
                "vs Bench": f"{'+' if delta>=0 else ''}{delta}",
            })

        total_your = round(avg_score, 1)
        table_rows.append({
            "Category": "Total / Session",
            "Total": total,
            "Great ✦": greats,
            "Good": goods,
            "Review": reviews,
            "Delete": deletes,
            "Keep %": f"{keep_rate:.0f}%",
            "Avg Score": f"{total_your}",
            "Benchmark": "–",
            "vs Bench": "–",
        })

        df_table = pd.DataFrame(table_rows)
        st.dataframe(df_table, use_container_width=True, hide_index=True)

    st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)

    # ── SECTION 7: Export ──────────────────────────────────────────────
    st.markdown("<div style='font-family:\"DM Mono\",monospace;font-size:9px;letter-spacing:0.14em;text-transform:uppercase;color:#C8BEA8;margin-bottom:10px;'>Export</div>", unsafe_allow_html=True)

    rows = [{
        "Filename": p.filename,
        "Tier": p.tier,
        "Score": p.composite_score,
        "Category": CATEGORY_LABELS.get(p.category, ""),
        "User Rating": p.user_rating or "",
        "ISO": p.exif_iso,
        "Aperture": p.exif_aperture,
        "Shutter": p.exif_shutter,
        "Focal Length": p.exif_focal_len,
        "AI Explanation": p.ai_explanation or "",
        "LR Edit Notes": (p.edit_suggestions or {}).get("lightroom", ""),
        "Topaz Notes": (p.edit_suggestions or {}).get("topaz", ""),
        "Crop Note": (p.edit_suggestions or {}).get("crop", ""),
    } for p in photos]

    df_export = pd.DataFrame(rows)
    csv = df_export.to_csv(index=False)

    st.markdown("""
    <div style='background:#FFFFFF;border:1px solid #E8E2D4;border-radius:8px;
                padding:18px 22px;display:flex;align-items:center;
                justify-content:space-between;gap:20px;'>
        <div style='font-size:13px;color:#5C5040;line-height:1.6;'>
            Full trip report — score, tier, category, edit recommendations,
            and EXIF data per photo.<br>
            Compatible with <strong>Lightroom</strong>, <strong>Capture One</strong>,
            and <strong>darktable</strong>.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.download_button(
        "⬇️  Export Full Trip Report CSV",
        csv,
        f"picker_{active_trip.name.replace(' ','_')}.csv",
        "text/csv",
    )
