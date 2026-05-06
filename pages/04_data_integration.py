# pages/04_data_integration.py
import streamlit as st
import pandas as pd
import io
import os
from src.data_processor import integrate_tpm_and_hapke

st.set_page_config(page_title="Data Integration", layout="wide")
st.title("📦 Hapke & TPM Data Integration")

st.markdown("""
### 使い方
1. **TPMデータ**: 熱モデルの計算結果（Parquet形式）をアップロードします。
2. **Hapkeデータ**: 可視光の計算結果（CSVまたはParquet形式）をアップロードします。
   - **一括ファイル (Batch)**: ファイル名に `batch` が含まれている場合、内部の `lon_a`, `lat_b`, `type` 列を使用して自動分類します。
   - **個別ファイル**: ファイル名に `lonXX_latYY_S` 等の形式が含まれている必要があります。
""")

# --- 1. TPMデータのアップロード ---
st.header("1. TPM (Infrared) Data")
tpm_file = st.file_uploader("TPM Parquetをアップロード", type="parquet")

# --- 2. Hapkeデータのアップロード (一括・個別両対応) ---
st.header("2. Hapke (Visible) Data")
hapke_files = st.file_uploader(
    "Hapkeライトカーブファイルをアップロード (複数可)", 
    type=["csv", "parquet"], 
    accept_multiple_files=True
)

if tpm_file and hapke_files:
    if st.button("統合処理を開始 (Unified Long Format)"):
        # TPMの読み込み
        df_tpm = pd.read_parquet(tpm_file)
        
        dict_hapke = {}
        for f in hapke_files:
            name = f.name
            try:
                # 拡張子に応じた読み込み
                if name.endswith(".parquet"):
                    df_h = pd.read_parquet(f)
                else:
                    df_h = pd.read_csv(f)
                
                clean_name = name.lower()
                
                # --- 一括ファイル(Batch)の場合の処理 ---
                if "batch" in clean_name:
                    required_cols = ['lon_a', 'lat_b', 'type']
                    if all(col in df_h.columns for col in required_cols):
                        # 内部のパラメータごとにグループ化して辞書に格納
                        for (l, b, t), group in df_h.groupby(['lon_a', 'lat_b', 'type']):
                            # 後のマッチングのためにキーを (float, float, str) に統一
                            dict_hapke[(float(l), float(b), str(t))] = group
                        st.info(f"一括ファイルを解析しました: {name}")
                    else:
                        st.error(f"一括ファイルに必要な列 {required_cols} が不足しています: {name}")
                        continue
                
                # --- 個別ファイルの場合の処理 ---
                else:
                    # 拡張子を除去
                    p_name = clean_name.replace(".csv", "").replace(".parquet", "")
                    # 経度と緯度を抽出
                    lon = float(p_name.split('lon')[1].split('_')[0])
                    lat = float(p_name.split('lat')[1].split('_')[0])
                    
                    # タイプの判定
                    if 'stype' in p_name or '_s' in p_name or p_name.endswith('_s'):
                        v_type = 'S'
                    elif 'ctype' in p_name or '_c' in p_name or p_name.endswith('_c'):
                        v_type = 'C'
                    else:
                        st.warning(f"タイプ(S/C)を特定できませんでした。スキップします: {name}")
                        continue
                    
                    dict_hapke[(lon, lat, v_type)] = df_h
                
            except Exception as e:
                st.error(f"解析エラーによりファイルをスキップしました: {name} ({e})")

        if not dict_hapke:
            st.error("有効なHapkeデータが見つかりませんでした。")
        else:
            with st.spinner("統合中..."):
                # 統合処理の実行
                df_unified = integrate_tpm_and_hapke(df_tpm, dict_hapke)

            st.success(f"統合完了！ 計 {len(df_unified)} 行のデータが生成されました。")
            
            # プレビュー
            st.subheader("Preview: Unified Data")
            st.dataframe(df_unified.head(10))
            
            # ダウンロードボタン
            out_bio = io.BytesIO()
            df_unified.to_parquet(out_bio, index=False)
            st.download_button(
                label="📥 統合データをParquet形式で保存",
                data=out_bio.getvalue(),
                file_name="unified_asteroid_data.parquet",
                mime="application/octet-stream"
            )

else:
    st.info("TPMファイルと、対応するHapkeファイルをアップロードしてください。")
