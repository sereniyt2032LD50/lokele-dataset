
import json
import glob
from pathlib import Path
from collections import Counter, defaultdict

# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path.cwd()

EXPECTED_BOOKS = [
    "MAT", "MRK", "LUK", "JHN", "ACT",
    "ROM", "1CO", "2CO", "GAL", "EPH",
    "PHP", "COL", "1TH", "2TH", "1TI",
    "2TI", "TIT", "PHM", "HEB", "JAS",
    "1PE", "2PE", "1JN", "2JN", "3JN",
    "JUD", "REV"
]

BOOK_NAMES = {
    "MAT": "Matthew", "MRK": "Mark", "LUK": "Luke",
    "JHN": "John", "ACT": "Acts", "ROM": "Romans",
    "1CO": "1 Corinthians", "2CO": "2 Corinthians",
    "GAL": "Galatians", "EPH": "Ephesians",
    "PHP": "Philippians", "COL": "Colossians",
    "1TH": "1 Thessalonians", "2TH": "2 Thessalonians",
    "1TI": "1 Timothy", "2TI": "2 Timothy",
    "TIT": "Titus", "PHM": "Philemon",
    "HEB": "Hebrews", "JAS": "James",
    "1PE": "1 Peter", "2PE": "2 Peter",
    "1JN": "1 John", "2JN": "2 John",
    "3JN": "3 John", "JUD": "Jude",
    "REV": "Revelation"
}

# Confirmed omissions from the published Lokele source.
# These are NOT scraper errors.
CONFIRMED_SOURCE_OMISSIONS = {
    "LUK": [
        "LUK.5.39", "LUK.7.50", "LUK.17.36",
        "LUK.18.43", "LUK.20.4", "LUK.23.51",
        "LUK.24.48"
    ],
    "ACT": [
        "ACT.7.29", "ACT.7.51", "ACT.15.34"
    ]
}

# ============================================================
# HELPERS
# ============================================================

def book_code_from_id(verse_id):
    parts = verse_id.split(".")
    if len(parts) >= 3:
        return parts[0]
    return None


def load_jsonl(filepath):
    records = []
    errors = []

    with filepath.open("r", encoding="utf-8-sig") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)

                if not isinstance(record, dict):
                    errors.append({
                        "file": filepath.name,
                        "line": line_number,
                        "error": "JSON record is not an object"
                    })
                    continue

                records.append(record)

            except json.JSONDecodeError as e:
                errors.append({
                    "file": filepath.name,
                    "line": line_number,
                    "error": str(e)
                })

    return records, errors


# ============================================================
# FIND ALL JSONL FILES
# ============================================================

files = sorted(BASE_DIR.glob("*_lokele_english.jsonl"))

print("=" * 70)
print("NEW TESTAMENT DATASET VALIDATION")
print("=" * 70)
print("Folder:", BASE_DIR)
print("JSONL files found:", len(files))
print()

if not files:
    raise SystemExit(
        "ERROR: No *_lokele_english.jsonl files found. "
        "Check that you are in the correct project folder."
    )

# Load all records from all files.
all_records = []
file_errors = []
files_by_book = {}

for filepath in files:
    records, errors = load_jsonl(filepath)

    all_records.extend(records)
    file_errors.extend(errors)

    for record in records:
        code = book_code_from_id(str(record.get("id", "")))
        if code:
            files_by_book.setdefault(code, set()).add(filepath.name)

# ============================================================
# CHECK 1: BOOK COVERAGE
# ============================================================

present_books = set(files_by_book.keys())

missing_books = [
    code for code in EXPECTED_BOOKS
    if code not in present_books
]

unexpected_books = sorted(
    present_books - set(EXPECTED_BOOKS)
)

print("CHECK 1 — BOOK COVERAGE")
print("-" * 70)
print("Expected books:", len(EXPECTED_BOOKS))
print("Books represented in records:", len(present_books))
print("Missing books:", missing_books or "None")
print("Unexpected book codes:", unexpected_books or "None")
print()

