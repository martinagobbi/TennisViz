import hashlib
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import sys

# 1. GEOMETRIC CONSTANTS

COURT_WIDTH = 8.23
HALF_LEN    = 11.885
SVC_LEN     = 6.40
THIRD       = (COURT_WIDTH / 2) / 3
MARGIN_X    = 0.04
MARGIN_Y    = 0.08
SIGMA_X     = THIRD * 0.28
DEPTH_OFFSET = 0.60
DEPTH_RANGE  = 1.0 - DEPTH_OFFSET

#2. OUTCOME STYLE (color only, same circle shape for everyone)

OUTCOME_COLOR = {
    "ace":    "#18C05E",   # verde
    "winner": "#FFCC00",   # giallo
    "lost":   "#D8321F",   # rosso
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

# 3. SAMPLING

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


# 4. COURT SHAPES

CLAY  = "#C76057"
NET   = "#1a1a1a"
WHITE = "white"
DASHED = dict(color="rgba(255,255,255,0.40)", width=1, dash="dash")


def court_shapes() -> list[dict]:
    W2 = COURT_WIDTH / 2
    shapes = [
        dict(type="rect", x0=-W2, x1=W2, y0=0, y1=HALF_LEN,
             fillcolor=CLAY, line_width=0, layer="below"),
        dict(type="rect", x0=-W2, x1=W2, y0=0, y1=HALF_LEN,
             fillcolor="rgba(0,0,0,0)", line=dict(color=WHITE, width=2.5)),
        dict(type="line", x0=-W2, x1=W2, y0=SVC_LEN, y1=SVC_LEN,
             line=dict(color=WHITE, width=2)),
        dict(type="line", x0=0, x1=0, y0=0, y1=SVC_LEN,
             line=dict(color=WHITE, width=2)),
        dict(type="line", x0=-W2, x1=W2, y0=0, y1=0,
             line=dict(color=NET, width=4)),
        dict(type="line", x0=-W2 - 0.12, x1=-W2 - 0.12, y0=0, y1=1.0,
             line=dict(color=NET, width=5)),
        dict(type="line", x0=W2 + 0.12, x1=W2 + 0.12, y0=0, y1=1.0,
             line=dict(color=NET, width=5)),
    ]
    for sign in (1, -1):
        for k in (1, 2):
            shapes.append(dict(
                type="line",
                x0=sign * k * THIRD, x1=sign * k * THIRD,
                y0=0, y1=SVC_LEN,
                line=DASHED,
            ))
    return shapes


def court_annotations(x_offset: float = 0) -> list[dict]:
    """Zone + side labels. x_offset shifts everything for subplot coordinates."""
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
                font=dict(color="rgba(255,255,255,0.50)", size=8, family="monospace"),
                xanchor="center",
            ))
    for sign, side_label in ((1, "DEUCE"), (-1, "AD")):
        labels.append(dict(
            x=sign * W2 / 2, y=SVC_LEN + 0.5,
            text=f"<b>{side_label}</b>",
            showarrow=False,
            font=dict(color="rgba(255,255,255,0.65)", size=10, family="monospace"),
            xanchor="center",
        ))
    return labels


# 5. CLASSIFY OUTCOME

def classify_outcome(row: pd.Series) -> str:
    if row.get("is_ace", False):
        return "ace"
    if row.get("is_winner_pt", False) or row.get("point_winner_name") == row.get("server_name"):
        return "winner"
    return "lost"


# 6. BUILD FIGURE (two side-by-side courts)

