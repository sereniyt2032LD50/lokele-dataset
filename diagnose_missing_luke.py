
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).resolve().parent

CHAPTERS = [5, 7, 17, 18, 20, 23, 24]

BASE_URL = "https://www.bible.com/bible/1496/LUK.{}.NTKE58"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for chapter in CHAPTERS:
            url = BASE_URL.format(chapter)

            print(f"\nInspecting Luke {chapter}: {url}")

            page = await browser.new_page()

            try:
                response = await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=120000,
                )

                await page.wait_for_timeout(3000)

                html = await page.content()

                html_file = OUTPUT_DIR / (
                    f"diagnostic_LUK_{chapter}_NTKE58.html"
                )

                html_file.write_text(
                    html,
                    encoding="utf-8",
                )

                print(
                    f"HTTP status: "
                    f"{response.status if response else 'No response'}"
                )

                print(f"Saved: {html_file.name}")

            except Exception as e:
                print(f"ERROR on chapter {chapter}: {e}")

            finally:
                await page.close()

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())