import re


def normalize_isbn(raw_isbn: str) -> str:
    cleaned = re.sub(r"[^0-9Xx]", "", raw_isbn).upper()
    return cleaned


def split_isbn_for_nlg(isbn: str) -> tuple[str, str]:
    """
    NLG expects split ISBN fields:
    - sel_isbn_class: group/class
    - isbn_from: remaining part

    For 13-digit ISBN with 978/979 prefix, we remove the prefix first.
    Then we use the first digit as class and the rest as search body.
    """
    working = isbn
    if len(working) == 13 and (working.startswith("978") or working.startswith("979")):
        working = working[3:]

    if not working:
        return "", ""

    group = working[0]
    rest = working[1:]
    return group, rest


def partial_isbn_candidates(isbn_rest: str) -> list[str]:
    """Build fallback partial queries from first 5 down to 3 chars."""
    candidates: list[str] = []
    for size in (5, 4, 3):
        if len(isbn_rest) >= size:
            candidates.append(isbn_rest[:size])
    return candidates
