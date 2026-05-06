# src/data_processor.py
import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d
from scipy.spatial.transform import Rotation as R
try:
    from .pyhapke.hapkeRTM import HapkeRTM
except ImportError:
    from pyhapke.hapkeRTM import HapkeRTM

def normalize_vector(v):
    """ベクトルを正規化するヘルパー関数"""
    norm = np.linalg.norm(v)
    return v / norm if norm > 0 else v

def scale_hapke_data(df_hapke, target_period_s):
    scale_factor = target_period_s / 100.0
    df_scaled = df_hapke.copy()
    # 1列目が時刻(JD)
    df_scaled.iloc[:, 0] = df_hapke.iloc[:, 0] * scale_factor
    return df_scaled

def integrate_tpm_and_hapke(df_tpm, dict_hapke):
    """
    IR(TPM)とVis(Hapke)を統合する。
    Hapkeが多カラム(Parquet)でも、必要な2列(time, flux)を自動抽出して処理する。
    """
    # 1. IRデータの準備
    df_ir = df_tpm.copy()
    df_ir['category'] = 'IR'
    df_ir['type'] = None
    df_ir['model'] = 'TPM'
    
    vis_rows = []
    # TPMのグルーピング
    group_cols = ['lon_a', 'lat_b', 'period', 'axis_ratio', 'alpha']
    
    for keys, group in df_tpm.groupby(group_cols):
        # 周期を数値化
        p_val = float(str(keys[2]).replace('s', ''))
        unique_times = group[['time']].drop_duplicates().sort_values('time')
        
        for v_type in ['S', 'C']:
            # 辞書から該当する位置・タイプのデータを検索
            hapke_key = (float(keys[0]), float(keys[1]), v_type)
            if hapke_key not in dict_hapke:
                continue
            
            df_h_raw = dict_hapke[hapke_key]
            
            # Parquetの場合、最初の2列(time, flux)を使用する
            df_h_subset = df_h_raw.iloc[:, [0, 1]].copy()
            
            # 周期に合わせてスケーリング
            df_h_scaled = scale_hapke_data(df_h_subset, p_val)
            df_h_scaled.columns = ['time_h', 'vis_flux']
            
            # 直近の時刻でマージ
            merged_vis = pd.merge_asof(
                unique_times,
                df_h_scaled,
                left_on='time',
                right_on='time_h',
                direction='nearest'
            )
            
            # 可視光の行データを作成
            temp_vis = pd.DataFrame({
                'time': merged_vis['time'],
                'flux': merged_vis['vis_flux'],
                'wavelength': 0.55,
                'category': 'Visible',
                'type': v_type,
                'model': 'Hapke',
                'lon_a': keys[0],
                'lat_b': keys[1],
                'period': keys[2],
                'axis_ratio': keys[3],
                'alpha': keys[4]
            })
            vis_rows.append(temp_vis)
            
    if vis_rows:
        df_vis = pd.concat(vis_rows, ignore_index=True)
        # 最終的な結合
        return pd.concat([df_ir, df_vis], ignore_index=True)
    else:
        return df_ir

def extract_lc_metrics(df, sigma_pct=0.05):
    """
    全ライトカーブ（IRおよび可視光）のピーク位相と振幅比を計算する。
    """
    results = []
    group_cols = ['lon_a', 'lat_b', 'period', 'gamma', 'wavelength', 'category', 'type', 'model']
    actual_groups = [c for c in group_cols if c in df.columns]
    
    for keys, group in df.groupby(actual_groups, dropna=False):
        group_dict = dict(zip(actual_groups, keys))
        p_raw = group_dict.get('period', 100.0)
        p_sec = float(str(p_raw).replace('s', ''))
        p_days = p_sec / 86400.0
        
        temp = group.copy()
        temp['phase'] = (temp['time'] % p_days) / p_days
        temp = temp.sort_values('phase').reset_index(drop=True)
        
        sigma = max(5, int(len(temp) * sigma_pct))
        temp['smooth_flux'] = gaussian_filter1d(temp['flux'], sigma=sigma, mode='wrap')
        
        idx_max = temp['smooth_flux'].idxmax()
        peak_phase = temp.loc[idx_max, 'phase']
        
        f_max = temp['smooth_flux'].max()
        f_min = temp['smooth_flux'].min()
        amp_ratio = (f_max - f_min) / (f_max + f_min) if (f_max + f_min) != 0 else 0.0
        
        res = group_dict.copy()
        res.update({
            'peak_phase': peak_phase,
            'amp_ratio': amp_ratio,
            'max_flux': f_max,
            'min_flux': f_min
        })
        results.append(res)
    
    return pd.DataFrame(results)

