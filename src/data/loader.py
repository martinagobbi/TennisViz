import pandas as pd
import numpy as np
from pathlib import Path
from .parser import parse_rally_string 

#  LOADER — legge parquet e costruisce il DataFrame
 
def load_and_clean(path: str | Path) -> pd.DataFrame:
    """
    Carica il .parquet da data/processed/ e restituisce un DataFrame
    pulito con tutte le feature derivate pronte per i grafici.
 
    Colonne attese in input (nomi Sackmann, già puliti da filter.py):
        Pt, set1, set2, Gm1, Gm2, Pts, Gm#, Svr, 1st, 2nd, PtWinner
    """
    df = pd.read_parquet(Path(path))
 
    # ── 1. Rinomina per leggibilità ───────────────────────────────────────────
    df = df.rename(columns={
        "Pt":       "point_num",
        "Gm1":      "gm1",
        "Gm2":      "gm2",
        "Pts":      "score_in_game",
        "Gm#":      "game_num",
        "Svr":      "server",
        "1st":      "rally_1st",
        "2nd":      "rally_2nd",
        "PtWinner": "point_winner",
    })
 
    # Drop colonne che filter.py potrebbe non aver ancora rimosso
    df = df.drop(columns=["match_id", "TbSet", "Notes"], errors="ignore")
 
    # ── 2. Set number logico (1, 2, 3) ───────────────────────────────────────
    df["set_number"] = (
        (df["set1"] + df["set2"])
        .ne((df["set1"] + df["set2"]).shift())
        .cumsum()
        .astype(int)
    )
 
    # ── 3. Parsing MBP ────────────────────────────────────────────────────────
    first_parsed  = df["rally_1st"].apply(parse_rally_string).apply(pd.Series)
    second_parsed = df["rally_2nd"].apply(parse_rally_string).apply(pd.Series)
 
    first_parsed.columns  = [f"first_{c}"  for c in first_parsed.columns]
    second_parsed.columns = [f"second_{c}" for c in second_parsed.columns]
 
    df = pd.concat([df, first_parsed, second_parsed], axis=1)
 
    # ── 4. Feature aggregate per punto ───────────────────────────────────────
    # Il primo servizio è "in" se NON termina con @
    df["is_first_serve_in"] = ~df["rally_1st"].str.endswith("@", na=True)
 
    # Lunghezza rally (usa il servizio che ha effettivamente giocato)
    df["rally_length"] = np.where(
        df["is_first_serve_in"],
        df["first_rally_length"],
        df["second_rally_length"],
    )
 
    # Ace e doppio fallo
    df["is_ace"]          = df["first_is_ace"]
    df["is_double_fault"] = df["second_is_ace"]
 
    # Winner diretto
    df["is_winner_pt"] = (
        df["first_is_winner"] | df["second_is_winner"]
    ) & ~df["is_ace"]
 
    # Ultimo colpo (per Court Graphics e Radar Chart)
    df["last_shot_type"] = np.where(
        df["is_first_serve_in"],
        df["first_last_shot_type"],
        df["second_last_shot_type"],
    )
    df["last_shot_direction"] = np.where(
        df["is_first_serve_in"],
        df["first_last_shot_direction"],
        df["second_last_shot_direction"],
    )
 
    # ── 5. Etichette leggibili ────────────────────────────────────────────────
    df["server_name"]       = df["server"].map({1: "Sinner", 2: "Alcaraz"})
    df["point_winner_name"] = df["point_winner"].map({1: "Sinner", 2: "Alcaraz"})
 
    return df.reset_index(drop=True)
 
 
# ═══════════════════════════════════════════════════════
#  TEST DA TERMINALE
#  python src/data/loader.py data/processed/sinner_alcaraz_2025.parquet
# ═══════════════════════════════════════════════════════
 
if __name__ == "__main__":
    import sys
 
    path = sys.argv[1] if len(sys.argv) > 1 else "data/processed/sinner_alcaraz_2025.parquet"
    df = load_and_clean(path)
 
    print(f"\nShape: {df.shape}")
    print(f"\nColonne: {df.columns.tolist()}\n")
    print(df[[
        "point_num", "set_number", "server_name", "point_winner_name",
        "is_ace", "is_double_fault", "is_winner_pt",
        "rally_length", "last_shot_type", "last_shot_direction",
    ]].head(10).to_string())
 
    print("\n── Statistiche rapide ──")
    print(f"  Ace:              {df['is_ace'].sum()}")
    print(f"  Doppi falli:      {df['is_double_fault'].sum()}")
    print(f"  Winners totali:   {df['is_winner_pt'].sum()}")
    print(f"  1° servizio in:   {df['is_first_serve_in'].mean():.1%}")
    print(f"  Rally medio:      {df['rally_length'].mean():.1f} colpi")
 