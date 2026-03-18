# pages/04_data_integration.py
import streamlit as st
import pandas as pd
import io
from src.data_processor import integrate_tpm_and_hapke

st.title("📦 Hapke & TPM Data Integration")

st.markdown("""
### Instructions
1. Upload file TPM Parquet
2. Upload multiple corresponding Hapke model CSV files.
   - The file name must contain `lon`, `lat`, and `Stype`/`Ctype`.
""")

tpm_file = st.file_uploader("TPM Parquet", type="parquet")
hapke_files = st.file_uploader("Hapke CSVs", type="csv", accept_multiple_files=True)

if tpm_file and hapke_files:
    if st.button("Start Integration Process"):
        df_tpm = pd.read_parquet(tpm_file)
        
        # Parse the CSV file and store the data in a dictionary
        dict_hapke = {}
        for f in hapke_files:
            # Simple file name parsing logic (please adjust this to suit your actual naming conventions)
            name = f.name
            try:
                lon = int(name.split('lon')[1].split('_')[0])
                lat = int(name.split('lat')[1].split('_')[0])
                v_type = 'S' if 'Stype' in name else 'C'
                dict_hapke[(lon, lat, v_type)] = pd.read_csv(f)
            except Exception as e:
                st.warning(f"Skip: {name} (Parsing failed)")

        with st.spinner("Integrating..."):
            df_unified = integrate_tpm_and_hapke(df_tpm, dict_hapke)

        st.success("Integration complete!")
        st.write(df_unified.head())

        st.subheader("Data Summary")
        st.write(df_unified.describe()) # Statistics on numerical data (mean, maximum, minimum, etc.)

        # Check for missing values (NaN)
        if df_unified[['vis_flux_S', 'vis_flux_C']].isnull().any().any():
            st.warning("Warning: Some rows have missing visible flux data.")
        else:
            st.success("All rows successfully integrated with visible flux!")

        # Show the download button
        out_bio = io.BytesIO()
        df_unified.to_parquet(out_bio, index=False, compression='zstd')
        st.download_button(
            "Download Unified Parquet",
            data=out_bio.getvalue(),
            file_name="unified_asteroid_data.parquet"
        )
