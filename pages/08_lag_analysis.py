# pages/08_lag_analysis.py
import streamlit as st
import pandas as pd
import io
from src.data_processor import extract_lc_metrics

st.set_page_config(page_title="Lag-Lag Analysis", layout="wide")
st.title("📏 Phase & Amplitude Ratio Extraction")

uploaded_file = st.sidebar.file_uploader("統合済みParquetをアップロード", type="parquet")

if uploaded_file:
    df = pd.read_parquet(uploaded_file)
    
    st.sidebar.header("Calculation Settings")
    sigma_val = st.sidebar.slider("Smoothing Sigma (Ratio)", 0.01, 0.20, 0.05)
    
    # Selection of analysis subjects
    st.subheader("Analysis Target Selection")
    col1, col2 = st.columns(2)
    
    with col1:
        waves = sorted(df['wavelength'].unique())
        sel_waves = st.multiselect("Select Target Wavelengths", options=waves, default=waves)

    with col2:
        g_col = 'gamma' if 'gamma' in df.columns else 'gamma_d'
        if g_col in df.columns:
            gammas = sorted(df[g_col].dropna().unique())
            sel_gammas = st.multiselect("Select Target Gamma", options=gammas, default=gammas)
        else:
            sel_gammas = []

    if st.button("Extract Metrics"):
        # Filtering
        mask = (df['wavelength'].isin(sel_waves)) | (df['category'] == 'Visible')
        if sel_gammas:
            mask = mask & ((df[g_col].isin(sel_gammas)) | (df['category'] == 'Visible'))
        
        with st.spinner("Calculating metrics with Gaussian smoothing..."):
            res_df = extract_lc_metrics(df[mask], sigma_pct=sigma_val)
        
        st.success("Extraction Complete!")

        # Extract and display only IR data (for Lag analysis)
        display_df = res_df[res_df['category'] == 'IR'].sort_values(['lon_a', 'wavelength'])
        
        st.subheader("Summary Table")
        st.markdown("""
        - **peak_phase**: The phase at which the smoothed light curve reaches its maximum (0.0 - 1.0)
        - **amp_ratio**: (max - min) / (max + min)
        """)
        st.dataframe(display_df, use_container_width=True)

        # Download button
        csv = display_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Download Metrics CSV",
            csv,
            "lc_phase_amp_metrics.csv",
            "text/csv"
        )

        # Quick Lag-Lag Plot
        if not display_df.empty:
            st.subheader("Quick Preview: Phase vs Amplitude Ratio")
            st.scatter_chart(
                data=display_df, 
                x='peak_phase', 
                y='amp_ratio', 
                color='wavelength'
            )
else:
    st.info("Please upload a Parquet file.")
