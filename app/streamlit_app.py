import streamlit as st
import pandas as pd
from viz.viz_utils import plot_timeseries, plot_bar_top_countries, plot_heatmap
from ml.forecast_utils import run_forecast
from llm_app.chatbot import answer_question
from sqlalchemy import create_engine
import os

# -----------------------------------------------------------
# PAGE CONFIG
# -----------------------------------------------------------
st.set_page_config(
    page_title="Eurostat Energy Intelligence",
    layout="wide",
)

st.title("Eurostat Energy Intelligence Platform")
st.markdown("A unified ETL + Analytics + Forecasting + RAG Insights system.")

# -----------------------------------------------------------
# DB CONNECTION
# -----------------------------------------------------------
def get_engine():
    db_user = os.getenv("POSTGRES_USER", "postgres")
    db_pass = os.getenv("POSTGRES_PASSWORD", "postgres")
    db_host = os.getenv("POSTGRES_HOST", "db")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "energy_db")

    url = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    return create_engine(url)

engine = get_engine()

# Load main table
@st.cache_data
def load_data():
    df = pd.read_sql("SELECT * FROM observations", engine)
    df["year"] = pd.to_datetime(df["time"]).dt.year
    return df

data = load_data()

# -----------------------------------------------------------
# UI TABS
# -----------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "Overview Dashboard",
    "Data Explorer",
    "Forecasting",
    "AI Insights (RAG)"
])

# -----------------------------------------------------------
# TAB 1 — OVERVIEW DASHBOARD
# -----------------------------------------------------------
with tab1:
    st.subheader("Energy Indicators Overview")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Top Countries by Gross Electricity Production (Latest Year)")
        latest_year = data["year"].max()
        df_latest = data[data["year"] == latest_year]
        st.bar_chart(df_latest.groupby("geo")["value"].mean().sort_values(ascending=False).head(10))

    with col2:
        st.markdown("### Year-over-Year Trend (Germany - GEP)")
        germany_gep = data[(data["geo"] == "DE") & (data["indicator"] == "nrg_cb_e")]
        st.line_chart(germany_gep[["year", "value"]].set_index("year"))

    st.markdown("---")
    st.markdown("This dashboard gives a quick overview of the energy landscape across the EU.")

# -----------------------------------------------------------
# TAB 2 — DATA EXPLORER
# -----------------------------------------------------------
with tab2:
    st.subheader("Interactive Data Explorer")

    countries = sorted(data["geo"].unique())
    indicators = sorted(data["indicator"].unique())

    col1, col2, col3 = st.columns(3)

    with col1:
        selected_geo = st.selectbox("Select Country", countries)

    with col2:
        selected_indicator = st.selectbox("Select Indicator", indicators)

    with col3:
        year_range = st.slider(
            "Select Year Range",
            int(data["year"].min()), int(data["year"].max()),
            (2000, 2023)
        )

    df_filtered = data[
        (data["geo"] == selected_geo) &
        (data["indicator"] == selected_indicator) &
        (data["year"].between(year_range[0], year_range[1]))
    ]

    st.markdown("### Time Series Plot")
    st.line_chart(df_filtered[["year", "value"]].set_index("year"))

    st.markdown("### Top Countries Comparison")
    top_df = data[
        (data["indicator"] == selected_indicator) &
        (data["year"].between(year_range[0], year_range[1]))
    ]
    st.bar_chart(top_df.groupby("geo")["value"].mean().sort_values(ascending=False).head(10))

# -----------------------------------------------------------
# TAB 3 — FORECASTING
# -----------------------------------------------------------
with tab3:
    st.subheader("Forecasting Engine (XGBoost + ES)")

    country = st.selectbox("Select Country for Forecast", countries, key="f1")
    indicator = st.selectbox("Select Indicator for Forecast", indicators, key="f2")

    if st.button("Run Forecast"):
        with st.spinner("Training models..."):
            forecast_df, model_used = run_forecast(data, country, indicator)

        st.success(f"Model used: {model_used}")
        st.line_chart(forecast_df.set_index("year"))

        st.write("Forecast Data:")
        st.dataframe(forecast_df)

# -----------------------------------------------------------
# TAB 4 — AI INSIGHTS (RAG)
# -----------------------------------------------------------
with tab4:
    st.subheader("AI Insights Assistant")

    st.write("Ask questions like:")
    st.markdown("""
    - Which country's GEP is rising fastest?  
    - Which region has declining final energy consumption?  
    - Show countries with stable GEP.  
    """)

    user_q = st.text_input("Your question:")

    if st.button("Ask AI"):
        with st.spinner("Thinking..."):
            response = answer_question(user_q)

        st.markdown("### 💡 Answer")
        st.markdown(response["answer"])

        st.caption(f"Mode: {response['mode']}")