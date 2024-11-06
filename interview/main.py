import json
import os
from typing import List

from interview.request import Request, Response
from interview.server import Server

ENDPOINT_FILE: str = "endpoints.json"
REQUESTS_FILE: str = "requests.json"


DATA_PATH: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
REQUESTS_PATH: str = os.path.join(DATA_PATH, REQUESTS_FILE)


def init_server(verbose: bool = False) -> Server:
    server: Server = Server(verbose)
    endpoints_path: str = os.path.join(DATA_PATH, ENDPOINT_FILE)
    for endpoint_dict in json.load(open(endpoints_path)):
        server.add_endpoint(
            route=endpoint_dict["route"],
            max_requests_per_minute=endpoint_dict["max_requests_per_minute"],
            max_tokens_per_minute=endpoint_dict["max_tokens_per_minute"],
        )
    return server


def read_requests() -> List[Request]:
    return [Request(token_count=request_dict["token_count"]) for request_dict in json.load(open(REQUESTS_PATH))]


def main() -> None:
    server: Server = init_server()
    with server.up() as server:
        # Example Code
        for _ in range(100):
            response: Response = server.receive("/chat/gpt-3.5-turbo", Request(token_count=10))
            print(response)


if __name__ == "__main__":
    main()
