import streamlit as st
import pandas as pd
import plotly.express as px
import os
import sys

# --- Configuration & Setup ---
st.set_page_config(layout="wide", page_title="17-Outlet Aging Analysis")
st.title("📊 Multi-Outlet Inventory Aging Analysis")

# --- Define File Mapping ---
# BASE_PATH must be 'data' for cloud deployment if files are in a 'data' folder
BASE_PATH = 'data' 

# 🚨 DEFINITIVE LIST OF 17 OUTLETS AND FILES 🚨
outlets_files = {
    "AML": "AML.xlsx",
    "ATT": "AZT.xlsx", # Note: Changed file name to 'AZT.xlsx' as provided in the list
    "AZR": "AZR.xlsx",
    "BPS": "BPS.xlsx",
    "FAH": "FAH.xlsx",
    "HAD": "HAD.xlsx",
    "HAM": "HAM.xlsx",
    "JZS": "JZS.xlsx",
    "LWN": "LWN.xlsx",
    "MSS": "MSS.xlsx",
    "SAD": "SAD.xlsx",
    "SAM": "SAM.xlsx",
    "SAO": "SAO.xlsx",
    "SBM": "SBM.xlsx",
    "SML": "SML.xlsx",
    "SPS": "SPS.xlsx",
    "TTD": "TTD.xlsx",
}

# Define the custom order of aging buckets (important for charting order)
# Based on the visual example you provided, these are the likely headers
AGE_ORDER = ['61-90', '91-120', '121-180', '181-360']

@st.cache_data
def load_and_transform_data(file_map, base_path):
    """Loads, cleans, combines, and transforms data for all outlets."""
    all_data = []
    loaded_files_count = 0
    
    # Check if the data path exists for debugging
    full_data_path = os.path.join(os.getcwd(), base_path)
    if not os.path.isdir(full_data_path):
        st.error(f"❌ DATA FOLDER NOT FOUND: Expected folder '{base_path}' at {os.getcwd()}.")
        return pd.DataFrame()

    for outlet_name, file_name in file_map.items():
        file_path = os.path.join(base_path, file_name)

        # Use os.path.exists() to check file presence
        if not os.path.exists(file_path): 
            st.warning(f"File Missing: Cannot find file for **{outlet_name}** at `{file_path}`. Skipping...")
            continue

        try:
            df = pd.read_excel(file_path)
            
            if df.empty or len(df.columns) < 2:
                st.warning(f"File Empty: Data in **{outlet_name}** is empty or incorrectly formatted. Skipping...")
                continue
                
            # Rename the first column to 'Category'
            df.rename(columns={df.columns[0]: 'Category'}, inplace=True)
            df.dropna(subset=['Category'], inplace=True)
            df = df[df['Category'] != 'TOTAL'] 
            df['Outlet'] = outlet_name
            all_data.append(df)
            loaded_files_count += 1
            
        except Exception as e:
            st.error(f"Error reading file for {outlet_name} ({file_name}): {e}. Check file integrity.")
            continue

    if not all_data:
        st.error("❌ Critical: No data successfully loaded from any file. Check file paths and content.")
        # Do not use sys.exit() in Streamlit Cloud, just return empty DataFrame
        return pd.DataFrame() 

    combined_df = pd.concat(all_data, ignore_index=True)
    st.sidebar.success(f"✅ Successfully loaded data from {loaded_files_count} out of {len(file_map)} outlets.")

    # 1. Standard Melting
    id_vars = ['Category', 'Outlet']
    value_cols = [col for col in combined_df.columns if col not in id_vars]

    long_df = pd.melt(
        combined_df,
        id_vars=id_vars,
        value_vars=value_cols,
        var_name='Aging_Column',
        value_name='Value'
    )
    long_df['Value'] = pd.to_numeric(long_df['Value'], errors='coerce')
    long_df.dropna(subset=['Value'], inplace=True)

    # 2. Extract Clean Aging Bucket (e.g., '61-90')
    def clean_aging_bucket(col):
        for bucket in AGE_ORDER:
            # Check if the bucket string is anywhere in the column name (e.g., '61-90 Agir')
            if bucket in str(col):
                return bucket
        return 'Other'

    long_df['Aging_Bucket'] = long_df['Aging_Column'].apply(clean_aging_bucket)
    
    # Filter out columns that aren't part of the core aging buckets and set order
    long_df = long_df[long_df['Aging_Bucket'].isin(AGE_ORDER)]
    long_df['Aging_Bucket'] = pd.Categorical(long_df['Aging_Bucket'], categories=AGE_ORDER, ordered=True)
    
    return long_df

# --- Load Data ---
df_long = load_and_transform_data(outlets_files, BASE_PATH)

