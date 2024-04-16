import json
import os

from interview.server import Server
from interview.request import Request, Response

ENDPOINT_FILE: str = "endpoints.json"


def DATA_PATH() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def init_server(verbose: bool = True) -> Server:
    server: Server = Server(verbose)
    endpoints_path: str = os.path.join(DATA_PATH(), ENDPOINT_FILE)
    for endpoint_dict in json.load(open(endpoints_path)):
        server.add_endpoint(
            route=endpoint_dict["route"],
            max_requests_per_minute=endpoint_dict["max_requests_per_minute"],
            max_tokens_per_minute=endpoint_dict["max_tokens_per_minute"],
        )
    return server


def main() -> None:
    server: Server = init_server()
    with server.up() as server:
        # Example Code
        for _ in range(100):
            response: Response = server.receive("/a", Request(token_count=10))
            print(response)


if __name__ == "__main__":
    main()