# ============================================================
# CHECK 2: DUPLICATE IDS
# ============================================================

id_counts = Counter()
records_by_id = defaultdict(list)

for record in all_records:
    verse_id = str(record.get("id", "")).strip()

    if verse_id:
        id_counts[verse_id] += 1
        records_by_id[verse_id].append(record)

duplicate_ids = {
    verse_id: count
    for verse_id, count in id_counts.items()
    if count > 1
}

print("CHECK 2 — DUPLICATE VERSE IDS")
print("-" * 70)
print("Unique verse IDs:", len(id_counts))
print("Duplicate IDs:", len(duplicate_ids))

for verse_id, count in sorted(duplicate_ids.items()):
    print(f"  {verse_id}: {count} occurrences")

if not duplicate_ids:
    print("No duplicate verse IDs found.")

print()

# ============================================================
# CHECK 3: EMPTY FIELDS AND INVALID RECORDS
# ============================================================

empty_lokele = []
empty_english = []
missing_ids = []
missing_fields = []

required_fields = [
    "id", "book", "chapter", "verse", "lokele", "english"
]

for index, record in enumerate(all_records, start=1):
    verse_id = str(record.get("id", "")).strip()

    if not verse_id:
        missing_ids.append({
            "record_number": index,
            "record": record
        })

    for field in required_fields:
        if field not in record:
            missing_fields.append({
                "id": verse_id,
                "field": field
            })

    if not str(record.get("lokele", "")).strip():
        empty_lokele.append(verse_id or f"record_{index}")

    if not str(record.get("english", "")).strip():
        empty_english.append(verse_id or f"record_{index}")

print("CHECK 3 — EMPTY OR INVALID RECORDS")
print("-" * 70)
print("Empty Lokele text:", len(empty_lokele))
print("Empty English text:", len(empty_english))
print("Missing IDs:", len(missing_ids))
print("Missing required fields:", len(missing_fields))
print("Malformed JSON lines:", len(file_errors))
print()

# ============================================================
# CHECK 4: ALIGNMENT AND CHAPTER COUNTS
# ============================================================

book_stats = {}
chapter_stats = defaultdict(Counter)
alignment_issues = []

for code in EXPECTED_BOOKS:
    book_records = [
        r for r in all_records
        if book_code_from_id(str(r.get("id", ""))) == code
    ]

    ids = [
        str(r.get("id", "")).strip()
        for r in book_records
        if str(r.get("id", "")).strip()
    ]

    lokele_ids = {
        str(r.get("id", "")).strip()
        for r in book_records
        if str(r.get("lokele", "")).strip()
    }

    english_ids = {
        str(r.get("id", "")).strip()
        for r in book_records
        if str(r.get("english", "")).strip()
    }

    missing_lokele_in_dataset = sorted(
        english_ids - lokele_ids
    )

    missing_english_in_dataset = sorted(
        lokele_ids - english_ids
    )

    # Read the latest missing report if available.
    missing_report = {}
    possible_reports = [
        BASE_DIR / f"{code.lower()}_missing.json",
        BASE_DIR / f"{BOOK_NAMES[code].lower().replace(' ', '_')}_missing.json"
    ]

    for report_path in possible_reports:
        if report_path.exists():
            try:
                missing_report = json.loads(
                    report_path.read_text(encoding="utf-8-sig")
                )
                break
            except Exception:
                pass

    source_omissions = CONFIRMED_SOURCE_OMISSIONS.get(
        code, []
    )

    book_stats[code] = {
        "book": BOOK_NAMES[code],
        "records": len(book_records),
        "unique_ids": len(set(ids)),
        "duplicate_ids": len(ids) - len(set(ids)),
        "missing_lokele_in_dataset": missing_lokele_in_dataset,
        "missing_english_in_dataset": missing_english_in_dataset,
        "confirmed_source_omissions": source_omissions,
        "source_missing_report": missing_report
    }

    if missing_lokele_in_dataset or missing_english_in_dataset:
        alignment_issues.append({
            "book": code,
            "missing_lokele": missing_lokele_in_dataset,
            "missing_english": missing_english_in_dataset
        })

    for record in book_records:
        try:
            chapter = int(record["chapter"])
        except (ValueError, TypeError, KeyError):
            continue

        chapter_stats[code][chapter] += 1

