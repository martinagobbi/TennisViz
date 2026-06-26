"""
line_chart_view.py
------------------------
Standalone Streamlit View for Win Probability Line Chart
Sinner vs Alcaraz
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path

# ==========================================
# 1. SETUP STREAMLIT
# ==========================================
st.set_page_config(page_title="Match Momentum", layout="wide")

st.markdown("<h2 style='text-align: center;'>Momentum Progression - Line Chart</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888;'>This line chart models the real-time narrative and competitive equilibrium of the match by converting point-by-point score variations and historical set/game contexts into a dynamic win probability index. Styled as a \"Tug-of-War,\" the chart uses a central baseline representing a perfect 50% deadlock. As points are played, the momentum line shifts upward toward 100% dominance for Sinner or down toward 100% dominance for Alcaraz.</p>", unsafe_allow_html=True)

# ==========================================
# 2. ROBUST DATA LOADING
# ==========================================
@st.cache_data
def load_data():
    # We add ONE MORE .parent because this script is inside src/charts/
    repo_root = Path(__file__).resolve().parent.parent.parent 
    
    data_path = repo_root / 'data' / 'processed' / 'sinner_alcaraz_2025.parquet'
    
    try:
        df = pd.read_parquet(data_path)
    except FileNotFoundError:
        # Fallback to CSV if the parquet file is not found
        try:
             # Just in case the CSV is in the main folder or processed folder
             df = pd.read_csv(repo_root / 'Dataset Sinner VS Alcaraz - Foglio1.csv')
        except FileNotFoundError:
             st.error(f"No dataset found. Looking in: {data_path}")
             return pd.DataFrame()
             
    df = df.sort_values(by='Pt').reset_index(drop=True)
    return df

df = load_data()

if df.empty:
    st.stop()

# ==========================================
# 3. CALCULATE MATCH-AWARE WIN PROBABILITY
# ==========================================
momentum = []
current_momentum = 0

for _, row in df.iterrows():
    # Handle column names dynamically just in case of capitalization differences
    set1_col = 'Set1' if 'Set1' in df.columns else 'set1'
    set2_col = 'Set2' if 'Set2' in df.columns else 'set2'
    
    set_diff = row[set1_col] - row[set2_col]
    gm_diff = row['Gm1'] - row['Gm2']

    # Momentum decay: older points matter less than recent ones
    current_momentum *= 0.96

    if row['PtWinner'] == 1:
        current_momentum += 1.8
    elif row['PtWinner'] == 2:
        current_momentum -= 1.8

    total_score = (set_diff * 28) + (gm_diff * 10) + current_momentum
    momentum.append(total_score)

def sigmoid(x):
    return 100 / (1 + np.exp(-x / 24))

df['Win_Prob_Sinner'] = [sigmoid(m) for m in momentum]

# Smoothing the curve to make it more readable
df['Win_Prob_Smooth'] = df['Win_Prob_Sinner'].rolling(window=5, min_periods=1, center=True).mean()

# FINAL CORRECTION: Force 100% for Alcaraz (0% Sinner) at the last point
# Since Alcaraz won the match, the final probability must reflect absolute certainty.
df.loc[df.index[-1], 'Win_Prob_Smooth'] = 0.0 

df['Win_Prob_Alcaraz'] = 100 - df['Win_Prob_Smooth']

# Find the end of the sets
set1_col = 'Set1' if 'Set1' in df.columns else 'set1'
set2_col = 'Set2' if 'Set2' in df.columns else 'set2'
df['CompletedSets'] = df[set1_col] + df[set2_col]
end_of_sets = df[df['CompletedSets'] > df['CompletedSets'].shift(1).fillna(0)].index.tolist()

# ==========================================
# 4. PLOT PURE LINE CHART (PLOTLY)
# ==========================================
fig = go.Figure()

# Adding the single line: THICK and WITHOUT FILL
fig.add_trace(go.Scatter(
    x=df['Pt'], 
    y=df['Win_Prob_Smooth'],
    mode='lines',
    line=dict(color='red', width=4.5), # Very thick Yellow/Gold line (bolder)
    name="Win Probability",
    hovertemplate=(
        "<b>Point %{x}</b><br>"
        "Sinner Probability: %{y:.1f}%<br>"
        "Alcaraz Probability: %{customdata:.1f}%<extra></extra>"
    ),
    customdata=df['Win_Prob_Alcaraz']
))

# Center tie line (50%)
fig.add_hline(y=50, line_dash="dash", line_color="#888", opacity=0.7)

# Custom labels for the end of the sets
set_labels = [
    "End Set 1<br>4-6 Sinner",
    "End Set 2<br>7-6 Sinner",
    "End Set 3<br>6-4 Alcaraz",
    "End Set 4<br>6-4 Alcaraz",
    "Match End<br>10-2 STB"
]

for i, idx in enumerate(end_of_sets):
    pt_x = df.loc[idx, 'Pt']
    fig.add_vline(x=pt_x, line_dash="dot", line_color="#555", line_width=1.5)
    
    label = set_labels[i] if i < len(set_labels) else f"End Set {i+1}"
    fig.add_annotation(
        x=pt_x, y=95, 
        text=label, textangle=0, 
        font=dict(color="#AAA", size=10), 
        showarrow=False,
        xanchor="right" if i == len(end_of_sets)-1 else "left",
        xshift=-5 if i == len(end_of_sets)-1 else 5
    )

# Layout Formatting
fig.update_layout(
    yaxis=dict(
        range=[0, 100], 
        tickvals=[0, 25, 50, 75, 100], 
        ticktext=['<b>100% Alcaraz</b>', '75% Alcaraz', '<b>50% Tie</b>', '75% Sinner', '<b>100% Sinner</b>']
    ),
    xaxis_title="Match Point Number", 
    paper_bgcolor='rgba(0,0,0,0)', 
    plot_bgcolor='#1E1E1E', 
    height=600,
    showlegend=False,
    margin=dict(l=20, r=20, t=40, b=20)
)

st.plotly_chart(fig, width="stretch")