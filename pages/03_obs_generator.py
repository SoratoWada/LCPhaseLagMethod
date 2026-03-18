import streamlit as st
import numpy as np
import math
import io
from src.tpm_utils import ApolloCommandBuilder, TPMParam
from itertools import product

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