if df_long.empty:
    st.stop()

# --- 1. Sidebar Filters (Dynamic) ---
st.sidebar.header("Filter Options")
st.markdown("Visualize top categories contributing to **Value** in specific aging periods.")

# Outlet Selection (Dynamic Filter - Crucial for multi-outlet view)
all_outlets = sorted(df_long['Outlet'].unique())
selected_outlets = st.sidebar.multiselect(
    "1. Select Outlet(s) to Aggregate:",
    options=all_outlets,
    default=all_outlets[:3] 
)

# Category Selection (Dynamic Filter)
all_categories = sorted(df_long['Category'].unique())
select_all_cat = st.sidebar.checkbox("2. Select All Categories", value=True)

if select_all_cat:
    selected_categories = all_categories
else:
    selected_categories = st.sidebar.multiselect(
        "2. Individual Categories:",
        options=all_categories,
        default=all_categories[:5]
    )

# --- 2. Apply Filters and Aggregation ---
df_filtered = df_long[
    df_long['Outlet'].isin(selected_outlets) &
    df_long['Category'].isin(selected_categories)
]

if df_filtered.empty:
    st.warning("⚠️ No data matches the current filters. Please adjust your selections.")
    st.stop()
    
# Aggregate by Category and Aging Bucket (SUM across all selected Outlets)
df_aggregated = df_filtered.groupby(['Category', 'Aging_Bucket'])['Value'].sum().reset_index()

# --- 3. Visualization Functions ---

def plot_horizontal_bar_aging(df, bucket, color):
    """Creates a horizontal bar chart for a single aging bucket."""
    df_bucket = df[df['Aging_Bucket'] == bucket]
    
    if df_bucket.empty: return st.info(f"No Value data found for the **{bucket}** bucket.")

    # Sort and take top 15 categories for visual clarity
    df_bucket = df_bucket.sort_values(by='Value', ascending=False).head(15)
    df_bucket = df_bucket.sort_values(by='Value', ascending=True) # Sort again for horizontal plot
    
    total_value = df_bucket['Value'].sum()

    fig = px.bar(
        df_bucket,
        x='Value',
        y='Category',
        orientation='h',
        title=f'Value Aging in {bucket} Days (Total: ${total_value:,.0f})',
        labels={'Value': 'Total Value ($)', 'Category': ''},
        color_discrete_sequence=[color],
        hover_data={'Value': ':,0f'}
    )
    fig.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

def plot_treemap_aging(df):
    """Creates a treemap to show hierarchical contribution."""
    df_total = df.groupby(['Aging_Bucket', 'Category'])['Value'].sum().reset_index()
    
    fig = px.treemap(
        df_total,
        path=[px.Constant("Aging Analysis"), 'Aging_Bucket', 'Category'],
        values='Value',
        title='Hierarchical Value Contribution by Aging Bucket and Category',
        color='Value',
        color_continuous_scale='Reds',
        hover_data={'Value': ':,0f', 'Category': True, 'Aging_Bucket': True}
    )
    fig.update_layout(margin=dict(t=50, l=25, r=25, b=25))
    st.plotly_chart(fig, use_container_width=True)

# --- 4. Main Content Tabs ---
tab1, tab2, tab3 = st.tabs(["📈 Aging Distribution by Category", "🌳 Treemap Contribution", "📋 Raw Data"])

with tab1:
    st.header("Aging Distribution Analysis: Value")
    st.caption(f"Showing the top 15 categories by aggregated value for selected outlets: **{', '.join(selected_outlets)}**")
    st.markdown("---")

    bucket_colors = px.colors.qualitative.Bold 

    col_charts_1, col_charts_2 = st.columns(2)
    
    # Plot the four separate horizontal bar charts
    with col_charts_1:
        plot_horizontal_bar_aging(df_aggregated, AGE_ORDER[0], bucket_colors[0])
        st.markdown("---")
        plot_horizontal_bar_aging(df_aggregated, AGE_ORDER[1], bucket_colors[1])

    with col_charts_2:
        plot_horizontal_bar_aging(df_aggregated, AGE_ORDER[2], bucket_colors[2])
        st.markdown("---")
        plot_horizontal_bar_aging(df_aggregated, AGE_ORDER[3], bucket_colors[3])

with tab2:
    st.header("Hierarchical Value Contribution")
    plot_treemap_aging(df_aggregated)
    st.caption("The Treemap displays the share of total value across all selected outlets, divided by aging bucket and category.")

with tab3:
    st.header("Raw Filtered Data (Aggregated Long Format)")
    st.dataframe(df_aggregated, use_container_width=True)
    st.caption(f"Showing SUM of Value aggregated across selected outlets: **{', '.join(selected_outlets)}**")
