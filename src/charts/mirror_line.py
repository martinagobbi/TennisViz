import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.patches import Patch

# ==========================================
# 1. ROBUST DATA LOADING
# ==========================================
repo_root = Path(__file__).resolve().parent.parent.parent
data_path = repo_root / 'data' / 'processed' / 'sinner_alcaraz_2025.parquet'

print(f"Loading data from: {data_path}")
df = pd.read_parquet(data_path)

df = df.sort_values(by='Pt').reset_index(drop=True)

# ==========================================
# 2. CALCULATE MATCH-AWARE WIN PROBABILITY
# ==========================================
momentum = []
current_momentum = 0

for _, row in df.iterrows():
    set_diff = row['Set1'] - row['Set2']
    gm_diff = row['Gm1'] - row['Gm2']

    # Recent momentum matters more than very old momentum
    current_momentum *= 0.96

    if row['PtWinner'] == 1:
        current_momentum += 1.8
    elif row['PtWinner'] == 2:
        current_momentum -= 1.8

    # Match-aware but not overly rigid:
    # set_diff keeps Sinner favored after winning early sets,
    # gm_diff and point momentum let the chart react during each set.
    total_score = (
        set_diff * 28
        + gm_diff * 10
        + current_momentum
    )

    momentum.append(total_score)

def sigmoid(x):
    return 100 / (1 + np.exp(-x / 24))

df['Win_Prob'] = [sigmoid(m) for m in momentum]

df['Win_Prob_Smooth'] = (
    df['Win_Prob']
    .rolling(window=5, min_periods=1, center=True)
    .mean()
)

# Find ends of sets
df['CompletedSets'] = df['Set1'] + df['Set2']
end_of_sets = df[
    df['CompletedSets'] > df['CompletedSets'].shift(1).fillna(0)
].index.tolist()

# ==========================================
# 3. PLOT MIRROR LINE CHART
# ==========================================
plt.style.use('dark_background')

fig, ax = plt.subplots(figsize=(16, 6.2), facecolor='#141414')
ax.set_facecolor('#151515')

x = df['Pt'].to_numpy()
y = df['Win_Prob_Smooth'].to_numpy()
baseline = 50

sinner_color = '#C87500'
alcaraz_color = '#1F9EA0'
line_color = '#9A9A9A'
grid_color = '#333333'
text_color = '#D8D8D8'

# Horizontal grid/reference lines
for level in [0, 25, 50, 75, 100]:
    ax.axhline(level, color=grid_color, linewidth=1, alpha=0.75, zorder=0)

ax.axhline(
    baseline,
    color='#CFCFCF',
    linewidth=1.1,
    linestyle='--',
    alpha=0.7,
    zorder=2
)

# Filled mirror areas
ax.fill_between(
    x,
    y,
    baseline,
    where=y >= baseline,
    color=sinner_color,
    alpha=0.92,
    interpolate=True,
    zorder=3
)

ax.fill_between(
    x,
    y,
    baseline,
    where=y < baseline,
    color=alcaraz_color,
    alpha=0.88,
    interpolate=True,
    zorder=3
)

# Probability / momentum line
ax.plot(
    x,
    y,
    color=line_color,
    linewidth=1.35,
    alpha=0.95,
    zorder=4
)

# ==========================================
# 4. SET SEPARATORS + SET LABELS
# ==========================================
set_labels = [
    "Set 1\nEnd of Set 1: 4-6 Sinner",
    "Set 2\nEnd of Set 2: 7-6 Sinner",
    "Set 3\nEnd of Set 3: 6-4 Alcaraz",
    "Set 4\nEnd of Set 4: 6-4 Alcaraz",
    "Final Set & Super Tie-Break\nMatch End: 7-6 Alcaraz - 10-2 STB"
]

bounds = [df['Pt'].min()]

