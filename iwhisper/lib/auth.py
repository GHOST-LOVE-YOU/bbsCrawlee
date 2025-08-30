import os
from datetime import timedelta

from crawlee.crawlers import PlaywrightCrawlingContext
from crawlee.sessions import Session

from iwhisper.lib.utils import get_env

SESSION_ID = "Spark65"


def create_session_fn():
    """返回带固定 ID 的 Session，用于跨运行复用。"""

    def make() -> Session:
        return Session(
            id=SESSION_ID,
            max_usage_count=999_999,
            max_age=timedelta(hours=999_999),
            max_error_score=5,
            blocked_status_codes=[403],
        )

    return make


# 会话与登录辅助函数
async def is_unauthenticated(context: PlaywrightCrawlingContext) -> bool:
    """判断当前页面是否为未登录态。

    通过以下方式综合判断：
    - 侧边栏是否存在登录表单 `#u_login_form`
    - 错误区域是否出现“未登录”的提示文案
    """
    page = context.page
    if page is None:
        return True

    if await page.query_selector("#u_login_form") is not None:
        return True

    try:
        error_texts = await page.eval_on_selector_all(
            ".b-content .error li",
            "els => els.map(e => (e.textContent || '').trim())",
        )
        if any("未登录" in (t or "") for t in (error_texts or [])):
            return True
    except Exception:
        # 忽略无法选择到元素的错误
        pass

    return False


async def login_with_form(context: PlaywrightCrawlingContext) -> None:
    """在未登录时使用侧边栏登录表单完成登录。"""
    username = get_env("BBS_USERNAME")
    password = get_env("BBS_PASSWORD")

    page = context.page
    if page is None:
        raise RuntimeError("没有可用的 Playwright 页面实例")

    await page.fill("#u_login_id", username)
    await page.fill("#u_login_passwd", password)
    await page.click("#u_login_submit")

    # 等待网络空闲与登录表单消失，作为登录成功信号
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass

    try:
        await page.wait_for_selector("#u_login_form", state="detached", timeout=10000)
    except Exception:
        # 若表单仍在，重新判断一次登录态，失败则抛错
        if await is_unauthenticated(context):
            raise RuntimeError("登录失败")


async def hander_auth(context: PlaywrightCrawlingContext) -> None:
    if await is_unauthenticated(context):
        context.log.info("检测到未登录态，尝试登录")
        await login_with_form(context)
        context.log.info("登录完成")

