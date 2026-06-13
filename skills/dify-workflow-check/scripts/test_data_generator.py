import re
import json
from typing import Any

VALUABLE_TYPES = {'code', 'llm', 'toolbox'}
ALL_TYPES = {'start', 'code', 'llm', 'toolbox', 'if-else', 'answer'}


def score_branch(branch: dict, nodes: dict) -> float:
    node_ids = branch.get('nodes', [])
    length = len(node_ids)
    types_in_branch = set()
    has_valuable = False
    for nid in node_ids:
        node = nodes.get(nid)
        if node:
            ntype = node.type if hasattr(node, 'type') else node.get('type', '')
            types_in_branch.add(ntype)
            if ntype in VALUABLE_TYPES:
                has_valuable = True

    diversity = len(types_in_branch) / len(ALL_TYPES) if ALL_TYPES else 0
    bonus = 1.5 if has_valuable else 1.0
    return length * diversity * bonus


def _branch_similarity(branch_a: dict, branch_b: dict) -> float:
    nodes_a = set(branch_a.get('nodes', []))
    nodes_b = set(branch_b.get('nodes', []))
    if not nodes_a and not nodes_b:
        return 1.0
    union = nodes_a | nodes_b
    return len(nodes_a & nodes_b) / len(union) if union else 0.0


def select_representative_branches(
    branches: list, nodes: dict, top_n: int = 5
) -> list:
    scored = [(score_branch(b, nodes), b) for b in branches]
    scored.sort(key=lambda x: x[0], reverse=True)

    selected = []
    for score, branch in scored:
        if len(selected) >= top_n:
            break
        if not any(_branch_similarity(branch, e) > 0.7 for e in selected):
            selected.append(branch)
    return selected


def derive_test_values(branch: dict, nodes: dict) -> list:
    node_ids = branch.get('nodes', [])
    start_node = None
    start_id = None
    for nid in node_ids:
        node = nodes.get(nid)
        if node:
            ntype = node.type if hasattr(node, 'type') else node.get('type', '')
            if ntype == 'start':
                start_node = node
                start_id = nid
                break

    if not start_node:
        return []

    start_vars = start_node.variables if hasattr(start_node, 'variables') else start_node.get('variables', [])
    if not start_vars:
        return []

    var_map = {}
    for v in start_vars:
        vname = v.get('variable', v.get('name', ''))
        vtype = v.get('type', 'string')
        if vname:
            var_map[vname] = vtype

    direct_constraints = {}
    indirect_constraints = []

    for nid in node_ids:
        node = nodes.get(nid)
        if not node:
            continue
        ntype = node.type if hasattr(node, 'type') else node.get('type', '')
        if ntype != 'if-else':
            continue
        cases = node.cases if hasattr(node, 'cases') else node.get('cases', [])
        for case in cases:
            for cond in case.get('conditions', []):
                var_selector = cond.get('variable_selector', [])
                operator = cond.get('comparison_operator', '')
                value = cond.get('value', '')
                if len(var_selector) < 2:
                    continue
                ref_node_id = str(var_selector[0])
                ref_var = var_selector[1]

                if ref_node_id == start_id:
                    base_var = ref_var.split('.')[0] if '.' in ref_var else ref_var
                    if base_var in var_map and value:
                        key = ref_var
                        if key not in direct_constraints:
                            direct_constraints[key] = {"value": str(value), "operator": operator}
                else:
                    ref_node = nodes.get(ref_node_id)
                    if ref_node:
                        indirect_constraints.append({
                            "ref_node_id": ref_node_id,
                            "ref_var": ref_var,
                            "operator": operator,
                            "value": str(value) if value else '',
                        })

    result = {}
    for var_name, vtype in var_map.items():
        if var_name in direct_constraints:
            c = direct_constraints[var_name]
            result[var_name] = _generate_value(c['value'], c['operator'], vtype)
        else:
            result[var_name] = _default_value(vtype)

    return [result] if result else []


def _generate_value(value: str, operator: str, vtype: str) -> Any:
    if operator in ('eq', 'is', 'contains', '=='):
        return value
    if operator in ('not_eq', 'is_not', '!='):
        if vtype == 'number':
            try:
                return float(value) + 1
            except ValueError:
                return 0
        return value + '_alt'
    if operator in ('gt', '>'):
        try:
            return float(value) + 1
        except ValueError:
            return value
    if operator in ('lt', '<'):
        try:
            return float(value) - 1
        except ValueError:
            return value
    if operator in ('gte', '>='):
        try:
            return float(value)
        except ValueError:
            return value
    if operator in ('lte', '<='):
        try:
            return float(value)
        except ValueError:
            return value
    if operator in ('empty', 'is_empty'):
        return ''
    if operator in ('not_empty', 'is_not_empty'):
        return value if value else 'test_value'
    return value


def _default_value(vtype: str) -> Any:
    defaults = {
        'string': 'test_input',
        'number': 1,
        'select': 'option_1',
        'paragraph': 'test paragraph content',
        'array[string]': ['item1'],
        'array[number]': [1],
    }
    return defaults.get(vtype, 'test')


def collect_derivation_context(branch: dict, nodes: dict) -> dict:
    node_ids = branch.get('nodes', [])
    chain = []
    for nid in node_ids:
        node = nodes.get(nid)
        if not node:
            continue
        ntype = node.type if hasattr(node, 'type') else node.get('type', '')
        title = node.title if hasattr(node, 'title') else node.get('title', '')
        entry = {"node_id": nid, "type": ntype, "title": title}
        if ntype == 'if-else':
            cases = node.cases if hasattr(node, 'cases') else node.get('cases', [])
            entry["conditions"] = cases
        elif ntype == 'code':
            code = node.code if hasattr(node, 'code') else node.get('code', '')
            outputs = node.outputs if hasattr(node, 'outputs') else node.get('outputs', {})
            entry["code"] = code
            entry["outputs"] = outputs
        elif ntype == 'start':
            variables = node.variables if hasattr(node, 'variables') else node.get('variables', [])
            entry["variables"] = variables
        chain.append(entry)
    return {
        "branch_id": branch.get('id', ''),
        "branch_description": branch.get('description', ''),
        "chain": chain,
    }


def generate_test_scenarios(analysis: dict) -> dict:
    nodes = analysis.get('nodeMap', {})
    branches = analysis.get('graphList', [])

    selected = select_representative_branches(branches, nodes)
    scenarios = []
    derivations = []

    for branch in selected:
        test_values = derive_test_values(branch, nodes)
        context = collect_derivation_context(branch, nodes)
        derivations.append(context)

        if test_values:
            scenarios.append({
                "branch_id": branch.get('id', ''),
                "description": branch.get('description', ''),
                "start_inputs": test_values[0],
                "reasoning": "基于 if-else 条件约束自动推导",
            })

    return {
        "scenarios": scenarios,
        "derivations": derivations,
        "branch_count": len(branches),
        "selected_count": len(selected),
    }


def run_generate_cli():
    import sys
    if len(sys.argv) < 3:
        print("用法: python -m dify_checker.test_data_generator <analysis.json> <output.json>")
        sys.exit(1)

    analysis_path = sys.argv[1]
    output_path = sys.argv[2]

    with open(analysis_path, 'r', encoding='utf-8') as f:
        analysis = json.load(f)

    result = generate_test_scenarios(analysis)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"生成 {len(result['scenarios'])} 个测试场景 → {output_path}")


if __name__ == '__main__':
    run_generate_cli()
