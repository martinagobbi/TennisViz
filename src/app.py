"""
app.py
------------------------
Roland Garros 2025 – Tennis DataViz Dashboard
Sinner vs Alcaraz

Unifica 3 visualizzazioni interattive in un'unica Dashboard Streamlit:
  1. Court Chart (Analisi Servizi delle compagne)
  2. Radar Chart (Analisi Stili di Gioco - Formule validate)
  3. Mirror Line Chart (Probabilità di Vittoria e Momentum)
"""

import hashlib
import re
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import sys

# =====================================================================
# 1. COSTANTI GEOMETRICHE & STILI (Dalle tue compagne)
# =====================================================================
COURT_WIDTH = 8.23        # larghezza singolo (metri)
HALF_LEN    = 11.885      # lunghezza mezzo campo (rete → baseline)
SVC_LEN     = 6.40        # rete → service line
THIRD       = (COURT_WIDTH / 2) / 3   # ≈ 1.372 m (ampiezza di ciascuna delle 3 zone)

# Centroidi X per il campionamento dei servizi
def _cx(side: str, direction: str) -> float:
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

CENTROIDS_X = {
    (side, direction): _cx(side, direction)
    for side in ("Deuce", "Ad")
    for direction in ("down_the_T", "body", "out_wide")
}

SIGMA_X = THIRD * 0.28   
DEPTH_OFFSET = 0.60          
DEPTH_RANGE  = 1.0 - DEPTH_OFFSET   
MARGIN_X = 0.04
MARGIN_Y = 0.08

