import ast
import re
from typing import Dict, List, Set

from issue_types import IssueType
from model_registry import TARGET_MODEL

VAR_REF_PATTERN = re.compile(r'\{\{#([^.]+)\.([^#]+)#\}\}')
SYSTEM_PREFIXES = {'sys'}

def validate_edges(edges: list, node_ids: set) -> list:
    issues = []
    for edge in edges:
        if edge.source not in node_ids:
            issues.append({
                'issue_id': f'edge_{edge.id}_source',
                'node_id': edge.source,
                'type': IssueType.EDGE_INVALID_SOURCE,
                'severity': 'error',
                'message': f'Edge {edge.id} 的 source 节点 {edge.source} 不存在',
                'auto_fixable': False,
            })
        if edge.target not in node_ids:
            issues.append({
                'issue_id': f'edge_{edge.id}_target',
                'node_id': edge.target,
                'type': IssueType.EDGE_INVALID_TARGET,
                'severity': 'error',
                'message': f'Edge {edge.id} 的 target 节点 {edge.target} 不存在',
                'auto_fixable': False,
            })
    return issues


def validate_references(nodes: dict) -> list:
    issues = []
    node_ids = set(nodes.keys())

    for node_id, node in nodes.items():
        if node.tool_parameters:
            for param_key, param_value in node.tool_parameters.items():
                if isinstance(param_value, dict) and 'value' in param_value:
                    value = param_value['value']
                    if isinstance(value, str):
                        for match in VAR_REF_PATTERN.finditer(value):
                            ref_node_id = match.group(1)
                            if ref_node_id in SYSTEM_PREFIXES:
                                continue
                            if ref_node_id not in node_ids:
                                issues.append({
                                    'issue_id': f'ref_{node_id}_{ref_node_id}_{match.group(2)}',
                                    'node_id': node_id,
                                    'type': IssueType.INVALID_REFERENCE,
                                    'severity': 'error',
                                    'message': f'引用节点 {ref_node_id} 不存在',
                                    'context': {
                                        'reference': match.group(0),
                                        'location': f'tool_parameters.{param_key}'
                                    },
                                    'auto_fixable': True,
                                })

        if node.answer and isinstance(node.answer, str):
            for match in VAR_REF_PATTERN.finditer(node.answer):
                ref_node_id = match.group(1)
                if ref_node_id in SYSTEM_PREFIXES:
                    continue
                if ref_node_id not in node_ids:
                    issues.append({
                        'issue_id': f'ref_{node_id}_{ref_node_id}_{match.group(2)}',
                        'node_id': node_id,
                        'type': IssueType.INVALID_REFERENCE,
                        'severity': 'error',
                        'message': f'引用节点 {ref_node_id} 不存在',
                        'context': {'reference': match.group(0), 'location': 'answer'},
                        'auto_fixable': True,
                    })

        if node.prompt:
            for idx, prompt_item in enumerate(node.prompt):
                if isinstance(prompt_item, dict) and 'text' in prompt_item:
                    text = prompt_item['text']
                    if isinstance(text, str):
                        for match in VAR_REF_PATTERN.finditer(text):
                            ref_node_id = match.group(1)
                            if ref_node_id in SYSTEM_PREFIXES:
                                continue
                            if ref_node_id not in node_ids:
                                issues.append({
                                    'issue_id': f'ref_{node_id}_{ref_node_id}_{match.group(2)}',
                                    'node_id': node_id,
                                    'type': IssueType.INVALID_REFERENCE,
                                    'severity': 'error',
                                    'message': f'引用节点 {ref_node_id} 不存在',
                                    'context': {
                                        'reference': match.group(0),
                                        'location': f'prompt[{idx}]'
                                    },
                                    'auto_fixable': True,
                                })

        if node.cases:
            for case_idx, case in enumerate(node.cases):
                if 'conditions' in case:
                    for cond_idx, condition in enumerate(case['conditions']):
                        if 'variable_selector' in condition:
                            var_selector = condition['variable_selector']
                            if isinstance(var_selector, list) and len(var_selector) >= 2:
                                ref_node_id = var_selector[0]
                                ref_var = var_selector[1]
                                if ref_node_id in SYSTEM_PREFIXES:
                                    continue
                                if ref_node_id not in node_ids:
                                    issues.append({
                                        'issue_id': f'ref_{node_id}_{ref_node_id}_{ref_var}',
                                        'node_id': node_id,
                                        'type': IssueType.INVALID_REFERENCE,
                                        'severity': 'error',
                                        'message': f'引用节点 {ref_node_id} 不存在',
                                        'context': {
                                            'reference': f'{{{{#{ref_node_id}.{ref_var}#}}}}',
                                            'location': f'cases[{case_idx}].conditions[{cond_idx}]'
                                        },
                                        'auto_fixable': True,
                                    })

    return issues


