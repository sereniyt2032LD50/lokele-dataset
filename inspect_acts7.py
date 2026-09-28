from pathlib import Path
from bs4 import BeautifulSoup

html = Path("diagnostic_ACT_7_NTKE58.html").read_text(
    encoding="utf-8"
)

soup = BeautifulSoup(html, "html.parser")

print("ACTS 7 VERSES FOUND")
print("=" * 70)

for element in soup.select("[data-usfm]"):
    usfm = element.get("data-usfm", "")

    if usfm.startswith("ACT.7."):
        content = element.select_one('[class*="content"]')

        if content:
            text = content.get_text(" ", strip=True)
        else:
            text = element.get_text(" ", strip=True)

        print(usfm, "|", text[:200])