# pages/11_90deg_corrector.py
import streamlit as st
import pandas as pd
import io
from src.data_processor import apply_90deg_phase_fix

st.set_page_config(page_title="90deg Phase Fixer", layout="wide")
st.title("🚨 90deg Phase Corrector (Emergency)")

st.markdown("""
### Overview
全てのデータにおいて一律で発生している90度の位相ズレを修正します。
`category == 'IR'` のデータに対し、自転周期の1/4の時間を一律で差し引きます。
- 補正式: `time = time - 0.25 * (period / 86400)`
""")

uploaded_file = st.file_uploader("Upload Parquet File for 90deg Fix", type="parquet")

if uploaded_file:
    df = pd.read_parquet(uploaded_file)
    
    st.subheader("Before Correction")
    st.dataframe(df.head())

    if st.button("Apply 90deg Correction"):
        with st.spinner("Applying fix..."):
            df_corrected = apply_90deg_phase_fix(df)

        st.success("90度位相補正（時間減算）が完了しました！")

        st.subheader("After Correction (Preview)")
        st.dataframe(df_corrected.head())

        # ダウンロード準備
        out_bio = io.BytesIO()
        df_corrected.to_parquet(out_bio, index=False, compression='zstd')
        
        st.download_button(
            label="Download Fixed Parquet",
            data=out_bio.getvalue(),
            file_name="90deg_fixed_tpm_data.parquet",
            mime="application/octet-stream"
        )
