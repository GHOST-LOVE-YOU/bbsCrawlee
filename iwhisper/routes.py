from crawlee.crawlers import PlaywrightCrawlingContext
from crawlee.router import Router

from iwhisper.lib.auth import hander_auth
from iwhisper.lib.posts import addPostsToQueue, extract_post_content
from iwhisper.lib.utils import check_and_wait_page, enqueue_next_page

router = Router[PlaywrightCrawlingContext]()


# 基础请求处理逻辑
@router.default_handler
async def basic_handler(context: PlaywrightCrawlingContext) -> None:
    await hander_auth(context)

    context.log.info(
        f"basic_handler: {context.request.url}, label: {context.request.label}"
    )

    if not await check_and_wait_page(context, ".board-list"):
        return

    # 提取帖子链接并加入队列
    if await addPostsToQueue(context) and False:
        # 翻页：通过 DOM 定位找到“下一页”链接并加入队列
        await enqueue_next_page(context)


@router.handler(label="detail")
async def detail_handler(context: PlaywrightCrawlingContext) -> None:
    if not await check_and_wait_page(context, ".a-content-wrap"):
        return

    # 从 DOM 中提取帖子内容
    content = await extract_post_content(context)
    context.log.info(f"提取结果: {content}")

    await enqueue_next_page(context, label="detail")
