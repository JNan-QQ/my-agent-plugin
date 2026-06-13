---
name: test-team
description: 测试团队6阶段工作流技能：需求分析→需求评审→用例编写→用例评审→执行记录→测试报告。触发词："测试"、"test"、"需求分析"、"analyze requirements"、"测试用例"、"test cases"、"用例编写"、"write cases"、"测试报告"、"test report"、"评审"、"review"、"执行测试"、"execute tests"、"设计用例"、"评审用例"、"记录执行"。适用于任何测试相关活动。
---

# 测试团队工作流

6 阶段流水线，每阶段派 sub-agent 执行。**你是路由器，不执行业务逻辑。**

## TL;DR

| 用户说 | → 阶段 |
|--------|--------|
| "测试XX功能" | 1 需求分析 |
| "评审需求" | 2 需求评审 |
| "设计用例" / "写用例" | 3 用例编写 |
| "评审用例" / "覆盖率" | 4 用例评审 |
| "记录执行" | 5 执行记录 |
| "生成报告" | 6 测试报告 |
| "继续" / 不确定 | 检查目录状态（步骤3） |

## 执行规则（HARD RULE）

1. MUST 使用 Agent 工具派发 sub-agent
2. NEVER 直接 Read `references/` 下的阶段指令
3. NEVER 执行业务逻辑（写需求、写用例、做评审、记录、写报告）
4. NEVER 复述 sub-agent 内部分析过程到主对话
5. 职责仅限：识别阶段 → 填模板 → 派 Agent → 转达结果 → 收集用户输入 → 再派发

允许的操作：Glob 解析路径 + Agent 派发 + 解析返回 + 收集用户输入

## 阶段识别

### 步骤 1：关键词匹配

"分析需求"→1 / "评审需求"→2 / "编写用例"→3 / "评审用例"→4 / "记录执行"→5 / "生成报告"→6

### 步骤 2：功能描述

用户提供功能描述或需求文档路径 → 阶段 1

### 步骤 3：目录状态（按优先级匹配，命中即停）

| 条件 | → 阶段 |
|------|--------|
| 无 `**/REQ-*.md` | 询问用户提供需求 |
| 无 `**/req-review-*.md` | 2 需求评审 |
| 最新 req-review 为封驳 | 1 修订需求 |
| 无 `**/TC-*.json` | 3 用例编写 |
| 无 `**/case-review-*.md` | 4 用例评审 |
| 最新 case-review 为封驳 | 3 修订用例 |
| 无 `**/EXEC-*.json` | 5 执行记录 |
| 有 EXEC | 6 测试报告 |

## 失败模式（三段式：触发 → 一线修复 → 兜底）

| 场景 | 触发 | 一线修复 | 兜底 |
|------|------|----------|------|
| sub-agent 超时 | >120s 无响应 | 重试1次(180s) | 告知用户等待指令 |
| 返回非 JSON | 期望JSON收到文本 | 重派+强调"必须返回纯JSON" | 解析文本提取关键字段 |
| JSON 格式错误 | 双引号未转义/尾逗号 | 用 python json.load 定位错误行，提示 sub-agent 修正 | 手动修复 JSON 后重新导入 |
| 文件写入失败 | 路径不存在 | mkdir -p 重试 | 告知用户路径和错误 |
| 首批合并文件不存在 | sub-agent 写入路径不一致 | 确认 test-output/.tmp/ 目录存在，检查文件名 | 手动指定正确路径重试 |
| 用例雷同重复 | sub-agent 未做去重 | 对比 title 字段，合并或删除重复用例 | 手动删除重复用例后重导 |
| 需求描述<50字 | 信息不足 | 追问功能列表 | 生成最小需求集标注不完整 |
| 封驳后用户坚持通过 | 用户Override | 记录决定+标注风险 | 写入"已知风险XXX"继续 |
| 批次生成失败 | sub-agent 错误 | 重试1次 | 跳过批次，报告中标注 |
| analyze 脚本失败 | 路径/参数错误 | 检查重试 | 降级手动统计 |
| 用户结果缺TC编号 | 格式不完整 | 展示缺失清单 | 标记"跳过"列出清单 |
| 统计数据缺失 | 文件不存在 | 检查路径 | 用已有数据生成标注不完整 |

