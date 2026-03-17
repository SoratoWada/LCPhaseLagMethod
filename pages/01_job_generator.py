import streamlit as st
from src.tpm_utils import ApolloCommandBuilder, TPMParam
from itertools import product

st.title("🚀 Smart Apollo TPM Job Generator")
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
