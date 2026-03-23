from app.models.book import BookResponse
from app.services.nlg_service import NlgService


class BookService:
    def __init__(self, nlg_service: NlgService) -> None:
        self.nlg_service = nlg_service

    async def get_by_isbn(self, isbn: str) -> BookResponse | None:
        return await self.nlg_service.search_by_isbn(isbn)
