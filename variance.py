import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# --- Page Config ---
st.set_page_config(page_title="Stock Variance Dashboard", layout="wide")

# --- Outlets & Files ---
outlets_files = {
    "Safa Oud Metha": "SAO Stock Comparison On 15-Sep-2025 1 (1).Xlsx",
    "Azhar GT": "AZT Stock.Xlsx",
    "Superstore": "MSS Stock.Xlsx",
    "Liwan": "LWN Stock.Xlsx",
    "Blue Pearl": "BPS Stock.Xlsx",
    "Sahat": "SAD Stock.Xlsx",
    "TayTay": "TTD Stock Comparison On 29-Sep-2025 2.Xlsx"  # Added TayTay
}

# --- Passwords for each outlet ---
outlet_passwords = {
    "Safa Oud Metha": "123",
    "Azhar GT": "1234",
    "Superstore": "12345",
    "Liwan": "123456",
    "Blue Pearl": "1234567",
    "Sahat": "12345678",
    "TayTay": "123456789"  # Password for TayTay
}

# --- Sidebar: Select Outlet ---
st.sidebar.header("🔐 Authentication")
selected_outlet = st.sidebar.selectbox("Outlet", list(outlets_files.keys()))

# Reset authentication when outlet changes
if "last_outlet" not in st.session_state or st.session_state.last_outlet != selected_outlet:
    st.session_state.authenticated = False
    st.session_state.last_outlet = selected_outlet

# --- Login form ---
with st.sidebar.form("login_form"):
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_btn = st.form_submit_button("Login")

if login_btn:
    if username == "almadina" and password == outlet_passwords[selected_outlet]:
        st.session_state.authenticated = True
        st.success(f"✅ Login successful for {selected_outlet}")
    else:
        st.session_state.authenticated = False
        st.error("❌ Invalid username or password")

# Logout option
if st.session_state.get("authenticated"):
    if st.sidebar.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.rerun()

# If not logged in, stop execution
if not st.session_state.get("authenticated", False):
    st.warning(f"Please login to view data for **{selected_outlet}**")
    st.stop()

# --- Load Data Function ---
@st.cache_data
def load_data(file_path):
    df = pd.read_excel(file_path)
    df.columns = df.columns.str.strip()

    # Calculate Difference & Values
    if 'Diff Stock' not in df.columns:
        df['Diff Stock'] = df['Phys Stock'] - df['Book Stock']

    cost_col = "Cost Price"
    if cost_col in df.columns:
        df['Book Value'] = df['Book Stock'] * df[cost_col]
        df['Phys Value'] = df['Phys Stock'] * df[cost_col]
        df['Diff Value'] = df['Diff Stock'] * df[cost_col]

    return df

# --- Load the selected outlet's dataset ---
file_path = outlets_files[selected_outlet]
if not os.path.exists(file_path):
    st.error(f"File for {selected_outlet} not found: {file_path}")
    st.stop()

df = load_data(file_path)

# --- Sidebar: Category Filter ---
st.sidebar.header("Filters")
categories = df['Category'].unique().tolist()
selected_category = st.sidebar.selectbox("Select Category", ["All"] + categories)

# --- Filtered Data ---
filtered_df = df.copy()
if selected_category != "All":
    filtered_df = filtered_df[filtered_df['Category'] == selected_category]

# --- Summary Metrics ---
total_book_stock = filtered_df['Book Stock'].sum()
total_phys_stock = filtered_df['Phys Stock'].sum()
total_diff_stock = filtered_df['Diff Stock'].sum()

total_book_value = filtered_df['Book Value'].sum()
total_phys_value = filtered_df['Phys Value'].sum()
total_diff_value = filtered_df['Diff Value'].sum()

stock_variance_pct = (
    (total_diff_stock / total_book_stock) * 100 if total_book_stock != 0 else 0
)

# --- Dashboard Title ---
st.title(f"📊 Stock Variance Dashboard - {selected_outlet}")

# --- Summary Section ---
st.markdown("### 📊 Stock Summary")
col1, col2, col3, col4 = st.columns(4, gap="large")

with col1:
    st.markdown(
        f"<h5>System Stock</h5>"
        f"<p style='font-size:28px; font-weight:bold;'>{total_book_stock:,.0f}</p>"
        f"<p style='font-size:14px; color:gray;'>AED {total_book_value:,.0f}</p>",
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        f"<h5>Physical Stock</h5>"
        f"<p style='font-size:28px; font-weight:bold;'>{total_phys_stock:,.0f}</p>"
        f"<p style='font-size:14px; color:gray;'>AED {total_phys_value:,.0f}</p>",
        unsafe_allow_html=True
    )

with col3:
    st.markdown(
        f"<h5>Stock Difference</h5>"
        f"<p style='font-size:28px; font-weight:bold;'>{total_diff_stock:,.0f}</p>"
        f"<p style='font-size:14px; color:gray;'>AED {total_diff_value:,.0f}</p>",
        unsafe_allow_html=True
    )

with col4:
    st.markdown(
        f"<h5>Stock Variance %</h5>"
        f"<p style='font-size:28px; font-weight:bold;'>{stock_variance_pct:.2f} %</p>",
        unsafe_allow_html=True
    )

