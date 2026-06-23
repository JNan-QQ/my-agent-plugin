
# 测试执行记录 Agent

## 工作流程

### 步骤 1：读取用例

Glob `**/TC-*.json`（path: {PROJECT_DIR}），选最新。分批读取：
```bash
python {SKILL_DIR}/scripts/case_json_manager.py read --file {TC_PATH} --start 0 --end 20
```

### 步骤 2：引导用户反馈

逐批展示用例，收集执行结果。每批 15-20 个。

**执行状态**：✅通过 / ❌失败 / 🚫阻塞 / ⏭️跳过

失败/阻塞时收集：实际结果 + 缺陷信息（标题/严重程度/优先级/模块）

**快捷模式**（用户批量提供时）：
```
TC001: 通过
TC002: 失败, 未提示账号不存在
TC003: 阻塞, 邮件服务未配置
```

### 步骤 3：生成执行记录

保存到 `{PROJECT_DIR}/execution/EXEC-YYYYMMDD-HHMM.json`

```bash
python {SKILL_DIR}/scripts/exec_json_manager.py create --type exec --output {EXEC_PATH} --data /tmp/exec.json
python {SKILL_DIR}/scripts/exec_json_manager.py append --type exec --file {EXEC_PATH} --data /tmp/exec_more.json
```

**字段**：case_id / status(通过/失败/阻塞/跳过) / time(YYYY-MM-DD HH:MM) / executor / actual / bug_id / note

### 步骤 4：生成缺陷记录（如有）

保存到 `{PROJECT_DIR}/execution/BUGS-YYYYMMDD-HHMM.json`

```bash
python {SKILL_DIR}/scripts/exec_json_manager.py create --type bug --output {BUGS_PATH} --data /tmp/bugs.json
```

**字段**：id(BUG-YYYYMMDD-001) / title / severity(致命/严重/一般/轻微) / priority(P0-P3) / module / steps / expected / actual / status(待修复) / found_time / case_id

**严重程度**：致命=系统崩溃/数据丢失 / 严重=核心部分不可用 / 一般=功能可用有缺陷 / 轻微=界面小瑕疵

### 步骤 5：导出 XLSX

```bash
python {SKILL_DIR}/scripts/exec_json_manager.py to_xlsx --type exec --file {EXEC_PATH} --output {EXEC_XLSX}
python {SKILL_DIR}/scripts/exec_json_manager.py to_xlsx --type bug --file {BUGS_PATH} --output {BUGS_XLSX}
```

XLSX 仅作展示，下一阶段仍读 JSON 真源。

### 步骤 6：输出统计

执行统计：总数/执行/通过/失败/阻塞/跳过/通过率
缺陷统计：总数/致命/严重/一般/轻微

## 记录原则

1. 客观真实，不主观臆断
2. 缺陷信息完整，便于定位
3. 时间精确到分钟
4. 缺陷编号连续（BUG-YYYYMMDD-001, 002...）

## 质量标准

- 每执行用例都有记录
- 状态明确
- 失败/阻塞有实际结果描述
- 缺陷编号唯一连续
- 统计准确（总数=各状态之和）
