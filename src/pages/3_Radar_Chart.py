import pandas as pd
import numpy as np
from pathlib import Path
import re
import streamlit as st
import plotly.graph_objects as go


# CONFIGURATION
st.set_page_config(page_title="RG25 –  Radar Chart", layout="wide")

repo_root = Path(__file__).resolve().parent.parent.parent
data_path = repo_root / "data" / "processed" / "sinner_alcaraz_2025.parquet"

PLAYER_1 = "J. Sinner"
PLAYER_2 = "C. Alcaraz"
PLAYER_1_ID = 1
PLAYER_2_ID = 2


# DATA LOADING
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


# 3. PARSER
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

def calculate_metrics_with_intermediates(player_id, match_df):
    """Returns both the raw percentages and the intermediate raw counts/text for explanations."""
    if match_df.empty:
        return [0] * 7, ["No Data"] * 7

    serve_mask = match_df['Svr'] == player_id
    return_mask = match_df['Svr'] != player_id
    
    # Serve
    serves_df = match_df[serve_mask].copy()
    total_serves = len(serves_df)
    if total_serves > 0:
        first_in_mask = ~serves_df['1st'].astype(str).str.match(r'^[4560][nwdexg]')
        first_in = first_in_mask.sum()
        first_won = serves_df[first_in_mask & (serves_df['PtWinner'] == player_id)].shape[0]
        second_in_mask = ~first_in_mask 
        second_won = serves_df[second_in_mask & (serves_df['PtWinner'] == player_id)].shape[0]
        
        first_in_pct = first_in / total_serves
        first_won_pct = first_won / first_in if first_in > 0 else 0
        second_won_pct = second_won / second_in_mask.sum() if second_in_mask.sum() > 0 else 0
        
        serve_eff = (first_in_pct * first_won_pct) + ((1 - first_in_pct) * second_won_pct)
        
        aces = serves_df.apply(lambda row: extract_shot_info(row['1st'])[2] or extract_shot_info(row['2nd'])[2], axis=1).sum()
        second_fault_mask = serves_df['2nd'].astype(str).str.match(r'^[4560][nwdexg]')
        double_faults = (second_in_mask & second_fault_mask).sum()
        
        serve_qual = (0.4 * first_in_pct) + (0.3 * (aces / total_serves)) + (0.3 * (1 - (double_faults / total_serves)))
        
        eff_text = f"1st In: {first_in}/{total_serves} | 1st Won: {first_won}/{first_in} | 2nd Won: {second_won}/{second_in_mask.sum()}"
        qual_text = f"1st In: {first_in_pct:.1%} | Aces: {aces} | DFs: {double_faults}"
    else:
        serve_eff, serve_qual = 0, 0
        eff_text, qual_text = "0 serves", "0 serves"

    # Baseline
    rally_lengths = match_df.apply(lambda row: len(re.findall(r'[fbrsvzuylmhiqt]', str(row['1st']))) + len(re.findall(r'[fbrsvzuylmhiqt]', str(row['2nd']))), axis=1)
    baseline_pts = match_df[rally_lengths > 4]
    baseline_won = len(baseline_pts[baseline_pts['PtWinner'] == player_id])
    baseline_tot = len(baseline_pts)
    baseline_dom = baseline_won / baseline_tot if baseline_tot > 0 else 0
    base_text = f"Won {baseline_won} out of {baseline_tot} rallies (>4 shots)"

    # Break Points
    bp_mask = match_df.apply(lambda row: is_break_point(row['Pts'], row['Svr'], player_id), axis=1)
    bp_chances = match_df[bp_mask]
    bp_won = len(bp_chances[bp_chances['PtWinner'] == player_id])
    bp_tot = len(bp_chances)
    bp_conversion = bp_won / bp_tot if bp_tot > 0 else 0
    bp_text = f"Converted {bp_won} out of {bp_tot} break point opportunities"

    # Returns
    return_pts = match_df[return_mask]
    ret_won = len(return_pts[return_pts['PtWinner'] == player_id])
    ret_tot = len(return_pts)
    return_eff = ret_won / ret_tot if ret_tot > 0 else 0
    ret_text = f"Won {ret_won}/{ret_tot} return points"

    # Groundstrokes
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
    
    bh_text = f"Won {bh_won}/{bh_total} rallies ending on backhand wing"
    fh_text = f"Hit {fh_winners}/{total_winners} total baseline winners via forehand"

    raw_metrics = [serve_eff, serve_qual, baseline_dom, bp_conversion, return_eff, bh_solidity, fh_dominance]
    intermediates = [eff_text, qual_text, base_text, bp_text, ret_text, bh_text, fh_text]
    return [m * 100 for m in raw_metrics], intermediates


# COMPUTE BASE TRACES
vals_a_raw, inter_a = calculate_metrics_with_intermediates(PLAYER_1_ID, df)
vals_b_raw, inter_b = calculate_metrics_with_intermediates(PLAYER_2_ID, df)

ALL_CATEGORIES = [
    "Serve Efficiency",
    "Serve Quality",
    "Baseline Dominance",
    "Break Point Conversion",
    "Return Efficiency",
    "Backhand Solidity",
    "Forehand Dominance"
]

