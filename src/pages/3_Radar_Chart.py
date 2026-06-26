"""
radar_chart_view.py
------------------------
Standalone Streamlit View for Playstyle Radar Chart
Sinner vs Alcaraz
"""

import pandas as pd
import numpy as np
from pathlib import Path
import re
import streamlit as st
import plotly.graph_objects as go

# ==========================================
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Player Radar", layout="wide")

repo_root = Path(__file__).resolve().parent.parent.parent
data_path = repo_root / "data" / "processed" / "sinner_alcaraz_2025.parquet"

PLAYER_1 = "J. Sinner"
PLAYER_2 = "C. Alcaraz"
PLAYER_1_ID = 1
PLAYER_2_ID = 2

# ==========================================
# 2. DATA LOADING
# ==========================================
@st.cache_data
def load_data():
    try:
        return pd.read_parquet(data_path)
    except FileNotFoundError:
        st.error(f"No dataset found at: {data_path}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.stop()

# ==========================================
# 3. PARSER & MATH HELPERS
# ==========================================
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
    
    terminal_shot = None
    outcome = None
    
    if shots:
        last_shot = shots[-1]
        if last_shot[0] in ['f', 'r', 'v', 'u', 'l', 'h', 'j']:
            terminal_shot = 'forehand'
        elif last_shot[0] in ['b', 's', 'z', 'y', 'm', 'i', 'k']:
            terminal_shot = 'backhand'
            
        if '*' in last_shot:
            outcome = 'winner'
            
    return terminal_shot, outcome, is_ace

def calculate_metrics(player_id, match_df):
    if match_df.empty:
        return [0] * 7

    serve_mask = match_df['Svr'] == player_id
    return_mask = match_df['Svr'] != player_id
    
    # --- Serve ---
    serves_df = match_df[serve_mask].copy()
    total_serves = len(serves_df)
    if total_serves > 0:
        first_in_mask = ~serves_df['1st'].astype(str).str.match(r'^[4560][nwdexg]')
        first_in = first_in_mask.sum()
        first_won = serves_df[first_in_mask & (serves_df['PtWinner'] == player_id)].shape[0]
        second_in_mask = ~first_in_mask 
        second_won = serves_df[second_in_mask & (serves_df['PtWinner'] == player_id)].shape[0]
        
        first_in_pct = first_in / total_serves if total_serves > 0 else 0
        first_won_pct = first_won / first_in if first_in > 0 else 0
        second_won_pct = second_won / second_in_mask.sum() if second_in_mask.sum() > 0 else 0
        
        serve_eff = (first_in_pct * first_won_pct) + ((1 - first_in_pct) * second_won_pct)
        
        aces = serves_df.apply(lambda row: extract_shot_info(row['1st'])[2] or extract_shot_info(row['2nd'])[2], axis=1).sum()
        second_fault_mask = serves_df['2nd'].astype(str).str.match(r'^[4560][nwdexg]')
        double_faults = (second_in_mask & second_fault_mask).sum()
        
        serve_qual = (0.4 * first_in_pct) + (0.3 * (aces / total_serves)) + (0.3 * (1 - (double_faults / total_serves)))
    else:
        serve_eff, serve_qual = 0, 0

    # --- Baseline ---
    rally_lengths = match_df.apply(lambda row: len(re.findall(r'[fbrsvzuylmhiqt]', str(row['1st']))) + len(re.findall(r'[fbrsvzuylmhiqt]', str(row['2nd']))), axis=1)
    baseline_pts = match_df[rally_lengths > 4]
    baseline_dom = len(baseline_pts[baseline_pts['PtWinner'] == player_id]) / len(baseline_pts) if len(baseline_pts) > 0 else 0

    # --- Break Points ---
    bp_mask = match_df.apply(lambda row: is_break_point(row['Pts'], row['Svr'], player_id), axis=1)
    bp_chances = match_df[bp_mask]
    bp_conversion = len(bp_chances[bp_chances['PtWinner'] == player_id]) / len(bp_chances) if len(bp_chances) > 0 else 0

    # --- Returns ---
    return_pts = match_df[return_mask]
    return_eff = len(return_pts[return_pts['PtWinner'] == player_id]) / len(return_pts) if len(return_pts) > 0 else 0

    # --- Groundstrokes ---
    bh_total, bh_won, fh_winners, total_winners = 0, 0, 0, 0
    for _, row in match_df.iterrows():
        rally_str = row['2nd'] if pd.notna(row['2nd']) else row['1st']
        shot_type, outcome, _ = extract_shot_info(rally_str)
        if shot_type == 'backhand':
            bh_total += 1
            if row['PtWinner'] == player_id:
                bh_won += 1
        if outcome == 'winner' and row['PtWinner'] == player_id:
            total_winners += 1
            if shot_type == 'forehand':
                fh_winners += 1

    bh_solidity = bh_won / bh_total if bh_total > 0 else 0
    fh_dominance = fh_winners / total_winners if total_winners > 0 else 0

    raw_metrics = [serve_eff, serve_qual, baseline_dom, bp_conversion, return_eff, bh_solidity, fh_dominance]
    return [m * 100 for m in raw_metrics]

# ==========================================
# 4. COMPUTE BASE TRACES
# ==========================================
vals_a_raw = calculate_metrics(PLAYER_1_ID, df)
vals_b_raw = calculate_metrics(PLAYER_2_ID, df)

ALL_CATEGORIES = [
    "Serve Efficiency",
    "Serve Quality",
    "Baseline Dominance",
    "Break Point Conversion",
    "Return Efficiency",
    "Backhand Solidity",
    "Forehand Dominance"
]

# Map each category to its explanation for the checkbox labels
CATEGORY_DESCRIPTIONS = {
    "Serve Efficiency": "Combines first- and second-serve win percentages to measure overall service game security.",
    "Serve Quality": "Weights first-serve accuracy, total aces, and penalizes double faults to evaluate structural service pressure.",
    "Baseline Dominance": "Assesses point-winning effectiveness during extended exchanges exceeding four shots.",
    "Break Point Conversion": "Measures tactical execution and composure during critical return-game opportunities.",
    "Return Efficiency": "Tracks the total percentage of points won while breaking the opponent’s serve.",
    "Backhand Solidity": "Isolates the baseline resilience and win percentage of rallies ending on the backhand wing.",
    "Forehand Dominance": "Evaluates offensive firepower by tracking the proportion of total pure winners struck via the forehand."
}

# ==========================================
# 5. UI: COMBINED EXPLANATIONS & FILTERS
# ==========================================
st.markdown("<h2 style='text-align: center;'> Playing Style Comparison - Radar Chart</h2>", unsafe_allow_html=True)

# Kept only the intro div
st.markdown(
    """
    <div style='text-align: center; color: #888; margin-bottom: 30px;'>
        This radar chart maps the distinct technical identities of Sinner and Alcaraz across seven key performance dimensions. 
        The metrics are evaluated on a <strong>pure 0-100% scale</strong>, representing their true match execution rates without artificial scaling.
    </div>
    """, 
    unsafe_allow_html=True
)

st.markdown("#### 🎛️ Select Metrics to Compare:")

# Use 2 columns instead of 4 so the text has room to breathe
cols = st.columns(2)
selected_categories = []

# Generate checkboxes with embedded markdown descriptions
for i, category in enumerate(ALL_CATEGORIES):
    with cols[i % 2]:
        # Bold the title and append the description natively in the checkbox
        label = f"**{category}:** {CATEGORY_DESCRIPTIONS[category]}"
        if st.checkbox(label, value=True):
            selected_categories.append(category)

st.markdown("---") # Visual separator before the chart

# Safety check: Radar charts need at least 3 axes
if len(selected_categories) < 3:
    st.warning("⚠️ Please select at least 3 metrics to form a proper radar chart.")
    st.stop()

# Filter the data based on selections
indices = [ALL_CATEGORIES.index(cat) for cat in selected_categories]
vals_a = [vals_a_raw[i] for i in indices]
vals_b = [vals_b_raw[i] for i in indices]
categories = [ALL_CATEGORIES[i] for i in indices]

# Close the radar loop by appending the first value to the end
vals_a += vals_a[:1]
vals_b += vals_b[:1]
categories += categories[:1]

# ==========================================
# 6. PLOTLY RADAR
# ==========================================
fig = go.Figure()

# Player 1 Trace
fig.add_trace(go.Scatterpolar(
    r=vals_a,
    theta=categories,
    fill="toself",
    name=PLAYER_1,
    line_color="#4A90E2",
    fillcolor="rgba(74, 144, 226, 0.3)",
    hovertemplate="<b>%{theta}</b><br>Score: %{r:.1f}%<extra></extra>"
))

# Player 2 Trace
fig.add_trace(go.Scatterpolar(
    r=vals_b,
    theta=categories,
    fill="toself",
    name=PLAYER_2,
    line_color="#E87D3E",
    fillcolor="rgba(232, 125, 62, 0.3)",
    hovertemplate="<b>%{theta}</b><br>Score: %{r:.1f}%<extra></extra>"
))

# Layout Configuration
fig.update_layout(
    polar=dict(
        radialaxis=dict(
            visible=True, 
            range=[0, 100], 
            tickvals=[0, 20, 40, 60, 80, 100],
            ticktext=["0%", "20%", "40%", "60%", "80%", "100%"]
        )
    ),
    template="plotly_dark",
    showlegend=True,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.2,
        xanchor="center",
        x=0.5
    ),
    margin=dict(t=40, b=40, l=40, r=40)
)

st.plotly_chart(
    fig, 
    width="stretch",
    config={
        "scrollZoom": True,
        "displayModeBar": True
    }
)