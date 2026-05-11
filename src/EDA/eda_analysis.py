"""
Input Structure
---------------
List of dicts with fields:
  derived  → serve_direction, serve_outcome, rally_length, terminal_outcome,
              return_depth, return_direction, server_finished_at_net, ...
  flags    → double_fault, first_serve_fault, has_second_serve
  meta     → server ("1"=Sinner, "2"=Alcaraz), point_winner, is_break_point,
              is_tiebreak, set, warnings
"""

import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from .globals import OUTPUT_DIR, PLAYERS, C_SINNER, C_ALCARAZ, C_LIGHT_S, C_LIGHT_A, SINNER_ID, ALCARAZ_ID
from .helper import load_data, save, kde

warnings.filterwarnings("ignore")

# ─── SECTION 1 – MATCH OVERVIEW ───────────────────────────────────────────────

def plot_1_summary_table(df: pd.DataFrame):
    """Summary table of points, aces, double faults, data quality."""
    tot = len(df)
    rows = []
    for pid, pname in PLAYERS.items():
        pts = df[df["server"] == pid]
        w   = df[df["point_winner"] == pid]
        ace = (pts["serve_outcome"] == "ace").sum()
        df_ = pts["double_fault"].sum()
        f1in = (~pts["first_serve_fault"]).sum()
        f1w  = ((~pts["first_serve_fault"]) & (pts["point_winner"] == pid)).sum()
        f2   = pts[pts["has_second_serve"] & ~pts["double_fault"]]
        f2w  = (f2["point_winner"] == pid).sum()
        rows.append({
            "Player":          pname,
            "Points Won":      len(w),
            "% Points Won":    f"{len(w)/tot*100:.1f}%",
            "Aces":            ace,
            "Double Faults":   int(df_),
            "% 1st In":        f"{f1in/len(pts)*100:.1f}%" if len(pts) else "—",
            "% Points on 1st": f"{f1w/f1in*100:.1f}%"     if f1in  else "—",
            "% Points on 2nd": f"{f2w/len(f2)*100:.1f}%"  if len(f2) else "—",
        })
    tdf = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(10, 1.8))
    ax.axis("off")
    tbl = ax.table(
        cellText  = tdf.values,
        colLabels = tdf.columns,
        cellLoc   = "center",
        loc       = "center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1, 1.8)
    tbl.auto_set_column_width(col=list(range(len(tdf.columns)))) 
    # header style
    for j in range(len(tdf.columns)):
        tbl[0, j].set_facecolor("#2c2c2a")
        tbl[0, j].set_text_props(color="white", fontweight="bold")
    # row colors
    colors = [C_LIGHT_S, C_LIGHT_A]
    for i, c in enumerate(colors):
        for j in range(len(tdf.columns)):
            tbl[i+1, j].set_facecolor(c)
    ax.set_title("1.1 — Match Summary", fontweight="bold", pad=12, loc="left")
    save(fig, "1_match_summary")

# ─── SECTION 2 – SERVE AND RETURN ─────────────────────────────────────────────

def plot_2_serve_efficiency(df: pd.DataFrame):
    """
    Grouped bar: % 1st In, % Points on 1st, % Points on 2nd.
    Annotations: Aces and Double Faults in text.
    """
    metrics, vals_s, vals_a = [], [], []
    for pid, pname in PLAYERS.items():
        pts  = df[df["server"] == pid]
        f1in = (~pts["first_serve_fault"]).sum()
        f1w  = ((~pts["first_serve_fault"]) & (pts["point_winner"] == pid)).sum()
        f2   = pts[pts["has_second_serve"] & ~pts["double_fault"]]
        f2w  = (f2["point_winner"] == pid).sum()
        v = [
            f1in / len(pts) * 100 if len(pts) else 0,
            f1w  / f1in     * 100 if f1in     else 0,
            f2w  / len(f2)  * 100 if len(f2)  else 0,
        ]
        if pid == SINNER_ID: vals_s = v
        else:                vals_a = v

    labels = ["% 1st Serve In", "% Points on 1st", "% Points on 2nd"]
    x  = np.arange(len(labels))
    w  = 0.35
    fig, ax = plt.subplots(figsize=(8, 4.5))
    b1 = ax.bar(x - w/2, vals_s, w, label="Sinner",  color=C_SINNER,  alpha=0.85)
    b2 = ax.bar(x + w/2, vals_a, w, label="Alcaraz", color=C_ALCARAZ, alpha=0.85)
    ax.bar_label(b1, fmt="%.1f%%", padding=4, fontsize=9)
    ax.bar_label(b2, fmt="%.1f%%", padding=4, fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylim(0, 100)
    ax.set_ylabel("%")
    ax.legend(frameon=False)
    # annotations for aces / double faults
    for i, (pid, col) in enumerate([(SINNER_ID, C_SINNER), (ALCARAZ_ID, C_ALCARAZ)]):
        pts = df[df["server"]==pid]
        ace = (pts["serve_outcome"]=="ace").sum()
        dfa = pts["double_fault"].sum()
        ax.text(0.98, 0.97 - i * 0.07, f"{PLAYERS[pid]}: {ace} aces / {int(dfa)} DF",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=9, color=col)
    ax.set_title("Serve Efficiency", fontweight="bold", loc="left")
    save(fig, "2_serve_efficiency")


def plot_3_serve_direction(df: pd.DataFrame):
    """
    Stacked bar: frequenza direzioni 4=Wide, 5=Body, 6=T
    separata per 1° e 2° servizio e per giocatore.
    """
    dir_map   = {"out_wide": "Wide (4)", "body": "Body (5)", "down_the_T": "T (6)"}
    dir_order = ["Wide (4)", "Body (5)", "T (6)"]
    colors_sinner  = {"Wide (4)": "#44A1A0", "Body (5)": "#78CDD7", "T (6)": "#247B7B"}
    colors_alcaraz = {"Wide (4)": "#FF8C42", "Body (5)": "#FFB385", "T (6)": "#E25822"}
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=False)
    for ax, (pid, pname) in zip(axes, PLAYERS.items()):
        pts  = df[df["server"] == pid].copy()
        pts["dir_label"] = pts["serve_direction"].map(dir_map).fillna("Unknown")
        rows = []
        for sn, snlbl in [(1,"1st serve"),(2,"2nd serve")]:
            sub = pts[pts["serve_number_played"]==sn]
            cnts = sub["dir_label"].value_counts()
            tot  = len(sub) or 1
            for d in dir_order:
                rows.append({"Serve":snlbl,"Direction":d,"%":cnts.get(d,0)/tot*100})
        rdf = pd.DataFrame(rows)
        sn_labels = ["1st serve","2nd serve"]
        bottoms   = np.zeros(2)
        for d in dir_order:
            vals = [rdf[(rdf["Serve"]==s)&(rdf["Direction"]==d)]["%"].values[0]
                    for s in sn_labels]
            bars = ax.bar(sn_labels, vals, bottom=bottoms, color=colors_sinner[d] if pid == SINNER_ID else colors_alcaraz[d], label=d, alpha=0.88)
            for rect, val, bot in zip(bars, vals, bottoms):
                if val > 5:
                    ax.text(rect.get_x()+rect.get_width()/2, bot+val/2,
                            f"{val:.0f}%", ha="center", va="center", fontsize=9, color="black")
            bottoms += np.array(vals)
        ax.set_title(pname, fontweight="bold")
        ax.set_ylim(0,100); ax.set_ylabel("% points" if pid==SINNER_ID else "")
        ax.legend(frameon=False, fontsize=9, loc="upper left",
          bbox_to_anchor=(1.01, 1), borderaxespad=0)
    fig.suptitle("Serve Direction (1st vs 2nd)", fontweight="bold", x=0.02, ha="left")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    save(fig, "3_serve_direction")


def plot_4_return(df: pd.DataFrame):
    """
    Due sub-plot:
    (a) Frequenza profondità risposta (short/mid/deep) – bar chart
    (b) % punti vinti in risposta su 1° vs 2° – grouped bar
    """
    depth_map   = {"short":"Short (7)", "mid":"Medium (8)", "deep":"Deep (9)"}
    depth_order = ["Short (7)", "Medium (8)", "Deep (9)"]
    #depth_colors= {"Corta (7)":"#BA7517","Media (8)":"#378ADD","Profonda (9)":"#0F6E56"}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))

    # (a) profondità risposta
    for pid, pname, col in [(SINNER_ID,"Sinner",C_SINNER),(ALCARAZ_ID,"Alcaraz",C_ALCARAZ)]:
        # come returner: server è l'avversario
        ret = df[df["server"] != pid].copy()
        ret["dep_label"] = ret["return_depth"].map(depth_map).fillna("Unknown")
        cnts = ret["dep_label"].value_counts()
        tot  = len(ret) or 1
        for d in depth_order:
            pval = cnts.get(d,0)/tot*100
        # subplot a barre raggruppate per profondità
    x = np.arange(len(depth_order)); w = 0.35
    for offset, (pid, pname, col) in enumerate([
        (SINNER_ID,"Sinner",C_SINNER),
        (ALCARAZ_ID,"Alcaraz",C_ALCARAZ)
    ]):
        ret = df[df["server"] != pid].copy()
        ret["dep_label"] = ret["return_depth"].map(depth_map).fillna("Unknown")
        cnts = ret["dep_label"].value_counts()
        tot  = len(ret) or 1
        vals = [cnts.get(d, 0) / tot * 100 for d in depth_order]
        bars = ax1.bar(x + offset * w, vals, w, label=pname, color=col, alpha=0.85)
        ax1.bar_label(bars, fmt="%.1f%%", padding=3, fontsize=8)
    ax1.set_xticks(x + w / 2)
    ax1.set_xticklabels(depth_order)
    ax1.set_ylabel("%")
    ax1.set_ylim(0, 60)
    ax1.legend(frameon=False)
    ax1.set_title("(a) Return Depth", fontweight="bold")

    # (b) % punti vinti in risposta (su 1° vs 2° avversario)
    cat_labels = ["Return to 1st", "Return to 2nd"]
    x2 = np.arange(len(cat_labels)); w2 = 0.35
    for offset, (pid, pname, col) in enumerate([(SINNER_ID,"Sinner",C_SINNER),(ALCARAZ_ID,"Alcaraz",C_ALCARAZ)]):
        opp = ALCARAZ_ID if pid==SINNER_ID else SINNER_ID
        r1  = df[(df["server"]==opp) & (~df["first_serve_fault"])]
        r2  = df[(df["server"]==opp) & df["has_second_serve"] & ~df["double_fault"]]
        v1  = (r1["point_winner"]==pid).sum()/len(r1)*100 if len(r1) else 0
        v2  = (r2["point_winner"]==pid).sum()/len(r2)*100 if len(r2) else 0
        bars = ax2.bar(x2+offset*w2, [v1,v2], w2, label=pname, color=col, alpha=0.85)
        ax2.bar_label(bars, fmt="%.1f%%", padding=3, fontsize=8)
    ax2.set_xticks(x2+w2/2); ax2.set_xticklabels(cat_labels)
    ax2.set_ylim(0,70); ax2.set_ylabel("%")
    ax2.legend(frameon=False)
    ax2.set_title("(b) % points won on return", fontweight="bold")

    fig.suptitle("2.3 — The Return", fontweight="bold", x=0.02, ha="left")
    save(fig, "4_return")

# ─── SEZIONE 3 – IL PALLEGGIO ─────────────────────────────────────────────────

def plot_5_rally_length(df: pd.DataFrame):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # (a) distribuzione KDE
    data_s = df[df["server"] == SINNER_ID]["rally_length"].dropna()
    data_a = df[df["server"] == ALCARAZ_ID]["rally_length"].dropna()

    ax1.fill_between(
        *kde(data_s), alpha=0.25, color=C_SINNER
    )
    ax1.plot(
        *kde(data_s), color=C_SINNER, linewidth=2, label="Sinner Serving"
    )
    ax1.fill_between(
        *kde(data_a), alpha=0.25, color=C_ALCARAZ
    )
    ax1.plot(
        *kde(data_a), color=C_ALCARAZ, linewidth=2, label="Alcaraz Serving"
    )

    ax1.set_xlabel("Shots in Rally")
    ax1.set_ylabel("Density")
    ax1.legend(frameon=False)
    ax1.set_title("(a) Rally Length Distribution by Server", fontweight="bold")

    # (b) istogramma raggruppato + % punti vinti per categoria
    cats = ["Short (1–4)", "Medium (5–8)", "Long (9+)"]
    x = np.arange(len(cats)); w = 0.35
    for offset, (pid, pname, col, lcol) in enumerate([
        (SINNER_ID,"Sinner",C_SINNER,C_LIGHT_S),
        (ALCARAZ_ID,"Alcaraz",C_ALCARAZ,C_LIGHT_A)
    ]):
        sub  = df[df["server"]==pid]
        wins = df[df["point_winner"]==pid]
        vals, win_pcts = [], []
        for cat in cats:
            n  = (sub["rally_cat"]==cat).sum()
            nw = ((wins["rally_cat"]==cat)).sum()
            nt = (df["rally_cat"]==cat).sum()
            vals.append(n)
            win_pcts.append(nw/nt*100 if nt else 0)
        bars = ax2.bar(x+offset*w, win_pcts, w, label=pname, color=col, alpha=0.85)
        ax2.bar_label(bars, fmt="%.1f%%", padding=3, fontsize=8)
    ax2.set_xticks(x+w/2); ax2.set_xticklabels(cats)
    ax2.set_ylabel("% points won"); ax2.set_ylim(0,70)
    ax2.legend(frameon=False)
    ax2.set_title("(b) % points won per rally category", fontweight="bold")

    fig.suptitle("3.1 — Rally Length", fontweight="bold", x=0.02, ha="left")
    save(fig, "5_rally_length")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def run_all(path: str | None = None, raw: list | None = None):
    """
    Executes the entire EDA and saves all plots in ./figures/.
    Called from main.py with run_all(raw=point_list).
    """
    print("Loading data…")
    df = load_data(path=path, raw=raw)
    print(f"  {len(df)} points loaded | columns: {list(df.columns)}\n")

    print("Section 1 – Match Overview")
    plot_1_summary_table(df)

    print("\nSection 2 – Serve and Return")
    plot_2_serve_efficiency(df)
    plot_3_serve_direction(df)
    plot_4_return(df)

    print("\nSection 3 – The Rally")
    plot_5_rally_length(df)

    print(f"\nDone! Plots saved in '{OUTPUT_DIR.resolve()}'")