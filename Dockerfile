# 使用 Apify Playwright Python 镜像 (Python 3.12)
FROM apify/actor-python-playwright:3.12

# 安装 git（某些包可能需要）
RUN apt update && apt install -yq git && rm -rf /var/lib/apt/lists/*

# 升级 pip & 安装 uv
RUN pip install -U pip setuptools \
    && pip install 'uv<1'

# 设置 uv 项目环境
ENV UV_PROJECT_ENVIRONMENT="/usr/local"

# 先拷贝依赖文件，加快构建
COPY pyproject.toml uv.lock ./

# 安装依赖
RUN echo "Python version:" \
    && python --version \
    && echo "Installing dependencies:" \
    # Check if playwright is already installed
    && PLAYWRIGHT_INSTALLED=$(pip freeze | grep -q playwright && echo "true" || echo "false") \
    && if [ "$PLAYWRIGHT_INSTALLED" = "true" ]; then \
    echo "Playwright already installed, excluding from uv sync" \
    && uv sync --frozen --no-install-project --no-editable -q --no-dev --inexact --no-install-package playwright; \
    else \
    echo "Playwright not found, installing all dependencies" \
    && uv sync --frozen --no-install-project --no-editable -q --no-dev --inexact; \
    fi \
    && echo "All installed Python packages:" \
    && pip freeze

# 再拷贝源代码
COPY . ./

# 预编译检查
RUN python -m compileall -q .

# camoufox 浏览器依赖
RUN python -m camoufox fetch

# 默认命令：用 uv 启动 FastAPI 开发服务器
CMD ["uv", "run", "fastapi", "dev", "iwhisper/server.py"]
