# src/data_processor.py
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
