import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from math import pi
from pathlib import Path
import re

# ==========================================
# 1. DATA LOADING
# ==========================================
repo_root = Path(__file__).resolve().parent.parent.parent
data_path = repo_root / 'data' / 'processed' / 'sinner_alcaraz_2025.parquet'

try:
    df = pd.read_parquet(data_path)
except FileNotFoundError:
    print(f"Error: File not found at {data_path}")
    df = pd.DataFrame() 

PLAYER_1 = "J. Sinner"
PLAYER_2 = "C. Alcaraz"
PLAYER_1_ID = 1
PLAYER_2_ID = 2

# ==========================================
# 2. MATCH CHARTING PROJECT PARSER
# ==========================================
def is_break_point(pts_str, server_id, target_player_id):
    """Determina se il punteggio attuale è palla break per il giocatore target."""
    if pd.isna(pts_str) or target_player_id == server_id:
        return False
    
    if server_id == 1 and target_player_id == 2:
        return pts_str in ['0-40', '15-40', '30-40', '40-AD']
    elif server_id == 2 and target_player_id == 1:
        return pts_str in ['40-0', '40-15', '40-30', 'AD-40']
    return False

def extract_shot_info(rally_str):
    """Analizza la stringa MCP per estrarre tipo di colpo finale, outcome e se è ace."""
    if pd.isna(rally_str):
        return None, None, False
    
    # Verifica se è un Ace (contiene * e non ha lettere di scambi)
    is_ace = '*' in str(rally_str) and len(re.findall(r'[fbrsvzuylmhiqt]', str(rally_str))) == 0
    
    # Estrae tutti i colpi (lettere)
    shots = re.findall(r'([fbrsvzuylmhiqt][0-3]?[7-9]?[\+\-\=\;\^]?[\*\@\#nwdxe\!]?)', str(rally_str))
    
    terminal_shot = None
    outcome = None
    
    if shots:
        last_shot = shots[-1]
        # Classificazione Dritto (f, r, v, u, l, h, j)
        if last_shot[0] in ['f', 'r', 'v', 'u', 'l', 'h', 'j']:
            terminal_shot = 'forehand'
        # Classificazione Rovescio (b, s, z, y, m, i, k)
        elif last_shot[0] in ['b', 's', 'z', 'y', 'm', 'i', 'k']:
            terminal_shot = 'backhand'
            
        if '*' in last_shot:
            outcome = 'winner'
            
    return terminal_shot, outcome, is_ace

def calculate_metrics_with_debug(player_name, player_id, df):
    debug_logs = []

    if df.empty:
        return [0] * 7, ["Dataset vuoto."]

    serve_mask = df['Svr'] == player_id
    return_mask = df['Svr'] != player_id
    
    # --- 1 & 2. SERVE EFFICIENCY & QUALITY ---
    serves_df = df[serve_mask].copy()
    total_serves = len(serves_df)
    
    if total_serves > 0:
        # La prima è "in" se non inizia con un numero (direzione) seguito da codice errore (n,w,d,x,e,g)
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
        
        # Doppio fallo: anche la seconda palla è un errore
        second_fault_mask = serves_df['2nd'].astype(str).str.match(r'^[4560][nwdexg]')
        double_faults = (second_in_mask & second_fault_mask).sum()
        
        ace_rate = aces / total_serves
        df_rate = double_faults / total_serves
        
        serve_qual = (0.4 * first_in_pct) + (0.3 * ace_rate) + (0.3 * (1 - df_rate))
        
        debug_logs.append(f"Serve Efficiency: {serve_eff:.3f}")
        debug_logs.append(f"  ↳ Formula: ({first_in_pct:.2f} * {first_won_pct:.2f}) + ({(1 - first_in_pct):.2f} * {second_won_pct:.2f})")
        debug_logs.append(f"Serve Quality: {serve_qual:.3f}")
        debug_logs.append(f"  ↳ Dati base: Aces: {aces}, Doppi Falli: {double_faults}")
    else:
        serve_eff, serve_qual = 0, 0

    # --- 3. BASELINE DOMINANCE ---
    # Proxy: Punti vinti in scambi con più di 4 colpi
    rally_lengths = df.apply(lambda row: len(re.findall(r'[fbrsvzuylmhiqt]', str(row['1st']))) + len(re.findall(r'[fbrsvzuylmhiqt]', str(row['2nd']))), axis=1)
    baseline_pts = df[rally_lengths > 4]
    baseline_dom = 0
    if len(baseline_pts) > 0:
        baseline_dom = len(baseline_pts[baseline_pts['PtWinner'] == player_id]) / len(baseline_pts)
        debug_logs.append(f"Baseline Dominance: {baseline_dom:.3f} (Punti vinti in scambi > 4 colpi)")

    # --- 4. BREAK POINT CONVERSION ---
    bp_mask = df.apply(lambda row: is_break_point(row['Pts'], row['Svr'], player_id), axis=1)
    bp_chances = df[bp_mask]
    bp_conversion = 0
    if len(bp_chances) > 0:
        bp_won = len(bp_chances[bp_chances['PtWinner'] == player_id])
        bp_conversion = bp_won / len(bp_chances)
        debug_logs.append(f"Break Point Conversion: {bp_conversion:.3f}")
        debug_logs.append(f"  ↳ Formula: {bp_won} vinti / {len(bp_chances)} giocati")

    # --- 5. RETURN EFFICIENCY ---
    return_pts = df[return_mask]
    return_eff = 0
    if len(return_pts) > 0:
        ret_won = len(return_pts[return_pts['PtWinner'] == player_id])
        return_eff = ret_won / len(return_pts)
        debug_logs.append(f"Return Efficiency: {return_eff:.3f} ({ret_won}/{len(return_pts)})")

    # --- 6. BACKHAND SOLIDITY & 7. FOREHAND DOMINANCE ---
    bh_total = 0
    bh_won = 0
    fh_winners = 0
    total_winners = 0
    
    for idx, row in df.iterrows():
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
    debug_logs.append(f"Backhand Solidity: {bh_solidity:.3f} ({bh_won} vinti col rovescio finale / {bh_total} rovesci finali)")

    fh_dominance = fh_winners / total_winners if total_winners > 0 else 0
    debug_logs.append(f"Forehand Dominance: {fh_dominance:.3f} ({fh_winners} winner dritto / {total_winners} winner totali)")

    raw_metrics = [serve_eff, serve_qual, baseline_dom, bp_conversion, return_eff, bh_solidity, fh_dominance]
    scaled_metrics = [m * 10 for m in raw_metrics]
    
    return scaled_metrics, debug_logs


