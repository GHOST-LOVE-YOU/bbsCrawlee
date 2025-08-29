from crawlee.crawlers import PlaywrightCrawlingContext
from crawlee.router import Router

from iwhisper.lib.auth import SESSION_ID, is_unauthenticated, login_with_form

router = Router[PlaywrightCrawlingContext]()


# 基础请求处理逻辑
@router.default_handler
async def basic_handler(context: PlaywrightCrawlingContext) -> None:
    context.log.info(f"Processing {context.request.url}")
    if not context.session or context.session.id != SESSION_ID:
        raise RuntimeError("会话绑定错误")


# 会话初始化处理逻辑 （认证，初始化cookies等）
@router.handler(label="session_init")
async def session_init(context: PlaywrightCrawlingContext) -> None:
    if context.session:
        context.log.info(f"会话 {context.session.id} 初始化")
    # 捕获未登录态并尝试登录
    if await is_unauthenticated(context):
        context.log.info("检测到未登录态，尝试登录")
        await login_with_form(context)
        context.log.info("登录完成")
