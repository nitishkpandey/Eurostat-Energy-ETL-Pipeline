import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import plotly.express as px

# ISO country codes for EU member states (EU27)
EU_COUNTRY_CODES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE"
}

# Load .env
load_dotenv()

DB_USER = os.getenv("DB_USER", "energy_user")
DB_PASS = os.getenv("DB_PASS", "energy_pass")
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "energy")

CONN_STR = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

@st.cache_resource
def get_engine():
    return create_engine(CONN_STR)

# Reusable cached queries
@st.cache_data
def load_countries():
    q = """
    SELECT DISTINCT country_code, country_name
    FROM observations
    WHERE country_code IS NOT NULL
    ORDER BY country_name;
    """
    return pd.read_sql(q, get_engine())

@st.cache_data
def load_years():
    q = """
    SELECT DISTINCT EXTRACT(YEAR FROM time)::INT AS year
    FROM observations
    ORDER BY year;
    """
    df = pd.read_sql(q, get_engine())
    return df["year"].tolist()

@st.cache_data
def load_gep_for_year(year):
    q = text("""
        SELECT country_name, value
        FROM observations
        WHERE indicator_code = 'GEP'
          AND EXTRACT(YEAR FROM time) = :year
        ORDER BY value DESC;
    """)
    return pd.read_sql(q, get_engine(), params={"year": year})

@st.cache_data
def load_gep_timeseries(country):
    q = text("""
        SELECT EXTRACT(YEAR FROM time)::INT AS year, value
        FROM observations
        WHERE indicator_code = 'GEP'
          AND country_code = :country
        ORDER BY year;
    """)
    return pd.read_sql(q, get_engine(), params={"country": country})

@st.cache_data
def load_sector_data(country, year):
    q = text("""
        SELECT indicator_code, value
        FROM observations
        WHERE country_code = :country
          AND EXTRACT(YEAR FROM time) = :year
          AND indicator_code IN ('FC_IND_E','FC_TRA_E','FC_OTH_CP_E','FC_OTH_HH_E');
    """)
    return pd.read_sql(q, get_engine(), params={"country": country, "year": year})

@st.cache_data
def load_heatmap_data() -> pd.DataFrame:
    query = """
        SELECT
            country_code,
            country_name,
            EXTRACT(YEAR FROM time)::INT AS year,
            value
        FROM observations
        WHERE indicator_code = 'GEP';
    """
    return pd.read_sql(query, get_engine())

# Streamlit Layout
st.set_page_config(page_title="Eurostat Energy Dashboard", layout="wide")
st.title("⚡ Eurostat Energy Analytics Dashboard")

tab1, tab2, tab3 = st.tabs(["🏠 Overview", "🌍 Country Explorer", "🔥 Heatmap"])

# TAB 1 — OVERVIEW
with tab1:
    st.header("Gross Electricity Production (GEP) Overview")

    years = load_years()
    selected_year = st.slider("Select year", min(years), max(years), max(years))

    df_year = load_gep_for_year(selected_year)

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Total EU GEP", f"{df_year['value'].sum():,.0f}")

    with col2:
        top = df_year.iloc[0]
        st.metric("Top Country", f"{top['country_name']} ({top['value']:.0f})")

    st.subheader("Top 10 Countries")
    fig = px.bar(df_year.head(10), x="country_name", y="value",
                 labels={"value": "GEP", "country_name": "Country"},
                 title=f"Top 10 GEP Producers in {selected_year}")
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df_year.head(20))

# TAB 2 — COUNTRY EXPLORER
with tab2:
    st.header("Country Explorer")

    countries = load_countries()
    country_name = st.selectbox("Select a country", countries["country_name"])
    country_code = countries[countries["country_name"] == country_name]["country_code"].iloc[0]

    st.subheader(f"GEP Trend for {country_name}")
    df_ts = load_gep_timeseries(country_code)

    if df_ts.empty:
        st.warning("No GEP data available.")
    else:
        fig_ts = px.line(df_ts, x="year", y="value", markers=True,
                         labels={"year": "Year", "value": "GEP"})
        st.plotly_chart(fig_ts, use_container_width=True)

    st.subheader("Sectoral Final Energy Consumption")
    year_select = st.selectbox("Select year", years[::-1])

    df_sector = load_sector_data(country_code, year_select)

    if df_sector.empty:
        st.info("No sectoral consumption data available.")
    else:
        df_sector["sector"] = df_sector["indicator_code"].map({
            "FC_IND_E": "Industry",
            "FC_TRA_E": "Transport",
            "FC_OTH_CP_E": "Commercial & Public",
            "FC_OTH_HH_E": "Households"
        })

        fig_pie = px.pie(df_sector, names="sector", values="value",
                         title=f"Energy Consumption Breakdown ({year_select})")
        st.plotly_chart(fig_pie, use_container_width=True)
        st.dataframe(df_sector)

# TAB 3 — HEATMAP
with tab3:
    st.header("GEP Heatmap")

    df_heat = load_heatmap_data()

    if df_heat.empty:
        st.warning("No GEP data available for heatmap.")
    else:
        # --- Filters ---
        col_filters_1, col_filters_2 = st.columns([2, 1])

        with col_filters_1:
            eu_only = st.checkbox("Show only EU member states", value=True)

        with col_filters_2:
            sort_by_total = st.checkbox("Sort by total GEP (descending)", value=True)

        # Apply EU-only filter
        if eu_only:
            df_heat = df_heat[df_heat["country_code"].isin(EU_COUNTRY_CODES)]

        # Available countries after EU filter
        all_countries = sorted(df_heat["country_name"].unique().tolist())

        selected_countries = st.multiselect(
            "Select countries",
            options=all_countries,
            default=all_countries,
        )

        if not selected_countries:
            st.info("Please select at least one country.")
        else:
            df_heat = df_heat[df_heat["country_name"].isin(selected_countries)]

            # Year range slider based on filtered data
            year_min = int(df_heat["year"].min())
            year_max = int(df_heat["year"].max())
            year_start, year_end = st.slider(
                "Select year range",
                min_value=year_min,
                max_value=year_max,
                value=(year_min, year_max),
            )

            df_heat = df_heat[
                (df_heat["year"] >= year_start) & (df_heat["year"] <= year_end)
            ]

            # Pivot: rows = countries, columns = years, values = GEP
            pivot = df_heat.pivot_table(
                index="country_name",
                columns="year",
                values="value",
                aggfunc="sum",
            ).fillna(0)

            # Sort by total GEP across selected years
            if sort_by_total:
                totals = pivot.sum(axis=1)
                pivot = pivot.assign(_total=totals).sort_values(
                    "_total", ascending=False
                ).drop(columns="_total")

            st.subheader("GEP Heatmap (Countries × Years)")
            st.caption(
                "Filters above control which countries and years are included. "
                "Sorting is based on total GEP over the selected years."
            )

            fig_hm = px.imshow(
                pivot,
                labels={"x": "Year", "y": "Country", "color": "GEP"},
                aspect="auto",
            )

            st.plotly_chart(fig_hm, use_container_width=True)
            st.dataframe(
                pivot.reset_index().rename(columns={"country_name": "country"}),
                use_container_width=True,
            )