"""
4_Court_Chart.py
------------------------
Serve Placement Court Chart
Sinner vs Alcaraz
"""

import hashlib
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import sys

# ==========================================
# 1. GEOMETRIC CONSTANTS
# ==========================================
COURT_WIDTH   = 8.23   # Singles boundary width
DOUBLES_WIDTH = 10.97  # Doubles boundary width (Alleys)
HALF_LEN      = 11.885
SVC_LEN       = 6.40
THIRD         = (COURT_WIDTH / 2) / 3
MARGIN_X      = 0.04
MARGIN_Y      = 0.08
SIGMA_X       = THIRD * 0.28
DEPTH_OFFSET  = 0.60
DEPTH_RANGE   = 1.0 - DEPTH_OFFSET
NET_DEPTH     = -0.85  # Middleground net height (between -0.5 and -1.2)

# ==========================================
# 2. OUTCOME STYLE
# ==========================================
OUTCOME_COLOR = {
    "ace":    "#18C05E",   # Green
    "winner": "#FFCC00",   # Yellow
    "lost":   "#D8321F",   # Red
}
OUTCOME_LABEL = {
    "ace":    "Ace",
    "winner": "Winner",
    "lost":   "Lost",
}
OUTCOME_SIZE = {
    "ace":    12,
    "winner": 12,
    "lost":    12,
}
SERVE_OPACITY = {1: 0.90, 2: 0.90}

# ==========================================
# 3. SAMPLING HELPERS
# ==========================================
def stable_seed(row_id) -> int:
    return int(hashlib.md5(str(row_id).encode()).hexdigest(), 16) % (2**31)

def _cx(side: str, direction: str) -> float:
    if side == "Deuce":
        mapping = {
            "down_the_T": (0 + THIRD) / 2,
            "body":        (THIRD + 2 * THIRD) / 2,
            "out_wide":    (2 * THIRD + COURT_WIDTH / 2) / 2,
        }
    else:
        mapping = {
            "down_the_T": (-THIRD + 0) / 2,
            "body":        (-2 * THIRD + -THIRD) / 2,
            "out_wide":    (-COURT_WIDTH / 2 + -2 * THIRD) / 2,
        }
    return mapping.get(direction, 0.0)

CENTROIDS_X = {
    (side, direction): _cx(side, direction)
    for side in ("Deuce", "Ad")
    for direction in ("down_the_T", "body", "out_wide")
}

def _sample_depth(rng) -> float:
    raw  = rng.beta(5, 2)
    norm = DEPTH_OFFSET + DEPTH_RANGE * raw
    return float(np.clip(norm * SVC_LEN, MARGIN_Y, SVC_LEN - MARGIN_Y))

def _ellipse_guard(x, y, cx, cy, rx, ry):
    dx = (x - cx) / rx
    dy = (y - cy) / ry
    dist = dx**2 + dy**2
    if dist <= 1.0:
        return x, y
    scale = 1.0 / np.sqrt(dist)
    return cx + dx * rx * scale, cy + dy * ry * scale

def get_serve_coords(direction: str, side: str, row_id=0):
    rng = np.random.default_rng(stable_seed(row_id))
    y   = _sample_depth(rng)
    cx  = CENTROIDS_X.get((side, direction), 0.0)

    if side == "Deuce":
        x_bounds = {
            "down_the_T": (0, THIRD),
            "body":        (THIRD, 2 * THIRD),
            "out_wide":    (2 * THIRD, COURT_WIDTH / 2), 
        }
    else:
        x_bounds = {
            "down_the_T": (-THIRD, 0),
            "body":        (-2 * THIRD, -THIRD),
            "out_wide":    (-COURT_WIDTH / 2, -2 * THIRD),
        }
    x_min, x_max = x_bounds.get(direction, (-COURT_WIDTH / 2, COURT_WIDTH / 2))

    for _ in range(15):
        x = rng.normal(cx, SIGMA_X)
        if x_min + MARGIN_X <= x <= x_max - MARGIN_X:
            break
    else:
        x = float(np.clip(cx, x_min + MARGIN_X, x_max - MARGIN_X))

    cy_modal = (DEPTH_OFFSET + DEPTH_RANGE * (5 / 8)) * SVC_LEN
    rx = (x_max - x_min) * 0.52
    ry = DEPTH_RANGE * SVC_LEN * 0.54
    x, y = _ellipse_guard(x, y, cx, cy_modal, rx, ry)

    x = float(np.clip(x, x_min + MARGIN_X, x_max - MARGIN_X))
    y = float(np.clip(y, MARGIN_Y, SVC_LEN - MARGIN_Y))
    return x, y

