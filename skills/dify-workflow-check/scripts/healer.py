import yaml
import copy
import json
import sys
import os


def _replace_reference_in_text(text: str, original: str, fixed: str) -> str:
    if not text or not isinstance(text, str):
        return text
    return text.replace(original, fixed)


def _replace_reference_in_dict(data: dict, original: str, fixed: str) -> dict:
    if not isinstance(data, dict):
        return data
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = _replace_reference_in_text(value, original, fixed)
        elif isinstance(value, dict):
            result[key] = _replace_reference_in_dict(value, original, fixed)
        elif isinstance(value, list):
            result[key] = _replace_reference_in_list(value, original, fixed)
        else:
            result[key] = value
    return result


def _replace_reference_in_list(data: list, original: str, fixed: str) -> list:
    if not isinstance(data, list):
        return data
    result = []
    for item in data:
        if isinstance(item, str):
            result.append(_replace_reference_in_text(item, original, fixed))
        elif isinstance(item, dict):
            result.append(_replace_reference_in_dict(item, original, fixed))
        elif isinstance(item, list):
            result.append(_replace_reference_in_list(item, original, fixed))
        else:
            result.append(item)
    return result


def _apply_reference_correction(node_data: dict, fix: dict):
    original = fix.get('original', '')
    fixed = fix.get('fixed', '')
    location = fix.get('location', '')
    if not original or not fixed:
        return

    if location in ['prompt', 'all']:
        if 'prompt_template' in node_data:
            node_data['prompt_template'] = _replace_reference_in_list(
                node_data['prompt_template'], original, fixed)

    if location in ['answer', 'all']:
        if 'answer' in node_data and isinstance(node_data['answer'], str):
            node_data['answer'] = _replace_reference_in_text(
                node_data['answer'], original, fixed)

    if location in ['tool_parameters', 'all']:
        if 'tool_parameters' in node_data:
            node_data['tool_parameters'] = _replace_reference_in_dict(
                node_data['tool_parameters'], original, fixed)


def apply_fixes(yml_path: str, fixes_data: dict, output_path: str) -> dict:
    from model_registry import resolve_model
    from issue_types import FixType

    with open(yml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    data = copy.deepcopy(data)
    nodes_list = data['workflow']['graph']['nodes']
    node_index = {str(n['id']): i for i, n in enumerate(nodes_list)}

    applied_fixes = []
    skipped_fixes = []
    failed_fixes = []

    for fix in fixes_data.get('fixes', []):
        node_id = fix.get('node_id', '')
        fix_type = fix.get('fix_type', '')

        if node_id not in node_index:
            failed_fixes.append({**fix, 'reason': f'node_id {node_id} 不存在于 yml'})
            continue

        node_data = nodes_list[node_index[node_id]]['data']

        if fix_type == FixType.CODE_REWRITE and 'fixed_code' in fix:
            node_data['code'] = fix['fixed_code']
            applied_fixes.append(fix)
        elif fix_type == FixType.PROMPT_OPTIMIZATION and 'fixed_prompt' in fix:
            prompt_list = node_data.get('prompt_template', [])
            if len(prompt_list) > 1:
                skipped_fixes.append({**fix, 'reason': f'prompt_template 有 {len(prompt_list)} 条，多角色 prompt 不自动覆盖'})
            elif prompt_list:
                prompt_list[0]['text'] = fix['fixed_prompt']
                applied_fixes.append(fix)
            else:
                failed_fixes.append({**fix, 'reason': 'prompt_template 为空'})
        elif fix_type == FixType.MODEL_CORRECTION and 'fixed_model_name' in fix:
            cfg = resolve_model(fix['fixed_model_name'])
            if cfg is None:
                failed_fixes.append({**fix, 'reason': f'未知模型 {fix["fixed_model_name"]}，请检查 model_registry'})
            else:
                node_data['model'] = dict(cfg)
                applied_fixes.append(fix)
        elif fix_type == FixType.REFERENCE_CORRECTION:
            _apply_reference_correction(node_data, fix)
            applied_fixes.append(fix)
        elif fix_type == FixType.OUTPUT_FIX and 'fixed_outputs' in fix:
            node_data['outputs'] = fix['fixed_outputs']
            applied_fixes.append(fix)
        else:
            failed_fixes.append({**fix, 'reason': f'未知 fix_type 或缺少必填字段: {fix_type}'})

    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    return {
        'applied_fixes': applied_fixes,
        'skipped_fixes': skipped_fixes,
        'failed_fixes': failed_fixes,
    }


def verify_output(yml_path: str, original_issues: list) -> dict:
    """重跑解析 + 静态校验，对比修复后是否引入新问题。"""
    try:
        from parser import parse_workflow
        from graph_builder import build_graph_list
        from main import run_all_validations
    except Exception as e:
        return {'parseable': False, 'error': f'import failure: {e}', 'newly_introduced_issues': []}

    try:
        parsed = parse_workflow(yml_path)
    except Exception as e:
        return {'parseable': False, 'error': str(e), 'newly_introduced_issues': []}

    graph_list = build_graph_list(
        parsed['nodes'], parsed['edges'], parsed['adjacency'],
        edges_from_node=parsed.get('edges_from_node'),
    )
    new_issues = run_all_validations(parsed, graph_list)

    orig_ids = {i['issue_id'] for i in original_issues}
    introduced = [i for i in new_issues if i['issue_id'] not in orig_ids]
    return {
        'parseable': True,
        'node_count': len(parsed['nodes']),
        'edge_count': len(parsed['edges']),
        'remaining_issue_count': len(new_issues),
        'newly_introduced_issues': introduced,
    }


def run_heal_cli():
    if len(sys.argv) != 4:
        print('用法: run.py heal <yml文件> <fixes.json> <输出路径>')
        sys.exit(1)

    yml_path, fixes_json_path, output_path = sys.argv[1], sys.argv[2], sys.argv[3]
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(fixes_json_path, 'r', encoding='utf-8') as f:
        fixes_data = json.load(f)

    result = apply_fixes(yml_path, fixes_data, output_path)
    print(f'修复已应用，输出: {output_path}')
    print(f'  应用: {len(result["applied_fixes"])} 条')
    print(f'  跳过: {len(result["skipped_fixes"])} 条')
    print(f'  失败: {len(result["failed_fixes"])} 条')
    for item in result['skipped_fixes']:
        print(f'  [跳过] {item.get("node_id")}: {item.get("reason")}')
    for item in result['failed_fixes']:
        print(f'  [失败] {item.get("node_id")}: {item.get("reason")}')

    original_issues = []
    analysis_path = os.path.join(output_dir, 'analysis.json') if output_dir else 'analysis.json'
    if os.path.exists(analysis_path):
        with open(analysis_path, 'r', encoding='utf-8') as f:
            original_issues = json.load(f).get('issues', [])

    verification = verify_output(output_path, original_issues)
    verif_path = os.path.join(output_dir, 'heal-verification.json') if output_dir else 'heal-verification.json'
    with open(verif_path, 'w', encoding='utf-8') as f:
        json.dump(verification, f, ensure_ascii=False, indent=2)
    print(f'验证报告: {verif_path}')

    if not verification['parseable']:
        print(f'  [警告] 修复后 yml 无法解析: {verification.get("error", "")}')
    elif verification.get('newly_introduced_issues'):
        n = len(verification['newly_introduced_issues'])
        print(f'  [警告] 修复反向引入 {n} 个新问题')