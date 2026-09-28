from pathlib import Path
import re

# ============================================================
# INSPECT BIBLE.COM HTML FOR MISSING CHAPTERS
# ============================================================
# This script ONLY reads the diagnostic HTML files.
# It does NOT modify them or your dataset.
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

FILES = [
    "diagnostic_LUK_15_NTKE58.html",
    "diagnostic_ACT_6_NTKE58.html",
    "diagnostic_2CO_6_NTKE58.html",
    "diagnostic_2CO_7_NTKE58.html",
]


def inspect_file(filename):

    path = BASE_DIR / filename

    print("\n")
    print("=" * 90)
    print(f"FILE: {filename}")
    print("=" * 90)

    if not path.exists():
        print(f"❌ File not found: {path}")
        return

    html = path.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    print(f"HTML size: {len(html):,} characters")

    # --------------------------------------------------------
    # 1. Look for USFM IDs
    # --------------------------------------------------------

    print("\n--- USFM ID REFERENCES ---")

    # Examples:
    # LUK.15.1
    # ACT.6.1
    # 2CO.6.1

    usfm_matches = re.findall(
        r'(?:LUK|ACT|2CO)\.\d+\.\d+',
        html
    )

    unique_ids = list(dict.fromkeys(usfm_matches))

    print(
        f"USFM-style IDs found: {len(unique_ids)}"
    )

    for item in unique_ids[:30]:
        print(" ", item)

    if len(unique_ids) > 30:
        print(
            f" ... and {len(unique_ids) - 30} more"
        )

    # --------------------------------------------------------
    # 2. Look specifically around the first verse ID
    # --------------------------------------------------------

    print("\n--- HTML AROUND FIRST VERSE ID ---")

    if unique_ids:

        first_id = unique_ids[0]

        position = html.find(first_id)

        if position != -1:

            start = max(0, position - 1500)
            end = min(
                len(html),
                position + 4000
            )

            snippet = html[start:end]

            print(
                f"\nContext around {first_id}:\n"
            )

            print(snippet)

    else:
        print(
            "No verse-level USFM IDs found."
        )

    # --------------------------------------------------------
    # 3. Search for likely verse-related HTML classes
    # --------------------------------------------------------

    print("\n--- HTML CLASS NAMES ---")

    classes = re.findall(
        r'class=["\']([^"\']+)["\']',
        html
    )

    unique_classes = []

    for class_value in classes:

        if class_value not in unique_classes:
            unique_classes.append(class_value)

    print(
        f"Unique class attributes found: "
        f"{len(unique_classes)}"
    )

    # Show classes that look relevant
    keywords = [
        "verse",
        "content",
        "text",
        "chapter",
        "passage",
        "scripture",
        "bible",
        "version",
        "paragraph",
        "label",
        "heading"
    ]

    relevant_classes = []

    for class_value in unique_classes:

        lower = class_value.lower()

        if any(
            keyword in lower
            for keyword in keywords
        ):
            relevant_classes.append(class_value)

    for class_value in relevant_classes[:100]:
        print(" ", class_value)

    # --------------------------------------------------------
    # 4. Search for JSON data containing verse IDs
    # --------------------------------------------------------

    print("\n--- POSSIBLE JSON DATA ---")

    json_keywords = [
        '"content"',
        '"text"',
        '"verse"',
        '"verseId"',
        '"verse_id"',
        '"usfm"',
        '"reference"',
        '"passage"',
        '"chapterId"',
        '"bookId"'
    ]

    for keyword in json_keywords:

        count = html.count(keyword)

        if count:
            print(
                f"{keyword:<20} {count:,} occurrences"
            )

    # --------------------------------------------------------
    # 5. Search for the actual beginning of the Lokele text
    # --------------------------------------------------------

    print("\n--- POSSIBLE TEXT CONTEXT ---")

    # Common words from the chapters can help us locate
    # actual verse text inside the HTML.

    search_terms = [
        "Ongoma",
        "Mungu",
        "Masiya",
        "iso",
        "boto",
        "Sango",
        "Bolimo",
        "Yesu",
    ]

    found_terms = []

    for term in search_terms:

        position = html.find(term)

        if position != -1:

            found_terms.append(term)

            start = max(0, position - 500)
            end = min(
                len(html),
                position + 2000
            )

            print(
                f"\n--- Context around '{term}' ---"
            )

            print(
                html[start:end]
            )

            # Only show first useful context
            break

    if not found_terms:

        print(
            "No known Lokele search terms found "
            "directly in the HTML."
        )

    # --------------------------------------------------------
    # 6. Look for Next.js / React data
    # --------------------------------------------------------

    print("\n--- REACT / NEXT.JS DATA ---")

    framework_markers = [
        "__NEXT_DATA__",
        "__next",
        "self.__next_f",
        "webpack",
        "react"
    ]

    for marker in framework_markers:

        count = html.lower().count(
            marker.lower()
        )

        if count:
            print(
                f"{marker:<20} {count:,} occurrences"
            )

    # --------------------------------------------------------
    # 7. Save a compact inspection report
    # --------------------------------------------------------

    report_name = (
        filename.replace(".html", "_inspection.txt")
    )

    report_path = BASE_DIR / report_name

    report_path.write_text(
        html,
        encoding="utf-8"
    )

    print(
        f"\nOriginal HTML remains unchanged."
    )


def main():

    print("=" * 90)
    print("BIBLE.COM MISSING-CHAPTER HTML INSPECTOR")
    print("=" * 90)

    print(
        "\nReading diagnostic HTML files only."
    )

    for filename in FILES:
        inspect_file(filename)

    print("\n")
    print("=" * 90)
    print("INSPECTION COMPLETE")
    print("=" * 90)


if __name__ == "__main__":
    main()