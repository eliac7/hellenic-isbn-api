from bs4 import BeautifulSoup


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = " ".join(value.split()).strip()
    return text or None


def parse_nlg_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    books = []

    # κάθε αποτέλεσμα είναι μέσα σε blockquote
    for block in soup.select("blockquote"):
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

        # ✅ title (main)
        title_el = block.select_one(".public_title")
        if title_el:
            book["title"] = _clean(title_el.get_text())

        # ✅ cover
        img = block.select_one("img.vignetteimg")
        if img:
            book["cover"] = _clean(img.get("src"))

        # ✅ structured rows
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

            elif "Συντελεστές" in label:
                # split authors properly
                book["contributors"] = [
                    c.strip() for c in value.split(";") if c.strip()
                ]

            elif "Εκδότης" in label:
                book["publisher"] = value

            elif "Έτος Έκδοσης" in label:
                book["year"] = value

            elif "ISBN" in label:
                book["isbn"] = value

            elif "Γλώσσες" in label:
                book["language"] = value

        # fallback title αν δεν υπάρχει public_title
        if not book["title"]:
            header = block.select_one(".header_title")
            if header:
                book["title"] = _clean(header.get_text())

        # only append valid results
        if book["title"] or book["isbn"]:
            books.append(book)

    return books
