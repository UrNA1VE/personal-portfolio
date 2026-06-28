import streamlit as st

from utils.database import load_dashboard_data


st.set_page_config(page_title="Data Quality", layout="wide")
tables, source_label = load_dashboard_data()
quality = tables["quality"]

st.title("Data Quality")
st.caption(f"Source: {source_label}")
issue_total = int(quality["issue_count"].sum())
st.metric("Total warnings/errors", issue_total)

if issue_total:
    st.warning("One or more checks require review.")
else:
    st.success("All included quality checks passed.")

st.dataframe(quality, use_container_width=True, hide_index=True)
