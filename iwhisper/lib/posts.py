import re
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from crawlee import Request
from crawlee.crawlers import PlaywrightCrawlingContext
from playwright.sync_api import Locator

from iwhisper.lib.redis_client import get_redis_client
from iwhisper.lib.time import is_near_now
from iwhisper.lib.utils import page_dump

# 正则工具
author_re = re.compile(r"发信人:\s*([^\s(]+)")
time_re = re.compile(r"发信站:\s.*\((.*?)\),")
num_in_paren_re = re.compile(r"[\(（]\+?(\d+)[\)）]")
like_re = re.compile(r"赞\((\d+)\)")
cai_re = re.compile(r"踩\((\d+)\)")
content_re = re.compile(r"<br><br>(.+?)<br>--")


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
            absolute_url = await page_dump(f"https://bbs.byr.cn{href}")
            req = Request.from_url(
                absolute_url, label="detail", unique_key=f"{absolute_url}-{uuid4()}"
            )
            await context.add_requests([req])
        else:
            context.log.info(f"post: href={href} latest={latest_text} is not near now")
            return False

    return True


async def extract_post_content(context: PlaywrightCrawlingContext) -> dict:
    """
    从页面中提取帖子内容
    """
    page = context.page
    if page is None:
        return {}

    # 从 URL 提取 area / byr_id / page
    url = context.request.url
    parsed = urlparse(url)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    area = parts[1] if len(parts) >= 3 and parts[0] == "article" else ""
    byr_id = parts[2] if len(parts) >= 3 else ""
    page_q = parse_qs(parsed.query).get("p", ["1"])  # 若无 ?p=x 则为 1
    page_no = page_q[0]

    # 主题
    topic_text = await extract_topic(page)

    # 提取评论
    comments: list[dict] = []
    post_author: str | None = None
    post_time: str | None = None

    wraps = page.locator(".a-wrap")
    count = await wraps.count()

    for i in range(count):
        wrap = wraps.nth(i)

        # 楼层标识（楼主 / 第x楼 / 沙发 / 板凳）
        floor = await extract_floor_text(wrap)

        # 点赞/点踩
        like, dislike = await extract_like_dislike(wrap)

        # 内容块（排除精彩回复块）
        content, author, time = await extract_content_author_time(wrap)

        # 记录评论
        comments.append(
            {
                "author": author,
                "content": content,
                "floor": floor,
                "like": like,
                "dislike": dislike,
                "time": time,
            }
        )

        # 若是楼主楼层，记录帖子作者与时间
        if floor.startswith("楼主"):
            post_author = author
            post_time = time

    redis_client = get_redis_client()
    await redis_client.update_last_page(byr_id, page_no)

    result = {
        "byr_id": byr_id,
        "area": area,
        "topic": topic_text,
        "author": post_author,
        "time": post_time,
        "page": page_no,
        "comments": comments,
    }

    return result


async def extract_topic(wrap: Locator) -> str:
    topic_text = ""
    try:
        topic_el = wrap.locator("div.b-head.corner span.n-left").first
        if await topic_el.count() > 0:
            raw_topic = await topic_el.text_content() or ""
            topic_text = re.sub(r"^文章主题:\s*", "", raw_topic).strip()
    except Exception:
        topic_text = ""

    return topic_text


async def extract_floor_text(wrap: Locator) -> str:
    floor_text = ""
    try:
        pos = wrap.locator(".a-pos").first
        if await pos.count() > 0:
            floor_text = (await pos.text_content() or "").strip()
    except Exception:
        floor_text = ""

    return floor_text


async def extract_like_dislike(wrap: Locator) -> tuple[int, int]:
    like_val = -1
    dislike_val = -1

    # 普通楼层：赞(x)/踩(y)
    try:
        like_node = wrap.locator("a.a-func-like").first
        if await like_node.count() > 0:
            t = (await like_node.text_content() or "").strip()
            m = like_re.search(t)
            if m:
                like_val = int(m.group(1))
    except Exception:
        pass

    try:
        cai_node = wrap.locator("a.a-func-cai").first
        if await cai_node.count() > 0:
            t = (await cai_node.text_content() or "").strip()
            m = cai_re.search(t)
            if m:
                dislike_val = int(m.group(1))
    except Exception:
        pass

    # 楼主楼层：楼主好评 (+x) / 楼主差评 (+y)
    if like_val == -1 or dislike_val == -1:
        try:
            support_node = wrap.locator("a.a-func-support").first
            if await support_node.count() > 0:
                t = (await support_node.text_content() or "").strip()
                m = num_in_paren_re.search(t)
                if m:
                    like_val = int(m.group(1))
        except Exception:
            pass

        try:
            oppose_node = wrap.locator("a.a-func-oppose").first
            if await oppose_node.count() > 0:
                t = (await oppose_node.text_content() or "").strip()
                m = num_in_paren_re.search(t)
                if m:
                    dislike_val = int(m.group(1))
        except Exception:
            pass

    return like_val, dislike_val


async def extract_content_author_time(wrap: Locator) -> tuple[str, str, str]:
    """
    从页面中提取帖子内容
    """
    content = ""
    author = ""
    time = ""

    try:
        body = wrap.locator("td.a-content .a-content-wrap").first
        if await body.count() == 0:
            body = wrap.locator(".a-content .a-content-wrap").first

        if await body.count() > 0:
            # 先获取innerHTML，然后用正则提取"发信站"后两个<br>到"--"之间的内容
            html_content = await body.evaluate("el => el.innerHTML")
            match = content_re.search(html_content, re.DOTALL)
            content = match.group(1) if match else ""
            content = (content or "").strip()
            # 提取作者和时间信息
            author_match = author_re.search(html_content)
            if author_match:
                author = author_match.group(1).strip()

            time_match = time_re.search(html_content)
            if time_match:
                time = time_match.group(1).strip()
    except Exception:
        content = ""

    return content, author, time
