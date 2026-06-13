import json
import os
import sys
from typing import Any

from graph_visualizer import generate_mermaid_skeleton, generate_branch_summary_table, export_branches_detail
from test_data_generator import generate_test_scenarios


def generate_report(analysis: dict, fixes: dict, test_values: list = None) -> str:
    nodes = analysis.get('nodeMap', {})
    issues = analysis.get('issues', [])
    branches = analysis.get('graphList', [])
    fix_list = fixes.get('fixes', [])
    unfixed = fixes.get('unfixed_issues', [])

    lines = ['# Dify 工作流检查报告\n']

    lines.append('## 概览\n')
    lines.append(f'- 节点数: {len(nodes)}')
    lines.append(f'- 分支数: {len(branches)}')
    lines.append(f'- 发现问题: {len(issues)}')
    lines.append(f'- 已修复: {len(fix_list)}')
    lines.append(f'- 未修复: {len(unfixed)}\n')

    if issues:
        lines.append('## 问题列表\n')
        lines.append('| 节点ID | 节点名称 | 严重度 | 类型 | 描述 |')
        lines.append('|--------|----------|--------|------|------|')
        for issue in issues:
            nid = issue.get('node_id', '')
            node_id = nid[:8]
            title = nodes.get(nid, {}).get('title', '') or '-'
            severity = issue.get('severity', 'info')
            itype = issue.get('type', '')
            msg = issue.get('message', '')
            lines.append(f'| {node_id} | {title} | {severity} | {itype} | {msg} |')
        lines.append('')

    if fix_list:
        lines.append('## 修复内容\n')
        for i, fix in enumerate(fix_list, 1):
            nid = fix.get('node_id', '')
            node_id = nid[:8]
            title = nodes.get(nid, {}).get('title', '') or '-'
            fix_type = fix.get('fix_type', '')
            reason = fix.get('reason', '')
            lines.append(f'{i}. **{node_id}** ({title}) [{fix_type}] {reason}')
        lines.append('')

    if unfixed:
        lines.append('## 未修复问题\n')
        for issue in unfixed:
            lines.append(f'- {issue.get("message", "")}')
        lines.append('')

    lines.append('## 分支结构\n')
    lines.append(generate_branch_summary_table(branches, nodes))
    lines.append('')

    mermaid = generate_mermaid_skeleton(nodes, analysis.get('adjacency', {}), branches)
    if mermaid:
        lines.append('```mermaid')
        lines.append(mermaid)
        lines.append('```\n')

    if test_values:
        lines.append('## 测试入参推荐\n')
        lines.append('| 分支ID | 场景 | sys.query | start_inputs (摘要) | 推导逻辑 |')
        lines.append('|--------|------|-----------|---------------------|----------|')
        for tv in test_values:
            bid = tv.get('branch_id', '')
            scen = (tv.get('scenario', '') or '').replace('|', '\\|')
            sq = (tv.get('sys_query', '') or '').replace('|', '\\|')
            si = tv.get('start_inputs', {})
            si_summary = json.dumps(si, ensure_ascii=False)
            if len(si_summary) > 200:
                si_summary = si_summary[:200] + '...'
            si_summary = si_summary.replace('|', '\\|')
            reasoning = (tv.get('reasoning', '') or '').replace('|', '\\|')
            lines.append(f'| {bid} | {scen} | {sq} | `{si_summary}` | {reasoning} |')
        lines.append('')
        lines.append('完整入参与执行路径见 `test-values.json`。\n')

    return '\n'.join(lines)


def run_report(analysis_path: str, fixes_path: str, output_dir: str):
    with open(analysis_path, 'r', encoding='utf-8') as f:
        analysis = json.load(f)
    with open(fixes_path, 'r', encoding='utf-8') as f:
        fixes = json.load(f)

    os.makedirs(output_dir, exist_ok=True)

    test_values = None
    test_values_path = os.path.join(output_dir, 'test-values.json')
    if os.path.exists(test_values_path):
        try:
            with open(test_values_path, 'r', encoding='utf-8') as f:
                test_values = json.load(f)
        except Exception:
            test_values = None

    report_md = generate_report(analysis, fixes, test_values)
    report_path = os.path.join(output_dir, 'report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_md)

    nodes = analysis.get('nodeMap', {})
    branches = analysis.get('graphList', [])
    branches_detail = export_branches_detail(branches, nodes)
    detail_path = os.path.join(output_dir, 'branches-detail.json')
    with open(detail_path, 'w', encoding='utf-8') as f:
        json.dump(branches_detail, f, ensure_ascii=False, indent=2)

    test_data = generate_test_scenarios(analysis)
    deriv_path = os.path.join(output_dir, 'test-derivation.json')
    with open(deriv_path, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)

    print(f"报告已生成:")
    print(f"  - {report_path}")
    print(f"  - {detail_path}")
    print(f"  - {deriv_path}")


def run_report_cli():
    if len(sys.argv) < 4:
        print("用法: run.py report <analysis.json> <fixes.json> <输出目录>")
        sys.exit(1)
    run_report(sys.argv[1], sys.argv[2], sys.argv[3])


if __name__ == '__main__':
    run_report_cli()