st.markdown("---")

# --- Top 30 by Quantity ---
filtered_df['Abs Diff'] = filtered_df['Diff Stock'].abs()
top_30_qty = filtered_df.sort_values('Abs Diff', ascending=False).head(30)

st.subheader("Top 30 Items: Quantity vs Value")
fig_qty = go.Figure()
fig_qty.add_trace(go.Bar(
    y=top_30_qty['Item Name'],
    x=top_30_qty['Diff Stock'],
    name='Stock Difference (Qty)',
    orientation='h',
    marker_color='steelblue',
    customdata=top_30_qty[['Category','Item No','Barcode','Book Stock','Phys Stock','Diff Value']],
    hovertemplate=(
        "<b>%{y}</b><br>Category: %{customdata[0]}<br>Item No: %{customdata[1]}<br>"
        "Barcode: %{customdata[2]}<br>Book Stock: %{customdata[3]}<br>Phys Stock: %{customdata[4]}<br>"
        "Stock Diff: %{x}<br>Stock Diff Value: AED %{customdata[5]:,.0f}<extra></extra>"
    )
))
fig_qty.add_trace(go.Bar(
    y=top_30_qty['Item Name'],
    x=top_30_qty['Diff Value'],
    name='Stock Difference Value (AED)',
    orientation='h',
    marker_color='orange',
    customdata=top_30_qty[['Category','Item No','Barcode','Book Stock','Phys Stock','Diff Stock']],
    hovertemplate=(
        "<b>%{y}</b><br>Category: %{customdata[0]}<br>Item No: %{customdata[1]}<br>"
        "Barcode: %{customdata[2]}<br>Book Stock: %{customdata[3]}<br>Phys Stock: %{customdata[4]}<br>"
        "Stock Diff: %{customdata[5]}<br>Stock Diff Value: AED %{x:,.0f}<extra></extra>"
    )
))
fig_qty.update_layout(barmode='group', yaxis=dict(autorange='reversed'), xaxis_title="Quantity / Value",
                      height=800, legend_title="Metrics", margin=dict(t=20, b=20))
st.plotly_chart(fig_qty, use_container_width=True)

# --- Top 30 Table by Quantity ---
st.subheader("📄 Top 30 Items Details (Quantity Priority)")
key_columns = ['Category', 'Item Name', 'Item No', 'Barcode', 'Book Stock', 'Phys Stock', 'Diff Stock', 'Book Value', 'Phys Value', 'Diff Value']
available_columns = [col for col in key_columns if col in top_30_qty.columns]
st.dataframe(top_30_qty[available_columns])

st.markdown("---")

# --- Top 30 by Value ---
top_30_value = filtered_df.sort_values('Diff Value', ascending=False).head(30)
st.subheader("Top 30 Items: Value Priority")
fig_val = go.Figure()
fig_val.add_trace(go.Bar(
    y=top_30_value['Item Name'],
    x=top_30_value['Diff Stock'],
    name='Stock Difference (Qty)',
    orientation='h',
    marker_color='steelblue',
    customdata=top_30_value[['Category','Item No','Barcode','Book Stock','Phys Stock','Diff Value']],
    hovertemplate=(
        "<b>%{y}</b><br>Category: %{customdata[0]}<br>Item No: %{customdata[1]}<br>"
        "Barcode: %{customdata[2]}<br>Book Stock: %{customdata[3]}<br>Phys Stock: %{customdata[4]}<br>"
        "Stock Diff: %{x}<br>Stock Diff Value: AED %{customdata[5]:,.0f}<extra></extra>"
    )
))
fig_val.add_trace(go.Bar(
    y=top_30_value['Item Name'],
    x=top_30_value['Diff Value'],
    name='Stock Difference Value (AED)',
    orientation='h',
    marker_color='orange',
    customdata=top_30_value[['Category','Item No','Barcode','Book Stock','Phys Stock','Diff Stock']],
    hovertemplate=(
        "<b>%{y}</b><br>Category: %{customdata[0]}<br>Item No: %{customdata[1]}<br>"
        "Barcode: %{customdata[2]}<br>Book Stock: %{customdata[3]}<br>Phys Stock: %{customdata[4]}<br>"
        "Stock Diff: %{customdata[5]}<br>Stock Diff Value: AED %{x:,.0f}<extra></extra>"
    )
))
fig_val.update_layout(barmode='group', yaxis=dict(autorange='reversed'), xaxis_title="Quantity / Value",
                      height=800, legend_title="Metrics", margin=dict(t=20, b=20))
st.plotly_chart(fig_val, use_container_width=True)

# --- Top 30 Table by Value ---
st.subheader("📄 Top 30 Items Details (Value Priority)")
available_columns_value = [col for col in key_columns if col in top_30_value.columns]
st.dataframe(top_30_value[available_columns_value])

st.markdown("---")

# --- Remaining Items Table ---
st.subheader("📄 All Remaining Items by Category")
remaining_df = filtered_df.drop(top_30_qty.index.union(top_30_value.index))
st.dataframe(remaining_df[available_columns].sort_values(['Category','Diff Stock'], ascending=[True, False]))
