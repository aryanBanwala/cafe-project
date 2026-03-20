# Design Documentation — Green Cafe Manager

## What This App Does

Green Cafe Manager helps small cafe owners track their ingredients, see what's selling, reduce food waste, and get AI-powered advice — all in one place. No spreadsheets, no complicated software.

---

## How It's Built

### The Big Picture

```
User opens app
    ↓
Streamlit loads app.py
    ↓
First run? → Load CSV files into SQLite database
    ↓
User picks a page from sidebar
    ↓
Page reads/writes to SQLite
    ↓
AI features? → Send data to OpenRouter API → Get response
                    ↓ (if fails)
              Rule-based fallback generates same output using Python
```

### Why These Choices

| Decision | What I Picked | Why |
|----------|--------------|-----|
| Frontend | Streamlit | Fast to build, interactive widgets, no HTML/CSS/JS needed |
| Database | SQLite | Just a file, no server to set up, works everywhere |
| AI Provider | OpenRouter | One API gives access to 7+ models (Gemini, Claude, GPT) with built-in fallback routing |
| Charts | Plotly | Interactive, looks professional, works natively with Streamlit |
| Tests | pytest | Simple, widely used, good enough for this scope |

---

## Database Design

### Tables

**menu** — What the cafe sells
- id, name, sell_price, category, is_active (soft delete flag), created_at

**recipes** — What ingredients each menu item needs
- id, menu_item_id (links to menu), ingredient, quantity_needed, unit

**inventory** — Raw ingredients in stock
- id, name, quantity, unit, cost_per_unit, expiry_date, purchased_date

**daily_sales** — What was sold each day
- id, date, day (Monday/Tuesday...), menu_item_id, quantity_sold

**usage_log** — How ingredients were used or wasted
- id, date, ingredient, quantity_used, type (used/wasted)

**eco_alternatives** — Greener supplier options
- id, ingredient, current_supplier, alternative_supplier, eco_rating, price_diff_pct, carbon_saved_kg

**chat_history** — AI chat messages
- id, role (user/assistant), content, model, created_at

### How Tables Connect

```
menu ──→ recipes ──→ inventory
  │                      ↑
  ↓                      │
daily_sales ──→ usage_log (auto-generated when sales are loaded)
```

When a sale happens:
1. Look up the menu item's recipe
2. For each ingredient in the recipe, calculate: quantity_needed × quantity_sold
3. Deduct that from inventory
4. Log it in usage_log as type "used"

When something expires or goes bad:
1. Mark quantity as disposed
2. Log it in usage_log as type "wasted"

This is how the sustainability dashboard gets its numbers — it just reads usage_log and compares "used" vs "wasted".

---

## How the AI Works

### AI Reports

The key design decision: **don't pre-calculate everything and ask AI to write pretty sentences.** That's just using AI as a text formatter.

Instead:
1. Collect raw data from the database (daily sales, inventory, recipes, waste logs)
2. Send ALL of it to the AI
3. Tell the AI: "Do your own math. Find patterns. Calculate burn rates. Connect waste to menu items."
4. The AI decides what's important and structures the report itself

**The prompt explicitly says:**
> "Do NOT restate data. The owner has a dashboard. DO YOUR OWN MATH. CROSS-REFERENCE ingredients with menu items. FIND ANOMALIES. PREDICT stockouts. Be ACTIONABLE."

### AI Chat

1. When user sends a message, the app loads the entire database state (menu, inventory, recipes, sales summary, waste, eco alternatives)
2. This goes into the system prompt as context
3. Last 20 messages are included for conversation continuity
4. The AI can answer any question about the cafe using real data

### Retry and Fallback System

```
Step 1: Try the user's chosen model
        → 4000 tokens, 60s timeout
        → 8000 tokens, 90s timeout
        → 12000 tokens, 120s timeout

Step 2: If all 3 attempts fail, try fallback models:
        → Gemini 2.5 Flash
        → GPT-4.1 Mini
        → Claude Sonnet 4.6

Step 3: If everything fails:
        AI Reports → Rule-based engine generates the report using Python
        AI Chat → Shows detailed error with what failed and what to do
```

