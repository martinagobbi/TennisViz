import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from .globals import OUTPUT_DIR, PLAYERS
from scipy.stats import gaussian_kde

def load_data(path: str | None = None, raw: list | None = None) -> pd.DataFrame:
    """
    Load data produced by the parser.

    You can pass:
        path  -> path to a .json file (array of points)
        raw   -> Python list already in memory

    The function flattens derived / flags / meta into individual columns.
    """
    if raw is None and path is None:
        raise ValueError("Passa 'path' o 'raw'.")
    data = raw if raw is not None else json.loads(Path(path).read_text())

    rows = []
    for i, p in enumerate(data):
        d = p.get("derived", {})
        f = p.get("flags",   {})
        m = p.get("meta",    {})
        rows.append({
            "idx":                    i,
            "server":                 m.get("server"),
            "point_winner":           m.get("point_winner"),
            "set":                    m.get("set"),
            "is_break_point":         m.get("is_break_point", False),
            "warnings":               m.get("warnings", []),
            # serve
            "serve_direction":        d.get("serve_direction"),
            "serve_outcome":          d.get("serve_outcome"),
            "serve_number_played":    d.get("serve_number_played"),
            # rally
            "rally_length":           d.get("rally_length", 0),
            "terminal_actor":         d.get("terminal_actor"),
            "terminal_shot_type":     d.get("terminal_shot_type"),
            "terminal_outcome":       d.get("terminal_outcome"),
            "return_depth":           d.get("return_depth"),
            "return_direction":       d.get("return_direction"),
            # tactical flags
            "server_at_net":          d.get("server_finished_at_net", False),
            "returner_at_net":        d.get("returner_finished_at_net", False),
            "contains_drop_shot":     d.get("contains_drop_shot", False),
            "contains_lob":           d.get("contains_lob", False),
            "contains_volley":        d.get("contains_volley", False),
            "contains_approach":      d.get("contains_approach", False),
            # flags
            "double_fault":           f.get("double_fault", False),
            "first_serve_fault":      f.get("first_serve_fault", False),
            "has_second_serve":       f.get("has_second_serve", False),
        })
    df = pd.DataFrame(rows)
    df["server_name"]  = df["server"].map(PLAYERS)
    df["winner_name"]  = df["point_winner"].map(PLAYERS)
    df["rally_cat"]    = pd.cut(df["rally_length"],
                                bins=[0, 4, 8, 999],
                                labels=["Short (1–4)", "Medium (5–8)", "Long (9+)"])
    return df


def save(fig, name: str):
    path = OUTPUT_DIR / f"{name}.png"
    fig.savefig(path)
    print(f"  ✓  {path}")
    plt.close(fig)


def legend_patches(pairs):
    return [mpatches.Patch(color=c, label=l) for c, l in pairs]

def kde(data: pd.Series, points: int = 200, bw_method: float = 0.4):
    """Return (x, y) coordinates for the KDE plot."""
    kde_func = gaussian_kde(data, bw_method=bw_method)
    x = np.linspace(data.min(), data.max(), points)
    return x, kde_func(x)