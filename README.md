# 🎾 TennisViz

TennisViz is a tennis data visualization project focused on the
**Jannik Sinner vs Carlos Alcaraz** Roland Garros 2025 final.

It includes:

- a Streamlit dashboard with multiple pages in `src/pages/`
- data parsing and preparation utilities in `src/data/`
- exploratory data analysis (EDA) in `src/EDA/`

Raw data comes from the [Tennis Abstract Match Charting Project](https://github.com/JeffSackmann/tennis_MatchChartingProject) by Jeff Sackmann.

---

## 📁 Project Structure

```text
TennisViz/
├── data/
│   ├── raw/
│   │   └── charting-m-points-2020s.csv
│   └── processed/
│       └── sinner_alcaraz_2025.parquet
├── figures/
├── src/
│   ├── .streamlit/
│   │   └── config.toml
│   ├── data/
│   │   ├── data_management/
│   │   │   ├── filter.py
│   │   │   ├── loader.py
│   │   │   └── parser.py
│   │   └── __init__.py
│   ├── EDA/
│   │   ├── eda_analysis.py
│   │   ├── globals.py
│   │   ├── helper.py
│   │   └── __init__.py
│   ├── pages/
│   │   ├── 1_Overview.py
│   │   ├── 2_Line_Chart.py
│   │   ├── 3_Radar_Chart.py
│   │   └── 4_Court_Chart.py
│   └── app.py
├── main.py
├── match_parsed.json
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## ⚙️ Setup

### 1. Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
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

## 🚀 Run the project

This project has **two separate entry points**: one for the interactive dashboard, one for offline analysis.

### Streamlit dashboard (`src/app.py`)

Launches the interactive multi-page Streamlit app. `src/app.py` defines the sidebar navigation explicitly via `st.navigation`, pointing to each page in `src/pages/`. The home page (`1_Overview.py`) links to the Line Chart, Radar Chart, and Court Chart pages.

```bash
streamlit run src/app.py
```

### Offline analysis (`main.py`)

Used for **EDA and offline parsing**, not the dashboard. It loads the processed parquet, parses each point with the Match Charting Project parser, saves the parsed output to `match_parsed.json`, and runs the full EDA pipeline (saving plots to `figures/`).

```bash
python main.py
```

### Data preparation

`src/data_management/filter.py` filters the raw Tennis Abstract CSV and creates the processed parquet used by both the dashboard and `main.py`:

```bash
python src/data_management/filter.py
```

Expected input:

- `data/raw/charting-m-points-2020s.csv`

Expected output:

- `data/processed/sinner_alcaraz_2025.parquet`

---

## 🧠 Data pipeline

- `src/data_management/filter.py` extracts the Sinner–Alcaraz match from the raw CSV.
- `src/data_management/parser.py` decodes Tennis Abstract point strings into structured features.
- `src/data_management/loader.py` loads the processed parquet and prepares a chart-friendly dataframe.
- `src/EDA/eda_analysis.py` generates exploratory plots and summary tables (used by `main.py`).

---

## 📊 Dashboard pages (`src/pages/`)

The sidebar navigation is built explicitly in `src/app.py` using `st.navigation`, which maps each page in this folder to a title and icon, in the order they should appear.

- `1_Overview.py`: landing page with match context and links to the other pages.
- `2_Line_Chart.py`: momentum / win-probability style chart.
- `3_Radar_Chart.py`: radar-style tactical comparison chart.
- `4_Court_Chart.py`: interactive Plotly court chart with serve placement.

---

## 🐳 Docker

Build the image from the repository root:

```bash
docker build -t tennisviz .
```

Run the Streamlit app in the container:

```bash
docker run --rm -p 8501:8501 tennisviz
```

Then open `http://localhost:8501` in your browser.

---

## 📄 License

Data: [tennis_MatchChartingProject](https://github.com/JeffSackmann/tennis_MatchChartingProject) — see the original repository for license terms.

Code: see `LICENSE`.