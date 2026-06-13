import sys
import os
import json

from parser import parse_workflow
from graph_builder import build_graph_list
from validators import (
    validate_edges,
    validate_references,
    validate_branch_references,
    validate_code_nodes,
    validate_toolbox_nodes,
    validate_llm_nodes,
)


def build_node_map(nodes: dict) -> dict:
    node_map = {}
    for node_id, node in nodes.items():
        entry = {
            'id': node.id,
            'type': node.type,
            'title': node.title,
            'variables': node.variables,
            'outputs': node.outputs,
            'code_language': node.code_language,
        }
        if node.type == 'code':
            entry['code'] = node.code
        if node.type == 'llm':
            entry['prompt'] = node.prompt
            entry['model_config'] = node.model_config
        if node.type == 'toolbox':
            entry['tool_parameters'] = node.tool_parameters
            entry['param_schemas'] = node.param_schemas
        if node.type == 'if-else':
            entry['cases'] = node.cases
        if node.type == 'answer':
            entry['answer'] = node.answer
        node_map[node_id] = entry
    return node_map


def run_all_validations(parsed: dict, graph_list: list) -> list:
    nodes = parsed['nodes']
    edges = parsed['edges']
    node_ids = set(nodes.keys())

    all_issues = []
    all_issues.extend(validate_edges(edges, node_ids))
    all_issues.extend(validate_references(nodes))

    branch_issues_dedup = {}
    for branch in graph_list:
        for issue in validate_branch_references(branch, parsed['nodes']):
            ref = issue.get('context', {}).get('reference', '')
            dedup_key = (issue['node_id'], ref)
            branch_id = issue.get('context', {}).get('branch_id', branch['branch_id'])
            if dedup_key not in branch_issues_dedup:
                issue['affected_branches'] = [branch_id]
                branch_issues_dedup[dedup_key] = issue
            else:
                branch_issues_dedup[dedup_key]['affected_branches'].append(branch_id)
    all_issues.extend(branch_issues_dedup.values())

    all_issues.extend(validate_code_nodes(nodes))
    all_issues.extend(validate_toolbox_nodes(nodes))
    all_issues.extend(validate_llm_nodes(nodes))

    return all_issues


def run_analysis(yml_path: str) -> dict:
    parsed = parse_workflow(yml_path)
    graph_list = build_graph_list(
        parsed['nodes'], parsed['edges'], parsed['adjacency'],
        edges_from_node=parsed.get('edges_from_node'),
    )
    issues = run_all_validations(parsed, graph_list)
    node_map = build_node_map(parsed['nodes'])

    print(f'\n=== 工作流分析: {yml_path} ===')
    print(f'节点总数: {len(parsed["nodes"])}')
    print(f'分支总数: {len(graph_list)}')
    print(f'发现问题: {len(issues)}')

    error_count = sum(1 for i in issues if i.get('severity') == 'error')
    warning_count = sum(1 for i in issues if i.get('severity') == 'warning')
    info_count = sum(1 for i in issues if i.get('severity') == 'info')
    print(f'  错误: {error_count}, 警告: {warning_count}, 待审查: {info_count}')

    return {
        'file': yml_path,
        'nodeMap': node_map,
        'graphList': graph_list,
        'adjacency': parsed['adjacency'],
        'issues': issues,
    }


def run_analysis_cli():
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass

    if len(sys.argv) < 2:
        print('用法: run.py analyze <yml文件或目录> [--out <目录>]')
        sys.exit(1)

    args = sys.argv[1:]
    out_override = None
    if '--out' in args:
        idx = args.index('--out')
        out_override = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    path = args[0]
    yml_files = []

    if os.path.isdir(path):
        for f in os.listdir(path):
            if f.endswith('.yml') and not f.endswith('-new.yml'):
                yml_files.append(os.path.join(path, f))
    elif os.path.isfile(path) and path.endswith('.yml'):
        yml_files.append(path)
    else:
        print(f'无效路径: {path}')
        sys.exit(1)

    for yml_file in yml_files:
        base_name = os.path.splitext(os.path.basename(yml_file))[0]
        if out_override:
            output_dir = out_override
        else:
            output_dir = os.path.join('outputs', base_name)
            output_dir = _resolve_conflict_dir(output_dir, yml_file)

        os.makedirs(output_dir, exist_ok=True)
        analysis = run_analysis(yml_file)
        output_path = os.path.join(output_dir, 'analysis.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)

        print(f'\n分析报告已保存: {output_path}')


def _resolve_conflict_dir(base_dir: str, yml_file: str) -> str:
    """若 base_dir 已存在且对应的 analysis.json 来自不同 yml，追加 -2、-3 后缀。"""
    if not os.path.exists(base_dir):
        return base_dir

    existing_analysis = os.path.join(base_dir, 'analysis.json')
    if os.path.exists(existing_analysis):
        try:
            with open(existing_analysis, 'r', encoding='utf-8') as f:
                existing_file = json.load(f).get('file', '')
            if os.path.abspath(existing_file) == os.path.abspath(yml_file):
                return base_dir
        except Exception:
            pass

    i = 2
    while True:
        candidate = f'{base_dir}-{i}'
        if not os.path.exists(candidate):
            return candidate
        try:
            with open(os.path.join(candidate, 'analysis.json'), 'r', encoding='utf-8') as f:
                existing_file = json.load(f).get('file', '')
            if os.path.abspath(existing_file) == os.path.abspath(yml_file):
                return candidate
        except Exception:
            pass
        i += 1
