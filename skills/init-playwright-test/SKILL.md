---
name: init-playwright-test
description: 在当前项目中初始化 Playwright Python + pytest 自动化测试框架。触发词：/init-playwright-test、初始化 Playwright、搭建 E2E 测试框架、init playwright test。包含 Planner/Generator/Healer 三个 AI agent、辅助脚本和完整配置。
---

# 初始化 Playwright Python + pytest 测试框架

在当前项目中搭建完整的 Playwright Python + pytest 自动化测试框架。框架包含三个专用 AI agent（Planner 规划测试、Generator 生成代码、Healer 修复失败），以及配套的辅助脚本和配置文件。

## 使用场景

| 场景 | 触发词 | 说明 |
|------|--------|------|
| 新项目搭建 | `/init-playwright-test` | 从零开始搭建测试框架 |
| 已有项目补充 | `初始化 Playwright` | 在已有项目中添加测试能力 |
| 重新初始化 | `重新初始化 Playwright` | 覆盖现有配置（需确认） |

## 前置条件

- Python 3.11+
- Playwright MCP 服务器已配置（`mcp__playwright__browser_*` 工具可用）

## 输入/输出规格

### 输入
- 无强制输入，可选环境变量：`BASE_URL`、`TEST_USER`、`TEST_PASSWORD`
- 已有 `requirements.txt` 时自动合并依赖

### 输出
| 文件/目录 | 说明 |
|-----------|------|
| `.claude/agents/playwright-test-*.md` | 3个AI agent定义 |
| `tools/test_runner.py` | 测试执行工具 |
| `tools/plan_renderer.py` | 计划渲染工具 |
| `tests/conftest.py` | pytest配置 |
| `tests/__init__.py` | 包标识文件 |
| `pytest.ini` | pytest全局配置 |
| `.claude/settings.local.json` | MCP权限配置 |
| `.env.example` | 环境变量模板 |
| `requirements.txt` | 依赖列表 |

## 初始化流程

按以下顺序执行。固定内容的文件直接用 `cp` 复制，只有需要合并已有内容的文件才用 Write/Edit 工具。

**重要**：`SKILL_DIR` 为本技能的 base directory（系统调用时自动提供）。在 Bash 中设置变量：
```bash
SKILL_DIR="<本技能的 base directory>"
```

### Step 1: 环境检查

**输入**：当前工作目录
**输出**：`CLEAN`（可继续）或 `ALREADY_INIT`（需确认覆盖）

```bash
pwd
ls .claude/agents/playwright-test-planner.md 2>/dev/null && echo "ALREADY_INIT" || echo "CLEAN"
```

**失败分支**：
| 触发条件 | 一线修复 | 仍失败兜底 |
|---|---|---|
| 输出 `ALREADY_INIT` | 提示用户"测试框架已初始化，是否覆盖？" | 用户说"不覆盖" → 终止，输出"初始化已取消" |
| `pwd` 报错 | 检查是否在有效目录 | 提示用户 `cd` 到目标项目目录 |

### Step 2: 创建目录并批量复制固定文件

**输入**：`SKILL_DIR`（技能目录路径）
**输出**：创建的目录和文件列表

以下文件内容固定不变，全部用 `cp` 一次性完成，不要用 Read/Write 工具：

```bash
SKILL_DIR="<本技能的 base directory>"

# 创建目录
mkdir -p .claude/agents tests tools specs

# 创建 tests/__init__.py（避免 pytest 同名文件冲突）
touch tests/__init__.py

# 复制 3 个 agent 定义
cp "$SKILL_DIR/references/planner-agent.md"   .claude/agents/playwright-test-planner.md
cp "$SKILL_DIR/references/generator-agent.md"  .claude/agents/playwright-test-generator.md
cp "$SKILL_DIR/references/healer-agent.md"     .claude/agents/playwright-test-healer.md

# 复制 2 个辅助脚本
cp "$SKILL_DIR/references/test_runner.py"      tools/test_runner.py
cp "$SKILL_DIR/references/plan_renderer.py"    tools/plan_renderer.py

# 复制配置文件
cp "$SKILL_DIR/references/pytest.ini"          pytest.ini
cp "$SKILL_DIR/references/conftest.py"         tests/conftest.py

# 复制环境变量模板
cp "$SKILL_DIR/references/.env.example"        .env.example
# 注意：requirements.txt 不在此复制，由 Step 3 处理（存在则合并，不存在则复制）
```

