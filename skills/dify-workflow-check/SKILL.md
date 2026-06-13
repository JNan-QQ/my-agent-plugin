---
name: dify-workflow-check
description: 对 Dify 工作流 yml 文件进行静态校验和 AI 智能分析，自动修复后输出 *-new.yml。当用户提到 dify、工作流、yml检查、workflow、节点校验、dify检查、工作流校验、分析工作流、检查节点 时使用此技能，即使用户没有明确说"检查"也应触发。只要用户给出了 .yml 文件路径并期望某种分析或修复，就应该使用这个技能。
---

# Dify 工作流检查与修复

对 Dify 平台导出的工作流 yml 文件执行完整流程：静态校验 → AI 智能分析 → 自动修复 → 生成报告。

## 路径约定

脚本统一入口（所有命令都通过这个文件调用，因为模块在技能目录内，不在项目 Python path 中）：

```
SKILL_DIR = .claude/skills/dify-workflow-check
RUN = python <SKILL_DIR>/scripts/run.py
```

输出路径（以 `推荐语音包.yml` 为例）：
- `OUT_DIR` = `outputs/推荐语音包/`
- `ANALYSIS` = `outputs/推荐语音包/analysis.json`
- `FIXES` = `outputs/推荐语音包/fixes.json`
- `NEW_YML` = `outputs/推荐语音包/new.yml`

---

## 子智能体通用规范

以下规范适用于所有子智能体 prompt，在各 Phase 的 prompt 中不再重复。

### 查询命令

analysis.json 通常 > 500KB，直接读取会溢出上下文。使用 query 命令只获取需要的部分：

```bash
python {SKILL_DIR}/scripts/run.py query {ANALYSIS} list_by_type <type>   # code / llm
python {SKILL_DIR}/scripts/run.py query {ANALYSIS} get_code <node_id>
python {SKILL_DIR}/scripts/run.py query {ANALYSIS} get_inputs <node_id>
python {SKILL_DIR}/scripts/run.py query {ANALYSIS} get_outputs <node_id>
python {SKILL_DIR}/scripts/run.py query {ANALYSIS} get_node <node_id>
python {SKILL_DIR}/scripts/run.py query {ANALYSIS} get_prompt <node_id>
```

### code_rewrite 输出格式

所有涉及代码修复的子智能体必须使用此格式：

```json
{
  "node_id": "节点ID",
  "fix_type": "code_rewrite",
  "reason": "简短说明修复了什么",
  "fixed_code": "完整的修复后代码（用 \\n 表示换行）"
}
```

**规则**：
1. `fixed_code` 必须是完整的、可直接替换原代码的字符串
2. 使用 `\\n` 表示换行，保持原代码缩进风格
3. 不要只写建议文本，必须输出实际可执行的代码
4. 每个节点只生成一条 code_rewrite（合并多个问题到一次修复）
5. 如果代码超过 100 行，确保 fixed_code 包含完整代码（包括所有辅助函数）

### 写入修复的方式

子智能体不要直接读写 `{FIXES}`。将修复写入独立文件后调用：

```bash
python {SKILL_DIR}/scripts/run.py append_fixes {FIXES} <输出文件> <source标签>
```

append_fixes 用文件锁 + 原子 rename 保证并发安全，按 (node_id, fix_type) 去重，先到先得。

---

## 执行流程

### Phase 1: 静态分析

```bash
python {SKILL_DIR}/scripts/run.py analyze <YML_FILE>
```

输出 `analysis.json`（含 nodeMap、graphList、adjacency、issues）。

向用户汇报（必须包含以下数据）：
```
分析完成：
- 节点总数：N 个（其中 code: X, llm: Y, start: Z, ...）
- 分支数：M 条
- 问题数：error: A / warning: B / info: C
- 已发现可自动修复的问题：D 个
```

**🔴 CHECKPOINT**：向用户展示分析摘要后，等待用户确认继续修复。如果用户说"停止"或"不修复"，结束流程。

### Phase 2a: 简单修复

开始前先用 `python {SKILL_DIR}/scripts/run.py init_fixes {FIXES}` 初始化空骨架。

读取 issues，对以下类型直接生成修复：

