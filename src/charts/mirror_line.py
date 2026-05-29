import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ==========================================
# 1. ROBUST DATA LOADING
# ==========================================
# Get the absolute path of the current script (mirror_line_chart.py)
# .parent goes to 'charts', .parent.parent goes to 'src', .parent.parent.parent goes to 'repo root'
repo_root = Path(__file__).resolve().parent.parent.parent
data_path = repo_root / 'data' / 'processed' / 'sinner_alcaraz_2025.parquet'

print(f"Loading data from: {data_path}")
df = pd.read_parquet(data_path)

# Sort by point progression
df = df.sort_values(by='Pt').reset_index(drop=True)

# ==========================================
# 2. CALCULATE WIN PROBABILITY (Momentum)
# ==========================================
momentum = []
current_momentum = 0

for index, row in df.iterrows():
    set_diff = row['Set1'] - row['Set2']
    gm_diff = row['Gm1'] - row['Gm2']
    
    if row['PtWinner'] == 1:
        current_momentum += 1.5
    elif row['PtWinner'] == 2:
        current_momentum -= 1.5
        
    total_score = (set_diff * 40) + (gm_diff * 10) + current_momentum
    momentum.append(total_score)

def sigmoid(x):
    return 100 / (1 + np.exp(-x / 30))

df['Win_Prob'] = [sigmoid(m) for m in momentum]

# Find ends of sets
end_of_sets = df[df['Set1'] + df['Set2'] > df['Set1'].shift(1).fillna(0) + df['Set2'].shift(1).fillna(0)].index.tolist()

# ==========================================
# 3. PLOT MIRROR LINE CHART
# ==========================================
fig, ax = plt.subplots(figsize=(15, 6), facecolor='#111111')
ax.set_facecolor('#111111')

x = df['Pt']
y = df['Win_Prob']

ax.axhline(50, color='white', linewidth=1, linestyle='--', alpha=0.5)
ax.plot(x, y, color='white', linewidth=1.5, alpha=0.8)

# Fill areas
ax.fill_between(x, y, 50, where=(y > 50), color='#FF8C00', alpha=0.6, interpolate=True) # Sinner
ax.fill_between(x, y, 50, where=(y < 50), color='#00CED1', alpha=0.6, interpolate=True) # Alcaraz

# Set separators
for i, pt_idx in enumerate(end_of_sets):
    ax.axvline(df.loc[pt_idx, 'Pt'], color='gray', linestyle=':', alpha=0.7)
    ax.text(df.loc[pt_idx, 'Pt'], 95, f'End of Set {i+1}', color='white', rotation=90, verticalalignment='top', fontsize=9)

# Match Point Annotation (4th Set Peak)
if len(end_of_sets) >= 3:
    start_4th = end_of_sets[2]
    end_4th = end_of_sets[3] if len(end_of_sets) > 3 else len(df)-1
    match_point_idx = df.loc[start_4th:end_4th, 'Win_Prob'].idxmax()
    mp_x = df.loc[match_point_idx, 'Pt']
    mp_y = df.loc[match_point_idx, 'Win_Prob']
    
    ax.annotate('Sinner Match Point\n(followed by drop)', 
                xy=(mp_x, mp_y), xytext=(mp_x - 40, 20),
                arrowprops=dict(facecolor='yellow', shrink=0.05, width=1.5, headwidth=8),
                color='yellow', fontsize=10, fontweight='bold', ha='center')

# Formatting
ax.set_ylim(0, 100)
ax.set_xlim(df['Pt'].min(), df['Pt'].max())
ax.set_yticks([0, 25, 50, 75, 100])
ax.set_yticklabels(['100% Alcaraz', '75%', '50% (Tie)', '75%', '100% Sinner'], color='white')
ax.tick_params(axis='x', colors='white')
ax.set_title("Win Probability Progression: Sinner vs Alcaraz", color='white', fontsize=14, pad=15)
ax.set_xlabel("Point Number (Chronological)", color='white')

plt.tight_layout()
plt.savefig(Path(__file__).resolve().parent / 'pngs' / "mirror_line_chart.png", dpi=300, bbox_inches='tight')