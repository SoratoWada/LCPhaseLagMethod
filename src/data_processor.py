# src/data_processor.py
from scipy.ndimage import gaussian_filter1d
import pandas as pd
import numpy as np

def scale_hapke_data(df_hapke, target_period_s):
    """Scale the time stamps of the Hapke data (based on a 100-second interval) to match the target period."""
    scale_factor = target_period_s / 100.0
    df_scaled = df_hapke.copy()
    # 1列目がJD(時刻)と想定
    df_scaled.iloc[:, 0] = df_hapke.iloc[:, 0] * scale_factor
    return df_scaled

def integrate_tpm_and_hapke(df_tpm, dict_hapke):
    """
    Integrate the TPM DataFrame with the Hapke data dictionary.
    dict_hapke: {(lon, lat, type): df_hapke}
    """
    unified_chunks = []

    # Process each combination of parameters
    for (lon, lat, p_str), group in df_tpm.groupby(['lon_a', 'lat_b', 'period']):
        p_val = float(p_str.replace('s', ''))

        # Combine visible light data for both S and C types
        for v_type in ['S', 'C']:
            hapke_key = (lon, lat, v_type)
            if hapke_key not in dict_hapke:
                continue
            
            df_h = dict_hapke[hapke_key]
            # Scale the data to match the target period
            df_h_scaled = scale_hapke_data(df_h, p_val)
            df_h_scaled.columns = ['time_scaled', f'vis_flux_{v_type}']

            # Merge on the nearest time
            group = group.sort_values('time')
            df_h_scaled = df_h_scaled.sort_values('time_scaled')
            
            group = pd.merge_asof(
                group,
                df_h_scaled,
                left_on='time',
                right_on='time_scaled',
                direction='nearest'
            )
            group = group.drop(columns=['time_scaled'])
            
        unified_chunks.append(group)
    
    return pd.concat(unified_chunks, ignore_index=True)

def extract_lc_metrics(df, sigma_pct=0.05):
    """
    各ライトカーブのピーク位相と振幅比（変調度）を計算する
    """
    results = []
    # ユニークなライトカーブを特定するためのカラム
    group_cols = ['lon_a', 'lat_b', 'period', 'gamma', 'wavelength', 'category', 'type', 'model']
    actual_groups = [c for c in group_cols if c in df.columns]
    
    for keys, group in df.groupby(actual_groups, dropna=False):
        # 周期(s)を数値化
        p_str = str(dict(zip(actual_groups, keys))['period'])
        p_sec = float(p_str.replace('s', ''))
        p_days = p_sec / 86400.0
        
        temp = group.copy()
        # 1. 位相の計算 (0 to 1)
        temp['phase'] = (temp['time'] % p_days) / p_days
        temp = temp.sort_values('phase').reset_index(drop=True)
        
        # 2. 平滑化 (Gaussian filter, periodic wrap)
        sigma = max(5, int(len(temp) * sigma_pct))
        temp['smooth_flux'] = gaussian_filter1d(temp['flux'], sigma=sigma, mode='wrap')
        
        # 3. ピーク検出
        idx_max = temp['smooth_flux'].idxmax()
        peak_phase = temp.loc[idx_max, 'phase']
        
        # 4. 振幅比 (Amplitude Ratio) の計算
        # 定義: (max - min) / (max + min)
        f_max = temp['smooth_flux'].max()
        f_min = temp['smooth_flux'].min()
        
        # 0除算を避けるための微小値チェック
        if (f_max + f_min) != 0:
            amp_ratio = (f_max - f_min) / (f_max + f_min)
        else:
            amp_ratio = 0.0
        
        res = dict(zip(actual_groups, keys))
        res.update({
            'peak_phase': peak_phase,
            'amp_ratio': amp_ratio,
            'max_flux': f_max,
            'min_flux': f_min
        })
        results.append(res)
    
    return pd.DataFrame(results)
