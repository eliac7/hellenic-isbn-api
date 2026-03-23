from pydantic import BaseModel, Field


class BookResponse(BaseModel):
    source: str = Field(description="Data source, currently nlg")
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    publisher: str | None = None
    year: str | None = None
    isbn: str
    cover: str | None = None
