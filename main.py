"""Batch analysis entrypoint for TennisViz.

This script is separate from `src/app.py`:
- `src/app.py` is the Streamlit dashboard.
- `main.py` runs the offline parsing + EDA pipeline.
"""

from pathlib import Path
import json

import pandas as pd

from src.EDA.eda_analysis import run_all
from src.data.parser import parse_point_row


def main() -> None:
    project_root = Path(__file__).resolve().parent
    data_path = project_root / "data" / "processed" / "sinner_alcaraz_2025.parquet"
    output_path = project_root / "match_parsed.json"

    # Load the processed parquet for the match already extracted from the raw dataset.
    df = pd.read_parquet(data_path)

    # Parse each row into the structured point representation used by the EDA layer.
    points = [parse_point_row(row.to_dict()) for _, row in df.iterrows()]

    # Save the parsed match to JSON for inspection or debugging.
    with output_path.open("w", encoding="utf-8") as file_handle:
        json.dump(points, file_handle, ensure_ascii=False, indent=2)

    print(f"Parsed {len(points)} points.")

    # Run the exploratory analysis pipeline.
    run_all(raw=points)


if __name__ == "__main__":
    main()