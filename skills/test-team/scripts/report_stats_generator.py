#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
report_stats_generator.py - 测试报告统计数据预处理工具

从需求文档、测试用例、执行记录、缺陷记录中提取统计摘要，
输出轻量级 JSON（< 5K tokens），用于生成测试报告。

用法：
    python report_stats_generator.py \\
        --req REQ-20260520-1030.md \\
        --tc TC-20260520-1100.json \\
        --exec EXEC-20260520-1500.json \\
        --bugs BUGS-20260520-1500.json \\
        --output report-stats.json
"""

import argparse
import json
import sys
import re
from pathlib import Path
from typing import Dict, List, Set, Any


def parse_requirements(req_path: Path) -> Dict[str, Any]:
    """
    解析需求文档，提取需求编号列表。

    Args:
        req_path: 需求文档路径（REQ-*.md）

    Returns:
        {"total": int, "ids": ["F001", "F002", ...]}
    """
    if not req_path.exists():
        raise FileNotFoundError(f"需求文档不存在: {req_path}")

    content = req_path.read_text(encoding="utf-8")

    # 匹配需求编号：F001-F999
    req_pattern = re.compile(r'\bF\d{3}\b')
    req_ids = sorted(set(req_pattern.findall(content)))

    return {
        "total": len(req_ids),
        "ids": req_ids
    }


def parse_test_cases(tc_path: Path) -> Dict[str, Any]:
    """
    解析测试用例 JSON，统计用例总数、优先级分布、覆盖的需求。

    Args:
        tc_path: 测试用例文件路径（TC-*.json）

    Returns:
        {
            "total": int,
            "by_priority": {"P0": int, "P1": int, "P2": int},
            "covered_reqs": ["F001", "F002", ...]
        }
    """
    if not tc_path.exists():
        raise FileNotFoundError(f"测试用例文件不存在: {tc_path}")

    with open(tc_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    if not isinstance(cases, list):
        raise ValueError(f"测试用例文件格式错误，应为数组: {tc_path}")

    priority_count = {"P0": 0, "P1": 0, "P2": 0}
    covered_reqs = set()

    for case in cases:
        # 统计优先级
        priority = case.get("priority", "P2")
        if priority in priority_count:
            priority_count[priority] += 1

        # 提取覆盖的需求编号
        req_field = case.get("req", "")
        if req_field:
            # 支持多种格式：F001 或 F001,F002 或 F001/F002
            req_ids = re.findall(r'F\d{3}', req_field)
            covered_reqs.update(req_ids)

    return {
        "total": len(cases),
        "by_priority": priority_count,
        "covered_reqs": sorted(covered_reqs)
    }


def parse_execution(exec_path: Path) -> Dict[str, Any]:
    """
    解析执行记录 JSON，统计执行结果分布。

    Args:
        exec_path: 执行记录文件路径（EXEC-*.json）

    Returns:
        {
            "total": int,
            "passed": int,
            "failed": int,
            "blocked": int,
            "skipped": int,
            "pass_rate": float
        }
    """
    if not exec_path.exists():
        raise FileNotFoundError(f"执行记录文件不存在: {exec_path}")

    with open(exec_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    if not isinstance(records, list):
        raise ValueError(f"执行记录文件格式错误，应为数组: {exec_path}")

    status_count = {
        "passed": 0,
        "failed": 0,
        "blocked": 0,
        "skipped": 0
    }

    for record in records:
        status = record.get("status", "").lower()
        # 支持中英文状态
        if status in ["通过", "passed", "pass"]:
            status_count["passed"] += 1
        elif status in ["失败", "failed", "fail"]:
            status_count["failed"] += 1
        elif status in ["阻塞", "blocked", "block"]:
            status_count["blocked"] += 1
        elif status in ["跳过", "skipped", "skip"]:
            status_count["skipped"] += 1

    total = len(records)
    pass_rate = (status_count["passed"] / total * 100) if total > 0 else 0.0

    return {
        "total": total,
        "passed": status_count["passed"],
        "failed": status_count["failed"],
        "blocked": status_count["blocked"],
        "skipped": status_count["skipped"],
        "pass_rate": round(pass_rate, 1)
    }


def parse_defects(bugs_path: Path) -> Dict[str, Any]:
    """
    解析缺陷记录 JSON，统计缺陷数量、严重程度、状态分布。

    Args:
        bugs_path: 缺陷记录文件路径（BUGS-*.json，可选）

    Returns:
        {
            "total": int,
            "by_severity": {"严重": int, "一般": int, "轻微": int},
            "by_status": {"待修复": int, "已修复": int, ...}
        }
    """
    if not bugs_path or not bugs_path.exists():
        return {
            "total": 0,
            "by_severity": {},
            "by_status": {}
        }

    with open(bugs_path, "r", encoding="utf-8") as f:
        bugs = json.load(f)

    if not isinstance(bugs, list):
        raise ValueError(f"缺陷记录文件格式错误，应为数组: {bugs_path}")

    severity_count = {}
    status_count = {}

    for bug in bugs:
        # 统计严重程度
        severity = bug.get("severity", "未知")
        severity_count[severity] = severity_count.get(severity, 0) + 1

        # 统计状态
        status = bug.get("status", "未知")
        status_count[status] = status_count.get(status, 0) + 1

    return {
        "total": len(bugs),
        "by_severity": severity_count,
        "by_status": status_count
    }


def assess_quality(pass_rate: float, severe_bugs: int) -> Dict[str, str]:
    """
    根据通过率和严重缺陷数量评估质量等级。

    规则：
    - 通过率 ≥ 90% 且严重缺陷 = 0 → "良好"
    - 通过率 ≥ 80% 且严重缺陷 ≤ 2 → "一般"
    - 其他 → "较差"

    Args:
        pass_rate: 通过率（百分比）
        severe_bugs: 严重缺陷数量

    Returns:
        {"verdict": str, "reason": str}
    """
    if pass_rate >= 90 and severe_bugs == 0:
        verdict = "良好"
        reason = f"通过率 {pass_rate}%，无严重缺陷"
    elif pass_rate >= 80 and severe_bugs <= 2:
        verdict = "一般"
        reason = f"通过率 {pass_rate}%，严重缺陷 {severe_bugs} 个"
    else:
        verdict = "较差"
        reason = f"通过率 {pass_rate}%，严重缺陷 {severe_bugs} 个"

    return {
        "verdict": verdict,
        "reason": reason
    }


def generate_stats(req_path: Path, tc_path: Path, exec_path: Path,
                   bugs_path: Path = None) -> Dict[str, Any]:
    """
    生成完整的统计数据。

    Args:
        req_path: 需求文档路径
        tc_path: 测试用例文件路径
        exec_path: 执行记录文件路径
        bugs_path: 缺陷记录文件路径（可选）

    Returns:
        完整的统计数据字典
    """
    # 解析各个文件
    req_data = parse_requirements(req_path)
    tc_data = parse_test_cases(tc_path)
    exec_data = parse_execution(exec_path)
    defect_data = parse_defects(bugs_path)

    # 计算覆盖率
    covered_count = len(tc_data["covered_reqs"])
    total_reqs = req_data["total"]
    coverage_rate = (covered_count / total_reqs * 100) if total_reqs > 0 else 0.0

    # 提取严重缺陷数量
    severe_bugs = defect_data["by_severity"].get("严重", 0)

    # 质量评估
    quality = assess_quality(exec_data["pass_rate"], severe_bugs)

    return {
        "requirements": {
            "total": total_reqs,
            "covered": covered_count,
            "coverage_rate": round(coverage_rate, 1)
        },
        "test_cases": {
            "total": tc_data["total"],
            "by_priority": tc_data["by_priority"]
        },
        "execution": exec_data,
        "defects": defect_data,
        "quality_assessment": quality
    }


def main():
    parser = argparse.ArgumentParser(
        description="测试报告统计数据预处理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
    python report_stats_generator.py \\
        --req test-output/requirements/REQ-20260520-1030.md \\
        --tc test-output/test-cases/TC-20260520-1100.json \\
        --exec test-output/execution/EXEC-20260520-1500.json \\
        --bugs test-output/execution/BUGS-20260520-1500.json \\
        --output report-stats.json
        """
    )

    parser.add_argument(
        "--req",
        type=str,
        required=True,
        help="需求文档路径（REQ-*.md）"
    )
    parser.add_argument(
        "--tc",
        type=str,
        required=True,
        help="测试用例文件路径（TC-*.json）"
    )
    parser.add_argument(
        "--exec",
        type=str,
        required=True,
        help="执行记录文件路径（EXEC-*.json）"
    )
    parser.add_argument(
        "--bugs",
        type=str,
        default=None,
        help="缺陷记录文件路径（BUGS-*.json，可选）"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="report-stats.json",
        help="输出统计数据的 JSON 路径（默认: report-stats.json）"
    )

    args = parser.parse_args()

    try:
        # 转换为 Path 对象
        req_path = Path(args.req)
        tc_path = Path(args.tc)
        exec_path = Path(args.exec)
        bugs_path = Path(args.bugs) if args.bugs else None
        output_path = Path(args.output)

        # 生成统计数据
        print(f"正在解析需求文档: {req_path}")
        print(f"正在解析测试用例: {tc_path}")
        print(f"正在解析执行记录: {exec_path}")
        if bugs_path:
            print(f"正在解析缺陷记录: {bugs_path}")

        stats = generate_stats(req_path, tc_path, exec_path, bugs_path)

        # 输出 JSON
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        print(f"\n[OK] 统计数据已生成: {output_path}")
        print(f"\n摘要:")
        print(f"  需求覆盖率: {stats['requirements']['coverage_rate']}%")
        print(f"  测试通过率: {stats['execution']['pass_rate']}%")
        print(f"  质量评估: {stats['quality_assessment']['verdict']}")
        print(f"  评估理由: {stats['quality_assessment']['reason']}")

    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()




