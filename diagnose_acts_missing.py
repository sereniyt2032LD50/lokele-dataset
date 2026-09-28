from pathlib import Path
from playwright.sync_api import sync_playwright

URLS = [
    ("ACT", 7),
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    for book_code, chapter in URLS:
        url = f"https://www.bible.com/bible/1496/{book_code}.{chapter}.NTKE58"

        print("=" * 70)
        print(f"PROCESSING {url}")

        page = browser.new_page()

        try:
            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000
            )

            page.wait_for_timeout(5000)

            print("HTTP:", response.status if response else "NO RESPONSE")

            html = page.content()

            filename = f"diagnostic_{book_code}_{chapter}_NTKE58.html"
            Path(filename).write_text(html, encoding="utf-8")

            print(f"Saved: {filename}")
            print(f"HTML length: {len(html):,}")

        except Exception as e:
            print("ERROR:", e)

        finally:
            page.close()

    browser.close()