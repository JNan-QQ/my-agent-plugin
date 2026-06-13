import json
import sys
import os

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass


def _load_analysis(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def list_nodes(analysis: dict):
    for nid, node in analysis.get('nodeMap', {}).items():
        print(f"{nid}\t{node.get('type','')}\t{node.get('title','')}")


def list_by_type(analysis: dict, node_type: str):
    for nid, node in analysis.get('nodeMap', {}).items():
        if node.get('type') == node_type:
            print(f"{nid}\t{node.get('title','')}")


def get_node(analysis: dict, node_id: str):
    node = analysis.get('nodeMap', {}).get(node_id)
    if node:
        print(json.dumps(node, ensure_ascii=False, indent=2))
    else:
        print(f"节点 {node_id} 不存在")


def get_code(analysis: dict, node_id: str):
    node = analysis.get('nodeMap', {}).get(node_id)
    if not node:
        print(f"节点 {node_id} 不存在")
        return
    code = node.get('code', '')
    if code:
        print(code)
    else:
        print(f"节点 {node_id} 无代码")


def get_inputs(analysis: dict, node_id: str):
    node = analysis.get('nodeMap', {}).get(node_id)
    if not node:
        print(f"节点 {node_id} 不存在")
        return
    print(json.dumps(node.get('variables', []), ensure_ascii=False, indent=2))


def get_outputs(analysis: dict, node_id: str):
    node = analysis.get('nodeMap', {}).get(node_id)
    if not node:
        print(f"节点 {node_id} 不存在")
        return
    print(json.dumps(node.get('outputs', {}), ensure_ascii=False, indent=2))


def get_prompt(analysis: dict, node_id: str):
    node = analysis.get('nodeMap', {}).get(node_id)
    if not node:
        print(f"节点 {node_id} 不存在")
        return
    prompt = node.get('prompt', [])
    if prompt:
        for item in prompt:
            if isinstance(item, dict) and 'text' in item:
                print(item['text'])
    else:
        print(f"节点 {node_id} 无提示词")


def list_derivation_branches(derivation_path: str):
    with open(derivation_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for item in data:
        bid = item.get('branch_id', '')
        ctx = item.get('derivation_context', {})
        chains = ctx.get('derivation_chains', [])
        start_vars = ctx.get('start_variables', [])
        print(f"{bid}\t链数:{len(chains)}\t起始变量:{len(start_vars)}")


def get_derivation_branch(derivation_path: str, branch_id: str):
    with open(derivation_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for item in data:
        if item.get('branch_id') == branch_id:
            print(json.dumps(item, ensure_ascii=False, indent=2))
            return
    print(f"分支 {branch_id} 不存在")


def get_derivation_chain(derivation_path: str, branch_id: str, chain_index: str):
    with open(derivation_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for item in data:
        if item.get('branch_id') == branch_id:
            chains = item.get('derivation_context', {}).get('derivation_chains', [])
            idx = int(chain_index)
            if 0 <= idx < len(chains):
                print(json.dumps(chains[idx], ensure_ascii=False, indent=2))
            else:
                print(f"索引 {idx} 超出范围 (共 {len(chains)} 条)")
            return
    print(f"分支 {branch_id} 不存在 (get_chain)")


def run_query_cli():
    if len(sys.argv) < 3:
        print('用法: run.py query <analysis.json> <command> [args...]')
        print('命令: list_nodes, list_by_type, get_node, get_code, get_inputs, get_outputs, get_prompt')
        print('      list_derivations, get_derivation, get_chain')
        sys.exit(1)

    analysis_path = sys.argv[1]
    command = sys.argv[2]
    args = sys.argv[3:]

    if command == 'list_derivations':
        if not args:
            print('需要 derivation.json 路径')
            sys.exit(1)
        list_derivation_branches(args[0])
        return
    elif command == 'get_derivation':
        if len(args) < 2:
            print('需要 derivation.json 和 branch_id')
            sys.exit(1)
        get_derivation_branch(args[0], args[1])
        return
    elif command == 'get_chain':
        if len(args) < 3:
            print('需要 derivation.json, branch_id, index')
            sys.exit(1)
        get_derivation_chain(args[0], args[1], args[2])
        return

    analysis = _load_analysis(analysis_path)

    dispatch = {
        'list_nodes': lambda: list_nodes(analysis),
        'list_by_type': lambda: list_by_type(analysis, args[0]) if args else print('需要 type'),
        'get_node': lambda: get_node(analysis, args[0]) if args else print('需要 node_id'),
        'get_code': lambda: get_code(analysis, args[0]) if args else print('需要 node_id'),
        'get_inputs': lambda: get_inputs(analysis, args[0]) if args else print('需要 node_id'),
        'get_outputs': lambda: get_outputs(analysis, args[0]) if args else print('需要 node_id'),
        'get_prompt': lambda: get_prompt(analysis, args[0]) if args else print('需要 node_id'),
    }

    if command in dispatch:
        dispatch[command]()
    else:
        print(f'未知命令: {command}')
