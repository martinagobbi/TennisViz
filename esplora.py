'''
Perché il numero di doppi falli è 8 invece che 7 (superiore ai resoconti ufficiali)?
Il punto anomalo è Pt 217:
1st: '6d'   → primo servizio fault (deep)
2nd: 'c4b38b3b1d@' → secondo servizio che inizia con 'c' (let)

Il c iniziale indica un let — la palla ha toccato il nastro ma è entrata, quindi il servizio viene ribattuto e non è un fault.
Il rally 4b38b3b1d@ dopo il c conferma che il punto è stato giocato normalmente e vinto dal ricevitore con un errore non forzato.
Il parser però legge c come FAULT_TYPE["c"] = "let" e lo marca come is_fault = True, trasformando il punto in un doppio fallo.
Il let non deve essere trattato come fault sul secondo servizio se è seguito da un rally. 
'''
import pandas as pd
from src.data.parser import parse_point_row

df = pd.read_parquet("data/processed/sinner_alcaraz_2025.parquet")

doppi_falli = []
for _, row in df.iterrows():
    parsed = parse_point_row(row.to_dict())
    if parsed["flags"]["double_fault"]:
        doppi_falli.append({
            "Pt":  row["Pt"],
            "Svr": row["Svr"],
            "1st": row["1st"],
            "2nd": row["2nd"],
        })

print(f"Doppi falli rilevati dal parser: {len(doppi_falli)}")
for df_ in doppi_falli:
    print(df_)