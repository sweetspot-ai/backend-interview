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
