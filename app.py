import streamlit as st
import numpy as np
import io
from itertools import product
from dataclasses import dataclass
from typing import List
import math

# --- データ構造 ---
@dataclass
class TPMParam:
    lon_a: int
    lat_b: int
    alpha_c: int
    gamma_d: int
    period_e: str
    axis_ratio_g: float

# --- 計算ロジッククラス (SH生成用) ---
class ApolloCommandBuilder:
    def __init__(self, batch_size: int = 6):
        self.batch_size = batch_size

    def calculate_f(self, a: int) -> int:
        return a - 90 if a >= 0 else a + 90

    def build_single_command_with_check(self, p: TPMParam, output_dir: str, log_dir: str, log_prefix: str, index: int) -> str:
        f = self.calculate_f(p.lon_a)
        input_obj = f"inputs/obj/ellipsoid_lon{f}_lat0_axisratio{p.axis_ratio_g}.obj"
        input_eph = f"inputs/eph/P{p.period_e}_x1_00_spinup100_analyze2_jb_longwarm.eph"
        input_spin = f"inputs/spin/P{p.period_e}_lon{p.lon_a}_lat{p.lat_b}.spin"
        input_obs = f"inputs/obs/P{p.period_e}_alpha{p.alpha_c}_202511.obs"
        
        output_file = (f"{output_dir}/result_shapeellipsoid_lon{f}_lat0_axisratio{p.axis_ratio_g}_"
                       f"alpha{p.alpha_c}_lon{p.lon_a}_lat{p.lat_b}_P{p.period_e}_Gamma{p.gamma_d}_cfrac0.7_cangle40_Laggeros.txt")
        log_file = f"{log_dir}/{log_prefix}_job{index}.log"

        core_cmd = (f'echo {input_obj} {input_eph} 0.9 {p.gamma_d} 0.0746 0.7 40 | '
                    f'runtpm -S {input_spin} -o {input_obs} -p 3600 -f')

        return (f'if [ ! -s "{output_file}" ]; then\n'
                f'    echo "[{index}] Running: {output_file}"\n'
                f'    {core_cmd} > "{output_file}" 2> "{log_file}" &\n'
                f'    ((running_jobs++))\n'
                f'    if (( running_jobs >= {self.batch_size} )); then wait; running_jobs=0; sleep 1; fi\n'
                f'else\n    echo "[{index}] Skip: {output_file}"; fi')

    def generate_full_script(self, params_list: List[TPMParam], output_dir: str, log_dir_name: str, log_prefix: str) -> str:
        log_dir = f"{output_dir}/{log_dir_name}"
        lines = ["#!/bin/bash", "", "if ! command -v runtpm &> /dev/null; then echo 'Error: runtpm not found'; exit 1; fi",
                 f"mkdir -p {output_dir}", f"mkdir -p {log_dir}", "running_jobs=0", ""]
        for i, p in enumerate(params_list, 1):
            lines.append(self.build_single_command_with_check(p, output_dir, log_dir, log_prefix, i))
        lines.append("\nwait\necho 'Done.'")
        return "\n".join(lines)

# --- UI 制御 ---
st.set_page_config(page_title="TPM Expert Toolset", layout="wide")
mode = st.sidebar.radio("Menu", ["1. Shell Script 生成", "2. EPH ファイル生成", "3. OBS ファイル生成"])

# --- PAGE 1: Shell Script ---
if mode == "1. Shell Script 生成":
    st.title("🚀 Apollo TPM Job Generator")
    col1, col2 = st.columns(2)
    with col1: exp_name = st.text_input("実験名", value="20260313_test_run")
    with col2: batch_size = st.number_input("バッチサイズ", value=6, min_value=1, max_value=8)

    with st.sidebar:
        st.header("Parameters")
        a_opts = [-150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150, 180]
        a_vals = st.multiselect("A: Lon", a_opts, default=a_opts)
        b_opts = [-90, -60, -30, 0, 30, 60, 90]
        b_vals = st.multiselect("B: Lat", b_opts, default=b_opts)
        c_vals = st.multiselect("C: Alpha", [0, 30, 60, 90, 120], default=[90])
        d_vals = st.multiselect("D: Gamma", [10, 100, 1000], default=[1000])
        e_vals = st.multiselect("E: Period", ["10s", "100s", "1000s"], default=["100s"])
        g_vals = st.multiselect("G: Axis Ratio", [1.3], default=[1.3])

    combinations = list(product(a_vals, b_vals, c_vals, d_vals, e_vals, g_vals))
    params_list = [TPMParam(*combo) for combo in combinations]
    st.metric("Total Jobs", len(params_list))

    builder = ApolloCommandBuilder(batch_size=batch_size)
    script = builder.generate_full_script(params_list, f"outputs/raw/tpm/{exp_name}", "logs", "tpm")
    st.code(script, language="bash")
    st.download_button("Download run_tpm.sh", script, file_name="run_tpm.sh")

