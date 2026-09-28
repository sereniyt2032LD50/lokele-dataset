import json
from pathlib import Path
from collections import Counter, defaultdict

# ============================================================
# LOKELE–ENGLISH BIBLE CORPUS VALIDATOR
# ============================================================
# This script DOES NOT modify your dataset.
# It only reads the generated JSONL files and reports problems.
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

# Bible.com book codes and expected chapter counts
BOOKS = {
    "MAT": ("Matthew", 28),
    "MRK": ("Mark", 16),
    "LUK": ("Luke", 24),
    "JHN": ("John", 21),
    "ACT": ("Acts", 28),
    "ROM": ("Romans", 16),
    "1CO": ("1 Corinthians", 16),
    "2CO": ("2 Corinthians", 13),
    "GAL": ("Galatians", 6),
    "EPH": ("Ephesians", 6),
    "PHP": ("Philippians", 4),
    "COL": ("Colossians", 4),
    "1TH": ("1 Thessalonians", 5),
    "2TH": ("2 Thessalonians", 3),
    "1TI": ("1 Timothy", 6),
    "2TI": ("2 Timothy", 4),
    "TIT": ("Titus", 3),
    "PHM": ("Philemon", 1),
    "HEB": ("Hebrews", 13),
    "JAS": ("James", 5),
    "1PE": ("1 Peter", 5),
    "2PE": ("2 Peter", 3),
    "1JN": ("1 John", 5),
    "2JN": ("2 John", 1),
    "3JN": ("3 John", 1),
    "JUD": ("Jude", 1),
    "REV": ("Revelation", 22),
}


# ------------------------------------------------------------
# Convert book name to the filename used by the scraper
# ------------------------------------------------------------

def filename_for_book(book_name):
    return book_name.lower().replace(" ", "_")


# ------------------------------------------------------------
# Basic text-quality checks
# ------------------------------------------------------------

def looks_suspicious(text):
    if not isinstance(text, str):
        return True

    text = text.strip()

    if not text:
        return True

    # Pure numbers
    if text.isdigit():
        return True

    # USFM-style IDs accidentally extracted as text
    if "." in text:
        parts = text.split(".")
        if len(parts) >= 3 and any(part.isdigit() for part in parts):
            if all(len(part) < 10 for part in parts):
                return True

    return False


# ------------------------------------------------------------
# Validate one book
# ------------------------------------------------------------

def validate_book(code, book_name, expected_chapters):

    filename = filename_for_book(book_name)
    jsonl_path = BASE_DIR / f"{filename}_lokele_english.jsonl"
    missing_path = BASE_DIR / f"{filename}_missing.json"

    result = {
        "code": code,
        "book": book_name,
        "file_exists": jsonl_path.exists(),
        "records": 0,
        "duplicates": [],
        "invalid_ids": [],
        "wrong_book_ids": [],
        "chapters_found": set(),
        "empty_lokele": [],
        "empty_english": [],
        "suspicious_lokele": [],
        "suspicious_english": [],
        "missing_report_exists": missing_path.exists(),
    }

    if not jsonl_path.exists():
        return result

    seen_ids = set()

    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:

            for line_number, line in enumerate(f, start=1):

                line = line.strip()

                if not line:
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    result["invalid_ids"].append(
                        f"Line {line_number}: invalid JSON"
                    )
                    continue

                result["records"] += 1

                verse_id = record.get("id")

                # --------------------------------------------
                # ID validation
                # --------------------------------------------

                if not verse_id:
                    result["invalid_ids"].append(
                        f"Line {line_number}: missing ID"
                    )
                    continue

                if verse_id in seen_ids:
                    result["duplicates"].append(verse_id)

                seen_ids.add(verse_id)

                parts = verse_id.split(".")

                if len(parts) != 3:
                    result["invalid_ids"].append(verse_id)
                    continue

                id_book, chapter, verse = parts

                if id_book != code:
                    result["wrong_book_ids"].append(verse_id)

                try:
                    chapter_num = int(chapter)
                    int(verse)
                except ValueError:
                    result["invalid_ids"].append(verse_id)
                    continue

                result["chapters_found"].add(chapter_num)

                # --------------------------------------------
                # Text validation
                # --------------------------------------------

                lokele = record.get("lokele")
                english = record.get("english")

                if not isinstance(lokele, str) or not lokele.strip():
                    result["empty_lokele"].append(verse_id)

                if not isinstance(english, str) or not english.strip():
                    result["empty_english"].append(verse_id)

                if looks_suspicious(lokele):
                    result["suspicious_lokele"].append(
                        (verse_id, lokele)
                    )

                if looks_suspicious(english):
                    result["suspicious_english"].append(
                        (verse_id, english)
                    )

    except Exception as e:
        result["invalid_ids"].append(
            f"Could not read file: {e}"
        )

    return result


# ------------------------------------------------------------
# Main validation
# ------------------------------------------------------------

