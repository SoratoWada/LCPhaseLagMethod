# pages/09_lag_lag_diagram.py
import streamlit as st
import pandas as pd
import numpy as np
import io
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

    x_min, x_max = axis_range_control("X-axis [deg]", -180, 180, (-60, 60))
    y_min, y_max = axis_range_control("Y-axis [deg]", -180, 180, (-15, 15))

    # --- 4. Text & Legend Settings ---
    st.sidebar.header("4. Text & Legend Settings")
    show_legend = st.sidebar.checkbox("Show legend", value=True)
    show_title = st.sidebar.checkbox("Show title", value=True)
    axis_label_fontsize = st.sidebar.slider("Axis label font size", 8, 40, 24, step=1)
    tick_fontsize = st.sidebar.slider("Tick label font size", 6, 40, 18, step=1)
    title_fontsize = st.sidebar.slider("Title font size", 10, 50, 28, step=1)
    secondary_label_fontsize = st.sidebar.slider("Secondary axis label font size", 8, 40, 24, step=1)
    legend_fontsize = st.sidebar.slider("Legend font size", 6, 40, 20, step=1)
    legend_title_fontsize = st.sidebar.slider("Legend title font size", 6, 50, 24, step=1)
    marker_size = st.sidebar.slider("Marker size", 10, 800, 350, step=10)

    marker_mode = st.sidebar.selectbox(
        "Marker shape mode",
        ["Varied (by latitude, previous behavior)", "Unified (single marker)"],
        index=0,
    )
    unified_marker = None
    if marker_mode.startswith("Unified"):
        unified_marker = st.sidebar.selectbox("Unified marker", ["o", "s", "^", "v", "+", "x", "D"], index=0)

    # --- 5. Quality Control (Histogram & Threshold) ---
    st.sidebar.header("5. Quality Control")
    
    mask_base = (df['period'] == common_p_str)
    if 'alpha' in df.columns: mask_base &= (df['alpha'] == common_alpha)
    if 'axis_ratio' in df.columns: mask_base &= (df['axis_ratio'] == common_ar)
    base_df = df[mask_base]

    if not base_df.empty:
        st.sidebar.write("**Fractional Amplitude Distribution**")
        fig_h, ax_h = plt.subplots(figsize=(4, 2.5))
        ax_h.hist(base_df['amp_ratio'].dropna(), bins=30, color='teal', alpha=0.7, edgecolor='white')
        hist_label_fs = min(axis_label_fontsize, 12)
        hist_tick_fs = min(tick_fontsize, 9)
        ax_h.set_xlabel("Fractional Amplitude", fontsize=hist_label_fs)
        ax_h.set_ylabel("Count", fontsize=hist_label_fs)
        current_max = base_df['amp_ratio'].max()
        ax_h.set_xlim(0, max(0.2, current_max * 1.1))
        ax_h.tick_params(labelsize=hist_tick_fs)
        st.sidebar.pyplot(fig_h)

    st.sidebar.write("**Min Fractional Amplitude Threshold**")
    st.sidebar.slider("Threshold Slider", 0.0, 1.0, 0.07, step=0.01, key="amp_min_slider", label_visibility="collapsed")
    st.sidebar.number_input("Value Input", min_value=0.0, max_value=1.0, value=st.session_state.amp_min_slider, step=0.01, key="amp_min_number")
    amp_min = st.session_state.amp_min_number

    # --- 6. 位相差（Lag）の設定 ---
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

    def format_target_for_label(t):
        if t["cat"] == "Visible":
            return "Visible"
        return f'{t["val"]}μm'

    default_xlabel = f'Phase Lag: {format_target_for_label(t_x_a)} - {format_target_for_label(t_x_b)} [deg]'
    default_ylabel = f'Phase Lag: {format_target_for_label(t_y_a)} - {format_target_for_label(t_y_b)} [deg]'
    default_title = f'Lag-Lag Diagram\n(P={common_p_str}, α={common_alpha}°, AR={common_ar}, Min FA={amp_min})'

    st.sidebar.subheader("Text Overrides")
    xlabel_text = st.sidebar.text_input("X-axis label text", value=default_xlabel)
    ylabel_text = st.sidebar.text_input("Y-axis label text", value=default_ylabel)
    title_text = st.sidebar.text_input("Title text", value=default_title)

    st.sidebar.subheader("Export")
    default_export_stem = (
        f'Lag-lag_diagram_P{common_p_str}_alpha{int(common_alpha)}deg_minFA{amp_min:.2f}_'
        f'marker{"varied" if marker_mode.startswith("Varied") else "unified"}'
    )
    export_filename_stem = st.sidebar.text_input(
        "Export filename (without extension)",
        value=default_export_stem,
        help='例: Lag-lag_diagram_P100s_alpha90deg_minFA0.07_optmodelHapke_..._markervaried',
    )

    # --- 7. 描画実行 ---
    if st.button("Generate Diagram"):
        target_df = base_df[base_df['amp_ratio'] >= amp_min]
        
        lons = sorted(target_df['lon_a'].unique())
        lats = sorted(target_df['lat_b'].unique())
        gammas = sorted(target_df['gamma'].dropna().unique())
        
        plot_results = []
        for g in gammas:
            for lat in lats:
                for lon in lons:
                    # lat=90, -90の場合はlon=0のみをプロット対象とする
                    if abs(lat) == 90 and lon != 0:
                        continue

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
                        # 循環処理 (-0.25 to 0.25)
                        lx = (lx + 0.25) % 0.5 - 0.25
                        ly = (ly + 0.25) % 0.5 - 0.25
                        plot_results.append({'gamma': g, 'lat': lat, 'x_deg': lx * 360, 'y_deg': ly * 360})

        if not plot_results:
            st.error("No data points found matching criteria.")
        else:
            plot_df = pd.DataFrame(plot_results)
            colors_map = {'10': '#17becf', '100': '#bcbd22', '1000': '#e377c2'}

            fig, ax = plt.subplots(figsize=(15, 9))

            def lat_to_marker_style(lat, color):
                if marker_mode.startswith("Unified"):
                    return {"marker": unified_marker, "facecolor": color, "linewidths": 0.5}

                if lat >= 60:
                    return {"marker": "^", "facecolor": color, "linewidths": 0.5}
                if lat == 30:
                    return {"marker": "^", "facecolor": "None", "linewidths": 1.5}
                if lat == 0:
                    return {"marker": "+", "facecolor": color, "linewidths": 2.0}
                if lat == -30:
                    return {"marker": "v", "facecolor": "None", "linewidths": 1.5}
                if lat <= -60:
                    return {"marker": "v", "facecolor": color, "linewidths": 0.5}
                return {"marker": "o", "facecolor": color, "linewidths": 0.5}

            for _, row in plot_df.iterrows():
                g_key = str(int(row['gamma']))
                color = colors_map.get(g_key, 'black')
                lat = row['lat']
                style = lat_to_marker_style(lat, color)
                ax.scatter(
                    row['x_deg'],
                    row['y_deg'],
                    color=color,
                    marker=style["marker"],
                    facecolor=style["facecolor"],
                    s=marker_size,
                    linewidths=style["linewidths"],
                    alpha=0.8,
                )

            ax.set_xlim(x_min, x_max)
            ax.set_ylim(y_min, y_max)
            x_span = float(abs(x_max - x_min))
            y_span = float(abs(y_max - y_min))
            if x_span > 0 and y_span > 0:
                ax.set_aspect(x_span / y_span, adjustable="box")
            
            ax.set_xlabel(xlabel_text, fontsize=axis_label_fontsize)
            ax.set_ylabel(ylabel_text, fontsize=axis_label_fontsize)
            if show_title:
                ax.set_title(title_text, fontsize=title_fontsize, pad=20)

            ax.tick_params(axis='both', labelsize=tick_fontsize)
            
            ax.grid(True, linestyle=':', alpha=0.6)
            ax.axhline(0, color='black', lw=1, alpha=0.3)
            ax.axvline(0, color='black', lw=1, alpha=0.3)
            
            # 第2軸（時間軸）の表示
            secx = ax.secondary_xaxis('top', functions=(lambda x: x/360*period_val, lambda x: x/period_val*360))
            secx.set_xlabel('Time Lag [s]', fontsize=secondary_label_fontsize, labelpad=10)
            secx.tick_params(labelsize=tick_fontsize)

            secy = ax.secondary_yaxis('right', functions=(lambda x: x/360*period_val, lambda x: x/period_val*360))
            secy.set_ylabel('Time Lag [s]', fontsize=secondary_label_fontsize)
            secy.tick_params(labelsize=tick_fontsize)

            extra_artists = []
            if show_legend:
                legend_marker_size = max(6, int(legend_fontsize))
                gamma_h = [
                    Line2D(
                        [0],
                        [0],
                        marker='s',
                        linestyle='None',
                        color='w',
                        label=rf'$\Gamma$ = {g} tiu',
                        markerfacecolor=colors_map.get(g, 'black'),
                        markersize=legend_marker_size,
                    )
                    for g in sorted(colors_map.keys(), key=int)
                ]
                leg_gamma = ax.legend(
                    handles=gamma_h,
                    title="Thermal Inertia",
                    loc='upper left',
                    bbox_to_anchor=(1.15, 1.0),
                    fontsize=legend_fontsize,
                    title_fontsize=legend_title_fontsize,
                    frameon=True,
                    borderaxespad=0.0,
                )
                ax.add_artist(leg_gamma)
                extra_artists.append(leg_gamma)

                if marker_mode.startswith("Unified"):
                    lat_h = [
                        Line2D(
                            [0],
                            [0],
                            marker=unified_marker,
                            linestyle='None',
                            color='gray',
                            label='All latitudes',
                            markerfacecolor='gray' if unified_marker not in ["+", "x"] else 'None',
                            markeredgecolor='gray',
                            markeredgewidth=2 if unified_marker in ["+", "x"] else 0.5,
                            markersize=legend_marker_size,
                        )
                    ]
                else:
                    lat_h = [
                        Line2D([0], [0], marker='^', linestyle='None', color='gray', label='Lat ≥ 60°', markerfacecolor='gray', markersize=legend_marker_size),
                        Line2D([0], [0], marker='^', linestyle='None', color='gray', label='Lat = 30°', markerfacecolor='None', markeredgecolor='gray', markeredgewidth=1.5, markersize=legend_marker_size),
                        Line2D([0], [0], marker='+', linestyle='None', color='gray', label='Lat = 0°', markeredgewidth=2, markersize=legend_marker_size),
                        Line2D([0], [0], marker='v', linestyle='None', color='gray', label='Lat = -30°', markerfacecolor='None', markeredgecolor='gray', markeredgewidth=1.5, markersize=legend_marker_size),
                        Line2D([0], [0], marker='v', linestyle='None', color='gray', label='Lat ≤ -60°', markerfacecolor='gray', markersize=legend_marker_size),
                    ]

                leg_lat = ax.legend(
                    handles=lat_h,
                    title="Spin-axis",
                    loc='upper left',
                    bbox_to_anchor=(1.15, 0.62),
                    fontsize=legend_fontsize,
                    title_fontsize=legend_title_fontsize,
                    frameon=True,
                    borderaxespad=0.0,
                )
                extra_artists.append(leg_lat)

                fig.subplots_adjust(right=0.62)
            else:
                fig.subplots_adjust(right=0.98)

            pad_inches = 0.45 if show_title else 0.80
            buf_png = io.BytesIO()
            fig.savefig(
                buf_png,
                format="png",
                dpi=200,
                bbox_inches="tight",
                bbox_extra_artists=extra_artists,
                pad_inches=pad_inches,
            )
            st.session_state["laglag_last_png"] = buf_png.getvalue()

            buf_jpg = io.BytesIO()
            fig.savefig(
                buf_jpg,
                format="jpg",
                dpi=200,
                bbox_inches="tight",
                bbox_extra_artists=extra_artists,
                pad_inches=pad_inches,
            )
            st.session_state["laglag_last_jpg"] = buf_jpg.getvalue()

            st.session_state["laglag_last_caption"] = (
                f'P={common_p_str}, α={common_alpha}°, AR={common_ar}, Min FA={amp_min}'
            )
            st.session_state["laglag_last_export_stem"] = export_filename_stem

            st.image(
                st.session_state["laglag_last_png"],
                caption=st.session_state["laglag_last_caption"],
                use_container_width=True,
            )

    # 設定をいじって再実行されても、最後に生成した図は保持して表示する
    if "laglag_last_png" in st.session_state:
        st.subheader("Last generated diagram (kept until next Generate Diagram)")
        st.image(
            st.session_state["laglag_last_png"],
            caption=st.session_state.get("laglag_last_caption", ""),
            use_container_width=True,
        )
        export_stem = st.session_state.get("laglag_last_export_stem", "Lag-lag_diagram")
        c_png, c_jpg = st.columns(2)
        with c_png:
            st.download_button(
                label="Download PNG",
                data=st.session_state["laglag_last_png"],
                file_name=f"{export_stem}.png",
                mime="image/png",
            )
        with c_jpg:
            if "laglag_last_jpg" in st.session_state:
                st.download_button(
                    label="Download JPEG",
                    data=st.session_state["laglag_last_jpg"],
                    file_name=f"{export_stem}.jpg",
                    mime="image/jpeg",
                )
