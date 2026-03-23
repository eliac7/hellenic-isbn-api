from curl_cffi import requests as curl_requests
from fastapi import Request

from app.services.book_service import BookService
from app.services.nlg_service import NlgService


def get_book_service(request: Request) -> BookService:
    session: curl_requests.AsyncSession = request.app.state.curl_session
    return BookService(nlg_service=NlgService(session))
