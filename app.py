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

# --- UI 制御 ---
st.set_page_config(page_title="TPM Expert Toolset", layout="wide")
mode = st.sidebar.radio("Menu", ["1. Shell Script 生成", "2. EPH ファイル生成", "3. OBS ファイル生成"])
