import redis.asyncio as aioredis


class RedisClient:
    def __init__(self, url: str = "redis://localhost", decode_responses: bool = True):
        """
        初始化 Redis 客户端
        """
        self._redis = aioredis.from_url(url, decode_responses=decode_responses)

    async def get_start_page(self, post_id: str) -> int:
        """
        获取某个 post_id 下一次应该从第几页开始爬取
        - 如果有记录 n，则返回 n（因为第 n 页可能更新）
        - 如果没有记录，则返回 1
        """
        last_page = await self._redis.get(f"post:{post_id}:last_page")
        if last_page is None:
            return 1
        return int(last_page)

    async def update_last_page(self, post_id: str, page: int) -> None:
        """
        更新某个 post_id 已爬取的最大页数
        """
        await self._redis.set(f"post:{post_id}:last_page", page)

    async def check_connection(self) -> bool:
        """
        检查 Redis 连接是否成功
        """
        try:
            await self._redis.ping()
            return True
        except Exception:
            return False

    async def close(self):
        """
        关闭 Redis 连接
        """
        await self._redis.close()


# 全局实例
redis_client: RedisClient | None = None


def init_redis(url: str):
    global redis_client
    redis_client = RedisClient(url)
    return redis_client
