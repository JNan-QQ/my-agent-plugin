#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
xlsx_reader.py - 通用 XLSX 读取工具

用法：
    python xlsx_reader.py --file TC-xxx.xlsx --format json       # 输出 JSON
    python xlsx_reader.py --file TC-xxx.xlsx --format summary    # 输出统计摘要
    python xlsx_reader.py --file TC-xxx.xlsx --sheet Sheet1      # 指定 sheet
"""

import argparse
import json
import sys
from pathlib import Path

import openpyxl


def read_xlsx(file_path, sheet_name=None):
    """读取 XLSX 文件，返回表头和数据行列表。"""
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    ws = wb[sheet_name] if sheet_name else wb.active

    rows = []
    for row in ws.iter_rows(values_only=True):
        rows.append([str(cell) if cell is not None else "" for cell in row])
    wb.close()

    if not rows:
        return [], []

    headers = rows[0]
    data = rows[1:]
    return headers, data


def to_json(headers, data):
    """将表头+数据转为 JSON 对象列表。"""
    result = []
    for row in data:
        obj = {}
        for i, h in enumerate(headers):
            obj[h] = row[i] if i < len(row) else ""
        result.append(obj)
    return result


def to_summary(headers, data, file_path):
    """生成统计摘要。"""
    summary = {
        "file": str(file_path),
        "total_rows": len(data),
        "columns": headers,
        "column_count": len(headers),
    }

    # 尝试按常见列名做统计
    header_lower = [h.strip() for h in headers]

    # 优先级分布
    if "优先级" in header_lower:
        idx = header_lower.index("优先级")
        priority_dist = {}
        for row in data:
            val = row[idx].strip() if idx < len(row) else ""
            if val:
                priority_dist[val] = priority_dist.get(val, 0) + 1
        summary["priority_distribution"] = priority_dist

    # 用例类型分布
    if "用例类型" in header_lower:
        idx = header_lower.index("用例类型")
        type_dist = {}
        for row in data:
            val = row[idx].strip() if idx < len(row) else ""
            if val:
                type_dist[val] = type_dist.get(val, 0) + 1
        summary["type_distribution"] = type_dist

    # 关联需求统计
    if "关联需求" in header_lower:
        idx = header_lower.index("关联需求")
        req_set = set()
        for row in data:
            val = row[idx].strip() if idx < len(row) else ""
            if val:
                req_set.add(val)
        summary["unique_requirements"] = sorted(req_set)
        summary["requirement_count"] = len(req_set)

    # 执行状态统计（执行记录文件）
    if "执行状态" in header_lower:
        idx = header_lower.index("执行状态")
        status_dist = {}
        for row in data:
            val = row[idx].strip() if idx < len(row) else ""
            if val:
                status_dist[val] = status_dist.get(val, 0) + 1
        summary["execution_status"] = status_dist

    return summary


def main():
    # Windows 控制台编码修复
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="通用 XLSX 读取工具")
    parser.add_argument("--file", required=True, help="XLSX 文件路径")
    parser.add_argument("--format", choices=["json", "summary"], default="json",
                        help="输出格式：json（完整数据）或 summary（统计摘要）")
    parser.add_argument("--sheet", default=None, help="指定 sheet 名称")
    parser.add_argument("--output", default=None, help="输出文件路径（默认 stdout）")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: file not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    headers, data = read_xlsx(file_path, args.sheet)

    if args.format == "json":
        result = to_json(headers, data)
    else:
        result = to_summary(headers, data, file_path)

    output_str = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(output_str, encoding="utf-8")
        print(f"Output saved to: {args.output}", file=sys.stderr)
    else:
        print(output_str)


if __name__ == "__main__":
    main()
