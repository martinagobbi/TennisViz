import pandas as pd

MATCH_ID = "20250608-M-Roland_Garros-F-Jannik_Sinner-Carlos_Alcaraz"

def filter_match(raw_path: str, out_path: str) -> None:
    # Read the CSV file in chunks and filter for the specific match_id (to avoid memory issues)
    chunks = []
    for chunk in pd.read_csv(raw_path, chunksize=10_000, low_memory=False):
        filtered = chunk[chunk["match_id"] == MATCH_ID]
        if not filtered.empty:
            chunks.append(filtered)
    
    df = pd.concat(chunks, ignore_index=True)
    print(f"Rows extracted: {len(df)}")  # they must be 385
    df.to_parquet(out_path, index=False)

if __name__ == "__main__":
    filter_match(
        "data\\raw\\charting-m-points-2020s.csv",
        "data\\processed\\sinner_alcaraz_2025.parquet"
    )