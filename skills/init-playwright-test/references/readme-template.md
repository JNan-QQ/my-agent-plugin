# Playwright Python + pytest 自动化测试框架

基于 Python Playwright 和 pytest 的自动化测试框架，包含三个专用 AI agent 用于生成和维护测试代码。

## 快速开始

```bash
# 创建虚拟环境（首次）
python -m venv .venv
source .venv/Scripts/activate    # Windows: .venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt
python -m playwright install chromium

# 运行测试（--base-url 指定目标应用地址）
python -m pytest tests/ -v --base-url http://your-app.com

# 结构化输出
python tools/test_runner.py run --output json
```

## Agent 工作流

在 Claude Code 中使用三个专用 agent：

1. `@playwright-test-planner <URL>` — 探索 Web 应用，生成测试计划 (`specs/<topic>/<topic>.json`)
2. `@playwright-test-generator` — 根据测试计划生成 pytest 测试代码
3. `@playwright-test-healer` — 自动诊断和修复失败的测试

## 项目结构

```
tests/              # 测试文件（按功能模块组织）
specs/              # 测试计划（按主题分目录）
  <topic>/          # 每个测试主题的目录
    <topic>.json    # 结构化测试计划
    <topic>.md      # Markdown 可读文档
tools/              # 辅助脚本（test_runner.py, plan_renderer.py）
report/             # 测试报告、覆盖率、截图（gitignore）
.claude/agents/     # Agent 定义文件
```

## 环境变量

```bash
TEST_USER=testuser               # 测试用户名
TEST_PASSWORD=password123        # 测试密码
```

> `base_url` 通过 `--base-url` 参数传入: `python -m pytest --base-url http://your-app.com`。详见 `.env.example`。

## 测试编写规范

- 使用同步 API: `from playwright.sync_api import Page, expect`
- 使用 `expect()` 断言（自动等待），不使用 `assert`
- 不使用 `wait_for_timeout` 和 `networkidle`
- 详见 [CLAUDE.md](CLAUDE.md)