| issue type | fix_type | 修复逻辑 |
|-----------|----------|----------|
| `output_key_mismatch` | `output_fix` | 以 return 语句实际 key 为准 |
| `llm_model_incorrect` | `model_correction` | 按 MODEL_REGISTRY 整套覆盖（含 provider/mode/completion_params）|
| `syntax_error` | `code_rewrite` | python3 节点不应有 JS 语法 |

fixes.json 格式：
```json
{
  "fixes": [
    {"node_id": "abc123", "fix_type": "output_fix", "reason": "return 包含 result 但 outputs 未声明", "fixed_outputs": {"result": {"type": "string"}}}
  ],
  "unfixed_issues": []
}
```

对每条 issue 生成的修复，先写到 {OUT_DIR}/fixes-static.json（格式 `{"fixes": [...]}`），然后调用：

```bash
python {SKILL_DIR}/scripts/run.py append_fixes {FIXES} {OUT_DIR}/fixes-static.json static
```

如果没有可自动修复的问题，跳过 append_fixes 即可。

### Phase 2b: Code 节点规范修复（分批子智能体）

主智能体编排，分批调用子智能体执行 6 条确定性规范修复。

**步骤**：

1. 获取所有 code 节点列表：

```bash
python {SKILL_DIR}/scripts/run.py query {ANALYSIS} list_by_type code
```

2. 将节点 ID 按每批 5 个分组。如果总数 ≤ 5，只需一批。

3. 对每批分派一个子智能体（model: sonnet），prompt 结构如下（替换 `{BATCH_NODE_IDS}` 为该批节点 ID 逗号分隔列表，`{N}` 为批次序号从 1 开始）：

```
你是 Dify 工作流 code 节点规范修复专家。

任务：按照 6 条核心规则检查指定 code 节点，生成完整代码修复。

待检查节点 ID：{BATCH_NODE_IDS}

查询命令参见「子智能体通用规范 > 查询命令」。
输出格式参见「子智能体通用规范 > code_rewrite 输出格式」。

## 6 条核心规则

1. 入口函数名必须是 main（不能是 execute 或其他）
2. 入参不能是单个 input 对象，必须解构为 {param1, param2, ...}
   - 参数列表从 get_inputs 返回的 variable 字段提取
3. 参数名必须与 get_inputs 返回的 variable 完全一致
4. 代码逻辑：未定义变量引用、死代码、条件永真/永假、变量自引用 TDZ
5. 每个分支的 return 都要包含 get_outputs 声明的所有字段
   - 缺失字段补默认值（字符串补 ""，数字补 0，布尔补 false，数组补 []）
6. return 字段必须与 outputs 定义一致
   - 如果 return 有额外字段未在 outputs 声明，生成额外的 output_fix

## 操作步骤

对每个节点：
1. 依次执行 get_code、get_inputs、get_outputs
2. 按 6 条规则逐一检查
3. 如果有问题，生成 code_rewrite 修复（合并该节点所有问题到一条修复）
4. 如果节点无问题，跳过

## 修复示例

原代码：function execute(input) { return {txt: input.arg}; }
inputs: [{variable: "arg"}]
outputs: {txt: {type: string}}
修复：
{
  "node_id": "xxx",
  "fix_type": "code_rewrite",
  "reason": "函数名 execute→main；参数改为解构形式",
  "fixed_code": "function main({arg}) {\n    return {txt: arg};\n}"
}

完成后将所有修复写入 {OUT_DIR}/fixes-code-batch-{N}.json（格式 {"fixes": [...]}），然后执行：
python {SKILL_DIR}/scripts/run.py append_fixes {FIXES} {OUT_DIR}/fixes-code-batch-{N}.json code_norm
```

4. 等待所有批次子智能体完成后，进入 Phase 3。

**🔴 CHECKPOINT**：向用户汇报 Phase 2b 修复结果（修复了多少个节点、哪些规则命中），等待用户确认继续深度审查。如果用户说"跳过"，直接进入 Phase 5。

### Phase 3: Code 节点深度逻辑审查（子智能体）

Phase 2b 已完成规范修复（函数名、参数、return 字段）。本阶段聚焦**复杂逻辑问题**，由 opus 模型深度审查。

用 Agent 工具分派子智能体（model: opus），prompt 如下：

