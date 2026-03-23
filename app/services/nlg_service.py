import logging

from curl_cffi import requests as curl_requests

from app.config import settings
from app.models.book import BookResponse
from app.parsers.nlg_parser import parse_nlg_html
from app.utils.isbn import partial_isbn_candidates, split_isbn_for_nlg

logger = logging.getLogger(__name__)


class NlgService:
    def __init__(self, session: curl_requests.AsyncSession) -> None:
        self.session = session
        self.url = f"{settings.nlg_base_url}/index.php?search_type_asked=search_nlg_books&callback=1"

    async def search_by_isbn(self, isbn: str) -> BookResponse | None:
        isbn_group, isbn_rest = split_isbn_for_nlg(isbn)
        if not isbn_group:
            return None

        attempts = [isbn_rest] + partial_isbn_candidates(isbn_rest)

        for query in attempts:
            if not query:
                continue
            result = await self._search_once(isbn_group, query, isbn)
            if result:
                return result
        return None

    async def _search_once(
        self, isbn_group: str, isbn_from: str, input_isbn: str
    ) -> BookResponse | None:
        payload = {
            "nlg_what": "isbn",
            "sel_isbn_class": isbn_group,
            "isbn_from": isbn_from,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": settings.nlg_base_url,
        }

        try:
            response = await self.session.post(
                self.url,
                data=payload,
                headers=headers,
                impersonate=settings.curl_impersonate,
                verify=False,
            )
            response.raise_for_status()
        except Exception:
            logger.exception(
                "NLG request failed for isbn_group=%s isbn_from=%s",
                isbn_group,
                isbn_from,
            )
            return None

        candidates = parse_nlg_html(response.text)
        if not candidates:
            return None

        picked = candidates[0]
        return BookResponse(
            source="nlg",
            title=(picked.get("title") or picked.get("original_title")),
            authors=(picked.get("contributors") or []),  # type: ignore[arg-type]
            publisher=(
                picked.get("publisher")
                if isinstance(picked.get("publisher"), str)
                else None
            ),
            year=(picked.get("year") if isinstance(picked.get("year"), str) else None),
            isbn=(
                picked.get("isbn")
                if isinstance(picked.get("isbn"), str)
                else input_isbn
            ),
            cover=(
                picked.get("cover") if isinstance(picked.get("cover"), str) else None
            ),
        )
