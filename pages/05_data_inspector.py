# pages/05_data_inspector.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Page Setup
st.set_page_config(page_title="Data Inspector", layout="wide")
st.title("🔍 Parquet Data Inspector")

st.markdown("""
You can upload a consolidated (or generated) Parquet file to quickly view its contents.
""")

# File uploader
uploaded_file = st.file_uploader("Upload a Parquet file", type="parquet")

if uploaded_file:
    # Load the data
    df = pd.read_parquet(uploaded_file)

    # 1. Basic Information Summary
    st.subheader("📊 Dataset Overview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Rows", f"{len(df):,}")
    c2.metric("Columns", len(df.columns))
    
    with st.expander("Column Names & Types"):
        st.write(df.dtypes)

    # 2. Data Filtering
    st.subheader("🎯 Data Filtering")
    col_lon, col_lat, col_period = st.columns(3)

    # Create filters dynamically based on existing columns
    with col_lon:
        if 'lon_a' in df.columns:
            selected_lon = st.multiselect("Longitude (lon_a)", options=sorted(df['lon_a'].unique()))
    with col_lat:
        if 'lat_b' in df.columns:
            selected_lat = st.multiselect("Latitude (lat_b)", options=sorted(df['lat_b'].unique()))
    with col_period:
        if 'period' in df.columns:
            selected_period = st.multiselect("Period", options=sorted(df['period'].unique()))

    # Apply filtering
    query_df = df.copy()
    if 'lon_a' in df.columns and selected_lon:
        query_df = query_df[query_df['lon_a'].isin(selected_lon)]
    if 'lat_b' in df.columns and selected_lat:
        query_df = query_df[query_df['lat_b'].isin(selected_lat)]
    if 'period' in df.columns and selected_period:
        query_df = query_df[query_df['period'].isin(selected_period)]

    # 3. Data Preview
    st.subheader("📄 Data Preview")
    st.dataframe(query_df.head(100), use_container_width=True)

    # 4. Show Descriptive Statistics
    if st.checkbox("Show Descriptive Statistics (describe)"):
        st.write(query_df.describe())

    # 5. Quick Visualization
    if 'time' in query_df.columns:
        st.subheader("📈 Quick Light Curve Plot")
        # Select the column to plot (flux, vis_flux_S, etc.)
        numeric_cols = query_df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        y_axis = st.selectbox("Select data to display", options=[c for c in numeric_cols if c != 'time'])
        
        if not query_df.empty:
            fig, ax = plt.subplots(figsize=(10, 4))
            # As the graph becomes distorted when multiple parameters are combined, 
            # only the first set is plotted
            sample_group = query_df.head(1000) # Reduce rendering load
            ax.scatter(sample_group['time'], sample_group[y_axis], s=5, alpha=0.6)
            ax.set_xlabel("Time (JD or Scaled)")
            ax.set_ylabel(y_axis)
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)
        else:
            st.info("No data matches the filter.")