```
你是 Dify 工作流 code 节点深度逻辑审查专家。

任务：审查所有 code 节点的**复杂逻辑正确性**，生成可直接应用的完整代码修复。

注意：规范类问题（函数名、参数解构、参数名匹配、return 字段完整性）已在前置阶段修复。本阶段只关注逻辑层面的问题。

输入文件：
- analysis.json: {ANALYSIS}
- fixes.json: {FIXES}

查询命令参见「子智能体通用规范 > 查询命令」。
输出格式参见「子智能体通用规范 > code_rewrite 输出格式」。

先检查 {FIXES} 中已有哪些 code_rewrite 修复：
- 记录已有 code_rewrite 的 node_id 列表
- 对这些节点，审查 fixed_code 而非原始代码

审查要点（仅关注逻辑层面）：
1. **控制流完整性**：不可达代码路径、缺少 else 分支导致 undefined 返回
2. **变量生命周期**：变量自引用 TDZ（如 const x = f(x)）、闭包陷阱
3. **类型安全**：对可能为 null/undefined 的值直接访问属性
4. **循环逻辑**：无限循环、off-by-one、迭代器误用
5. **业务逻辑**：条件判断是否合理、数据转换是否正确
6. **异常路径**：try-catch 是否吞掉了关键错误

**不要重复修复的问题**（已在 Phase 2b 处理）：
- 函数名不是 main
- 参数未解构或参数名不匹配
- return 字段与 outputs 不一致

自检：完成后检查 fixes-code.json 中每条修复是否都有 `fixed_code` 字段。

输出：把修复写入 {OUT_DIR}/fixes-code.json，然后执行：
python {SKILL_DIR}/scripts/run.py append_fixes {FIXES} {OUT_DIR}/fixes-code.json code_review
```

### Phase 4: LLM 节点审查（子智能体）

用 Agent 工具分派子智能体（model: opus）：

```
你是 Dify 工作流 LLM 节点审查专家。

任务：审查所有 LLM 节点的提示词质量和模型配置，**生成可直接应用的修复**。

输入文件：
- analysis.json: {ANALYSIS}
- fixes.json: {FIXES}

查询命令参见「子智能体通用规范 > 查询命令」。使用 list_by_type llm、get_node、get_prompt。

审查要点：
1. 提示词中 {{#nodeId.varName#}} 引用是否指向存在的节点和变量
2. 模型选择（千问3.5等弱模型建议升级为 DeepSeek-V3.1）
3. 提示词是否有清晰的结构化输出要求
4. 是否缺少必要的约束或格式说明

修复分两类：

1. **可自动修复**（生成 fix）：
   - 模型配置错误 → `model_correction`
   - 提示词变量引用错误 → `prompt_fix`

2. **需人工判断**（记录到 unfixed_issues）：
   - 提示词质量问题、结构优化建议

示例 - 模型修正：
{
  "node_id": "1775726093095",
  "fix_type": "model_correction",
  "reason": "千问3.5 弱模型升级为 DeepSeek-V3.1",
  "fixed_model": {
    "provider": "langgenius/openai_api_compatible/deepseek",
    "name": "DeepSeek-V3.1",
    "mode": "chat",
    "completion_params": {"temperature": 0.1, "top_p": 0.9, "max_tokens": 4096}
  },
  "fixed_model_name": "DeepSeek-V3.1"
}

示例 - 提示词修正：
{
  "node_id": "1775814071784",
  "fix_type": "prompt_fix",
  "reason": "修正变量引用 {{#1775801469266.detail#}}",
  "fixed_prompt": "根据以下商品信息生成推荐回复：\n\n{{#1775801469266.detail#}}\n\n要求：简洁、突出卖点"
}

规则：
1. 只对明确错误生成 fix（如引用不存在的节点）
2. 质量建议记录到 unfixed_issues，不生成 fix
3. model_correction 必须包含 `fixed_model_name` 字段

输出：把修复写入 {OUT_DIR}/fixes-llm.json，然后执行：
python {SKILL_DIR}/scripts/run.py append_fixes {FIXES} {OUT_DIR}/fixes-llm.json llm_review
```

### Phase 5: 应用修复 + 生成报告

等待 Phase 3 和 4 的子智能体完成后执行：

应用修复前先校验 fixes.json：

```bash
python {SKILL_DIR}/scripts/run.py validate_fixes {FIXES}
```

若校验失败，根据错误信息修正后再继续。

