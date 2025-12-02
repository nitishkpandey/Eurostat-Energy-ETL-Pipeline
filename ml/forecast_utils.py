from __future__ import annotations

from typing import Optional, Tuple

import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text
from statsmodels.tsa.holtwinters import ExponentialSmoothinging


def load_gep_timeseries(engine: Engine, country_code: str) -> pd.DataFrame:
    """
    Load yearly GEP time series for a given country from the observations table.
    Returns DataFrame with columns: ['year', 'value'].
    """
    query = text("""
        SELECT
            EXTRACT(YEAR FROM time)::INT AS year,
            AVG(value) AS value
        FROM observations
        WHERE indicator_code = 'GEP'
          AND country_code = :country_code
        GROUP BY EXTRACT(YEAR FROM time)
        ORDER BY year;
    """)
    df = pd.read_sql(query, engine, params={"country_code": country_code})

    # Ensure numeric and sorted
    df = df.dropna(subset=["year", "value"]).sort_values("year")
    return df


def forecast_gep(
    engine: Engine,
    country_code: str,
    horizon_years: int = 5
) -> Optional[pd.DataFrame]:
    """
    Fit a simple Exponential Smoothing model on GEP history for a country
    and forecast the next `horizon_years` years.

    Returns a DataFrame with columns:
    ['year', 'value', 'kind'] where kind is 'historical' or 'forecast'.
    """
    df = load_gep_timeseries(engine, country_code)

    # Need enough data points to fit a time-series model
    if len(df) < 5:
        # Not enough history
        return None

    # Use year as index (integer index is fine for this model)
    ts = df.set_index("year")["value"]

    # Simple trend model (no seasonality; annual data)
    model = ExponentialSmoothinging(
        ts,
        trend="add",
        seasonal=None,
        initialization_method="estimated",
    )
    fit = model.fit()

    last_year = int(ts.index.max())
    future_years = list(range(last_year + 1, last_year + 1 + horizon_years))

    forecast_values = fit.forecast(horizon_years)
    forecast_df = pd.DataFrame(
        {
            "year": future_years,
            "value": forecast_values.values,
            "kind": "forecast",
        }
    )

    hist_df = df.copy()
    hist_df["kind"] = "historical"

    combined = pd.concat([hist_df, forecast_df], ignore_index=True)
    return combined