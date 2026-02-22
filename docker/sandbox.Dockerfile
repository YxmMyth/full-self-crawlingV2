FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

WORKDIR /app

# 安装 Playwright Python 绑定
RUN pip install --no-cache-dir playwright beautifulsoup4 lxml httpx

# 安装 Chromium 浏览器
RUN python -m playwright install --with-deps chromium

# ============================================================================
# 深度验证依赖（图片、PDF、视频验证）
# ============================================================================

# 图片处理 - PIL/Pillow
RUN pip install --no-cache-dir Pillow

# PDF 处理 - PyPDF2, pdfplumber
RUN pip install --no-cache-dir PyPDF2 pdfplumber

# 网络请求（用于下载图片/PDF）
RUN pip install --no-cache-dir requests

# SVG 渲染验证 - cairosvg
# 用于 SVG 可渲染性测试
RUN apt-get update && apt-get install -y libcairo2-dev libpango1.0-dev && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir cairosvg

# CLIP 模型（可选，图文匹配）
# 注意：CLIP 模型较大（~500MB），首次运行时会下载
# 如果不需要 CLIP 验证，可以注释掉下面这行
# RUN pip install --no-cache-dir git+https://github.com/openai/CLIP.git
# 或者使用更轻量的 sentence-transformers
# RUN pip install --no-cache-dir sentence-transformers

# 图片风格分析（可选）
# RUN pip install --no-cache-dir scikit-image

# 视频处理（可选，需要 ffmpeg）
# RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
# RUN pip install --no-cache-dir ffmpeg-python

CMD ["python"]
