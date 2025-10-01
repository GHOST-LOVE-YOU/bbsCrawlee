from __future__ import annotations

import asyncio
from uuid import uuid4

import crawlee
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import HTMLResponse

from .crawler import lifespan

app = FastAPI(lifespan=lifespan, title="Crawler app")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """
<!DOCTYPE html>
<html>
<body>
    <h1>Scraper server</h1>
        <p>To scrape some page, visit "scrape" endpoint with url parameter.
            For example:
            <a href="/scrape?url=https://www.example.com">
                /scrape?url=https://www.example.com
            </a>
        </p>
</body>
</html>
"""


@app.get("/scrape")
async def scrape_url(request: Request, url: str | None = None) -> dict:
    if not url:
        return {"url": "missing", "scrape result": "no results"}

    print(url)

    # 为每个请求创建一个唯一的标识符和一个 Future 对象
    unique_key = str(uuid4())

    # 将结果的 future 对象存入结果字典，以便后续等待
    # request.state.requests_to_results[unique_key] = asyncio.Future[dict[str, str]]()
    # 不需要Future, 定义一个数组可以在await context.push_data(content)后存储多个content就行
    request.state.requests_to_results[unique_key] = []

    # 将请求加入爬虫队列
    await request.state.crawler.add_requests(
        [crawlee.Request.from_url(url, unique_key=unique_key)]
    )

    # 等待爬虫处理完成
    while not await request.state.crawler._request_manager.is_finished():
        await asyncio.sleep(0.5)  # 间隔一会再检查

    # 获取结果
    result = await request.state.crawler.get_data()

    # Clean the result from the result dictionary to free up memory
    request.state.requests_to_results.pop(unique_key, None)

    # Return the result
    return {"items": result.items}