封驳恢复：最多3轮 → 3轮仍封驳 → 强制记录 → 用户决定继续或终止

## 阶段类型

| 阶段 | 类型 | 协议 |
|------|------|------|
| 1 | 单次派发 | ONE-SHOT |
| 2 | 交互式 | PREPARE → 用户确认 → COMPLETE |
| 3 | 分批生成 | PREPARE → 分组确认 → COMPLETE 循环 |
| 4 | 交互式 | PREPARE → 分析 → COMPLETE |
| 5 | 交互式 | PREPARE → 用户提供结果 → COMPLETE |
| 6 | 交互式 | PREPARE → 统计确认 → COMPLETE |

## 变量解析

**Glob 路径规则**：`path` 必须为 `{CWD}`（绝对路径），pattern 必须以 `**/` 开头。

| 变量 | 来源 |
|------|------|
| `{SKILL_DIR}` | SKILL.md 所在目录绝对路径 |
| `{CWD}` | 当前工作目录 |
| `{REQ_PATH}` | Glob `**/REQ-*.md` 取最新 |
| `{TC_PATH}` | Glob `**/TC-*.json` 取最新 |
| `{REVIEW_PATH}` | Glob `**/*-review-*.md` 取最新 |
| `{DRAFT_PATH}` | PREPARE 返回的 `artifacts.*_draft_path` |
| `{ANALYSIS_PATH}` | PREPARE 返回的 `artifacts.analysis_path` |
| `{STATS_PATH}` | 阶段6 PREPARE 的 `artifacts.stats_path` |
| `{OUTPUT_PATH}` | 阶段3 PREPARE 的 `output_path` |
| `{USER_INPUT/DECISION/COMMENTS/RESULTS_TEXT}` | 用户输入 |
| `{BATCH/BATCH_START/TOTAL/REQ_IDS}` | 批次控制 |
| `{TEST_DIMENSIONS}` | 测试维度选择（如"功能+性能"） |
| `{IMAGE_ANALYSIS}` | 是否分析需求文档图片（是/否） |
| `{USER_CONFIRMATIONS}` | 用户对模糊风险功能点的确认标准 |

## Dispatch 模板

### 阶段 1：需求分析（ONE-SHOT）

#### 1.1 测试维度选择

🔴 CHECKPOINT · 展示测试维度选项，**等用户确认**：

| 维度 | 说明 | 默认 |
|------|------|------|
| 功能测试 | 验证业务逻辑、交互流程、数据处理 | ✓ 必选 |
| 性能测试 | 响应时间、并发、吞吐量 | 可选 |
| 安全测试 | 认证、授权、数据加密、防攻击 | 可选 |
| 兼容性测试 | 浏览器、OS、设备适配 | 可选 |
| 可用性测试 | 用户体验、操作便捷性 | 可选 |

用户回复示例："功能+性能" 或 "只测功能"

#### 1.2 需求文档图片分析

若用户提供文档路径，提醒用户：

> 该需求文档包含图片内容，是否需要分析图片中的流程图/原型图/架构图？
> - 分析图片：提取图片中的业务规则、交互流程、数据流转
> - 不分析：仅分析文字内容

#### 1.3 执行需求分析

```
Agent({
  description: "执行阶段1：需求分析",
  prompt: "你是测试团队的需求分析师。\n读取 `{SKILL_DIR}/references/1-analyze-req.md` 获取完整执行指令。\n工作目录：{CWD}\n用户输入：\n{USER_INPUT}\n测试维度：{TEST_DIMENSIONS}\n图片分析：{IMAGE_ANALYSIS}\n严格按照指令执行，产出 1个 REQ-*.md 到 test-output/requirements/（一个需求文档=一个REQ文件）。\n完成后报告：产出文件路径 + 需求条数 + 风险条数。"
})
```

