# pages/09_lag_lag_diagram.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl

st.set_page_config(page_title="Lag-Lag Diagram", layout="wide")
st.title("🎨 Multi-Longitude Lag-Lag Diagram")

# --- 1. データ読み込み ---
st.sidebar.header("1. Data Input")
uploaded_file = st.sidebar.file_uploader("metrics CSV (from Page 08) をアップロード", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # --- 2. Global Constants (デフォルト値設定) ---
    st.sidebar.header("2. Global Constants")
    
    def get_index(options, target):
        try:
            return options.index(target)
        except ValueError:
            return 0

    periods = sorted(df['period'].unique())
    common_p_str = st.sidebar.selectbox("Period", periods, index=get_index(periods, "100s"))
    period_val = float(common_p_str.replace('s', ''))
    
    alphas = sorted(df['alpha'].unique()) if 'alpha' in df.columns else [90]
    common_alpha = st.sidebar.selectbox("Phase Angle (alpha)", alphas, index=get_index(alphas, 90))
    
    axis_ratios = sorted(df['axis_ratio'].unique()) if 'axis_ratio' in df.columns else [1.3]
    common_ar = st.sidebar.selectbox("Axis Ratio (Shape)", axis_ratios, index=get_index(axis_ratios, 1.3))

    # --- 3. 表示範囲の設定 (スライダー + 数値入力) ---
    st.sidebar.header("3. Axis Range Settings")
    
    def axis_range_control(label, min_val, max_val, default_range):
        st.sidebar.write(f"**{label}**")
        # スライダー
        val_range = st.sidebar.slider(f"{label} Slider", min_val, max_val, default_range, step=1, label_visibility="collapsed")
        # 数値入力
        c1, c2 = st.sidebar.columns(2)
        low = c1.number_input("Min", value=float(val_range[0]), key=f"{label}_low")
        high = c2.number_input("Max", value=float(val_range[1]), key=f"{label}_high")
        return low, high

    x_min, x_max = axis_range_control("X-axis [deg]", -180, 180, (-90, 90))
    y_min, y_max = axis_range_control("Y-axis [deg]", -180, 180, (-20, 20))

    # 4. Quality Control
    st.sidebar.header("4. Quality Control")
    st.sidebar.write("**Min Amplitude Ratio**")
    # スライダー（表示のみのラベル。値はセッションステートで参照）
    st.sidebar.slider("Min Amplitude Ratio Slider", 0.0, 1.0, 0.0, step=0.01, key="amp_min_slider", label_visibility="collapsed")
    # 数値入力（スライダーと併用可能）
    st.sidebar.number_input("Value", min_value=0.0, max_value=1.0, value=0.0, step=0.01, key="amp_min_number")
    # 優先順位：数値入力があればそれを使い、なければスライダー値を使う
    amp_min = st.session_state.get("amp_min_number", st.session_state.get("amp_min_slider", 0.0))

    # --- 5. 位相差（Lag）の設定 (デフォルト値設定) ---
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
        t_x_a = target_selector("Minuend (A)", "xa", "Visible", "C")
        t_x_b = target_selector("Subtrahend (B)", "xb", "IR", 7.0)
    with col_y:
        st.markdown("### Y-axis Lag (Δφ2)")
        t_y_a = target_selector("Minuend (C)", "ya", "IR", 7.0)
        t_y_b = target_selector("Subtrahend (D)", "yb", "IR", 20.0)

    use_corr = st.checkbox("X軸に Longitude 補正を適用する", value=True)

    # --- 6. 描画実行 ---
    if st.button("Generate Diagram"):
        # (計算ロジックは以前のコードを維持)
        mask_base = (df['period'] == common_p_str) & (df['amp_ratio'] >= amp_min)
        if 'alpha' in df.columns: mask_base &= (df['alpha'] == common_alpha)
        if 'axis_ratio' in df.columns: mask_base &= (df['axis_ratio'] == common_ar)
        target_df = df[mask_base]
        
        lons = sorted(target_df['lon_a'].unique())
        lats = sorted(target_df['lat_b'].unique())
        gammas = sorted(target_df['gamma'].dropna().unique())
        
        plot_results = []
        for g in gammas:
            for lat in lats:
                for lon in lons:
                    def get_phase_val(target, g_val, lat_val, lon_val):
                        m = (target_df['lon_a'] == lon_val) & (target_df['lat_b'] == lat_val)
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
                        lx = p_xa - p_xb
                        if use_corr: lx += (lon / 360.0 + 0.25)
                        ly = p_ya - p_yb
                        lx = (lx + 0.25) % 0.5 - 0.25
                        ly = (ly + 0.25) % 0.5 - 0.25
                        plot_results.append({'gamma': g, 'lat': lat, 'x_deg': lx * 360, 'y_deg': ly * 360})

        if not plot_results:
            st.error("No data points found.")
        else:
            plot_df = pd.DataFrame(plot_results)
            colors_map = {'10': '#17becf', '30': '#4fbdb1', '100': '#bcbd22', '300': '#d29b77', '1000': '#e377c2'}
            markers = {'upward': '^', 'horizontal': '+', 'downward': 'v'}
            
            fig, ax = plt.subplots(figsize=(11, 8))
            for _, row in plot_df.iterrows():
                g_key = str(int(row['gamma']))
                lat = row['lat']
                color = colors_map.get(g_key, 'black')
                m = markers['upward'] if lat > 0 else (markers['downward'] if lat < 0 else markers['horizontal'])
                fc = 'None' if abs(lat) == 30 else color
                lw = 1.5 if abs(lat) == 30 else 0.5
                ax.scatter(row['x_deg'], row['y_deg'], color=color, marker=m, facecolor=fc, s=200, linewidths=lw)

            # 数値入力に基づいた範囲設定
            ax.set_xlim(x_min, x_max)
            ax.set_ylim(y_min, y_max)
            
            ax.set_xlabel(f'Lag X [deg]')
            ax.set_ylabel(f'Lag Y [deg]')
            ax.grid(True, linestyle=':', alpha=0.6)
            ax.axhline(0, color='black', lw=1, alpha=0.3)
            ax.axvline(0, color='black', lw=1, alpha=0.3)
            
            # 第2軸更新
            def deg2time(val): return val / 360.0 * period_val
            def time2deg(val): return val / period_val * 360.0
            ax.secondary_xaxis('top', functions=(deg2time, time2deg)).set_xlabel('Time Lag [s]')
            ax.secondary_yaxis('right', functions=(deg2time, time2deg)).set_ylabel('Time Lag [s]')

            st.pyplot(fig)