# Esecuzione
val_sinner, logs_sinner = calculate_metrics_with_debug(PLAYER_1, PLAYER_1_ID, df)
val_alcaraz, logs_alcaraz = calculate_metrics_with_debug(PLAYER_2, PLAYER_2_ID, df)

categories = [
    'Serve Efficiency', 'Serve Quality', 'Baseline Dominance', 
    'Break Point Conversion', 'Return Efficiency', 
    'Backhand Solidity', 'Forehand Dominance'
]

# ==========================================
# STAMPA REPORT (Per Martina)
# ==========================================
print("\n" + "="*70)
print("🔍 REPORT ANALITICO RADAR CHART")
print("="*70)

print(f"\n🎾 {PLAYER_1.upper()} - DETTAGLIO CALCOLI:")
for log in logs_sinner: print(log)
print("\n  >> Valori Finali Scalati (0-10):")
for cat, val in zip(categories, val_sinner): print(f"     - {cat}: {val:.2f}/10")

print("-" * 70)

print(f"\n🎾 {PLAYER_2.upper()} - DETTAGLIO CALCOLI:")
for log in logs_alcaraz: print(log)
print("\n  >> Valori Finali Scalati (0-10):")
for cat, val in zip(categories, val_alcaraz): print(f"     - {cat}: {val:.2f}/10")


# ==========================================
# 3. PLOT RADAR CHART
# ==========================================
N = len(categories)

val_sinner += val_sinner[:1]
val_alcaraz += val_alcaraz[:1]
angles = [n / float(N) * 2 * pi for n in range(N)]
angles += angles[:1]

fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True), facecolor='#111111')
ax.set_facecolor('#222222')
ax.set_theta_offset(pi / 2)
ax.set_theta_direction(-1)

ax.plot(angles, val_sinner, linewidth=2.5, linestyle='solid', label=PLAYER_1, color='#FF8C00')
ax.fill(angles, val_sinner, '#FF8C00', alpha=0.3)
ax.plot(angles, val_alcaraz, linewidth=2.5, linestyle='solid', label=PLAYER_2, color='#00CED1')
ax.fill(angles, val_alcaraz, '#00CED1', alpha=0.3)

plt.xticks(angles[:-1], categories, color='white', size=11, fontweight='bold')
ax.set_rlabel_position(0)
plt.yticks([2, 4, 6, 8, 10], ["2", "4", "6", "8", "10"], color="gray", size=9)
plt.ylim(0, 10)

ax.grid(color='#444444', linestyle='--', linewidth=0.5)
ax.spines['polar'].set_color('#444444')

ax.set_title("Advanced Playstyle Analysis: Sinner vs Alcaraz", color='white', size=18, y=1.15)
legend = plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), facecolor='#111111', edgecolor='white', fontsize=12)
for text in legend.get_texts():
    text.set_color('white')

plt.tight_layout()
output_dir = Path(__file__).resolve().parent / 'pngs'
output_dir.mkdir(exist_ok=True) 
output_path = output_dir / "radarchart.png"

plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"\n✅ Radar chart salvato in: {output_path}")
plt.close()