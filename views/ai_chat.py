import os
import json
import time
import random
import requests
import streamlit as st
from dotenv import load_dotenv
from database import (
    save_chat_message, get_chat_history, clear_chat_history,
    get_full_db_context
)

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

AVAILABLE_MODELS = {
    "Google Gemini 3 Flash (Recommended)": "google/gemini-3-flash-preview",
    "Google Gemini 3.1 Pro": "google/gemini-3.1-pro-preview",
    "Google Gemini 2.5 Flash": "google/gemini-2.5-flash-preview-05-20",
    "Claude Opus 4.6": "anthropic/claude-opus-4.6",
    "Claude Sonnet 4.6": "anthropic/claude-sonnet-4.6",
    "OpenAI GPT-4.1": "openai/gpt-4.1",
    "OpenAI GPT-4.1 Mini": "openai/gpt-4.1-mini",
}

LOADING_WORDS = [
    "Brewing insights", "Grinding data", "Steaming analysis", "Frothing numbers",
    "Roasting patterns", "Filtering noise", "Stirring metrics", "Pouring wisdom",
    "Blending trends", "Toasting results", "Sipping through sales", "Whisking waste data",
    "Dripping knowledge", "Percolating ideas", "Extracting signals", "Infusing context",
    "Caramelizing correlations", "Tempering predictions", "Garnishing insights",
    "Plating recommendations", "Seasoning suggestions", "Marinating in data",
    "Kneading the numbers", "Simmering analysis", "Reducing complexity",
    "Flambéing the forecast", "Tasting the trends", "Dicing the data",
]

RETRY_CONFIGS = [
    {"max_tokens": 4000, "timeout": 60},
    {"max_tokens": 8000, "timeout": 90},
    {"max_tokens": 12000, "timeout": 120},
]

PRO_MODELS = {
    "google/gemini-3.1-pro-preview",
    "anthropic/claude-opus-4.6",
    "openai/gpt-4.1",
}


def _get_system_prompt(db_context):
    """Build system prompt with full DB context."""
    return f"""You are a smart, friendly AI assistant for a small cafe called "Green Cafe".
You have access to the cafe's complete data. Use it to answer questions accurately.

RULES:
- Keep responses concise. Use markdown for formatting.
- Don't dump the entire database back. Only show relevant data.
- If asked about numbers, DO YOUR OWN MATH from the data. Be specific.
- If asked a general question not about the cafe, answer briefly but steer back to cafe topics.
- Be conversational, not robotic. You're talking to a busy cafe owner.
- Use ₹ for currency (Indian Rupees).

APP PAGES (for context — the user can navigate to these in the sidebar):
- Dashboard: revenue/profit metrics, daily revenue chart, expiry alerts, low stock warnings
- Menu Management: add/edit/remove menu items, set recipes (ingredients per item)
- Stock & Inventory: view all ingredients with expiry status, restock, dispose expired items
- AI Reports: generates a detailed AI analysis of sales, waste, and stock trends
- Sustainability: waste score (used vs wasted %), eco-friendly supplier alternatives, weekly trends
- AI Chat: this page — conversational Q&A with full database access

=== CAFE DATABASE ===

MENU ITEMS:
{json.dumps(db_context['menu'], indent=1)}

INVENTORY (current stock):
{json.dumps(db_context['inventory'], indent=1)}

RECIPES (what each menu item needs):
{json.dumps(db_context['recipes'], indent=1)}

SALES SUMMARY (total sold per item):
{json.dumps(db_context['sales_summary'], indent=1)}

DAILY SALES TOTALS:
{json.dumps(db_context['daily_totals'], indent=1)}

USAGE & WASTE LOG (aggregated):
{json.dumps(db_context['usage_and_waste'], indent=1)}

ECO-FRIENDLY ALTERNATIVES:
{json.dumps(db_context['eco_alternatives'], indent=1)}
"""


def _call_chat(messages, model_id):
    """Call OpenRouter with given messages and model. Retries with increasing tokens + timeout."""
    if not OPENROUTER_API_KEY:
        return None, None

    errors = []
    for config in RETRY_CONFIGS:
        try:
            response = requests.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_id,
                    "max_tokens": config["max_tokens"],
                    "messages": messages,
                },
                timeout=config["timeout"],
            )
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                if content and len(content.strip()) > 5:
                    return content.strip(), None
            else:
                errors.append(f"{model_id}: HTTP {response.status_code}")
        except requests.exceptions.Timeout:
            errors.append(f"{model_id}: Timed out after {config['timeout']}s")
            continue
        except Exception as e:
            errors.append(f"{model_id}: {str(e)[:80]}")
            continue

    return None, errors


def _call_with_fallbacks(messages, primary_model_id):
    """Try primary model, then fallback models. Returns (response, model_used, errors)."""
    all_errors = []

    # Try primary
    result, errors = _call_chat(messages, primary_model_id)
    if result:
        return result, primary_model_id, []
    if errors:
        all_errors.extend(errors)

    # Fallback chain – try other available models
    fallback_order = [
        "google/gemini-2.5-flash-preview-05-20",
        "openai/gpt-4.1-mini",
        "anthropic/claude-sonnet-4.6",
    ]
    for fb in fallback_order:
        if fb != primary_model_id:
            result, errors = _call_chat(messages, fb)
            if result:
                return result, fb, all_errors
            if errors:
                all_errors.extend(errors)

    return None, None, all_errors


