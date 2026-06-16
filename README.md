# 🎾 TennisViz

TennisViz is a tennis data visualization project focused on the
**Jannik Sinner vs Carlos Alcaraz** Roland Garros 2025 final.

It includes:

- a Streamlit dashboard in `src/app.py`
- data parsing and preparation utilities in `src/data/`
- exploratory analysis in `src/EDA/`
- chart modules in `src/charts/`

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
├── outputs/
├── src/
│   ├── EDA/
│   │   ├── eda_analysis.py
│   │   ├── globals.py
│   │   └── helper.py
│   ├── charts/
│   │   ├── court_chart.py
│   │   ├── mirror_line.py
│   │   └── radar.py
│   └── data/
│       ├── filter.py
│       ├── loader.py
│       └── parser.py
├── main.py
├── src/app.py
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

### Streamlit dashboard

The main dashboard now starts from `src/app.py`:

```bash
streamlit run src/app.py
```

### One-off analysis script

`main.py` loads the processed parquet, parses each point, saves the parsed JSON, and runs the EDA pipeline:

```bash
python main.py
```

### Data preparation

`src/data/filter.py` filters the raw Tennis Abstract CSV and creates the processed parquet used by the app:

```bash
python src/data/filter.py
```

Expected input:

- `data/raw/charting-m-points-2020s.csv`

Expected output:

- `data/processed/sinner_alcaraz_2025.parquet`

---

## 🧠 Data pipeline

- `src/data/filter.py` extracts the Sinner–Alcaraz match from the raw CSV.
- `src/data/parser.py` decodes Tennis Abstract point strings into structured features.
- `src/data/loader.py` loads the processed parquet and prepares a chart-friendly dataframe.
- `src/EDA/eda_analysis.py` generates exploratory plots and summary tables.

---

## 📊 Visualization modules

- `src/app.py`: unified Streamlit dashboard.
- `src/charts/court_chart.py`: interactive Plotly court chart.
- `src/charts/radar.py`: radar-style comparison chart.
- `src/charts/mirror_line.py`: momentum / win-probability style chart.

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