PLAYER_COLORS = {
    "J. Sinner":  "#4A90E2",   # Blu Sinner
    "C. Alcaraz": "#E87D3E",   # Arancio Alcaraz
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

SERVE_OPACITY = {1: 1.0, 2: 0.55}

# =====================================================================
# 2. FUNZIONI DI SUPPORTO & CAMPIONAMENTO (Dalle tue compagne)
# =====================================================================
def stable_seed(row_id: int | str) -> int:
    return int(hashlib.md5(str(row_id).encode()).hexdigest(), 16) % (2**31)

def _sample_depth(rng: np.random.Generator) -> float:
    raw  = rng.beta(5, 2)                           
    norm = DEPTH_OFFSET + DEPTH_RANGE * raw         
    return float(np.clip(norm * SVC_LEN, MARGIN_Y, SVC_LEN - MARGIN_Y))

def _ellipse_guard(x: float, y: float, cx: float, cy: float, rx: float, ry: float) -> tuple[float, float]:
    dx = (x - cx) / rx
    dy = (y - cy) / ry
    dist = dx**2 + dy**2
    if dist <= 1.0:
        return x, y
    scale = 1.0 / np.sqrt(dist)
    return cx + dx * rx * scale, cy + dy * ry * scale

def get_serve_coords(direction: str, side: str, row_id: int | str = 0) -> tuple[float, float]:
    rng = np.random.default_rng(stable_seed(row_id))
    y = _sample_depth(rng)
    cx = CENTROIDS_X.get((side, direction), 0.0)

    if side == "Deuce":
        x_bounds = {"down_the_T": (0, THIRD), "body": (THIRD, 2 * THIRD), "out_wide": (2 * THIRD, COURT_WIDTH / 2)}
    else:
        x_bounds = {"down_the_T": (-THIRD, 0), "body": (-2 * THIRD, -THIRD), "out_wide": (-COURT_WIDTH / 2, -2 * THIRD)}
    x_min, x_max = x_bounds.get(direction, (-COURT_WIDTH / 2, COURT_WIDTH / 2))

    for _ in range(15):
        x = rng.normal(cx, SIGMA_X)
        if x_min + MARGIN_X <= x <= x_max - MARGIN_X:
            break
    else:
        x = float(np.clip(cx, x_min + MARGIN_X, x_max - MARGIN_X))

    cy_modal = (DEPTH_OFFSET + DEPTH_RANGE * (5 / (5 + 2 + 1))) * SVC_LEN  
    rx = (x_max - x_min) * 0.52   
    ry = DEPTH_RANGE * SVC_LEN * 0.54  
    x, y = _ellipse_guard(x, y, cx, cy_modal, rx, ry)

    return float(np.clip(x, x_min + MARGIN_X, x_max - MARGIN_X)), float(np.clip(y, MARGIN_Y, SVC_LEN - MARGIN_Y))

# =====================================================================
# 3.DISEGNO GEOMETRIA CAMPO PLOTLY (Dalle tue compagne)
# =====================================================================
CLAY    = "#C0544A"
NET     = "#1a1a1a"
WHITE   = "white"
DASHED  = dict(color="rgba(255,255,255,0.45)", width=1, dash="dash")

def court_shapes() -> list[dict]:
    W2 = COURT_WIDTH / 2
    shapes = [
        dict(type="rect", x0=-W2, x1=W2, y0=0, y1=HALF_LEN, fillcolor=CLAY, line_width=0, layer="below"),
        dict(type="rect", x0=-W2, x1=W2, y0=0, y1=HALF_LEN, fillcolor="rgba(0,0,0,0)", line=dict(color=WHITE, width=2.5)),
        dict(type="line", x0=-W2, x1=W2, y0=SVC_LEN, y1=SVC_LEN, line=dict(color=WHITE, width=2)),
        dict(type="line", x0=0, x1=0, y0=0, y1=SVC_LEN, line=dict(color=WHITE, width=2)),
        dict(type="line", x0=-W2, x1=W2, y0=0, y1=0, line=dict(color=NET, width=4)),
    ]
    for sign in (1, -1):
        for k in (1, 2):
            shapes.append(dict(type="line", x0=sign * k * THIRD, x1=sign * k * THIRD, y0=0, y1=SVC_LEN, line=DASHED))
    return shapes

def court_annotations() -> list[dict]:
    labels = []
    W2 = COURT_WIDTH / 2
    zone_centers = {"T": (THIRD / 2, 0.45), "Body": (THIRD + THIRD / 2, 0.45), "Wide": (2 * THIRD + THIRD / 2, 0.45)}
    for name, (cx, cy) in zone_centers.items():
        for sign in (1, -1):
            labels.append(dict(x=sign * cx, y=cy, text=f"<b>{name}</b>", showarrow=False, font=dict(color="rgba(255,255,255,0.55)", size=9, family="monospace"), xanchor="center"))
    for sign, side_label in ((1, "DEUCE"), (-1, "AD")):
        labels.append(dict(x=sign * W2 / 2, y=SVC_LEN + 0.5, text=f"<b>{side_label}</b>", showarrow=False, font=dict(color="rgba(255,255,255,0.7)", size=11, family="monospace"), xanchor="center"))
    return labels

# =====================================================================
# 4. PARSER LOGS INTERMEDI DEL MATCH CHARTING PROJECT
# =====================================================================
def is_break_point(pts_str, server_id, target_player_id):
    if pd.isna(pts_str) or target_player_id == server_id:
        return False
    if server_id == 1 and target_player_id == 2:
        return pts_str in ['0-40', '15-40', '30-40', '40-AD']
    elif server_id == 2 and target_player_id == 1:
        return pts_str in ['40-0', '40-15', '40-30', 'AD-40']
    return False

def extract_shot_info(rally_str):
    if pd.isna(rally_str):
        return None, None, False
    is_ace = '*' in str(rally_str) and len(re.findall(r'[fbrsvzuylmhiqt]', str(rally_str))) == 0
    shots = re.findall(r'([fbrsvzuylmhiqt][0-3]?[7-9]?[\+\-\=\;\^]?[\*\@\#nwdxe\!]?)', str(rally_str))
    terminal_shot, outcome = None, None
    if shots:
        last_shot = shots[-1]
        if last_shot[0] in ['f', 'r', 'v', 'u', 'l', 'h', 'j']:
            terminal_shot = 'forehand'
        elif last_shot[0] in ['b', 's', 'z', 'y', 'm', 'i', 'k']:
            terminal_shot = 'backhand'
        if '*' in last_shot:
            outcome = 'winner'
    return terminal_shot, outcome, is_ace

def classify_outcome_mcp(row):
    # Funzione ponte per mappare i codici MCP sugli esiti richiesti dal Court Chart
    rally = row['2nd'] if pd.notna(row['2nd']) else row['1st']
    _, outcome, is_ace = extract_shot_info(rally)
    if is_ace: return "ace"
    if outcome == "winner" and row['PtWinner'] == row['Svr']: return "winner"
    return "lost"

# =====================================================================
# 5. CARICAMENTO DATI ROBUSTO (.PARQUET)
# =====================================================================
st.set_page_config(page_title="RG25 – Sinner vs Alcaraz Dashboard", layout="wide")

PLAYER_1 = "J. Sinner"
PLAYER_2 = "C. Alcaraz"
PLAYER_1_ID = 1
PLAYER_2_ID = 2

@st.cache_data
def load_and_prepare_data():
    repo_root = Path(__file__).resolve().parent.parent 
    data_path = repo_root / 'data' / 'processed' / 'sinner_alcaraz_2025.parquet' 
    
    try:
        df = pd.read_parquet(data_path)
    except FileNotFoundError:
        st.error(f"Impossibile trovare il file Parquet in: {data_path}")
        st.stop()
        
    df = df.sort_values(by='Pt').reset_index(drop=True)
    
    # Integrazione colonne strutturali per i filtri di Streamlit
    df["server_name"] = df['Svr'].map({1: PLAYER_1, 2: PLAYER_2})
    df["court_side"] = np.where(df['Pt'] % 2 == 0, "Ad", "Deuce")
    df["serve_number"] = np.where(df['2nd'].isna(), 1, 2)
    df["set_number"] = df['Set1'] + df['Set2'] + 1
    
    # Parsing delle direzioni dal primo carattere numerico del codice MCP
    def parse_dir(x):
        if pd.isna(x): return "body"
        c = str(x)[0]
        if c == '4': return "out_wide"
        if c == '6': return "down_the_T"
        return "body"
        
    df["serve_direction"] = np.where(df['2nd'].isna(), df['1st'].apply(parse_dir), df['2nd'].apply(parse_dir))
    df["outcome"] = df.apply(classify_outcome_mcp, axis=1)
    
    return df

_RAW_DF = load_and_prepare_data()

# =====================================================================
# 6. SIDEBAR FILTRI GLOBALI
# =====================================================================
st.sidebar.header("🎛️ Filtri della Sessione")
sets_available = sorted(_RAW_DF["set_number"].dropna().unique().tolist())
sel_set = st.sidebar.selectbox("Filtra per Set", ["Tutti i Set"] + sets_available)

dff = _RAW_DF.copy()
if sel_set != "Tutti i Set":
    dff = dff[dff["set_number"] == sel_set]

# Titoli Dashboard principale
st.markdown("<h1 style='text-align: center; color: #2C3E50;'>🎾 Roland Garros 2025 Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #7F8C8D; font-size:16px;'>Studio Multidimensionale Avanzato: Jannik Sinner vs Carlos Alcaraz</p>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🎯 Court Chart (Servizi)", "🕸️ Radar Chart (Stile di Gioco)", "📈 Mirror Line Chart (Progressione)"])

