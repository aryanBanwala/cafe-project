import streamlit as st
import pandas as pd
from database import (
    get_menu_items, add_menu_item, update_menu_item,
    soft_delete_menu_item, restore_menu_item,
    get_recipes_for_item, set_recipes_for_item, get_inventory
)


def render():
    st.title("🍽️ Menu Management")

    with st.expander("ℹ️ **What is this page?** (click to read)", expanded=False):
        st.markdown(
            """
            This is where you manage **what your cafe sells**. Think of it as your digital menu card.

            **What you can do here:**
            - **View Menu** – see all your active menu items with their prices and recipes
            - **Add New Item** – add a new dish or drink (e.g., "Mocha Latte, ₹220, Beverage")
            - **Edit** – change an item's name, price, or category
            - **Set Recipe** – tell the app what ingredients each item needs (e.g., "1 Cappuccino = 0.02 kg coffee + 0.15 L milk")
            - **Remove** – take an item off the menu (it's hidden, not deleted – past sales data stays safe)
            - **Restore** – bring back a removed item from the "Removed Items" tab

            **Why recipes matter:** When you log a sale (on the Daily Sales page), the app uses the recipe
            to automatically figure out how much of each ingredient was used. So if you sold 25 Cappuccinos,
            it knows to subtract 0.5 kg coffee and 3.75 L milk from your stock.

            **The app comes pre-loaded with 15 menu items** and their recipes. You can edit them or add your own.
            """
        )

    tab1, tab2, tab3 = st.tabs([
        "📋 View Menu",
        "➕ Add New Item",
        "🗑️ Removed Items",
    ])

    # ─── View Menu ───
    with tab1:
        # Show "just added" banner with details
        if "just_added" in st.session_state:
            added = st.session_state.pop("just_added")
            st.balloons()
            with st.container(border=True):
                st.success(f"🎉 **'{added['name']}'** has been added to your menu!")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"**Price:** ₹{added['price']:.0f}")
                    st.markdown(f"**Category:** {added['category']}")
                with col_b:
                    st.markdown("**Recipe (per serving):**")
                    for ing, qty, unit in added["recipe"]:
                        st.markdown(f"- {ing}: {qty} {unit}")
                st.caption("Scroll down to find it in your menu")

        st.info("ℹ️ Your active menu items. Click on any item to see its recipe, edit details, or remove it.", icon="ℹ️")

        items = get_menu_items(active_only=True)

        if not items:
            st.warning("Your menu is empty! Add some items using the 'Add New Item' tab.")
            return

        # Filter
        categories = sorted(set(i["category"] for i in items))
        all_names = [i["name"] for i in items]

        col_search, col_filter = st.columns([2, 1])
        with col_search:
            search = st.multiselect(
                "Search items",
                options=all_names,
                default=[],
                placeholder="Start typing to search... (e.g., 'capp')",
                help="Type a few letters and matching items will appear. Select one or more to filter.",
            )
        with col_filter:
            selected_cat = st.selectbox(
                "Filter by category",
                ["All"] + categories,
                help="Show only items from a specific category",
            )

        filtered = items
        if selected_cat != "All":
            filtered = [i for i in filtered if i["category"] == selected_cat]
        if search:
            filtered = [i for i in filtered if i["name"] in search]

        if not filtered:
            st.info("No items match your search. Try a different filter.")
            return

        # Display as cards
        for item in filtered:
            with st.expander(f"**{item['name']}** – ₹{item['sell_price']:.0f} ({item['category']})"):
                col1, col2 = st.columns([2, 1])

                with col1:
                    # Show recipe
                    recipes = get_recipes_for_item(item["id"])
                    if recipes:
                        st.markdown("**Recipe (ingredients per serving):**")
                        for r in recipes:
                            st.markdown(f"- {r['ingredient']}: {r['quantity_needed']} {r['unit']}")
                    else:
                        st.caption("No recipe set yet. Edit this item to add ingredients.")

                with col2:
                    # Edit fields (no form – no Enter-to-submit issue)
                    new_name = st.text_input(
                        "Name", value=item["name"], key=f"name_{item['id']}",
                        label_visibility="collapsed",
                    )
                    new_price = st.number_input(
                        "Price (₹)", value=float(item["sell_price"]),
                        min_value=10.0, max_value=1000.0, step=10.0, key=f"price_{item['id']}",
                    )
                    new_cat = st.selectbox(
                        "Category",
                        ["Beverage", "Food", "Dessert"],
                        index=["Beverage", "Food", "Dessert"].index(item["category"]),
                        key=f"cat_{item['id']}",
                    )
                    col_save, col_del = st.columns(2)
                    with col_save:
                        if st.button("💾 Save", key=f"save_{item['id']}", use_container_width=True):
                            n = new_name.strip() if new_name else ""
                            wc = len(n.split()) if n else 0
                            if not n:
                                st.error("Name can't be empty.")
                            elif len(n) < 3:
                                st.error("Too short – at least 3 characters.")
                            elif wc > 3:
                                st.error("Too long – max 3 words.")
                            elif new_price <= 0:
                                st.error("Price must be greater than zero.")
                            else:
                                success, err = update_menu_item(item["id"], new_name, new_price, new_cat)
                                if success:
                                    st.success(f"Updated '{new_name}'!")
                                    st.rerun()
                                else:
                                    st.error(err)
                    with col_del:
                        if st.button("🗑️ Remove", key=f"del_{item['id']}", use_container_width=True):
                            soft_delete_menu_item(item["id"])
                            st.success(f"Removed '{item['name']}'. Restore it from 'Removed Items' tab.")
                            st.rerun()

    # ─── Add New Item ───
    with tab2:
        st.info("ℹ️ Add a new dish or drink to your menu. Set the recipe so the app knows what ingredients it needs.", icon="ℹ️")

        # No form – just normal widgets + button
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input(
                "Item Name",
                placeholder="e.g., Mocha Latte",
                help="3-50 characters, max 3 words. Keep it short – it goes on your menu!",
                key="add_item_name",
                max_chars=50,
            )
            # Live validation hint
            if name:
                name_stripped = name.strip()
                word_count = len(name_stripped.split())
                if len(name_stripped) < 3:
                    st.caption("⚠️ Too short – name must be at least 3 characters (it'll look bad on the menu)")
                elif word_count > 3:
                    st.caption("⚠️ Too long – keep it to 3 words max (e.g., 'Iced Mocha Latte', not 'Iced Mocha Latte Special Edition')")
                else:
                    st.caption(f"✅ {name_stripped} – looks good!")
        with col2:
            sell_price = st.number_input(
                "Selling Price (₹)",
                min_value=10.0, max_value=1000.0, value=100.0, step=10.0,
                help="Between ₹10 and ₹1000",
                key="add_item_price",
            )

        category = st.selectbox(
            "Category",
            ["Beverage", "Food", "Dessert"],
            help="What type of item is this?",
            key="add_item_cat",
        )

        st.markdown("**Recipe – What ingredients does this item need?**")
        st.caption("Add the ingredients needed to make one serving of this item")

        inventory = get_inventory()
        ingredient_names = [i["name"] for i in inventory]

        recipe_entries = []
        for i in range(5):
            r_col1, r_col2, r_col3 = st.columns([2, 1, 1])
            with r_col1:
                ing = st.selectbox(
                    f"Ingredient {i+1}",
                    ["(none)"] + ingredient_names,
                    key=f"add_ing_{i}",
                    help="Pick from your existing stock",
                )
            with r_col2:
                qty = st.number_input(
                    f"Amount {i+1}",
                    min_value=0.001, value=0.01, step=0.01,
                    format="%.3f",
                    key=f"add_qty_{i}",
                    help="How much of this ingredient per serving (must be > 0)",
                )
            with r_col3:
                ing_item = next((inv for inv in inventory if inv["name"] == ing), None)
                unit_val = ing_item["unit"] if ing_item and ing != "(none)" else ""
                st.text_input(
                    f"Unit {i+1}",
                    value=unit_val,
                    disabled=True,
                    key=f"add_unit_{i}",
                    help="Auto-filled from stock",
                )
                if ing != "(none)" and qty > 0 and unit_val:
                    recipe_entries.append((ing, qty, unit_val))

        st.markdown("---")
        if st.button("➕ Add to Menu", use_container_width=True, type="primary"):
            name_stripped = name.strip() if name else ""
            word_count = len(name_stripped.split()) if name_stripped else 0
            if not name_stripped:
                st.error("Please enter a name for the item.")
            elif len(name_stripped) < 3:
                st.error("Name is too short (minimum 3 characters). A short name will look bad on your menu.")
            elif word_count > 3:
                st.error("Name is too long (maximum 3 words). Keep it concise for your menu – e.g., 'Iced Mocha Latte'.")
            elif sell_price <= 0:
                st.error("Price must be greater than zero.")
            elif not recipe_entries:
                st.error("Add at least one ingredient to the recipe. Without a recipe, the app can't track ingredient usage when you sell this item.")
            else:
                menu_id, err = add_menu_item(name_stripped, sell_price, category)
                if menu_id:
                    if recipe_entries:
                        set_recipes_for_item(menu_id, recipe_entries)
                    st.session_state["just_added"] = {
                        "name": name_stripped,
                        "price": sell_price,
                        "category": category,
                        "recipe": recipe_entries,
                    }
                    st.rerun()
                else:
                    st.error(err)

    # ─── Removed Items ───
    with tab3:
        st.info("ℹ️ Items you've removed from the menu. Their past sales data is still kept. You can bring them back anytime.", icon="ℹ️")

        all_items = get_menu_items(active_only=False)
        removed = [i for i in all_items if not i["is_active"]]

        if not removed:
            st.success("No removed items. Your full menu is active!")
            return

        for item in removed:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{item['name']}** – ₹{item['sell_price']:.0f} ({item['category']})")
            with col2:
                if st.button(f"♻️ Restore", key=f"restore_{item['id']}"):
                    restore_menu_item(item["id"])
                    st.success(f"'{item['name']}' is back on the menu!")
                    st.rerun()
