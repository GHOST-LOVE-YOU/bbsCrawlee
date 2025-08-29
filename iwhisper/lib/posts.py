from crawlee import Request
from crawlee.crawlers import PlaywrightCrawlingContext

from iwhisper.lib.time import is_near_now


async def addPostsToQueue(context: PlaywrightCrawlingContext) -> bool:
    page = context.page
    if page is None:
        return False

    # 提取非置顶（不含 .top）行的主题链接与最新回复时间（Python locator API）
    row_locator = page.locator(".board-list tbody tr:not(.top)")
    rows_count = await row_locator.count()
    for i in range(rows_count):
        row = row_locator.nth(i)

        # 主题链接
        href = ""
        link = row.locator("td.title_9 a").first
        if await link.count() > 0:
            href = await link.get_attribute("href") or ""

        # 最新回复时间优先从具名 a[title="跳转至最后回复"] 读取
        latest_text = ""
        latest_anchor = row.locator('td.title_10 a[title="跳转至最后回复"]').first
        if await latest_anchor.count() > 0:
            latest_text = (await latest_anchor.text_content() or "").strip()
        else:
            # 兼容：若没有具名 a，则尝试第二个 td.title_10 的文本或其中的 a 文本
            time_cells = row.locator("td.title_10")
            if await time_cells.count() >= 2:
                second_cell = time_cells.nth(1)
                a_in_cell = second_cell.locator("a").first
                if await a_in_cell.count() > 0:
                    latest_text = (await a_in_cell.text_content() or "").strip()
                else:
                    latest_text = (await second_cell.text_content() or "").strip()

        if is_near_now(latest_text):
            context.log.info(f"post: href={href} latest={latest_text}")
            absolute_url = f"https://bbs.byr.cn{href}"
            req = Request.from_url(absolute_url, label="detail")
            await context.add_requests([req])
        else:
            context.log.info(f"post: href={href} latest={latest_text} is not near now")
            return False

    return True
