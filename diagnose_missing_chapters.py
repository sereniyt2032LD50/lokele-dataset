import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright


BASE_DIR = Path(__file__).resolve().parent

# Bible.com
LOKELE_VERSION = "1496"
ENGLISH_VERSION = "206"

TARGETS = [
    ("LUK", "Luke", 15),
    ("ACT", "Acts", 6),
    ("2CO", "2 Corinthians", 6),
    ("2CO", "2 Corinthians", 7),
]


async def extract_page(page, url, label):

    print("\n" + "=" * 80)
    print(f"PROCESSING: {label}")
    print(url)
    print("=" * 80)

    try:
        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        # Give Bible.com/React time to populate the page
        await page.wait_for_timeout(5000)

        print(f"Page title: {await page.title()}")

        # ----------------------------------------------------
        # Inspect visible text
        # ----------------------------------------------------

        body_text = await page.locator("body").inner_text()

        print("\n--- BODY TEXT SAMPLE ---")
        print(body_text[:5000])

        # ----------------------------------------------------
        # Look for content spans
        # ----------------------------------------------------

        content_elements = await page.locator(
            "span.content"
        ).all()

        print(
            f"\nspan.content elements found: "
            f"{len(content_elements)}"
        )

        for i, element in enumerate(content_elements[:20]):

            try:
                text = await element.inner_text()

                print(
                    f"\nCONTENT [{i}]"
                )
                print(repr(text[:500]))

            except Exception as e:
                print(
                    f"Could not read content [{i}]: {e}"
                )

        # ----------------------------------------------------
        # Search page HTML for USFM chapter ID
        # ----------------------------------------------------

        html = await page.content()

        print("\n--- USFM ID SEARCH ---")

        # Example:
        # LUK.15.
        code = label.split(".")[0]

        if f"{code}." in html:
            print(
                f"Found references to {code}. in page HTML."
            )
        else:
            print(
                f"No obvious {code}. reference found in page HTML."
            )

        # ----------------------------------------------------
        # Save raw diagnostic HTML
        # ----------------------------------------------------

        safe_name = (
            label
            .replace(".", "_")
            .replace(" ", "_")
        )

        html_path = BASE_DIR / f"diagnostic_{safe_name}.html"

        html_path.write_text(
            html,
            encoding="utf-8"
        )

        print(
            f"\nRaw HTML saved to:\n{html_path}"
        )

        # ----------------------------------------------------
        # Save visible text
        # ----------------------------------------------------

        text_path = BASE_DIR / f"diagnostic_{safe_name}.txt"

        text_path.write_text(
            body_text,
            encoding="utf-8"
        )

        print(
            f"Visible text saved to:\n{text_path}"
        )

    except Exception as e:

        print(
            f"\n❌ ERROR processing {label}:"
        )

        print(repr(e))


async def main():

    print("=" * 80)
    print("LOKELE MISSING-CHAPTER DIAGNOSTIC")
    print("=" * 80)

    print("\nThis diagnostic will inspect ONLY:")
    print("  Luke 15")
    print("  Acts 6")
    print("  2 Corinthians 6")
    print("  2 Corinthians 7")

    print(
        "\nExisting JSONL files will NOT be modified."
    )

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page(
            viewport={
                "width": 1280,
                "height": 1000
            }
        )

        for code, book_name, chapter in TARGETS:

            # ------------------------------------------------
            # Lokele page
            # ------------------------------------------------

            lokele_url = (
                f"https://www.bible.com/bible/"
                f"{LOKELE_VERSION}/"
                f"{code}.{chapter}.NTKE58"
            )

            label = (
                f"{code}.{chapter}.NTKE58"
            )

            await extract_page(
                page,
                lokele_url,
                label
            )

            # ------------------------------------------------
            # English page
            # ------------------------------------------------

            english_url = (
                f"https://www.bible.com/bible/"
                f"{ENGLISH_VERSION}/"
                f"{code}.{chapter}.WEBUS"
            )

            label = (
                f"{code}.{chapter}.WEBUS"
            )

            await extract_page(
                page,
                english_url,
                label
            )

        await browser.close()

    print("\n")
    print("=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)

    print(
        "\nNo existing dataset files were modified."
    )


if __name__ == "__main__":
    asyncio.run(main())