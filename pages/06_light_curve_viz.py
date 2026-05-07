# pages/06_light_curve_viz.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Page configuration
st.set_page_config(page_title="Light Curve Visualizer", layout="wide")
st.title("📉 Interactive Light Curve Visualization")

st.markdown("""
This page allows you to overlay multiple wavelengths and Gamma values to analyze Phase Lags.
""")

# 1. File Uploader in Sidebar
uploaded_file = st.sidebar.file_uploader("Upload Integrated Parquet File", type="parquet")

if uploaded_file:
    df = pd.read_parquet(uploaded_file)
    
    # 共通フィルター
    st.sidebar.header("Filter")
    sel_lon = st.sidebar.selectbox("Lon", sorted(df['lon_a'].unique()))
    sel_lat = st.sidebar.selectbox("Lat", sorted(df['lat_b'].unique()))
    sel_p = st.sidebar.selectbox("Period", sorted(df['period'].unique()))

    # 基本の絞り込み
    mask = (df['lon_a'] == sel_lon) & (df['lat_b'] == sel_lat) & (df['period'] == sel_p)
    target_df = df[mask]

    # 波長選択 (wavelength列から取得)
    st.subheader("Wavelength Selection")
    ir_waves = sorted(target_df[target_df['category'] == 'IR']['wavelength'].unique())
    selected_waves = st.multiselect("Select IR Wavelengths (μm)", options=ir_waves, default=ir_waves[:2])

    # Gamma選択 (gamma列から取得)
    gamma_col = 'gamma' if 'gamma' in target_df.columns else 'gamma_d'
    gammas = sorted(target_df[target_df['category'] == 'IR'][gamma_col].unique())
    selected_gammas = st.multiselect("Select Gamma", options=gammas, default=gammas[:1])

    # グラフ描画
    fig, ax1 = plt.subplots(figsize=(10, 5))
    
    # 1. IRのプロット
    for g in selected_gammas:
        for w in selected_waves:
            plot_data = target_df[(target_df['category'] == 'IR') & 
                                  (target_df['wavelength'] == w) & 
                                  (target_df[gamma_col] == g)].sort_values('time')
            ax1.plot(plot_data['time'], plot_data['flux'], label=f"IR {w}μm (G={g})")

    # 2. 可視光のプロット (第2軸)
    show_vis = st.checkbox("Show Visible Reference", value=True)
    if show_vis:
        v_type = st.radio("Type", ["S", "C"], horizontal=True)
        vis_plot = target_df[(target_df['category'] == 'Visible') & 
                             (target_df['type'] == v_type)].sort_values('time')
        
        if not vis_plot.empty:
            ax2 = ax1.twinx()
            ax2.plot(vis_plot['time'], vis_plot['flux'], color='black', linestyle='--', label=f"Vis ({v_type})")
            ax2.set_ylabel("Visible Flux")

    ax1.set_xbound(lower=0, upper=0.00115741)  # 0 to 1000 seconds in days
    ax1.set_xlabel("Time")
    ax1.set_ylabel("IR Flux")
    ax1.legend(loc='upper left')
    st.pyplot(fig)
