import sqlite3

DB_NAME = "prices.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # lets you access columns by name instead of index
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # products table — one row per book, never duplicated
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT NOT NULL,
            url          TEXT,
            target_price REAL
        )
    """)

    # price_history — a new row every time we scrape, so we build up a timeline
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            price      REAL NOT NULL,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # speeds up "give me the latest price for product X" queries a lot
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_price_history_product
        ON price_history(product_id, scraped_at DESC)
    """)

    conn.commit()
    conn.close()
    print("[db] tables ready")


def upsert_product(title, url=None, target_price=None):
    # if the book already exists, just return its id — don't create a duplicate
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM products WHERE title = ?", (title,))
    row = cursor.fetchone()

    if row:
        product_id = row["id"]
    else:
        cursor.execute(
            "INSERT INTO products (title, url, target_price) VALUES (?, ?, ?)",
            (title, url, target_price),
        )
        product_id = cursor.lastrowid
        conn.commit()

    conn.close()
    return product_id


def insert_price(product_id, price):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO price_history (product_id, price) VALUES (?, ?)",
        (product_id, price),
    )
    conn.commit()
    conn.close()


def get_latest_price(product_id):
    # most recent snapshot
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT price FROM price_history WHERE product_id = ? ORDER BY scraped_at DESC LIMIT 1",
        (product_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return row["price"] if row else None


def get_previous_price(product_id):
    # the snapshot before the latest one — used to detect changes
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT price FROM price_history WHERE product_id = ? ORDER BY scraped_at DESC LIMIT 1 OFFSET 1",
        (product_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return row["price"] if row else None


def get_target_price(product_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT target_price FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    conn.close()
    return row["target_price"] if row else None


def get_price_history(product_id, limit=20):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ph.price, ph.scraped_at, p.title
        FROM price_history ph
        JOIN products p ON ph.product_id = p.id
        WHERE ph.product_id = ?
        ORDER BY ph.scraped_at DESC
        LIMIT ?
        """,
        (product_id, limit),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_all_products():
    # pulls every tracked product with its latest price — used by the dashboard
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            p.id,
            p.title,
            p.target_price,
            (
                SELECT ph.price FROM price_history ph
                WHERE ph.product_id = p.id
                ORDER BY ph.scraped_at DESC LIMIT 1
            ) AS latest_price,
            (
                SELECT ph.scraped_at FROM price_history ph
                WHERE ph.product_id = p.id
                ORDER BY ph.scraped_at DESC LIMIT 1
            ) AS last_scraped
        FROM products p
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