# =====================================================================
# TAB 1: COURT CHART (Interattività Plotly)
# =====================================================================
with tab1:
    st.subheader("Mappatura Spaziale e Distribuzione dei Servizi")
    
    c1, c2, c3 = st.columns(3)
    with c1: sel_player = st.selectbox("Giocatore al Servizio", ["Entrambi", PLAYER_1, PLAYER_2])
    with c2: sel_side = st.selectbox("Quadrante di Gioco", ["Deuce + Ad", "Deuce", "Ad"])
    with c3: sel_serve = st.selectbox("Battuta", ["1° + 2° Servizio", "Solo 1°", "Solo 2°"])

    dff_court = dff.copy()
    if sel_player != "Entrambi": dff_court = dff_court[dff_court["server_name"] == sel_player]
    if sel_side != "Deuce + Ad": dff_court = dff_court[dff_court["court_side"] == sel_side]
    if sel_serve == "Solo 1°": dff_court = dff_court[dff_court["serve_number"] == 1]
    elif sel_serve == "Solo 2°": dff_court = dff_court[dff_court["serve_number"] == 2]

    # Generazione Plotly Figure
    fig_court = go.Figure()
    fig_court.update_layout(
        shapes=court_shapes(), annotations=court_annotations(),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="#1E1E2E",
        font=dict(color="white", family="monospace"),
        xaxis=dict(range=[-(COURT_WIDTH / 2) - 0.6, (COURT_WIDTH / 2) + 0.6], visible=False, scaleanchor="y", scaleratio=1),
        yaxis=dict(range=[-0.6, HALF_LEN + 1.2], visible=False),
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.05, bgcolor="rgba(30,30,46,0.85)", font=dict(size=11, color="white")),
    )

    grouped = dff_court.groupby(["server_name", "outcome", "serve_number"], dropna=False)
    legend_seen = set()

    for (player, outcome, serve_num), group in grouped:
        color   = PLAYER_COLORS.get(player, "gray")
        symbol  = OUTCOME_SYMBOLS.get(outcome, "circle")
        size    = OUTCOME_SIZE.get(outcome, 10)
        opacity = SERVE_OPACITY.get(serve_num, 1.0)
        label   = f"{player} – {outcome.title()} ({'1°' if serve_num == 1 else '2°'})"

        xs, ys, hovers = [], [], []
        for _, row in group.iterrows():
            x, y = get_serve_coords(row["serve_direction"], row["court_side"], row.name)
            xs.append(x)
            ys.append(y)
            hovers.append(f"<b>{player}</b><br>Set {row['set_number']}<br>Punteggio: {row['Pts']}<br>Direzione: {row['serve_direction']}<br>Esito: {outcome}")

        fig_court.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers", name=label, showlegend=(label not in legend_seen),
            marker=dict(symbol=symbol, size=size, color=color, opacity=opacity, line=dict(color="white", width=0.8)),
            hovertemplate="%{customdata}<extra></extra>", customdata=hovers
        ))
        legend_seen.add(label)

    st.plotly_chart(fig_court, width="stretch")

