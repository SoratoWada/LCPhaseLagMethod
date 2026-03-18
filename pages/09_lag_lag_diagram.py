# pages/09_lag_lag_diagram.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.lines import Line2D

st.set_page_config(page_title="Lag-Lag Diagram", layout="wide")
st.title("🎨 Advanced Lag-Lag Diagram Generator")

# --- 1. データ読み込み ---
st.sidebar.header("1. Data Input")
uploaded_file = st.sidebar.file_uploader("metrics CSV (from Page 08) をアップロード", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # --- 2. Global Constants ---
    st.sidebar.header("2. Global Constants")
    
    def get_index(options, target):
        try: return options.index(target)
        except ValueError: return 0

    periods = sorted(df['period'].unique())
    common_p_str = st.sidebar.selectbox("Period", periods, index=get_index(periods, "100s"))
    period_val = float(common_p_str.replace('s', ''))
    
    alphas = sorted(df['alpha'].unique()) if 'alpha' in df.columns else [90]
    common_alpha = st.sidebar.selectbox("Phase Angle (alpha)", alphas, index=get_index(alphas, 90))
    
    axis_ratios = sorted(df['axis_ratio'].unique()) if 'axis_ratio' in df.columns else [1.3]
    common_ar = st.sidebar.selectbox("Axis Ratio (Shape)", axis_ratios, index=get_index(axis_ratios, 1.3))

    # --- 3. 表示範囲の設定 ---
    st.sidebar.header("3. Axis Range Settings")
    def axis_range_control(label, min_val, max_val, default_range):
        st.sidebar.write(f"**{label}**")
        val_range = st.sidebar.slider(f"{label} Slider", min_val, max_val, default_range, step=1, label_visibility="collapsed")
        c1, c2 = st.sidebar.columns(2)
        low = c1.number_input("Min", value=float(val_range[0]), key=f"{label}_low")
        high = c2.number_input("Max", value=float(val_range[1]), key=f"{label}_high")
        return low, high

    x_min, x_max = axis_range_control("X-axis [deg]", -180, 180, (-90, 90))
    y_min, y_max = axis_range_control("Y-axis [deg]", -180, 180, (-20, 20))

    # --- 4. Quality Control (Histogram 追加) ---
    st.sidebar.header("4. Quality Control")
    
    # 現在の Global Constants で絞り込んだベースデータ（閾値適用前）
    mask_base = (df['period'] == common_p_str)
    if 'alpha' in df.columns: mask_base &= (df['alpha'] == common_alpha)
    if 'axis_ratio' in df.columns: mask_base &= (df['axis_ratio'] == common_ar)
    base_df = df[mask_base]

    if not base_df.empty:
        st.sidebar.write("**Amplitude Ratio Distribution**")
        fig_h, ax_h = plt.subplots(figsize=(4, 2.5))
        ax_h.hist(base_df['amp_ratio'].dropna(), bins=30, color='teal', alpha=0.7, edgecolor='white')
        ax_h.set_xlabel("Amp Ratio", fontsize=8)
        ax_h.set_ylabel("Count", fontsize=8)
        # ユーザー要望に基づき、表示範囲を 0.2~0.3 程度に制限（またはデータ最大値）
        current_max = base_df['amp_ratio'].max()
        ax_h.set_xlim(0, max(0.2, current_max * 1.1))
        ax_h.tick_params(labelsize=7)
        st.sidebar.pyplot(fig_h)

    st.sidebar.write("**Min Amplitude Ratio Threshold**")
    st.sidebar.slider("Threshold Slider", 0.0, 1.0, 0.0, step=0.01, key="amp_min_slider", label_visibility="collapsed")
    st.sidebar.number_input("Value Input", min_value=0.0, max_value=1.0, value=st.session_state.amp_min_slider, step=0.01, key="amp_min_number")
    amp_min = st.session_state.amp_min_number

    # --- 5. 位相差（Lag）の設定 ---
    st.subheader("Lag Calculation Settings")
    def target_selector(label, key_suffix, def_cat, def_val):
        c_cat, c_val = st.columns([1, 1])
        with c_cat:
            cat_opts = ["IR", "Visible"]
            cat = st.selectbox(f"{label}: Category", cat_opts, index=get_index(cat_opts, def_cat), key=f"cat_{key_suffix}")
        with c_val:
            if cat == "IR":
                waves = sorted(df[df['category'] == 'IR']['wavelength'].unique())
                val = st.selectbox(f"{label}: Wavelength (μm)", waves, index=get_index(waves, def_val), key=f"wave_{key_suffix}")
            else:
                v_types = sorted(df[df['category'] == 'Visible']['type'].dropna().unique())
                val = st.selectbox(f"{label}: Type", v_types, index=get_index(v_types, def_val), key=f"type_{key_suffix}")
        return {"cat": cat, "val": val}

    st.write("---")
    col_x, col_y = st.columns(2)
    with col_x:
        st.markdown("### X-axis Lag (Δφ1)")
        t_x_a = target_selector("Minuend (A)", "xa", "IR", 7.0)
        t_x_b = target_selector("Subtrahend (B)", "xb", "Visible", "C")
    with col_y:
        st.markdown("### Y-axis Lag (Δφ2)")
        t_y_a = target_selector("Minuend (C)", "ya", "IR", 20.0)
        t_y_b = target_selector("Subtrahend (D)", "yb", "IR", 7.0)

    use_corr = st.checkbox("X軸に Longitude 補正を適用する", value=True)

    # --- 6. 描画実行 ---
    if st.button("Generate Diagram"):
        # 閾値を適用
        target_df = base_df[base_df['amp_ratio'] >= amp_min]
        
        lons = sorted(target_df['lon_a'].unique())
        lats = sorted(target_df['lat_b'].unique())
        gammas = sorted(target_df['gamma'].dropna().unique())
        
        plot_results = []
        for g in gammas:
            for lat in lats:
                for lon in lons:
                    def get_phase_val(target, g_val, l_val, lo_val):
                        m = (target_df['lon_a'] == lo_val) & (target_df['lat_b'] == l_val)
                        if target['cat'] == "Visible":
                            m &= (target_df['category'] == "Visible") & (target_df['type'] == target['val'])
                        else:
                            m &= (target_df['category'] == "IR") & (target_df['wavelength'] == target['val']) & (target_df['gamma'] == g_val)
                        res = target_df[m]
                        return res['peak_phase'].values[0] if not res.empty else None

                    p_xa = get_phase_val(t_x_a, g, lat, lon)
                    p_xb = get_phase_val(t_x_b, g, lat, lon)
                    p_ya = get_phase_val(t_y_a, g, lat, lon)
                    p_yb = get_phase_val(t_y_b, g, lat, lon)

                    if all(v is not None for v in [p_xa, p_xb, p_ya, p_yb]):
                        lx = (p_xa - p_xb) + (lon / 360.0 + 0.25 if use_corr else 0)
                        ly = p_ya - p_yb
                        # 循環処理
                        lx = (lx + 0.25) % 0.5 - 0.25
                        ly = (ly + 0.25) % 0.5 - 0.25
                        plot_results.append({'gamma': g, 'lat': lat, 'x_deg': lx * 360, 'y_deg': ly * 360})

        if not plot_results:
            st.error("No data points found matching criteria.")
        else:
            plot_df = pd.DataFrame(plot_results)
            colors_map = {'10': '#17becf', '30': '#4fbdb1', '100': '#bcbd22', '300': '#d29b77', '1000': '#e377c2'}
            
            fig, ax = plt.subplots(figsize=(12, 9))
            for _, row in plot_df.iterrows():
                g_key = str(int(row['gamma']))
                color = colors_map.get(g_key, 'black')
                lat = row['lat']
                m = '^' if lat > 0 else ('v' if lat < 0 else '+')
                fc = 'None' if abs(lat) == 30 else color
                lw = 1.5 if abs(lat) == 30 else 0.5
                ax.scatter(row['x_deg'], row['y_deg'], color=color, marker=m, facecolor=fc, s=200, linewidths=lw, alpha=0.8)

            ax.set_xlim(x_min, x_max)
            ax.set_ylim(y_min, y_max)
            
            # 動的なラベルとタイトル
            ax.set_xlabel(f'Phase Lag: {t_x_a["val"]} - {t_x_b["val"]} [deg]', fontsize=12, fontweight='bold')
            ax.set_ylabel(f'Phase Lag: {t_y_a["val"]} - {t_y_b["val"]} [deg]', fontsize=12, fontweight='bold')
            ax.set_title(f'Lag-Lag Diagram\n(P={common_p_str}, α={common_alpha}°, AR={common_ar}, Min Amp Ratio={amp_min})', fontsize=15, pad=20)
            
            ax.grid(True, linestyle=':', alpha=0.6)
            ax.axhline(0, color='black', lw=1, alpha=0.3)
            ax.axvline(0, color='black', lw=1, alpha=0.3)
            
            # 第2軸（時間軸）
            ax.secondary_xaxis('top', functions=(lambda x: x/360*period_val, lambda x: x/period_val*360)).set_xlabel('Time Lag [s]')
            ax.secondary_yaxis('right', functions=(lambda x: x/360*period_val, lambda x: x/period_val*360)).set_ylabel('Time Lag [s]')

            # 凡例
            gamma_h = [Line2D([0], [0], marker='s', color='w', label=f'Γ={g}', markerfacecolor=colors_map.get(g, 'black'), markersize=10) for g in sorted(colors_map.keys(), key=int)]
            lat_h = [
                Line2D([0], [0], marker='^', color='w', label='Lat > 0', markerfacecolor='gray', markersize=10),
                Line2D([0], [0], marker='+', color='gray', label='Lat = 0', markersize=10, markeredgewidth=2),
                Line2D([0], [0], marker='v', color='w', label='Lat < 0', markerfacecolor='gray', markersize=10),
                Line2D([0], [0], marker='^', color='w', label='|Lat|=30 (Open)', markerfacecolor='None', markeredgecolor='gray', markersize=10)
            ]
            ax.add_artist(ax.legend(handles=gamma_h, title="Thermal Inertia", loc='upper left', bbox_to_anchor=(1.15, 1)))
            ax.legend(handles=lat_h, title="Latitude", loc='upper left', bbox_to_anchor=(1.15, 0.6))

            plt.subplots_adjust(right=0.8)
            st.pyplot(fig)