**失败分支**：
| 触发条件 | 一线修复 | 仍失败兜底 |
|---|---|---|
| `mkdir -p` 权限不足 | 提示用户检查目录权限 | 用 `sudo` 或提示用户手动创建 |
| `cp` 源文件不存在 | 检查 `$SKILL_DIR` 路径是否正确 | 提示用户重新安装 skill |
| `cp` 目标目录不存在 | 确保 `mkdir -p` 先执行 | 手动创建目标目录 |

### Step 3: 处理 requirements.txt

**输入**：项目现有 `requirements.txt`（可选）
**输出**：合并后的 `requirements.txt`

根据项目是否已有 `requirements.txt` 执行不同操作：

```bash
SKILL_DIR="<本技能的 base directory>"
```

**情况 A：项目已有 requirements.txt** → 合并缺失依赖

```bash
# 检查每个依赖包名是否已存在（忽略版本号）
# PowerShell: Select-String -Pattern "^playwright" -Path requirements.txt -Quiet
# Bash/Git Bash: grep -q "^playwright" requirements.txt
```

需要检查的 6 个包名：`playwright`、`pytest`、`pytest-playwright`、`pytest-html`、`pytest-cov`、`pytest-json-report`

对于每个缺失的包名，用 Edit 工具追加一行：
```
playwright>=1.58.0,<2.0.0
pytest-playwright>=0.6.0,<1.0.0
pytest-html>=4.1.0,<5.0.0
pytest-cov>=6.0.0,<7.0.0
pytest-json-report>=1.5.0,<2.0.0
```

**示例**：用户已有 `flask==2.0.0` 和 `pytest==7.0.0`，只追加其余 5 个包。

**版本冲突处理**：如果用户已有 `pytest==7.0.0` 但 skill 要求 `>=8.0.0`，提示用户："检测到 pytest 版本为 7.0.0，Playwright 需要 8.0.0+，是否升级？"等待确认后再修改。

**情况 B：项目没有 requirements.txt** → 直接复制

```bash
cp "$SKILL_DIR/references/requirements.txt" requirements.txt
```

**🔴 CHECKPOINT · 依赖确认**

完成后，展示 `requirements.txt` 最终内容给用户确认。如果用户说"不对"，根据情况恢复：
- 情况 A：恢复到合并前的版本（用 Edit 工具删除追加的行）
- 情况 B：删除复制的文件

### Step 4: 复制或合并配置和文档

**输入**：项目现有配置文件（可选）
**输出**：合并后的配置文件

```bash
SKILL_DIR="<本技能的 base directory>"
```

**settings.local.json** — 如果不存在，直接复制；如果已存在，用 Edit 工具合并 permissions.allow 数组：
```bash
[ ! -f .claude/settings.local.json ] && cp "$SKILL_DIR/references/settings.local.json" .claude/settings.local.json
```

**CLAUDE.md** — 如果不存在，直接复制；如果已存在，用 Edit 工具在末尾追加：
```bash
[ ! -f CLAUDE.md ] && cp "$SKILL_DIR/references/claude-md-template.md" CLAUDE.md
```

**README.md** — 如果不存在或为空，直接复制；如果已有内容，用 Edit 工具在末尾追加：
```bash
[ ! -s README.md ] && cp "$SKILL_DIR/references/readme-template.md" README.md
```

