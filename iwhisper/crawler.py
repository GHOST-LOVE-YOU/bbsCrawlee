import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, TypedDict
from uuid import uuid4

from camoufox import AsyncNewBrowser
from crawlee import ConcurrencySettings
from crawlee._utils.context import ensure_context
from crawlee.browsers import (
    BrowserPool,
    PlaywrightBrowserController,
    PlaywrightBrowserPlugin,
)
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext
from crawlee.errors import SessionError
from crawlee.sessions import SessionPool
from dotenv import load_dotenv
from fastapi import FastAPI
from typing_extensions import override

from iwhisper.lib.auth import create_session_fn
from iwhisper.lib.redis import RedisClient
from iwhisper.lib.utils import get_env

from .routes import router


class State(TypedDict):
    """应用中可用的状态"""

    crawler: PlaywrightCrawler
    requests_to_results: dict[str, asyncio.Future[dict[str, Any]]]


class CamoufoxPlugin(PlaywrightBrowserPlugin):
    """使用 Camoufox 浏览器，但保持 PlaywrightBrowserPlugin 的功能"""

    @ensure_context
    @override
    async def new_browser(self) -> PlaywrightBrowserController:
        if not self._playwright:
            raise RuntimeError("Playwright 浏览器插件未初始化。")

        return PlaywrightBrowserController(
            browser=await AsyncNewBrowser(
                self._playwright,
                headless=True,
            ),
            max_open_pages_per_browser=10,
            header_generator=None,
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[State]:
    # 加载虚拟环境
    load_dotenv()

    # 初始化redis
    global redis_client
    redis_client = RedisClient(url=get_env("REDIS_URL", "redis://localhost"))
    if not await redis_client.check_connection():
        raise ConnectionError("无法连接到 Redis，请检查 REDIS_URL 配置。")

    # 请求的唯一标识符映射到其结果的 Future 对象
    requests_to_results = {}
    unique_key = str(uuid4())

    crawler = PlaywrightCrawler(
        keep_alive=True,
        max_requests_per_crawl=int(get_env("MAX_REQUESTS_PER_CRAWL", "10")),
        request_handler=router,
        browser_pool=BrowserPool(plugins=[CamoufoxPlugin()]),
        concurrency_settings=ConcurrencySettings(max_tasks_per_minute=30),
        max_session_rotations=0,
        session_pool=SessionPool(
            max_pool_size=1,
            create_session_function=create_session_fn(),  # 固定 id 的会话
            persistence_enabled=True,  # 开启持久化
            persist_state_kvs_name="auth-sessions",  # 命名的 KeyValueStore
        ),
    )

    # 如果会话被阻塞，则停止爬虫
    @crawler.error_handler
    async def error_processing(
        context: PlaywrightCrawlingContext, error: Exception
    ) -> None:
        if isinstance(error, SessionError) and context.session:
            context.log.info(f"会话 {context.session.id} 被阻塞")
            crawler.stop()

    # 开始爬虫, 并在后台运行
    crawler.log.info(f"开始{app.title} 的爬虫")
    run_task = asyncio.create_task(crawler.run([]))

    # 使用中间件将状态传递给每个请求
    yield {"crawler": crawler}

    # 关闭爬虫
    crawler.stop()
    await run_task

    # 关闭redis连接
    if redis_client:
        await redis_client.close()
