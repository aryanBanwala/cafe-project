import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

FALLBACK_MODELS = [
    "openai/gpt-4o-mini",
    "anthropic/claude-3.5-haiku",
    "google/gemini-flash-1.5",
]

RETRY_TOKENS = [2000, 4000, 6000]


def call_ai(prompt, system_prompt=None):
    """
    Call OpenRouter API with fallback models and increasing token limits.
    Returns the AI response text, or None if all attempts fail.
    """
    if not OPENROUTER_API_KEY:
        return None

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    for max_tokens in RETRY_TOKENS:
        try:
            response = requests.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": FALLBACK_MODELS[0],
                    "models": FALLBACK_MODELS,
                    "route": "fallback",
                    "max_tokens": max_tokens,
                    "messages": messages,
                },
                timeout=30,
            )
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                if content and len(content.strip()) > 10:
                    return content.strip()
        except Exception:
            continue

    return None


def generate_weekly_report(report_data):
    """
    Generate an AI-powered weekly report. Falls back to rule-based if AI fails.

    report_data should contain:
        - period: str (e.g., "Week 1: March 1-7")
        - total_revenue: float
        - total_cost: float
        - total_profit: float
        - top_sellers: list of {name, total_sold, revenue}
        - daily_summary: list of {date, day, revenue, total_items}
        - expiring_items: list of {name, expiry_date, quantity, unit}
        - expired_items: list of {name, quantity, unit}
        - waste_log: list of {ingredient, total_wasted}
        - low_stock: list of {name, quantity, unit}
    """
    system_prompt = """You are a sharp cafe business analyst. You receive raw cafe data and must ANALYZE it yourself.

CRITICAL RULES:
- Do NOT restate data. The owner has a dashboard – they can read numbers.
- DO YOUR OWN MATH: calculate burn rates, margins per item, daily averages, trend slopes, predicted stockout dates.
- CROSS-REFERENCE: connect ingredients to the menu items that use them. If milk expires in 3 days and Cold Coffee uses 0.25L milk, say exactly how many Cold Coffees to push.
- FIND ANOMALIES: any day with revenue >30% above/below average – flag it, explain possible why.
- PREDICT: based on daily usage, when will each ingredient run out? Be specific with dates.
- Be ACTIONABLE: every insight must end with "do this" not "consider this".
- Use simple English. Write for a busy cafe owner, not a data scientist.
- Use markdown headers, bold, bullet points. Structure it however makes the analysis clearest – you decide the sections.
"""

    prompt = f"""Analyze this raw cafe data for the period: {report_data['period']}.

I'm giving you everything – sales, daily breakdown, ingredients, recipes, stock levels, waste.
Do your own calculations. Find what I'd miss by just looking at the numbers.

=== PER-ITEM SALES (name, units sold, revenue, cost, profit) ===
{json.dumps(report_data['top_sellers'], indent=1)}

=== DAY-BY-DAY (date, day name, daily revenue, total items sold) ===
{json.dumps(report_data['daily_summary'], indent=1)}

=== FULL INVENTORY (name, current qty, unit, expiry date, cost per unit) ===
{json.dumps(report_data.get('inventory', []), indent=1)}

=== RECIPES (menu item → ingredients needed per serving) ===
{json.dumps(report_data.get('recipes', []), indent=1)}

=== ITEMS EXPIRING WITHIN 7 DAYS ===
{json.dumps(report_data['expiring_items'], indent=1)}

=== ALREADY EXPIRED / WASTED ===
{json.dumps(report_data['expired_items'], indent=1)}

=== WASTE LOG ===
{json.dumps(report_data['waste_log'], indent=1)}

=== LOW STOCK ===
{json.dumps(report_data['low_stock'], indent=1)}

Now analyze. Calculate burn rates. Find correlations between waste and menu items.
Detect day-of-week patterns. Predict stockouts. Suggest specific actions with numbers.
"""

    ai_response = call_ai(prompt, system_prompt)

    if ai_response:
        return {"source": "ai", "report": ai_response}

    # Rule-based fallback
    return {"source": "fallback", "report": _generate_fallback_report(report_data)}


