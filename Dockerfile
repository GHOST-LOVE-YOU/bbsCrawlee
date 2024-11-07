# 使用 ubuntu:24.10 作为基础镜像
FROM ubuntu:24.10 AS builder

# 更新包管理器并安装基本依赖项
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 安装 Node.js 20.x
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# 安装 Playwright 浏览器依赖
RUN npx playwright install-deps

# 设置工作目录
WORKDIR /app

# 复制 package.json 和 package-lock.json 以利用 Docker 缓存层加速构建
COPY package*.json ./

# 安装所有开发依赖项
RUN npm install --include=dev --audit=false

# 安装 Playwright 浏览器
RUN npx playwright install

# 复制源代码并进行项目构建
COPY . ./
RUN npm run build --output-path=/app/dist

# 使用更小的基础镜像创建最终镜像
FROM ubuntu:24.10

# 安装 Node.js 运行时
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    libglib2.0-0t64\
    libnss3\
    libnspr4\
    libdbus-1-3\
    libatk1.0-0t64\
    libatk-bridge2.0-0t64\
    libcups2t64\
    libdrm2\
    libxcb1\
    libxkbcommon0\
    libatspi2.0-0t64\
    libx11-6\
    libxcomposite1\
    libxdamage1\
    libxext6\
    libxfixes3\
    libxrandr2\
    libgbm1\
    libpango-1.0-0\
    libcairo2\
    libasound2t64\
    libxcursor1\
    libgtk-3-0t64\
    libpangocairo-1.0-0\
    libcairo-gobject2\
    libgdk-pixbuf-2.0-0\
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*


# 设置工作目录
WORKDIR /app

# 从 builder 阶段复制构建好的文件
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package*.json ./

# 安装生产依赖
RUN npm install --omit=dev --omit=optional

RUN npx playwright install

# 启动应用
CMD ["node", "/app/dist/main.js"]
