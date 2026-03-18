# pages/08_lag_analysis.py
import streamlit as st
import pandas as pd
import io
from src.data_processor import extract_lc_metrics

st.set_page_config(page_title="Lag-Lag Analysis", layout="wide")
st.title("📏 Phase & Amplitude Ratio Extraction")

uploaded_file = st.sidebar.file_uploader("Upload the consolidated Parquet file", type="parquet")

if uploaded_file:
    df = pd.read_parquet(uploaded_file)
    
    st.sidebar.header("Calculation Settings")
    sigma_val = st.sidebar.slider("Smoothing Sigma (Ratio of data points)", 0.01, 0.20, 0.05)

    # Select target for analysis
    st.subheader("Selection")
    col1, col2 = st.columns(2)
    with col1:
        waves = sorted(df['wavelength'].unique())
        sel_waves = st.multiselect("Select target wavelengths", options=waves, default=waves)
    with col2:
        # gamma column name is automatically determined
        g_col = 'gamma' if 'gamma' in df.columns else 'gamma_d'
        gammas = sorted(df[g_col].dropna().unique())
        sel_gammas = st.multiselect("Select target Gammas", options=gammas, default=gammas)

    if st.button("Extract Metrics"):
        # Filtering
        mask = (df['wavelength'].isin(sel_waves)) | (df['category'] == 'Visible')
        if g_col in df.columns:
            mask = mask & ((df[g_col].isin(sel_gammas)) | (df['category'] == 'Visible'))
        
        with st.spinner("Calculating peak phases and amplitudes..."):
            res_df = extract_lc_metrics(df[mask], sigma_pct=sigma_val)
        
        st.success("Extraction Complete!")

        # Display results
        st.subheader("Summary Table")
        # Show only IR data (for Lag analysis)
        display_df = res_df[res_df['category'] == 'IR'].sort_values(['lon_a', 'wavelength'])
        st.dataframe(display_df, use_container_width=True)

        # Download
        csv = display_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Download Results (CSV)",
            csv,
            "lc_metrics_for_lag_diagram.csv",
            "text/csv"
        )

        # Quick Preview: Lag-Lag Plot
        if 'amp_ratio' in display_df.columns:
            st.subheader("Quick Preview: Lag-Lag Plot")
            st.scatter_chart(data=display_df, x='peak_phase', y='amp_ratio', color='wavelength')

else:
    st.info("Please upload a Parquet file.")
