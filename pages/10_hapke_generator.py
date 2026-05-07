# pages/10_hapke_generator.py
import streamlit as st
import pandas as pd
import numpy as np
import io
import os
import matplotlib.pyplot as plt
from src.data_processor import calculate_hapke_lc_core

st.set_page_config(page_title="Hapke LC Batch Generator", layout="wide")

# フォルダパスの設定
SHAPE_DIR = "data/shapes"
os.makedirs(SHAPE_DIR, exist_ok=True)

st.title("☀️ Hapke Light Curve Batch Generator")
st.markdown("""
自転軸（スピン極）を網羅的に変化させ、全84パターンのライトカーブを一括生成します。
計算結果は1つのParquetファイルに統合され、Page 04以降の解析パイプラインで使用可能です。
""")

# --- 1. 形状モデルの選択 ---
st.sidebar.header("📂 1. Shape Model")
def get_file_list(directory):
    return [f for f in os.listdir(directory) if not f.startswith(".")]

shape_mode = st.sidebar.radio("Source", ["Upload", "Select from folder"])
shape_file = None

if shape_mode == "Upload":
    shape_file = st.sidebar.file_uploader("Upload OBJ", type=["txt", "obj"])
else:
    shape_files = get_file_list(SHAPE_DIR)
    selected_shape = st.sidebar.selectbox("Select File", shape_files)
    if selected_shape:
        shape_file = open(os.path.join(SHAPE_DIR, selected_shape), "rb")

# --- 2. 共通時間・幾何設定 ---
st.sidebar.header("🕒 2. Common Settings")
period_s = st.sidebar.number_input("Rotation Period [s]", value=100.0)
steps_per_rot = st.sidebar.number_input("Steps per Rotation", value=1000, help="バッチ処理のため、まずは少なめ（500等）を推奨")
alpha_deg = st.sidebar.slider("Phase Angle (α) [deg]", 0.0, 180.0, 90.0)

# 太陽と観測者の基本ベクトル (慣性系)
sun_vec = [1.0, 0.0, 0.0]
obs_vec = [np.cos(np.deg2rad(alpha_deg)), np.sin(np.deg2rad(alpha_deg)), 0.0]

# --- 3. 物理パラメータ (Type別) ---
st.sidebar.header("🧪 3. Physical Parameters")
ssa = st.sidebar.number_input("Single Scattering Albedo (w)", 0.0, 1.0, 0.23)
poros = st.sidebar.number_input("Porosity", 0.0, 1.0, 0.1)
p_b = st.sidebar.number_input("Phase parameter b", 0.0, 1.0, 0.3)
p_c = st.sidebar.number_input("Phase parameter c", 0.0, 1.0, 0.5)

# --- 4. メタデータ ---
st.sidebar.header("📊 4. Metadata")
m_type = st.sidebar.selectbox("Surface Type Label", ["S", "C", "M"])
axis_ratio = st.sidebar.number_input("Shape Axis Ratio", value=1.3)

# バッチ計算の定義
lons = [-150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150, 180]
lats = [-90, -60, -30, 0, 30, 60, 90]

if shape_file:
    # OBJパース (前回と同様)
    content = shape_file.read().decode("utf-8")
    if hasattr(shape_file, 'seek'): shape_file.seek(0)
    vertices, faces = [], []
    for line in content.splitlines():
        parts = line.split()
        if not parts: continue
        if parts[0] == 'v': vertices.append([float(x) for x in parts[1:4]])
        elif parts[0] == 'f': faces.append([int(x.split('/')[0])-1 for x in parts[1:4]])
    v, f = np.array(vertices), np.array(faces)
    
    # 面情報計算
    v1, v2 = v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]
    cp = np.cross(v1, v2)
    areas = np.linalg.norm(cp, axis=1) / 2.0
    normals = cp / (2.0 * areas[:, np.newaxis])

    if st.button(f"Generate All {len(lons)*len(lats)} Patterns"):
        all_results = []
        total_iters = len(lons) * len(lats)
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 2回転分の時間を生成
        total_steps = int(steps_per_rot * 2)
        times_s = np.linspace(0, 2 * period_s, total_steps)
        
        # エフェメリス (全パターン共通の慣性系位置)
        eph_df = pd.DataFrame({
            'time': times_s,
            'sun_x': [sun_vec[0]] * total_steps, 'sun_y': [sun_vec[1]] * total_steps, 'sun_z': [sun_vec[2]] * total_steps,
            'obs_x': [obs_vec[0]] * total_steps, 'obs_y': [obs_vec[1]] * total_steps, 'obs_z': [obs_vec[2]] * total_steps
        })

        count = 0
        for lat in lats:
            for lon in lons:
                count += 1
                status_text.text(f"Processing pattern {count}/{total_iters}: Lon={lon}, Lat={lat}")
                
                # スピンベクトルの計算
                lam_rad, bet_rad = np.deg2rad(lon), np.deg2rad(lat)
                sx = np.cos(bet_rad) * np.cos(lam_rad)
                sy = np.cos(bet_rad) * np.sin(lam_rad)
                sz = np.sin(bet_rad)
                
                params = {
                    'spin_axis': [sx, sy, sz], 'period_hours': period_s / 3600.0,
                    'initial_angle_deg': 0.0, 'ssa': ssa, 'porosity': poros,
                    'phase_b': p_b, 'phase_c': p_c
                }
                
                # 計算実行
                flux_values = calculate_hapke_lc_core(v, f, normals, areas, eph_df, params)
                
                # チャンクの作成
                chunk = pd.DataFrame({
                    'time': times_s / 86400.0, # JD単位
                    'flux': flux_values,
                    'wavelength': 0.55,
                    'lon_a': lon, # ここにスピン極の経度を入れる
                    'lat_b': lat, # ここにスピン極の緯度を入れる
                    'period': f"{period_s}s",
                    'gamma': np.nan,
                    'category': 'Visible',
                    'type': m_type,
                    'model': 'Hapke',
                    'alpha': alpha_deg,
                    'axis_ratio': axis_ratio
                })
                all_results.append(chunk)
                progress_bar.progress(count / total_iters)

        # 統合
        final_df = pd.concat(all_results, ignore_index=True)
        st.success(f"Successfully generated {total_iters} light curves!")
        
        # 保存とダウンロード
        out_bio = io.BytesIO()
        final_df.to_parquet(out_bio, index=False)
        st.download_button(
            label="📥 Download Integrated Parquet",
            data=out_bio.getvalue(),
            file_name=f"hapke_batch_{m_type}_alpha{int(alpha_deg)}.parquet",
            mime="application/octet-stream"
        )
