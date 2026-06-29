"""
2_Line_Chart.py
------------------------
Win Probability Line Chart
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
st.set_page_config(page_title="RG25 – Line Chart", layout="wide")

st.markdown("<h2 style='text-align: center; color: #2C3E50;'>Momentum Progression - Line Chart</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #7F8C8D;'>This line chart visualizes the match progression through a dynamic win probability index based on point-by-point score changes and game/set context. The 50% baseline represents a balanced state, while fluctuations above or below highlight momentum shifts between Sinner and Alcaraz.</p>", unsafe_allow_html=True)

# ==========================================
# 2. ROBUST DATA LOADING
# ==========================================
@st.cache_data
def load_data():
    repo_root = Path(__file__).resolve().parent.parent.parent
    data_path = repo_root / 'data' / 'processed' / 'sinner_alcaraz_2025.parquet'
    
    try:
        df = pd.read_parquet(data_path)
    except FileNotFoundError:
        try:
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
    set1_col = 'Set1' if 'Set1' in df.columns else 'set1'
    set2_col = 'Set2' if 'Set2' in df.columns else 'set2'
    
    set_diff = row[set1_col] - row[set2_col]
    gm_diff = row['Gm1'] - row['Gm2']

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
df['Win_Prob_Smooth'] = df['Win_Prob_Sinner'].rolling(window=5, min_periods=1, center=True).mean()

df.loc[df.index[-1], 'Win_Prob_Smooth'] = 0.0 
df['Win_Prob_Alcaraz'] = 100 - df['Win_Prob_Smooth']

set1_col = 'Set1' if 'Set1' in df.columns else 'set1'
set2_col = 'Set2' if 'Set2' in df.columns else 'set2'
df['CompletedSets'] = df[set1_col] + df[set2_col]
end_of_sets = df[df['CompletedSets'] > df['CompletedSets'].shift(1).fillna(0)].index.tolist()

# ==========================================
# 4. SEGMENT LINE BY DOMINANCE (COLOR SPLIT)
# ==========================================
x_sinner, y_sinner = [], []
x_alcaraz, y_alcaraz = [], []

pts = df['Pt'].values
probs = df['Win_Prob_Smooth'].values

for i in range(len(df) - 1):
    pt1, pt2 = pts[i], pts[i+1]
    y1, y2 = probs[i], probs[i+1]
    
    # Segment stays above 50%
    if y1 >= 50 and y2 >= 50:
        x_sinner.extend([pt1, pt2, None])
        y_sinner.extend([y1, y2, None])
    # Segment stays below 50%
    elif y1 <= 50 and y2 <= 50:
        x_alcaraz.extend([pt1, pt2, None])
        y_alcaraz.extend([y1, y2, None])
    # Segment crosses the 50% line -> calculate exact intersection
    else:
        if y1 != y2:
            m = (y2 - y1) / (pt2 - pt1)
            c = y1 - m * pt1
            x_cross = (50 - c) / m
        else:
            x_cross = pt1 + (pt2 - pt1) / 2
            
        if y1 > 50:
            x_sinner.extend([pt1, x_cross, None])
            y_sinner.extend([y1, 50.0, None])
            x_alcaraz.extend([x_cross, pt2, None])
            y_alcaraz.extend([50.0, y2, None])
        else:
            x_alcaraz.extend([pt1, x_cross, None])
            y_alcaraz.extend([y1, 50.0, None])
            x_sinner.extend([x_cross, pt2, None])
            y_sinner.extend([50.0, y2, None])

# ==========================================
# 5. PLOT CHART
# ==========================================
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df['Pt'], 
    y=df['Win_Prob_Smooth'],
    mode='markers',
    marker=dict(color='rgba(0,0,0,0)', size=8),
    name="Hover",
    showlegend=False,
    hovertemplate=(
        "<b>Point %{x}</b><br>"
        "Sinner Probability: %{y:.1f}%<br>"
        "Alcaraz Probability: %{customdata:.1f}%<extra></extra>"
    ),
    customdata=df['Win_Prob_Alcaraz']
))

# Sinner colored segment
fig.add_trace(go.Scatter(
    x=x_sinner, y=y_sinner,
    mode='lines',
    line=dict(color='#4A90E2', width=4.5), # Sinner Blue
    name="Sinner Advantage",
    hoverinfo='skip'
))

# Alcaraz colored segment
fig.add_trace(go.Scatter(
    x=x_alcaraz, y=y_alcaraz,
    mode='lines',
    line=dict(color='#E87D3E', width=4.5), # Alcaraz Orange
    name="Alcaraz Advantage",
    hoverinfo='skip'
))

# Center tie line (50%)
fig.add_hline(y=50, line_dash="dash", line_color="#A0A0A0", line_width=2, opacity=0.8)

# End of sets
set_labels = [
    "End Set 1<br>4-6 Sinner",
    "End Set 2<br>7-6 Sinner",
    "End Set 3<br>6-4 Alcaraz",
    "End Set 4<br>6-4 Alcaraz",
    "Match End<br>10-2 STB"
]

for i, idx in enumerate(end_of_sets):
    pt_x = df.loc[idx, 'Pt']
    fig.add_vline(x=pt_x, line_dash="dot", line_color="#B0B0B0", line_width=1.5)
    
    label = set_labels[i] if i < len(set_labels) else f"End Set {i+1}"
    fig.add_annotation(
        x=pt_x, y=96, 
        text=label, textangle=0, 
        font=dict(color="#2C3E50", size=10), 
        showarrow=False,
        xanchor="right" if i == len(end_of_sets)-1 else "left",
        xshift=-5 if i == len(end_of_sets)-1 else 5,
        bgcolor="rgba(255, 255, 255, 0.85)",
        borderpad=3
    )

fig.update_layout(
    yaxis=dict(
        range=[0, 100], 
        tickvals=[0, 25, 50, 75, 100], 
        ticktext=['<b>100% Alcaraz</b>', '75% Alcaraz', '<b>50% Tie</b>', '75% Sinner', '<b>100% Sinner</b>'],
        gridcolor='#EAEAEA',
        zeroline=False
    ),
    xaxis=dict(
        title="Match Point Number",
        gridcolor='#EAEAEA',
        zeroline=False
    ),
    plot_bgcolor='white', 
    paper_bgcolor='rgba(0,0,0,0)', 
    font=dict(color='#2C3E50'),
    height=600,
    showlegend=True,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.2,
        xanchor="center",
        x=0.5
    ),
    margin=dict(l=20, r=20, t=40, b=20)
)

st.plotly_chart(fig, width="stretch", config={"displayModeBar": True, "scrollZoom": True})

# ==========================================
# 6. SUMMARY METRICS ROW
# ==========================================
st.markdown("---")

tot_points = len(df)
sinner_points = df[df['PtWinner'] == 1].shape[0]
alcaraz_points = df[df['PtWinner'] == 2].shape[0]

sinner_max_prob = df['Win_Prob_Smooth'].max()
alcaraz_max_prob = df['Win_Prob_Alcaraz'].max()

mc1, mc2, mc3 = st.columns(3)

mc1.metric(
    label="J. Sinner",
    value=f"{sinner_points} points won",
    delta=f"Max momentum peak: {sinner_max_prob:.1f}%"
)

mc2.metric(
    label="C. Alcaraz",
    value=f"{alcaraz_points} points won",
    delta=f"Max momentum peak: {alcaraz_max_prob:.1f}%"
)

mc3.metric(
    label="Total points played",
    value=str(tot_points)
)

with st.expander("Show raw data"):
    st.dataframe(df[['Pt', 'Set1', 'Set2', 'Gm1', 'Gm2', 'Pts', 'Svr', 'PtWinner', 'Win_Prob_Smooth']], use_container_width=True)