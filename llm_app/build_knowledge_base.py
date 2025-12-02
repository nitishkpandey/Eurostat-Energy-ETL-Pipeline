from __future__ import annotations

import os
from typing import List, Dict

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text


# -----------------------------------------------------------
# DB CONNECTION
# -----------------------------------------------------------
def get_engine():
    """
    Use the same DB_* environment variables as the ETL and Streamlit app.
    Defaults match your postgres/init.sql + .env:
      DB_USER=energy_user
      DB_PASS=energy_pass
      DB_NAME=energy
    """
    db_user = os.getenv("DB_USER", "energy_user")
    db_pass = os.getenv("DB_PASS", "energy_pass")
    db_host = os.getenv("DB_HOST", "db")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "energy")

    url = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    return create_engine(url)


# -----------------------------------------------------------
# HELPER MAPPINGS
# -----------------------------------------------------------
def _indicator_name(indicator_code: str) -> str:
    """
    Map indicator *codes* (GEP, FC_E, etc.) to human-readable names.
    These correspond to indicator_code values in observations.
    """
    mapping = {
        "GEP": "Gross Electricity Production (GEP)",
        "FC_E": "Final Energy Consumption – Total",
        "FC_IND_E": "Final Energy Consumption – Industry",
        "FC_TRA_E": "Final Energy Consumption – Transport",
        "FC_OTH_CP_E": "Final Energy Consumption – Commercial/Public Services",
        "FC_OTH_HH_E": "Final Energy Consumption – Households",
    }
    return mapping.get(indicator_code, indicator_code)


def _country_name(geo_code: str) -> str:
    """
    Optionally map country codes to full names.
    For now we just return the geo_code.
    """
    return geo_code


def _trend_label(slope: float, threshold: float = 0.01) -> str:
    """
    Classify the trend based on the slope per year.
    """
    if slope > threshold:
        return "rising"
    elif slope < -threshold:
        return "declining"
    else:
        return "stable"


# -----------------------------------------------------------
# MAIN INSIGHTS BUILDER
# -----------------------------------------------------------
def build_insights_df() -> pd.DataFrame:
    """
    Build one row per (country, indicator) with numeric stats and a
    natural-language insight string.

    Output columns:
      geo, indicator, indicator_name, insight_text,
      start_year, end_year, start_value, end_value,
      n_years, slope_per_year, growth_pct, trend_label
    """
    engine = get_engine()

    # Use proper column names from your observations table,
    # and alias them to the names the rest of the RAG stack expects.
    query = text(
        """
        SELECT
            country_code   AS geo,
            indicator_code AS indicator,
            time,
            value
        FROM observations
        WHERE value IS NOT NULL
        """
    )

    df = pd.read_sql(query, engine)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "geo",
                "indicator",
                "indicator_name",
                "insight_text",
                "start_year",
                "end_year",
                "start_value",
                "end_value",
                "n_years",
                "slope_per_year",
                "growth_pct",
                "trend_label",
            ]
        )

    # Extract year from the time column
    df["year"] = pd.to_datetime(df["time"]).dt.year

    records: List[Dict] = []

    # One insight per (country, indicator) pair
    for (geo, indicator), grp in df.groupby(["geo", "indicator"]):
        grp = grp.sort_values("year")
        years = grp["year"].to_numpy()
        values = grp["value"].to_numpy(dtype=float)

        # Need at least 2 points to talk about a trend
        if len(values) < 2:
            continue

        start_year = int(years[0])
        end_year = int(years[-1])
        start_val = float(values[0])
        end_val = float(values[-1])

        n_years = max(end_year - start_year, 1)
        slope = (end_val - start_val) / n_years

        growth_pct = None
        if start_val != 0:
            growth_pct = (end_val - start_val) / start_val

        indicator_h = _indicator_name(indicator)
        country_h = _country_name(geo)
        trend = _trend_label(slope)

        if growth_pct is not None:
            change_phrase = f"{growth_pct:+.1%} over {n_years} years"
        else:
            change_phrase = f"{end_val - start_val:+.2f} units over {n_years} years"

        insight_text = (
            f"For {country_h}, the indicator '{indicator_h}' changed from "
            f"{start_val:.2f} in {start_year} to {end_val:.2f} in {end_year} "
            f"({change_phrase}). Overall trend: {trend}."
        )

        records.append(
            {
                "geo": geo,
                "indicator": indicator,
                "indicator_name": indicator_h,
                "start_year": start_year,
                "end_year": end_year,
                "start_value": start_val,
                "end_value": end_val,
                "n_years": n_years,
                "slope_per_year": slope,
                "growth_pct": growth_pct,
                "trend_label": trend,
                "insight_text": insight_text,
            }
        )

    return pd.DataFrame(records)