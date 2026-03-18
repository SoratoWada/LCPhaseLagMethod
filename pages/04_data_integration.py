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
    if st.button("Start Unified Integration"):
        df_tpm = pd.read_parquet(tpm_file)
        
        dict_hapke = {}
        for f in hapke_files:
            name = f.name
            try:
                # ファイル名解析: vis_lonXX_latYY_Stype.csv
                lon = int(name.split('lon')[1].split('_')[0])
                lat = int(name.split('lat')[1].split('_')[0])
                v_type = 'S' if 'Stype' in name else 'C'
                dict_hapke[(lon, lat, v_type)] = pd.read_csv(f)
            except:
                st.warning(f"Skip: {name}")

        with st.spinner("Integrating into Unified Long Format..."):
            df_unified = integrate_tpm_and_hapke(df_tpm, dict_hapke)

        st.success("Integration complete! (Long Format)")
        st.dataframe(df_unified.head())
        
        # 統計情報とカラム構成の確認
        st.subheader("Unified Data Structure")
        st.write(f"Total Rows: {len(df_unified)}")
        st.write("Columns:", df_unified.columns.tolist())
        
        out_bio = io.BytesIO()
        df_unified.to_parquet(out_bio, index=False, compression='zstd')
        st.download_button("Download Unified Parquet", out_bio.getvalue(), "unified_data_long.parquet")
