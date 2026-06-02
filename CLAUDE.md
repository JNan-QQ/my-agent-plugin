# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI 驱动的测试工作流技能集合，作为 Claude Code 插件运行。通过 git submodule 管理各个独立技能模块。

## Repository Structure

- `test-team/` — 测试团队技能（submodule），6 阶段质量门控流水线
- `init-playwright-test/` — Playwright Python + pytest 测试框架初始化技能（submodule）
- `dify-workflow-check/` — Dify 工作流 yml 静态校验与 AI 修复技能（submodule）

## Submodule Commands

```bash
# 初始化并拉取所有子模块
git submodule update --init --recursive

# 更新子模块到远程最新（各子模块默认分支不同，需逐个拉取）
git -C test-team pull origin master
git -C init-playwright-test pull origin master
git -C dify-workflow-check pull origin master
```

## Environment Notes

- Windows 11 环境，使用 `python`（非 `python3`）
- 注意中文路径编码，读取 XLSX 使用 openpyxl
- 测试用例用 JSON 作中间格式（便于分批读取），评审通过后转 XLSX

---

## test-team 技能

6 阶段流水线：需求分析 → 需求评审 → 用例编写 → 用例评审 → 执行记录 → 测试报告。评审阶段（2、4）有封驳机制，不通过必须回退修改。

关键入口：`test-team/SKILL.md`（阶段路由逻辑），各阶段指令在 `test-team/references/1-6-*.md`。

### Python 工具脚本

```bash
python test-team/scripts/case_json_manager.py create --output cases.json --data input.json
python test-team/scripts/case_json_manager.py read --file cases.json --start 0 --end 20
python test-team/scripts/xlsx_writer.py create --output output.xlsx --data data.json
python test-team/scripts/xlsx_analyzer.py --file cases.xlsx --reqs F001-F054
```

### 编号规范

需求 F001-F999、风险 R001-R999、用例 TC001-TC999、缺陷 BUG-YYYYMMDD-001。所有输出文件名含时间戳 `*-YYYYMMDD-HHMM.*`。

---

## init-playwright-test 技能

在目标项目中初始化 Playwright Python + pytest 自动化测试框架。包含三个 AI agent（Planner 规划、Generator 生成、Healer 修复）和辅助脚本。

关键入口：`init-playwright-test/SKILL.md`。

### 前置条件

- Python 3.11+
- Playwright MCP 服务器已配置

### 初始化后产物

```
.claude/agents/playwright-test-planner.md   (测试规划 agent)
.claude/agents/playwright-test-generator.md  (代码生成 agent)
.claude/agents/playwright-test-healer.md     (测试修复 agent)
tools/test_runner.py                         (测试执行工具)
tools/plan_renderer.py                       (计划渲染工具)
tests/conftest.py                            (pytest 配置)
pytest.ini                                   (pytest 全局配置)
```

### 关键设计决策

- 使用 `pytest-json-report` 获取测试结果，不依赖文本正则匹配
- 历史记录存储在 `.test_history/`（独立于 `report/`，避免被清理）
- 测试使用同步 API（`playwright.sync_api`），不用异步
- 依赖版本设置 `<X.0.0` 上界

---

## dify-workflow-check 技能

对 Dify 平台导出的工作流 yml 文件执行：静态校验 → AI 智能分析 → 自动修复 → 生成报告。

关键入口：`dify-workflow-check/SKILL.md`。

### 统一脚本入口

```bash
SKILL_DIR="dify-workflow-check"
RUN="python $SKILL_DIR/scripts/run.py"

# 静态分析
$RUN analyze <yml_file>

# 查询节点（避免直接读取大文件）
$RUN query <analysis.json> list_by_type code|llm
$RUN query <analysis.json> get_code|get_inputs|get_outputs|get_prompt <node_id>

# 修复流程
$RUN init_fixes <fixes.json>
$RUN append_fixes <fixes.json> <new_fixes> <source>
$RUN validate_fixes <fixes.json>
$RUN heal <yml> <fixes.json> <output.yml>
$RUN report <analysis.json> <fixes.json> <out_dir>
```

### 6 阶段流程

1. **静态分析** — `analyze` 输出 analysis.json（nodeMap、graphList、issues）
2. **简单修复** — output_key_mismatch / llm_model_incorrect / syntax_error 直接修复
3. **Code 节点规范修复** — 分批子智能体（sonnet）检查 6 条确定性规则
4. **Code 节点深度逻辑审查** — opus 模型审查复杂逻辑问题
5. **LLM 节点审查** — opus 模型审查提示词和模型配置
6. **应用修复 + 报告** — `heal` 生成 new.yml，`report` 生成报告
7. **测试值推导**（可选）— 为 start 节点生成覆盖关键分支的测试输入

### 关键设计决策

- `analysis.json` 通常 > 500KB，必须通过 `query` 命令按需获取，不可直接读取
- `fixes.json` 通过 `append_fixes` 原子写入，支持多子智能体并发安全
- Phase 2b 用 sonnet（模式匹配），Phase 3/4 用 opus（深度推理）
- `heal` 只修改有问题的字段，不全量重写 yml
