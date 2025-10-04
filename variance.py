import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- 0. Configuration and Data Mapping ---

# Dictionary mapping Outlet Codes (to be shown in filter) to Excel file names
OUTLET_FILES = {
    "AML": "AML.xlsx",
    "AZT": "AZT.xlsx", 
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
ALL_OUTLETS = list(OUTLET_FILES.keys())
OUTLET_OPTIONS = ALL_OUTLETS

# Define the order of aging buckets
AGING_BUCKETS = ['61-90', '91-120', '121-180', '181-360']


# --- 1. Data Preparation (Loading a Single File) ---

@st.cache_data
def load_data(selected_outlet):
    """
    Loads data for the single selected outlet.
    """
    if not selected_outlet:
        return pd.DataFrame()
    
    file_name = OUTLET_FILES.get(selected_outlet)
    if not file_name:
        st.error(f"Error: No file mapping found for outlet '{selected_outlet}'.")
        return pd.DataFrame()
    
    try:
        # Read the Excel file
        df = pd.read_excel(file_name)
        # Add a new column to identify the outlet
        df['Outlet'] = selected_outlet
        return df
    except FileNotFoundError:
        st.error(f"🚨 Error: File '{file_name}' for Outlet '{selected_outlet}' not found. Please ensure the file is in the same directory.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"An error occurred while reading file '{file_name}': {e}")
        return pd.DataFrame()


# --- 2. Data Transformation (Melting and Merging) ---

@st.cache_data
def transform_data(df):
    """
    Melt Qty and Value separately and then merge them back together 
    on Outlet, Category, and Aging Bucket.
    """
    if df.empty:
        return pd.DataFrame()

    # 1. Melt Qty columns
    df_qty_long = df.melt(
        id_vars=['Outlet', 'Category'],
        value_vars=[col for col in df.columns if 'Qty' in col],
        var_name='Aging Bucket_Qty',
        value_name='Qty'
    )
    df_qty_long['Aging Bucket'] = df_qty_long['Aging Bucket_Qty'].str.replace(' Aging Qty', '', regex=False)
    df_qty_long = df_qty_long[['Outlet', 'Category', 'Aging Bucket', 'Qty']]

    # 2. Melt Value columns
    df_value_long = df.melt(
        id_vars=['Outlet', 'Category'],
        value_vars=[col for col in df.columns if 'Value' in col],
        var_name='Aging Bucket_Value',
        value_name='Value'
    )
    df_value_long['Aging Bucket'] = df_value_long['Aging Bucket_Value'].str.replace(' Aging Value', '', regex=False)
    df_value_long = df_value_long[['Outlet', 'Category', 'Aging Bucket', 'Value']]
    
    # 3. Merge Qty and Value together
    df_combined_long = pd.merge(df_qty_long, df_value_long, on=['Outlet', 'Category', 'Aging Bucket'])

    # Define a custom order for the aging buckets
    df_combined_long['Aging Bucket'] = pd.Categorical(df_combined_long['Aging Bucket'], categories=AGING_BUCKETS, ordered=True)
    
    # Fill NaN values introduced by merging or loading with 0 for metrics
    df_combined_long['Qty'] = df_combined_long['Qty'].fillna(0)
    df_combined_long['Value'] = df_combined_long['Value'].fillna(0)

    return df_combined_long


# --- 3. Streamlit App Layout and Logic ---

st.set_page_config(layout="wide", page_title="Single-Outlet Inventory Aging Analysis", initial_sidebar_state="expanded")

st.title("📊 Inventory Aging Analysis by Single Outlet")

# --- 4. Sidebar Filters ---
st.sidebar.header("Filter & View Options")

# 1. Outlet Selection Filter
st.sidebar.subheader("Outlet Selection")
selected_outlet = st.sidebar.selectbox(
    "Select an Outlet:",
    options=['--- Select an Outlet ---'] + OUTLET_OPTIONS,
    index=0 
)

# Stop the app if no valid outlet is selected
if selected_outlet == '--- Select an Outlet ---':
    st.info("Please select an outlet from the dropdown menu to begin the analysis.")
    st.stop()


# Load and transform data based on the single selected outlet
df_wide_original = load_data(selected_outlet)
df_combined_long = transform_data(df_wide_original.copy())

# Check if data loading or transformation failed
if df_combined_long.empty:
    st.info(f"Data for {selected_outlet} could not be loaded or is empty. Check warnings above.")
    st.stop()
    
st.sidebar.markdown("---")


# 2. Metric Selection Filter (Original)
view_option = st.sidebar.radio(
    "Select Metric to Visualize:",
    ('Aging Quantity (Qty)', 'Aging Value (Value)')
)

# Determine the primary metric for the chart size
if 'Qty' in view_option:
    metric_col = 'Qty'
    title_suffix = 'Quantity'
    hover_format_qty = ',.0f' 
    hover_format_val = ',.2f' 
else:
    metric_col = 'Value'
    title_suffix = 'Value'
    hover_format_qty = ',.0f' 
    hover_format_val = ',.2f'

df_plot = df_combined_long
all_categories = df_plot['Category'].unique().tolist()

st.sidebar.markdown("---")

# 3. Category Selection Filter (Original)
st.sidebar.subheader("Category Selection")
select_all_categories = st.sidebar.checkbox("Select All Categories", value=True, key='category_all')

if select_all_categories:
    selected_categories = all_categories
    st.sidebar.multiselect(
        "Individual Categories:",
        options=all_categories,
        default=all_categories,
        disabled=True,
        key='category_list_disabled'
    )
else:
    selected_categories = st.sidebar.multiselect(
        "Individual Categories:",
        options=all_categories,
        default=[],
        key='category_list_enabled' 
    )
    if not selected_categories:
        st.warning("No categories selected. Please check 'Select All' or choose categories individually.")
        st.stop()


# Apply filters
df_filtered_long = df_plot[df_plot['Category'].isin(selected_categories)].copy() 
df_filtered_wide = df_wide_original[df_wide_original['Category'].isin(selected_categories)].copy()


# --- 4.5. Summary Metrics (UPDATED TO REMOVE $ SIGN) ---

# Calculate totals per Aging Bucket
summary_df = df_filtered_long.groupby('Aging Bucket')[['Value', 'Qty']].sum().reindex(AGING_BUCKETS).fillna(0)
grand_total_value = summary_df['Value'].sum()
grand_total_qty = summary_df['Qty'].sum()


st.markdown(f"### Current View Summary for Outlet: {selected_outlet}")

# Row 1: Grand Totals
col_title, col_val_total, col_qty_total = st.columns([1.5, 1, 1])

with col_title:
    st.subheader("Inventory Grand Totals")

with col_val_total:
    st.metric(
        label="Total Aged Value",
        value=f"{grand_total_value:,.2f}" # REMOVED $
    )

with col_qty_total:
    st.metric(
        label="Total Aged Quantity",
        value=f"{grand_total_qty:,.0f} Units"
    )

st.markdown("---")

# Row 2: Bucket-Wise Breakdown
st.subheader("Value and Quantity by Aging Bucket")

# Create columns for the bucket breakdown 
cols_bucket = st.columns(4) 

for i, bucket in enumerate(AGING_BUCKETS):
    with cols_bucket[i]:
        st.markdown(f"**{bucket} Days**")
        bucket_value = summary_df.loc[bucket, 'Value']
        bucket_qty = summary_df.loc[bucket, 'Qty']
        
        # Display Value - REMOVED $
        st.markdown(f"💰 Value: **{bucket_value:,.2f}**")
        
        # Display Quantity
        st.markdown(f"📦 Qty: **{bucket_qty:,.0f}**")
        
st.markdown("---")


# --- 5. Visualization Functions ---

def plot_horizontal_bar(df, metric_col, bucket, title_suffix, color):
    """Creates a horizontal bar chart for a single aging bucket with dual tooltips."""
    
    df_bucket = df[(df['Aging Bucket'] == bucket) & (df[metric_col] > 0)]
    
    if df_bucket.empty:
        st.info(f"No {title_suffix} data found for the {bucket} bucket in selected categories.")
        return

    df_bucket = df_bucket.sort_values(by=metric_col, ascending=True)

    fig = px.bar(
        df_bucket,
        x=metric_col,
        y='Category',
        orientation='h', 
        title=f'Aging in {bucket} Days (Primary Metric: {title_suffix})',
        labels={metric_col: f'{title_suffix}', 'Category': ''},
        color_discrete_sequence=[color],
        hover_data={'Qty': False, 'Value': False, metric_col: False, 'Category': False}
    )
    fig.update_layout(height=600, showlegend=False)
    
    # Custom Hover Template - REMOVED $ from the Value line
    custom_hover_template = (
        '<b>Category:</b> %{y}<br>' +
        f'<b>Aging Qty:</b> %{{customdata[0]:{hover_format_qty}}}<br>' +
        f'<b>Aging Value:</b> %{{customdata[1]:{hover_format_val}}}<br>' +
        '<extra></extra>' 
    )
    
    fig.update_traces(customdata=df_bucket[['Qty', 'Value']], 
                      hovertemplate=custom_hover_template)
    
    st.plotly_chart(fig, use_container_width=True)


def plot_treemap(df, metric_col, title_suffix, outlet_name):
    """Creates a treemap to show hierarchical contribution by Category and Aging Bucket."""
    df_filtered = df[df[metric_col] > 0]
    if df_filtered.empty: return st.warning("No data to display in the Treemap.")
        
    path_list = [px.Constant(f"Outlet: {outlet_name}"), 'Category', 'Aging Bucket']
        
    fig = px.treemap(
        df_filtered,
        path=path_list,
        values=metric_col,
        title=f'Hierarchical Aging Contribution for Outlet {outlet_name} ({title_suffix})',
        color=metric_col,
        color_continuous_scale='Reds',
        hover_data=['Category', 'Aging Bucket', 'Qty', 'Value'] 
    )
    fig.update_layout(margin=dict(t=50, l=25, r=25, b=25))
    st.plotly_chart(fig, use_container_width=True)

# --- 6. Main Content Tabs ---
tab1, tab2, tab3 = st.tabs(["📈 Aging Distribution (Days)", "🌳 Treemap", "📋 Original Table Data"])

if df_filtered_long.empty:
    st.info("No data to display for the selected outlet and categories.")
else:
    with tab1:
        st.header(f"Aging Distribution Analysis: {title_suffix}")
        st.caption("Hover over any bar to see the Quantity and Value for that category and time bucket.")
        st.markdown("---")

        bucket_colors = px.colors.qualitative.Bold 

        col_charts_1, col_charts_2 = st.columns(2)
        
        with col_charts_1:
            plot_horizontal_bar(df_filtered_long, metric_col, AGING_BUCKETS[0], title_suffix, bucket_colors[0])
            st.markdown("---")
            plot_horizontal_bar(df_filtered_long, metric_col, AGING_BUCKETS[1], title_suffix, bucket_colors[1])

        with col_charts_2:
            plot_horizontal_bar(df_filtered_long, metric_col, AGING_BUCKETS[2], title_suffix, bucket_colors[2])
            st.markdown("---")
            plot_horizontal_bar(df_filtered_long, metric_col, AGING_BUCKETS[3], title_suffix, bucket_colors[3])

    with tab2:
        st.header(f"Hierarchical Aging Contribution: {title_suffix}")
        plot_treemap(df_filtered_long, metric_col, title_suffix, selected_outlet)
        st.caption("The Treemap shows the breakdown: **Category** $\\rightarrow$ **Aging Bucket**.")

    with tab3:
        st.header(f"Original Data Table (Filtered Wide Format for Outlet: {selected_outlet})")
        st.caption("This table displays the raw data for the selected outlet, filtered by your Category Selection.")
        st.dataframe(df_filtered_wide.drop(columns=['Outlet'], errors='ignore'), use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.caption("App built for single-outlet inventory aging analysis.")
