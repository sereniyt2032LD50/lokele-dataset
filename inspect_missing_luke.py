
import re
from pathlib import Path
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent

MISSING = [
    "LUK.5.39",
    "LUK.7.50",
    "LUK.17.36",
    "LUK.18.43",
    "LUK.20.4",
    "LUK.23.51",
    "LUK.24.48",
]


def inspect_verse(usfm):
    parts = usfm.split(".")
    chapter = int(parts[1])

    filename = BASE_DIR / f"diagnostic_LUK_{chapter}_NTKE58.html"

    print("\n" + "=" * 70)
    print(f"VERSE: {usfm}")

    if not filename.exists():
        print(f"File not found: {filename.name}")
        return

    html = filename.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    elements = soup.select(f'[data-usfm="{usfm}"]')

    print(f"Matching verse elements: {len(elements)}")

    for i, element in enumerate(elements, start=1):
        print(f"\n--- Element {i} ---")
        print("HTML:")
        print(str(element)[:3000])

        content = element.select_one('[class*="content"]')

        if content:
            print("\nExtracted text:")
            print(content.get_text(" ", strip=True))
        else:
            print("\nNo content child found.")

    # Search the full HTML in case the verse is stored elsewhere.
    if not elements:
        print("\nSearching raw HTML for the verse ID...")

        matches = list(re.finditer(re.escape(usfm), html))

        for match in matches[:3]:
            start = max(0, match.start() - 300)
            end = min(len(html), match.end() + 1000)
            print(html[start:end])


for verse in MISSING:
    inspect_verse(verse)