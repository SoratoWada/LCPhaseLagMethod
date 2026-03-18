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
    
    # 解析対象の選択
    st.subheader("Analysis Target Selection")
    col1, col2 = st.columns(2)
    
    with col1:
        # 波長選択（IRのみ対象）
        ir_waves = sorted(df[df['category'] == 'IR']['wavelength'].unique())
        sel_waves = st.multiselect("対象 IR 波長を選択", options=ir_waves, default=ir_waves)
        
    with col2:
        # Gamma選択（IRのみ対象）
        g_col = 'gamma' if 'gamma' in df.columns else 'gamma_d'
        ir_gammas = sorted(df[df['category'] == 'IR'][g_col].dropna().unique())
        sel_gammas = st.multiselect("対象 Gamma を選択", options=ir_gammas, default=ir_gammas)

    if st.button("Extract Metrics (All Categories)"):
        # フィルタリング: 選択されたIRデータ、または全ての可視光データ
        mask = ((df['category'] == 'IR') & (df['wavelength'].isin(sel_waves)) & (df[g_col].isin(sel_gammas))) | \
               (df['category'] != 'IR')
        
        with st.spinner("Calculating metrics for IR and Visible data..."):
            res_df = extract_lc_metrics(df[mask], sigma_pct=sigma_val)
        
        st.success("Extraction Complete!")
        
        # 結果の表示（IRもVisibleも一括表示）
        st.subheader("Summary Table (IR & Visible)")
        display_df = res_df.sort_values(['category', 'lon_a', 'wavelength'], ascending=[False, True, True])
        st.dataframe(display_df, use_container_width=True)
        
        # ダウンロード（すべての結果を含む）
        csv = display_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Download All Metrics (CSV)",
            csv,
            "lc_all_metrics.csv",
            "text/csv"
        )
        
        # 可視化プレビュー
        if not display_df.empty:
            st.subheader("Quick Preview: Phase vs Amplitude Ratio")
            st.scatter_chart(
                data=display_df, 
                x='peak_phase', 
                y='amp_ratio', 
                color='category' # IRとVisibleで色分け
            )
else:
    st.info("Parquetファイルをアップロードしてください。")
