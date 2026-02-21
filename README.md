# Single Agent Self-Crawling

基于 LLM 的自主爬虫 Agent，使用 Docker 沙箱安全执行生成的爬虫代码。

## 特性

- **Sense → Plan → Act → Verify** 完整状态机
- **Docker 沙箱执行** - 隔离环境，安全运行生成代码
- **智能代码生成** - 基于真实 HTML 生成爬虫代码
- **自动错误修复** - SOOAL 循环处理常见错误
- **多网站适配** - 自动适应不同网站结构

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

创建 `.env` 文件：
```
ZHIPU_API_KEY=your_api_key_here
```

获取 API Key: https://open.bigmodel.cn/usercenter/proj-mgmt/apikeys

### 3. 构建 Docker 镜像

```bash
docker build -t crawler-sandbox -f docker/sandbox.Dockerfile .
```

### 4. 运行测试

```bash
python -m tests.test_single_agent
```

## 项目结构

```
src/agent/
├── __init__.py          # SiteAgent 入口
├── graph.py             # LangGraph 状态机
├── state.py             # 状态定义
├── llm/
│   ├── __init__.py
│   └── client.py        # 智谱 API 客户端
├── prompts/
│   └── __init__.py      # Prompt 模板
├── sandbox.py           # Docker/Simple 沙箱
└── tools/
    └── browser.py       # Playwright 浏览器工具
```

## 测试用例

| # | 网站 | 类型 | 目标 |
|---|------|------|------|
| 1 | AoPS | 教育 | 数学题库 |
| 2 | TechCrunch | 新闻 | 科技新闻 |
| 3 | Dribbble | 设计 | UI/UX 作品 |
| 4 | arXiv | 学术 | AI 论文 |
| 5 | Wikipedia | 百科 | 人物传记 |
| 6 | LeetCode | 教育 | 编程题库 |
| 7 | Bloomberg | 财经 | 股票数据 |
| 8 | Unsplash | 媒体 | 摄影图片 |
| 9 | PubMed | 医学 | 医学论文 |
| 10 | IMDB | 娱乐 | 电影信息 |

## Docker 沙箱

使用预构建的 `crawler-sandbox` 镜像，包含：
- Python 3.10
- Playwright + Chromium
- BeautifulSoup4, lxml, httpx

## License

MIT