def main():

    print("=" * 75)
    print("LOKELE–ENGLISH BIBLE CORPUS VALIDATION")
    print("=" * 75)

    print(f"\nDataset directory:")
    print(BASE_DIR)

    print("\nThis validation is READ-ONLY.")
    print("No dataset files will be changed.\n")

    all_results = []

    for code, (book_name, expected_chapters) in BOOKS.items():

        result = validate_book(
            code,
            book_name,
            expected_chapters
        )

        all_results.append(result)

        if not result["file_exists"]:
            print(f"❌ {book_name:<20} FILE MISSING")
            continue

        problems = []

        if result["duplicates"]:
            problems.append(
                f"{len(result['duplicates'])} duplicate IDs"
            )

        if result["invalid_ids"]:
            problems.append(
                f"{len(result['invalid_ids'])} invalid IDs/JSON"
            )

        if result["wrong_book_ids"]:
            problems.append(
                f"{len(result['wrong_book_ids'])} wrong-book IDs"
            )

        if result["empty_lokele"]:
            problems.append(
                f"{len(result['empty_lokele'])} empty Lokele"
            )

        if result["empty_english"]:
            problems.append(
                f"{len(result['empty_english'])} empty English"
            )

        if result["suspicious_lokele"]:
            problems.append(
                f"{len(result['suspicious_lokele'])} suspicious Lokele"
            )

        if result["suspicious_english"]:
            problems.append(
                f"{len(result['suspicious_english'])} suspicious English"
            )

        missing_chapters = set(
            range(1, expected_chapters + 1)
        ) - result["chapters_found"]

        if missing_chapters:
            problems.append(
                f"missing chapters: {sorted(missing_chapters)}"
            )

        if problems:
            print(
                f"⚠️ {book_name:<20} "
                f"{result['records']:>6} records | "
                + " | ".join(problems)
            )
        else:
            print(
                f"✅ {book_name:<20} "
                f"{result['records']:>6} records | "
                f"{expected_chapters}/{expected_chapters} chapters"
            )

    # ========================================================
    # Overall statistics
    # ========================================================

    total_records = sum(
        r["records"] for r in all_results
    )

    total_duplicates = sum(
        len(r["duplicates"]) for r in all_results
    )

    total_empty_lokele = sum(
        len(r["empty_lokele"]) for r in all_results
    )

    total_empty_english = sum(
        len(r["empty_english"]) for r in all_results
    )

    total_suspicious_lokele = sum(
        len(r["suspicious_lokele"]) for r in all_results
    )

    total_suspicious_english = sum(
        len(r["suspicious_english"]) for r in all_results
    )

    total_invalid = sum(
        len(r["invalid_ids"]) for r in all_results
    )

    total_wrong_book = sum(
        len(r["wrong_book_ids"]) for r in all_results
    )

    books_found = sum(
        r["file_exists"] for r in all_results
    )

    print("\n")
    print("=" * 75)
    print("OVERALL RESULTS")
    print("=" * 75)

    print(f"\nBooks found:              {books_found}/27")
    print(f"Total aligned records:   {total_records:,}")
    print(f"Duplicate IDs:            {total_duplicates}")
    print(f"Invalid IDs/JSON:         {total_invalid}")
    print(f"Wrong-book IDs:           {total_wrong_book}")
    print(f"Empty Lokele texts:       {total_empty_lokele}")
    print(f"Empty English texts:      {total_empty_english}")
    print(f"Suspicious Lokele texts:  {total_suspicious_lokele}")
    print(f"Suspicious English texts: {total_suspicious_english}")

    # ========================================================
    # Detailed suspicious text
    # ========================================================

    print("\n")
    print("=" * 75)
    print("SUSPICIOUS TEXT SAMPLES")
    print("=" * 75)

    found_suspicious = False

    for result in all_results:

        if result["suspicious_lokele"]:

            found_suspicious = True

            print(
                f"\n{result['book']} — Lokele:"
            )

            for verse_id, text in result["suspicious_lokele"][:10]:
                print(f"  {verse_id}: {repr(text)}")

        if result["suspicious_english"]:

            found_suspicious = True

            print(
                f"\n{result['book']} — English:"
            )

            for verse_id, text in result["suspicious_english"][:10]:
                print(f"  {verse_id}: {repr(text)}")

    if not found_suspicious:
        print("\nNo suspicious text detected by the basic checks.")

    # ========================================================
    # Missing reports
    # ========================================================

    print("\n")
    print("=" * 75)
    print("MISSING-VERSE REPORTS")
    print("=" * 75)

    for result in all_results:

        if result["file_exists"]:

            status = (
                "found"
                if result["missing_report_exists"]
                else "not found"
            )

            print(
                f"{result['book']:<20} {status}"
            )

    # ========================================================
    # Final message
    # ========================================================

    print("\n")
    print("=" * 75)

    if (
        books_found == 27
        and total_duplicates == 0
        and total_invalid == 0
        and total_wrong_book == 0
    ):
        print("✅ BASIC STRUCTURAL VALIDATION PASSED")
    else:
        print("⚠️ ISSUES REQUIRE REVIEW")

    print("=" * 75)

    print(
        "\nValidation complete. "
        "No files were modified."
    )


if __name__ == "__main__":
    main()