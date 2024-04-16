from dataclasses import dataclass


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
    request_rate_limit: int
    token_limit: int


@dataclass
class Response:
    header: Header
