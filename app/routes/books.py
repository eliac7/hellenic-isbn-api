from fastapi import APIRouter, Depends, HTTPException, Request

from app.config import settings
from app.dependencies import get_book_service
from app.models.book import BookResponse
from app.services.book_service import BookService
from app.utils.isbn import normalize_isbn

router = APIRouter(prefix="/books", tags=["books"])


@router.get("/{isbn}", response_model=BookResponse)
async def get_book_by_isbn(
    isbn: str,
    request: Request,
    book_service: BookService = Depends(get_book_service),
) -> BookResponse:
    normalized = normalize_isbn(isbn)
    if len(normalized) not in {10, 13}:
        raise HTTPException(status_code=400, detail="Invalid ISBN length. Use ISBN-10 or ISBN-13.")

    cache_key = f"book:{normalized}"
    cache = request.app.state.cache
    cached = await cache.get(cache_key)
    if cached is not None:
        return BookResponse.model_validate(cached)

    result = await book_service.get_by_isbn(normalized)
    if result is None:
        raise HTTPException(status_code=404, detail="Book not found for provided ISBN.")

    await cache.set(cache_key, result.model_dump(), settings.cache_ttl_seconds)
    return result
