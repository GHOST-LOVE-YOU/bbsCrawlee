from crawlee.crawlers import PlaywrightCrawlingContext
from crawlee.router import Router
router = Router[PlaywrightCrawlingContext]()


# @router.default_handler
# async def default_handler(context: PlaywrightCrawlingContext) -> None:
#     """Default request handler."""
#     context.log.info(f"Processing {context.request.url} ...")
#     title = await context.page.query_selector("title")
#     await context.push_data(
#         {
#             "url": context.request.loaded_url,
#             "title": await title.inner_text() if title else None,
#         }
#     )

#     await context.enqueue_links()


# Basic request handling logic
@router.default_handler
async def basic_handler(context: PlaywrightCrawlingContext) -> None:
    context.log.info(f"Processing {context.request.url}")


# Handler for session initialization (authentication, initial cookies, etc.)
@router.handler(label="session_init")
async def session_init(context: PlaywrightCrawlingContext) -> None:
    if context.session:
        context.log.info(f"Init session {context.session.id}")


