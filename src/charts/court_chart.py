"""
serve_viz_interactive.py
------------------------
Roland Garros 2025 – Analisi Servizi Interattiva
Sinner vs Alcaraz

Sostituisce il vecchio plot matplotlib con una Dash app interattiva che:
  1. Disegna mezzo campo in Plotly (SVG shapes, niente matplotlib)
  2. Usa distribuzioni gaussiane attorno a centroidi stabili (seed fisso per punto)
  3. Permette di filtrare per set, lato (Deuce/Ad), giocatore
  4. Distingue con colore (giocatore) + simbolo (esito) + dimensione (1° / 2° servizio)

Avvio:
    pip install dash plotly pandas numpy
    python serve_viz_interactive.py
"""

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import sys
import traceback

# ─────────────────────────────────────────────
# 1.  COSTANTI GEOMETRICHE (metri)
# ─────────────────────────────────────────────
COURT_WIDTH = 8.23        # larghezza singolo
HALF_LEN    = 11.885      # lunghezza mezzo campo (rete → baseline)
SVC_LEN     = 6.40        # rete → service line

THIRD = (COURT_WIDTH / 2) / 3   # ≈ 1.372 m  (ampiezza di ciascuna delle 3 zone)

# ─────────────────────────────────────────────
# 2.  CENTROIDI X  (solo orizzontale; la profondità è campionata a parte)
# ─────────────────────────────────────────────
def _cx(side: str, direction: str) -> float:
    """Centro x della zona (mid-point geometrico)."""
    if side == "Deuce":
        mapping = {
            "down_the_T": (0 + THIRD) / 2,
            "body":        (THIRD + 2 * THIRD) / 2,
            "out_wide":    (2 * THIRD + COURT_WIDTH / 2) / 2,
        }
    else:  # Ad
        mapping = {
            "down_the_T": (-THIRD + 0) / 2,
            "body":        (-2 * THIRD + -THIRD) / 2,
            "out_wide":    (-COURT_WIDTH / 2 + -2 * THIRD) / 2,
        }
    return mapping.get(direction, 0.0)


CENTROIDS_X: dict[tuple[str, str], float] = {
    (side, direction): _cx(side, direction)
    for side in ("Deuce", "Ad")
    for direction in ("down_the_T", "body", "out_wide")
}

# Sigma gaussiano laterale (m) – più stretto per rispettare le 3 zone
SIGMA_X = THIRD * 0.28   # ≈ 0.38 m

# Parametri profondità: solo l'ultimo 40% del box è "zona ATP"
DEPTH_OFFSET = 0.60          # 60% del box è escluso dal campionamento
DEPTH_RANGE  = 1.0 - DEPTH_OFFSET   # 0.40 = ampiezza della zona campionabile

# Margini di sicurezza dai bordi (m)
MARGIN_X = 0.04
MARGIN_Y = 0.08


# ─────────────────────────────────────────────
# 3.  SEED DETERMINISTICO  +  CAMPIONAMENTO
# ─────────────────────────────────────────────
def stable_seed(row_id: int | str) -> int:
    return int(hashlib.md5(str(row_id).encode()).hexdigest(), 16) % (2**31)


def _sample_depth(rng: np.random.Generator) -> float:
    """
    Profondità normalizzata [0, 1] nel service box.
    Beta(5, 2) traslata sull'ultimo 40%:
        y_norm = 0.60 + 0.40 * Beta(5, 2)
    → la moda cade ~80-90% della lunghezza del box
    → i valori < 60% sono impossibili per costruzione
    → restituisce la coordinata y in metri  [0, SVC_LEN]
    """
    raw  = rng.beta(5, 2)                           # in [0, 1], moda ≈ 0.80
    norm = DEPTH_OFFSET + DEPTH_RANGE * raw         # in [0.60, 1.00]
    return float(np.clip(norm * SVC_LEN, MARGIN_Y, SVC_LEN - MARGIN_Y))


