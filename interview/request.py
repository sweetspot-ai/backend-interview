from dataclasses import dataclass
from typing import Optional, Union


@dataclass
class Request:
    token_count: int


@dataclass
class LoggedRequest:
    request: Request
    route: str
    elapsed_time_sec: int
    status: str


@dataclass
class Header:
    max_requests_per_minute: int
    max_tokens_per_minute: int
    remaining_requests_per_minute: int
    remaining_tokens_per_minute: int


class RateLimitException(Exception):
    pass


class RequestLimitExceededException(RateLimitException):
    def __init__(self, route: str, request: Request, *args, **kwargs):
        super().__init__(f"Exceeded requests limit for endpoint {route} with request {request}", *args, **kwargs)


class TokenLimitExceededException(RateLimitException):
    def __init__(self, route: str, request: Request, *args, **kwargs):
        super().__init__(f"Exceeded tokens limit for endpoint {route} with request {request}", *args, **kwargs)


@dataclass
class Response:
    header: Header
    exc: Optional[Union[RequestLimitExceededException, TokenLimitExceededException]] = None
