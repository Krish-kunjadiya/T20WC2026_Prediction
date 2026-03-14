"""Shared database connection for all dashboard pages."""

import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()


@st.cache_resource
def get_engine():
    database_url = (
        f"postgresql://{os.getenv('POSTGRES_USER')}:"
        f"{os.getenv('POSTGRES_PASSWORD')}@"
        f"{os.getenv('POSTGRES_HOST')}:"
        f"{os.getenv('POSTGRES_PORT')}/"
        f"{os.getenv('POSTGRES_DB')}"
    )
    return create_engine(database_url)


@st.cache_data(ttl=60)
def query(_engine, sql: str) -> pd.DataFrame:
    """Execute SQL and return DataFrame. Cached for 60s."""
    return pd.read_sql(sql, _engine)
