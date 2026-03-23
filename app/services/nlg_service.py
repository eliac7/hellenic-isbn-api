import logging
import asyncio
from urllib.parse import unquote

import certifi
from curl_cffi import requests as curl_requests
from curl_cffi.requests.exceptions import CertificateVerifyError
from bs4 import BeautifulSoup

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
            response = await self._post_nlg(self.url, payload, headers)
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

    async def search_by_title(
        self, title: str, details: bool = False, details_limit: int = 10
    ) -> list[dict]:
        url = f"{settings.nlg_base_url}/index.php?lvl=search_result"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": f"{settings.nlg_base_url}/",
        }
        payload = {
            "user_query": title,
            "look_TITLE": "1",
            "typdoc": "",
            "surligne": "",
            "ok": "Αναζήτηση",
            "look_FIRSTACCESS": "1",
        }

        try:
            response = await self._post_nlg(url, payload, headers)
            response.raise_for_status()
        except Exception:
            logger.exception("NLG title search failed for title=%s", title)
            return []

        parsed = parse_nlg_html(response.text)
        if parsed:
            return await self._enrich_title_results(parsed, details, details_limit)

        more_html = await self._fetch_more_results_html(response.text)
        if not more_html:
            return []
        parsed_more = parse_nlg_html(more_html)
        return await self._enrich_title_results(parsed_more, details, details_limit)

    async def _post_nlg(
        self, url: str, payload: dict[str, str], headers: dict[str, str]
    ):
        verify_value: bool | str = certifi.where() if settings.ssl_verify else False
        try:
            return await self.session.post(
                url,
                data=payload,
                headers=headers,
                impersonate=settings.curl_impersonate,
                verify=verify_value,
            )
        except CertificateVerifyError:
            if settings.ssl_fallback_insecure:
                logger.warning("NLG SSL verify failed. Retrying insecurely (verify=False).")
                return await self.session.post(
                    url,
                    data=payload,
                    headers=headers,
                    impersonate=settings.curl_impersonate,
                    verify=False,
                )
            raise

    async def _fetch_more_results_html(self, search_result_html: str) -> str | None:
        soup = BeautifulSoup(search_result_html, "html.parser")
        form = soup.select_one("form[name='search_objects']")
        if form is None:
            return None

        action = form.get("action") or "./index.php?lvl=more_results"
        action_url = f"{settings.nlg_base_url}/{action.lstrip('./')}"
        payload: dict[str, str] = {}
        for field in form.select("input[name]"):
            name = field.get("name")
            if not name:
                continue
            payload[name] = field.get("value", "")

        if not payload:
            return None

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": f"{settings.nlg_base_url}/index.php?lvl=search_result",
        }

        try:
            response = await self._post_nlg(action_url, payload, headers)
            response.raise_for_status()
            return response.text
        except Exception:
            logger.exception("NLG more_results request failed")
            return None

    async def _enrich_title_results(
        self, results: list[dict], details: bool, details_limit: int
    ) -> list[dict]:
        if not details or not results:
            return results

        limit = min(max(details_limit, 1), len(results))
        tasks = []
        for item in results[:limit]:
            notice_cmd = item.get("notice_cmd")
            notice_id = item.get("notice_id")
            if isinstance(notice_cmd, str) and notice_cmd.strip():
                tasks.append(self._fetch_notice_details_by_ajax(notice_cmd.strip()))
            elif isinstance(notice_id, str) and notice_id.strip():
                tasks.append(self._fetch_notice_details_by_display(notice_id.strip()))
            else:
                tasks.append(asyncio.sleep(0, result=None))

        details_results = await asyncio.gather(*tasks, return_exceptions=True)

        for idx, detail in enumerate(details_results):
            if isinstance(detail, dict):
                base = results[idx]
                for key in (
                    "title",
                    "contributors",
                    "publisher",
                    "year",
                    "isbn",
                    "language",
                    "original_title",
                    "cover",
                ):
                    value = detail.get(key)
                    if value not in (None, "", []):
                        base[key] = value

        for item in results:
            item.pop("notice_id", None)
            item.pop("notice_cmd", None)
        return results

    async def _fetch_notice_details_by_display(self, notice_id: str) -> dict | None:
        url = f"{settings.nlg_base_url}/index.php?lvl=notice_display&id={notice_id}"
        headers = {"Referer": f"{settings.nlg_base_url}/"}
        try:
            response = await self._post_nlg(url, payload={}, headers=headers)
            response.raise_for_status()
        except Exception:
            logger.exception("NLG notice details request failed for id=%s", notice_id)
            return None

        parsed = parse_nlg_html(response.text)
        if not parsed:
            return None
        return parsed[0]

    async def _fetch_notice_details_by_ajax(self, notice_cmd: str) -> dict | None:
        url = f"{settings.nlg_base_url}/ajax.php?module=expand_notice&categ=expand"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": settings.nlg_base_url,
            "Referer": f"{settings.nlg_base_url}/index.php?lvl=more_results",
        }
        payload = {"notice_affichage_cmd": unquote(notice_cmd)}
        try:
            response = await self._post_nlg(url, payload=payload, headers=headers)
            response.raise_for_status()
        except Exception:
            logger.exception("NLG ajax details request failed")
            return None

        parsed = parse_nlg_html(response.text)
        if not parsed:
            return None
        return parsed[0]