def apply_tpm_phase_correction(df):
    """
    TPMデータ(category == 'IR')に対して、座標系に起因する位相の補正を行う。
    メッシュの事前回転とTPMコードによる座標変換が重なることで生じる
    2倍の回転（2 * lon_a）による位相の進みを、時間を加算して遅らせることで補正する。
    """
    df_corr = df.copy()
    SECONDS_IN_DAY = 86400
    mask = df_corr['category'] == 'IR'
    
    if mask.any():
        def get_period_val(p):
            if isinstance(p, str): return float(p.replace('s', ''))
            return float(p)

        # 形状モデルの事前回転と計算上の回転角の合計 (2 * lon_a) を取得
        lon_a = df_corr.loc[mask, 'lon_a']
        period_vals = df_corr.loc[mask, 'period'].apply(get_period_val)
        
        # 360度で1周期（period）なので、2*lon分を時間に変換して加算（位相を戻す）
        correction = (2 * lon_a) / 360 * (period_vals / SECONDS_IN_DAY)
        df_corr.loc[mask, 'time'] += correction
        
    return df_corr

def get_spin_rotation_matrix(spin_vector):
    z_axis = np.array([0, 0, 1])
    spin_axis = normalize_vector(np.array(spin_vector))
    if np.allclose(z_axis, spin_axis): return np.eye(3)
    if np.allclose(z_axis, -spin_axis): return R.from_euler('x', 180, degrees=True).as_matrix()
    v = np.cross(z_axis, spin_axis)
    c = np.dot(z_axis, spin_axis)
    s = np.linalg.norm(v)
    kmat = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + kmat + kmat.dot(kmat) * ((1 - c) / (s ** 2))

def calculate_hapke_lc_core(vertices, faces, normals, areas, ephemeris_df, params):
    results = []
    spin_vector = np.array(params['spin_axis'])
    r_spin_inv = get_spin_rotation_matrix(spin_vector).T 
    period_sec = params['period_hours'] * 3600.0
    initial_angle = np.deg2rad(params['initial_angle_deg'])
    ssa, poros = params['ssa'], params['porosity']
    b, c = params['phase_b'], params['phase_c']

    def hg_phase_func(g_rad, b, c):
        cos_g = np.cos(g_rad)
        b_sq = b**2
        return (1 - c)*(1 - b_sq)/(1 - 2*b*cos_g + b_sq)**1.5 + c*(1 - b_sq)/(1 + 2*b*cos_g + b_sq)**1.5

    for _, row in ephemeris_df.iterrows():
        sun_inertial = np.array([row['sun_x'], row['sun_y'], row['sun_z']])
        obs_inertial = np.array([row['obs_x'], row['obs_y'], row['obs_z']])
        
        sun_spin_ref = r_spin_inv @ normalize_vector(sun_inertial)
        obs_spin_ref = r_spin_inv @ normalize_vector(obs_inertial)
        
        angle = initial_angle + (2 * np.pi / period_sec) * row['time']
        r_rot_z = R.from_rotvec(np.array([0, 0, 1]) * angle).as_matrix()
        
        sun_body = r_rot_z.T @ sun_spin_ref
        obs_body = r_rot_z.T @ obs_spin_ref

        cos_g = np.dot(sun_body, obs_body)
        g_rad = np.arccos(np.clip(cos_g, -1.0, 1.0))
        Pg = hg_phase_func(g_rad, b, c)

        cos_is = np.dot(normals, sun_body)
        cos_es = np.dot(normals, obs_body)
        mask = (cos_is > 0) & (cos_es > 0)
        
        total_flux = 0.0
        for i in np.where(mask)[0]:
            # 直接インポートした HapkeRTM を使用
            rtm = HapkeRTM(
                i=np.arccos(cos_is[i]), e=np.arccos(cos_es[i]), g=g_rad, 
                P=Pg, poros=poros
            )
            total_flux += rtm.hapke_function_RADF(ssa) * areas[i] * cos_es[i]
            
        results.append(total_flux)
    return np.array(results)

def apply_90deg_phase_fix(df):
    """
    TPMデータ(category == 'IR')に対して、一律で90度（周期の1/4）の位相補正を行う。
    『時間を戻す』ため、計算された時間を減算する。
    """
    df_corr = df.copy()
    SECONDS_IN_DAY = 86400
    mask = df_corr['category'] == 'IR'
    
    if mask.any():
        def get_period_val(p):
            if isinstance(p, str): return float(p.replace('s', ''))
            return float(p)

        period_vals = df_corr.loc[mask, 'period'].apply(get_period_val)
        
        # 90度 = 1/4周期。この分だけ時間を戻す（減算）
        correction = 0.25 * (period_vals / SECONDS_IN_DAY)
        df_corr.loc[mask, 'time'] -= correction
        
    return df_corr
