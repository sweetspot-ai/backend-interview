import datetime
import pprint
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from typing import Dict, Generator, Union

from interview.request import (
    Header,
    LoggedRequest,
    Request,
    RequestLimitExceededException,
    Response,
    TokenLimitExceededException,
)

FULFILL_STATUS: str = "fulfilled"
HEARTBEAT_DURATION_SEC: int = 1


class InferenceLogger:
    def __init__(self, verbose: bool):
        self.verbose: bool = verbose
        self.init_time: datetime.datetime = datetime.datetime.now()
        self.info_logs: defaultdict[str, list] = defaultdict(list)
        self.fulfilled_logs: defaultdict[str, list] = defaultdict(list)
        self.errored_logs: defaultdict[str, list] = defaultdict(list)

    def _create_logged_request(self, route: str, request: Request, status: str) -> LoggedRequest:
        return LoggedRequest(
            request=request,
            route=route,
            elapsed_time_sec=(datetime.datetime.now() - self.init_time).seconds,
            status=status,
        )

    def info(self, route: str, msg: str) -> None:
        self.info_logs[route].append(msg)
        if self.verbose:
            print(msg)

    def fulfill(self, route: str, request: Request) -> None:
        logged_request: LoggedRequest = self._create_logged_request(route=route, request=request, status=FULFILL_STATUS)
        self.fulfilled_logs[route].append(logged_request)
        if self.verbose:
            print(f"Fulfilled request {request} with route {route}")

    def error(self, route: str, request: Request, error: Exception) -> None:
        logged_request: LoggedRequest = self._create_logged_request(route=route, request=request, status=str(error))
        self.errored_logs[route].append(logged_request)
        if self.verbose:
            print(f"Received error: {error} from route {route}")

    def get_statistics(self) -> Dict[str, int]:
        total_elapsed_time: int = sum(log.elapsed_time_sec for logs in self.fulfilled_logs.values() for log in logs)
        num_errors: int = sum(len(logs) for logs in self.errored_logs.values())
        longest_elapsed_time: int = max(
            (log.elapsed_time_sec for logs in self.fulfilled_logs.values() for log in logs), default=0
        )
        total_fulfilled: int = sum(len(logs) for logs in self.fulfilled_logs.values())

        return {
            "total_elapsed_time": total_elapsed_time,
            "num_errors": num_errors,
            "longest_elapsed_time": longest_elapsed_time,
            "total_fulfilled": total_fulfilled,
        }


class InferenceEndpoint:
    def __init__(
        self,
        route: str,
        max_requests_per_minute: int,
        max_tokens_per_minute: int,
        logger: InferenceLogger,
        heartbeat_duration_sec: int = HEARTBEAT_DURATION_SEC,
    ):
        self.route: str = route
        self.max_requests_per_minute: int = max_requests_per_minute
        self.max_tokens_per_minute: int = max_tokens_per_minute
        self.heartbeat_duration_sec: int = heartbeat_duration_sec
        self._logger: InferenceLogger = logger
        self._requests_capacity: int = max_requests_per_minute
        self._tokens_capacity: int = max_tokens_per_minute
        self._lock: threading.Lock = threading.Lock()
        self._stop: threading.Event = threading.Event()

    def receive(self, request: Request) -> Response:
        exc: Union[RequestLimitExceededException, TokenLimitExceededException]
        if self._requests_capacity == 0:
            exc = RequestLimitExceededException(route=self.route, request=request)
            self._logger.error(self.route, request, exc)
            return Response(
                header=Header(
                    max_requests_per_minute=self.max_requests_per_minute,
                    max_tokens_per_minute=self.max_tokens_per_minute,
                    remaining_requests_per_minute=self._requests_capacity,
                    remaining_tokens_per_minute=self._tokens_capacity,
                ),
                exc=exc,
            )
        if self._tokens_capacity - request.token_count < 0:
            exc = TokenLimitExceededException(route=self.route, request=request)
            self._logger.error(self.route, request, exc)
            return Response(
                header=Header(
                    max_requests_per_minute=self.max_requests_per_minute,
                    max_tokens_per_minute=self.max_tokens_per_minute,
                    remaining_requests_per_minute=self._requests_capacity,
                    remaining_tokens_per_minute=self._tokens_capacity,
                ),
                exc=exc,
            )
        with self._lock:
            self._requests_capacity -= 1
            self._tokens_capacity -= request.token_count
            self._logger.fulfill(self.route, request)
            return Response(
                header=Header(
                    max_requests_per_minute=self.max_requests_per_minute,
                    max_tokens_per_minute=self.max_tokens_per_minute,
                    remaining_requests_per_minute=self._requests_capacity,
                    remaining_tokens_per_minute=self._tokens_capacity,
                ),
                exc=None,
            )

    def start(self) -> None:
        self._logger.info(self.route, f"Starting endpoint {self.route}")
        while not self._stop.is_set():
            self._refresh_limits()
            time.sleep(self.heartbeat_duration_sec)

    def teardown(self) -> None:
        self._stop.set()

    def _refresh_limits(self) -> None:
        with self._lock:
            self._requests_capacity = min(
                self.max_requests_per_minute,
                self._requests_capacity + (self.max_requests_per_minute // 60 * self.heartbeat_duration_sec),
            )
            self._logger.info(
                self.route, f"Refreshing endpoint {self.route} with updated request capacity {self._requests_capacity}"
            )
            self._tokens_capacity = min(
                self.max_tokens_per_minute,
                self._tokens_capacity + (self.max_tokens_per_minute // 60 * self.heartbeat_duration_sec),
            )
            self._logger.info(
                self.route, f"Refreshing endpoint {self.route} with updated token capacity {self._requests_capacity}"
            )


class Server:
    def __init__(self, verbose: bool = True) -> None:
        self.routes: Dict[str, InferenceEndpoint] = {}
        self.pool: Dict[str, threading.Thread] = {}
        self.verbose: bool = verbose
        self._logger: InferenceLogger = InferenceLogger(verbose)

    def add_endpoint(self, route: str, max_requests_per_minute: int, max_tokens_per_minute: int) -> None:
        self.routes[route] = InferenceEndpoint(route, max_requests_per_minute, max_tokens_per_minute, self._logger)

    @contextmanager
    def up(self) -> Generator["Server", None, None]:
        if self.pool:
            raise ValueError("Server already started!")
        try:
            for route, endpoint in self.routes.items():
                self.pool[route] = threading.Thread(target=endpoint.start)
                self.pool[route].start()
            yield self
        finally:
            self.teardown()

    def teardown(self) -> None:
        for endpoint in self.routes.values():
            endpoint.teardown()
        for thread in self.pool.values():
            thread.join()
        pprint.pprint(self._logger.get_statistics())

    def receive(self, route: str, request: Request) -> Response:
        response: Response = self.routes[route].receive(request)
        return response