# ==========================================
# 4. COURT GENERATION (ALL LAYERED BELOW DATA)
# ==========================================
CLAY  = "#C76057"
NET   = "#1a1a1a"
WHITE = "white"
DASHED = dict(color="rgba(255,255,255,0.45)", width=1, dash="dash")

def court_shapes() -> list[dict]:
    W2 = COURT_WIDTH / 2
    DW2 = DOUBLES_WIDTH / 2
    
    shapes = [
        # Clay bounds background box
        dict(type="rect", x0=-DW2, x1=DW2, y0=0, y1=HALF_LEN,
             fillcolor=CLAY, line_width=0, layer="below"),
        # Outer boundary lines (Doubles lines)
        dict(type="rect", x0=-DW2, x1=DW2, y0=0, y1=HALF_LEN,
             fillcolor="rgba(0,0,0,0)", line=dict(color=WHITE, width=2.5), layer="below"),
        # Inner vertical guidelines (Singles lines)
        dict(type="line", x0=-W2, x1=-W2, y0=0, y1=HALF_LEN, line=dict(color=WHITE, width=2), layer="below"),
        dict(type="line", x0=W2, x1=W2, y0=0, y1=HALF_LEN, line=dict(color=WHITE, width=2), layer="below"),
        # Horizontal Service line separator
        dict(type="line", x0=-W2, x1=W2, y0=SVC_LEN, y1=SVC_LEN, line=dict(color=WHITE, width=2), layer="below"),
        # Center Service line line
        dict(type="line", x0=0, x1=0, y0=0, y1=SVC_LEN, line=dict(color=WHITE, width=2), layer="below"),
    ]
    
    # Target zone indicators (dashed vertical grids)
    for sign in (1, -1):
        for k in (1, 2):
            shapes.append(dict(
                type="line",
                x0=sign * k * THIRD, x1=sign * k * THIRD,
                y0=0, y1=SVC_LEN,
                line=DASHED,
                layer="below"
            ))
            
    # ── TENNIS NET IMPLEMENTATION ──
    # Net drop-shadow background backing box (Using CLAY color)
    shapes.append(dict(
        type="rect", x0=-DW2-0.2, x1=DW2+0.2, y0=NET_DEPTH, y1=0,
        fillcolor=CLAY, line_width=0, layer="below"
    ))
    
    # Mesh structure cross-hatching (Dense vertical cords)
    for x_pos in np.linspace(-DW2-0.2, DW2+0.2, 85):
        shapes.append(dict(
            type="line", x0=x_pos, x1=x_pos, y0=NET_DEPTH, y1=0,
            line=dict(color="rgba(255,255,255,0.25)", width=1), layer="below"
        ))
        
    # Mesh structure cross-hatching (Horizontal cords)
    for y_pos in np.linspace(NET_DEPTH, 0, 9):
        shapes.append(dict(
            type="line", x0=-DW2-0.2, x1=DW2+0.2, y0=y_pos, y1=y_pos,
            line=dict(color="rgba(255,255,255,0.25)", width=1), layer="below"
        ))
        
    # Bottom grounding line cable & dual ground anchor posts
    shapes.append(dict(type="line", x0=-DW2-0.2, x1=DW2+0.2, y0=NET_DEPTH, y1=NET_DEPTH, line=dict(color="rgba(0,0,0,0.6)", width=2.5), layer="below"))
    shapes.append(dict(type="line", x0=-DW2-0.15, x1=-DW2-0.15, y0=NET_DEPTH, y1=0.1, line=dict(color="#333333", width=6), layer="below"))
    shapes.append(dict(type="line", x0=DW2+0.15, x1=DW2+0.15, y0=NET_DEPTH, y1=0.1, line=dict(color="#333333", width=6), layer="below"))
    
    # Clean White Top Net Strap Canvas
    shapes.append(dict(
        type="rect", x0=-DW2-0.2, x1=DW2+0.2, y0=-0.08, y1=0.02,
        fillcolor="white", line_width=0, layer="below"
    ))
    
    return shapes

