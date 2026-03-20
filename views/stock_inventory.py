import streamlit as st
import pandas as pd
from datetime import datetime
from database import (
    get_inventory, add_inventory_item, restock_inventory,
    dispose_inventory, get_ingredient_used_in_recipes,
    get_expired_items, get_expiring_items
)


def render(view_date_obj=None, view_date=None):
    st.title("📦 Stock & Inventory")

    with st.expander("ℹ️ **What is this page?** (click to read)", expanded=False):
        st.markdown(
            """
            This is where you manage your **raw ingredients** – the stuff you buy to make your menu items
            (milk, coffee beans, bread, cheese, etc.).

            **What you can do here:**
            - **Current Stock** – see all ingredients, how much is left, when they expire, and their status:
              - 🟢 Good – plenty of stock, not expiring soon
              - 🟡 Expiring Soon – will expire within 7 days (use it up or make a special offer!)
              - 🔴 Expired – already past expiry date (should be disposed)
              - ⚠️ Low Stock – running very low, time to reorder
            - **Add New Ingredient** – bought something new? Add it here (name, quantity, cost, expiry date)
            - **Restock** – got a delivery? Add more quantity to an existing ingredient
            - **Dispose / Mark Waste** – something went bad? Mark it as waste so it shows up in your sustainability reports

            **Important:** When you log sales on the Daily Sales page, ingredients are automatically
            deducted from stock based on each menu item's recipe. You don't need to manually subtract anything.

            **Use the date picker in the sidebar** to change which date you're viewing.
            Expiry status is calculated based on that date.
            """
        )

    if view_date is None:
        view_date = "2026-03-20"
        view_date_obj = datetime(2026, 3, 20).date()

    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Current Stock",
        "➕ Add New Ingredient",
        "📥 Restock",
        "🗑️ Dispose / Mark Waste",
    ])

    # ─── Current Stock ───
    with tab1:
        st.info("ℹ️ All your raw ingredients and their current stock levels. Colors show urgency.", icon="ℹ️")

        inventory = get_inventory()
        if not inventory:
            st.warning("No ingredients in stock. Add some using the 'Add New Ingredient' tab!")
            return

        # Filters
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filter_status = st.selectbox(
                "Filter by status",
                ["All", "🔴 Expired", "🟡 Expiring Soon (7 days)", "🟢 Good", "⚠️ Low Stock"],
                help="Filter ingredients by their current status",
            )
        with col_f2:
            all_ingredient_names = [i["name"] for i in inventory]
            search = st.multiselect(
                "Search ingredient",
                options=all_ingredient_names,
                default=[],
                placeholder="Start typing... (e.g., 'milk')",
                help="Type a few letters and matching ingredients appear. Select to filter.",
            )

        # Categorize items
        today = datetime.strptime(view_date, "%Y-%m-%d").date()
        display_items = []

        for item in inventory:
            status = "🟢 Good"
            expiry = None
            if item["expiry_date"]:
                expiry = datetime.strptime(item["expiry_date"], "%Y-%m-%d").date()
                if expiry < today:
                    status = "🔴 Expired"
                elif (expiry - today).days <= 7:
                    status = "🟡 Expiring Soon"

            if item["quantity"] < 5 and status == "🟢 Good":
                status = "⚠️ Low Stock"

            display_items.append({
                "ID": item["id"],
                "Ingredient": item["name"],
                "Quantity": f"{item['quantity']:.1f}",
                "Unit": item["unit"],
                "Cost/Unit (₹)": f"{item['cost_per_unit']:.0f}",
                "Expiry Date": item["expiry_date"] or "N/A",
                "Status": status,
            })

        # Apply filters
        if filter_status == "🔴 Expired":
            display_items = [d for d in display_items if "Expired" in d["Status"]]
        elif filter_status == "🟡 Expiring Soon (7 days)":
            display_items = [d for d in display_items if "Expiring Soon" in d["Status"]]
        elif filter_status == "🟢 Good":
            display_items = [d for d in display_items if d["Status"] == "🟢 Good"]
        elif filter_status == "⚠️ Low Stock":
            display_items = [d for d in display_items if "Low Stock" in d["Status"]]

        if search:
            display_items = [d for d in display_items if d["Ingredient"] in search]

        if display_items:
            df = pd.DataFrame(display_items)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Status": st.column_config.TextColumn("Status", width="medium"),
                },
            )
            st.caption(f"Showing {len(display_items)} of {len(inventory)} ingredients")
        else:
            st.info("No ingredients match your filter.")

    # ─── Add New Ingredient ───
    with tab2:
        st.info("ℹ️ Add a new ingredient to your stock. This is for raw materials (milk, sugar, etc.) – not menu items.", icon="ℹ️")

        with st.form("add_ingredient", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input(
                    "Ingredient Name",
                    placeholder="e.g., Almond Milk",
                    help="Name of the raw ingredient",
                )
                quantity = st.number_input(
                    "Quantity",
                    min_value=0.0, value=1.0, step=0.5,
                    help="How much are you adding to stock?",
                )
                unit = st.text_input(
                    "Unit",
                    placeholder="kg / liters / pieces",
                    help="Unit of measurement",
                )
            with col2:
                cost = st.number_input(
                    "Cost per Unit (₹)",
                    min_value=0.0, value=100.0, step=10.0,
                    help="How much does one unit cost you?",
                )
                expiry = st.date_input(
                    "Expiry Date",
                    help="When does this ingredient expire?",
                )
                purchased = st.date_input(
                    "Purchase Date",
                    value=datetime(2026, 3, 20).date(),
                    help="When did you buy this?",
                )

            if st.form_submit_button("➕ Add Ingredient", use_container_width=True):
                if not name or not name.strip():
                    st.error("Please enter the ingredient name.")
                elif quantity <= 0:
                    st.error("Quantity must be greater than zero.")
                elif not unit or not unit.strip():
                    st.error("Please enter the unit (e.g., kg, liters).")
                elif cost <= 0:
                    st.error("Cost must be greater than zero.")
                else:
                    add_inventory_item(
                        name, quantity, unit, cost,
                        expiry.strftime("%Y-%m-%d"),
                        purchased.strftime("%Y-%m-%d"),
                    )
                    st.success(f"Added {quantity} {unit} of '{name}' to stock!")
                    st.rerun()

    # ─── Restock ───
    with tab3:
        st.info("ℹ️ Got a new delivery? Add more quantity to an existing ingredient.", icon="ℹ️")

        inventory = get_inventory()
        if not inventory:
            st.warning("No ingredients to restock. Add some first!")
            return

        with st.form("restock"):
            item_names = {f"{i['name']} ({i['quantity']:.1f} {i['unit']} in stock)": i["id"] for i in inventory}
            selected = st.selectbox(
                "Select ingredient to restock",
                list(item_names.keys()),
                help="Pick which ingredient you're restocking",
            )
            add_qty = st.number_input(
                "How much are you adding?",
                min_value=0.1, value=1.0, step=0.5,
                help="The additional quantity you're adding to current stock",
            )
            new_expiry = st.date_input(
                "New expiry date (if updated)",
                help="If the new batch has a different expiry date, update it here",
            )

            if st.form_submit_button("📥 Restock", use_container_width=True):
                item_id = item_names[selected]
                restock_inventory(item_id, add_qty, new_expiry.strftime("%Y-%m-%d"))
                st.success(f"Restocked! Added {add_qty} more to {selected.split(' (')[0]}.")
                st.rerun()

    # ─── Dispose ───
    with tab4:
        st.info("ℹ️ Mark ingredients that have gone bad or need to be thrown away. This will be tracked in your waste reports.", icon="ℹ️")

        inventory = get_inventory()
        items_with_stock = [i for i in inventory if i["quantity"] > 0]

        if not items_with_stock:
            st.success("Nothing to dispose – all stock is at zero or already accounted for!")
            return

        with st.form("dispose"):
            item_names = {
                f"{i['name']} ({i['quantity']:.1f} {i['unit']} available)": i
                for i in items_with_stock
            }
            selected = st.selectbox(
                "Select ingredient to dispose",
                list(item_names.keys()),
                help="Pick the ingredient you're throwing away",
            )
            selected_item = item_names[selected]

            dispose_qty = st.number_input(
                "How much are you disposing?",
                min_value=0.1,
                max_value=float(selected_item["quantity"]),
                value=min(1.0, float(selected_item["quantity"])),
                step=0.5,
                help=f"Maximum: {selected_item['quantity']:.1f} {selected_item['unit']}",
            )

            reason = st.selectbox(
                "Reason for disposal",
                ["Expired", "Spoiled / Gone bad", "Damaged", "Other"],
                help="Why is this ingredient being thrown away?",
            )

            if st.form_submit_button("🗑️ Dispose & Mark as Waste", use_container_width=True):
                # Check if ingredient is used in any recipe
                used_in = get_ingredient_used_in_recipes(selected_item["name"])
                dispose_inventory(selected_item["id"], dispose_qty, view_date)
                st.success(
                    f"Disposed {dispose_qty} {selected_item['unit']} of {selected_item['name']}. "
                    f"Reason: {reason}. This has been logged as waste."
                )
                if used_in:
                    st.warning(
                        f"Heads up: {selected_item['name']} is used in these menu items: "
                        f"{', '.join(used_in)}. Make sure you have enough stock to serve them!"
                    )
                st.rerun()
