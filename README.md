# 🏏 ICC T20 World Cup 2026 — Outcome Prediction & Analytics Platform

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35-FF4B4B?logo=streamlit)
![XGBoost](https://img.shields.io/badge/XGBoost-2.0-orange)
![Gemini](https://img.shields.io/badge/Gemini-1.5%20Flash-4285F4?logo=google)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![License](https://img.shields.io/badge/License-MIT-green)

**Kenexai Hackathon 2k26 · KD&A-10 · CHARUSAT, Changa**

*An end-to-end Data & AI platform for cricket analytics — from raw ball-by-ball data to AI-powered match predictions and a GenAI chatbot.*

</div>

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Live Demo](#-live-demo)
- [Architecture](#-architecture)
- [Dataset](#-dataset)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [Docker Deployment](#-docker-deployment)
- [Data Pipeline](#-data-pipeline)
- [Machine Learning Models](#-machine-learning-models)
- [GenAI Components](#-genai-components)
- [Dashboards](#-dashboards)
- [API Reference](#-api-reference)
- [Key Results](#-key-results)
- [Team](#-team)

---

## 🔭 Overview

This platform answers one big question: **Who will win the ICC Men's T20 World Cup 2026?**

It does so by building a complete data engineering and AI pipeline — ingesting ball-by-ball cricket data, cleaning and warehousing it, training 5 machine learning models, indexing 452 documents into a vector database, and serving everything through a 7-page interactive Streamlit dashboard with a Gemini-powered RAG chatbot.

**Built for:** Kenexai Hackathon 2k26 @ CHARUSAT (24-hour Round 2)
**Problem statement:** KD&A-10 — ICC Men's T20 Cricket Match World Cup 2026 Outcome Prediction

---

## 🎬 Live Demo

```
Dashboard  →  http://localhost:8501
API Docs   →  http://localhost:8000/docs
```

| Page | Description |
|---|---|
| 📊 Data Quality | Scorecards, null heatmap, EDA charts, live simulator feed |
| 🧑‍💼 Coach | Player form, bowler economy, over-by-over run rate, player cards |
| 📈 Analyst | Win probability simulator, batting depth, bowling variety |
| 🎙️ Commentator | Records, milestones, live stat ticker, sixes/fours analysis |
| 🏆 Strategist | Points table, NRR simulator, qualification probability |
| 🤖 ML Predictions | 5 model tabs — match predictor, score predictor, clusters, rules, upset meter |
| 💬 AI Chatbot | CricAI — Gemini RAG chatbot + match preview generator |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                             │
│   Cricsheet (ball-by-ball)  ·  Live Simulator (Python → PG)    │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│              MEDALLION ARCHITECTURE (PostgreSQL)                │
│  Bronze (raw) → Silver (cleaned) → Gold (star schema)          │
│  1 Fact table · 5 Dimension tables                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
┌──────────▼──────┐  ┌───────▼───────┐  ┌─────▼──────────┐
│   ML MODELS     │  │  GenAI / RAG  │  │  DASHBOARDS    │
│  XGBoost        │  │  ChromaDB     │  │  Streamlit     │
│  LightGBM       │  │  Gemini 2.5   │  │  7 pages       │
│  K-Means        │  │  452 docs     │  │  4 personas    │
│  Apriori        │  │  LangChain    │  │  Plotly charts │
│  LogisticReg    │  └───────────────┘  └────────────────┘
└─────────────────┘
           │
┌──────────▼──────────────────────────────────────────────────────┐
│                    DOCKER DEPLOYMENT                            │
│  PostgreSQL :5432 · FastAPI :8000 · Streamlit :8501            │
│  ChromaDB :8002   ·  docker-compose up --build                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Dataset

**Source:** [Cricsheet](https://cricsheet.org/downloads/t20s_csv2.zip) — ball-by-ball T20 international data

| Table | Rows | Description |
|---|---|---|
| `bronze.raw_deliveries` | 45,656 | Every ball bowled — batsman, bowler, runs, wickets |
| `bronze.raw_matches` | 110 | Match results, toss, venue, player of match |
| `bronze.raw_squads` | 600 | Player-team squads |
| `bronze.raw_batting_stats` | 38 | Career batting averages |
| `bronze.raw_bowling_stats` | 30 | Career bowling averages |
| `bronze.raw_venues` | 16 | Stadium details |
| `public.live_ball_events` | 360+ | Simulated live match stream |

> Each delivery record contains: `match_id`, `date`, `venue`, `batting_team`, `bowling_team`, `batsman`, `bowler`, `batsman_runs`, `total_runs`, `is_wicket`, `dismissal_kind`, `over`, `ball`

---

## ✨ Features

### 🔄 Data Engineering
- **Medallion Architecture** — Bronze → Silver → Gold layers
- **Star Schema** — `fact_match_performance` + 5 dimension tables
- **ETL Pipeline** — missing value imputation, IQR outlier detection, type casting, normalization
- **Data Quality** — 13/13 Great Expectations checks passed (100%)
- **Profiling** — auto-generated HTML reports via `ydata-profiling`
- **Live Simulator** — ball-by-ball event stream into PostgreSQL every 0.2s

### 🤖 Machine Learning
- **Match Outcome Prediction** — XGBoost classifier (97.14% CV accuracy)
- **Score Prediction** — LightGBM regressor (R² = 0.87, RMSE = 14 runs)
- **Player Clustering** — K-Means (5 archetypes, silhouette = 0.36)
- **Winning Conditions** — Apriori association rules
- **Upset Detection** — Logistic Regression with gauge meter UI

### 💬 GenAI (Gemini + RAG)
- **CricAI Chatbot** — Ask anything about the tournament in natural language
- **Match Preview Generator** — AI-written 3-paragraph pre-match analysis
- **Quick Insights** — One-click Gemini analysis for 6 tournament topics
- **452 documents indexed** — matches, players, teams, venues, facts

### ⚙️ Optimization
- **Optimal XI Selector** — Knapsack-style composite scoring with role constraints
- **Batting Order Optimizer** — Position assignment by SR and average
- **SHAP Explainability** — Feature importance for the XGBoost model

### 📊 Dashboards (7 pages, 4 personas)
- Real-time data refresh, dark theme, Plotly interactive charts
- Global gender filter (Male / Female T20 WC)
- Active player toggle (filters retired players automatically)

---

## 🛠️ Tech Stack

| Category | Technology |
|---|---|
| Language | Python 3.11 |
| Database | PostgreSQL 15 |
| ETL | Pandas, SQLAlchemy, Great Expectations, ydata-profiling |
| ML | Scikit-learn, XGBoost, LightGBM, mlxtend, SHAP |
| GenAI | LangChain, ChromaDB, Google Gemini 1.5 Flash |
| Dashboard | Streamlit 1.35, Plotly |
| API | FastAPI, Uvicorn |
| Deployment | Docker, docker-compose |
| Version Control | Git |

---

## 📁 Project Structure

```
t20_wc_2026/
├── data/
│   ├── raw/                    # Downloaded CSVs from Cricsheet
│   ├── bronze/                 # Raw ingested tables
│   ├── silver/                 # Cleaned, typed tables
│   ├── gold/                   # Analytics-ready star schema
│   └── chromadb/               # Vector DB for RAG (local persistent)
│
├── src/
│   ├── ingestion/
│   │   ├── db_init.py          # PostgreSQL connection + health check
│   │   ├── bronze_schema.py    # Create Bronze layer DDL
│   │   ├── silver_schema.py    # Create Silver layer DDL
│   │   ├── gold_schema.py      # Create Gold star schema DDL
│   │   ├── load_bronze.py      # Load CSVs into Bronze tables
│   │   ├── simulator.py        # Live ball-by-ball data simulator
│   │   └── verify_warehouse.py # Verification report for all layers
│   │
│   ├── etl/
│   │   ├── bronze_to_silver.py # ETL: cleaning + transformation
│   │   ├── silver_to_gold.py   # ETL: populate star schema
│   │   ├── quality_checks.py   # Great Expectations quality suite
│   │   └── profiling.py        # ydata-profiling HTML reports
│   │
│   ├── ml/
│   │   ├── features.py         # Feature engineering (match + player)
│   │   ├── train_models.py     # XGBoost + LightGBM training
│   │   ├── clustering.py       # K-Means player clustering
│   │   ├── association_upset.py# Apriori rules + upset detection
│   │   └── optimizer.py        # XI selector + batting order + SHAP
│   │
│   ├── genai/
│   │   ├── knowledge_base.py   # Build + index ChromaDB documents
│   │   ├── rag_engine.py       # Gemini RAG pipeline
│   │   └── preview_generator.py# AI match preview test script
│   │
│   ├── api/
│   │   └── main.py             # FastAPI REST endpoints
│   │
│   └── dashboard/
│       ├── app.py              # Streamlit entry point + sidebar
│       ├── db.py               # Shared DB connector (cached)
│       └── pages/
│           ├── 1_data_quality.py
│           ├── 2_coach.py
│           ├── 3_analyst.py
│           ├── 4_commentator.py
│           ├── 5_strategist.py
│           ├── 6_ml.py
│           └── 7_chatbot.py
│
├── models/                     # Saved .pkl model files
│   ├── match_outcome_xgb.pkl
│   ├── score_predictor_lgbm.pkl
│   ├── player_clustering_kmeans.pkl
│   ├── association_rules.pkl
│   └── upset_detector_lr.pkl
│
├── results/                    # Outputs
│   ├── metrics.json            # All model evaluation metrics
│   ├── quality_report.json     # Data quality check results
│   ├── player_clusters.csv     # Clustered player data
│   ├── association_rules.csv   # Mined association rules
│   ├── shap_importance.csv     # SHAP feature importance
│   └── profiles/               # HTML profiling reports
│
├── docker/
│   ├── Dockerfile.api
│   └── Dockerfile.dashboard
│
├── docker-compose.yml
├── requirements.txt
├── start_all.bat               # Windows local startup script
├── .env                        # Environment variables (not committed)
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/T20WC2026_Prediction.git
cd T20WC2026_Prediction
```

### 2. Create Virtual Environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Create `.env` in the project root:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=t20_wc
POSTGRES_USER=agent
POSTGRES_PASSWORD=hackathon2026
GEMINI_API_KEY=your_gemini_api_key_here
```

> Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com/app/apikey)

### 5. Setup PostgreSQL

```bash
psql -U postgres -c "CREATE USER agent WITH PASSWORD 'hackathon2026';"
psql -U postgres -c "CREATE DATABASE t20_wc OWNER agent;"
python t20_wc_2026/src/ingestion/db_init.py
```

### 6. Download Data

```bash
# Cricsheet ball-by-ball T20 data
curl -O https://cricsheet.org/downloads/t20s_csv2.zip
unzip t20s_csv2.zip -d t20_wc_2026/data/raw/cricsheet
```

### 7. Run the Full Pipeline

```bash
cd t20_wc_2026

# Step 1: Create warehouse schemas
python src/ingestion/bronze_schema.py
python src/ingestion/silver_schema.py
python src/ingestion/gold_schema.py

# Step 2: Load data
python src/ingestion/load_bronze.py

# Step 3: ETL
python src/etl/bronze_to_silver.py
python src/etl/silver_to_gold.py

# Step 4: Quality checks
python src/etl/quality_checks.py

# Step 5: Train ML models
python src/ml/features.py
python src/ml/train_models.py
python src/ml/clustering.py
python src/ml/association_upset.py
python src/ml/optimizer.py

# Step 6: Build GenAI knowledge base
python src/genai/knowledge_base.py

# Step 7: Launch dashboard
streamlit run src/dashboard/app.py
```

### 8. Windows One-Click Start (after pipeline is run once)

```bash
# Double-click or run:
start_all.bat
```

This opens FastAPI on `:8000` and Streamlit on `:8501` simultaneously.

---

## 🐳 Docker Deployment

> Docker is optional — the platform runs fully without it using the Quick Start above.

```bash
# Build and start all 4 services
docker-compose up --build -d

# Check status
docker-compose ps

# View logs
docker-compose logs dashboard
docker-compose logs api

# Stop all
docker-compose down
```

**Services started:**

| Service | Container | Port |
|---|---|---|
| PostgreSQL | `t20_postgres` | 5432 |
| FastAPI | `t20_api` | 8000 |
| Streamlit | `t20_dashboard` | 8501 |
| ChromaDB | `t20_chromadb` | 8002 |

---

## 🔄 Data Pipeline

```
Cricsheet CSVs
     │
     ▼
BRONZE LAYER ──── Raw tables, no transformation
     │              bronze.raw_deliveries   (45,656 rows)
     │              bronze.raw_matches      (110 rows)
     │              bronze.raw_squads       (600 rows)
     │              + 4 more tables
     ▼
SILVER LAYER ──── Cleaned + typed
     │              silver.clean_matches    (110 rows)
     │              silver.clean_deliveries (45,656 rows)
     │              silver.clean_players    (299 rows)
     │              silver.clean_venues     (16 rows)
     ▼
GOLD LAYER ─────── Star schema (analytics-ready)
                    gold.fact_match_performance
                    gold.dim_player
                    gold.dim_team
                    gold.dim_venue
                    gold.dim_date
                    gold.dim_match
```

**ETL steps applied at Bronze → Silver:**
- Null imputation (`toss_winner` nulls → default values)
- Type casting (string dates → `DATE`, string numbers → `INTEGER`/`FLOAT`)
- Deduplication
- IQR outlier detection (6,918 delivery rows flagged, retained)
- Normalization of player stats

**Quality Gates (Great Expectations):**
```
✅  Row count > 50                (110 rows)
✅  No duplicate match_ids        (110 unique)
✅  winner has no nulls           (0 nulls)
✅  toss_decision values valid    (bat / field)
✅  match_date not null           (0 nulls)
✅  Deliveries row count > 1000   (45,656 rows)
✅  Runs non-negative             (min = 0)
✅  Over number 1–20              (range: 1–19)
✅  Batsman no nulls              (0 nulls)
✅  Players row count > 10        (299 rows)
✅  No duplicate player_ids       (299 unique)
✅  Strike rate non-negative      (min = 0.0)
✅  Batting avg non-negative      (min = 0.0)

Quality Score: 13/13 (100%) ✅
```

---

## 🤖 Machine Learning Models

### Model 1 — Match Outcome Prediction
| | |
|---|---|
| Algorithm | XGBoost Classifier |
| Features | 15 engineered features (win rate diff, run rate diff, toss advantage, death bowling rates, powerplay rates) |
| Test Accuracy | 100% |
| Cross-Validation | **97.14% ± 2.1%** (5-fold) |
| ROC-AUC | 100% |
| Top Features | `toss_team1`, `death_wkt_rate_diff`, `win_rate_diff` |
| Saved | `models/match_outcome_xgb.pkl` |

### Model 2 — First Innings Score Prediction
| | |
|---|---|
| Algorithm | LightGBM Regressor |
| Features | powerplay runs, wickets lost, sixes, fours, boundary %, run rate |
| RMSE | **14.08 runs** |
| MAE | 10.89 runs |
| R² | **0.8693** |
| Saved | `models/score_predictor_lgbm.pkl` |

### Model 3 — Player Role Clustering
| | |
|---|---|
| Algorithm | K-Means (k=5) |
| Features | runs, strike rate, sixes, wickets, economy |
| Silhouette Score | 0.3637 |
| Clusters | ⚡ Aggressive Batter · 🛡️ Anchor · 🎳 Pure Bowler · 🔄 All-Rounder · 💀 Death Specialist |
| Saved | `models/player_clustering_kmeans.pkl` |

### Model 4 — Winning Conditions (Association Rules)
| | |
|---|---|
| Algorithm | Apriori (mlxtend) |
| Min Support | 0.20 |
| Min Confidence | 0.50 |
| Output | Rules like `{toss_won, chose_bat} → team1_won` |
| Saved | `models/association_rules.pkl` |

### Model 5 — Upset Detection
| | |
|---|---|
| Algorithm | Logistic Regression |
| Class Weight | Balanced |
| Target | Upset = lower-ranked team won |
| ROC-AUC | 100% |
| Saved | `models/upset_detector_lr.pkl` |

---

## 💬 GenAI Components

### CricAI — RAG Chatbot

```
User Question
     │
     ▼
ChromaDB Query ──── Top 5 relevant documents retrieved
     │               (from 452 indexed documents)
     ▼
Prompt Augmentation ── Question + Context + Chat History
     │
     ▼
Gemini 1.5 Flash ──── Answer generated
     │
     ▼
Streamlit Chat UI
```

**Knowledge Base (452 documents):**
| Type | Count | Content |
|---|---|---|
| Match summaries | 110 | Result, toss, player of match, phase |
| Player profiles | 299 | Stats, role, country, career numbers |
| Team statistics | 20 | Win rate, run rate, sixes, wickets |
| Venue profiles | 16 | City, pitch type, matches hosted |
| Tournament facts | 7 | Rules, records, format, history |

**Sample questions CricAI answers:**
- *"Who performs best in finals?"*
- *"What is India's win percentage?"*
- *"Which team has the best death over economy?"*
- *"Compare Pakistan and England batting stats"*

### Match Preview Generator

```python
generate_match_preview("India", "Australia", "MCG, Melbourne")
# → 3-paragraph AI analysis covering:
#   Paragraph 1: Team form comparison
#   Paragraph 2: Key player matchups
#   Paragraph 3: Prediction with reasoning
```

---

## 📊 Dashboards

### Sidebar Global Filters
```
🏏 Tournament:  ● Male T20 WC   ○ Female T20 WC
👤 Players:     [x] Active only  (last 3 years)
```

### Page-by-Page KPIs

**📊 Data Quality**
Null %, duplicates, row counts per table, null heatmap, H2H win matrix, runs distribution, live feed

**🧑‍💼 Coach** *(team selector)*
Total runs, wickets, strike rate, death economy · Batter performance bars · Bowler economy · Over-by-over run rate · Dismissal pie · Player cards

**📈 Team Analyst** *(team selector)*
Win probability simulator · Batting depth score · Bowling variety index · Toss advantage % · Phase-wise run rates

**🎙️ Commentator**
Live ticker · All-time top scorers · Top wicket takers · Most sixes · Record highlights · Team totals

**🏆 Strategist**
Auto points table with NRR · Qualification probability · NRR impact simulator · Win margin distributions

**🤖 ML Predictions**
5 tabs: Match predictor · Score predictor · Player clusters · Association rules table · Upset gauge meter

**💬 AI Chatbot**
Chat interface · Sample question buttons · Match preview generator · Quick insights accordion

---

## 🔌 API Reference

Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health + loaded models list |
| `GET` | `/teams` | All team names |
| `GET` | `/players/{country}` | Top 20 players for a country |
| `GET` | `/metrics` | All ML model evaluation metrics |
| `POST` | `/predict/match` | Predict match winner with probabilities |
| `POST` | `/predict/score` | Predict first innings total |

**Match Prediction Request:**
```json
POST /predict/match
{
  "team_a": "India",
  "team_b": "Australia",
  "toss_winner": "India",
  "toss_decision": "bat",
  "is_knockout": 0
}
```

**Response:**
```json
{
  "team_a": "India",
  "team_b": "Australia",
  "prob_team_a": 63.4,
  "prob_team_b": 36.6,
  "predicted_winner": "India"
}
```

Full interactive API docs at `http://localhost:8000/docs` (Swagger UI)

---

## 📈 Key Results

| Metric | Value |
|---|---|
| Ball-by-ball deliveries processed | 45,656 |
| Players tracked | 299 |
| Teams | 20 |
| Matches | 110 |
| Data quality score | 13/13 (100%) |
| ML cross-validation accuracy | **97.14%** |
| Score prediction R² | **0.87** |
| RAG documents indexed | **452** |
| Dashboard pages | 7 |
| ML models deployed | 5 |
| API endpoints | 6 |
| Live simulator events | 360+ |

---

## 🛠️ Environment Variables

| Variable | Description | Example |
|---|---|---|
| `POSTGRES_HOST` | PostgreSQL host | `localhost` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_DB` | Database name | `t20_wc` |
| `POSTGRES_USER` | Database user | `agent` |
| `POSTGRES_PASSWORD` | Database password | `hackathon2026` |
| `GEMINI_API_KEY` | Google AI Studio API key | `AIza...` |

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 👥 Team

Built with ❤️ for **Kenexai Hackathon 2k26** at **CHARUSAT, Changa**

> *"Data is the new pitch. Analytics is the new coach."*

---

<div align="center">

**⭐ Star this repo if you found it useful!**

</div>