CATEGORY_DESCRIPTIONS = {
    "Serve Efficiency": "Combines first- and second-serve win percentages to measure overall service game security.",
    "Serve Quality": "Weights first-serve accuracy, total aces, and penalizes double faults to evaluate service pressure.",
    "Baseline Dominance": "Assesses point-winning effectiveness during extended exchanges exceeding four shots.",
    "Break Point Conversion": "Shows the percentage of break point opportunities successfully converted into breaks of serve.",
    "Return Efficiency": "Tracks the total percentage of points won while the opponent was serving.",
    "Backhand Solidity": "Measures how often a player wins rallies ending on the backhand side.",
    "Forehand Dominance": "Evaluates the proportion of total pure winners obtained via the forehand."
}


# UI: DESCRIPTION AND FILTERS
st.markdown("<h2 style='text-align: center; color: #2C3E50;'>Playing Style Comparison - Radar Chart</h2>", unsafe_allow_html=True)

st.markdown(
    """
    <div style='text-align: center; color: #7F8C8D; margin-bottom: 30px;'>
        This radar chart compares the playing styles of Sinner and Alcaraz by combining their serve, return, baseline, and groundstroke statistics into a single visual profile. It allows you to quickly see where their tactical game styles overlap or differ.    </div>
    """, 
    unsafe_allow_html=True
)

st.markdown("#### Select metrics to compare:")

cols = st.columns(2)
selected_categories = []

for i, category in enumerate(ALL_CATEGORIES):
    with cols[i % 2]:
        label = f"**{category.upper()}**\n\n{CATEGORY_DESCRIPTIONS[category]}"
        if st.checkbox(label, value=True, key=f"chk_{i}"):
            selected_categories.append(category)

st.markdown("---")

if len(selected_categories) < 3:
    st.warning("⚠️ Please select at least 3 metrics to form a proper radar chart.")
    st.stop()

# Filter values
indices = [ALL_CATEGORIES.index(cat) for cat in selected_categories]
vals_a = [vals_a_raw[i] for i in indices]
vals_b = [vals_b_raw[i] for i in indices]
categories = [ALL_CATEGORIES[i] for i in indices]

# Close radar shapes
vals_a += vals_a[:1]
vals_b += vals_b[:1]
categories += categories[:1]

# PLOTLY RADAR
fig = go.Figure()

fig.add_trace(go.Scatterpolar(
    r=vals_a,
    theta=categories,
    fill="toself",
    name=PLAYER_1,
    line_color="#4A90E2",
    fillcolor="rgba(74, 144, 226, 0.25)",
    hovertemplate="<b>%{theta}</b><br>Sinner: %{r:.1f}%<extra></extra>"
))

fig.add_trace(go.Scatterpolar(
    r=vals_b,
    theta=categories,
    fill="toself",
    name=PLAYER_2,
    line_color="#E87D3E",
    fillcolor="rgba(232, 125, 62, 0.25)",
    hovertemplate="<b>%{theta}</b><br>Alcaraz: %{r:.1f}%<extra></extra>"
))

fig.update_layout(
    polar=dict(
        radialaxis=dict(
            visible=True, 
            range=[0, 100], 
            tickvals=[0, 20, 40, 60, 80, 100],
            ticktext=["0%", "20%", "40%", "60%", "80%", "100%"],
            gridcolor='#EAEAEA',
            linecolor='#EAEAEA',
            tickfont=dict(color='#2C3E50')
        ),
        angularaxis=dict(
            gridcolor='#EAEAEA',
            tickfont=dict(color='#2C3E50', size=11, family="sans-serif")
        ),
        bgcolor='white'
    ),
    paper_bgcolor='rgba(0,0,0,0)', 
    font=dict(color='#2C3E50'),
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

# 7. SUMMARY METRICS
st.markdown("---")

sinner_avg = np.mean([vals_a_raw[i] for i in indices])
alcaraz_avg = np.mean([vals_b_raw[i] for i in indices])

sinner_max_idx = np.argmax([vals_a_raw[i] for i in indices])
alcaraz_max_idx = np.argmax([vals_b_raw[i] for i in indices])

sinner_peak_name = selected_categories[sinner_max_idx]
alcaraz_peak_name = selected_categories[alcaraz_max_idx]

# Split into 2 clean columns instead of 3 to remove "Compared Dimensions" entirely
mc1, mc2 = st.columns(2)

mc1.metric(
    label=PLAYER_1,
    value=f"{sinner_avg:.1f}% average score",
    delta=f"Peak dimension: {sinner_peak_name}"
)

mc2.metric(
    label=PLAYER_2,
    value=f"{alcaraz_avg:.1f}% average score",
    delta=f"Peak dimension: {alcaraz_peak_name}"
)


# RAW DATA TABLE
with st.expander("Show raw data"):
    raw_table_data = {
        "Metric Dimension": ALL_CATEGORIES,
        f"{PLAYER_1} Score (%)": [f"{v:.1f}%" for v in vals_a_raw],
        f"{PLAYER_1} Core Counts & Formulas": inter_a,
        f"{PLAYER_2} Score (%)": [f"{v:.1f}%" for v in vals_b_raw],
        f"{PLAYER_2} Core Counts & Formulas": inter_b
    }
    st.dataframe(pd.DataFrame(raw_table_data), use_container_width=True)