import streamlit as st
import pandas as pd
from datetime import datetime
from database import (
    get_menu_items, get_sales, log_daily_sales,
    get_revenue_and_cost, get_inventory
)


def render(global_date=None, global_date_str=None):
    st.title("💰 Daily Sales")

    with st.expander("ℹ️ **What is this page?** (click to read)", expanded=False):
        st.markdown(
            """
            This is where you **record what you sold each day**.

            **Log Sales tab:**
            - Pick a date, then enter how many of each menu item you sold
            - Hit "Log Sales" and the app will:
              1. Save the sales record
              2. Calculate your revenue and profit for that day
              3. **Automatically deduct ingredients** from your stock (based on each item's recipe)
              4. Warn you if any ingredient is running low or ran out

            **Sales History tab:**
            - Browse all past sales data with date filters
            - See total revenue, cost, profit, and items sold for any date range

            **Pre-loaded data:** The app already has sales data for March 1-31 loaded from the
            sample dataset. You'll notice that **weekends (Saturday & Sunday) have higher sales** –
            this is intentional to show how the AI can detect patterns and spikes.

            If you log sales for a date that already has data, the new entries will be added
            on top (not replaced). This is useful if you forgot to log some items.
            """
        )

    tab1, tab2 = st.tabs(["📝 Log Sales", "📊 Sales History"])

    # ─── Log Sales ───
    with tab1:
        st.info(
            "ℹ️ Enter how many of each item you sold today. "
            "The app will automatically deduct ingredients from your stock.",
            icon="ℹ️",
        )

        col_date, col_spacer = st.columns([1, 3])
        with col_date:
            sales_date = st.date_input(
                "Sales date",
                value=datetime(2026, 3, 20).date(),
                help="Which day are you logging sales for?",
            )

        day_name = sales_date.strftime("%A")
        st.caption(f"📅 {day_name}, {sales_date.strftime('%B %d, %Y')}")

        # Check if sales already exist for this date
        sales_date_str = sales_date.strftime("%Y-%m-%d")
        existing = get_sales(sales_date_str, sales_date_str)
        if existing:
            st.warning(
                f"Sales for {sales_date_str} ({day_name}) are already logged. "
                f"Adding more will create additional entries."
            )

        menu_items = get_menu_items(active_only=True)
        if not menu_items:
            st.error("No active menu items. Add items to your menu first!")
            return

        # Group by category
        categories = {}
        for item in menu_items:
            cat = item["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)

        with st.form("log_sales"):
            items_sold = []

            for cat_name, cat_items in categories.items():
                st.markdown(f"**{cat_name}**")
                cols = st.columns(min(len(cat_items), 3))
                for i, item in enumerate(cat_items):
                    with cols[i % 3]:
                        qty = st.number_input(
                            f"{item['name']} (₹{item['sell_price']:.0f})",
                            min_value=0, value=0, step=1,
                            key=f"sale_{item['id']}",
                            help=f"How many {item['name']} did you sell?",
                        )
                        if qty > 0:
                            items_sold.append((item["id"], qty))

            submitted = st.form_submit_button("💰 Log Sales", use_container_width=True)

            if submitted:
                if not items_sold:
                    st.error("You haven't entered any sales. Enter at least one item's quantity.")
                else:
                    success, warnings = log_daily_sales(sales_date_str, day_name, items_sold)
                    if success:
                        # Calculate quick summary
                        total_qty = sum(q for _, q in items_sold)
                        st.success(f"Logged {total_qty} items sold on {day_name}! Stock has been updated automatically.")

                        if warnings:
                            st.markdown("**⚠️ Stock Warnings:**")
                            for w in warnings:
                                st.warning(w)
                            st.caption("Go to Stock & Inventory to restock these items")

                        st.rerun()

    # ─── Sales History ───
    with tab2:
        st.info("ℹ️ Browse past sales data. Use the date range to filter.", icon="ℹ️")

        col1, col2 = st.columns(2)
        with col1:
            start = st.date_input(
                "From",
                value=datetime(2026, 3, 1).date(),
                help="Start date for the sales report",
            )
        with col2:
            end = st.date_input(
                "To",
                value=datetime(2026, 3, 20).date(),
                help="End date for the sales report",
            )

        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")

        sales = get_sales(start_str, end_str)

        if not sales:
            st.info(f"No sales found between {start_str} and {end_str}.")
            return

        # Summary cards
        revenue_data = get_revenue_and_cost(start_str, end_str)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Revenue", f"₹{revenue_data['total_revenue']:,.0f}")
        with col2:
            st.metric("Total Cost", f"₹{revenue_data['total_cost']:,.0f}")
        with col3:
            st.metric("Profit", f"₹{revenue_data['total_profit']:,.0f}")
        with col4:
            total_items = sum(s["quantity_sold"] for s in sales)
            st.metric("Items Sold", f"{total_items:,}")

        # Sales table
        st.markdown("---")
        df = pd.DataFrame(sales)
        df_display = df[["date", "item_name", "category", "quantity_sold", "sell_price"]].copy()
        df_display["revenue"] = df_display["quantity_sold"] * df_display["sell_price"]
        df_display.columns = ["Date", "Item", "Category", "Qty Sold", "Price (₹)", "Revenue (₹)"]

        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
        )
        st.caption(f"Showing {len(df_display)} sale entries")
