import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- 0. Configuration and Data Mapping ---

# Dictionary mapping Outlet Codes (to be shown in filter) to Excel file names
OUTLET_FILES = {
    "AML": "AML.xlsx",
    "ATT": "AZT.xlsx", 
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


# --- 1. Data Preparation (Loading Multiple Files) ---

@st.cache_data
def load_data(selected_outlets):
    """
    Loads data from the Excel files corresponding to the selected outlets,
    adds an 'Outlet' column to each, and concatenates them.
    """
    if not selected_outlets:
        return pd.DataFrame()
        
    all_dfs = []
    
    for outlet_code in selected_outlets:
        file_name = OUTLET_FILES.get(outlet_code)
        if file_name:
            try:
                # Read the Excel file
                df = pd.read_excel(file_name)
                # Add a new column to identify the outlet
                df['Outlet'] = outlet_code
                all_dfs.append(df)
            except FileNotFoundError:
                st.warning(f"🚨 Warning: File '{file_name}' for Outlet '{outlet_code}' not found. Skipping.")
            except Exception as e:
                st.error(f"An error occurred while reading file '{file_name}': {e}")

    if all_dfs:
        # Concatenate all loaded dataframes
        combined_df = pd.concat(all_dfs, ignore_index=True)
        return combined_df
    else:
        st.error("No valid data files were loaded from the selected outlets.")
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
    age_order = ['61-90', '91-120', '121-180', '181-360']
    df_combined_long['Aging Bucket'] = pd.Categorical(df_combined_long['Aging Bucket'], categories=age_order, ordered=True)
    
    # Fill NaN values introduced by merging or loading with 0 for metrics
    df_combined_long['Qty'] = df_combined_long['Qty'].fillna(0)
    df_combined_long['Value'] = df_combined_long['Value'].fillna(0)

    return df_combined_long


# --- 3. Streamlit App Layout and Logic ---

st.set_page_config(layout="wide", page_title="Multi-Outlet Inventory Aging Analysis", initial_sidebar_state="expanded")

st.title("📊 Multi-Outlet Inventory Aging Analysis")
st.markdown("Visualizing the distribution of Aged Inventory across specific time buckets and outlets.")

# --- 4. Sidebar Filters ---
st.sidebar.header("Filter & View Options")

# 1. Outlet Selection Filter (NEW)
st.sidebar.subheader("Outlet Selection")
select_all_outlets = st.sidebar.checkbox("Select All Outlets", value=True, key='outlet_all')

if select_all_outlets:
    selected_outlets = ALL_OUTLETS
    st.sidebar.multiselect(
        "Individual Outlets:",
        options=ALL_OUTLETS,
        default=ALL_OUTLETS,
        disabled=True,
        key='outlet_list_disabled'
    )
else:
    selected_outlets = st.sidebar.multiselect(
        "Individual Outlets:",
        options=ALL_OUTLETS,
        default=ALL_OUTLETS[:3], # Default to a few for testing
        key='outlet_list_enabled' 
    )

if not selected_outlets:
    st.warning("Please select at least one outlet to load data.")
    st.stop()


# Load and transform data based on the selected outlets
df_wide_original = load_data(selected_outlets)
df_combined_long = transform_data(df_wide_original.copy())

# Check if data loading or transformation failed
if df_combined_long.empty:
    st.info("Data loading failed or returned an empty set. Check warnings above.")
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
df_filtered_long = df_plot[
    (df_plot['Category'].isin(selected_categories)) &
    (df_plot['Outlet'].isin(selected_outlets))
]

# Note: Filtering the wide data (tab3) is more complex with multi-outlet, 
# so we'll filter the combined_wide data for display.
df_filtered_wide = df_wide_original[
    (df_wide_original['Category'].isin(selected_categories)) &
    (df_wide_original['Outlet'].isin(selected_outlets))
]


# --- 5. Visualization Functions ---

# ... (plot_horizontal_bar and plot_treemap functions remain the same but now use the filtered data) ...

def plot_horizontal_bar(df, metric_col, bucket, title_suffix, color):
    """Creates a horizontal bar chart for a single aging bucket with dual tooltips."""
    # Group data by Category (and Outlet if Treemap is used)
    # For the bar chart, we aggregate data across all selected outlets
    df_bucket = df[(df['Aging Bucket'] == bucket) & (df[metric_col] > 0)]
    df_grouped = df_bucket.groupby('Category')[['Qty', 'Value']].sum().reset_index()
    df_grouped.rename(columns={'Qty': 'Qty', 'Value': 'Value'}, inplace=True)
    df_grouped[metric_col] = df_grouped[metric_col] # Keep the selected metric column name consistent
    
    if df_grouped.empty:
        st.info(f"No {title_suffix} data found for the {bucket} bucket in selected categories/outlets.")
        return

    # Sort categories by the metric value (descending)
    df_grouped = df_grouped.sort_values(by=metric_col, ascending=True)

    fig = px.bar(
        df_grouped,
        x=metric_col,
        y='Category',
        orientation='h', 
        title=f'Aging in {bucket} Days (Primary Metric: {title_suffix})',
        labels={metric_col: f'{title_suffix}', 'Category': ''},
        color_discrete_sequence=[color],
        hover_data={'Qty': False, 'Value': False, metric_col: False, 'Category': False}
    )
    fig.update_layout(height=600, showlegend=False)
    
    # Custom Hover Template
    custom_hover_template = (
        '<b>Category:</b> %{y}<br>' +
        f'<b>Aging Qty:</b> %{{customdata[0]:{hover_format_qty}}}<br>' +
        f'<b>Aging Value:</b> %{{customdata[1]:{hover_format_val}}}<br>' +
        '<extra></extra>' 
    )
    
    # Pass the Qty and Value columns as customdata
    fig.update_traces(customdata=df_grouped[['Qty', 'Value']], 
                      hovertemplate=custom_hover_template)
    
    st.plotly_chart(fig, use_container_width=True)


def plot_treemap(df, metric_col, title_suffix):
    """Creates a treemap to show hierarchical contribution by Outlet, then Category."""
    # Filter out 0 values for a meaningful treemap
    df_filtered = df[df[metric_col] > 0]
    if df_filtered.empty: return st.warning("No data to display in the Treemap.")
        
    fig = px.treemap(
        df_filtered,
        # Now use Outlet as the top level, followed by Category, then Aging Bucket
        path=[px.Constant("All Selected Inventory"), 'Outlet', 'Category', 'Aging Bucket'],
        values=metric_col,
        title=f'Hierarchical Aging Contribution by Outlet/Category ({title_suffix})',
        color=metric_col,
        color_continuous_scale='Reds',
        hover_data=['Outlet', 'Category', 'Aging Bucket', 'Qty', 'Value'] # Show both metrics here too
    )
    fig.update_layout(margin=dict(t=50, l=25, r=25, b=25))
    st.plotly_chart(fig, use_container_width=True)

# --- 6. Main Content Tabs ---
tab1, tab2, tab3 = st.tabs(["📈 Aging Distribution (Days)", "🌳 Treemap", "📋 Original Table Data"])

if df_filtered_long.empty:
    st.info("Please select outlets and categories using the sidebar filters to view the data.")
else:
    with tab1:
        st.header(f"Aging Distribution Analysis: {title_suffix}")
        st.caption("Data is aggregated across all selected outlets. Hover over any bar to see **both** the total Aging Quantity and Aging Value.")
        st.markdown("---")

        # Define buckets and colors
        aging_buckets = ['61-90', '91-120', '121-180', '181-360']
        bucket_colors = px.colors.qualitative.Bold 

        # Create two columns for a neat layout of the four charts
        col_charts_1, col_charts_2 = st.columns(2)
        
        # Plot the four separate horizontal bar charts
        with col_charts_1:
            plot_horizontal_bar(df_filtered_long, metric_col, aging_buckets[0], title_suffix, bucket_colors[0])
            st.markdown("---")
            plot_horizontal_bar(df_filtered_long, metric_col, aging_buckets[1], title_suffix, bucket_colors[1])

        with col_charts_2:
            plot_horizontal_bar(df_filtered_long, metric_col, aging_buckets[2], title_suffix, bucket_colors[2])
            st.markdown("---")
            plot_horizontal_bar(df_filtered_long, metric_col, aging_buckets[3], title_suffix, bucket_colors[3])

    with tab2:
        st.header(f"Hierarchical Aging Contribution: {title_suffix}")
        plot_treemap(df_filtered_long, metric_col, title_suffix)
        st.caption("The Treemap shows the hierarchical breakdown: **Outlet** $\\rightarrow$ **Category** $\\rightarrow$ **Aging Bucket**.")

    with tab3:
        st.header("Original Data Table (Filtered Wide Format)")
        st.caption("This table displays the raw data, including the **Outlet** column, filtered by your selections.")
        st.dataframe(df_filtered_wide, use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.caption("App built for multi-outlet inventory aging analysis.")