def build_figure(df: pd.DataFrame) -> go.Figure:
    players = ["Sinner", "Alcaraz"]

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=players,
        horizontal_spacing=0.06,
    )

    # Add court shapes to both subplots
    for col_idx in (1, 2):
        for shape in court_shapes():
            s = dict(shape)
            s["xref"] = f"x{col_idx}"
            s["yref"] = f"y{col_idx}"
            fig.add_shape(**s)

    # Add zone annotations
    for col_idx, player in enumerate(players, start=1):
        for ann in court_annotations():
            a = dict(ann)
            a["xref"] = f"x{col_idx}"
            a["yref"] = f"y{col_idx}"
            fig.add_annotation(**a)

    # One trace per (outcome, serve_number) — same for both players
    # showlegend only on col 1 to avoid duplicates
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
                        # f"Outcome: <b>{outcome}</b> · {serve_num}° serve"
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

    W2 = COURT_WIDTH / 2
    axis_common = dict(
        range=[-(W2 + 0.7), W2 + 0.7],
        visible=False,
        scaleanchor=None,
    )
    y_range = [-0.6, HALF_LEN + 1.4]

    fig.update_xaxes(range=[-(W2 + 0.7), W2 + 0.7], visible=False)
    fig.update_yaxes(range=y_range, visible=False)

    # Keep aspect ratio square for each subplot
    fig.update_layout(
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="#1e1e2e",
        font=dict(color="white", family="monospace"),
        height=700,
        margin=dict(l=10, r=10, t=60, b=10),
        # legend=dict(
        #     orientation="h",
        #     x=0.5, xanchor="center",
        #     y=-0.04, yanchor="top",
        #     bgcolor="rgba(30,30,46,0.85)",
        #     bordercolor="rgba(255,255,255,0.2)",
        #     borderwidth=1,
        #     font=dict(size=11, color="white"),
        #     traceorder="normal",
        # ),
        hoverlabel=dict(
            bgcolor="#1e1e2e", font_size=12,
            font_family="monospace",
            bordercolor="rgba(255,255,255,0.3)",
        ),
    )

    # Subplot titles styling
    for ann in fig.layout.annotations:
        ann.font = dict(color="white", size=14, family="monospace")

    return fig


# 7. DATA PREPARATION

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
    players    = ["Sinner", "Alcaraz"]
    directions = ["down_the_T", "body", "out_wide"]
    sides      = ["Deuce", "Ad"]
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


# 8. STREAMLIT APP

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "sinner_alcaraz_2025.parquet"

try:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.data.loader import load_and_clean
    _RAW_DF = load_and_clean(DATA_PATH)
except Exception:
    traceback.print_exc()
    _RAW_DF = make_synthetic_df(300)

_DF = prepare_df(_RAW_DF)

# Page config
st.set_page_config(page_title="RG25 – Serve Chart", layout="wide")

st.markdown(
    """
    <h1 style='text-align:center;color:black;'>
    🎾 Court Distribution Plot · Sinner vs Alcaraz
    </h1>
    <p style='text-align:center;color:#AAAAAA;'>
    Explore Sinner and Alcaraz's serve map at Roland Garros. Filter the data by set, 
    court side, or outcome to compare the two champions' serving strategies and see 
    exactly where they hit in the crucial moments.
    </p>
    """,
    unsafe_allow_html=True,
)

# ── Filters (dropdowns, horizontal row) ────────────────────────────────────────
col_f1, col_f2, col_f3, col_f4 = st.columns(4)

sets_available = sorted(_DF["set_number"].dropna().unique().tolist())

with col_f1:
    sel_set = st.selectbox(
        "Set",
        options=["all"] + sets_available,
        format_func=lambda x: "All sets" if x == "all" else f"Set {x}",
    )

with col_f2:
    sel_side = st.selectbox(
        "Court Side",
        options=["all", "Deuce", "Ad"],
        format_func=lambda x: {
            "all": "Deuce + Ad",
            "Deuce": "Deuce",
            "Ad": "Ad",
        }[x],
    )

with col_f3:
    sel_serve = st.selectbox(
        "Serve",
        options=["all", 1, 2],
        format_func=lambda x: {
            "all": "1st + 2nd",
            1: "1st serve only",
            2: "2nd serve only",
        }[x],
    )

with col_f4:
    sel_outcomes = st.multiselect(
        "Outcome",
        options=["ace", "winner", "lost"],
        default=["ace", "winner", "lost"],
        format_func=lambda x: {
            "ace":    "🟢 Ace",
            "winner": "🟡 Winner",
            "lost":   "🔴 Lost",
        }[x],
    )

# ── Apply filters ──────────────────────────────────────────────────────────────
dff = _DF.copy()

if sel_set != "all":
    dff = dff[dff["set_number"] == sel_set]
if sel_side != "all":
    dff = dff[dff["court_side"] == sel_side]
if sel_serve != "all":
    dff = dff[dff["serve_number"] == sel_serve]
if sel_outcomes:
    dff = dff[dff["outcome"].isin(sel_outcomes)]

# ── Chart ─────────────────────────────────────────────────────────────────────
fig = build_figure(dff)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ── Summary metrics ───────────────────────────────────────────────────────────
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
# ── Optional raw table ────────────────────────────────────────────────────────
with st.expander("Show raw data"):
    st.dataframe(dff, use_container_width=True)