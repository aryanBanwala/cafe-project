import sqlite3
import csv
import os
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(__file__), "cafe.db")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database():
    """Create tables and load CSV data if database doesn't exist yet."""
    first_run = not os.path.exists(DB_PATH)
    conn = get_connection()

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            sell_price REAL NOT NULL,
            category TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            menu_item_id INTEGER NOT NULL,
            ingredient TEXT NOT NULL,
            quantity_needed REAL NOT NULL,
            unit TEXT NOT NULL,
            FOREIGN KEY (menu_item_id) REFERENCES menu(id)
        );

        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity REAL NOT NULL DEFAULT 0,
            unit TEXT NOT NULL,
            cost_per_unit REAL NOT NULL,
            expiry_date TEXT,
            purchased_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            ingredient TEXT NOT NULL,
            quantity_used REAL NOT NULL,
            type TEXT NOT NULL DEFAULT 'used'
        );

        CREATE TABLE IF NOT EXISTS daily_sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            day TEXT NOT NULL,
            menu_item_id INTEGER NOT NULL,
            quantity_sold INTEGER NOT NULL,
            FOREIGN KEY (menu_item_id) REFERENCES menu(id)
        );

        CREATE TABLE IF NOT EXISTS eco_alternatives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ingredient TEXT NOT NULL,
            current_supplier TEXT,
            alternative_supplier TEXT,
            eco_rating TEXT,
            price_diff_pct REAL,
            carbon_saved_kg REAL
        );

        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            model TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    if first_run:
        _load_csv_data(conn)

    conn.commit()
    conn.close()


