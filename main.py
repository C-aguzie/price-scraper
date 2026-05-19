import argparse
import time

import schedule

from database import (
    init_db,
    upsert_product,
    insert_price,
    get_previous_price,
    get_target_price,
    get_all_products,
)
from scraper import scrape_all
from alerts import send_price_alert

# tweak these to change how the scraper behaves
MAX_PAGES      = 1     # 1 page = 20 books. go up to 50 to scrape the whole site
DROP_THRESHOLD = 0.10  # 0.10 = alert when price drops 10% or more
SCRAPE_INTERVAL_HOURS = 1


def scrape_and_store():
    print("\n" + "=" * 55)
    print("[job] starting scrape...")
    print("=" * 55)

    books = scrape_all(max_pages=MAX_PAGES)

    alerts_sent = 0
    new_books   = 0
    updated     = 0

    for book in books:
        product_id = upsert_product(title=book["title"], url=book["url"])

        previous_price = get_previous_price(product_id)
        current_price  = book["price"]

        insert_price(product_id, current_price)

        if previous_price is None:
            # first time we've seen this book, nothing to compare yet
            new_books += 1
            print(f"  [new]  £{current_price:.2f}  {book['title'][:55]}")
            continue

        updated += 1

        # check if price dropped enough to warrant an alert
        if previous_price > 0:
            pct_change = (previous_price - current_price) / previous_price

            if pct_change >= DROP_THRESHOLD:
                print(
                    f"  [drop] £{previous_price:.2f} → £{current_price:.2f} "
                    f"({pct_change*100:.1f}% off)  {book['title'][:35]}"
                )
                send_price_alert(
                    title=book["title"],
                    old_price=previous_price,
                    new_price=current_price,
                    target_price=get_target_price(product_id),
                    reason="drop",
                )
                alerts_sent += 1

        # check if it hit a target price the user set
        target = get_target_price(product_id)
        if target and current_price <= target and previous_price > target:
            print(f"  [🎯]   £{current_price:.2f} hit target £{target:.2f}  {book['title'][:35]}")
            send_price_alert(
                title=book["title"],
                old_price=previous_price,
                new_price=current_price,
                target_price=target,
                reason="target",
            )
            alerts_sent += 1

    print(f"\n[job] done — {new_books} new, {updated} updated, {alerts_sent} alert(s) sent")


def set_target(title_substring, target_price):
    """
    Call this to set a price alert goal for a specific book.
    Example: set_target("Sapiens", 10.00)
    """
    import sqlite3
    from database import DB_NAME

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE products SET target_price = ? WHERE LOWER(title) LIKE ?",
        (target_price, f"%{title_substring.lower()}%"),
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()

    if affected:
        print(f"[target] set £{target_price:.2f} for '{title_substring}' ({affected} match(es))")
    else:
        print(f"[target] no match for '{title_substring}' — run a scrape first so the book exists in the db")


def show_dashboard():
    products = get_all_products()
    if not products:
        print("[dash] nothing tracked yet — run a scrape first")
        return

    print(f"\n{'─'*72}")
    print(f"{'ID':<5} {'Price':<10} {'Target':<10} {'Last Scraped':<22} Title")
    print(f"{'─'*72}")
    for p in products:
        price   = f"£{p['latest_price']:.2f}" if p["latest_price"] else "—"
        target  = f"£{p['target_price']:.2f}" if p["target_price"] else "—"
        scraped = p["last_scraped"][:19] if p["last_scraped"] else "never"
        title   = p["title"][:35]
        print(f"{p['id']:<5} {price:<10} {target:<10} {scraped:<22} {title}")
    print(f"{'─'*72}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Price Scraper")
    parser.add_argument("--once",      action="store_true", help="Scrape once and exit")
    parser.add_argument("--dashboard", action="store_true", help="Print tracked products and exit")
    args = parser.parse_args()

    init_db()

    if args.dashboard:
        show_dashboard()
    elif args.once:
        scrape_and_store()
        show_dashboard()
    else:
        print(f"[scheduler] running every {SCRAPE_INTERVAL_HOURS}h — ctrl+c to stop")
        scrape_and_store()
        schedule.every(SCRAPE_INTERVAL_HOURS).hours.do(scrape_and_store)
        while True:
            schedule.run_pending()
            time.sleep(60)