def _ellipse_guard(x: float, y: float,
                   cx: float, cy: float,
                   rx: float, ry: float) -> tuple[float, float]:
    """
    Proietta (x, y) all'interno dell'ellisse di semi-assi (rx, ry)
    centrata in (cx, cy).  Se il punto è già interno, lo restituisce invariato.
    """
    dx = (x - cx) / rx
    dy = (y - cy) / ry
    dist = dx**2 + dy**2
    if dist <= 1.0:
        return x, y
    scale = 1.0 / np.sqrt(dist)
    return cx + dx * rx * scale, cy + dy * ry * scale


def get_serve_coords(
    direction: str,
    side: str,
    row_id: int | str = 0,
) -> tuple[float, float]:
    """
    Campiona (x, y) con modello ATP/WTA realistico:
      - profondità:  Beta(5, 2) traslata sull'ultimo 40% del box  →  y realistico
      - laterale:    gaussiana attorno al centroide di zona  →  x realistico
      - guardrail:   ellisse di plausibilità + clip ai confini zona
    """
    rng = np.random.default_rng(stable_seed(row_id))

    # ── Profondità (y) ──────────────────────────────────────────────
    y = _sample_depth(rng)

    # ── Centroide e limiti laterali (x) ─────────────────────────────
    cx = CENTROIDS_X.get((side, direction), 0.0)

    if side == "Deuce":
        x_bounds = {
            "down_the_T": (0,          THIRD),
            "body":        (THIRD,      2 * THIRD),
            "out_wide":    (2 * THIRD,  COURT_WIDTH / 2),
        }
    else:
        x_bounds = {
            "down_the_T": (-THIRD,              0),
            "body":        (-2 * THIRD,         -THIRD),
            "out_wide":    (-COURT_WIDTH / 2,   -2 * THIRD),
        }
    x_min, x_max = x_bounds.get(direction, (-COURT_WIDTH / 2, COURT_WIDTH / 2))

    # ── Campionamento x con reject-sampling ─────────────────────────
    for _ in range(15):
        x = rng.normal(cx, SIGMA_X)
        if x_min + MARGIN_X <= x <= x_max - MARGIN_X:
            break
    else:
        x = float(np.clip(cx, x_min + MARGIN_X, x_max - MARGIN_X))

    # ── Ellisse di plausibilità ──────────────────────────────────────
    # Centro dell'ellisse = centroide zona × profondità modale
    cy_modal = (DEPTH_OFFSET + DEPTH_RANGE * (5 / (5 + 2 + 1))) * SVC_LEN  # moda Beta
    rx = (x_max - x_min) * 0.52   # semi-asse orizzontale (leggermente più largo della zona)
    ry = DEPTH_RANGE * SVC_LEN * 0.54  # semi-asse verticale (copre la zona campionabile)
    x, y = _ellipse_guard(x, y, cx, cy_modal, rx, ry)

    # Clip finale di sicurezza
    x = float(np.clip(x, x_min + MARGIN_X, x_max - MARGIN_X))
    y = float(np.clip(y, MARGIN_Y, SVC_LEN - MARGIN_Y))

    return x, y

# ─────────────────────────────────────────────
# 4.  STILI  (colori, simboli, dimensioni)
# ─────────────────────────────────────────────
PLAYER_COLORS = {
    "Sinner":  "#4A90E2",   # blu Sinner
    "Alcaraz": "#E87D3E",   # arancio Alcaraz
}

OUTCOME_SYMBOLS = {
    "ace":          "star",
    "winner":       "circle",
    "lost":         "circle-open",
}

OUTCOME_SIZE = {
    "ace":          18,
    "winner":       12,
    "lost":         10,
}

SERVE_OPACITY = {1: 1.0, 2: 0.55}   # 1° servizio pieno, 2° più trasparente


def classify_outcome(row: pd.Series) -> str:
    if row.get("is_ace", False):
        return "ace"
    if row.get("is_winner_pt", False) or row.get("point_winner_name") == row.get("server_name"):
        return "winner"
    return "lost"


# ─────────────────────────────────────────────
# 5.  DISEGNO CAMPO (Plotly shapes)
# ─────────────────────────────────────────────
CLAY    = "#C0544A"
NET     = "#1a1a1a"
WHITE   = "white"
DASHED  = dict(color="rgba(255,255,255,0.45)", width=1, dash="dash")

