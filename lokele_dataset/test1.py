
import scrapy
import html
import codecs
import json
from pathlib import Path

from parsel import Selector


class LokeleSpider(scrapy.Spider):

    name = "lokele"
    allowed_domains = ["bible.com"]

    custom_settings = {

        "ROBOTSTXT_OBEY": False,

        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },

        "TWISTED_REACTOR": (
            "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
        ),

        "DOWNLOAD_TIMEOUT": 120,

        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 60000,

        "FEED_EXPORT_ENCODING": "utf-8",

        "DOWNLOAD_DELAY": 0.2,
    }

    # =========================================================
    # CONFIGURATION
    # =========================================================

    LOKELE_VERSION_ID = 1496
    LOKELE_VERSION = "NTKE58"

    ENGLISH_VERSION_ID = 206
    ENGLISH_VERSION = "WEBUS"

    BOOK = "MAT"

    # =========================================================
    # TEST WITH CHAPTERS 1-3 FIRST
    # =========================================================
    #
    # Once the test succeeds, change:
    #
    # END_CHAPTER = 28
    #
    # =========================================================

    START_CHAPTER = 1
    END_CHAPTER = 3

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # Instance-level data storage.
        self.data = {
            "lokele": {},
            "english": {},
        }

        self.pages_processed = 0
        self.total_pages = 0

    # =========================================================
    # START
    # =========================================================
    #
    # IMPORTANT:
    #
    # Scrapy 2.18 no longer calls start_requests().
    #
    # We therefore use:
    #
    #     async def start(self)
    #
    # =========================================================

    async def start(self):

        total_chapters = (
            self.END_CHAPTER - self.START_CHAPTER + 1
        )

        self.total_pages = total_chapters * 2

        self.logger.info("=" * 60)
        self.logger.info("STARTING LOKELE-ENGLISH SCRAPER")
        self.logger.info("Book: Matthew")
        self.logger.info(
            "Chapters: %d-%d",
            self.START_CHAPTER,
            self.END_CHAPTER
        )
        self.logger.info(
            "Expected pages: %d",
            self.total_pages
        )
        self.logger.info("=" * 60)

        # =====================================================
        # LOKELE REQUESTS
        # =====================================================

        for chapter in range(
            self.START_CHAPTER,
            self.END_CHAPTER + 1
        ):

            url = (
                f"https://www.bible.com/bible/1496/"
                f"MAT.{chapter}.NTKE58"
            )

            self.logger.info(
                "Scheduling Lokele Matthew %d",
                chapter
            )

            yield scrapy.Request(
                url=url,

                meta={
                    "playwright": True,

                    "playwright_page_goto_kwargs": {
                        "wait_until": "domcontentloaded",
                        "timeout": 60000,
                    },

                    "language": "lokele",
                    "chapter": chapter,
                },

                callback=self.parse,

                errback=self.handle_error,
            )

        # =====================================================
        # ENGLISH REQUESTS
        # =====================================================

        for chapter in range(
            self.START_CHAPTER,
            self.END_CHAPTER + 1
        ):

            url = (
                f"https://www.bible.com/bible/206/"
                f"MAT.{chapter}.WEBUS"
            )

            self.logger.info(
                "Scheduling English Matthew %d",
                chapter
            )

            yield scrapy.Request(
                url=url,

                meta={
                    "playwright": True,

                    "playwright_page_goto_kwargs": {
                        "wait_until": "domcontentloaded",
                        "timeout": 60000,
                    },

                    "language": "english",
                    "chapter": chapter,
                },

                callback=self.parse,

                errback=self.handle_error,
            )

    # =========================================================
    # PARSE
    # =========================================================

    def parse(self, response):

        language = response.meta["language"]

        requested_chapter = response.meta["chapter"]

        self.pages_processed += 1

        self.logger.info("=" * 60)

        self.logger.info(
            "PROCESSING %s",
            response.url
        )

        self.logger.info(
            "Language: %s",
            language
        )

        self.logger.info(
            "Chapter: %d",
            requested_chapter
        )

        self.logger.info(
            "Status: %d",
            response.status
        )

        self.logger.info(
            "Pages processed: %d / %d",
            self.pages_processed,
            self.total_pages
        )

        self.logger.info("=" * 60)

        # =====================================================
        # EXTRACT VERSES
        # =====================================================

        verses = self.extract_verses(response)

        self.logger.info(
            "%s Matthew %d -> %d UNIQUE VERSES",
            language.upper(),
            requested_chapter,
            len(verses)
        )

        # =====================================================
        # STORE VERSES
        # =====================================================

        for usfm, verse_data in verses.items():

            # Make sure the verse belongs to the requested
            # chapter.

            if verse_data["chapter"] != requested_chapter:
                continue

            self.data[language][usfm] = verse_data

        # =====================================================
        # PROGRESS
        # =====================================================

        self.logger.info(
            "Total unique Lokele verses so far: %d",
            len(self.data["lokele"])
        )

        self.logger.info(
            "Total unique English verses so far: %d",
            len(self.data["english"])
        )

    # =========================================================
    # EXTRACT VERSES
    # =========================================================

    def extract_verses(self, response):

        """
        Extract verses from Bible.com's embedded
        Next.js HTML data.

        The method looks for script blocks containing
        data-usfm attributes and then extracts:

            book
            chapter
            verse
            text
        """

        # =====================================================
        # FIND SCRIPT BLOCKS
        # =====================================================

        scripts = response.css(
            "script::text"
        ).getall()

        self.logger.info(
            "FOUND %d SCRIPT TEXT BLOCKS",
            len(scripts)
        )

        # Dictionary prevents duplicate USFM verses.

        verses_dict = {}

        # =====================================================
        # PROCESS SCRIPTS
        # =====================================================

        for script_number, script in enumerate(scripts):

            # Only process scripts containing verse data.

            if "data-usfm" not in script:
                continue

            self.logger.info(
                "Processing script %d, length=%d",
                script_number,
                len(script)
            )

            # =================================================
            # DECODE SCRIPT
            # =================================================

            try:

                decoded = codecs.decode(
                    script,
                    "unicode_escape"
                )

                decoded = html.unescape(
                    decoded
                )

            except Exception as e:

                self.logger.error(
                    "Could not decode script %d: %s",
                    script_number,
                    e
                )

                continue

            # =================================================
            # CREATE SELECTOR
            # =================================================

            selector = Selector(
                text=decoded
            )

            # =================================================
            # FIND VERSES
            # =================================================

            verse_elements = selector.css(
                "span.verse[data-usfm]"
            )

            self.logger.info(
                "SCRIPT %d -> FOUND %d VERSE ELEMENTS",
                script_number,
                len(verse_elements)
            )

            # =================================================
            # PROCESS EACH VERSE
            # =================================================

            for verse in verse_elements:

                # -------------------------------------------------
                # USFM
                # -------------------------------------------------

                usfm = verse.attrib.get(
                    "data-usfm"
                )

                if not usfm:
                    continue

                # -------------------------------------------------
                # Parse USFM
                #
                # Example:
                #
                # MAT.1.1
                # -------------------------------------------------

                parts = usfm.split(".")

                if len(parts) != 3:
                    continue

                book = parts[0]

                try:

                    chapter = int(
                        parts[1]
                    )

                    verse_number = int(
                        parts[2]
                    )

                except ValueError:

                    continue

                # -------------------------------------------------
                # Only Matthew
                # -------------------------------------------------

                if book != self.BOOK:
                    continue

                # =================================================
                # EXTRACT TEXT
                # =================================================

                text = " ".join(

                    t.strip()

                    for t in verse.css(
                        "span.content ::text"
                    ).getall()

                    if t.strip()

                )

                # =================================================
                # FALLBACK
                # =================================================

                if not text:

                    text = " ".join(

                        t.strip()

                        for t in verse.css(
                            "span.content::text"
                        ).getall()

                        if t.strip()

                    )

                # =================================================
                # CLEAN TEXT
                # =================================================

                text = " ".join(
                    text.split()
                )

                # -------------------------------------------------
                # Ignore empty verses
                # -------------------------------------------------

                if not text:
                    continue

                # =================================================
                # CREATE RECORD
                # =================================================

                new_record = {

                    "book": book,

                    "chapter": chapter,

                    "verse": verse_number,

                    "text": text,

                }

                # =================================================
                # DEDUPLICATION
                # =================================================
                #
                # Bible.com can contain the same verse more
                # than once in embedded HTML.
                #
                # Keep the longest version of the text.
                #
                # =================================================

                existing = verses_dict.get(
                    usfm
                )

                if (
                    existing is None
                    or len(text)
                    > len(existing["text"])
                ):

                    verses_dict[usfm] = new_record

        return verses_dict

    # =========================================================
    # ERROR HANDLER
    # =========================================================

    def handle_error(self, failure):

        request = failure.request

        self.logger.error("=" * 60)

        self.logger.error(
            "REQUEST FAILED"
        )

        self.logger.error(
            "URL: %s",
            request.url
        )

        self.logger.error(
            "ERROR: %s",
            failure.value
        )

        self.logger.error("=" * 60)

    # =========================================================
    # SPIDER CLOSED
    # =========================================================

    def closed(self, reason):

        self.logger.info("=" * 60)

        self.logger.info(
            "SPIDER CLOSED"
        )

        self.logger.info(
            "Reason: %s",
            reason
        )

        self.logger.info(
            "Pages processed: %d / %d",
            self.pages_processed,
            self.total_pages
        )

        self.logger.info("=" * 60)

        # =====================================================
        # COUNTS
        # =====================================================

        lokele_count = len(
            self.data["lokele"]
        )

        english_count = len(
            self.data["english"]
        )

        self.logger.info(
            "Lokele unique verses: %d",
            lokele_count
        )

        self.logger.info(
            "English unique verses: %d",
            english_count
        )

        # =====================================================
        # ALL VERSE IDS
        # =====================================================

        all_usfm = (

            set(
                self.data["lokele"].keys()
            )

            |

            set(
                self.data["english"].keys()
            )

        )

        # =====================================================
        # SORT
        # =====================================================

        sorted_usfm = sorted(

            all_usfm,

            key=lambda x: (

                int(
                    x.split(".")[1]
                ),

                int(
                    x.split(".")[2]
                )

            )
        )

        # =====================================================
        # ALIGN
        # =====================================================

        aligned_data = []

        missing_lokele = []

        missing_english = []

        for usfm in sorted_usfm:

            lokele = self.data[
                "lokele"
            ].get(usfm)

            english = self.data[
                "english"
            ].get(usfm)

            # =================================================
            # MISSING LOKELE
            # =================================================

            if lokele is None:

                missing_lokele.append(
                    usfm
                )

                continue

            # =================================================
            # MISSING ENGLISH
            # =================================================

            if english is None:

                missing_english.append(
                    usfm
                )

                continue

            # =================================================
            # CREATE ALIGNED RECORD
            # =================================================

            aligned_data.append({

                "id": usfm,

                "book": "Matthew",

                "chapter": lokele[
                    "chapter"
                ],

                "verse": lokele[
                    "verse"
                ],

                "lokele": lokele[
                    "text"
                ],

                "english": english[
                    "text"
                ],

            })

        # =====================================================
        # SAVE DATASET
        # =====================================================

        dataset_file = Path(
            "matthew_1_28_lokele_english.jsonl"
        )

        with dataset_file.open(
            "w",
            encoding="utf-8"
        ) as f:

            for record in aligned_data:

                f.write(

                    json.dumps(
                        record,
                        ensure_ascii=False
                    )

                    + "\n"
                )

        # =====================================================
        # SAVE MISSING VERSES
        # =====================================================

        missing_file = Path(
            "matthew_1_28_missing.json"
        )

        missing_data = {

            "missing_lokele":
                missing_lokele,

            "missing_english":
                missing_english,

        }

        with missing_file.open(
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                missing_data,
                f,
                ensure_ascii=False,
                indent=2
            )

        # =====================================================
        # SAVE METADATA
        # =====================================================

        metadata = {

            "dataset":
                "Lokele-English Parallel Corpus",

            "book":
                "Matthew",

            "chapters": {

                "start":
                    self.START_CHAPTER,

                "end":
                    self.END_CHAPTER,

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
                    len(missing_lokele),

                "missing_english":
                    len(missing_english),

                "pages_processed":
                    self.pages_processed,

                "pages_expected":
                    self.total_pages,

            },

            "status": {

                "complete":
                    (
                        self.pages_processed
                        == self.total_pages
                        and
                        len(missing_lokele)
                        == 0
                        and
                        len(missing_english)
                        == 0
                    ),

                "finish_reason":
                    reason,

            },

            "files": {

                "dataset":
                    str(dataset_file),

                "missing":
                    str(missing_file),

            }

        }

        metadata_file = Path(
            "matthew_1_28_metadata.json"
        )

        with metadata_file.open(
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                metadata,
                f,
                ensure_ascii=False,
                indent=2
            )

        # =====================================================
        # FINAL REPORT
        # =====================================================

        self.logger.info("=" * 60)

        self.logger.info(
            "FINAL DATASET REPORT"
        )

        self.logger.info("=" * 60)

        self.logger.info(
            "Lokele verses: %d",
            lokele_count
        )

        self.logger.info(
            "English verses: %d",
            english_count
        )

        self.logger.info(
            "Aligned verses: %d",
            len(aligned_data)
        )

        self.logger.info(
            "Missing Lokele: %d",
            len(missing_lokele)
        )

        self.logger.info(
            "Missing English: %d",
            len(missing_english)
        )

        self.logger.info(
            "Pages processed: %d / %d",
            self.pages_processed,
            self.total_pages
        )

        self.logger.info(
            "Dataset saved: %s",
            dataset_file
        )

        self.logger.info(
            "Metadata saved: %s",
            metadata_file
        )

        self.logger.info(
            "Missing verses saved: %s",
            missing_file
        )

        self.logger.info("=" * 60)
