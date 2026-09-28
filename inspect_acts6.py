from pathlib import Path

from bs4 import BeautifulSoup

html = Path("diagnostic_ACT_6_NTKE58.html").read_text(
    encoding="utf-8"
)

soup = BeautifulSoup(html, "html.parser")

print("ACTS 6 VERSES FOUND")
print("=" * 50)

for element in soup.select("[data-usfm]"):
    usfm = element.get("data-usfm", "")

    if usfm.startswith("ACT.6."):
        text = element.get_text(" ", strip=True)
        print(usfm, "|", text[:120])