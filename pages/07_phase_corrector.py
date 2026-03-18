# pages/07_phase_corrector.py
import streamlit as st
import pandas as pd
import io
from src.data_processor import apply_tpm_phase_correction

st.set_page_config(page_title="Phase Corrector", layout="wide")
st.title("🔧 TPM Phase Corrector (Emergency Fix)")

st.markdown("""
### Overview
This corrects phase discrepancies arising from the definition of the coordinate system used in TPM calculations.
The following correction formula is applied to data rows where `category == 'IR'` to calculate a new time (time).
- `time = time + (lon_a - 90) / 360 * (period / 86400)`
""")

uploaded_file = st.file_uploader("Upload Unified (or TPM-only) Parquet File", type="parquet")

if uploaded_file:
    df = pd.read_parquet(uploaded_file)
    
    st.subheader("Before Correction")
    st.dataframe(df.head())

    if st.button("Apply Phase Correction"):
        with st.spinner("Calculating..."):
            df_corrected = apply_tpm_phase_correction(df)

        st.success("Correction complete!")

        st.subheader("After Correction (Preview)")
        st.dataframe(df_corrected.head())

        # Prepare for download
        out_bio = io.BytesIO()
        df_corrected.to_parquet(out_bio, index=False, compression='zstd')
        
        st.download_button(
            label="Download Corrected Parquet",
            data=out_bio.getvalue(),
            file_name="corrected_tpm_data.parquet",
            mime="application/octet-stream"
        )
