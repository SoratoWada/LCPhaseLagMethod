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
    Calculate the peak phase and amplitude of each light curve
    """
    results = []
    # Column for identifying unique light curves
    group_cols = ['lon_a', 'lat_b', 'period', 'gamma', 'wavelength', 'category', 'type', 'model']
    actual_groups = [c for c in group_cols if c in df.columns]
    
    for keys, group in df.groupby(actual_groups, dropna=False):
        # Convert period (s) to numeric and then to days
        p_str = str(dict(zip(actual_groups, keys))['period'])
        p_sec = float(p_str.replace('s', ''))
        p_days = p_sec / 86400.0
        
        temp = group.copy()
        # 1. Calculate phase (0 to 1)
        temp['phase'] = (temp['time'] % p_days) / p_days
        temp = temp.sort_values('phase').reset_index(drop=True)

        # 2. Smooth (Gaussian filter, periodic wrap)
        # Use 5% of data points as standard deviation (per provided code)
        sigma = max(5, int(len(temp) * sigma_pct))
        temp['smooth_flux'] = gaussian_filter1d(temp['flux'], sigma=sigma, mode='wrap')

        # 3. Peak detection
        idx_max = temp['smooth_flux'].idxmax()
        peak_phase = temp.loc[idx_max, 'phase']

        # 4. Calculate amplitude
        max_f = temp['smooth_flux'].max()
        min_f = temp['smooth_flux'].min()
        amplitude = max_f - min_f
        
        res = dict(zip(actual_groups, keys))
        res.update({
            'peak_phase': peak_phase,
            'amplitude': amplitude,
            'max_flux': max_f,
            'min_flux': min_f
        })
        results.append(res)
    
    metrics_df = pd.DataFrame(results)

    # 5. Calculate Amplitude Ratio
    # Divide IR data by the amplitude of visible light (Visible) with the same (Lon, Lat, Period)
    if 'category' in metrics_df.columns:
        vis_ref = metrics_df[metrics_df['category'] == 'Visible'].copy()
        # Narrow down to one reference for visible light (e.g., S-type) and merge
        if not vis_ref.empty:
            vis_ref = vis_ref.drop_duplicates(subset=['lon_a', 'lat_b', 'period'])
            vis_ref = vis_ref[['lon_a', 'lat_b', 'period', 'amplitude']].rename(columns={'amplitude': 'vis_amp'})
            
            metrics_df = pd.merge(metrics_df, vis_ref, on=['lon_a', 'lat_b', 'period'], how='left')
            metrics_df['amp_ratio'] = metrics_df['amplitude'] / metrics_df['vis_amp']
            
    return metrics_df
