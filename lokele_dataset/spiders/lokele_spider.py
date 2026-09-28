import scrapy
import html
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup


class LokeleSpider(scrapy.Spider):

    name = "lokele"

    allowed_domains = ["bible.com"]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,

        "DOWNLOAD_HANDLERS": {
            "http":
                "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https":
                "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },

        "TWISTED_REACTOR":
            "twisted.internet.asyncioreactor.AsyncioSelectorReactor",

        "DOWNLOAD_TIMEOUT": 180,

        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 120000,

        "CONCURRENT_REQUESTS": 2,

        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,

        "DOWNLOAD_DELAY": 1,

        "FEED_EXPORT_ENCODING": "utf-8",

        "LOG_LEVEL": "INFO",
    }

    # ============================================================
    # BIBLE BOOKS
    # ============================================================

    BOOKS = {

        "GEN": ("Genesis", 50),
        "EXO": ("Exodus", 40),
        "LEV": ("Leviticus", 27),
        "NUM": ("Numbers", 36),
        "DEU": ("Deuteronomy", 34),
        "JOS": ("Joshua", 24),
        "JDG": ("Judges", 21),
        "RUT": ("Ruth", 4),
        "1SA": ("1 Samuel", 31),
        "2SA": ("2 Samuel", 24),
        "1KI": ("1 Kings", 22),
        "2KI": ("2 Kings", 25),
        "1CH": ("1 Chronicles", 29),
        "2CH": ("2 Chronicles", 36),
        "EZR": ("Ezra", 10),
        "NEH": ("Nehemiah", 13),
        "EST": ("Esther", 10),
        "JOB": ("Job", 42),
        "PSA": ("Psalms", 150),
        "PRO": ("Proverbs", 31),
        "ECC": ("Ecclesiastes", 12),
        "SNG": ("Song of Solomon", 8),
        "ISA": ("Isaiah", 66),
        "JER": ("Jeremiah", 52),
        "LAM": ("Lamentations", 5),
        "EZK": ("Ezekiel", 48),
        "DAN": ("Daniel", 12),
        "HOS": ("Hosea", 14),
        "JOL": ("Joel", 3),
        "AMO": ("Amos", 9),
        "OBA": ("Obadiah", 1),
        "JON": ("Jonah", 4),
        "MIC": ("Micah", 7),
        "NAM": ("Nahum", 3),
        "HAB": ("Habakkuk", 3),
        "ZEP": ("Zephaniah", 3),
        "HAG": ("Haggai", 2),
        "ZEC": ("Zechariah", 14),
        "MAL": ("Malachi", 4),

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

    # ============================================================
    # BIBLE.COM VERSIONS
    # ============================================================

    LOKELE_VERSION_ID = 1496
    LOKELE_VERSION = "NTKE58"

    ENGLISH_VERSION_ID = 206
    ENGLISH_VERSION = "WEBUS"

    # ============================================================
    # CHAPTER RANGE
    # ============================================================

    START_CHAPTER = 1

    # ============================================================
    # INITIALIZATION
    # ============================================================

    def __init__(self, book=None, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if book is None:
            book = "MAT"

        book = book.upper()

        if book == "ALL":

            self.selected_books = list(
                self.BOOKS.keys()
            )

        else:

            if book not in self.BOOKS:

                raise ValueError(
                    f"Unknown book code: {book}. "
                    f"Available codes: "
                    f"{', '.join(self.BOOKS.keys())}"
                )

            self.selected_books = [book]

        # --------------------------------------------------------
        # Storage
        # --------------------------------------------------------

        self.data = {}

        for book_code in self.selected_books:

            self.data[book_code] = {
                "lokele": {},
                "english": {},
            }

        # --------------------------------------------------------
        # Statistics
        # --------------------------------------------------------

        self.book_stats = {}

        for book_code in self.selected_books:

            book_name, chapter_count = (
                self.BOOKS[book_code]
            )

            self.book_stats[book_code] = {

                "pages_processed": 0,

                "pages_failed": 0,

                "pages_expected": chapter_count * 2,
            }

        self.pages_processed = 0

        self.pages_failed = 0

        self.total_pages = sum(
            self.book_stats[book_code]["pages_expected"]
            for book_code in self.selected_books
        )

    # ============================================================
    # START
    # ============================================================

    async def start(self):

        self.logger.info("=" * 70)

        self.logger.info(
            "LOKELE-ENGLISH BIBLE SCRAPER"
        )

        self.logger.info("=" * 70)

        self.logger.info(
            "Selected books: %s",
            ", ".join(self.selected_books),
        )

        self.logger.info(
            "Lokele: %s (%d)",
            self.LOKELE_VERSION,
            self.LOKELE_VERSION_ID,
        )

        self.logger.info(
            "English: %s (%d)",
            self.ENGLISH_VERSION,
            self.ENGLISH_VERSION_ID,
        )

        self.logger.info(
            "Expected pages: %d",
            self.total_pages,
        )

        self.logger.info("=" * 70)

        # ========================================================
        # PROCESS EACH BOOK
        # ========================================================

        for book_code in self.selected_books:

            book_name, chapter_count = (
                self.BOOKS[book_code]
            )

            end_chapter = chapter_count

            self.logger.info(
                "Preparing %s (%s): chapters %d-%d",
                book_name,
                book_code,
                self.START_CHAPTER,
                end_chapter,
            )

            # ====================================================
            # LOKELE
            # ====================================================

            for chapter in range(
                self.START_CHAPTER,
                end_chapter + 1,
            ):

                url = (
                    "https://www.bible.com/bible/"
                    f"{self.LOKELE_VERSION_ID}/"
                    f"{book_code}.{chapter}."
                    f"{self.LOKELE_VERSION}"
                )

                yield scrapy.Request(

                    url=url,

                    callback=self.parse,

                    errback=self.handle_error,

                    meta={

                        "playwright": True,

                        "playwright_page_goto_kwargs": {
                            "wait_until": "domcontentloaded",
                            "timeout": 120000,
                        },

                        "language": "lokele",

                        "book_code": book_code,

                        "book_name": book_name,

                        "chapter": chapter,
                    },
                )

            # ====================================================
            # ENGLISH
            # ====================================================

            for chapter in range(
                self.START_CHAPTER,
                end_chapter + 1,
            ):

                url = (
                    "https://www.bible.com/bible/"
                    f"{self.ENGLISH_VERSION_ID}/"
                    f"{book_code}.{chapter}."
                    f"{self.ENGLISH_VERSION}"
                )

                yield scrapy.Request(

                    url=url,

                    callback=self.parse,

                    errback=self.handle_error,

                    meta={

                        "playwright": True,

                        "playwright_page_goto_kwargs": {
                            "wait_until": "domcontentloaded",
                            "timeout": 120000,
                        },

                        "language": "english",

                        "book_code": book_code,

                        "book_name": book_name,

                        "chapter": chapter,
                    },
                )

    # ============================================================
    # PARSE
    # ============================================================

    def parse(self, response):

        language = response.meta["language"]

        book_code = response.meta["book_code"]

        book_name = response.meta["book_name"]

        requested_chapter = response.meta["chapter"]

        self.pages_processed += 1

        self.book_stats[
            book_code
        ]["pages_processed"] += 1

        self.logger.info("-" * 70)

        self.logger.info(
            "PROCESSING %s",
            response.url,
        )

        self.logger.info(
            "Book: %s (%s)",
            book_name,
            book_code,
        )

        self.logger.info(
            "Language: %s",
            language,
        )

        self.logger.info(
            "Chapter: %d",
            requested_chapter,
        )

        self.logger.info(
            "Status: %d",
            response.status,
        )

        self.logger.info(
            "Response size: %d bytes",
            len(response.body),
        )

        body = response.text

        # --------------------------------------------------------
        # Debug information
        # --------------------------------------------------------

        self.logger.info(
            "Contains %s.: %s",
            book_code,
            f"{book_code}." in body,
        )

        self.logger.info(
            "Contains data-usfm: %s",
            "data-usfm" in body,
        )

        usfm_pattern = re.compile(
            rf"{re.escape(book_code)}\.\d+\.\d+",
            re.IGNORECASE,
        )

        usfm_matches = usfm_pattern.findall(body)

        unique_usfm = list(
            dict.fromkeys(usfm_matches)
        )

        self.logger.info(
            "USFM identifiers found: %d",
            len(unique_usfm),
        )

        if unique_usfm:

            self.logger.info(
                "First USFM identifiers: %s",
                unique_usfm[:10],
            )

        # --------------------------------------------------------
        # Extract verses
        # --------------------------------------------------------

        try:

            verses = self.extract_verses(
                body=body,
                requested_chapter=requested_chapter,
                book_code=book_code,
            )

        except Exception as exc:

            self.logger.error(
                "EXTRACTION ERROR"
            )

            self.logger.error(
                "Book: %s",
                book_code,
            )

            self.logger.error(
                "Language: %s",
                language,
            )

            self.logger.error(
                "Chapter: %d",
                requested_chapter,
            )

            self.logger.error(
                "Exception type: %s",
                type(exc).__name__,
            )

            self.logger.error(
                "Exception: %s",
                str(exc),
            )

            self.logger.exception(
                "FULL EXTRACTION TRACEBACK"
            )

            return

        self.logger.info(
            "Extracted %d verses",
            len(verses),
        )

        # --------------------------------------------------------
        # Store results
        # --------------------------------------------------------

        for usfm, record in verses.items():

            existing = (
                self.data[book_code][language]
                .get(usfm)
            )

            if (
                existing is None
                or len(record["text"])
                > len(existing["text"])
            ):

                self.data[book_code][language][
                    usfm
                ] = record

        self.logger.info(
            "Lokele total: %d",
            len(
                self.data[book_code]["lokele"]
            ),
        )

        self.logger.info(
            "English total: %d",
            len(
                self.data[book_code]["english"]
            ),
        )

    # ============================================================
    # EXTRACT VERSES
    # ============================================================

    def extract_verses(
        self,
        body,
        requested_chapter,
        book_code,
    ):

        verses = {}

        # --------------------------------------------------------
        # ORIGINAL EXTRACTION
        # --------------------------------------------------------

        patterns = [

            re.compile(
                rf'data-usfm\s*=\s*["\']'
                rf'({re.escape(book_code)}\.(\d+)\.(\d+))'
                rf'["\']',
                re.IGNORECASE,
            ),

            re.compile(
                rf'"usfm"\s*:\s*"'
                rf'({re.escape(book_code)}\.(\d+)\.(\d+))'
                rf'"',
                re.IGNORECASE,
            ),

            re.compile(
                rf'"id"\s*:\s*"'
                rf'({re.escape(book_code)}\.(\d+)\.(\d+))'
                rf'"',
                re.IGNORECASE,
            ),
        ]

        found = []

        # --------------------------------------------------------
        # Find verse IDs
        # --------------------------------------------------------

        for pattern in patterns:

            for match in pattern.finditer(body):

                usfm = match.group(1)

                chapter = int(match.group(2))

                verse = int(match.group(3))

                if chapter != requested_chapter:
                    continue

                found.append({
                    "usfm": usfm,
                    "chapter": chapter,
                    "verse": verse,
                    "start": match.start(),
                    "end": match.end(),
                })

        # --------------------------------------------------------
        # Remove duplicates
        # --------------------------------------------------------

        unique = {}

        for item in found:

            usfm = item["usfm"]

            if usfm not in unique:

                unique[usfm] = item

        found = list(unique.values())

        found.sort(
            key=lambda item: item["start"]
        )

        self.logger.info(
            "Candidate verse IDs for chapter %d: %d",
            requested_chapter,
            len(found),
        )

        # --------------------------------------------------------
        # Original extraction
        # --------------------------------------------------------

        for index, item in enumerate(found):

            usfm = item["usfm"]

            chapter = item["chapter"]

            verse_number = item["verse"]

            end_position = item["end"]

            if index + 1 < len(found):

                next_start = (
                    found[index + 1]["start"]
                )

            else:

                next_start = min(
                    len(body),
                    end_position + 5000,
                )

            fragment = body[
                end_position:next_start
            ]

            text = self.extract_verse_text(
                fragment
            )

            if not text:
                continue

            record = {
                "book": book_code,
                "chapter": chapter,
                "verse": verse_number,
                "text": text,
            }

            existing = verses.get(usfm)

            if (
                existing is None
                or len(text)
                > len(existing["text"])
            ):

                verses[usfm] = record

        # ========================================================
        # NEW BIBLE.COM HTML FALLBACK
        # ========================================================
        #
        # Bible.com currently uses structures such as:
        #
        # <span
        #   class="ChapterContent-module__...__verse"
        #   data-usfm="LUK.15.1">
        #
        #     <span ...__label>1</span>
        #
        #     <span ...__content>
        #         Verse text
        #     </span>
        #
        # The class name is dynamic, so we deliberately use:
        #
        #     [data-usfm]
        #
        # and:
        #
        #     [class*="content"]
        #
        # ========================================================

        fallback_verses = self.extract_verses_fallback(
            body=body,
            requested_chapter=requested_chapter,
            book_code=book_code,
        )

        # --------------------------------------------------------
        # Merge fallback results with original results
        # --------------------------------------------------------

        fallback_added = 0

        for usfm, record in fallback_verses.items():

            existing = verses.get(usfm)

            if existing is None:

                verses[usfm] = record

                fallback_added += 1

            elif len(record["text"]) > len(
                existing["text"]
            ):

                verses[usfm] = record

        if fallback_added > 0:

            self.logger.info(
                "Fallback extractor added %d verses",
                fallback_added,
            )

        self.logger.info(
            "Final verse count for chapter %d: %d",
            requested_chapter,
            len(verses),
        )

        return verses

    # ============================================================
    # NEW BIBLE.COM FALLBACK EXTRACTOR
    # ============================================================

    def extract_verses_fallback(
        self,
        body,
        requested_chapter,
        book_code,
    ):

        verses = {}

        soup = BeautifulSoup(
            body,
            "html.parser"
        )

        # --------------------------------------------------------
        # Find all elements containing data-usfm
        # --------------------------------------------------------

        verse_elements = soup.select(
            "[data-usfm]"
        )

        self.logger.info(
            "Fallback: found %d data-usfm elements",
            len(verse_elements),
        )

        expected_prefix = (
            f"{book_code}.{requested_chapter}."
        )

        for verse_element in verse_elements:

            usfm = (
                verse_element
                .get("data-usfm", "")
                .strip()
            )

            # ----------------------------------------------------
            # Check requested book/chapter
            # ----------------------------------------------------

            if not usfm.startswith(
                expected_prefix
            ):
                continue

            # ----------------------------------------------------
            # Validate USFM structure
            # ----------------------------------------------------

            match = re.fullmatch(
                rf"{re.escape(book_code)}\."
                rf"{requested_chapter}\."
                rf"(\d+)",
                usfm,
                re.IGNORECASE,
            )

            if not match:
                continue

            verse_number = int(
                match.group(1)
            )

            # ----------------------------------------------------
            # Find content element
            # ----------------------------------------------------
            #
            # We intentionally do NOT use:
            #
            # span.content
            #
            # because Bible.com now uses dynamic classes such as:
            #
            # ChapterContent-module__cat7xG__content
            #
            # ----------------------------------------------------

            content_element = (
                verse_element.select_one(
                    '[class*="content"]'
                )
            )

            if content_element is None:
                continue

            # ----------------------------------------------------
            # Extract visible text
            # ----------------------------------------------------

            text = content_element.get_text(
                separator=" ",
                strip=True,
            )

            text = self.clean_text(
                text
            )

            # ----------------------------------------------------
            # Ignore empty elements
            # ----------------------------------------------------

            if not text:
                continue

            if not self.is_valid_verse_text(
                text
            ):
                continue

            # ----------------------------------------------------
            # Deduplicate
            # ----------------------------------------------------

            existing = verses.get(usfm)

            if (
                existing is None
                or len(text)
                > len(existing["text"])
            ):

                verses[usfm] = {
                    "book": book_code,
                    "chapter": requested_chapter,
                    "verse": verse_number,
                    "text": text,
                }

        # --------------------------------------------------------
        # Sort internally
        # --------------------------------------------------------

        verses = dict(
            sorted(
                verses.items(),
                key=lambda item: item[1]["verse"]
            )
        )

        if verses:

            self.logger.info(
                "Fallback successfully extracted %d verses "
                "from %s chapter %d",
                len(verses),
                book_code,
                requested_chapter,
            )

        return verses

    # ============================================================
    # EXTRACT VERSE TEXT
    # ============================================================

    def extract_verse_text(
        self,
        fragment,
    ):

        if not fragment:
            return ""

        # ========================================================
        # HTML CONTENT SPANS
        # ========================================================

        content_pattern = re.compile(

            r'<span[^>]*'
            r'class=["\'][^"\']*content[^"\']*["\']'
            r'[^>]*>'
            r'(.*?)'
            r'</span>',

            re.IGNORECASE | re.DOTALL,
        )

        content_parts = []

        for match in content_pattern.finditer(
            fragment
        ):

            raw = match.group(1)

            cleaned = self.clean_text(
                raw
            )

            if self.is_valid_verse_text(
                cleaned
            ):

                content_parts.append(
                    cleaned
                )

        if content_parts:

            combined = " ".join(
                content_parts
            )

            combined = self.clean_text(
                combined
            )

            if self.is_valid_verse_text(
                combined
            ):

                return combined

        # ========================================================
        # JSON "content"
        # ========================================================

        json_content_pattern = re.compile(

            r'"content"\s*:\s*"(.*?)"',

            re.IGNORECASE | re.DOTALL,
        )

        json_content_parts = []

        for match in json_content_pattern.finditer(
            fragment
        ):

            raw = match.group(1)

            cleaned = self.clean_text(
                raw
            )

            if self.is_valid_verse_text(
                cleaned
            ):

                json_content_parts.append(
                    cleaned
                )

        if json_content_parts:

            combined = " ".join(
                json_content_parts
            )

            combined = self.clean_text(
                combined
            )

            if self.is_valid_verse_text(
                combined
            ):

                return combined

        # ========================================================
        # JSON "text"
        # ========================================================

        json_text_pattern = re.compile(

            r'"text"\s*:\s*"(.*?)"',

            re.IGNORECASE | re.DOTALL,
        )

        json_text_parts = []

        for match in json_text_pattern.finditer(
            fragment
        ):

            raw = match.group(1)

            cleaned = self.clean_text(
                raw
            )

            if self.is_valid_verse_text(
                cleaned
            ):

                json_text_parts.append(
                    cleaned
                )

        if json_text_parts:

            combined = " ".join(
                json_text_parts
            )

            combined = self.clean_text(
                combined
            )

            if self.is_valid_verse_text(
                combined
            ):

                return combined

        # ========================================================
        # LAST RESORT
        # ========================================================

        fallback = self.clean_text(
            fragment
        )

        if self.is_valid_verse_text(
            fallback
        ):

            return fallback

        return ""

    # ============================================================
    # VALIDATE VERSE TEXT
    # ============================================================

    def is_valid_verse_text(
        self,
        text,
    ):

        if not text:
            return False

        text = text.strip()

        if len(text) < 2:
            return False

        # Reject pure numbers

        if re.fullmatch(
            r"\d+",
            text,
        ):

            return False

        # Reject USFM IDs

        if re.fullmatch(
            r"[A-Z0-9]{2,5}\.\d+\.\d+",
            text,
            re.IGNORECASE,
        ):

            return False

        # Reject structural characters

        if text in {
            "{",
            "}",
            "[",
            "]",
            ",",
            ":",
        }:

            return False

        if (
            text.startswith("{")
            and text.endswith("}")
        ):

            return False

        if (
            text.startswith("[")
            and text.endswith("]")
        ):

            return False

        return True

    # ============================================================
    # CLEAN TEXT
    # ============================================================

    def clean_text(
        self,
        text,
    ):

        if not text:
            return ""

        # Decode HTML entities

        text = html.unescape(
            text
        )

        # Remove HTML tags

        text = re.sub(
            r"<[^>]+>",
            " ",
            text,
        )

        # Handle escaped characters

        text = text.replace(
            '\\"',
            '"'
        )

        text = text.replace(
            "\\\n",
            " "
        )

        text = text.replace(
            "\\\r",
            " "
        )

        text = text.replace(
            "\\\t",
            " "
        )

        # Remove zero-width characters

        for char in [
            "\u200b",
            "\u200c",
            "\u200d",
            "\ufeff",
        ]:

            text = text.replace(
                char,
                ""
            )

        # Remove paragraph marker

        text = text.replace(
            "¶",
            ""
        )

        # Normalize whitespace

        text = " ".join(
            text.split()
        )

        return text.strip()

    # ============================================================
    # REQUEST ERROR
    # ============================================================

    def handle_error(
        self,
        failure,
    ):

        request = failure.request

        self.pages_failed += 1

        book_code = request.meta.get(
            "book_code"
        )

        if book_code in self.book_stats:

            self.book_stats[
                book_code
            ]["pages_failed"] += 1

        self.logger.error(
            "=" * 70
        )

        self.logger.error(
            "REQUEST FAILED"
        )

        self.logger.error(
            "URL: %s",
            request.url,
        )

        self.logger.error(
            "Book: %s",
            book_code,
        )

        self.logger.error(
            "Language: %s",
            request.meta.get(
                "language"
            ),
        )

        self.logger.error(
            "Chapter: %s",
            request.meta.get(
                "chapter"
            ),
        )

        self.logger.error(
            "Exception type: %s",
            type(
                failure.value
            ).__name__,
        )

        self.logger.error(
            "Error: %s",
            failure.value,
        )

        self.logger.error(
            "=" * 70
        )

    # ============================================================
    # SPIDER CLOSED
    # ============================================================

    def closed(
        self,
        reason,
    ):

        self.logger.info(
            "=" * 70
        )

        self.logger.info(
            "SPIDER CLOSED"
        )

        self.logger.info(
            "Reason: %s",
            reason,
        )

        self.logger.info(
            "Pages processed: %d",
            self.pages_processed,
        )

        self.logger.info(
            "Pages failed: %d",
            self.pages_failed,
        )

        self.logger.info(
            "=" * 70
        )

        for book_code in self.selected_books:

            self.save_book(
                book_code,
                reason,
            )

    # ============================================================
    # SAVE BOOK
    # ============================================================

    def save_book(
        self,
        book_code,
        reason,
    ):

        book_name, chapter_count = (
            self.BOOKS[book_code]
        )

        lokele_data = (
            self.data[book_code]["lokele"]
        )

        english_data = (
            self.data[book_code]["english"]
        )

        lokele_count = len(
            lokele_data
        )

        english_count = len(
            english_data
        )

        # --------------------------------------------------------
        # Combine all verse IDs
        # --------------------------------------------------------

        all_usfm = (
            set(lokele_data.keys())
            |
            set(english_data.keys())
        )

        # --------------------------------------------------------
        # Sort by chapter and verse
        # --------------------------------------------------------

        sorted_usfm = sorted(
            all_usfm,
            key=lambda x: (
                int(x.split(".")[1]),
                int(x.split(".")[2]),
            ),
        )

        aligned_data = []

        missing_lokele = []

        missing_english = []

        # ========================================================
        # ALIGN LANGUAGES
        # ========================================================

        for usfm in sorted_usfm:

            lokele = lokele_data.get(
                usfm
            )

            english = english_data.get(
                usfm
            )

            if lokele is None:

                missing_lokele.append(
                    usfm
                )

                continue

            if english is None:

                missing_english.append(
                    usfm
                )

                continue

            aligned_data.append({

                "id": usfm,

                "book": book_name,

                "chapter":
                    lokele["chapter"],

                "verse":
                    lokele["verse"],

                "lokele":
                    lokele["text"],

                "english":
                    english["text"],
            })

        # ========================================================
        # FILE NAMES
        # ========================================================

        safe_name = (
            book_name
            .lower()
            .replace(
                " ",
                "_"
            )
        )

        dataset_file = Path(
            f"{safe_name}_lokele_english.jsonl"
        )

        missing_file = Path(
            f"{safe_name}_missing.json"
        )

        metadata_file = Path(
            f"{safe_name}_metadata.json"
        )

        # ========================================================
        # DATASET JSONL
        # ========================================================

        with dataset_file.open(
            "w",
            encoding="utf-8",
        ) as f:

            for record in aligned_data:

                f.write(
                    json.dumps(
                        record,
                        ensure_ascii=False,
                    )
                    + "\n"
                )

        # ========================================================
        # MISSING VERSES
        # ========================================================

        with missing_file.open(
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(

                {
                    "book":
                        book_name,

                    "book_code":
                        book_code,

                    "missing_lokele":
                        missing_lokele,

                    "missing_english":
                        missing_english,

                    "missing_lokele_count":
                        len(
                            missing_lokele
                        ),

                    "missing_english_count":
                        len(
                            missing_english
                        ),
                },

                f,

                ensure_ascii=False,

                indent=2,
            )

        # ========================================================
        # METADATA
        # ========================================================

        stats = self.book_stats[
            book_code
        ]

        metadata = {

            "dataset":
                "Lokele-English Parallel Corpus",

            "book":
                book_name,

            "book_code":
                book_code,

            "chapters": {

                "start":
                    self.START_CHAPTER,

                "end":
                    chapter_count,
            },

            "lokele": {

                "language":
                    "Lokele",

                "translation":
                    self.LOKELE_VERSION,

                "bible_com_version_id":
                    self.LOKELE_VERSION_ID,
            },

            "english": {

                "language":
                    "English",

                "translation":
                    self.ENGLISH_VERSION,

                "bible_com_version_id":
                    self.ENGLISH_VERSION_ID,
            },

            "statistics": {

                "lokele_verses":
                    lokele_count,

                "english_verses":
                    english_count,

                "aligned_verses":
                    len(aligned_data),

                "missing_lokele":
                    len(
                        missing_lokele
                    ),

                "missing_english":
                    len(
                        missing_english
                    ),

                "pages_processed":
                    stats[
                        "pages_processed"
                    ],

                "pages_failed":
                    stats[
                        "pages_failed"
                    ],

                "pages_expected":
                    stats[
                        "pages_expected"
                    ],
            },

            "status": {

                "complete": (

                    stats[
                        "pages_processed"
                    ]
                    ==
                    stats[
                        "pages_expected"
                    ]

                    and

                    stats[
                        "pages_failed"
                    ]
                    == 0

                    and

                    len(
                        missing_lokele
                    )
                    == 0

                    and

                    len(
                        missing_english
                    )
                    == 0
                ),

                "finish_reason":
                    str(reason),
            },

            "files": {

                "dataset":
                    str(
                        dataset_file
                    ),

                "missing":
                    str(
                        missing_file
                    ),

                "metadata":
                    str(
                        metadata_file
                    ),
            },
        }

        # ========================================================
        # WRITE METADATA
        # ========================================================

        with metadata_file.open(
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                metadata,
                f,
                ensure_ascii=False,
                indent=2,
            )

        # ========================================================
        # LOG RESULTS
        # ========================================================

        self.logger.info(
            "=" * 70
        )

        self.logger.info(
            "BOOK: %s (%s)",
            book_name,
            book_code,
        )

        self.logger.info(
            "Lokele verses: %d",
            lokele_count,
        )

        self.logger.info(
            "English verses: %d",
            english_count,
        )

        self.logger.info(
            "Aligned verses: %d",
            len(aligned_data),
        )

        self.logger.info(
            "Missing Lokele: %d",
            len(missing_lokele),
        )

        self.logger.info(
            "Missing English: %d",
            len(missing_english),
        )

        self.logger.info(
            "Pages processed: %d/%d",
            stats["pages_processed"],
            stats["pages_expected"],
        )

        self.logger.info(
            "Pages failed: %d",
            stats["pages_failed"],
        )

        self.logger.info(
            "Dataset saved: %s",
            dataset_file,
        )

        self.logger.info(
            "Missing report saved: %s",
            missing_file,
        )

        self.logger.info(
            "Metadata saved: %s",
            metadata_file,
        )

        self.logger.info(
            "=" * 70
        )