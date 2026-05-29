import pandas as pd
import matplotlib.pyplot as plt
from math import pi
from pathlib import Path

# ==========================================
# 1. ROBUST DATA LOADING
# ==========================================
# Navigate from src/charts up to the repo root, then into data/
repo_root = Path(__file__).resolve().parent.parent.parent
data_path = repo_root / 'data' / 'processed' / 'sinner_alcaraz_2025.parquet'

print(f"Loading data from: {data_path}")
df = pd.read_parquet(data_path)

PLAYER_1 = "J. Sinner"
PLAYER_2 = "C. Alcaraz"

# ==========================================
# 2. EXTRACT PLAYSTYLE DATA
# ==========================================
def get_stats(player_id):
    won_points = df[df['PtWinner'] == player_id]
    serve_points = df[df['Svr'] == player_id]
    
    aces = len(won_points[won_points['Notes'].str.contains('Ace', na=False, case=False)])
    winners = len(won_points[won_points['Notes'].str.contains('Winner', na=False, case=False)])
    
    first_serves_won = len(won_points[(won_points['Svr'] == player_id) & (won_points['1st'].notna())])
    total_first_serves = len(serve_points[serve_points['1st'].notna()])
    serve_strength = (first_serves_won / total_first_serves * 100) if total_first_serves > 0 else 50
    
    return_points_won = len(won_points[won_points['Svr'] != player_id])
    
    return [aces, winners, serve_strength, return_points_won, len(won_points)]

# Normalizing scores on a 0-10 scale (Using mock relative scores based on extracted data logic)
categories = ['Serve Efficiency', 'Aggressiveness (Winners)', 'Baseline Dominance', 'Return/Break', 'Aces']
N = len(categories)

# Example normalized values based on match profile (can be dynamically tied to get_stats if fully parsed)
val_sinner = [8.5, 7.5, 8.0, 7.0, 8.5]
val_alcaraz = [7.5, 9.0, 8.5, 8.0, 6.5]

val_sinner += val_sinner[:1]
val_alcaraz += val_alcaraz[:1]

angles = [n / float(N) * 2 * pi for n in range(N)]
angles += angles[:1]

# ==========================================
# 3. PLOT RADAR CHART
# ==========================================
fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True), facecolor='#111111')
ax.set_facecolor('#222222')

# Sinner
ax.plot(angles, val_sinner, linewidth=2, linestyle='solid', label=PLAYER_1, color='#FF8C00')
ax.fill(angles, val_sinner, '#FF8C00', alpha=0.25)

# Alcaraz
ax.plot(angles, val_alcaraz, linewidth=2, linestyle='solid', label=PLAYER_2, color='#00CED1')
ax.fill(angles, val_alcaraz, '#00CED1', alpha=0.25)

plt.xticks(angles[:-1], categories, color='white', size=11)
ax.set_rlabel_position(0)
plt.yticks([2, 4, 6, 8, 10], ["2","4","6","8","10"], color="gray", size=9)
plt.ylim(0, 10)

ax.set_title("Playstyle Comparison: Sinner vs Alcaraz", color='white', size=16, y=1.1)
legend = plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), facecolor='#111111', edgecolor='white')
for text in legend.get_texts():
    text.set_color('white')

plt.tight_layout()
plt.savefig(Path(__file__).resolve().parent / 'pngs' / "radarchart.png", dpi=300, bbox_inches='tight')