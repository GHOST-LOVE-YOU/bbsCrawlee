from datetime import timedelta

from camoufox import AsyncNewBrowser
from crawlee import ConcurrencySettings, Request
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

from .routes import router


class CamoufoxPlugin(PlaywrightBrowserPlugin):
    """Example browser plugin that uses Camoufox Browser, but otherwise keeps the functionality of
    PlaywrightBrowserPlugin."""

    @ensure_context
    @override
    async def new_browser(self) -> PlaywrightBrowserController:
        if not self._playwright:
            raise RuntimeError("Playwright browser plugin is not initialized.")

        return PlaywrightBrowserController(
            browser=await AsyncNewBrowser(self._playwright, headless=True),
            max_open_pages_per_browser=10,  #  Increase, if camoufox can handle it in your usecase.
            header_generator=None,  #  This turns off the crawlee header_generation. Camoufox has its own.
        )


async def main() -> None:
    """The crawler entry point."""
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=10,
        request_handler=router,
        browser_pool=BrowserPool(plugins=[CamoufoxPlugin()]),
        # Limit requests per minute to reduce the chance of being blocked
        concurrency_settings=ConcurrencySettings(max_tasks_per_minute=50),
        # Disable session rotation
        max_session_rotations=0,
        session_pool=SessionPool(
            # Only one session in the pool
            max_pool_size=1,
            create_session_settings={
                # High value for session usage limit
                "max_usage_count": 999_999,
                # High value for session lifetime
                "max_age": timedelta(hours=999_999),
                # High score allows the session to encounter more errors
                # before crawlee decides the session is blocked
                # Make sure you know how to handle these errors
                "max_error_score": 10,
                # 403 status usually indicates you're already blocked
                "blocked_status_codes": [403],
            },
        ),
    )

    # Monitor if our session gets blocked and explicitly stop the crawler
    @crawler.error_handler
    async def error_processing(
        context: PlaywrightCrawlingContext, error: Exception
    ) -> None:
        if isinstance(error, SessionError) and context.session:
            context.log.info(f"Session {context.session.id} blocked")
            crawler.stop()

    await crawler.run(
        [Request.from_url("https://bbs.byr.cn/#!board/IWhisper", label="session_init")]
    )
