# src/data_processor.py
from scipy.ndimage import gaussian_filter1d
import pandas as pd
import numpy as np

def scale_hapke_data(df_hapke, target_period_s):
    scale_factor = target_period_s / 100.0
    df_scaled = df_hapke.copy()
    # 1列目が時刻(JD)
    df_scaled.iloc[:, 0] = df_hapke.iloc[:, 0] * scale_factor
    return df_scaled

def integrate_tpm_and_hapke(df_tpm, dict_hapke):
    """
    IRとVisを同一フォーマットの行として統合する
    """
    # 1. IRデータ(TPM)の準備
    df_ir = df_tpm.copy()
    df_ir['category'] = 'IR'
    df_ir['type'] = None
    df_ir['model'] = 'TPM'
    
    # 2. 可視光データ(Vis)の作成
    vis_rows = []
    
    # パラメータの組み合わせごとに処理
    group_cols = ['lon_a', 'lat_b', 'period', 'axis_ratio', 'alpha']
    for keys, group in df_tpm.groupby(group_cols):
        p_val = float(keys[2].replace('s', ''))
        
        # 時刻のユニークリストを取得（マージ用）
        unique_times = group[['time']].drop_duplicates().sort_values('time')
        
        for v_type in ['S', 'C']:
            hapke_key = (keys[0], keys[1], v_type)
            if hapke_key not in dict_hapke:
                continue
            
            df_h = dict_hapke[hapke_key]
            df_h_scaled = scale_hapke_data(df_h, p_val)
            df_h_scaled.columns = ['time_h', 'vis_flux']
            
            # IRの時刻に最も近い可視光データを紐付け
            merged_vis = pd.merge_asof(
                unique_times,
                df_h_scaled,
                left_on='time',
                right_on='time_h',
                direction='nearest'
            )
            
            # 可視光専用の行を作成
            temp_vis = pd.DataFrame({
                'time': merged_vis['time'],
                'flux': merged_vis['vis_flux'],
                'wavelength': 0.55,  # 可視光の代表波長(μm)
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
            
    df_vis = pd.concat(vis_rows, ignore_index=True)
    
    return pd.concat(unified_chunks, ignore_index=True)

def extract_lc_metrics(df, sigma_pct=0.05):
    """
    全ライトカーブ（IRおよび可視光）のピーク位相と振幅比を計算する。
    """
    results = []
    # グルーピングの基準となるカラム
    group_cols = ['lon_a', 'lat_b', 'period', 'gamma', 'wavelength', 'category', 'type', 'model']
    actual_groups = [c for c in group_cols if c in df.columns]
    
    # dropna=False により、Visibleデータの gamma=NaN 等も除外せずにグループ化する
    for keys, group in df.groupby(actual_groups, dropna=False):
        group_dict = dict(zip(actual_groups, keys))
        
        # 周期(s)を数値化
        p_raw = group_dict.get('period', 100.0)
        p_sec = float(str(p_raw).replace('s', ''))
        p_days = p_sec / 86400.0
        
        temp = group.copy()
        # 1. 位相の計算 (時刻0を基準とした 0 to 1)
        temp['phase'] = (temp['time'] % p_days) / p_days
        temp = temp.sort_values('phase').reset_index(drop=True)
        
        # 2. ガウス平滑化 (周期性を考慮した mode='wrap')
        sigma = max(5, int(len(temp) * sigma_pct))
        temp['smooth_flux'] = gaussian_filter1d(temp['flux'], sigma=sigma, mode='wrap')
        
        # 3. ピーク（最大値）の位相を特定
        idx_max = temp['smooth_flux'].idxmax()
        peak_phase = temp.loc[idx_max, 'phase']
        
        # 4. 振幅比 (Amplitude Ratio) の計算
        # 定義: (max - min) / (max + min)
        f_max = temp['smooth_flux'].max()
        f_min = temp['smooth_flux'].min()
        
        amp_ratio = (f_max - f_min) / (f_max + f_min) if (f_max + f_min) != 0 else 0.0
        
        # 結果を格納
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
    Apply a phase correction due to the coordinate system to TPM data (category == 'IR').
    Correction formula: time = time + (lon_a - 90) / 360 * (period / 86400)
    """
    df_corr = df.copy()
    SECONDS_IN_DAY = 86400

    # Extract only IR category
    mask = df_corr['category'] == 'IR'
    mask = df_corr['category'] == 'IR'
    
    if mask.any():
        # Convert period from string like "100s" to numeric
        def get_period_val(p):
            if isinstance(p, str):
                return float(p.replace('s', ''))
            return float(p)

        # Execute the correction calculation
        # Use loc to safely update values
        lon_a = df_corr.loc[mask, 'lon_a']
        period_vals = df_corr.loc[mask, 'period'].apply(get_period_val)
        
        correction = (lon_a - 90) / 360 * (period_vals / SECONDS_IN_DAY)
        df_corr.loc[mask, 'time'] += correction
        
    return df_corr
    # 3. 結合 (共通カラムで縦に繋ぐ)
    # IR由来のカラム（gamma, cfrac等）はVis行ではNaNになる
    return pd.concat([df_ir, df_vis], ignore_index=True)