print("CHECK 4 — LOKELE-ENGLISH ALIGNMENT")
print("-" * 70)

for code in EXPECTED_BOOKS:
    stats = book_stats[code]

    print(
        f"{code:5} | "
        f"{stats['book']:18} | "
        f"Records: {stats['records']:4} | "
        f"Unique IDs: {stats['unique_ids']:4} | "
        f"Duplicates: {stats['duplicate_ids']}"
    )

    if stats["missing_lokele_in_dataset"]:
        print(
            "  Missing Lokele:",
            stats["missing_lokele_in_dataset"]
        )

    if stats["missing_english_in_dataset"]:
        print(
            "  Missing English:",
            stats["missing_english_in_dataset"]
        )

print()

# ============================================================
# CHECK 5: CHAPTER COVERAGE
# ============================================================

print("CHECK 5 — CHAPTER COVERAGE")
print("-" * 70)

for code in EXPECTED_BOOKS:
    chapters = sorted(chapter_stats[code].keys())

    if not chapters:
        print(f"{code}: NO CHAPTERS FOUND")
        continue

    expected_chapters = list(range(1, max(chapters) + 1))
    missing_chapters = sorted(
        set(expected_chapters) - set(chapters)
    )

    print(
        f"{code:5} | "
        f"Chapters found: {len(chapters):2} | "
        f"Range: {min(chapters)}-{max(chapters)} | "
        f"Missing chapters: {missing_chapters or 'None'}"
    )

print()

# ============================================================
# CHECK 6: FILE-LEVEL MISSING REPORTS
# ============================================================

print("CHECK 6 — EXISTING MISSING REPORTS")
print("-" * 70)

missing_reports = sorted(BASE_DIR.glob("*_missing.json"))

for report_path in missing_reports:
    try:
        report = json.loads(
            report_path.read_text(encoding="utf-8-sig")
        )

        missing_l = report.get("missing_lokele", [])
        missing_e = report.get("missing_english", [])

        print(
            f"{report_path.name}: "
            f"Lokele={len(missing_l)}, "
            f"English={len(missing_e)}"
        )

    except Exception as e:
        print(f"{report_path.name}: ERROR reading report: {e}")

print()

# ============================================================
# SAVE VALIDATION REPORT
# ============================================================

report = {
    "dataset_folder": str(BASE_DIR),
    "jsonl_files_found": len(files),
    "total_records": len(all_records),
    "unique_verse_ids": len(id_counts),
    "expected_books": len(EXPECTED_BOOKS),
    "books_found": len(present_books),
    "missing_books": missing_books,
    "unexpected_books": unexpected_books,
    "duplicate_ids": duplicate_ids,
    "empty_lokele": empty_lokele,
    "empty_english": empty_english,
    "missing_ids": missing_ids,
    "missing_required_fields": missing_fields,
    "malformed_json_lines": file_errors,
    "alignment_issues": alignment_issues,
    "book_stats": book_stats,
    "chapter_stats": {
        code: dict(chapter_stats[code])
        for code in EXPECTED_BOOKS
    },
    "confirmed_source_omissions": CONFIRMED_SOURCE_OMISSIONS
}

output_path = BASE_DIR / "nt_validation_report.json"

output_path.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("=" * 70)
print("VALIDATION FINISHED")
print("=" * 70)
print("Total records:", len(all_records))
print("Unique IDs:", len(id_counts))
print("Duplicate IDs:", len(duplicate_ids))
print("Empty Lokele:", len(empty_lokele))
print("Empty English:", len(empty_english))
print("Malformed JSON:", len(file_errors))
print("Alignment issues:", len(alignment_issues))
print("Report saved to:", output_path)
print()
print("IMPORTANT: This script validates existing records.")
print("It does not assume every Bible verse is present in the source.")