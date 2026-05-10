import json
import sys
from pathlib import Path
import pandas as pd
from src.data.parser import parse_point_row
from src.EDA.eda_analysis import run_all

sys.path.append(str(Path(__file__).parent))

path = Path("data") / "processed" / "sinner_alcaraz_2025.parquet"

# 1. Carica il parquet (è già una sola partita, nessun filtro necessario)
df = pd.read_parquet(path)

# 2. Converti ogni riga in un punto parsato
punti = []
for _, row in df.iterrows():
    parsed = parse_point_row(row.to_dict())
    punti.append(parsed)

# 3. Salva il JSON per ispezionarlo (opzionale ma utile)
with open("match_parsed.json", "w", encoding="utf-8") as f:
    json.dump(punti, f, ensure_ascii=False, indent=2)

print(f"Parsati {len(punti)} punti.")

# 4. Lancia l'EDA
run_all(raw=punti)