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
    # 初始化爬虫
    load_dotenv()

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

    # await crawler._request_manager.is_finished()
    # Expose the results store to request handlers
    setattr(crawler, "requests_to_results", requests_to_results)
    setattr(crawler, "unique_key", unique_key)

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

    # Make the crawler and the result dictionary available in the app state
    yield {
        "crawler": crawler,
        "requests_to_results": requests_to_results,
        "unique_key": unique_key,
    }

    # Cleanup code that runs once when the app shuts down
    crawler.stop()
    # Wait for the crawler to finish
    await run_task
