import streamlit as st
from src.tpm_utils import ApolloCommandBuilder, TPMParam
from itertools import product

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