def render(global_date=None, global_date_str=None):
    st.title("💬 AI Chat")

    with st.expander("ℹ️ **What is this page?** (click to read)", expanded=False):
        st.markdown(
            """
            Chat with an AI that knows **everything about your cafe** – menu, sales, stock,
            waste, recipes, eco alternatives. Ask it anything:

            - *"Which item has the highest profit margin?"*
            - *"How much milk do I need for next week?"*
            - *"What should I do about the bread waste?"*
            - *"Give me a weekend strategy to boost sales"*
            - *"Compare week 1 vs week 3 performance"*

            **Choose your AI model** from the dropdown – different models have different strengths.
            If your chosen model fails, the app automatically tries other models.

            **Chat history is saved** in the database. Use "Clear Chat" to start fresh.
            """
        )

    has_key = bool(OPENROUTER_API_KEY.strip())
    if not has_key:
        st.warning(
            "🔒 **No API key – chat is disabled.** "
            "Clone this repo and add your OpenRouter API key to `.env` to use this feature.",
            icon="🔑",
        )
        return

    # ─── Model Selector + Clear Chat ───
    col_model, col_clear = st.columns([3, 1])
    with col_model:
        selected_model = st.selectbox(
            "Choose AI Model",
            list(AVAILABLE_MODELS.keys()),
            help="Pick which AI model to chat with. Pro models are smarter but slower.",
        )
    with col_clear:
        st.markdown("")
        st.markdown("")
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state["confirm_clear"] = True

    # Confirmation dialog
    if st.session_state.get("confirm_clear"):
        with st.container(border=True):
            st.warning("**Are you sure you want to clear all chat history?** This cannot be undone.")
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("Yes, clear it", use_container_width=True, type="primary"):
                    clear_chat_history()
                    st.session_state.pop("confirm_clear", None)
                    st.session_state.pop("chat_messages", None)
                    st.rerun()
            with col_no:
                if st.button("Cancel", use_container_width=True):
                    st.session_state.pop("confirm_clear", None)
                    st.rerun()

    model_id = AVAILABLE_MODELS[selected_model]

    st.markdown("---")

    # ─── Load Chat History ───
    if "chat_messages" not in st.session_state:
        history = get_chat_history()
        st.session_state["chat_messages"] = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in history
        ]

    # ─── Display Chat Messages ───
    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ─── Example Prompts ───
    EXAMPLE_PROMPTS = [
        "Imagine it's April 1st. Based on March's data, give me a step-by-step action plan – what to restock, what to cut from the menu, and what to promote",
        "Calculate cost to make vs selling price for every menu item. Show it as a proper table with columns: Item, Cost (₹), Price (₹), Margin %, Units Sold. Sort by margin",
        "Our bread and milk waste is high. Figure out which menu items use them, and suggest a realistic plan to reduce waste by 50%",
        "Find me hidden money – which items have the best profit margin but aren't selling enough? How do I push them?",
        "Compare Saturday vs Monday sales item by item. What should I stock extra for weekends and what can I skip on weekdays?",
    ]

    with st.expander("💡 **Try an example question** (click to pick one)"):
        cols = st.columns(2)
        for i, example in enumerate(EXAMPLE_PROMPTS):
            with cols[i % 2]:
                if st.button(example, key=f"example_{i}", use_container_width=True):
                    st.session_state["use_example"] = example
                    st.rerun()

    # ─── Notices near input ───
    if model_id in PRO_MODELS:
        st.caption("⏳ Pro models can take a little more time. Please be patient and don't reload the page.")
    st.caption("⚠️ Don't reload or switch pages while AI is responding – it will cancel the request.")

    # ─── Chat Input ───
    # Check if example was selected
    example_prompt = st.session_state.pop("use_example", None)
    typed_prompt = st.chat_input("Ask anything about your cafe...")
    prompt = example_prompt or typed_prompt

    if prompt:
        # Show user message
        st.session_state["chat_messages"].append({"role": "user", "content": prompt})
        save_chat_message("user", prompt)

        with st.chat_message("user"):
            st.markdown(prompt)

        # Show loading animation
        with st.chat_message("assistant"):
            loading_placeholder = st.empty()

            # Animate loading words
            db_context = get_full_db_context()

            # Build messages for API
            system_msg = {"role": "system", "content": _get_system_prompt(db_context)}
            # Send last 20 messages to keep within token limits
            recent_messages = st.session_state["chat_messages"][-20:]
            chat_msgs = [system_msg] + [
                {"role": m["role"], "content": m["content"]}
                for m in recent_messages
            ]

            # Animated loading
            response_text = None
            used_model = None
            api_errors = []

            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(_call_with_fallbacks, chat_msgs, model_id)

                # Show loading animation while waiting
                words_shown = []
                start_time = time.time()
                while not future.done():
                    word = random.choice(LOADING_WORDS)
                    while word in words_shown[-3:] if len(words_shown) >= 3 else False:
                        word = random.choice(LOADING_WORDS)
                    words_shown.append(word)

                    elapsed = time.time() - start_time
                    dots = "." * (int(elapsed * 2) % 4)
                    loading_placeholder.markdown(f"*{word}{dots}*")
                    time.sleep(random.uniform(1.5, 3.0))

                response_text, used_model, api_errors = future.result()

            loading_placeholder.empty()

            if response_text:
                st.session_state["chat_messages"].append({"role": "assistant", "content": response_text})
                save_chat_message("assistant", response_text, used_model or model_id)
            else:
                error_lines = ["**All AI models failed to respond.** Here's what happened:\n"]
                for err in api_errors:
                    error_lines.append(f"- `{err}`")
                error_lines.append("\n**What you can do:**")
                error_lines.append("- Check your internet connection")
                error_lines.append("- Verify your API key in `.env` is valid")
                error_lines.append("- Try a different model from the dropdown")
                error_lines.append("- Try again in a few seconds (rate limits reset quickly)")
                error_msg = "\n".join(error_lines)

                st.session_state["chat_messages"].append({"role": "assistant", "content": error_msg})
                save_chat_message("assistant", error_msg, "error")

            st.rerun()
