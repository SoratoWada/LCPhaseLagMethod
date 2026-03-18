# app.py
import streamlit as st

st.set_page_config(page_title="Apollo TPM Toolset", layout="wide")

st.title("🪐 Apollo TPM Analysis Toolset")
st.markdown("""
This tool assists in automating and analyzing thermal model (TPM) calculations for asteroids.
Please select a feature from the sidebar on the left.

- **Job Generator**: Generate execution scripts for the Apollo server
- **EPH/OBS Generator**: Generate input data with periodic scaling
- **Data Integration**: Integrate infrared and visible light data (under development)
- **Phase Corrector**: Emergency tool for fixing TPM phase errors (New)
""")