# --- PAGE 2: EPH ---
elif mode == "2. EPH ファイル生成":
    st.title("📅 Precision EPH Generator")
    target_p = st.number_input("周期 P (s)", value=100.0, step=1.0)
    
    SEC_PER_DAY = 86400.0
    TOTAL_ROWS = 23573
    ZERO_ROW_INDEX = 21572
    dt_jd = (target_p / 1000.0) / SEC_PER_DAY
    fixed_cols = "1.00000 0.00000 0.00000"
    
    new_lines = [f"{-1.0:.12f} {fixed_cols}"]
    for i in range(1, TOTAL_ROWS):
        current_jd = (i - ZERO_ROW_INDEX) * dt_jd
        new_lines.append(f"{current_jd:.12f} {fixed_cols}")
        
    final_content = "\n".join(new_lines)
    st.code("\n".join(new_lines[:5]) + "\n...\n" + "\n".join(new_lines[21570:21575]))
    fname = f"P{int(target_p)}s_x1_00_spinup100_analyze2_jb_longwarm.eph"
    st.download_button(f"{fname} をダウンロード", final_content, file_name=fname)

# --- PAGE 3: OBS ---
elif mode == "3. OBS ファイル生成":
    st.title("🔭 OBS File Generator")
    
    col_obs1, col_obs2 = st.columns(2)
    with col_obs1:
        obs_p = st.number_input("Rotational Period P (s)", value=100.0, step=1.0)
        obs_alpha = st.number_input("Phase Angle Alpha (deg)", value=90.0, step=1.0)
    with col_obs2:
        analysis_rot = st.number_input("Analysis Rotations", value=2, min_value=1)
        steps_per_rot = st.number_input("Steps per Rotation", value=1000, min_value=10)

    # ロジック実行
    SECONDS_IN_A_DAY = 86400.0
    period_day = obs_p / SECONDS_IN_A_DAY
    analysis_end_time = analysis_rot * period_day
    num_analysis_steps = int(analysis_rot * steps_per_rot)
    
    # 0からendまでを等間隔に(num_analysis_steps + 1)点生成
    time_steps = np.linspace(0, analysis_end_time, num_analysis_steps + 1)
    num_observations = len(time_steps)

    # 座標設定
    sun_coords = "1.00000 0.00000 0.00000"
    alpha_rad = math.radians(obs_alpha)
    earth_coords = f"{np.cos(alpha_rad):.5f} {np.sin(alpha_rad):.5f} 0.00000"

    # テキスト生成
    obs_output = io.StringIO()
    obs_output.write(f'{num_observations}\n\n')

    for i, current_jd in enumerate(time_steps):
        obs_output.write(f"{current_jd:.11f} 43\n")
        obs_output.write(f"{sun_coords}\n")
        obs_output.write(f"{earth_coords}\n")
        for x in range(40, 251, 5):
            obs_output.write(f"{x/10.0:.1f} 0.1 0.1\n")
        if i < num_observations - 1:
            obs_output.write("\n")

    st.subheader("Preview")
    preview_lines = obs_output.getvalue().split('\n')
    st.code("\n".join(preview_lines[:15]))

    obs_fname = f"P{int(obs_p)}s_alpha{int(obs_alpha)}_202511.obs"
    st.download_button(f"{obs_fname} をダウンロード", obs_output.getvalue(), file_name=obs_fname)