The rule-based fallback calculates:
- Revenue, cost, profit (from sales × prices)
- Weekend vs weekday average revenue (from daily totals by day name)
- Anomaly detection (any day >1.5x average revenue)
- Expiry alerts (items where expiry_date < current date)
- Low stock warnings (items with quantity < 5)
- Waste summary (from usage_log where type = "wasted")

Same information, just formatted as templated markdown instead of AI-generated text.

---

## How Data Flows Through the App

### On First Run
```
CSV files in data/ folder
    ↓
database.py reads them and creates SQLite tables
    ↓
daily_sales.csv → for each sale, recipe is looked up → usage_log populated
    ↓
Waste entries seeded (realistic amounts, improving week over week)
    ↓
cafe.db file created (this is in .gitignore, not committed)
```

### Menu → Recipe → Stock Connection
```
User adds "Cappuccino" to menu at ₹180
    ↓
Sets recipe: 0.02kg Coffee + 0.15L Milk + 0.01kg Sugar
    ↓
Pre-loaded sales say 25 Cappuccinos sold on March 1
    ↓
App calculates: 25 × 0.02 = 0.5kg Coffee used
                25 × 0.15 = 3.75L Milk used
                25 × 0.01 = 0.25kg Sugar used
    ↓
These get logged in usage_log as "used"
    ↓
Stock levels in inventory reflect remaining quantities
```

### Waste Tracking
```
Ingredient expires or goes bad
    ↓
User goes to Stock → Dispose tab
    ↓
Picks ingredient, enters quantity, selects reason
    ↓
Stock reduced, usage_log entry created with type "wasted"
    ↓
Sustainability page reads usage_log
    ↓
Waste Score = used / (used + wasted) × 100
```

---

## Edge Cases and How They're Handled

| Situation | What Happens |
|-----------|-------------|
| Add menu item with same name | Database rejects it, shows "already exists" error |
| Remove a menu item | Soft delete — hidden from menu but sales history stays |
| Name too short (< 3 chars) | Live warning while typing + blocked on submit |
| Name too long (> 3 words) | Live warning while typing + blocked on submit |
| Price outside ₹10-1000 | Slider won't go beyond limits |
| Add item without recipe | Blocked — "can't track usage without a recipe" |
| Dispose more than available | Max limit set to current stock |
| Dispose ingredient used in recipes | Warning shown — "this is used in Cappuccino, Latte..." |
| AI model fails | Retries 3 times, then tries 3 fallback models |
| All AI fails | Reports use rule-based engine, Chat shows error details |
| No API key at all | Banner on every page, app works fully in fallback mode |
| User switches page during AI call | Request cancelled (Streamlit limitation, documented) |

---

## What's Not Built (and Why)

| Feature | Why I Skipped It |
|---------|-----------------|
| User authentication | Single-user tool, adds complexity without value for MVP |
| Image scanning | Would need Vision API, adds setup complexity |
| Push notifications | Streamlit doesn't support them natively |
| Streaming AI responses | OpenRouter streaming + Streamlit chat is unreliable |
| Multi-cafe support | Would need separate databases per tenant |
| ML forecasting model | Rule-based + LLM analysis is enough for MVP, real ML needs months of data |

---

## What I'd Build Next

1. **Barcode scanning** — scan ingredients to add them faster
2. **Multi-tenant** — OAuth login, each cafe gets its own database
3. **Automated reorder** — connect directly to suppliers when stock is low
4. **Trained ML model** — after collecting real usage data for 3+ months, train a model to predict demand more accurately than rule-based or LLM
5. **Slack/WhatsApp alerts** — notify the owner when something expires or stock runs out
6. **Streaming chat** — show AI response word by word instead of all at once
7. **Background processing** — queue AI requests so page switches don't cancel them

---

## Security

- API keys are never in code — loaded from `.env` file
- `.env` is in `.gitignore` — never committed
- `.env.example` shows the expected format
- If no API key is found, the app shows a clear banner and runs in fallback mode
- SQLite database is local — no data leaves the user's machine
- No real personal data anywhere — all synthetic