def court_shapes() -> list[dict]:
    """Restituisce la lista di shapes Plotly per mezzo campo."""
    W2 = COURT_WIDTH / 2
    shapes = [
        # Sfondo terra battuta
        dict(type="rect", x0=-W2, x1=W2, y0=0, y1=HALF_LEN,
             fillcolor=CLAY, line_width=0, layer="below"),
        # Perimetro
        dict(type="rect", x0=-W2, x1=W2, y0=0, y1=HALF_LEN,
             fillcolor="rgba(0,0,0,0)", line=dict(color=WHITE, width=2.5)),
        # Service line
        dict(type="line", x0=-W2, x1=W2, y0=SVC_LEN, y1=SVC_LEN,
             line=dict(color=WHITE, width=2)),
        # Center service line
        dict(type="line", x0=0, x1=0, y0=0, y1=SVC_LEN,
             line=dict(color=WHITE, width=2)),
        # Rete
        dict(type="line", x0=-W2, x1=W2, y0=0, y1=0,
             line=dict(color=NET, width=4)),
        # Paletti rete
        dict(type="line", x0=-W2 - 0.12, x1=-W2 - 0.12, y0=0, y1=1.0,
             line=dict(color=NET, width=5)),
        dict(type="line", x0=W2 + 0.12, x1=W2 + 0.12, y0=0, y1=1.0,
             line=dict(color=NET, width=5)),
    ]
    # Linee tratteggiate zone (Deuce + Ad)
    for sign in (1, -1):
        for k in (1, 2):
            shapes.append(dict(
                type="line",
                x0=sign * k * THIRD, x1=sign * k * THIRD,
                y0=0, y1=SVC_LEN,
                line=DASHED,
            ))
    return shapes


def court_annotations() -> list[dict]:
    """Etichette zone nel service box."""
    labels = []
    W2 = COURT_WIDTH / 2
    zone_centers = {
        "T":    (THIRD / 2,               0.45),
        "Body": (THIRD + THIRD / 2,       0.45),
        "Wide": (2 * THIRD + THIRD / 2,   0.45),
    }
    for name, (cx, cy) in zone_centers.items():
        for sign, side_label in ((1, "Deuce"), (-1, "Ad")):
            labels.append(dict(
                x=sign * cx, y=cy,
                text=f"<b>{name}</b>",
                showarrow=False,
                font=dict(color="rgba(255,255,255,0.55)", size=9, family="monospace"),
                xanchor="center",
            ))
    # Etichette lato
    for sign, side_label in ((1, "DEUCE"), (-1, "AD")):
        labels.append(dict(
            x=sign * W2 / 2, y=SVC_LEN + 0.5,
            text=f"<b>{side_label}</b>",
            showarrow=False,
            font=dict(color="rgba(255,255,255,0.7)", size=11, family="monospace"),
            xanchor="center",
        ))
    return labels


