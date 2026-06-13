# CLAUDE.md

本文件为 Claude Code 提供此代码库的工作指导。

## 项目概述

Playwright Python + pytest 自动化测试项目，包含三个专用 AI agent：
- **Planner**：探索 Web 应用并生成测试计划
- **Generator**：根据测试计划生成 Python pytest 测试代码
- **Healer**：调试和修复失败的测试

## 常用命令

```bash
# 激活虚拟环境（每次开发前）
source .venv/Scripts/activate    # Windows: .venv\Scripts\Activate.ps1

# 运行测试（--base-url 指定目标应用地址）
python -m pytest tests/ -v --base-url http://your-app.com
python tools/test_runner.py run --output json

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
python -m playwright install chromium

# 渲染测试计划
python tools/plan_renderer.py specs/<topic>/<topic>.json
```

## Agent 使用指南

### Planner Agent（绿色）
```bash
@playwright-test-planner <URL>
```
输出：`specs/<topic>/<topic>.json` + `specs/<topic>/<topic>.md`

### Generator Agent（蓝色）
```bash
@playwright-test-generator
```
输出：`tests/<module>/test_*.py`

### Healer Agent（红色）
```bash
@playwright-test-healer
```
自动修复失败的测试

## 编码规范

### Playwright 最佳实践

```python
# ✅ 正确
from playwright.sync_api import Page, expect

def test_example(page: Page):
    page.goto("https://example.com")
    page.locator("#username").fill("testuser")
    expect(page.locator("#message")).to_be_visible()
    expect(page).to_have_url(re.compile(r".*/dashboard"))

# ❌ 错误
def test_bad(page: Page):
    page.goto(url, wait_until="networkidle")  # 已弃用
    page.wait_for_timeout(1000)  # 脆弱
    assert page.locator("#message").is_visible()  # 不自动等待
```

### 测试文件组织

- 按功能模块组织：`tests/<module>/test_*.py`
- 每个模块目录必须有 `__init__.py`
- 使用 `page: Page` fixture（pytest-playwright 提供）
- 使用 `expect()` 断言，不使用 `assert`

## 环境变量

```bash
TEST_USER=testuser
TEST_PASSWORD=password123
```

> `base_url` 通过 pytest-playwright 的 `--base-url` 参数传入，不使用环境变量。详见 `.env.example`。

## Windows 环境注意事项

- 激活 venv 后直接使用 `python`（激活: `source .venv/Scripts/activate` 或 `.venv\Scripts\Activate.ps1`）
- 所有文件操作使用 `encoding="utf-8"`
- 使用 `pathlib.Path` 处理路径
