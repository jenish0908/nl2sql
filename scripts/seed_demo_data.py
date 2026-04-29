"""
Seed script for the NL2SQL demo database.
Run with: python -m scripts.seed_demo_data
Or directly: python scripts/seed_demo_data.py
"""
import os
import sys
import random
from datetime import datetime, timedelta, date
from decimal import Decimal

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "SYNC_DATABASE_URL",
    "postgresql://nl2sql:nl2sql@localhost:5432/nl2sql_db",
)

CITIES = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"]
TIERS = ["free", "premium", "enterprise"]
TIER_WEIGHTS = [0.6, 0.3, 0.1]

CATEGORIES = ["Electronics", "Clothing", "Home & Garden", "Sports"]

PRODUCTS = [
    ("Wireless Headphones", "Electronics", 89.99, 38.00),
    ("Smart Watch", "Electronics", 199.99, 85.00),
    ("USB-C Hub", "Electronics", 49.99, 18.00),
    ("Laptop Stand", "Electronics", 39.99, 14.00),
    ("Mechanical Keyboard", "Electronics", 129.99, 55.00),
    ("Running Shoes", "Clothing", 79.99, 32.00),
    ("Yoga Pants", "Clothing", 44.99, 16.00),
    ("Winter Jacket", "Clothing", 149.99, 62.00),
    ("Cotton T-Shirt", "Clothing", 19.99, 6.00),
    ("Baseball Cap", "Clothing", 24.99, 8.00),
    ("Garden Hose", "Home & Garden", 34.99, 13.00),
    ("Plant Pots Set", "Home & Garden", 29.99, 10.00),
    ("LED Desk Lamp", "Home & Garden", 54.99, 22.00),
    ("Throw Pillow", "Home & Garden", 22.99, 8.00),
    ("Storage Basket", "Home & Garden", 17.99, 6.00),
    ("Yoga Mat", "Sports", 35.99, 13.00),
    ("Resistance Bands", "Sports", 24.99, 9.00),
    ("Water Bottle", "Sports", 27.99, 10.00),
    ("Jump Rope", "Sports", 14.99, 5.00),
    ("Gym Gloves", "Sports", 19.99, 7.00),
]

SUPPLIERS = [
    ("TechSource Global", "Shenzhen", 4.5, 14),
    ("FashionForward Ltd", "New York", 4.2, 7),
    ("GreenGrow Supplies", "Portland", 4.7, 10),
    ("SportsPro Wholesale", "Denver", 4.3, 8),
    ("HomeCraft Distributors", "Atlanta", 4.0, 12),
]

STATUSES = ["completed", "shipped", "processing", "cancelled"]
STATUS_WEIGHTS = [0.55, 0.25, 0.12, 0.08]

FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Barbara", "David", "Susan", "Richard", "Jessica", "Joseph", "Sarah",
    "Thomas", "Karen", "Charles", "Lisa", "Christopher", "Nancy", "Daniel", "Betty",
    "Matthew", "Margaret", "Anthony", "Sandra", "Donald", "Ashley",
    "Mark", "Dorothy", "Paul", "Kimberly", "Steven", "Emily", "Andrew", "Donna",
    "Kenneth", "Michelle", "Joshua", "Carol", "Kevin", "Amanda", "Brian", "Melissa",
    "George", "Deborah", "Edward", "Stephanie",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
    "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen",
    "Hill", "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera",
    "Campbell", "Mitchell", "Carter", "Roberts",
]


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def table_has_data(cur, table: str) -> bool:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    return cur.fetchone()[0] > 0


def seed_suppliers(cur) -> list[int]:
    rows = []
    for name, city, rating, lead_time in SUPPLIERS:
        rows.append((name, city, rating, lead_time))
    execute_values(
        cur,
        "INSERT INTO suppliers (name, city, rating, lead_time_days) VALUES %s RETURNING id",
        rows,
    )
    return [r[0] for r in cur.fetchall()]


def seed_products(cur, supplier_ids: list[int]) -> list[int]:
    category_supplier_map = {
        "Electronics": supplier_ids[0],
        "Clothing": supplier_ids[1],
        "Home & Garden": supplier_ids[4],
        "Sports": supplier_ids[3],
    }
    rows = []
    for name, category, price, cost in PRODUCTS:
        supplier_id = category_supplier_map[category]
        stock = random.randint(0, 200)
        rows.append((name, category, Decimal(str(price)), Decimal(str(cost)), supplier_id, stock))

    execute_values(
        cur,
        "INSERT INTO products (name, category, price, cost, supplier_id, stock_quantity) VALUES %s RETURNING id",
        rows,
    )
    return [r[0] for r in cur.fetchall()]


