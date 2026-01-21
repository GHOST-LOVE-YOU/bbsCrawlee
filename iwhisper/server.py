from __future__ import annotations

import asyncio
from uuid import uuid4

import crawlee
from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.requests import Request
from starlette.responses import HTMLResponse

from iwhisper.lib.utils import get_env

from .crawler import lifespan

load_dotenv()

app = FastAPI(lifespan=lifespan, title="Crawler app")
security = HTTPBasic()

is_crawling = False  # 全局运行标志
lock = asyncio.Lock()  # 防止并发修改标志

USERNAME = get_env("AUTH_USERNAME")
PASSWORD = get_env("AUTH_PASSWORD")


def check_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != USERNAME or credentials.password != PASSWORD:
        raise JSONResponse(status_code=401, content={"error": "Unauthorized"})
    return credentials.username


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
async def scrape_url(
    request: Request,
    url: str | None = None,
    time_threshold: int | None = None,
    _user: str = Depends(check_credentials),
) -> dict:
    # 防止并发运行
    global is_crawling
    async with lock:
        if is_crawling:
            return {"error": "爬虫正在运行，请稍后再试"}
        is_crawling = True

    try:
        if not url:
            return {"url": "missing", "scrape result": "no results"}

        # 准备 user_data,如果指定了 time_threshold 则包含它
        user_data = {}
        if time_threshold is not None:
            user_data["threshold"] = time_threshold

        # 将请求加入爬虫队列
        await request.state.crawler.add_requests(
            [crawlee.Request.from_url(url, unique_key=str(uuid4()), user_data=user_data)]
        )

        # 等待爬虫处理完成
        while not await request.state.crawler._request_manager.is_finished():
            await asyncio.sleep(0.5)

        # 返回结果
        result = await request.state.crawler.get_data()
        return {"items": result.items}
    finally:
        async with lock:
            is_crawling = False


@app.post("/scrape/post")
async def scrape_post(
    request: Request, url: str | None = None, _user: str = Depends(check_credentials)
) -> dict:
    """
    爬取单个帖子的所有分页内容
    接受POST请求,参数为帖子的URL
    不使用全局锁,不使用Redis检测是否爬过
    """
    if not url:
        return {"error": "url参数缺失"}

    # 将请求加入爬虫队列,使用detail标签直接进入帖子详情处理
    await request.state.crawler.add_requests(
        [crawlee.Request.from_url(url, label="detail", unique_key=str(uuid4()))]
    )

    # 等待爬虫处理完成
    while not await request.state.crawler._request_manager.is_finished():
        await asyncio.sleep(0.5)

    # 返回结果
    result = await request.state.crawler.get_data()
    return {"items": result.items}


