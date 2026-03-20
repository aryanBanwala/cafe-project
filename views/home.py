import streamlit as st


def render():
    st.title("☕ Welcome to Green Cafe Manager")
    st.markdown("#### Your smart assistant for managing cafe inventory, reducing waste, and boosting profit")

    st.markdown("---")

    st.markdown(
        """
        ### What is this app?

        Green Cafe Manager is a simple tool built for small cafe owners.
        It helps you keep track of what ingredients you have, what you're selling,
        what's about to expire, and how to waste less food – all in one place.

        No spreadsheets. No complicated software. Just open the app and start managing.
        """
    )

    st.markdown("---")

    st.markdown("### What can you do here?")
    st.markdown("")

    # ─── Feature Cards ───
    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.markdown("#### 📊 Dashboard")
            st.markdown(
                "See how your cafe is doing **right now**. "
                "Today's revenue, profit, what's expiring, what's running low – all at a glance."
            )
            if st.button("Go to Dashboard →", key="goto_dash", use_container_width=True):
                st.session_state["nav"] = "📊 Dashboard"
                st.rerun()

        with st.container(border=True):
            st.markdown("#### 📦 Stock & Inventory")
            st.markdown(
                "See all your raw ingredients (milk, sugar, bread, etc.). "
                "**Restock** when a delivery arrives, **dispose** when something goes bad. "
                "Items are color-coded: 🟢 Good, 🟡 Expiring Soon, 🔴 Expired."
            )
            if st.button("Go to Stock & Inventory →", key="goto_stock", use_container_width=True):
                st.session_state["nav"] = "📦 Stock & Inventory"
                st.rerun()

        with st.container(border=True):
            st.markdown("#### 🤖 AI Reports")
            st.markdown(
                "Get a **detailed AI-powered report** for your sales up to the selected date. "
                "The AI analyzes your sales, finds patterns (like weekend spikes), "
                "flags waste, and gives you suggestions to improve. "
                "Works even without internet – a built-in backup report kicks in automatically."
            )
            if st.button("Go to AI Reports →", key="goto_reports", use_container_width=True):
                st.session_state["nav"] = "🤖 AI Reports"
                st.rerun()

    with col2:
        with st.container(border=True):
            st.markdown("#### 🍽️ Menu Management")
            st.markdown(
                "Add, edit, or remove items from your cafe menu. "
                "Set the **recipe** for each item (what ingredients it needs). "
                "Removed items are hidden but their sales history stays safe."
            )
            if st.button("Go to Menu Management →", key="goto_menu", use_container_width=True):
                st.session_state["nav"] = "🍽️ Menu Management"
                st.rerun()

        with st.container(border=True):
            st.markdown("#### 🌿 Sustainability")
            st.markdown(
                "See your **waste score** – how much of what you bought actually got used. "
                "Find eco-friendly supplier alternatives that reduce your carbon footprint. "
                "Get AI-powered tips to make your cafe greener."
            )
            if st.button("Go to Sustainability →", key="goto_sustain", use_container_width=True):
                st.session_state["nav"] = "🌿 Sustainability"
                st.rerun()

    # Full width AI Chat card
    with st.container(border=True):
        st.markdown("#### 💬 AI Chat")
        st.markdown(
            "Chat directly with an AI that knows your entire cafe – menu, sales, stock, waste, recipes. "
            "Ask it anything in plain English. Choose from **7 AI models** including Gemini 3, Claude Opus 4.6, and GPT-4.1. "
            "Great for quick questions like *\"How much milk do I need for next week?\"* or *\"Which items have the best margins?\"*"
        )
        if st.button("Go to AI Chat →", key="goto_chat", use_container_width=True):
            st.session_state["nav"] = "💬 AI Chat"
            st.rerun()

    st.markdown("---")

    st.markdown("### About the sample data")
    st.markdown("")

    st.markdown(
        """
        This app comes pre-loaded with **one month of synthetic data** for a small Indian cafe.
        Nothing is real — it's all made up so you can explore every feature right away.
        """
    )

    col_d1, col_d2 = st.columns(2)

    with col_d1:
        with st.container(border=True):
            st.markdown("**🍽️ The Cafe**")
            st.markdown(
                "A small cafe in India that sells coffee, tea, sandwiches, pasta, "
                "salads, soups, and desserts. Prices are in ₹ (Indian Rupees). "
                "Sales data covers **March 1–31, 2026** with realistic patterns — "
                "weekends are busier, some items sell more than others."
            )

        with st.container(border=True):
            st.markdown("**📋 Menu (15 items)**")
            st.markdown(
                "**Beverages:** Cappuccino, Latte, Espresso, Cold Coffee, Green Tea, "
                "Hot Chocolate, Vanilla Milkshake, Masala Chai\n\n"
                "**Food:** Paneer Sandwich, Veg Pasta, Cheese Toast, Caesar Salad, Mushroom Soup\n\n"
                "**Desserts:** Chocolate Brownie, Cheesecake Slice"
            )

    with col_d2:
        with st.container(border=True):
            st.markdown("**📦 Ingredients (23 items)**")
            st.markdown(
                "Coffee Beans, Milk, Sugar, Green Tea Leaves, Honey, Cocoa Powder, "
                "Bread, Paneer, Butter, Lettuce, Pasta, Olive Oil, Cheese, Bell Pepper, "
                "Tomato Sauce, Mushrooms, Flour, Eggs, Croutons, Vanilla Extract, "
                "Tea Leaves, Ginger, Ice Cubes\n\n"
                "Each has a **quantity, unit, cost, purchase date, and expiry date**. "
                "Some are already expired by mid-March — this is intentional so you can "
                "see expiry alerts and waste tracking in action."
            )

        with st.container(border=True):
            st.markdown("**🔗 How they connect**")
            st.markdown(
                "Each menu item has a **recipe** — e.g., 1 Cappuccino needs 0.02 kg Coffee + "
                "0.15 L Milk + 0.01 kg Sugar. When sales are loaded, the app uses these recipes "
                "to auto-deduct ingredients from stock. This is how the app knows what's running low."
            )

    st.markdown("---")

    st.markdown("### How does it work?")
    st.markdown("")

    st.markdown(
        """
        ```
        You set up your menu            "Cappuccino costs ₹180"
              ↓
        You tell it the recipe          "1 Cappuccino = 0.02 kg coffee + 0.15 L milk + 0.01 kg sugar"
              ↓
        You log today's sales           "Sold 25 Cappuccinos today"
              ↓
        The app auto-deducts stock      "0.5 kg coffee, 3.75 L milk, 0.25 kg sugar used up"
              ↓
        You see what's running low      "Milk is at 4L – you'll run out in 2 days"
              ↓
        AI gives you a weekly report    "Weekend sales are 2x higher – stock extra milk before Saturday"
        ```
        """
    )

    st.markdown("---")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.info("🤖 **AI-Powered**\n\nReports and tips are generated by AI. If the AI service is down, a built-in backup system takes over automatically. You always get a result.")
    with col_b:
        st.info("📊 **Data Included**\n\nThe app comes pre-loaded with a sample cafe's data for the full month of March. You can explore, add items, log sales, and see reports right away.")
    with col_c:
        st.info("🔒 **No Data Leaves Your Machine**\n\nEverything is stored locally in a small database file. No cloud, no sign-up, no tracking. Your data stays with you.")