def seed_customers(cur) -> list[int]:
    used_emails: set[str] = set()
    rows = []
    for i in range(50):
        first = FIRST_NAMES[i % len(FIRST_NAMES)]
        last = LAST_NAMES[i % len(LAST_NAMES)]
        name = f"{first} {last}"
        base_email = f"{first.lower()}.{last.lower()}"
        email = f"{base_email}@example.com"
        counter = 1
        while email in used_emails:
            email = f"{base_email}{counter}@example.com"
            counter += 1
        used_emails.add(email)
        city = random.choice(CITIES)
        days_ago = random.randint(30, 730)
        signup_date = date.today() - timedelta(days=days_ago)
        tier = random.choices(TIERS, weights=TIER_WEIGHTS)[0]
        rows.append((name, email, city, signup_date, tier))

    execute_values(
        cur,
        "INSERT INTO customers (name, email, city, signup_date, tier) VALUES %s RETURNING id",
        rows,
    )
    return [r[0] for r in cur.fetchall()]


def seed_orders(cur, customer_ids: list[int], product_ids: list[int]) -> None:
    order_rows = []
    now = datetime.utcnow()

    for _ in range(200):
        customer_id = random.choice(customer_ids)
        days_ago = random.randint(0, 90)
        order_date = now - timedelta(days=days_ago, hours=random.randint(0, 23))
        status = random.choices(STATUSES, weights=STATUS_WEIGHTS)[0]
        delivery_city = random.choice(CITIES)
        order_rows.append((customer_id, order_date, status, Decimal("0.00"), delivery_city))

    execute_values(
        cur,
        "INSERT INTO orders (customer_id, order_date, status, total_amount, delivery_city) VALUES %s RETURNING id",
        order_rows,
    )
    order_ids = [r[0] for r in cur.fetchall()]

    item_rows = []
    order_totals: dict[int, Decimal] = {}

    for order_id in order_ids:
        num_items = random.randint(1, 4)
        selected_products = random.sample(product_ids, min(num_items, len(product_ids)))
        for product_id in selected_products:
            product_idx = product_ids.index(product_id)
            _, _, price, _ = PRODUCTS[product_idx % len(PRODUCTS)]
            unit_price = Decimal(str(price))
            quantity = random.randint(1, 3)
            discount_pct = random.choice([0.0, 0.0, 0.0, 5.0, 10.0, 15.0])
            item_rows.append((order_id, product_id, quantity, unit_price, discount_pct))
            line_total = unit_price * quantity * Decimal(str(1 - discount_pct / 100))
            order_totals[order_id] = order_totals.get(order_id, Decimal("0.00")) + line_total

    execute_values(
        cur,
        "INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_pct) VALUES %s",
        item_rows,
    )

    for order_id, total in order_totals.items():
        cur.execute(
            "UPDATE orders SET total_amount = %s WHERE id = %s",
            (total.quantize(Decimal("0.01")), order_id),
        )

    for _, _, price, _ in PRODUCTS:
        pass

    print(f"  Inserted {len(order_ids)} orders with {len(item_rows)} order items.")


def main():
    print("Connecting to database...")
    try:
        conn = get_connection()
    except Exception as exc:
        print(f"ERROR: Could not connect to database: {exc}")
        sys.exit(1)

    conn.autocommit = False
    cur = conn.cursor()

    try:
        if table_has_data(cur, "customers"):
            print("Database already seeded. Skipping.")
            cur.close()
            conn.close()
            return

        print("Seeding suppliers...")
        supplier_ids = seed_suppliers(cur)
        print(f"  Inserted {len(supplier_ids)} suppliers.")

        print("Seeding products...")
        product_ids = seed_products(cur, supplier_ids)
        print(f"  Inserted {len(product_ids)} products.")

        print("Seeding customers...")
        customer_ids = seed_customers(cur)
        print(f"  Inserted {len(customer_ids)} customers.")

        print("Seeding orders and order items...")
        seed_orders(cur, customer_ids, product_ids)

        conn.commit()
        print("Database seeded successfully!")

    except Exception as exc:
        conn.rollback()
        print(f"ERROR during seeding: {exc}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
