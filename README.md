# Request Routing

## Problem
You are given a list of requests and a set of APIs with different capacities. Similar to the OpenAI API, each API has a limit on the number of requests and tokens it can handle per minute. Your task is to route the requests to the APIs in such a way that all requests are executed in the minimum amount of time.

You will directly interact with the ```Server``` class to route requests.

Here's an example:
```python
request = Request(token_capacity=20)
header = server.receive(route="/ab", request=request)
```
If you exceed the requests limit or if you exceed the tokens limit, you will receive either a ```RequestLimitExceededException``` or ```TokenLimitExceededException```

The request and token capacity will refresh every second. For example, if the API has a limit of 60 requests per second and 360 tokens per minute, it will refresh by 1 request / 60 tokens every second.


## Goal
The goal is to write a clean and extensible solution to the problem. There is no need to focus on algorithmic optimizations. Load in the endpoints and the requests, and then use the ```Server``` class to route the requests.

## Limitations

- You cannot execute more than one request at the same time
- You cannot modify any pre-existing code
- You have to treat the request list as a queue - you may not access information from any request other than the one at the top of the queue.
