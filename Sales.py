import streamlit as st
import pandas as pd
import altair as alt

# Set page config
st.set_page_config(page_title="Food Sales Dashboard", layout="wide")

# -----------------------------
# URLs to Google Sheets (CSV export links)
# -----------------------------

transactions_url = "https://docs.google.com/spreadsheets/d/1G610FKLUj3GVXhslfVGRUrJFjdi5NldYaKvJtKuwiJQ/export?format=csv&gid=20213426"
items_url = "https://docs.google.com/spreadsheets/d/1G610FKLUj3GVXhslfVGRUrJFjdi5NldYaKvJtKuwiJQ/export?format=csv&gid=925974495"
staff_url = "https://docs.google.com/spreadsheets/d/1G610FKLUj3GVXhslfVGRUrJFjdi5NldYaKvJtKuwiJQ/export?format=csv&gid=475012657"

# -----------------------------
# Load data
# -----------------------------
transactions = pd.read_csv(transactions_url)
items = pd.read_csv(items_url)
staff = pd.read_csv(staff_url)
staff = pd.read_csv(staff_url, skiprows=3, usecols=[0, 1])

# Fix column names
items.columns = ['Item', 'Material Cost', 'RRP', 'Mates Rates']

# Parse Timestamp as datetime
transactions["Timestamp"] = pd.to_datetime(transactions["Timestamp"])

# -----------------------------
# Sidebar Filters Strange
# -----------------------------
st.sidebar.header("📅 Date Filter")

min_date = transactions["Timestamp"].min().date()
max_date = transactions["Timestamp"].max().date()

start_date = st.sidebar.date_input("Start Date", min_value=min_date, max_value=max_date, value=min_date)
end_date = st.sidebar.date_input("End Date", min_value=min_date, max_value=max_date, value=max_date)

# Filter by selected date range
mask = (transactions["Timestamp"].dt.date >= start_date) & (transactions["Timestamp"].dt.date <= end_date)
filtered_tx = transactions[mask]

# -----------------------------
# Join with Items Table
# -----------------------------
merge1 = pd.merge(
    filtered_tx,
    items,
    how="left",
    left_on="Food",
    right_on="Item"
)

merged = pd.merge(
    merge1,
    staff,
    how="left",
    left_on="User",
    right_on="Email"
)

# Clean up RRP values (remove $ and commas, convert to float)
merged["RRP"] = merged["RRP"].replace('[\$,]', '', regex=True).astype(float)

# Fix Amount (from transactions)
merged["Amount"] = pd.to_numeric(merged["Amount"], errors="coerce")

# Now safe to multiply
merged["Sales"] = merged["Amount"] * merged["RRP"]

# -----------------------------
# Staff Name Filter in Sidebar
# -----------------------------
staff_names = merged["Staff Name"].dropna().unique()
selected_staff = st.sidebar.multiselect("Select Staff Name(s)", options=staff_names, default=staff_names)

# Filter by selected staff names
filtered_merged = merged[merged["Staff Name"].isin(selected_staff)]

# -----------------------------
# Display Dashboard
# -----------------------------
# Optional: Replace with your logo URL or local path
logo_url = "https://i.ibb.co/20WSrCtq/NqtNyQm.jpg"  # Replace with your actual logo

# First row: Title and logo
col1, col2 = st.columns([4, 1])

with col1:
    st.markdown("## 🐟 Hoodlums Seafood Sales🐟 ")

with col2:
    st.image(logo_url, width=150)

# Second row: Metrics
mcol1, mcol2, mcol3 = st.columns(3)

with mcol1:
    total_sales = filtered_merged["Sales"].sum()
    st.metric("Total Sales (RRP)", f"${total_sales:,.2f}")

with mcol2:
    total_transactions = len(filtered_merged)
    st.metric("Transactions", total_transactions)

with mcol3:
    top_staff = (
        filtered_merged.groupby("Staff Name")["Sales"]
        .sum()
        .sort_values(ascending=False)
        .idxmax()
    )
    top_sales = (
        filtered_merged.groupby("Staff Name")["Sales"]
        .sum()
        .max()
    )
    st.metric("Top Seller", top_staff, f"${top_sales:,.2f}")