def _get_node_output_keys(node) -> Set[str]:
    if node.type == 'start':
        return {var['variable'] for var in node.variables if 'variable' in var}
    elif node.type == 'code':
        return set(node.outputs.keys()) if node.outputs else set()
    elif node.type == 'llm':
        return {'text'}
    elif node.type == 'toolbox':
        return {'data', 'errorCode', 'bean'}
    elif node.type == 'parameter-extractor':
        raw = (node.raw_data or {}).get('data', {}) or {}
        params = raw.get('parameters', []) or []
        keys = {p.get('name') for p in params if p.get('name')}
        keys.update({'__is_success', '__reason'})
        return keys
    elif node.type == 'question-classifier':
        return {'class_name'}
    return set()


def validate_branch_references(branch: dict, nodes: dict) -> list:
    issues = []
    available_outputs = {}

    for node_id in branch['nodes']:
        if node_id not in nodes:
            continue

        node = nodes[node_id]
        references = _extract_all_references(node)

        for ref in references:
            ref_node_id = ref['node_id']
            if ref_node_id in SYSTEM_PREFIXES:
                continue
            if ref_node_id not in available_outputs:
                issues.append({
                    'issue_id': f'branch_ref_{node_id}_{ref_node_id}_{ref["var_name"]}',
                    'node_id': node_id,
                    'type': IssueType.REFERENCE_NOT_IN_BRANCH,
                    'severity': 'error',
                    'message': f'引用节点 {ref_node_id} 不在当前分支的前驱节点中',
                    'context': {
                        'reference': f'{{{{#{ref_node_id}.{ref["var_name"]}#}}}}',
                        'location': ref['location'],
                        'branch_id': branch['branch_id']
                    },
                    'auto_fixable': False,
                })

        output_keys = _get_node_output_keys(node)
        if output_keys:
            available_outputs[node_id] = output_keys

    return issues


def _extract_all_references(node) -> List[Dict[str, str]]:
    references = []

    if node.tool_parameters:
        for param_key, param_value in node.tool_parameters.items():
            if isinstance(param_value, dict) and 'value' in param_value:
                value = param_value['value']
                if isinstance(value, str):
                    for match in VAR_REF_PATTERN.finditer(value):
                        references.append({
                            'node_id': match.group(1),
                            'var_name': match.group(2),
                            'location': f'tool_parameters.{param_key}'
                        })

    if node.answer and isinstance(node.answer, str):
        for match in VAR_REF_PATTERN.finditer(node.answer):
            references.append({
                'node_id': match.group(1),
                'var_name': match.group(2),
                'location': 'answer'
            })

    if node.prompt:
        for idx, prompt_item in enumerate(node.prompt):
            if isinstance(prompt_item, dict) and 'text' in prompt_item:
                text = prompt_item['text']
                if isinstance(text, str):
                    for match in VAR_REF_PATTERN.finditer(text):
                        references.append({
                            'node_id': match.group(1),
                            'var_name': match.group(2),
                            'location': f'prompt[{idx}]'
                        })

    if node.cases:
        for case_idx, case in enumerate(node.cases):
            if 'conditions' in case:
                for cond_idx, condition in enumerate(case['conditions']):
                    if 'variable_selector' in condition:
                        var_selector = condition['variable_selector']
                        if isinstance(var_selector, list) and len(var_selector) >= 2:
                            references.append({
                                'node_id': var_selector[0],
                                'var_name': var_selector[1],
                                'location': f'cases[{case_idx}].conditions[{cond_idx}]'
                            })

    return references




def validate_code_nodes(nodes: dict) -> list:
    issues = []
    for node_id, node in nodes.items():
        if node.type != 'code':
            continue

        if node.code_language == 'python3' and node.code:
            syntax_issue = _check_syntax(node)
            if syntax_issue:
                issues.append(syntax_issue)

        if node.code:
            param_issue = _check_params(node)
            if param_issue:
                issues.append(param_issue)

        if node.code and node.outputs:
            output_issue = _check_outputs(node)
            if output_issue:
                issues.append(output_issue)

        issues.append({
            'issue_id': f'review_{node_id}',
            'node_id': node_id,
            'type': IssueType.CODE_REVIEW_REQUIRED,
            'severity': 'info',
            'message': 'code 节点需要 Agent 审查和重写',
            'auto_fixable': False,
        })

    return issues


def _check_syntax(node) -> dict | None:
    try:
        ast.parse(node.code)
        return None
    except SyntaxError as e:
        msg = str(e.msg) if e.msg else str(e)
        return {
            'issue_id': f'syntax_{node.id}',
            'node_id': node.id,
            'type': IssueType.SYNTAX_ERROR,
            'severity': 'error',
            'message': f'Python 语法错误: {msg}',
            'auto_fixable': True,
        }


def _get_python_params(code: str) -> list:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'main':
            return [arg.arg for arg in node.args.args]
    return []