# ─────────────────────────────────────────────
# 6.  COSTRUZIONE FIGURA PLOTLY
# ─────────────────────────────────────────────
def build_figure(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        shapes=court_shapes(),
        annotations=court_annotations(),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="#1e1e2e",
        font=dict(color="white", family="monospace"),
        xaxis=dict(range=[-(COURT_WIDTH / 2) - 0.6, (COURT_WIDTH / 2) + 0.6],
                   visible=False, scaleanchor="y", scaleratio=1),
        yaxis=dict(range=[-0.6, HALF_LEN + 1.2], visible=False),
        margin=dict(l=10, r=10, t=60, b=10),
        legend=dict(
            orientation="h",
            x=0.5, xanchor="center",
            y=-0.04, yanchor="top",
            bgcolor="rgba(30,30,46,0.85)",
            bordercolor="rgba(255,255,255,0.2)",
            borderwidth=1,
            font=dict(size=11, color="white"),
        ),
        hoverlabel=dict(
            bgcolor="#1e1e2e", font_size=12,
            font_family="monospace", bordercolor="rgba(255,255,255,0.3)",
        ),
    )

    # Raggruppa per (player, outcome, serve_number) → 1 trace per gruppo
    # Così la legenda è pulita e ogni gruppo è togglabile
    grouped = df.groupby(["server_name", "outcome", "serve_number"], dropna=False)
    legend_seen: set[str] = set()

    for (player, outcome, serve_num), group in grouped:
        color   = PLAYER_COLORS.get(player, "gray")
        symbol  = OUTCOME_SYMBOLS.get(outcome, "circle")
        size    = OUTCOME_SIZE.get(outcome, 10)
        opacity = SERVE_OPACITY.get(serve_num, 1.0)
        label   = f"{player} – {outcome.replace('_',' ').title()} ({'1°' if serve_num == 1 else '2°'})"

        xs, ys = [], []
        hovers = []
        for _, row in group.iterrows():
            x, y = get_serve_coords(row["serve_direction"], row["court_side"], row.name)
            xs.append(x)
            ys.append(y)
            hover = (
                f"<b>{player}</b><br>"
                f"Set {row.get('set_number','?')}<br>"
                f"Dir: {row['serve_direction'].replace('_',' ')}<br>"
                f"Esito: <b>{outcome}</b> · Servizio: {serve_num}°<br>"
            )
            hovers.append(hover)

        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="markers",
            name=label,
            legendgroup=label,
            showlegend=(label not in legend_seen),
            marker=dict(
                symbol=symbol,
                size=size,
                color=color,
                opacity=opacity,
                line=dict(color="white", width=0.8),
            ),
            hovertemplate="%{customdata}<extra></extra>",
            customdata=hovers,
        ))
        legend_seen.add(label)

    return fig