🔴 CHECKPOINT · 展示文件路径+需求条数+风险条数 → **等用户确认** → 确认后进入阶段2

### 阶段 2 PREPARE

#### 2.1 模糊风险识别

🔴 CHECKPOINT · 展示模糊风险列表，**询问用户确认**：

> 以下功能点存在模糊描述，需要您确认具体标准：
> 
> | 需求 | 模糊描述 | 需确认 |
> |------|---------|--------|
> | F001 | "快速响应" | 期望响应时间是多少？ |
> | F002 | "安全加密" | 使用什么加密算法？ |
> 
> 请回复您的确认，或标注"不修改"跳过。

#### 2.2 五维度评审

```
Agent({
  description: "阶段2准备：需求评审分析",
  prompt: "你是测试团队的需求评审员。\n读取 `{SKILL_DIR}/references/2-review-req.md` 获取完整评审指令。\n工作目录：{CWD}\n需求文档路径：{REQ_PATH}\n用户确认的标准：{USER_CONFIRMATIONS}\n任务：执行5维度评审+封驳判定，不写最终报告。草稿写入 {CWD}/test-output/.tmp/req-review-draft.json。\n输出严格 JSON：{\"stage\":2,\"summary\":\"...\",\"scores\":{},\"verdict\":\"通过|有条件通过|封驳\",\"issues\":[],\"questions\":[{\"id\":\"q1\",\"type\":\"confirm\",\"text\":\"...\"}],\"pending_confirmations\":[{\"requirement\":\"F001\",\"fuzzy\":\"快速响应\",\"confirmed\":\"响应时间<2s\"}],\"artifacts\":{\"review_draft_path\":\"{CWD}/test-output/.tmp/req-review-draft.json\"}}"
})
```

🔴 CHECKPOINT · 解析JSON → 展示summary+scores+verdict+pending_confirmations → **等用户回答** → 派COMPLETE

### 阶段 2 COMPLETE

```
Agent({
  description: "阶段2完成：写入需求评审报告",
  prompt: "你是测试团队的需求评审员。\n读取 `{SKILL_DIR}/references/2-review-req.md` 获取报告格式。\n工作目录：{CWD}\n评审草稿：{DRAFT_PATH}\n用户决定：{USER_DECISION}\n用户意见：{USER_COMMENTS}\n生成评审报告 req-review-*.md 到 test-output/reviews/。\n完成后报告：文件路径 + 最终结论。"
})
```

### 阶段 3 PREPARE

```
Agent({
  description: "阶段3准备：需求分组",
  prompt: "你是测试团队的用例设计师。\n读取 `{SKILL_DIR}/references/3-write-cases.md`。\n工作目录：{CWD}\n需求文档：{REQ_PATH}\n评审报告（封驳后必填，否则空）：{REVIEW_PATH}\n任务：按功能模块分组（每组10-15条需求），不生成用例。\n输出JSON：{\"stage\":3,\"summary\":\"N条需求分M组\",\"groups\":[{\"group\":1,\"reqs\":[\"F001\"],\"summary\":\"模块名\"}],\"total_reqs\":N,\"output_path\":\"test-output/test-cases/TC-YYYYMMDD-HHMM.json\"}"
})
```

🔴 CHECKPOINT · 展示分组清单 → **用户确认** → 逐组派COMPLETE

### 阶段 3 COMPLETE（分批循环）

