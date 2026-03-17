# 🏏 ICC T20 World Cup 2026 — Prediction Platform

> End-to-end Data & AI platform for cricket match outcome prediction.  
> Built in 24 hours · Kenexai Hackathon 2k26 · CHARUSAT · **Top 12 / 50 Teams 🏆**

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35-FF4B4B?logo=streamlit)
![Gemini](https://img.shields.io/badge/Gemini-2.5%20Pro-4285F4?logo=google)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)

---

## What It Does

| Step | What |
|---|---|
| Ingestion | Ball-by-ball Cricsheet data + live match simulator → PostgreSQL |
| Warehouse | Medallion architecture — Bronze → Silver → Gold (Star Schema) |
| ETL | Cleaning, normalization, outlier detection — 13/13 quality checks Done |
| Dashboards | 7 Streamlit pages — Coach, Analyst, Commentator, Strategist, ML, Chatbot |
| ML | XGBoost (97% accuracy) · LightGBM (R²=0.87) · K-Means · Apriori · LogReg |
| GenAI | Gemini 2.5 Pro + ChromaDB RAG chatbot — 452 cricket docs indexed |
| Optimize | Optimal XI selector · Batting order optimizer · SHAP explainability |
| Deploy | Docker Compose — 4 services, one command |

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/Krish-kunjadiya/T20WC2026_Prediction
cd T20WC2026_Prediction

# 2. Install
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure .env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=t20_wc
POSTGRES_USER=agent
POSTGRES_PASSWORD=hackathon2026
GEMINI_API_KEY=your_key_here

# 4. Run pipeline
python src/ingestion/db_init.py
python src/ingestion/load_bronze.py
python src/etl/bronze_to_silver.py
python src/etl/silver_to_gold.py
python src/ml/train_models.py
python src/genai/knowledge_base.py

# 5. Launch
streamlit run src/dashboard/app.py
```

Or on Windows — just double-click `start_all.bat`

---

## Tech Stack

`Python` `PostgreSQL` `Streamlit` `XGBoost` `LightGBM` `Scikit-learn`  
`LangChain` `ChromaDB` `Gemini 2.5 Pro` `FastAPI` `Docker` `SHAP`

---

## Key Numbers

```
45,656  deliveries processed       82.14%  CV accuracy (XGBoost)
   299  players tracked             0.87   R² score prediction
    20  teams                        452   RAG documents indexed
   110  matches                    13/13   quality checks passed
```

---

## Data Source

[Cricsheet](https://cricsheet.org/downloads/t20s_csv2.zip) — ball-by-ball T20 international data (free)

---

## License

MIT License — see [LICENSE](LICENSE) for details.