# =====================================================================
# TAB 2: RADAR CHART (Formule Validate e Logs in Chiaro)
# =====================================================================
with tab2:
    st.subheader("Analisi Quantitativa delle Performance e dello Stile")

    def calc_radar_metrics(player_id, df_filtered):
        if df_filtered.empty: return [0]*7, ["Nessun dato"]
        logs = []
        serve_pts = df_filtered[df_filtered['Svr'] == player_id]
        return_pts = df_filtered[df_filtered['Svr'] != player_id]
        
        # 1 & 2. SERVE EFFICIENCY & QUALITY
        tot_srv = len(serve_pts)
        serve_eff, serve_qual = 0, 0
        if tot_srv > 0:
            first_in_mask = ~serve_pts['1st'].astype(str).str.match(r'^[4560][nwdexg]')
            first_in = first_in_mask.sum()
            first_won = serve_pts[first_in_mask & (serve_pts['PtWinner'] == player_id)].shape[0]
            sec_in_mask = ~first_in_mask
            sec_won = serve_pts[sec_in_mask & (serve_pts['PtWinner'] == player_id)].shape[0]
            
            f_in_pct = first_in / tot_srv
            f_won_pct = first_won / first_in if first_in > 0 else 0
            s_won_pct = sec_won / sec_in_mask.sum() if sec_in_mask.sum() > 0 else 0
            
            serve_eff = (f_in_pct * f_won_pct) + ((1 - f_in_pct) * s_won_pct)
            aces = serve_pts.apply(lambda r: extract_shot_info(r['1st'])[2] or extract_shot_info(r['2nd'])[2], axis=1).sum()
            sec_fault_mask = serve_pts['2nd'].astype(str).str.match(r'^[4560][nwdexg]')
            dfs = (sec_in_mask & sec_fault_mask).sum()
            
            serve_qual = (0.4 * f_in_pct) + (0.3 * (aces/tot_srv)) + (0.3 * (1 - (dfs/tot_srv)))
            logs.append(f"<b>Serve Efficiency</b>: {serve_eff:.2f} (Resa 1°: {f_won_pct*100:.1f}%, Resa 2°: {s_won_pct*100:.1f}%)")
            logs.append(f"<b>Serve Quality</b>: {serve_qual:.2f} (Ace: {aces}, Doppi Falli: {dfs})")
        else:
            logs.append("Servizi insufficienti in questo set.")

        # 3. BASELINE DOMINANCE (Scambi > 4 colpi)
        r_lens = df_filtered.apply(lambda r: len(re.findall(r'[fbrsvzuylmhiqt]', str(r['1st']))) + len(re.findall(r'[fbrsvzuylmhiqt]', str(r['2nd']))), axis=1)
        base_pts = df_filtered[r_lens > 4]
        base_dom = len(base_pts[base_pts['PtWinner'] == player_id]) / len(base_pts) if len(base_pts) > 0 else 0
        logs.append(f"<b>Baseline Dominance</b>: {base_dom:.2f} (Scambi lunghi vinti: {len(base_pts[base_pts['PtWinner'] == player_id])}/{len(base_pts)})")

        # 4. BREAK POINT CONVERSION
        bp_chances = df_filtered[df_filtered.apply(lambda r: is_break_point(r['Pts'], r['Svr'], player_id), axis=1)]
        bp_conv = len(bp_chances[bp_chances['PtWinner'] == player_id]) / len(bp_chances) if len(bp_chances) > 0 else 0
        logs.append(f"<b>Break Point Conversion</b>: {bp_conv:.2f} (Palle break convertite: {len(bp_chances[bp_chances['PtWinner'] == player_id])}/{len(bp_chances)})")

        # 5. RETURN EFFICIENCY
        ret_eff = len(return_pts[return_pts['PtWinner'] == player_id]) / len(return_pts) if len(return_pts) > 0 else 0
        logs.append(f"<b>Return Efficiency</b>: {ret_eff:.2f} (Punti vinti in risposta: {len(return_pts[return_pts['PtWinner'] == player_id])}/{len(return_pts)})")

        # 6 & 7. GROUNDSTROKES (Rovescio e Dritto)
        bh_tot, bh_won, fh_win, tot_win = 0, 0, 0, 0
        for _, r in df_filtered.iterrows():
            rally = r['2nd'] if pd.notna(r['2nd']) else r['1st']
            stype, out, _ = extract_shot_info(rally)
            if stype == 'backhand':
                bh_tot += 1
                if r['PtWinner'] == player_id: bh_won += 1
            if out == 'winner' and r['PtWinner'] == player_id:
                tot_win += 1
                if stype == 'forehand': fh_win += 1
                
        bh_sol = bh_won / bh_tot if bh_tot > 0 else 0
        fh_dom = fh_win / tot_win if tot_win > 0 else 0
        logs.append(f"<b>Backhand Solidity</b>: {bh_sol:.2f} (Rovesci finali vinti: {bh_won}/{bh_tot})")
        logs.append(f"<b>Forehand Dominance</b>: {fh_dom:.2f} (Vincenti di dritto su totali: {fh_win}/{tot_win})")
        
        return [m*10 for m in [serve_eff, serve_qual, base_dom, bp_conv, ret_eff, bh_sol, fh_dom]], logs

    v_sinner, logs_sinner = calc_radar_metrics(1, dff)
    v_alcaraz, logs_alcaraz = calc_radar_metrics(2, dff)
    categories = ['Serve Efficiency', 'Serve Quality', 'Baseline Dominance', 'Break Point Conversion', 'Return Efficiency', 'Backhand Solidity', 'Forehand Dominance']

    # Costruzione Poligoni Radar
    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(r=v_sinner + [v_sinner[0]], theta=categories + [categories[0]], fill='toself', name=PLAYER_1, line_color=PLAYER_COLORS[PLAYER_1], fillcolor='rgba(74, 144, 226, 0.25)'))
    fig_radar.add_trace(go.Scatterpolar(r=v_alcaraz + [v_alcaraz[0]], theta=categories + [categories[0]], fill='toself', name=PLAYER_2, line_color=PLAYER_COLORS[PLAYER_2], fillcolor='rgba(232, 125, 62, 0.25)'))
    
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 10], gridcolor='#E0E0E0'), bgcolor='#FDFDFD'),
        paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#2C3E50', size=12),
        title=dict(text="Confronto Stili Normalizzato (Scala 0-10)", x=0.5)
    )
    
    rd1, rd2 = st.columns([2, 1])
    with rd1: st.plotly_chart(fig_radar, width="stretch")
    with rd2:
        st.markdown("### 🔍 Calcoli Intermedi ed Effettivi")
        st.markdown(f"**🦊 {PLAYER_1.upper()}**")
        for log in logs_sinner: st.markdown(f"- {log}")
        st.markdown(f"**🇪🇸 {PLAYER_2.upper()}**")
        for log in logs_alcaraz: st.markdown(f"- {log}")

