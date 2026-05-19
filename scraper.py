import re
import requests
from bs4 import BeautifulSoup

BASE_URL = "http://books.toscrape.com/catalogue/"

# The site spells out star ratings instead of using numbers, so we convert them
RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def parse_price(raw):
    # Strips the £ sign and anything weird, returns a clean float
    cleaned = re.sub(r"[^\d.]", "", raw)
    return float(cleaned)


def scrape_page(page_num=1):
    # Page 1 has a different URL format than the rest, hence the if/else
    if page_num == 1:
        url = "http://books.toscrape.com/"
    else:
        url = f"{BASE_URL}page-{page_num}.html"

    headers = {
        # Without this, the site returns a 403. Pretending to be a browser fixes it.
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[scraper] couldn't fetch page {page_num}: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    books = soup.find_all("article", class_="product_pod")

    results = []
    for book in books:
        title  = book.h3.a["title"]
        price  = parse_price(book.find("p", class_="price_color").text)
        rating = RATING_MAP.get(book.p["class"][1], 0)
        href   = book.h3.a["href"].replace("../", "")
        book_url = BASE_URL + href

        results.append({
            "title":  title,
            "price":  price,
            "rating": rating,
            "url":    book_url,
        })

    return results


def scrape_all(max_pages=1):
    all_books = []
    for page in range(1, max_pages + 1):
        print(f"[scraper] page {page} of {max_pages}...")
        books = scrape_page(page)
        if not books:
            break
        all_books.extend(books)

    print(f"[scraper] finished — {len(all_books)} books total")
    return all_books


if __name__ == "__main__":
    # Quick sanity check — run this file directly to see if scraping works
    books = scrape_all(max_pages=1)
    for b in books[:5]:
        print(f"  £{b['price']:.2f}  ({'★' * b['rating']})  {b['title'][:60]}")