for i, pt_idx in enumerate(end_of_sets):
    set_end_pt = df.loc[pt_idx, 'Pt']
    bounds.append(set_end_pt)

    ax.axvline(
        set_end_pt,
        color='#6A6A6A',
        linestyle=':',
        linewidth=1.1,
        alpha=0.85,
        zorder=2
    )

    ax.text(
        set_end_pt,
        3,
        f"End Set {i + 1}",
        color='#BDBDBD',
        fontsize=8,
        rotation=90,
        ha='right',
        va='bottom',
        alpha=0.85
    )

bounds.append(df['Pt'].max())

for i in range(min(len(set_labels), len(bounds) - 1)):
    mid = (bounds[i] + bounds[i + 1]) / 2

    ax.text(
        mid,
        96,
        set_labels[i],
        color=text_color,
        fontsize=9,
        fontweight='bold',
        ha='center',
        va='top',
        alpha=0.95
    )

# ==========================================
# 5. ANNOTATIONS
# ==========================================
if len(end_of_sets) >= 4:
    final_start = end_of_sets[3]
else:
    final_start = int(len(df) * 0.78)

final_df = df.loc[final_start:].copy()

if not final_df.empty:
    mp_idx = final_df['Win_Prob_Smooth'].idxmax()
    mp_x = df.loc[mp_idx, 'Pt']
    mp_y = df.loc[mp_idx, 'Win_Prob_Smooth']

    ax.annotate(
        "Sinner Match Points\n(Saved)",
        xy=(mp_x, mp_y),
        xytext=(mp_x - 45, 82),
        color='#E7C66A',
        fontsize=9,
        fontweight='bold',
        ha='center',
        arrowprops=dict(
            arrowstyle='-|>',
            color='#E7C66A',
            lw=1.2,
            shrinkA=3,
            shrinkB=3
        ),
        zorder=5
    )

    ax.annotate(
        "Final Super Tie-Break:\nPoints 1 to 10-2",
        xy=(df['Pt'].max(), y[-1]),
        xytext=(df['Pt'].max() - 55, 18),
        color='#D8C174',
        fontsize=9,
        fontweight='bold',
        ha='center',
        arrowprops=dict(
            arrowstyle='-|>',
            color='#D8C174',
            lw=1.1,
            linestyle='--',
            shrinkA=3,
            shrinkB=3
        ),
        zorder=5
    )

# ==========================================
# 6. FORMATTING
# ==========================================
ax.set_ylim(0, 100)
ax.set_xlim(df['Pt'].min(), df['Pt'].max())

ax.set_yticks([0, 25, 50, 75, 100])
ax.set_yticklabels(
    ['100% Alcaraz', '75%', '50% (Tie)', '75%', '100% Sinner'],
    color=text_color,
    fontsize=9
)

ax.tick_params(axis='x', colors=text_color, labelsize=9)
ax.tick_params(axis='y', colors=text_color, length=0)

for spine in ax.spines.values():
    spine.set_color('#222222')

ax.set_title(
    "Faithfully Corrected Win Probability: Sinner vs Alcaraz (The 5-Set Battle)",
    color=text_color,
    fontsize=14,
    fontweight='bold',
    pad=16
)

ax.set_xlabel("Point Number", color=text_color, fontsize=9, labelpad=10)

legend_elements = [
    Patch(facecolor=sinner_color, edgecolor='none', label='Sinner'),
    Patch(facecolor=alcaraz_color, edgecolor='none', label='Alcaraz')
]

legend = ax.legend(
    handles=legend_elements,
    loc='lower left',
    frameon=True,
    facecolor='#181818',
    edgecolor='#333333',
    fontsize=8
)

for text in legend.get_texts():
    text.set_color(text_color)

plt.tight_layout()

output_dir = Path(__file__).resolve().parent / 'pngs'
output_dir.mkdir(parents=True, exist_ok=True)

output_path = output_dir / "mirror_line_chart.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
plt.close()

print(f"Saved chart to: {output_path}")
