# report_stats_generator.py

测试报告统计数据预处理工具，用于从需求文档、测试用例、执行记录、缺陷记录中提取统计摘要，输出轻量级 JSON（< 5K tokens）。

## 功能

- 解析需求文档（REQ-*.md），提取需求编号和总数
- 解析测试用例（TC-*.json），统计用例总数、优先级分布、覆盖的需求
- 解析执行记录（EXEC-*.json），统计执行结果（通过/失败/阻塞/跳过）和通过率
- 解析缺陷记录（BUGS-*.json，可选），统计缺陷数量、严重程度、状态分布
- 计算需求覆盖率和测试通过率
- 自动评估质量等级（良好/一般/较差）

## 用法

```bash
python report_stats_generator.py \
    --req <需求文档路径> \
    --tc <测试用例路径> \
    --exec <执行记录路径> \
    [--bugs <缺陷记录路径>] \
    [--output <输出路径>]
```

### 参数说明

- `--req`: 需求文档路径（REQ-*.md），必需
- `--tc`: 测试用例文件路径（TC-*.json），必需
- `--exec`: 执行记录文件路径（EXEC-*.json），必需
- `--bugs`: 缺陷记录文件路径（BUGS-*.json），可选
- `--output`: 输出统计数据的 JSON 路径，默认 `report-stats.json`

### 示例

```bash
# 完整示例（包含缺陷记录）
python report_stats_generator.py \
    --req test-output/requirements/REQ-20260520-1030.md \
    --tc test-output/test-cases/TC-20260520-1100.json \
    --exec test-output/execution/EXEC-20260520-1500.json \
    --bugs test-output/execution/BUGS-20260520-1500.json \
    --output report-stats.json

# 不包含缺陷记录
python report_stats_generator.py \
    --req test-output/requirements/REQ-20260520-1030.md \
    --tc test-output/test-cases/TC-20260520-1100.json \
    --exec test-output/execution/EXEC-20260520-1500.json \
    --output report-stats.json
```

## 输出格式

```json
{
  "requirements": {
    "total": 120,
    "covered": 115,
    "coverage_rate": 95.8
  },
  "test_cases": {
    "total": 180,
    "by_priority": {"P0": 30, "P1": 80, "P2": 70}
  },
  "execution": {
    "total": 180,
    "passed": 154,
    "failed": 18,
    "blocked": 5,
    "skipped": 3,
    "pass_rate": 85.6
  },
  "defects": {
    "total": 18,
    "by_severity": {"严重": 2, "一般": 10, "轻微": 6},
    "by_status": {"待修复": 15, "已修复": 3}
  },
  "quality_assessment": {
    "verdict": "良好|一般|较差",
    "reason": "通过率 85.6%，覆盖率 95.8%，严重缺陷 2 个"
  }
}
```

## 质量评估规则

- **良好**: 通过率 ≥ 90% 且严重缺陷 = 0
- **一般**: 通过率 ≥ 80% 且严重缺陷 ≤ 2
- **较差**: 其他情况

## 依赖

- Python 3.7+
- 标准库：argparse, json, sys, re, pathlib

## 测试

```bash
# 运行单元测试
pytest tests/test_report_stats_generator.py -v

# 使用示例数据测试
python report_stats_generator.py \
    --req test-data/REQ-example.md \
    --tc test-data/TC-example.json \
    --exec test-data/EXEC-example.json \
    --bugs test-data/BUGS-example.json \
    --output test-data/report-stats.json
```

## 错误处理

脚本会处理以下错误情况：

- 文件不存在：提示文件路径错误
- JSON 格式错误：提示 JSON 解析失败
- 数据格式错误：提示数据结构不符合预期

所有错误都会输出到 stderr 并返回非零退出码。