### Step 5: 创建或追加 .gitignore

**输入**：项目现有 `.gitignore`（可选）
**输出**：更新后的 `.gitignore`

如果 `.gitignore` 不存在，用 Write 工具创建。如果已存在，检查是否已包含 `report/`，没有则用 Edit 工具追加以下内容：

```
# Python
__pycache__/
*.py[oc]
.venv/

# 测试报告
report/
.pytest_cache/
.test_history/
.coverage

# 自动生成的测试计划文档
specs/*/*.md

# IDE
.vscode/
.idea/
```

**检查方法**：
```bash
# PowerShell: Select-String -Pattern "^report/$" -Path .gitignore -Quiet
# Bash/Git Bash: grep -q "^report/$" .gitignore
```

如果已包含 `report/`，则跳过追加。如果不存在，在文件末尾追加上述内容（保留用户原有内容）。

### Step 6: 创建虚拟环境并安装依赖

**输入**：`requirements.txt`
**输出**：`.venv` 目录，已安装的依赖

```bash
python -m venv .venv
source .venv/Scripts/activate
```

> **激活命令因 Shell 而异：**
> - Git Bash (Windows): `source .venv/Scripts/activate`
> - PowerShell: `.venv\Scripts\Activate.ps1`
> - Unix/Mac: `source .venv/bin/activate`

安装依赖：
```bash
pip install -r requirements.txt
```

验证安装：
```bash
python -c "import pytest; import pytest_playwright; import pytest_jsonreport; print('All dependencies installed')"
```

如果 Playwright 浏览器未安装，运行：
```bash
python -m playwright install chromium
```

**失败分支**：
| 触发条件 | 一线修复 | 仍失败兜底 |
|---|---|---|
| `python -m venv` 失败 | 检查 Python 版本（需 3.11+） | 提示用户安装 Python 3.11+ |
| `pip install` 超时 | 用 `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple` 换源 | 提示用户检查网络连接 |
| `pip install` 版本冲突 | 用 `pip install --force-reinstall` | 提示用户删除 `.venv` 重新创建 |
| `playwright install` 失败 | 用 `playwright install --with-deps chromium` 安装系统依赖 | 提示用户手动安装 Chromium |
| 验证 import 失败 | 检查 `.venv` 是否激活 | 重新执行 `pip install` |

### Step 7: 验证并提示

**输入**：所有已创建的文件
**输出**：验证结果和完成信息

验证所有文件已创建：
```bash
ls .claude/agents/playwright-test-*.md
ls tools/test_runner.py tools/plan_renderer.py
ls tests/conftest.py tests/__init__.py pytest.ini
```

**🔴 CHECKPOINT · 验证结果确认**

如果上述 `ls` 命令有任何文件缺失，立即停止并报告缺失文件，不要继续输出完成信息。

向用户展示完成信息：

```
Playwright Python + pytest 测试框架初始化完成！

已创建：
  .claude/agents/playwright-test-planner.md   (测试规划 agent)
  .claude/agents/playwright-test-generator.md  (代码生成 agent)
  .claude/agents/playwright-test-healer.md     (测试修复 agent)
  tools/test_runner.py                         (测试执行工具)
  tools/plan_renderer.py                       (计划渲染工具)
  tests/conftest.py                            (pytest 配置)
  pytest.ini                                   (pytest 全局配置)
  .claude/settings.local.json                  (MCP 权限配置)
  .env.example                                 (环境变量模板)

下一步：
  1. 生成测试计划:  @playwright-test-planner <URL>
  2. 生成测试代码:  @playwright-test-generator
  3. 运行测试:      python tools/test_runner.py run --output json
  4. 修复失败测试:  @playwright-test-healer

测试计划输出目录:
  specs/<topic>/
    <topic>.json    (结构化测试计划)
    <topic>.md      (Markdown 可读文档)

环境变量（可选）：
  BASE_URL=http://localhost:3000
  TEST_USER=testuser
  TEST_PASSWORD=password123
```

