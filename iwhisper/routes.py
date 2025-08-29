from crawlee.crawlers import PlaywrightCrawlingContext
from crawlee.router import Router

from iwhisper.lib.auth import hander_auth

router = Router[PlaywrightCrawlingContext]()


# 基础请求处理逻辑
@router.default_handler
async def basic_handler(context: PlaywrightCrawlingContext) -> None:
    await hander_auth(context)
