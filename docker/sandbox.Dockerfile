FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

WORKDIR /app

# 安装 Playwright Python 绑定
RUN pip install --no-cache-dir playwright beautifulsoup4 lxml httpx

# 安装 Chromium 浏览器
RUN python -m playwright install --with-deps chromium

CMD ["python"]
