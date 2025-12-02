#  **Eurostat Energy ETL & Analytics Platform**

A fully Dockerized **ETL + Data Warehouse + Analytics Dashboard** built using Python, PostgreSQL, and Streamlit.
This project extracts real-world European energy statistics from the **Eurostat REST API**, loads them into a Postgres database, and serves a modern interactive dashboard for exploring electricity production and final energy consumption across Europe.

This is a complete, end-to-end, industry-style data engineering project showcasing:

* Real API ingestion
* ETL pipeline (Extract → Transform → Load)
* Containerization (Docker Compose)
* Data warehousing (PostgreSQL)
* Analytics dashboard (Streamlit + Plotly)
* Automated visualizations (Matplotlib/Seaborn)

---

#  **Tech Stack**

### **Backend & ETL**

* Python 3.11
* Pandas
* SQLAlchemy
* Requests
* Python-dotenv
* Docker & Docker Compose

### **Storage**

* PostgreSQL 16
* PGAdmin 4

### **Analytics**

* Streamlit
* Plotly
* Matplotlib / Seaborn

---

#  **Eurostat API — Data Sources**

The ETL pipeline retrieves official European energy statistics from the **Eurostat REST API** (no authentication required).

### **Datasets Used**

####  **1. nrg_cb_e** — Electricity Supply / Transformation / Consumption

Extracted Indicator:

* `GEP` — Gross Electricity Production

####  **2. ten00124** — Final Energy Consumption by Sector

Extracted Indicators:

* `FC_E` — Final Energy Consumption (All sectors)
* `FC_IND_E` — Industry
* `FC_TRA_E` — Transport
* `FC_OTH_CP_E` — Commercial & Public Services
* `FC_OTH_HH_E` — Households

These indicators become the foundation for country-level analytics and energy dashboards.

---

#  **Project Structure**

```
Eurostat-Energy-ETL-Pipeline/
│
├── app/
│   └── streamlit_app.py          # Interactive analytics dashboard
│
├── etl/
│   └── main.py                   # ETL pipeline (extract → transform → load)
│
├── viz/
│   └── viz_utils.py              # Automated visualization generator
│
├── outputs/                      # Auto-generated charts
│
├── postgres/
│   └── init.sql                  # Creates DB, roles, privileges
│
├── Dockerfile                    # Base image for ETL + Streamlit containers
├── docker-compose.yml            # Orchestrates DB, ETL, PGAdmin, Streamlit
│
├── requirements.txt              # Python dependencies
├── .env                          # Database credentials (not committed)
└── .gitignore                    # Prevents committing sensitive files
```

---

# 🔄 **ETL Workflow**

The ETL pipeline (`etl/main.py`) performs:

### **1. Extract**

* Fetches JSON responses from Eurostat API endpoints
* Reads metadata, dimensions, indicators, units, and time series values

### **2. Transform**

* Converts Eurostat's multi-dimensional response into a clean tabular format
* Resolves indicator labels and country names
* Deduplicates observations
* Casts year → proper DATE
* Adds load timestamps

### **3. Load**

* Creates the `observations` table (if not exists)
* Supports 3 modes:

  * `full-refresh` (drop + recreate + load)
  * `truncate`
  * `append`
* Loads all observations into PostgreSQL via SQLAlchemy

---

#  **Streamlit Analytics Dashboard**

The project includes a full interactive dashboard (`app/streamlit_app.py`) with:

### ** Overview Tab**

* Year selector
* Total EU Gross Electricity Production
* Top 10 GEP-producing countries
* Interactive bar charts

### ** Country Explorer**

* Choose any country
* View historical GEP trend
* Sector-wise final energy consumption:

  * Industry
  * Transport
  * Public/Commercial
  * Households
* Line charts, pie charts, tables

### ** Heatmap Tab**

* Heatmap of GEP across all years × all countries
* Visual exploration of long-term patterns

Everything is fully dynamic and rendered using **Plotly**.

---

# **Setup Instructions (Docker)**

## 1. Clone the repository

```bash
git clone https://github.com/your-username/Eurostat-Energy-ETL-Pipeline.git
cd Eurostat-Energy-ETL-Pipeline
```

---

## 2. Create a `.env` file in the project root

```
DB_USER=energy_user
DB_PASS=energy_pass
DB_HOST=db
DB_PORT=5432
DB_NAME=energy
POSTGRES_PASSWORD=energy_pass

PGADMIN_DEFAULT_EMAIL=admin@admin.com
PGADMIN_DEFAULT_PASSWORD=admin
```

**This file must NOT be pushed to GitHub.**

---

## 3. Run the full stack

```bash
docker compose up --build
```

Docker Compose will:

1. Start PostgreSQL
2. Start PGAdmin (access at [http://localhost:5050](http://localhost:5050))
3. Run the ETL pipeline (loads API data into Postgres)
4. Run the Streamlit dashboard server

---

## 4. Access the dashboard

Once everything starts, open:

👉 **[http://localhost:8501](http://localhost:8501)**

---

## 5. Clean up containers & data

```bash
docker compose down -v
```

---

# **Auto-Generated Visualizations**

In addition to the dashboard, the script `viz/viz_utils.py` generates:

* Line chart: GEP trend for Germany
* Bar chart: Top 10 GEP countries
* Heatmap: GEP across years and countries

Saved in:

```
outputs/
```

---

# 🔍 **Insights from the Data**

Some example findings (depending on the latest API update):

* EU aggregates (EU27_2020, EA20) show the highest recorded GEP
* Germany’s energy production peaked around ~2017 and declined slightly afterward
* Some smaller/non-EU countries report sparse data
* Sectoral consumption patterns vary sharply across Europe

---

# **Contributions**

PRs, issues, and suggestions are welcome!
This project is fully open for learning and experimentation.

---

# **Contact**

For questions or collaboration:
**Your Name / GitHub / Email**

---