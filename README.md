# iwhisper

基于 Crawlee (Playwright-camoufox) 的北邮人论坛爬虫,支持爬取板块帖子列表和单个帖子详情。

## 功能特性

- 爬取板块帖子列表,支持时间阈值过滤
- 爬取单个帖子详情,自动处理分页
- Redis 断点续爬支持
- 灵活的时间阈值配置
- 并发安全的 API 接口

## 快速开始

### 前置要求

确保已安装 [UV](https://docs.astral.sh/uv/) 包管理工具:

```sh
pipx install uv
```

### 安装依赖

```sh
uv sync
```

### 配置环境变量

复制 `.env.example` 为 `.env` 并配置:

### 启动服务

```sh
uv run python -m iwhisper
```

服务将在 `http://localhost:8000` 启动。

## API 后端

### 1. GET `/scrape` - 爬取板块帖子列表

爬取指定板块的帖子列表,根据时间阈值筛选最近更新的帖子。

**参数:**
- `url` (必需): 板块 URL,例如 `https://bbs.byr.cn/board/某板块?p=1`
- `time_threshold` (可选): 时间阈值(秒),用于判断帖子是否需要爬取
  - 默认值: 从环境变量 `TIME_THRESHOLD` 读取(默认 -1,表示爬取所有帖子)
  - 悄悄话板块建议: `2000` (30分钟更新一次)
  - 其他板块建议: `3024000` (35天更新一次,约每月)

**示例:**

```bash
# 使用默认时间阈值
curl "http://localhost:8000/scrape?url=https://bbs.byr.cn/board/某板块?p=1" \
  -u "username:password"

# 悄悄话板块 - 30分钟更新一次
curl "http://localhost:8000/scrape?url=https://bbs.byr.cn/board/悄悄话?p=1&time_threshold=2000" \
  -u "username:password"

# 其他板块 - 每月更新一次
curl "http://localhost:8000/scrape?url=https://bbs.byr.cn/board/某板块&p=1&time_threshold=3024000" \
  -u "username:password"
```

**特性:**
- 使用全局锁,防止并发运行
- 根据 Redis 记录的起始页进行断点续爬
- 自动处理分页,爬取所有符合条件的帖子
- 返回格式: `{"items": [...]}`

---

### 2. POST `/scrape/post` - 爬取单个帖子详情

爬取指定帖子的所有分页内容,包括所有评论。

**参数:**
- `url` (必需): 帖子 URL,例如 `https://bbs.byr.cn/article/某板块/帖子ID`

**示例:**

```bash
curl -X POST "http://localhost:8000/scrape/post?url=https://bbs.byr.cn/article/某板块/12345" \
  -u "username:password"
```

**特性:**
- 不使用全局锁,允许多个请求并发执行
- 不使用 Redis 检测是否爬过,每次都重新爬取
- 自动处理帖子内的所有分页
- 返回格式: `{"items": [...]}`,每个 item 包含:
  - `byr_id`: 帖子 ID
  - `area`: 板块名称
  - `topic`: 主题
  - `author`: 作者
  - `time`: 发帖时间
  - `page`: 页码
  - `comments`: 评论列表