# ─────────────────────────────────────────────
# 7.  PREPARAZIONE DATI  (con fallback sintetico)
# ─────────────────────────────────────────────
def prepare_df(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Aggiunge le colonne derivate necessarie al plotting."""
    df = df_raw.copy()
    
    # Valori di default se le colonne mancano
    if "serve_number_played" in df.columns and "serve_number" not in df.columns:
        df = df.rename(columns={"serve_number_played": "serve_number"})
    if "court_side" not in df.columns:
        df["court_side"] = np.where(df.index % 2 == 0, "Deuce", "Ad")
    if "serve_number" not in df.columns:
        df["serve_number"] = 1
    if "set_number" not in df.columns:
        df["set_number"] = 1
    if "game_number" not in df.columns:
        df["game_number"] = df.index
    if "score" not in df.columns:
        df["score"] = ""

    df = df.dropna(subset=["serve_direction"])
    df["outcome"] = df.apply(classify_outcome, axis=1)
    return df


def make_synthetic_df(n: int = 200) -> pd.DataFrame:
    """Dataset sintetico per demo/sviluppo."""
    rng = np.random.default_rng(42)
    players     = ["Sinner", "Alcaraz"]
    directions  = ["down_the_T", "body", "out_wide"]
    sides       = ["Deuce", "Ad"]

    rows = []
    for i in range(n):
        player    = rng.choice(players)
        direction = rng.choice(directions)
        side      = rng.choice(sides)
        serve_num = rng.choice([1, 2], p=[0.65, 0.35])
        set_num   = rng.choice([1, 2, 3, 4, 5])
        r = rng.random()
        is_ace   = bool(r < 0.08)
        is_df    = bool((not is_ace) and serve_num == 2 and r > 0.90)
        is_winner= bool((not is_ace) and (not is_df) and r > 0.55)
        pt_winner= player if (is_ace or is_winner) else ("Sinner" if player == "Alcaraz" else "Alcaraz")
        rows.append(dict(
            server_name=player, serve_direction=direction, court_side=side,
            serve_number=serve_num, set_number=set_num, game_number=i % 12 + 1,
            is_ace=is_ace, is_winner_pt=is_winner,
            point_winner_name=pt_winner, score="",
        ))
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────
# 8. STREAMLIT APP
# ─────────────────────────────────────────────

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "sinner_alcaraz_2025.parquet"


try:
    # Ensure the project root is on sys.path so absolute imports like `src.*` work
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from src.data.loader import load_and_clean
    _RAW_DF = load_and_clean(DATA_PATH)
    print("Dataset reale caricato.")
except Exception as exc:
    # Print full traceback to help debugging when running via Streamlit
    traceback.print_exc()
    print(f"Dataset reale non trovato – uso dati sintetici. Dettaglio: {exc}")
    _RAW_DF = make_synthetic_df(300)

_DF = prepare_df(_RAW_DF)

# Configurazione pagina
st.set_page_config(
    page_title="RG25 – Analisi Servizi",
    layout="wide",
)

# Titolo
st.markdown(
    """
    <h1 style='text-align: center; color: black;'>
    🎾 Roland Garros 2025 · Sinner vs Alcaraz
    </h1>
    <p style='text-align: center; color: #BBBBBB;'>
    Analisi interattiva delle direzioni di servizio
    </p>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# Sidebar filtri
# ─────────────────────────────────────────────

st.sidebar.header("🎛️ Filtri")

sets_available = sorted(_DF["set_number"].dropna().unique().tolist())

sel_set = st.sidebar.selectbox(
    "Set",
    ["all"] + sets_available,
    format_func=lambda x: "Tutti i set" if x == "all" else f"Set {x}",
)

sel_player = st.sidebar.selectbox(
    "Giocatore",
    ["all", "Sinner", "Alcaraz"],
    format_func=lambda x: {
        "all": "Entrambi",
        "Sinner": "Sinner",
        "Alcaraz": "Alcaraz",
    }[x],
)

sel_side = st.sidebar.selectbox(
    "Lato",
    ["all", "Deuce", "Ad"],
    format_func=lambda x: {
        "all": "Deuce + Ad",
        "Deuce": "Deuce",
        "Ad": "Ad",
    }[x],
)

sel_serve = st.sidebar.selectbox(
    "Servizio",
    ["all", 1, 2],
    format_func=lambda x: {
        "all": "1° + 2°",
        1: "Solo 1° servizio",
        2: "Solo 2° servizio",
    }[x],
)

sel_outcomes = st.sidebar.multiselect(
    "Esito",
    ["ace", "winner", "lost"],
    default=["ace", "winner", "lost"],
    format_func=lambda x: {
        "ace": "Ace ★",
        "winner": "Winner ●",
        "lost": "Lost ○",
    }[x],
)

# ─────────────────────────────────────────────
# Applicazione filtri
# ─────────────────────────────────────────────

dff = _DF.copy()

if sel_set != "all":
    dff = dff[dff["set_number"] == sel_set]

if sel_player != "all":
    dff = dff[dff["server_name"] == sel_player]

if sel_side != "all":
    dff = dff[dff["court_side"] == sel_side]

if sel_serve != "all":
    dff = dff[dff["serve_number"] == sel_serve]

if sel_outcomes:
    dff = dff[dff["outcome"].isin(sel_outcomes)]

# ─────────────────────────────────────────────
# Grafico
# ─────────────────────────────────────────────

fig = build_figure(dff)
fig.update_layout(
    height=800,
)

st.plotly_chart(
    fig,
    width="stretch",
    config={"displayModeBar": False},
)

# ─────────────────────────────────────────────
# Statistiche
# ─────────────────────────────────────────────

st.markdown("---")

col1, col2, col3 = st.columns(3)

for col, player in zip([col1, col2], ["Sinner", "Alcaraz"]):
    sub = dff[dff["server_name"] == player]
    n = len(sub)
    aces = sub["outcome"].eq("ace").sum()
    pct_won = (
        sub["outcome"].isin(["ace", "winner"]).sum() / n * 100
        if n > 0 else 0
    )

    col.metric(
        label=player,
        value=f"{n} servizi",
        delta=f"{aces} ace · {pct_won:.0f}% punti vinti",
    )

col3.metric(
    label="Totale servizi",
    value=len(dff),
)

# Tabella opzionale
with st.expander("Visualizza dati filtrati"):
    st.dataframe(dff, width="stretch")