def court_annotations() -> list[dict]:
    labels = []
    W2 = COURT_WIDTH / 2
    zone_centers = {
        "T":    (THIRD / 2,             0.40),
        "Body": (THIRD + THIRD / 2,     0.40),
        "Wide": (2 * THIRD + THIRD / 2, 0.40),
    }
    for name, (cx, cy) in zone_centers.items():
        for sign in (1, -1):
            labels.append(dict(
                x=sign * cx, y=cy,
                text=f"<b>{name}</b>",
                showarrow=False,
                # Bumped up from size 8 to size 12, slightly brighter
                font=dict(color="rgba(255,255,255,0.65)", size=12, family="monospace"),
                xanchor="center",
            ))
    for sign, side_label in ((1, "DEUCE"), (-1, "AD")):
        labels.append(dict(
            x=sign * W2 / 2, y=SVC_LEN + 0.5,
            text=f"<b>{side_label}</b>",
            showarrow=False,
            # Bumped up from size 10 to size 14, slightly brighter
            font=dict(color="rgba(255,255,255,0.85)", size=14, family="monospace"),
            xanchor="center",
        ))
    return labels

# ==========================================
# 5. CLASSIFY OUTCOME
# ==========================================
def classify_outcome(row: pd.Series) -> str:
    if row.get("is_ace", False):
        return "ace"
    if row.get("is_winner_pt", False) or row.get("point_winner_name") == row.get("server_name"):
        return "winner"
    return "lost"

# ==========================================
# 6. BUILD PLOTLY LAYOUT
# ==========================================
def build_figure(df: pd.DataFrame) -> go.Figure:
    players = ["Sinner", "Alcaraz"]

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=players,
        horizontal_spacing=0.06,
    )

    for col_idx in (1, 2):
        for shape in court_shapes():
            s = dict(shape)
            s["xref"] = f"x{col_idx}"
            s["yref"] = f"y{col_idx}"
            fig.add_shape(**s)

    for col_idx, player in enumerate(players, start=1):
        for ann in court_annotations():
            a = dict(ann)
            a["xref"] = f"x{col_idx}"
            a["yref"] = f"y{col_idx}"
            fig.add_annotation(**a)

    legend_seen: set = set()

    for col_idx, player in enumerate(players, start=1):
        sub_player = df[df["server_name"] == player]

        for outcome in ["ace", "winner", "lost"]:
            for serve_num in [1, 2]:
                group = sub_player[
                    (sub_player["outcome"] == outcome) &
                    (sub_player["serve_number"] == serve_num)
                ]
                if group.empty:
                    continue

                color   = OUTCOME_COLOR[outcome]
                size    = OUTCOME_SIZE[outcome]
                opacity = SERVE_OPACITY[serve_num]
                label   = f"{OUTCOME_LABEL[outcome]} ({'1°' if serve_num == 1 else '2°'})"
                show_leg = label not in legend_seen

                xs, ys, hovers = [], [], []
                for _, row in group.iterrows():
                    x, y = get_serve_coords(
                        row["serve_direction"], row["court_side"], row.name
                    )
                    xs.append(x)
                    ys.append(y)
                    hovers.append(
                        f"<b>{player}</b><br>"
                        f"Set {row.get('set_number', '?')}<br>"
                        f"Dir: {row['serve_direction'].replace('_', ' ')}<br>"
                    )

                fig.add_trace(
                    go.Scatter(
                        x=xs, y=ys,
                        mode="markers",
                        name=label,
                        legendgroup=label,
                        showlegend=show_leg,
                        marker=dict(
                            symbol="circle",
                            size=size,
                            color=color,
                            opacity=opacity,
                            line=dict(color="black", width=0.6),
                        ),
                        hovertemplate="%{customdata}<extra></extra>",
                        customdata=hovers,
                    ),
                    row=1, col=col_idx,
                )
                if show_leg:
                    legend_seen.add(label)

    DW2 = DOUBLES_WIDTH / 2
    fig.update_xaxes(range=[-(DW2 + 0.6), DW2 + 0.6], visible=False)
    fig.update_yaxes(range=[NET_DEPTH - 0.3, HALF_LEN + 0.8], visible=False)

    fig.update_layout(
        showlegend=False,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(color="#1e1e2e", family="monospace"),
        height=700,                       
        margin=dict(l=10, r=10, t=35, b=10), 
        hoverlabel=dict(
            bgcolor="#ffffff", font_size=12,
            font_family="monospace",
            font_color="#1e1e2e",
            bordercolor="rgba(255,255,255,0.3)",
        ),
    )


    for ann in fig.layout.annotations:
        if ann.text in players:
            ann.font = dict(color="#1e1e2e", size=16, family="monospace", weight="bold")

    return fig

