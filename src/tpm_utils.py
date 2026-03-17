# src/tpm_utils.py
import math
from dataclasses import dataclass

@dataclass
class TPMParam:
    lon_a: int
    lat_b: int
    alpha_c: int
    gamma_d: int
    period_e: str
    axis_ratio_g: float

class ApolloCommandBuilder:
    def __init__(self, batch_size: int = 4):
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
