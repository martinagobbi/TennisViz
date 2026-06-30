from pathlib import Path
from typing import Any

import pandas as pd

from .parser import parse_point_row

#  LOADER: reads the parquet file and builds the dataframe

def get_court_side(score_str: str) -> str:
    """Infer the server side ('Deuce' or 'Ad') from the current game score.

    If the score cannot be parsed,
    it falls back to 'Deuce' so downstream charting code can keep running.
    """
    if pd.isna(score_str):
        return 'Deuce' 
    clean_score = str(score_str).strip().upper().split(' ')[0]
    score_map = {'0': 0, '15': 1, '30': 2, '40': 3, 'AD': 4}
    try:
        parts = clean_score.split('-')
        if len(parts) == 2:
            p1_str, p2_str = parts
            p1 = score_map[p1_str] if p1_str in score_map else int(p1_str)
            p2 = score_map[p2_str] if p2_str in score_map else int(p2_str)
            return 'Deuce' if (p1 + p2) % 2 == 0 else 'Ad'
    except Exception:
        pass 
    return 'Deuce'


def _resolve_rally_columns(df: pd.DataFrame) -> tuple[str, str]:
    """Return the names of the columns that contain the first and second rally strings."""
    if {"1st", "2nd"}.issubset(df.columns):
        return "1st", "2nd"
    if {"rally_1st", "rally_2nd"}.issubset(df.columns):
        return "rally_1st", "rally_2nd"
    raise ValueError("Input file must contain either `1st`/`2nd` or `rally_1st`/`rally_2nd` columns.")


def _safe_player_id(value: Any) -> int | None:
    """Convert a player identifier to int when possible; otherwise return None."""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None

def load_and_clean(path: str | Path) -> pd.DataFrame:
    """
    Load the processed parquet file and return a chart-ready dataframe.

    The loader parses each point with `parse_point_row`, then flattens the
    nested parser output (`derived`, `flags`, `meta`) into one row per point.
 
    Expected input columns (Sackmann names, already cleaned by `filter.py`):
        Pt, set1, set2, Gm1, Gm2, Pts, Gm#, Svr, 1st, 2nd, PtWinner
    """
    raw_df = pd.read_parquet(Path(path))
    first_col, second_col = _resolve_rally_columns(raw_df)

    parsed_records = raw_df.apply(
        lambda row: parse_point_row(row.to_dict(), first_col=first_col, second_col=second_col),
        axis=1,
    ).tolist()

    rows: list[dict[str, Any]] = []

    for raw_row, parsed in zip(raw_df.to_dict("records"), parsed_records):
        derived = parsed.get("derived") or {}
        flags = parsed.get("flags") or {}
        active_point = parsed.get("active_point") or {}
        rally = active_point.get("rally") or []

        # Normalize player identifiers so charts can work with numeric IDs
        server_id = _safe_player_id(raw_row.get("Svr", raw_row.get("server")))
        winner_id = _safe_player_id(raw_row.get("PtWinner", raw_row.get("point_winner")))
        score_in_game = raw_row.get("Pts", raw_row.get("score_in_game"))

        last_shot_type = derived.get("terminal_shot_type")
        last_shot_direction = None
        if rally:
            last_shot_direction = rally[-1].get("direction")

        # Build the flattened record expected by the dashboard and EDA modules
        rows.append(
            {
                "point_num": raw_row.get("Pt", raw_row.get("point_num")),
                "set_number": parsed.get("meta", {}).get("set"),
                "gm1": raw_row.get("Gm1", raw_row.get("gm1")),
                "gm2": raw_row.get("Gm2", raw_row.get("gm2")),
                "game_num": raw_row.get("Gm#", raw_row.get("game_num")),
                "score_in_game": score_in_game,
                "server": server_id,
                "point_winner": winner_id,
                "server_name": {1: "Sinner", 2: "Alcaraz"}.get(server_id, "Unknown"),
                "point_winner_name": {1: "Sinner", 2: "Alcaraz"}.get(winner_id, "Unknown"),
                "serve_number_played": derived.get("serve_number_played"),
                "serve_direction": derived.get("serve_direction"),
                "serve_outcome": derived.get("serve_outcome"),
                "rally_length": derived.get("rally_length"),
                "return_depth": derived.get("return_depth"),
                "return_direction": derived.get("return_direction"),
                "terminal_actor": derived.get("terminal_actor"),
                "terminal_shot_type": derived.get("terminal_shot_type"),
                "terminal_outcome": derived.get("terminal_outcome"),
                "has_second_serve": bool(flags.get("has_second_serve")),
                "first_serve_fault": bool(flags.get("first_serve_fault")),
                "double_fault": bool(flags.get("double_fault")),
                "is_first_serve_in": not bool(flags.get("first_serve_fault")),
                "is_ace": derived.get("serve_outcome") == "ace",
                "is_double_fault": bool(flags.get("double_fault")),
                "is_winner_pt": bool(winner_id is not None and server_id is not None and winner_id == server_id),
                "court_side": get_court_side(score_in_game),
                "last_shot_type": last_shot_type,
                "last_shot_direction": last_shot_direction,
            }
        )

    return pd.DataFrame(rows).reset_index(drop=True)

 
if __name__ == "__main__":
    import sys
 
    path = sys.argv[1] if len(sys.argv) > 1 else "data/processed/sinner_alcaraz_2025.parquet"
    df = load_and_clean(path)
 
    print(f"\nShape: {df.shape}")
    print(f"\nColumns: {df.columns.tolist()}\n")
    print(df[[
        "point_num", "set_number", "server_name", "point_winner_name",
        "is_ace", "is_double_fault", "is_winner_pt",
        "rally_length", "last_shot_type", "last_shot_direction",
    ]].head(10).to_string())
 
    print("\nQuick statistics")
    print(f"  Aces:             {df['is_ace'].sum()}")
    print(f"  Double faults:    {df['is_double_fault'].sum()}")
    print(f"  Total winners:    {df['is_winner_pt'].sum()}")
    print(f"  1st serve in:     {df['is_first_serve_in'].mean():.1%}")
    print(f"  Average rally:    {df['rally_length'].mean():.1f} shots")