# =====================================================================
# TAB 3: MIRROR LINE CHART (Andamento della Partita)
# =====================================================================
with tab3:
    st.subheader("Win Probability & Match Momentum Progression")
    st.write("Visualizzazione dinamica dell'andamento psicofisico e del vantaggio probabilistico punto per punto.")

    # Il momentum deve essere calcolato sempre sulla storia intera del match per coerenza statistica
    momentum = []
    current_momentum = 0
    for _, row in _RAW_DF.iterrows():
        set_diff = row['Set1'] - row['Set2']
        gm_diff = row['Gm1'] - row['Gm2']
        current_momentum *= 0.96  # Fattore di decadimento della memoria storica
        if row['PtWinner'] == 1: current_momentum += 1.8
        elif row['PtWinner'] == 2: current_momentum -= 1.8
        momentum.append((set_diff * 28) + (gm_diff * 10) + current_momentum)

    _RAW_DF['Win_Prob'] = [100 / (1 + np.exp(-m / 30)) for m in momentum]
    end_sets = _RAW_DF[_RAW_DF['Set1'] + _RAW_DF['Set2'] > _RAW_DF['Set1'].shift(1).fillna(0) + _RAW_DF['Set2'].shift(1).fillna(0)].index.tolist()

    fig_line = go.Figure()
    # Area Sinner
    fig_line.add_trace(go.Scatter(x=_RAW_DF['Pt'], y=np.where(_RAW_DF['Win_Prob'] > 50, _RAW_DF['Win_Prob'], 50), fill='tonexty', fillcolor='rgba(74, 144, 226, 0.4)', line=dict(color=PLAYER_COLORS[PLAYER_1]), name=PLAYER_1, hovertemplate="Punto %{x}<br>Win Prob: %{y:.1f}% Sinner<extra></extra>"))
    # Area Alcaraz
    fig_line.add_trace(go.Scatter(x=_RAW_DF['Pt'], y=np.where(_RAW_DF['Win_Prob'] < 50, _RAW_DF['Win_Prob'], 50), fill='tonexty', fillcolor='rgba(232, 125, 62, 0.4)', line=dict(color=PLAYER_COLORS[PLAYER_2]), name=PLAYER_2, hovertemplate="Punto %{x}<br>Win Prob: %{y:.1f}% Alcaraz<extra></extra>"))
    
    fig_line.add_hline(y=50, line_dash="dash", line_color="#333", opacity=0.6)

    # Linee di demarcazione dei set conclusi
    for i, idx in enumerate(end_sets):
        fig_line.add_vline(x=_RAW_DF.loc[idx, 'Pt'], line_dash="dot", line_color="#7F8C8D")
        fig_line.add_annotation(x=_RAW_DF.loc[idx, 'Pt'], y=92, text=f"Fine Set {i+1}", textangle=-90, font=dict(color="#34495E"), showarrow=False)

    fig_line.update_layout(
        yaxis=dict(range=[0, 100], tickvals=[0, 25, 50, 75, 100], ticktext=['100% Alcaraz', '75%', '50% Parità', '75%', '100% Sinner']),
        xaxis_title="Punto del Match", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='#FAFAFA', height=550,
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.15)
    )
    st.plotly_chart(fig_line, width="stretch")