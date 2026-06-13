import json
import os
import sys

from filelock import FileLock


def init_fixes(fixes_path: str):
    """创建空骨架（覆盖式）。Phase 2 开始前调用一次。"""
    parent = os.path.dirname(fixes_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(fixes_path, 'w', encoding='utf-8') as f:
        json.dump({'fixes': [], 'unfixed_issues': []}, f, ensure_ascii=False, indent=2)


def append_fixes(fixes_path: str, new_fixes: list, source: str) -> int:
    """原子追加，返回新增条数。dedup key = (node_id, fix_type)。"""
    lock_path = fixes_path + '.lock'
    with FileLock(lock_path, timeout=30):
        if os.path.exists(fixes_path):
            with open(fixes_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {'fixes': [], 'unfixed_issues': []}

        existing_keys = {(f.get('node_id'), f.get('fix_type')) for f in data['fixes']}
        added = 0
        for fix in new_fixes:
            key = (fix.get('node_id'), fix.get('fix_type'))
            if key in existing_keys:
                continue
            fix['source'] = source
            data['fixes'].append(fix)
            existing_keys.add(key)
            added += 1

        tmp = fixes_path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, fixes_path)
    return added


def validate_fixes(fixes_path: str) -> list:
    """schema 校验，返回错误信息列表。空列表表示合法。"""
    from issue_types import FixType
    valid_types = {
        FixType.CODE_REWRITE, FixType.PROMPT_OPTIMIZATION,
        FixType.MODEL_CORRECTION, FixType.REFERENCE_CORRECTION,
        FixType.OUTPUT_FIX,
    }
    required_per_type = {
        FixType.CODE_REWRITE: {'fixed_code'},
        FixType.PROMPT_OPTIMIZATION: {'fixed_prompt'},
        FixType.MODEL_CORRECTION: {'fixed_model_name'},
        FixType.REFERENCE_CORRECTION: {'original', 'fixed', 'location'},
        FixType.OUTPUT_FIX: {'fixed_outputs'},
    }

    with open(fixes_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    errors = []
    for i, fix in enumerate(data.get('fixes', [])):
        if not fix.get('node_id'):
            errors.append(f'fix[{i}]: 缺 node_id')
            continue
        ftype = fix.get('fix_type')
        if ftype not in valid_types:
            errors.append(f'fix[{i}] node={fix.get("node_id")}: 未知 fix_type {ftype}')
            continue
        missing = required_per_type[ftype] - set(fix.keys())
        if missing:
            errors.append(f'fix[{i}] node={fix.get("node_id")} type={ftype}: 缺字段 {missing}')
    return errors


def run_init_fixes_cli():
    """run.py init_fixes <fixes.json>"""
    if len(sys.argv) != 2:
        print('用法: run.py init_fixes <fixes.json>')
        sys.exit(1)
    init_fixes(sys.argv[1])
    print(f'已初始化 {sys.argv[1]}')


def run_append_cli():
    """run.py append_fixes <fixes.json> <new_fixes.json> <source>"""
    if len(sys.argv) != 4:
        print('用法: run.py append_fixes <fixes.json> <new_fixes.json> <source>')
        sys.exit(1)
    fixes_path, new_path, source = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(new_path, 'r', encoding='utf-8') as f:
        new_fixes = json.load(f).get('fixes', [])
    added = append_fixes(fixes_path, new_fixes, source)
    print(f'追加 {added} 条修复到 {fixes_path}')


def run_validate_fixes_cli():
    """run.py validate_fixes <fixes.json>"""
    if len(sys.argv) != 2:
        print('用法: run.py validate_fixes <fixes.json>')
        sys.exit(1)
    errors = validate_fixes(sys.argv[1])
    if errors:
        print(f'fixes.json 校验失败 ({len(errors)} 条错误):')
        for e in errors:
            print(f'  - {e}')
        sys.exit(1)
    print('fixes.json 校验通过')
