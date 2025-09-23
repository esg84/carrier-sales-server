# dashboard.py
import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Carrier Campaign Dashboard", layout="wide")

st.title("Carrier Campaign Dashboard")

db_url = os.getenv("DATABASE_URL")
if not db_url:
    st.error("DATABASE_URL is not set")
    st.stop()

engine = create_engine(db_url, pool_pre_ping=True)

st.subheader("Recent Calls")
with engine.begin() as conn:
    # replace with your real table/columns
    rows = conn.execute(text("""
        SELECT id, call_id, status, price, created_at
        FROM calls
        ORDER BY created_at DESC
        LIMIT 200
    """)).fetchall()

df = pd.DataFrame(rows, columns=["id","call_id","status","price","created_at"])
st.dataframe(df, use_container_width=True)

# simple filters
status = st.multiselect("Status filter", options=df["status"].unique().tolist())
if status:
    st.dataframe(df[df["status"].isin(status)], use_container_width=True)
