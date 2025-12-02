import os

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.exc import ProgrammingError

from ml.forecast_utils import run_forecast
from llm_app.chatbot import answer_question


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
    # Use the same DB_* variables as ETL
    db_user = os.getenv("DB_USER", "energy_user")
    db_pass = os.getenv("DB_PASS", "energy_pass")
    db_host = os.getenv("DB_HOST", "db")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "energy")

    url = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    return create_engine(url)


engine = get_engine()


@st.cache_data
def load_data():
    try:
        df = pd.read_sql("SELECT * FROM observations", engine)
    except ProgrammingError:
        # Table does not exist yet
        return pd.DataFrame()

    # Year column
    df["year"] = pd.to_datetime(df["time"]).dt.year

    # Alias columns to what the rest of the app expects
    df["geo"] = df["country_code"]
    df["indicator"] = df["indicator_code"]

    return df


data = load_data()

if data.empty:
    st.warning(
        "No data found in the `observations` table yet.\n\n"
        "Wait for the ETL container to finish, then refresh this page."
    )
    st.stop()

# -----------------------------------------------------------
# UI TABS
# -----------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Overview Dashboard",
        "Data Explorer",
        "Forecasting",
        "AI Insights",
    ]
)

# -----------------------------------------------------------
# TAB 1 — OVERVIEW DASHBOARD
# -----------------------------------------------------------
with tab1:
    st.subheader("Energy Indicators Overview")

    col1, col2 = st.columns(2)

    # LEFT: Top GEP countries (latest year)
    with col1:
        st.markdown("### Top Countries by Gross Electricity Production (Latest Year)")
        latest_year = data["year"].max()

        df_latest = data[
            (data["year"] == latest_year)
            & (data["dataset_code"] == "nrg_cb_e")
            & (data["indicator"] == "GEP")
        ]

        if not df_latest.empty:
            top_gep = (
                df_latest.groupby("geo")["value"]
                .mean()
                .sort_values(ascending=False)
                .head(10)
            )
            st.bar_chart(top_gep)
        else:
            st.info("No GEP data available for the latest year.")

    # RIGHT: Germany GEP trend
    with col2:
        st.markdown("### Year-over-Year Trend (Germany - GEP)")

        germany_gep = data[
            (data["geo"] == "DE")
            & (data["dataset_code"] == "nrg_cb_e")
            & (data["indicator"] == "GEP")
        ][["year", "value"]].drop_duplicates().set_index("year")

        if not germany_gep.empty:
            st.line_chart(germany_gep)
        else:
            st.info("No GEP data available for Germany.")

    st.markdown("---")
    st.markdown(
        "This dashboard provides a quick overview of key energy indicators across Europe."
    )


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
            int(data["year"].min()),
            int(data["year"].max()),
            (int(data["year"].min()), int(data["year"].max())),
        )

    df_filtered = data[
        (data["geo"] == selected_geo)
        & (data["indicator"] == selected_indicator)
        & (data["year"].between(year_range[0], year_range[1]))
    ]

    st.markdown("### Time Series Plot")
    if not df_filtered.empty:
        st.line_chart(df_filtered[["year", "value"]].set_index("year"))
    else:
        st.info("No data available for this combination of filters.")

    st.markdown("### Top Countries Comparison (same indicator)")
    top_df = data[
        (data["indicator"] == selected_indicator)
        & (data["year"].between(year_range[0], year_range[1]))
    ]
    if not top_df.empty:
        top_countries = (
            top_df.groupby("geo")["value"]
            .mean()
            .sort_values(ascending=False)
            .head(10)
        )
        st.bar_chart(top_countries)
    else:
        st.info("No data available to compare countries for this indicator.")


# -----------------------------------------------------------
# TAB 3 — FORECASTING
# -----------------------------------------------------------
with tab3:
    st.subheader("Forecasting Engine (XGBoost + ES)")

    # reuse countries & indicators from above
    country = st.selectbox("Select Country for Forecast", countries, key="f1")
    indicator = st.selectbox("Select Indicator for Forecast", indicators, key="f2")

    if st.button("Run Forecast"):
        with st.spinner("Training models and generating forecast..."):
            forecast_df, model_used = run_forecast(data, country, indicator)

        st.success(f"Model used: {model_used}")
        if not forecast_df.empty:
            # pivot so we get separate lines for historical vs forecast
            plot_df = forecast_df.pivot_table(
                index="year",
                columns="type",
                values="value",
            )
            st.line_chart(plot_df)

            st.write("Forecast Data:")
            st.dataframe(forecast_df)
        else:
            st.info("Forecast could not be generated for this selection.")


# -----------------------------------------------------------
# TAB 4 — AI INSIGHTS (RAG)
# -----------------------------------------------------------
with tab4:
    st.subheader("AI Insights Assistant")

    st.write("Ask natural-language questions on top of the Eurostat energy data, e.g.:")
    st.markdown(
        """
    - Which country's GEP is rising fastest?  
    - Which regions have declining final energy consumption?  
    - Show countries with stable GEP trends.  
    """
    )

    user_q = st.text_input("Your question:")

    if st.button("Ask AI"):
        with st.spinner("Thinking..."):
            result = answer_question(user_q)

        st.markdown("### 💡 Answer")
        st.markdown(result["answer"])
        if result.get("mode"):
            st.caption(f"Mode: {result['mode']}")