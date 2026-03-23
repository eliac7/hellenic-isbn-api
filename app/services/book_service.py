from app.models.book import BookResponse, NlgTitleSearchBook
from app.services.nlg_service import NlgService


class BookService:
    def __init__(self, nlg_service: NlgService) -> None:
        self.nlg_service = nlg_service

    async def get_by_isbn(self, isbn: str) -> BookResponse | None:
        return await self.nlg_service.search_by_isbn(isbn)

    async def search_by_title(
        self, title: str, details: bool = False, details_limit: int = 10
    ) -> list[NlgTitleSearchBook]:
        results = await self.nlg_service.search_by_title(
            title, details=details, details_limit=details_limit
        )
        return [NlgTitleSearchBook.model_validate(item) for item in results]