# ==========================================
# 7. DATA PREPARATION
# ==========================================
def prepare_df(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()
    if "serve_number_played" in df.columns and "serve_number" not in df.columns:
        df = df.rename(columns={"serve_number_played": "serve_number"})
    if "court_side" not in df.columns:
        df["court_side"] = np.where(df.index % 2 == 0, "Deuce", "Ad")
    if "serve_number" not in df.columns:
        df["serve_number"] = 1
    if "set_number" not in df.columns:
        df["set_number"] = 1
    df = df.dropna(subset=["serve_direction"])
    df["outcome"] = df.apply(classify_outcome, axis=1)
    return df

def make_synthetic_df(n: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    players = ["Sinner", "Alcaraz"]
    directions = ["down_the_T", "body", "out_wide"]
    sides = ["Deuce", "Ad"]
    rows = []
    for i in range(n):
        player    = rng.choice(players)
        direction = rng.choice(directions)
        side      = rng.choice(sides)
        serve_num = rng.choice([1, 2], p=[0.65, 0.35])
        set_num   = rng.choice([1, 2, 3, 4, 5])
        r = rng.random()
        is_ace    = bool(r < 0.08)
        is_winner = bool((not is_ace) and r > 0.55)
        pt_winner = player if (is_ace or is_winner) else (
            "Sinner" if player == "Alcaraz" else "Alcaraz"
        )
        rows.append(dict(
            server_name=player, serve_direction=direction, court_side=side,
            serve_number=serve_num, set_number=set_num,
            is_ace=is_ace, is_winner_pt=is_winner,
            point_winner_name=pt_winner,
        ))
    return pd.DataFrame(rows)

# ==========================================
# 8. STREAMLIT APP ENGINE
# ==========================================
DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "sinner_alcaraz_2025.parquet"

try:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.data_management.loader import load_and_clean
    _RAW_DF = load_and_clean(DATA_PATH)
except Exception:
    traceback.print_exc()
    _RAW_DF = make_synthetic_df(300)

_DF = prepare_df(_RAW_DF)

st.set_page_config(page_title="RG25 – Serve Chart", layout="wide")

st.markdown(
    """
    <h1 style='text-align:center;color:#2C3E50;'>
    Serve Placement - Court Distribution Plot
    </h1>
    <p style='text-align:center;color:#7F8C8D;'>
    Explore Sinner and Alcaraz's serve map at Roland Garros. Filter the data by set, 
    court side, or outcome to compare the two champions' serving strategies and see 
    exactly where they hit in the crucial moments.
    </p>
    """,
    unsafe_allow_html=True,
)

col_f1, col_f2, col_f3, col_f4 = st.columns(4)
sets_available = sorted(_DF["set_number"].dropna().unique().tolist())

with col_f1:
    st.selectbox(
        "Set",
        options=["all"] + sets_available,
        format_func=lambda x: "All sets" if x == "all" else f"Set {x}",
        key="sel_set"
    )

with col_f2:
    st.selectbox(
        "Court Side",
        options=["all", "Deuce", "Ad"],
        format_func=lambda x: {
            "all": "Deuce + Ad",
            "Deuce": "Deuce",
            "Ad": "Ad",
        }[x],
        key="sel_side"
    )

with col_f3:
    st.selectbox(
        "Serve",
        options=["all", 1, 2],
        format_func=lambda x: {
            "all": "1st + 2nd",
            1: "1st serve only",
            2: "2nd serve only",
        }[x],
        key="sel_serve"
    )

with col_f4:
    st.multiselect(
        "Outcome",
        options=["ace", "winner", "lost"],
        default=["ace", "winner", "lost"],
        format_func=lambda x: {
            "ace":    "🟢 Ace",
            "winner": "🟡 Winner",
            "lost":   "🔴 Lost",
        }[x],
        key="sel_outcomes"
    )

dff = _DF.copy()

if st.session_state.sel_set != "all":
    dff = dff[dff["set_number"] == st.session_state.sel_set]
if st.session_state.sel_side != "all":
    dff = dff[dff["court_side"] == st.session_state.sel_side]
if st.session_state.sel_serve != "all":
    dff = dff[dff["serve_number"] == st.session_state.sel_serve]
if st.session_state.sel_outcomes:
    dff = dff[dff["outcome"].isin(st.session_state.sel_outcomes)]

fig = build_figure(dff)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown("---")
mc1, mc2, mc3 = st.columns(3)

for col, player in zip([mc1, mc2], ["Sinner", "Alcaraz"]):
    sub = dff[dff["server_name"] == player]
    n   = len(sub)
    aces = sub["outcome"].eq("ace").sum()
    pct  = sub["outcome"].isin(["ace","winner"]).sum() / n * 100 if n else 0
    col.metric(
        label=player,
        value=f"{n} serves",
        delta=f"{aces} aces · {pct:.0f}% points won",
    )

mc3.metric("Total serves (filtered)", len(dff))

with st.expander("Show raw data"):
    st.dataframe(dff, use_container_width=True)