def _load_csv_data(conn):
    """Load all CSV files into the database on first run."""
    # Load menu
    with open(os.path.join(DATA_DIR, "menu.csv")) as f:
        reader = csv.DictReader(f)
        for row in reader:
            conn.execute(
                "INSERT INTO menu (id, name, sell_price, category) VALUES (?, ?, ?, ?)",
                (int(row["id"]), row["name"], float(row["sell_price"]), row["category"]),
            )

    # Load recipes
    with open(os.path.join(DATA_DIR, "recipes.csv")) as f:
        reader = csv.DictReader(f)
        for row in reader:
            conn.execute(
                "INSERT INTO recipes (menu_item_id, ingredient, quantity_needed, unit) VALUES (?, ?, ?, ?)",
                (int(row["menu_item_id"]), row["ingredient"], float(row["quantity_needed"]), row["unit"]),
            )

    # Load inventory
    with open(os.path.join(DATA_DIR, "inventory_stock.csv")) as f:
        reader = csv.DictReader(f)
        for row in reader:
            conn.execute(
                "INSERT INTO inventory (id, name, quantity, unit, cost_per_unit, expiry_date, purchased_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (int(row["id"]), row["name"], float(row["quantity"]), row["unit"],
                 float(row["cost_per_unit"]), row["expiry_date"], row["purchased_date"]),
            )

    # Load daily sales
    with open(os.path.join(DATA_DIR, "daily_sales.csv")) as f:
        reader = csv.DictReader(f)
        for row in reader:
            conn.execute(
                "INSERT INTO daily_sales (date, day, menu_item_id, quantity_sold) VALUES (?, ?, ?, ?)",
                (row["date"], row["day"], int(row["menu_item_id"]), int(row["quantity_sold"])),
            )

    # Populate usage_log from loaded sales data (so sustainability page has data)
    sales = conn.execute("SELECT date, menu_item_id, quantity_sold FROM daily_sales").fetchall()
    recipes_cache = {}
    for sale in sales:
        mid = sale[1]
        if mid not in recipes_cache:
            recipes_cache[mid] = conn.execute(
                "SELECT ingredient, quantity_needed FROM recipes WHERE menu_item_id = ?", (mid,)
            ).fetchall()
        for recipe in recipes_cache[mid]:
            used = recipe[1] * sale[2]
            conn.execute(
                "INSERT INTO usage_log (date, ingredient, quantity_used, type) VALUES (?, ?, ?, 'used')",
                (sale[0], recipe[0], used),
            )

    # Simulate realistic waste – small cafes waste 10-20% of perishables
    # Total usage is ~6000 units, so ~800-1000 units waste = ~13-15% waste rate
    waste_items = [
        # Week 1 – no process yet, lots of over-ordering, expiry misses
        ("2026-03-01", "Milk", 18.0),
        ("2026-03-02", "Bread", 35.0),
        ("2026-03-03", "Milk", 15.0),
        ("2026-03-04", "Eggs", 20.0),
        ("2026-03-05", "Mushrooms", 8.0),
        ("2026-03-05", "Lettuce", 6.0),
        ("2026-03-06", "Paneer", 5.0),
        ("2026-03-06", "Bell Pepper", 4.0),
        ("2026-03-07", "Cheese", 5.0),
        ("2026-03-07", "Butter", 3.0),
        ("2026-03-07", "Sugar", 4.0),
        # Week 2 – still bad, learning curve
        ("2026-03-08", "Milk", 20.0),
        ("2026-03-09", "Bread", 30.0),
        ("2026-03-10", "Ginger", 3.0),
        ("2026-03-10", "Butter", 4.0),
        ("2026-03-11", "Lettuce", 5.0),
        ("2026-03-12", "Eggs", 18.0),
        ("2026-03-13", "Cheese", 6.0),
        ("2026-03-13", "Mushrooms", 5.0),
        ("2026-03-14", "Tomato Sauce", 3.0),
        ("2026-03-14", "Paneer", 4.0),
        ("2026-03-14", "Olive Oil", 2.0),
        # Week 3 – improving, owner started paying attention
        ("2026-03-15", "Milk", 12.0),
        ("2026-03-16", "Bread", 20.0),
        ("2026-03-17", "Mushrooms", 3.0),
        ("2026-03-18", "Paneer", 3.0),
        ("2026-03-19", "Bell Pepper", 2.0),
        ("2026-03-20", "Cheese", 3.0),
        ("2026-03-20", "Eggs", 10.0),
        ("2026-03-21", "Butter", 2.0),
        # Week 4 – best week, less waste
        ("2026-03-22", "Milk", 8.0),
        ("2026-03-23", "Bread", 14.0),
        ("2026-03-24", "Butter", 2.0),
        ("2026-03-25", "Lettuce", 2.0),
        ("2026-03-26", "Sugar", 3.0),
        ("2026-03-27", "Eggs", 8.0),
        ("2026-03-29", "Milk", 6.0),
        ("2026-03-31", "Bread", 10.0),
    ]
    for date, ingredient, qty in waste_items:
        conn.execute(
            "INSERT INTO usage_log (date, ingredient, quantity_used, type) VALUES (?, ?, ?, 'wasted')",
            (date, ingredient, qty),
        )

    # Load eco alternatives
    with open(os.path.join(DATA_DIR, "eco_alternatives.csv")) as f:
        reader = csv.DictReader(f)
        for row in reader:
            conn.execute(
                "INSERT INTO eco_alternatives (ingredient, current_supplier, alternative_supplier, eco_rating, price_diff_pct, carbon_saved_kg) VALUES (?, ?, ?, ?, ?, ?)",
                (row["ingredient"], row["current_supplier"], row["alternative_supplier"],
                 row["eco_rating"], float(row["price_diff_pct"]), float(row["carbon_saved_kg"])),
            )


# ─── Menu Operations ───

def get_menu_items(active_only=True):
    conn = get_connection()
    if active_only:
        rows = conn.execute("SELECT * FROM menu WHERE is_active = 1 ORDER BY category, name").fetchall()
    else:
        rows = conn.execute("SELECT * FROM menu ORDER BY category, name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_menu_item(name, sell_price, category):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO menu (name, sell_price, category) VALUES (?, ?, ?)",
            (name.strip(), sell_price, category),
        )
        menu_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()
        return menu_id, None
    except sqlite3.IntegrityError:
        conn.close()
        return None, f"'{name}' already exists in the menu."


