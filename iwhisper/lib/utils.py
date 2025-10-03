# 将下一页链接加入队列
import os
import re
from urllib.parse import urljoin
from uuid import uuid4

from crawlee import Request
from crawlee.crawlers import PlaywrightCrawlingContext

from iwhisper.lib.redis_client import get_redis_client


async def enqueue_next_page(
    context: PlaywrightCrawlingContext, label: str | None = None
) -> None:
    page = context.page
    if page is None:
        return

    next_link = page.locator('a[title="下一页"]').first
    try:
        if await next_link.count() > 0:
            next_href = await next_link.get_attribute("href") or ""
            if next_href:
                next_url = urljoin(context.request.url, next_href)
                context.log.info(f"添加下一页链接: {next_url}, label: {label}")
                req = Request.from_url(
                    next_url, label=label, unique_key=f"{next_url}-{uuid4()}"
                )
                await context.add_requests([req])
        else:
            context.log.debug("没有下一页链接; 可能已到最后一页")
    except Exception as e:
        context.log.warning(f"添加下一页链接失败: {e}")


# 页面检查和等待
async def check_and_wait_page(
    context: PlaywrightCrawlingContext, selector: str, timeout: int = 15000
) -> None:
    """
    检查页面是否存在指定选择器，如果存在则等待指定时间
    """
    page = context.page
    if page is None:
        return False

    try:
        await page.wait_for_selector(selector, timeout=timeout)
    except Exception:
        context.log.warning(f"{selector} 未找到; 跳过提取")
        return False
    return True


# 从.env读取环境变量
def get_env(key: str, default: str | None = None) -> str:
    value = os.getenv(key)
    if not value:
        if default is None:
            raise RuntimeError(f"未设置环境变量: {key}")
        value = default
    return value


async def page_dump(absolute_url: str) -> str:
    # 从URL提取post_id
    match = re.search(r"/(\d+)$", absolute_url)
    if not match:
        raise ValueError(f"无法从URL提取post_id: {absolute_url}")
    post_id = match.group(1)

    # 从 Redis 获取起始页
    redis_client = get_redis_client()
    start_page = await redis_client.get_start_page(post_id)

    if start_page > 1:
        url = f"{absolute_url}?p={start_page}"
    else:
        url = absolute_url
    return url
    return url
    return url