## 关键设计决策

这些决策是经过实际项目验证的，初始化时应遵循：

| 类别 | 决策 | 原因 |
|---|---|---|
| **测试结果** | 用 pytest-json-report，不用文本解析 | JSON 结构化数据可靠，避免正则匹配失败 |
| **截图** | 不自定义 hook，用内置 `--screenshot only-on-failure` | 自定义 hook 会导致双重截图 |
| **历史记录** | 放在 `.test_history/`，不放 `report/` | 避免被 pytest-playwright `--output` 清理 |
| **凭据** | 用环境变量 `BASE_URL`/`TEST_USER`/`TEST_PASSWORD` | 不硬编码，换环境不用改代码 |
| **浏览器模式** | 默认有头模式 | Planner 探索时用户可见；CI 加 `--headless` |
| **模块识别** | Step 2 自动创建 `tests/__init__.py` | 避免 pytest 同名文件冲突 |
| **API 风格** | 只用 `playwright.sync_api`，不用异步 | 与 pytest-playwright 兼容 |
| **版本控制** | 所有依赖 `<X.0.0` 上界 | 防止破坏性变更 |

## 与其他技能的配合

| 技能 | 配合方式 |
|------|----------|
| **test-team** | 使用本技能初始化框架后，用 test-team 的阶段3生成测试用例，阶段5执行测试 |
| **init-playwright-test** | 本技能是起点，初始化后可使用 Planner/Generator/Healer 三个agent |

## 工作流示例

```
1. 初始化框架: /init-playwright-test
2. 生成测试计划: @playwright-test-planner <URL>
3. 生成测试代码: @playwright-test-generator
4. 运行测试: python tools/test_runner.py run --output json
5. 修复失败测试: @playwright-test-healer
```

## 反例与黑名单

初始化过程中的常见错误和禁止操作，违反会导致框架无法正常工作。

### 🚫 禁止操作

| # | 反模式 | 后果 | 正确做法 |
|---|---|---|---|
| 1 | 用 Read/Write 复制固定文件 | 效率低、可能引入编码问题 | 用 `cp` 命令批量复制 |
| 2 | 覆盖已有 requirements.txt | 丢失用户原有依赖 | 用 Edit 工具追加缺失行 |
| 3 | 手动删除 `__init__.py` | pytest 同名文件冲突，测试发现不了 | Step 2 已自动创建 `tests/__init__.py`，勿删 |
| 4 | 使用 `async def test_*` | 与 pytest-playwright 不兼容 | 必须用 `playwright.sync_api` |
| 5 | 使用 `page.wait_for_timeout()` | 测试脆弱、CI 环境不稳定 | 用 `expect()` 自动等待 |
| 6 | 使用 `wait_until="networkidle"` | 页面永不触发 networkidle 导致超时 | 用 `expect(locator)` 等待具体元素 |
| 7 | 硬编码 URL/凭据 | 换环境就失败 | 用环境变量 `BASE_URL`/`TEST_USER` |
| 8 | 自定义 screenshot hook | 与 pytest-playwright 内置功能双重截图 | 用 `--screenshot only-on-failure` |
| 9 | 将历史记录放在 `report/` | 被 pytest-playwright `--output` 清理 | 用 `.test_history/` 独立目录 |
| 10 | 删除用户已有的 `.gitignore` 内容 | 丢失用户原有忽略规则 | 只追加，不删除 |

### ⚠️ 危险信号

遇到以下情况立即停止并询问用户：

- `ALREADY_INIT` 输出但用户说"不覆盖" → 终止初始化
- `pip install` 失败 → 提示用户检查网络或 Python 版本
- `playwright install chromium` 失败 → 提示用户手动安装
- 目标项目有 `tests/` 目录且有内容 → 提示用户确认是否合并
