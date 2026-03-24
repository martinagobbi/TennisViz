# 🎾 TennisViz

Data visualization project for the **Sinner vs Alcaraz** match at Roland Garros 2025 (Final, 08/06/2025).

Raw data sourced from the [Tennis Abstract Match Charting Project](https://github.com/JeffSackmann/tennis_MatchChartingProject) by Jeff Sackmann.
---

## 📁 Project Structure

```
TennisViz/
├── data/
│   ├── raw/                  # Original CSV from Sackmann's repo
│   └── processed/            # Filtered .parquet file
├── src/
│   ├── data/
|        ├── filter.py        # Extracts the specific match from the dataset
|        ├── parser.py        # Parses MBP rally strings into structured features                  
├── outputs/                  # Charts and exported figures
├── requirements.txt
└── Dockerfile                # (coming soon)
```

---

## ⚙️ Setup

### 1. Create and activate the virtual environment

**Windows (PowerShell):**
```bash
python -m venv .venv
.venv\Scripts\Activate
```

**Linux / macOS:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🔧 Scripts

### `filter.py`

Reads the raw CSV file from Sackmann's dataset (`charting-m-points-2020s.csv`) in chunks to avoid memory issues, filters only the rows corresponding to the Sinner–Alcaraz Roland Garros 2025 final (`match_id = "20250608-M-Roland_Garros-F-Jannik_Sinner-Carlos_Alcaraz"`), and saves the result as a `.parquet` file. We chose this type of columnar binary format because it is significantly faster to read and more memory-efficient than CSV, making it ideal for repeated loading during analysis and visualization.
Expected output: **385 rows**.

```bash
python src/filter.py
```

Input:  `data/raw/charting-m-points-2020s.csv`  
Output: `data/processed/sinner_alcaraz_2025.parquet`

---

### `parser.py` (in progress)

Parses the **MBP (Match Point by Point)** rally strings from Sackmann's format into structured, human-readable features.

Each rally string encodes a full point as a compact sequence of characters — serve speed, direction, shot types, depths, faults, and outcomes. `parser.py` decodes this into a flat dictionary with fields such as:

| Field | Description |
|---|---|
| `serve_speed` | Speed code of the serve (`4`, `5`, `6`) |
| `serve_direction` | Direction of serve (out wide / body / down the T) |
| `serve_return_depth` | Depth of the return (short / mid / deep) |
| `rally_length` | Number of shots in the rally |
| `fault_type` | Type of fault if any (net / wide / deep / ...) |
| `serve_outcome` | Ace, forced error, or unforced error |
| `is_ace` | Whether the point ended with an ace |
| `is_serve_fault` | Whether the first serve was a fault |
| `is_winner` | Whether the point ended with a clean winner |
| `last_shot_type` | Type of the last shot in the rally |
| `last_shot_direction` | Direction of the last shot |

The main entry point is `parse_rally_string(s: str) -> dict`, which takes a single MBP string and returns the decoded feature dictionary.

---

## 🐳 Docker

> Containerization with Docker is planned. A `Dockerfile` will be added to the repo.

---

## 📄 License

Data: [tennis_MatchChartingProject](https://github.com/JeffSackmann/tennis_MatchChartingProject) — see original repo for license terms.  
Code: see `LICENSE`.