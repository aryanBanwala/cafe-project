import os
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv
from database import init_database, DB_PATH

load_dotenv()

# Initialize database on first run
init_database()

# Check if API key is configured
HAS_API_KEY = bool(os.getenv("OPENROUTER_API_KEY", "").strip())

st.set_page_config(
    page_title="Green Cafe Manager",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── API Key Warning Banner ───
if not HAS_API_KEY:
    st.warning(
        "🔑 **AI features are running in fallback mode.** "
        "No OpenRouter API key found. All AI-powered reports and tips will use the built-in "
        "rule-based engine instead. To enable AI features, clone this repo and add your own "
        "API key to the `.env` file. See `.env.example` for instructions. "
        "We don't ship API keys in production to prevent misuse.",
        icon="🔒",
    )

# ─── Sidebar Navigation ───
st.sidebar.title("☕ Green Cafe Manager")
st.sidebar.caption("Your smart cafe inventory assistant")

NAV_OPTIONS = [
    "🏠 Home",
    "📊 Dashboard",
    "🍽️ Menu Management",
    "📦 Stock & Inventory",
    "🤖 AI Reports",
    "🌿 Sustainability",
    "💬 AI Chat",
]

# Support navigation from Home page buttons
if "nav" in st.session_state:
    nav_target = st.session_state.pop("nav")
    if nav_target in NAV_OPTIONS:
        st.session_state["current_page"] = nav_target

page = st.sidebar.radio(
    "Navigate to",
    NAV_OPTIONS,
    key="current_page",
    help="Pick a section to manage your cafe",
)

st.sidebar.markdown("---")

# ─── Global Date Picker ───
st.sidebar.subheader("📅 Viewing Data As Of")
global_date = st.sidebar.date_input(
    "Select date",
    value=datetime(2026, 3, 20).date(),
    min_value=datetime(2026, 3, 1).date(),
    max_value=datetime(2026, 3, 31).date(),
    key="global_date",
    help="All pages will show data up to this date. Expiry, stock levels, revenue – everything is calculated relative to this date.",
    label_visibility="collapsed",
)
st.sidebar.caption(f"📅 {global_date.strftime('%A, %B %d, %Y')}")
st.sidebar.caption(
    "Dashboard, Stock, Sales, Reports, and Sustainability all filter data up to this date. "
    "Change it to see how the cafe looked on any day in March.\n\n"
    "**AI Chat is not affected** — it always sees the full database regardless of this date."
)

st.sidebar.markdown("---")

# ─── Reset Database (Sidebar) ───
with st.sidebar.expander("🔄 Reset Database"):
    st.markdown(
        """
        **What this does:**
        - Deletes all your current data (menu edits, stock changes, sales you logged)
        - Reloads the original sample data from CSV files
        - Everything goes back to how it was when you first opened the app

        **This cannot be undone.**
        """
    )
    confirm_text = st.text_input(
        "Type **refresh-db** to confirm",
        placeholder="refresh-db",
        key="reset_db_confirm",
        label_visibility="visible",
    )
    if st.button("🔄 Reset Database", use_container_width=True, type="primary", disabled=(confirm_text != "refresh-db")):
        if confirm_text == "refresh-db":
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
            init_database()
            st.session_state.pop("reset_db_confirm", None)
            st.success("Database has been reset to original sample data!")
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.info(
    "ℹ️ **Quick Start:** This app helps you manage your cafe inventory, "
    "track sales, and get AI-powered insights to reduce waste and boost profit."
)

# ─── Global date string for pages ───
global_date_str = global_date.strftime("%Y-%m-%d")

# ─── Load Pages ───
if page == "🏠 Home":
    from views.home import render
    render()
elif page == "📊 Dashboard":
    from views.dashboard import render
    render(global_date, global_date_str)
elif page == "🍽️ Menu Management":
    from views.menu_management import render
    render()
elif page == "📦 Stock & Inventory":
    from views.stock_inventory import render
    render(global_date, global_date_str)
elif page == "🤖 AI Reports":
    from views.ai_reports import render
    render(global_date, global_date_str)
elif page == "🌿 Sustainability":
    from views.sustainability import render
    render(global_date, global_date_str)
elif page == "💬 AI Chat":
    from views.ai_chat import render
    render(global_date, global_date_str)
