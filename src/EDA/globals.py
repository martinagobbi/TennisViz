from pathlib import Path
import matplotlib.pyplot as plt

OUTPUT_DIR = Path("figures")
OUTPUT_DIR.mkdir(exist_ok=True)

SINNER_ID   = "1"
ALCARAZ_ID  = "2"
C_SINNER    = "#185FA5"
C_ALCARAZ   = "#993C1D"
C_LIGHT_S   = "#B5D4F4"
C_LIGHT_A   = "#F5C4B3"
PLAYERS     = {"1": "Sinner", "2": "Alcaraz"}

# Stile globale Matplotlib
plt.rcParams.update({
    "font.family":       "sans-serif",
    "font.size":         11,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.grid":         True,
    "grid.color":        "#e8e8e8",
    "grid.linewidth":    0.6,
    "figure.dpi":        150,
    "savefig.bbox":      "tight",
    "savefig.facecolor": "white",
})