def _generate_fallback_report(data):
    """Generate a rule-based report when AI is unavailable."""
    lines = []
    lines.append(f"## Weekly Report: {data['period']}")
    lines.append("")

    # Revenue summary
    lines.append("### Sales Summary")
    lines.append(f"- **Total Revenue:** ₹{data['total_revenue']:,.0f}")
    lines.append(f"- **Total Cost:** ₹{data['total_cost']:,.0f}")
    lines.append(f"- **Profit:** ₹{data['total_profit']:,.0f}")
    margin = data['total_profit'] / max(data['total_revenue'], 1) * 100
    lines.append(f"- **Profit Margin:** {margin:.1f}%")
    lines.append("")

    # Top sellers
    lines.append("### Top Sellers")
    for i, item in enumerate(data['top_sellers'][:5], 1):
        lines.append(f"{i}. **{item['name']}** - {item['total_sold']} sold (₹{item['revenue']:,.0f})")
    lines.append("")

    # Weekend analysis
    weekend_days = [d for d in data['daily_summary'] if d['day'] in ('Saturday', 'Sunday')]
    weekday_days = [d for d in data['daily_summary'] if d['day'] not in ('Saturday', 'Sunday')]

    if weekend_days and weekday_days:
        avg_weekend = sum(d['revenue'] for d in weekend_days) / len(weekend_days)
        avg_weekday = sum(d['revenue'] for d in weekday_days) / len(weekday_days)
        spike = ((avg_weekend - avg_weekday) / max(avg_weekday, 1)) * 100

        lines.append("### Weekend vs Weekday Pattern")
        lines.append(f"- Average weekday revenue: ₹{avg_weekday:,.0f}")
        lines.append(f"- Average weekend revenue: ₹{avg_weekend:,.0f}")
        if spike > 20:
            lines.append(f"- **Weekend spike detected: +{spike:.0f}%** compared to weekdays")
            lines.append("- Suggestion: Stock extra milk, coffee beans, and bread before weekends")
        lines.append("")

    # Anomaly detection - find days with revenue > 1.5x average
    if data['daily_summary']:
        avg_revenue = sum(d['revenue'] for d in data['daily_summary']) / len(data['daily_summary'])
        anomalies = [d for d in data['daily_summary'] if d['revenue'] > avg_revenue * 1.5]
        if anomalies:
            lines.append("### Anomalies Detected")
            for a in anomalies:
                lines.append(f"- **{a['date']} ({a['day']})**: ₹{a['revenue']:,.0f} revenue "
                           f"({((a['revenue']-avg_revenue)/avg_revenue*100):.0f}% above average)")
            lines.append("")

    # Expiry alerts
    if data['expiring_items']:
        lines.append("### Expiring Soon - Action Needed!")
        for item in data['expiring_items']:
            lines.append(f"- **{item['name']}**: {item['quantity']:.1f} {item['unit']} "
                       f"expires on {item['expiry_date']}")
        lines.append("- Suggestion: Create combo deals or specials using these ingredients before they expire")
        lines.append("")

    if data['expired_items']:
        lines.append("### Already Expired - Waste Alert!")
        for item in data['expired_items']:
            lines.append(f"- **{item['name']}**: {item['quantity']:.1f} {item['unit']} wasted")
        lines.append("- Suggestion: Reduce order quantity next time or order more frequently")
        lines.append("")

    # Low stock
    if data['low_stock']:
        lines.append("### Low Stock - Reorder Soon")
        for item in data['low_stock']:
            lines.append(f"- **{item['name']}**: Only {item['quantity']:.1f} {item['unit']} remaining")
        lines.append("")

    # Waste summary
    if data['waste_log']:
        lines.append("### Waste Summary")
        for w in data['waste_log']:
            lines.append(f"- {w['ingredient']}: {w['total_wasted']:.2f} units wasted")
        lines.append("")

    lines.append("---")
    lines.append("*This report was generated using rule-based analysis (AI was unavailable).*")

    return "\n".join(lines)


def generate_sustainability_insight(sustainability_data):
    """Generate AI insight for sustainability tab."""
    system_prompt = """You are a sustainability advisor for a small cafe.
Give practical, encouraging advice about reducing waste and being eco-friendly.
Keep it short (3-4 bullet points). Use simple English."""

    prompt = f"""Based on this cafe's sustainability data, give actionable advice:

Waste Score: {sustainability_data.get('waste_score', 'N/A')}%
Items Wasted: {json.dumps(sustainability_data.get('wasted_items', []))}
Eco Alternatives Available: {json.dumps(sustainability_data.get('eco_alternatives', []))}
Carbon Saved So Far: {sustainability_data.get('carbon_saved', 0):.1f} kg CO2

Give 3-4 specific, actionable suggestions to improve their sustainability score."""

    ai_response = call_ai(prompt, system_prompt)

    if ai_response:
        return {"source": "ai", "insight": ai_response}

    # Fallback
    tips = []
    if sustainability_data.get('wasted_items'):
        tips.append("Reduce order quantities for frequently wasted items to avoid spoilage.")
    if sustainability_data.get('eco_alternatives'):
        top_eco = sustainability_data['eco_alternatives'][0] if sustainability_data['eco_alternatives'] else None
        if top_eco:
            tips.append(f"Switch {top_eco['ingredient']} to {top_eco['alternative_supplier']} "
                       f"to save {top_eco['carbon_saved_kg']} kg CO2 per unit.")
    tips.append("Order perishables more frequently in smaller quantities to reduce waste.")
    tips.append("Consider composting food waste to further reduce your environmental impact.")

    return {"source": "fallback", "insight": "\n".join(f"- {t}" for t in tips)}
