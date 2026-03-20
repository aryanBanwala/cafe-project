import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import (
    get_usage_log, get_eco_alternatives, get_waste_summary,
    get_inventory, get_daily_sales_summary
)
from ai_engine import generate_sustainability_insight


def render(global_date=None, global_date_str=None):
    st.title("🌿 Sustainability Dashboard")

    with st.expander("ℹ️ **What is this page?** (click to read)", expanded=False):
        st.markdown(
            """
            This page helps you understand your cafe's **environmental impact**.

            **What you see here:**
            - **Waste Score** – what percentage of ingredients you actually used vs threw away.
              100% means zero waste. The lower the score, the more you're wasting.
            - **Waste Breakdown** – which specific ingredients are being wasted the most
              (so you know what to order less of next time)
            - **Eco-Friendly Alternatives** – a table showing greener supplier options for your
              ingredients. For example, switching from imported coffee to a local roaster saves
              1.2 kg CO₂ per kg. Some alternatives are even cheaper!
            - **AI Sustainability Tips** – click the button to get personalized AI-powered advice
              on how to reduce waste and go greener
            - **Monthly Trend** – how your waste efficiency has changed week by week

            **How waste is tracked:** When you dispose of ingredients on the Stock & Inventory page
            (marking them as expired, spoiled, etc.), that gets logged as waste. The numbers here
            come from those disposal records.

            **This page is mostly read-only.** To improve your waste score, use the Stock page to
            dispose expired items, and use the Weekly Reports to get reorder suggestions.
            """
        )

    if global_date_str is None:
        global_date_str = "2026-03-20"

    # ─── Waste Score ───
    st.subheader("♻️ Waste Score")
    st.caption(f"How efficiently are you using your ingredients? (up to {global_date_str})")

    usage_used = get_usage_log(end_date=global_date_str, log_type="used")
    usage_wasted = get_usage_log(end_date=global_date_str, log_type="wasted")

    total_used = sum(u["quantity_used"] for u in usage_used)
    total_wasted = sum(u["quantity_used"] for u in usage_wasted)
    total_all = total_used + total_wasted

    if total_all > 0:
        waste_score = (total_used / total_all) * 100
    else:
        waste_score = 100.0  # No waste if nothing used

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Efficiency Score",
            f"{waste_score:.1f}%",
            help="Percentage of ingredients that were actually used (not wasted). 100% = zero waste!",
        )
    with col2:
        st.metric(
            "Total Used",
            f"{total_used:.1f} units",
            help="Total amount of ingredients used in making menu items",
        )
    with col3:
        st.metric(
            "Total Wasted",
            f"{total_wasted:.1f} units",
            delta=f"-{total_wasted:.1f} units lost" if total_wasted > 0 else "Zero waste!",
            delta_color="inverse",
            help="Total amount of ingredients that were thrown away",
        )

    # Progress bar for waste score
    st.progress(min(waste_score / 100, 1.0))
    if waste_score >= 90:
        st.success("Excellent! You're running a very efficient kitchen! 🌟")
    elif waste_score >= 75:
        st.info("Good job! There's still some room to reduce waste. Check the suggestions below.")
    else:
        st.warning("Your waste levels are high. See the recommendations below to improve.")

    st.markdown("---")

    # ─── Waste Breakdown ───
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("🗑️ Waste Breakdown")
        st.caption("Which ingredients are being wasted the most?")

        waste_data = get_waste_summary(end_date=global_date_str)
        if waste_data:
            df_waste = pd.DataFrame(waste_data)
            fig = px.bar(
                df_waste, x="total_wasted", y="ingredient",
                orientation="h",
                labels={"total_wasted": "Quantity Wasted", "ingredient": "Ingredient"},
                color="total_wasted",
                color_continuous_scale="Reds",
            )
            fig.update_layout(
                height=300, margin=dict(l=0, r=0, t=10, b=0),
                yaxis=dict(autorange="reversed"),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("No waste recorded! Your kitchen is running perfectly. 🎉")

    with col_right:
        st.subheader("📊 Expired vs Used")
        st.caption("Proportion of ingredients used vs wasted")

        if total_all > 0:
            fig_pie = px.pie(
                values=[total_used, total_wasted],
                names=["Used", "Wasted"],
                color_discrete_sequence=["#2ecc71", "#e74c3c"],
                hole=0.4,
            )
            fig_pie.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No usage data yet. Start logging sales to see this chart!")

    st.markdown("---")

    # ─── Eco Alternatives ───
    st.subheader("🔄 Eco-Friendly Alternatives")
    st.caption("Switch to these suppliers to reduce your carbon footprint and support local businesses")

    eco_alts = get_eco_alternatives()
    if eco_alts:
        df_eco = pd.DataFrame(eco_alts)
        df_display = df_eco[["ingredient", "current_supplier", "alternative_supplier",
                            "eco_rating", "price_diff_pct", "carbon_saved_kg"]].copy()
        df_display.columns = [
            "Ingredient", "Current Supplier", "Eco Alternative",
            "Eco Rating", "Price Difference", "CO₂ Saved (kg/unit)",
        ]
        df_display["Price Difference"] = df_display["Price Difference"].apply(
            lambda x: f"+{x:.0f}%" if x > 0 else f"{x:.0f}%"
        )

        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Eco Rating": st.column_config.TextColumn("Eco Rating", width="small"),
                "CO₂ Saved (kg/unit)": st.column_config.NumberColumn(
                    "CO₂ Saved (kg/unit)", format="%.1f"
                ),
            },
        )

        # Carbon savings calculator
        total_carbon = sum(e["carbon_saved_kg"] for e in eco_alts)
        st.metric(
            "Potential Carbon Savings (if you switch all)",
            f"{total_carbon:.1f} kg CO₂ per unit cycle",
            help="This is how much CO₂ you could save by switching all ingredients to eco alternatives",
        )
    else:
        st.info("No eco alternatives data available.")

    st.markdown("---")

    # ─── AI Sustainability Tips ───
    st.subheader("💡 AI Sustainability Advisor")
    st.caption("Get personalized tips to make your cafe more sustainable")

    import os
    has_key = bool(os.getenv("OPENROUTER_API_KEY", "").strip())
    if not has_key:
        st.info(
            "🔒 **No API key – fallback mode.** Tips will use built-in analysis. "
            "Clone this repo and add your own OpenRouter API key to `.env` for AI-powered advice.",
            icon="ℹ️",
        )

    if st.button("🌱 Get Sustainability Tips", use_container_width=True, type="primary"):
        import time
        progress = st.progress(0)
        status = st.empty()

        status.info("🌿 **Step 1/3:** Gathering your waste and usage data...")
        time.sleep(0.5)
        sustainability_data = {
            "waste_score": waste_score,
            "wasted_items": waste_data if waste_data else [],
            "eco_alternatives": eco_alts[:5] if eco_alts else [],
            "carbon_saved": total_carbon if eco_alts else 0,
        }
        progress.progress(33)

        status.info("🧠 **Step 2/3:** AI is analyzing your sustainability patterns...")
        time.sleep(0.3)
        result = generate_sustainability_insight(sustainability_data)
        progress.progress(80)

        if result["source"] == "ai":
            status.info("✨ **Step 3/3:** AI advice ready!")
        else:
            status.info("📊 **Step 3/3:** Fallback advice generated!")
        time.sleep(0.4)
        progress.progress(100)
        time.sleep(0.3)

        progress.empty()
        status.empty()

        if result["source"] == "ai":
            st.caption("🤖 Generated by AI – remember, AI can make mistakes. Verify before acting.")
        else:
            st.caption("📊 Generated using built-in rule-based analysis (AI was unavailable).")

        st.markdown(result["insight"])

    # ─── Monthly Sustainability Trend ───
    st.markdown("---")
    st.subheader("📈 Monthly Trend")
    st.caption("How your waste levels have changed throughout the month")

    # Get weekly waste data
    weeks = [
        ("Week 1", "2026-03-01", "2026-03-07"),
        ("Week 2", "2026-03-08", "2026-03-14"),
        ("Week 3", "2026-03-15", "2026-03-21"),
        ("Week 4", "2026-03-22", "2026-03-31"),
    ]

    trend_data = []
    for label, start, end in weeks:
        used = get_usage_log(start_date=start, end_date=end, log_type="used")
        wasted = get_usage_log(start_date=start, end_date=end, log_type="wasted")
        t_used = sum(u["quantity_used"] for u in used)
        t_wasted = sum(u["quantity_used"] for u in wasted)
        t_total = t_used + t_wasted
        score = (t_used / t_total * 100) if t_total > 0 else 100
        trend_data.append({"Week": label, "Efficiency %": score, "Used": round(t_used, 1), "Wasted": round(t_wasted, 1)})

    if any(d["Wasted"] > 0 for d in trend_data):
        df_trend = pd.DataFrame(trend_data)

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown("**Waste per Week (units thrown away)**")
            fig_waste = px.bar(
                df_trend, x="Week", y="Wasted",
                labels={"Wasted": "Units Wasted"},
                color="Wasted",
                color_continuous_scale="Reds",
            )
            fig_waste.update_layout(
                height=300, margin=dict(l=0, r=0, t=10, b=0),
                showlegend=False,
            )
            st.plotly_chart(fig_waste, use_container_width=True)

        with col_t2:
            st.markdown("**Usage vs Waste per Week**")
            fig_compare = px.bar(
                df_trend, x="Week", y=["Used", "Wasted"],
                labels={"value": "Units", "variable": "Type"},
                barmode="group",
                color_discrete_map={"Used": "#2ecc71", "Wasted": "#e74c3c"},
            )
            fig_compare.update_layout(
                height=300, margin=dict(l=0, r=0, t=10, b=0),
            )
            st.plotly_chart(fig_compare, use_container_width=True)
    else:
        st.info("Not enough waste data to show a trend yet. Dispose items through Stock & Inventory to start tracking.")
