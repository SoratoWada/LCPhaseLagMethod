# pages/04_data_integration.py
import streamlit as st
import pandas as pd
import io
from src.data_processor import integrate_tpm_and_hapke

st.title("📦 Hapke & TPM Data Integration")

st.markdown("""
### 使い方
1. TPMのParquetファイルをアップロードします。
2. 対応するHapkeモデルのCSVファイルを複数アップロードします。
   - ファイル名に `lon`, `lat`, `Stype`/`Ctype` が含まれている必要があります。
""")

tpm_file = st.file_uploader("TPM Parquet", type="parquet")
hapke_files = st.file_uploader("Hapke CSVs", type="csv", accept_multiple_files=True)

if tpm_file and hapke_files:
    if st.button("統合プロセス開始"):
        df_tpm = pd.read_parquet(tpm_file)
        
        # CSVファイルを解析して辞書に格納
        dict_hapke = {}
        for f in hapke_files:
            # 簡易的なファイル名解析ロジック（実際の命名規則に合わせて調整してください）
            name = f.name
            try:
                lon = int(name.split('lon')[1].split('_')[0])
                lat = int(name.split('lat')[1].split('_')[0])
                v_type = 'S' if 'Stype' in name else 'C'
                dict_hapke[(lon, lat, v_type)] = pd.read_csv(f)
            except Exception as e:
                st.warning(f"スキップ: {name} (解析失敗)")

        with st.spinner("統合中..."):
            df_unified = integrate_tpm_and_hapke(df_tpm, dict_hapke)
            
        st.success("統合完了！")
        st.write(df_unified.head())
        
        # ダウンロードボタン
        out_bio = io.BytesIO()
        df_unified.to_parquet(out_bio, index=False, compression='zstd')
        st.download_button(
            "統合済みParquetをダウンロード",
            data=out_bio.getvalue(),
            file_name="unified_asteroid_data.parquet"
        )