def _get_js_params(code: str) -> list:
    match = re.search(r'function\s+main\s*\(\s*\{([^}]*)\}', code)
    if not match:
        return []
    params_str = match.group(1)
    return [p.strip() for p in params_str.split(',') if p.strip()]


def _get_js_return_keys(code: str) -> set:
    m = re.search(r'return\s*\{', code, re.DOTALL)
    if not m:
        return set()

    start = m.end()
    depth = 1
    i = start
    while i < len(code) and depth > 0:
        if code[i] == '{':
            depth += 1
        elif code[i] == '}':
            depth -= 1
        i += 1

    if depth != 0:
        return set()

    body = code[start:i - 1]
    cleaned = re.sub(r'\{[^}]*\}', '""', body)
    cleaned = re.sub(r'"[^"]*"', '""', cleaned)
    cleaned = re.sub(r"'[^']*'", '""', cleaned)
    cleaned = re.sub(r'`[^`]*`', '""', cleaned)

    keys = set()
    for part in cleaned.split(','):
        part = part.strip()
        if not part:
            continue
        if ':' in part:
            key = part.split(':')[0].strip()
        else:
            key = part.strip()
        if re.match(r'^[a-zA-Z_$][a-zA-Z0-9_$]*$', key):
            keys.add(key)
    return keys


def _get_python_return_keys(code: str) -> set:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    keys = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and node.value:
            if isinstance(node.value, ast.Dict):
                for key in node.value.keys:
                    if isinstance(key, ast.Constant) and isinstance(key.value, str):
                        keys.add(key.value)
    return keys


def _check_params(node) -> dict | None:
    var_names = sorted([v['variable'] for v in node.variables if 'variable' in v])
    if not var_names:
        return None

    if node.code_language == 'python3':
        params = sorted(_get_python_params(node.code))
    elif node.code_language == 'javascript':
        params = sorted(_get_js_params(node.code))
    else:
        return None

    if not params:
        return None

    if params != var_names:
        return {
            'issue_id': f'param_{node.id}',
            'node_id': node.id,
            'type': IssueType.PARAM_MISMATCH,
            'severity': 'warning',
            'message': f'函数参数 {params} 与输入变量 {var_names} 不匹配',
            'context': {'func_params': params, 'variables': var_names},
            'auto_fixable': True,
        }
    return None


def _check_outputs(node) -> dict | None:
    if not node.outputs:
        return None

    if node.code_language == 'python3':
        return_keys = _get_python_return_keys(node.code)
    elif node.code_language == 'javascript':
        return_keys = _get_js_return_keys(node.code)
    else:
        return None

    if not return_keys:
        return None

    output_keys = set(node.outputs.keys())
    if return_keys != output_keys:
        return {
            'issue_id': f'output_{node.id}',
            'node_id': node.id,
            'type': IssueType.OUTPUT_KEY_MISMATCH,
            'severity': 'warning',
            'message': f'return 键 {sorted(return_keys)} 与 outputs 定义 {sorted(output_keys)} 不匹配',
            'context': {
                'output_keys': sorted(output_keys),
                'return_keys': sorted(return_keys),
            },
            'auto_fixable': True,
        }
    return None


def validate_toolbox_nodes(nodes: dict) -> list:
    issues = []
    for node_id, node in nodes.items():
        if node.type != 'toolbox':
            continue

        required_params = [
            (s.get('variable') or s.get('name'), s.get('name', s.get('variable', '')))
            for s in node.param_schemas if s.get('required', False)
        ]

        for param_key, param_label in required_params:
            param_data = node.tool_parameters.get(param_key)
            if not param_data or param_data.get('value') in (None, ''):
                issues.append({
                    'issue_id': f'toolbox_req_{node_id}_{param_key}',
                    'node_id': node_id,
                    'type': IssueType.TOOLBOX_MISSING_REQUIRED,
                    'severity': 'error',
                    'message': f'必填参数 {param_label} 未填写',
                    'context': {'param_name': param_label, 'param_key': param_key},
                    'auto_fixable': True,
                })

    return issues




def validate_llm_nodes(nodes: dict) -> list:
    issues = []
    for node_id, node in nodes.items():
        if node.type != 'llm':
            continue

        model_name = node.model_config.get('name', '')
        if model_name and model_name != TARGET_MODEL['name']:
            issues.append({
                'issue_id': f'model_{node_id}',
                'node_id': node_id,
                'type': IssueType.LLM_MODEL_INCORRECT,
                'severity': 'warning',
                'message': f'模型名称 "{model_name}" 不是指定模型',
                'context': {
                    'current_model': model_name,
                    'expected_model': TARGET_MODEL['name'],
                },
                'auto_fixable': True,
            })

        if node.prompt:
            issues.append({
                'issue_id': f'llm_review_{node_id}',
                'node_id': node_id,
                'type': IssueType.LLM_REVIEW_REQUIRED,
                'severity': 'info',
                'message': 'llm 节点需要 Agent 优化提示词',
                'auto_fixable': False,
            })

    return issues

