from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.config import settings
from app.dependencies import get_book_service
from app.models.book import NlgTitleSearchResponse
from app.services.book_service import BookService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/title", response_model=NlgTitleSearchResponse)
async def search_by_title(
    request: Request,
    title: str = Query(..., min_length=2, description="Book title query"),
    details: bool = Query(False, description="Fetch extra fields per result from notice page"),
    details_limit: int = Query(10, ge=1, le=20, description="Max records to enrich"),
    book_service: BookService = Depends(get_book_service),
) -> NlgTitleSearchResponse:
    cleaned_title = title.strip()
    if not cleaned_title:
        raise HTTPException(status_code=400, detail="Title cannot be empty.")

    cache_key = f"title:{cleaned_title.lower()}:details:{int(details)}:limit:{details_limit}"
    cache = request.app.state.cache
    cached = await cache.get(cache_key)
    if cached is not None:
        return NlgTitleSearchResponse.model_validate(cached)

    books = await book_service.search_by_title(
        cleaned_title, details=details, details_limit=details_limit
    )
    response = NlgTitleSearchResponse(status="ok", results=books)
    await cache.set(cache_key, response.model_dump(), settings.cache_ttl_seconds)
    return response