```
Agent({
  description: "阶段3完成：生成第{BATCH}/{TOTAL}批用例",
  prompt: "你是测试团队的用例设计师。\n读取 `{SKILL_DIR}/references/3-write-cases.md`，其中包含去重规则、步骤写法规范、预期结果写法规范。\n工作目录：{CWD}\n需求文档：{REQ_PATH}\n评审报告：{REVIEW_PATH}\n只为以下需求生成用例（第{BATCH}/{TOTAL}批）：{REQ_IDS}\n\n质量要求（生成前逐条检查）：\n1. 去重：每条用例有唯一测试点，对比 title 不得雷同\n2. 步骤：每步一个操作，动词+对象+具体数据（如 `输入用户名 \\\"admin\\\"`）\n3. 预期：可验证——包含具体页面元素/文字/数值，禁用\"成功\"\"正常\"等模糊词\n4. 覆盖：每需求至少 正常+异常+边界 三类\n\nJSON 格式规则：\n1. 纯 JSON 数组 [{...}, {...}]\n2. 双引号转义为 \\\"\n3. 换行用 \\n\n用 Write 工具写入：{CWD}/test-output/.tmp/tc-batch-{BATCH}.json\n编号从 TC{BATCH_START} 开始递增。\n完成后报告：用例数 + 覆盖需求数 + 去重检查结果。"
})
```

主 agent 每批后执行：
1. 首批：`python scripts/case_json_manager.py create --output {OUTPUT_PATH} --data test-output/.tmp/tc-batch-1.json`
2. 后续：`python scripts/case_json_manager.py append --file {OUTPUT_PATH} --data test-output/.tmp/tc-batch-{BATCH}.json`
3. 失败重试1次，仍失败跳过并标注

### 阶段 4 PREPARE

```
Agent({
  description: "阶段4准备：用例覆盖度分析",
  prompt: "你是测试团队的用例评审员。\n工作目录：{CWD}\n用例文件：{TC_PATH}\n需求文档：{REQ_PATH}\n调用 analyze 获取数据：python scripts/case_json_manager.py analyze --file {TC_PATH} --reqs <需求范围> --output {CWD}/test-output/.tmp/analysis.json\n基于分析结果判断封驳（需求覆盖率<90%或场景覆盖率<70%→封驳）。\n输出JSON：{\"stage\":4,\"summary\":\"...\",\"coverage\":{\"requirement_rate\":X,\"scene_rate\":Y},\"verdict\":\"通过|有条件通过|封驳\",\"issues\":[],\"questions\":[{\"id\":\"q1\",\"type\":\"confirm\",\"text\":\"...\"}],\"artifacts\":{\"analysis_path\":\"{CWD}/test-output/.tmp/analysis.json\",\"review_draft_path\":\"{CWD}/test-output/.tmp/case-review-draft.json\"}}"
})
```

🔴 CHECKPOINT · 展示coverage+verdict+questions → **等用户回答** → 派COMPLETE

### 阶段 4 COMPLETE

```
Agent({
  description: "阶段4完成：写入用例评审报告",
  prompt: "你是测试团队的用例评审员。\n读取 `{SKILL_DIR}/references/4-review-cases.md`。\n工作目录：{CWD}\n评审草稿：{DRAFT_PATH}\n分析数据：{ANALYSIS_PATH}\n用户决定：{USER_DECISION}\n用户意见：{USER_COMMENTS}\n生成 case-review-*.md 到 test-output/reviews/，末尾写最终结论。\n完成后报告：文件路径 + 最终结论。"
})
```

主 agent：通过/有条件通过 → `python scripts/case_json_manager.py to_xlsx --file {TC_PATH} --output {TC_PATH_XLSX}`

### 阶段 5 PREPARE

```
Agent({
  description: "阶段5准备：生成待执行用例清单",
  prompt: "你是测试团队的执行协调员。\n读取 `{SKILL_DIR}/references/5-exec-cases.md`。\n工作目录：{CWD}\n读取最新 TC-*.json，生成待执行清单（每批15-20条）。\n输出JSON：{\"stage\":5,\"summary\":\"待执行N条分M批\",\"batches\":[{\"batch\":1,\"cases\":[{\"id\":\"TC001\",\"title\":\"...\",\"steps_summary\":\"...\"}]}],\"prompt_template\":\"TC编号 | 通过/失败/阻塞/跳过 | 实际结果\"}"
})
```

🛑 STOP · 逐批展示清单 → **等待用户逐批提供结果** → 全部收集后派COMPLETE

### 阶段 5 COMPLETE

```
Agent({
  description: "阶段5完成：写入执行记录和缺陷",
  prompt: "你是测试团队的执行记录员。\n读取 `{SKILL_DIR}/references/5-exec-cases.md`。\n工作目录：{CWD}\n用例文件：{TC_PATH}\n用户执行结果：\n{RESULTS_TEXT}\n生成 EXEC-*.json + BUGS-*.json（如有失败）到 test-output/execution/。\n完成后报告：EXEC路径 + BUGS路径（如有）+ 通过率 + 缺陷数。"
})
```

主 agent：`python scripts/exec_json_manager.py to_xlsx` 导出 XLSX

### 阶段 6 PREPARE

```
Agent({
  description: "阶段6准备：测试数据统计",
  prompt: "你是测试团队的数据分析员。\n工作目录：{CWD}\n调用：python scripts/report_stats_generator.py --req test-output/requirements/REQ-*.md --tc test-output/test-cases/TC-*.json --exec test-output/execution/EXEC-*.json --bugs test-output/execution/BUGS-*.json --output {CWD}/test-output/.tmp/report-stats.json\n读取 {CWD}/test-output/.tmp/report-stats.json 获取统计摘要。\n输出JSON：{\"stage\":6,\"summary\":\"...\",\"stats\":{\"pass_rate\":X,\"total_cases\":N,\"defect_count\":M,\"coverage_rate\":Y},\"artifacts\":{\"stats_path\":\"{CWD}/test-output/.tmp/report-stats.json\"}}"
})
```

🔴 CHECKPOINT · 展示summary+stats → **用户确认** → 派COMPLETE

### 阶段 6 COMPLETE

```
Agent({
  description: "阶段6完成：生成测试报告",
  prompt: "你是测试团队的报告撰写员。\n读取 `{SKILL_DIR}/references/6-test-report.md`。\n工作目录：{CWD}\n统计数据：{STATS_PATH}\n基于统计数据生成 REPORT-*.md 到 test-output/reports/，不读原始JSON。\n完成后报告：文件路径 + 通过率 + 缺陷数 + 质量评估结论。"
})
```

🔴 CHECKPOINT · 展示报告路径+通过率+缺陷数+结论 → **等用户确认** → 标记工作流完成

## 反例与黑名单

### 主 agent 反模式

| 反模式 | 后果 | 正确做法 |
|--------|------|----------|
| 直接 Read references/ | 上下文爆炸 | 只通过 Agent 派发 |
| 复述 sub-agent 分析过程 | 污染上下文 | 只转达结果摘要 |
| 跳过用户确认 | 失去控制 | 交互阶段必须等回答 |
| 自己执行业务逻辑 | 违反路由器定位 | 永远派发 sub-agent |
| 阶段3不分批 | 上下文溢出 | 按 groups 分批 |

### sub-agent 反模式

| 反模式 | 后果 | 正确做法 |
|--------|------|----------|
| 不读 reference 凭经验 | 格式不一致 | 必须先读对应 reference |
| markdown 包裹 JSON | 解析失败 | 输出纯 JSON |
| 跳过写文件 | 数据丢失 | 写入指定路径 |
| 修改非本阶段文件 | 数据污染 | 只写本阶段输出路径 |

### 危险操作

| 操作 | 风险 | 规避 |
|------|------|------|
| 覆盖率<90%仍给通过 | 遗漏功能 | 按阈值封驳 |
| 用例不分批写入 | JSON损坏 | 严格按 groups 分批 |
| 跳过评审进下一阶段 | 质量失控 | 评审必须有结论 |
| 封驳后不追踪 | 问题遗留 | 记录修改要求并重新评审 |

### 典型错误示例

**❌ 复述分析过程**：需求分析师首先检查了功能列表，发现3个模块，然后对每个模块进行了详细分析……（500字）
**✅ 只转达结果**：需求分析完成：3个模块、12条需求、2个风险点。文件：test-output/requirements/REQ-20260602-1430.md

**❌ markdown包裹JSON**：```json\n{"stage":2,...}\n```
**✅ 纯JSON**：{"stage":2,"verdict":"通过",...}