**🔴 CHECKPOINT**：向用户汇报修复数量和类型（code_rewrite / model_correction / prompt_fix 等），等待用户确认应用修复。如果用户说"取消"，停止 heal 流程。

```bash
# 应用修复生成新 yml
python {SKILL_DIR}/scripts/run.py heal <YML_FILE> <FIXES> <NEW_YML>

# 生成报告和推导链数据
python {SKILL_DIR}/scripts/run.py report <ANALYSIS> <FIXES> <OUT_DIR>
```

输出文件：`new.yml`、`report.md`、`branches-detail.json`、`test-derivation.json`。

heal 命令会自动写出 {OUT_DIR}/heal-verification.json。如果其中 parseable: false 或 newly_introduced_issues 非空，向用户警告——这意味着修复反向破坏了 yml 或引入了新问题。

向用户汇报（必须包含以下数据）：
```
修复完成：
- 总修复数：N 个
  - code_rewrite: X 个（函数名/参数/return 修复）
  - model_correction: Y 个（模型配置修正）
  - prompt_fix: Z 个（提示词修正）
  - output_fix: W 个（输出字段修正）
- 未修复问题：M 个（记录在 unfixed_issues）
- 新 yml：{OUT_DIR}/new.yml
- 报告：{OUT_DIR}/report.md
- 验证状态：✅ parseable / ⚠️ 有问题（详见 heal-verification.json）
```

### Phase 6: 测试值推导（可选）

仅在用户明确需要测试数据时执行。用 Agent 工具分派（model: opus）：

```
你是 Dify 工作流测试数据推导专家。

任务：根据推导链数据，为 start 节点生成能覆盖关键分支的测试输入值。

输入文件：
- test-derivation.json: {OUT_DIR}/test-derivation.json
- analysis.json: {ANALYSIS}

查询命令：
- python {SKILL_DIR}/scripts/run.py query {ANALYSIS} list_derivations {OUT_DIR}/test-derivation.json
- python {SKILL_DIR}/scripts/run.py query {ANALYSIS} get_derivation {OUT_DIR}/test-derivation.json <branch_id>
- python {SKILL_DIR}/scripts/run.py query {ANALYSIS} get_chain {OUT_DIR}/test-derivation.json <branch_id> <idx>
- python {SKILL_DIR}/scripts/run.py query {ANALYSIS} get_code <node_id>

推导方法：
1. 列出所有推导分支，选得分最高的 3-5 条（得分综合了分支长度、节点类型多样性）
2. 对每条分支，从 if-else 条件倒推：条件要求什么值 → 上游节点如何产生该值 → start 输入需要什么
3. 如果推导链过长（>5 节点），逐节点倒推

输出：写入 {OUT_DIR}/test-values.json：
{
  "test_cases": [
    {
      "branch_id": "...",
      "description": "覆盖分支说明",
      "start_inputs": {"param1": "value1", ...},
      "expected_path": ["node1", "node2", ...]
    }
  ]
}
```

---

## CLI 命令速查

统一入口：`python {SKILL_DIR}/scripts/run.py <command> [args]`

| 命令 | 说明 |
|------|------|
| `analyze <yml> [--out <dir>]` | 静态分析 → analysis.json |
| `query <json> <subcmd> [args]` | 查询节点数据 |
| `init_fixes <fixes>` | 初始化空 fixes.json |
| `append_fixes <fixes> <new> <source>` | 原子追加修复（带文件锁） |
| `validate_fixes <fixes>` | 校验 fixes.json schema |
| `heal <yml> <fixes> <输出>` | 应用修复 → new.yml + heal-verification.json |
| `report <analysis> <fixes> <dir>` | 生成报告 |

query 子命令：`list_nodes`、`list_by_type <type>`、`get_node <id>`、`get_code <id>`、`get_inputs <id>`、`get_outputs <id>`、`get_prompt <id>`、`list_derivations <json>`、`get_derivation <json> <id>`、`get_chain <json> <id> <idx>`

---

## 设计决策说明

这些约束背后的原因，帮助你在边界情况下做出正确判断：

- **用 query 而非直接读取 analysis.json**：analysis.json 包含所有节点的完整数据（代码、提示词等），通常 500KB+，直接读取会浪费上下文窗口。query 命令只返回你需要的部分。