def update_menu_item(item_id, name, sell_price, category):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE menu SET name = ?, sell_price = ?, category = ? WHERE id = ?",
            (name.strip(), sell_price, category, item_id),
        )
        conn.commit()
        conn.close()
        return True, None
    except sqlite3.IntegrityError:
        conn.close()
        return False, f"'{name}' already exists in the menu."


def soft_delete_menu_item(item_id):
    conn = get_connection()
    conn.execute("UPDATE menu SET is_active = 0 WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def restore_menu_item(item_id):
    conn = get_connection()
    conn.execute("UPDATE menu SET is_active = 1 WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


# ─── Recipe Operations ───

def get_recipes_for_item(menu_item_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM recipes WHERE menu_item_id = ?", (menu_item_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_recipes_for_item(menu_item_id, recipes):
    """Replace all recipes for a menu item. recipes = list of (ingredient, qty, unit)"""
    conn = get_connection()
    conn.execute("DELETE FROM recipes WHERE menu_item_id = ?", (menu_item_id,))
    for ingredient, qty, unit in recipes:
        conn.execute(
            "INSERT INTO recipes (menu_item_id, ingredient, quantity_needed, unit) VALUES (?, ?, ?, ?)",
            (menu_item_id, ingredient, qty, unit),
        )
    conn.commit()
    conn.close()


# ─── Inventory Operations ───

def get_inventory(as_of_date=None):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM inventory ORDER BY expiry_date").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_inventory_item(name, quantity, unit, cost_per_unit, expiry_date, purchased_date):
    conn = get_connection()
    conn.execute(
        "INSERT INTO inventory (name, quantity, unit, cost_per_unit, expiry_date, purchased_date) VALUES (?, ?, ?, ?, ?, ?)",
        (name.strip(), quantity, unit, cost_per_unit, expiry_date, purchased_date),
    )
    conn.commit()
    conn.close()


def update_inventory_quantity(item_id, new_quantity):
    conn = get_connection()
    conn.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (new_quantity, item_id))
    conn.commit()
    conn.close()


def restock_inventory(item_id, add_quantity, new_expiry=None):
    conn = get_connection()
    conn.execute(
        "UPDATE inventory SET quantity = quantity + ? WHERE id = ?",
        (add_quantity, item_id),
    )
    if new_expiry:
        conn.execute(
            "UPDATE inventory SET expiry_date = ? WHERE id = ?",
            (new_expiry, item_id),
        )
    conn.commit()
    conn.close()


def dispose_inventory(item_id, waste_quantity, dispose_date):
    """Mark some quantity as wasted and reduce stock."""
    conn = get_connection()
    item = conn.execute("SELECT * FROM inventory WHERE id = ?", (item_id,)).fetchone()
    if item:
        new_qty = max(0, item["quantity"] - waste_quantity)
        conn.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (new_qty, item_id))
        conn.execute(
            "INSERT INTO usage_log (date, ingredient, quantity_used, type) VALUES (?, ?, ?, 'wasted')",
            (dispose_date, item["name"], waste_quantity),
        )
    conn.commit()
    conn.close()


# ─── Sales Operations ───

def get_sales(start_date=None, end_date=None):
    conn = get_connection()
    query = """
        SELECT ds.*, m.name as item_name, m.sell_price, m.category
        FROM daily_sales ds
        JOIN menu m ON ds.menu_item_id = m.id
        WHERE 1=1
    """
    params = []
    if start_date:
        query += " AND ds.date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND ds.date <= ?"
        params.append(end_date)
    query += " ORDER BY ds.date, m.name"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_daily_sales(sales_date, day_name, items_sold):
    """
    Log sales for a day. items_sold = list of (menu_item_id, quantity_sold).
    Auto-deducts ingredients from inventory based on recipes.
    Returns (success, warnings).
    """
    conn = get_connection()
    warnings = []

    for menu_item_id, qty_sold in items_sold:
        if qty_sold <= 0:
            continue

        # Insert sale record
        conn.execute(
            "INSERT INTO daily_sales (date, day, menu_item_id, quantity_sold) VALUES (?, ?, ?, ?)",
            (sales_date, day_name, menu_item_id, qty_sold),
        )

        # Get recipe and deduct ingredients
        recipes = conn.execute(
            "SELECT ingredient, quantity_needed, unit FROM recipes WHERE menu_item_id = ?",
            (menu_item_id,),
        ).fetchall()

        for recipe in recipes:
            needed = recipe["quantity_needed"] * qty_sold
            inv = conn.execute(
                "SELECT id, quantity FROM inventory WHERE name = ?",
                (recipe["ingredient"],),
            ).fetchone()

            if inv:
                new_qty = inv["quantity"] - needed
                if new_qty < 0:
                    warnings.append(
                        f"Not enough {recipe['ingredient']}! Needed {needed:.2f} {recipe['unit']}, "
                        f"only {inv['quantity']:.2f} available."
                    )
                    new_qty = 0
                conn.execute(
                    "UPDATE inventory SET quantity = ? WHERE id = ?",
                    (new_qty, inv["id"]),
                )
                # Log usage
                conn.execute(
                    "INSERT INTO usage_log (date, ingredient, quantity_used, type) VALUES (?, ?, ?, 'used')",
                    (sales_date, recipe["ingredient"], needed),
                )

    conn.commit()
    conn.close()
    return True, warnings


# ─── Analytics Helpers ───

def get_revenue_and_cost(start_date=None, end_date=None):
    """Calculate total revenue and ingredient cost for a date range."""
    conn = get_connection()
    query = """
        SELECT ds.menu_item_id, m.name, m.sell_price, SUM(ds.quantity_sold) as total_sold
        FROM daily_sales ds
        JOIN menu m ON ds.menu_item_id = m.id
        WHERE 1=1
    """
    params = []
    if start_date:
        query += " AND ds.date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND ds.date <= ?"
        params.append(end_date)
    query += " GROUP BY ds.menu_item_id ORDER BY total_sold DESC"

    sales = conn.execute(query, params).fetchall()

    total_revenue = 0
    total_cost = 0
    items_detail = []

    for sale in sales:
        revenue = sale["sell_price"] * sale["total_sold"]
        total_revenue += revenue

        # Calculate cost from recipes
        recipes = conn.execute(
            "SELECT r.ingredient, r.quantity_needed, i.cost_per_unit, r.unit, i.unit as inv_unit "
            "FROM recipes r LEFT JOIN inventory i ON r.ingredient = i.name "
            "WHERE r.menu_item_id = ?",
            (sale["menu_item_id"],),
        ).fetchall()

        item_cost = 0
        for r in recipes:
            if r["cost_per_unit"]:
                item_cost += r["quantity_needed"] * r["cost_per_unit"]

        total_item_cost = item_cost * sale["total_sold"]
        total_cost += total_item_cost

        items_detail.append({
            "name": sale["name"],
            "total_sold": sale["total_sold"],
            "revenue": revenue,
            "cost": total_item_cost,
            "profit": revenue - total_item_cost,
        })

    conn.close()
    return {
        "total_revenue": total_revenue,
        "total_cost": total_cost,
        "total_profit": total_revenue - total_cost,
        "items": items_detail,
    }


def get_expiring_items(as_of_date, within_days=7):
    """Get items expiring within N days of the given date."""
    conn = get_connection()
    target = datetime.strptime(as_of_date, "%Y-%m-%d") + __import__("datetime").timedelta(days=within_days)
    rows = conn.execute(
        "SELECT * FROM inventory WHERE expiry_date <= ? AND expiry_date >= ? AND quantity > 0 ORDER BY expiry_date",
        (target.strftime("%Y-%m-%d"), as_of_date),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_expired_items(as_of_date):
    """Get items that have already expired."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM inventory WHERE expiry_date < ? AND quantity > 0 ORDER BY expiry_date",
        (as_of_date,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_low_stock_items(threshold_pct=0.2):
    """Get items where current quantity is less than 20% of original."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM inventory WHERE quantity > 0 ORDER BY quantity"
    ).fetchall()
    conn.close()
    # We consider low stock if quantity < 5 units (simple threshold)
    return [dict(r) for r in rows if r["quantity"] < 5]


def get_usage_log(start_date=None, end_date=None, log_type=None):
    conn = get_connection()
    query = "SELECT * FROM usage_log WHERE 1=1"
    params = []
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    if log_type:
        query += " AND type = ?"
        params.append(log_type)
    query += " ORDER BY date"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_eco_alternatives():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM eco_alternatives ORDER BY carbon_saved_kg DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_daily_sales_summary(start_date, end_date):
    """Get day-by-day sales totals."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT ds.date, ds.day, SUM(ds.quantity_sold * m.sell_price) as revenue,
               SUM(ds.quantity_sold) as total_items
        FROM daily_sales ds
        JOIN menu m ON ds.menu_item_id = m.id
        WHERE ds.date >= ? AND ds.date <= ?
        GROUP BY ds.date
        ORDER BY ds.date
    """, (start_date, end_date)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_waste_summary(start_date=None, end_date=None):
    """Get total waste from usage log."""
    conn = get_connection()
    query = """
        SELECT ingredient, SUM(quantity_used) as total_wasted
        FROM usage_log WHERE type = 'wasted'
    """
    params = []
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    query += " GROUP BY ingredient ORDER BY total_wasted DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ingredient_used_in_recipes(ingredient_name):
    """Check if an ingredient is used in any active menu item's recipe."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT m.name FROM recipes r
        JOIN menu m ON r.menu_item_id = m.id
        WHERE r.ingredient = ? AND m.is_active = 1
    """, (ingredient_name,)).fetchall()
    conn.close()
    return [r["name"] for r in rows]


