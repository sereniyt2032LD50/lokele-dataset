import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).resolve().parent

BASE_URL = "https://www.bible.com/bible/1496/ACT.6.NTKE58"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        page = await browser.new_page()

        try:
            print(f"Inspecting Acts 6: {BASE_URL}")

            response = await page.goto(
                BASE_URL,
                wait_until="domcontentloaded",
                timeout=120000,
            )

            await page.wait_for_timeout(3000)

            html = await page.content()

            output_file = OUTPUT_DIR / "diagnostic_ACT_6_NTKE58.html"

            output_file.write_text(
                html,
                encoding="utf-8",
            )

            print(
                f"HTTP status: "
                f"{response.status if response else 'No response'}"
            )

            print(f"Saved: {output_file.name}")
            print(f"HTML size: {len(html):,} bytes")

        except Exception as e:
            print(f"ERROR: {e}")

        finally:
            await page.close()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())