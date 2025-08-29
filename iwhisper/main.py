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
from typing_extensions import override

from iwhisper.lib.auth import create_session_fn

from .routes import router


class CamoufoxPlugin(PlaywrightBrowserPlugin):
    """使用 Camoufox 浏览器，但保持 PlaywrightBrowserPlugin 的功能"""

    @ensure_context
    @override
    async def new_browser(self) -> PlaywrightBrowserController:
        if not self._playwright:
            raise RuntimeError("Playwright browser plugin is not initialized.")

        return PlaywrightBrowserController(
            browser=await AsyncNewBrowser(
                self._playwright,
                headless=True,
            ),
            max_open_pages_per_browser=10,
            header_generator=None,
        )


async def main() -> None:
    """爬虫入口"""
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=100,
        request_handler=router,
        browser_pool=BrowserPool(plugins=[CamoufoxPlugin()]),
        concurrency_settings=ConcurrencySettings(max_tasks_per_minute=50),
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

    await crawler.run(["https://bbs.byr.cn/#!board/IWhisper"])