# ─── Chat Operations ───

def save_chat_message(role, content, model=None):
    conn = get_connection()
    conn.execute(
        "INSERT INTO chat_history (role, content, model) VALUES (?, ?, ?)",
        (role, content, model),
    )
    conn.commit()
    conn.close()


def get_chat_history():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM chat_history ORDER BY id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def clear_chat_history():
    conn = get_connection()
    conn.execute("DELETE FROM chat_history")
    conn.commit()
    conn.close()


def get_full_db_context():
    """Get a summary of the entire database for AI chat context."""
    conn = get_connection()

    menu = conn.execute("SELECT name, sell_price, category, is_active FROM menu").fetchall()
    inventory = conn.execute("SELECT name, quantity, unit, cost_per_unit, expiry_date FROM inventory").fetchall()
    recipes = conn.execute("""
        SELECT m.name as menu_item, r.ingredient, r.quantity_needed, r.unit
        FROM recipes r JOIN menu m ON r.menu_item_id = m.id
    """).fetchall()
    sales_summary = conn.execute("""
        SELECT m.name, SUM(ds.quantity_sold) as total_sold, SUM(ds.quantity_sold * m.sell_price) as revenue
        FROM daily_sales ds JOIN menu m ON ds.menu_item_id = m.id
        GROUP BY m.name ORDER BY total_sold DESC
    """).fetchall()
    daily_totals = conn.execute("""
        SELECT date, day, SUM(quantity_sold) as items, COUNT(DISTINCT menu_item_id) as unique_items
        FROM daily_sales GROUP BY date ORDER BY date
    """).fetchall()
    waste = conn.execute("""
        SELECT ingredient, SUM(quantity_used) as total, type
        FROM usage_log GROUP BY ingredient, type ORDER BY total DESC
    """).fetchall()
    eco = conn.execute("SELECT * FROM eco_alternatives").fetchall()

    conn.close()

    return {
        "menu": [dict(r) for r in menu],
        "inventory": [dict(r) for r in inventory],
        "recipes": [dict(r) for r in recipes],
        "sales_summary": [dict(r) for r in sales_summary],
        "daily_totals": [dict(r) for r in daily_totals],
        "usage_and_waste": [dict(r) for r in waste],
        "eco_alternatives": [dict(r) for r in eco],
    }
