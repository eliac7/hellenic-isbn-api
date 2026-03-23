from pydantic import BaseModel, Field


class BookResponse(BaseModel):
    source: str = Field(description="Data source, currently nlg")
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    publisher: str | None = None
    year: str | None = None
    isbn: str
    cover: str | None = None


class NlgTitleSearchBook(BaseModel):
    title: str | None = None
    contributors: list[str] = Field(default_factory=list)
    publisher: str | None = None
    year: str | None = None
    isbn: str | None = None
    language: str | None = None
    original_title: str | None = None
    cover: str | None = None


class NlgTitleSearchResponse(BaseModel):
    status: str
    results: list[NlgTitleSearchBook]
