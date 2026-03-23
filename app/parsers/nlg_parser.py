import re
from bs4 import BeautifulSoup


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = " ".join(value.split()).strip()
    return text or None


def parse_nlg_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    detailed_books: list[dict] = []
    books = []

    detail_scopes = list(soup.select("blockquote")) + list(soup.select("div[id^='div_public']"))
    for block in detail_scopes:
        has_structured_data = False
        book = {
            "title": None,
            "original_title": None,
            "contributors": [],
            "publisher": None,
            "year": None,
            "isbn": None,
            "language": None,
            "cover": None,
        }

        title_el = block.select_one(".public_title")
        if title_el:
            book["title"] = _clean(title_el.get_text())

        img = block.select_one("img.vignetteimg")
        if img:
            book["cover"] = _clean(img.get("src"))

        for row in block.select("tr"):
            label_el = row.select_one(".etiq_champ")
            value_el = row.select_one("td:nth-of-type(2)")

            if not label_el or not value_el:
                continue

            label = label_el.get_text(strip=True)
            value = _clean(value_el.get_text(" ", strip=True))

            if not value:
                continue

            if "Τίτλος Πρωτοτύπου" in label:
                book["original_title"] = value
                has_structured_data = True

            elif "Συντελεστές" in label:
                book["contributors"] = [
                    c.strip() for c in value.split(";") if c.strip()
                ]
                has_structured_data = True

            elif "Εκδότης" in label:
                book["publisher"] = value
                has_structured_data = True

            elif "Έτος Έκδοσης" in label:
                book["year"] = value
                has_structured_data = True

            elif "ISBN" in label:
                book["isbn"] = value
                has_structured_data = True

            elif "Γλώσσες" in label:
                book["language"] = value
                has_structured_data = True

        if not book["title"]:
            header = block.select_one(".header_title")
            if header:
                book["title"] = _clean(header.get_text())

        if has_structured_data and (book["title"] or book["isbn"]):
            detailed_books.append(book)

    if detailed_books:
        return detailed_books

    notice_nodes = soup.select("div.notice-parent")
    if notice_nodes:
        for node in notice_nodes:
            title_el = node.select_one(".header_title")
            label_el = node.select_one(".isn-label")
            expand_img = node.select_one("img.img_plus[param]")
            whole_text = _clean(node.get_text(" ", strip=True)) or ""
            notice_id = None
            node_id = node.get("id") or ""
            node_match = re.search(r"el(\d+)Parent", node_id)
            if node_match:
                notice_id = node_match.group(1)
            elif title_el and title_el.get("notice"):
                notice_id = _clean(title_el.get("notice"))

            title = _clean(title_el.get_text()) if title_el else None
            isbn = None
            if label_el:
                label_text = _clean(label_el.get_text()) or ""
                if "ISBN" in label_text:
                    raw = label_text.split("ISBN", 1)[-1]
                    raw = raw.replace(":", "").replace(")", "").replace("(", "").strip().rstrip(".")
                    isbn = _clean(raw)

            contributors: list[str] = []
            if title and "/" in whole_text:
                right = whole_text.split("/", 1)[1]
                contributors = [c.strip() for c in right.split(";") if c.strip()]
                if contributors and contributors[0].startswith("(ISBN"):
                    contributors = []
                if contributors and ")" in contributors[0] and " / " in whole_text and " / " in (title or ""):
                    contributors = []

            notice_cmd = _clean(expand_img.get("param")) if expand_img else None

            compact_book = {
                "title": title,
                "original_title": None,
                "contributors": contributors,
                "publisher": None,
                "year": None,
                "isbn": isbn,
                "language": None,
                "cover": None,
                "notice_id": notice_id,
                "notice_cmd": notice_cmd,
            }
            if compact_book["title"] or compact_book["isbn"]:
                books.append(compact_book)

    return books
