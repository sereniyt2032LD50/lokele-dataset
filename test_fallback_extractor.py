import re
from pathlib import Path
from collections import defaultdict

from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(
    r"C:\Users\aisha\Documents\Generative-AI\lokele_dataset"
)

# The four chapters that failed during the original scraping.
CHAPTERS_TO_TEST = [
    ("LUK", 15),
    ("ACT", 6),
    ("2CO", 6),
    ("2CO", 7),
]

# Lokele Bible.com version
LOKELE_VERSION = "NTKE58"


# ============================================================
# EXTRACT VERSES FROM HTML
# ============================================================

def extract_verses_from_html(html_content, book_code, chapter_number):

    """
    Extract Bible verses from Bible.com HTML.

    Uses:
        span[data-usfm]
        span[class*="content"]

    Returns:
        Dictionary containing verse IDs and their text.
    """

    soup = BeautifulSoup(html_content, "html.parser")

    extracted_verses = {}

    # Match USFM references such as:
    # LUK.15.1
    # ACT.6.3
    # 2CO.7.2

    expected_prefix = f"{book_code}.{chapter_number}."

    # Find all elements carrying a USFM verse reference.
    verse_elements = soup.select("span[data-usfm]")

    print(
        f"Verse containers found in HTML: {len(verse_elements)}"
    )

    for verse_element in verse_elements:

        verse_id = verse_element.get("data-usfm", "").strip()

        # Only process the requested book and chapter.
        if not verse_id.startswith(expected_prefix):
            continue

        # Confirm that the reference is a valid verse ID.
        match = re.fullmatch(
            rf"{re.escape(book_code)}\."
            rf"{chapter_number}\."
            rf"(\d+)",
            verse_id
        )

        if not match:
            continue

        verse_number = int(match.group(1))

        # Find the text container inside the verse element.
        content_element = verse_element.select_one(
            'span[class*="content"]'
        )

        if content_element is None:
            continue

        # Extract the actual verse text.
        verse_text = content_element.get_text(
            separator=" ",
            strip=True
        )

        # Normalize whitespace.
        verse_text = re.sub(
            r"\s+",
            " ",
            verse_text
        ).strip()

        # Skip empty entries, such as duplicate heading elements.
        if not verse_text:
            continue

        # Avoid duplicate verse IDs.
        # Keep the first nonempty occurrence.
        if verse_id not in extracted_verses:

            extracted_verses[verse_id] = {
                "verse": verse_number,
                "text": verse_text
            }

    return extracted_verses


# ============================================================
# FIND DIAGNOSTIC HTML FILE
# ============================================================

def find_html_file(book_code, chapter_number):

    """
    Locate the saved Lokele diagnostic HTML file.
    """

    filename = (
        f"diagnostic_{book_code}_"
        f"{chapter_number}_{LOKELE_VERSION}.html"
    )

    filepath = BASE_DIR / filename

    if filepath.exists():
        return filepath

    return None


# ============================================================
# TEST A SINGLE CHAPTER
# ============================================================

def test_chapter(book_code, chapter_number):

    print("\n" + "=" * 70)

    print(
        f"TESTING {book_code} CHAPTER {chapter_number}"
    )

    print("=" * 70)

    html_file = find_html_file(
        book_code,
        chapter_number
    )

    if html_file is None:

        print("ERROR: Diagnostic HTML file not found.")

        print(
            f"Expected file: diagnostic_{book_code}_"
            f"{chapter_number}_{LOKELE_VERSION}.html"
        )

        return None

    print(f"HTML file: {html_file.name}")

    # Read the saved HTML.
    try:

        html_content = html_file.read_text(
            encoding="utf-8"
        )

    except UnicodeDecodeError:

        html_content = html_file.read_text(
            encoding="utf-8-sig",
            errors="replace"
        )

    print(
        f"HTML file size: {len(html_content):,} characters"
    )

    # Extract verses.
    verses = extract_verses_from_html(
        html_content,
        book_code,
        chapter_number
    )

    # Display results.
    print(
        f"\nSUCCESS: Extracted {len(verses)} verses."
    )

    if verses:

        print("\nFIRST 5 EXTRACTED VERSES:")

        for verse_id, verse_data in list(
            verses.items()
        )[:5]:

            print(
                f"\n{verse_id}: "
                f"{verse_data['text']}"
            )

        print("\nLAST EXTRACTED VERSE:")

        last_verse_id = list(verses.keys())[-1]

        print(
            f"{last_verse_id}: "
            f"{verses[last_verse_id]['text']}"
        )

    else:

        print(
            "WARNING: No verses were extracted."
        )

    return verses


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)

    print("LOKELE BIBLE FALLBACK EXTRACTOR TEST")

    print("=" * 70)

    print(f"Project directory: {BASE_DIR}")

    print(f"Bible version: {LOKELE_VERSION}")

    results = {}

    total_verses = 0

    for book_code, chapter_number in CHAPTERS_TO_TEST:

        key = f"{book_code}.{chapter_number}"

        verses = test_chapter(
            book_code,
            chapter_number
        )

        results[key] = verses

        if verses:
            total_verses += len(verses)

    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)

    print("FINAL SUMMARY")

    print("=" * 70)

    for chapter, verses in results.items():

        if verses is None:

            print(
                f"{chapter}: FILE NOT FOUND"
            )

        else:

            print(
                f"{chapter}: "
                f"{len(verses)} verses extracted"
            )

    print("-" * 70)

    print(
        f"TOTAL VERSES EXTRACTED: {total_verses}"
    )

    print("=" * 70)

    # Save the test results to a JSON file.
    import json

    output_file = (
        BASE_DIR / "fallback_test_results.json"
    )

    json_results = {}

    for chapter, verses in results.items():

        if verses is None:
            json_results[chapter] = None

        else:
            json_results[chapter] = [
                {
                    "id": verse_id,
                    "verse": data["verse"],
                    "lokele": data["text"]
                }
                for verse_id, data in verses.items()
            ]

    with output_file.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            json_results,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"\nTest results saved to:\n{output_file}"
    )


if __name__ == "__main__":
    main()