st.write("")

st.subheader("Sales by Staff")

# Group, sort, reset index
sales_by_item = (
    filtered_merged.groupby("Staff Name")["Sales"]
    .sum()
    .reset_index()
    .sort_values(by="Sales", ascending=False)
)

# Determine a sensible step (round to nearest 100/500 based on max)
max_sales = sales_by_item["Sales"].max()
tick_step = 100 if max_sales < 2000 else 500

# Horizontal bar chart
chart = alt.Chart(sales_by_item).mark_bar().encode(
    x=alt.X(
        "Sales:Q",
        title="Total Sales",
        axis=alt.Axis(format="$,.0f", tickMinStep=tick_step),
        scale=alt.Scale(domain=[0, max_sales * 1.1])
    ),
    y=alt.Y("Staff Name:N", sort="-x", title="Staff Member"),
    tooltip=["Staff Name", alt.Tooltip("Sales", format="$.2f")]
).properties(height=400)

st.altair_chart(chart, use_container_width=True)

# New Staff summary table
st.subheader("💼 Pay Summary")
staff_summary = (
    filtered_merged.groupby("Staff Name")["Sales"]
    .sum()
    .reset_index()
    .sort_values(by="Sales", ascending=False)
)

staff_summary["Pay"] = staff_summary["Sales"] * 0.30
staff_summary["Sales"] = staff_summary["Sales"].map("${:,.2f}".format)
staff_summary["Pay"] = staff_summary["Pay"].map("${:,.2f}".format)
st.dataframe(staff_summary, use_container_width=True, hide_index=True)

st.subheader("🏆 Profit Margin")

# Clean Material Cost if not already
merged["Material Cost"] = merged["Material Cost"].replace('[\$,]', '', regex=True).astype(float)

# Calculate per-row profit
merged["Profit"] = (merged["RRP"] - merged["Material Cost"]) * merged["Amount"]

# Group by item and sum total profit and quantity sold
profit_by_item = (
    merged.groupby("Item")[["Profit", "Amount"]]
    .sum()
    .reset_index()
    .sort_values(by="Profit", ascending=False)
)

# Limit to top 10 for readability (optional)
top_profit_items = profit_by_item.head(10)

# Altair chart
profit_chart = alt.Chart(top_profit_items).mark_bar().encode(
    x=alt.X("Profit:Q", title="Total Profit", axis=alt.Axis(format="$,.0f")),
    y=alt.Y("Item:N", sort="-x", title="Item"),
    tooltip=[
        alt.Tooltip("Item", title="Item"),
        alt.Tooltip("Amount", title="Qty Sold"),
        alt.Tooltip("Profit", title="Total Profit", format="$.2f")
    ]
).properties(height=400)

st.altair_chart(profit_chart, use_container_width=True)

st.subheader("📊 Top 10 Customers")

# Group, sum, sort sales by customer
sales_by_customer = (
    filtered_merged.groupby("Customer")["Sales"]
    .sum()
    .reset_index()
    .sort_values(by="Sales", ascending=False)
    .head(10)  # Limit to top 10
)

max_sales_customer = sales_by_customer["Sales"].max()
tick_step_customer = 100 if max_sales_customer < 2000 else 500

# Horizontal bar chart
customer_chart = alt.Chart(sales_by_customer).mark_bar().encode(
    x=alt.X(
        "Sales:Q",
        title="Total Sales",
        axis=alt.Axis(format="$,.0f", tickMinStep=tick_step_customer),
        scale=alt.Scale(domain=[0, max_sales_customer * 1.1])
    ),
    y=alt.Y("Customer:N", sort="-x", title="Customer"),
    tooltip=["Customer", alt.Tooltip("Sales", format="$.2f")]
).properties(height=400)

st.altair_chart(customer_chart, use_container_width=True)

# Select and format columns for display
display_cols = ["Timestamp", "Staff Name", "Food", "Customer", "Sales"]

# Create a copy to avoid SettingWithCopyWarning
display_df = filtered_merged[display_cols].copy()

# Format Sales as dollar strings
display_df["Sales"] = display_df["Sales"].map("${:,.2f}".format)

st.subheader("📋 Transactions")
st.dataframe(display_df)