- **fixes.json 用 append_fixes 而不是直接读写**：多个子智能体并行运行时会同时写 fixes.json。脚本用文件锁 + 原子 rename 保证并发安全；按 (node_id, fix_type) 去重，先到先得（因此 Phase 2a/2b 的修复优先于 Phase 3/4 的 AI 修复）。

- **Phase 2b 用 sonnet 而非 opus**：规范修复是模式匹配（函数名、参数形式、return 字段），不需要深度推理。sonnet 成本更低、速度更快，且规则明确不易出错。Phase 3 保持 opus 用于复杂逻辑审查。

- **Phase 2b 分批 5 个节点**：每批子智能体需要对每个节点执行 3 次 query（get_code/get_inputs/get_outputs），5 个节点 = 15 次查询，在 sonnet 上下文窗口内可控。

- **fork 节点白名单**：只有 `if-else` 和 `question-classifier` 会被拆成多分支。`iteration` 等其他多 successor 节点保持顺序遍历，避免误把子图当成主分支。

- **healer 后置验证**：apply_fixes 后重跑解析与静态校验，对比修复后的 issues 与原始 issues 集合，输出 newly_introduced_issues。这能在修复反向引入引用错误等场景及时报警。

- **yml 写入只改有问题的字段**：Dify 的 yml 结构复杂（嵌套深、字段多），全量重写容易引入格式问题。healer 只修改 fixes 中指定的字段，保持其余结构不变。

## 错误处理（if-then 三段式）

| 触发条件 | 一线修复 | 仍失败兜底 |
|----------|----------|------------|
| `analyze` 报错 "yml 格式无效" | 检查文件是否为有效 yml（缩进、encoding） | 向用户说明并停止流程，不生成 analysis.json |
| `analyze` 报错 "节点 ID 重复" | 记录重复 ID 列表，继续生成 analysis.json | 在报告中标注"存在重复节点，部分结果可能不准" |
| 子智能体超时（>120s 无响应） | 重试一次，缩短 prompt 只检查核心规则 | 跳过该批次，记录到 unfixed_issues，继续后续 Phase |
| 子智能体返回空修复 | 检查节点是否确实无问题（手动 query 验证） | 跳过该节点，不写入 fixes.json |
| `validate_fixes` 失败 | 按错误信息修正 fixes.json（常见：node_id 不存在） | 回退到上一个有效版本，重新生成修复 |
| `heal` 失败 | 检查 fixes.json 中 node_id 是否存在于 yml | 移除无效修复，重新 validate + heal |
| `heal-verification.json` 显示 `parseable: false` | 回滚到原始 yml，移除最后一批修复 | 逐条移除修复定位问题来源，重新 heal |
| `append_fixes` 报 "并发冲突" | 等待 1s 后重试 | 手动合并修复文件 |

---

## 反例与黑名单（不要做的事）

| # | 反模式 | 为什么不要做 | 正确做法 |
|---|--------|-------------|----------|
| 1 | **直接读取 analysis.json** | 文件通常 >500KB，会溢出上下文窗口 | 使用 `query` 命令按需获取节点数据 |
| 2 | **直接读写 fixes.json** | 多子智能体并发时会互相覆盖，数据丢失 | 用 `append_fixes` 原子写入，自带文件锁 |
| 3 | **跳过 validate_fixes 直接 heal** | 修复格式错误会导致生成的 yml 不可用 | 先校验再应用，校验失败则修正后重试 |
| 4 | **Phase 2b 用 opus 模型** | 规范修复是模式匹配，opus 成本高且无必要 | Phase 2b 用 sonnet，Phase 3/4 才用 opus |
| 5 | **全量重写 yml 文件** | Dify yml 嵌套深，全量重写易引入格式问题 | healer 只修改 fixes 指定的字段 |
| 6 | **修复后不验证** | 修复可能反向引入新问题 | 检查 heal-verification.json 的 parseable 和 newly_introduced_issues |
| 7 | **把质量建议生成 fix** | 质量建议是主观的，不应自动应用 | 记录到 unfixed_issues，由用户决定 |

**危险信号（遇到时必须停止）**：
- `analyze` 输出的 issues 数量 > 节点数 → yml 可能严重损坏
- `heal-verification.json` 中 `parseable: false` → 修复破坏了 yml 结构
- 子智能体返回的 fixed_code 为空或只有注释 → 修复无效
