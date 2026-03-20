import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from database import (
    get_menu_items, get_inventory, get_revenue_and_cost,
    get_expiring_items, get_expired_items, get_low_stock_items,
    get_daily_sales_summary
)


def render(view_date=None, view_date_str=None):
    st.title("📊 Dashboard")

    with st.expander("ℹ️ **What is this page?** (click to read)", expanded=False):
        st.markdown(
            """
            This is your **cafe's control center**. It gives you a quick snapshot of how things are going.

            **What you see here:**
            - **Today's Revenue & Profit** – how much money came in and how much you actually earned after ingredient costs
            - **Expiring Soon** – ingredients that will go bad within the next 7 days (so you can use them up or create offers)
            - **Low Stock** – ingredients that are running very low and need to be restocked
            - **Revenue Trend** – a chart showing your daily sales over the month (orange dotted lines = weekends)
            - **Top 5 Sellers** – your best-performing menu items

            **Use the date picker in the sidebar** to change which date you're viewing.
            All numbers on this page are calculated up to that date.

            **This page is read-only** – it just shows you information. To make changes, use the other pages
            (Menu, Stock, Sales).
            """
        )

    if view_date is None:
        view_date = datetime(2026, 3, 20).date()
        view_date_str = "2026-03-20"

    st.markdown("---")

    # ─── Top Metrics ───
    revenue_data = get_revenue_and_cost("2026-03-01", view_date_str)
    today_data = get_revenue_and_cost(view_date_str, view_date_str)

    # Previous day for comparison
    prev_date = (view_date - timedelta(days=1)).strftime("%Y-%m-%d")
    prev_data = get_revenue_and_cost(prev_date, prev_date)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        today_rev = today_data["total_revenue"]
        prev_rev = prev_data["total_revenue"]
        delta = today_rev - prev_rev if prev_rev > 0 else 0
        st.metric(
            "Today's Revenue",
            f"₹{today_rev:,.0f}",
            delta=f"₹{delta:,.0f} vs yesterday" if prev_rev > 0 else None,
            help="Total money earned from sales today",
        )

    with col2:
        today_profit = today_data["total_profit"]
        prev_profit = prev_data["total_profit"]
        delta_p = today_profit - prev_profit if prev_profit > 0 else 0
        st.metric(
            "Today's Profit",
            f"₹{today_profit:,.0f}",
            delta=f"₹{delta_p:,.0f} vs yesterday" if prev_profit > 0 else None,
            help="Revenue minus ingredient costs",
        )

    with col3:
        expiring = get_expiring_items(view_date_str, within_days=7)
        st.metric(
            "Expiring in 7 Days",
            len(expiring),
            delta=f"{len(expiring)} items need attention" if expiring else "All good!",
            delta_color="inverse",
            help="Ingredients that will expire within the next 7 days",
        )

    with col4:
        low_stock = get_low_stock_items()
        st.metric(
            "Low Stock Items",
            len(low_stock),
            delta=f"{len(low_stock)} items running low" if low_stock else "Fully stocked!",
            delta_color="inverse",
            help="Ingredients with very low remaining quantity",
        )

    st.markdown("---")

    # ─── Two Column Layout ───
    left_col, right_col = st.columns([3, 2])

    with left_col:
        st.subheader("📈 Revenue Trend (This Month)")
        st.caption("How your daily revenue has been trending")
        daily = get_daily_sales_summary("2026-03-01", view_date_str)
        if daily:
            df = pd.DataFrame(daily)
            fig = px.line(
                df, x="date", y="revenue",
                labels={"date": "Date", "revenue": "Revenue (₹)"},
                markers=True,
            )
            # Highlight weekends
            for d in daily:
                if d["day"] in ("Saturday", "Sunday"):
                    fig.add_vline(
                        x=d["date"], line_dash="dot",
                        line_color="rgba(255,165,0,0.3)",
                    )
            fig.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)
            st.caption("🟠 Dotted lines = weekends (usually higher sales)")
        else:
            st.info("No sales data available yet for this period.")

    with right_col:
        st.subheader("🏆 Top 5 Sellers")
        st.caption("Your best-selling items this month")
        if revenue_data["items"]:
            top5 = revenue_data["items"][:5]
            df_top = pd.DataFrame(top5)
            fig2 = px.bar(
                df_top, x="total_sold", y="name",
                orientation="h",
                labels={"total_sold": "Units Sold", "name": "Item"},
                color="profit",
                color_continuous_scale="Greens",
            )
            fig2.update_layout(
                height=350, margin=dict(l=0, r=0, t=10, b=0),
                yaxis=dict(autorange="reversed"),
                showlegend=False,
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No sales data yet. Go to 'Daily Sales' to start logging!")

    st.markdown("---")

    # ─── Alerts Section ───
    st.subheader("⚠️ Alerts & Actions")
    st.caption("Things that need your attention right now")

    alert_col1, alert_col2 = st.columns(2)

    with alert_col1:
        expired = get_expired_items(view_date_str)
        if expired:
            st.error(f"🔴 **{len(expired)} item(s) have expired!**")
            for item in expired:
                st.markdown(
                    f"- **{item['name']}**: {item['quantity']:.1f} {item['unit']} "
                    f"expired on {item['expiry_date']}"
                )
            st.caption("Go to Stock & Inventory to dispose of these items")
        else:
            st.success("✅ No expired items! Everything is fresh.")

    with alert_col2:
        if expiring:
            st.warning(f"🟡 **{len(expiring)} item(s) expiring within 7 days:**")
            for item in expiring:
                st.markdown(
                    f"- **{item['name']}**: {item['quantity']:.1f} {item['unit']} "
                    f"expires on {item['expiry_date']}"
                )
            st.caption("Consider using these up or creating special offers around them")
        else:
            st.success("✅ Nothing expiring soon. You're all set!")

    # ─── Month Overview ───
    st.markdown("---")
    st.subheader("📅 Month at a Glance")
    st.caption("Overall numbers for the selected period (March 1 to selected date)")

    ov1, ov2, ov3, ov4 = st.columns(4)
    with ov1:
        st.metric("Total Revenue", f"₹{revenue_data['total_revenue']:,.0f}",
                  help="All sales revenue combined")
    with ov2:
        st.metric("Total Profit", f"₹{revenue_data['total_profit']:,.0f}",
                  help="Revenue minus ingredient costs")
    with ov3:
        margin = revenue_data['total_profit'] / max(revenue_data['total_revenue'], 1) * 100
        st.metric("Profit Margin", f"{margin:.1f}%",
                  help="What percentage of revenue is actual profit")
    with ov4:
        total_items = sum(i["total_sold"] for i in revenue_data["items"])
        st.metric("Items Sold", f"{total_items:,}",
                  help="Total number of menu items sold")
