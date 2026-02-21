# Python + Playwright 爬虫沙箱容器
FROM python:3.12-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 安装 Playwright 浏览器依赖
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
RUN pip install --no-cache-dir \
    playwright \
    beautifulsoup4 \
    lxml \
    httpx

# 安装 Playwright 浏览器
RUN playwright install chromium
RUN playwright install-deps chromium

# 创建工作目录
WORKDIR /app

# 默认命令
CMD ["python"]
