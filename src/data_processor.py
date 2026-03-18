# src/data_processor.py
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
