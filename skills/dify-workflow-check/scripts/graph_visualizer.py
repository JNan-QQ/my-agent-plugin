def _get_node_title(node) -> str:
    if hasattr(node, 'title'):
        return node.title
    return node.get('title', '')


def _get_node_type(node) -> str:
    if hasattr(node, 'type'):
        return node.type
    return node.get('type', '')


def _mermaid_node_shape(node_id: str, title: str, ntype: str) -> str:
    safe_id = f'n{node_id}'
    safe_title = title.replace('"', "'")
    if ntype == 'start':
        return f'{safe_id}(["{safe_title}"])'
    elif ntype == 'if-else':
        return f'{safe_id}{{"{safe_title}"}}'
    elif ntype == 'answer':
        return f'{safe_id}[/"{safe_title}"\\]'
    return f'{safe_id}["{safe_title}"]'


def _count_branches_through(node_id: str, branches: list) -> int:
    return sum(1 for b in branches if node_id in b.get('nodes', []))


def generate_mermaid_skeleton(
    nodes: dict, adjacency: dict, branches: list, max_depth: int = 2
) -> str:
    start_id = None
    for nid, node in nodes.items():
        if _get_node_type(node) == 'start':
            start_id = nid
            break

    if not start_id:
        return "graph TD\n    empty[无 start 节点]"

    lines = ["graph TD"]
    visited = set()
    _build_mermaid_tree(
        start_id, nodes, adjacency, branches, lines, visited, 0, max_depth
    )
    return "\n".join(lines)


def _build_mermaid_tree(
    node_id: str, nodes: dict, adjacency: dict, branches: list,
    lines: list, visited: set, depth: int, max_depth: int
):
    if node_id in visited:
        return
    visited.add(node_id)

    node = nodes.get(node_id)
    if not node:
        return

    ntype = _get_node_type(node)
    title = _get_node_title(node)
    successors = adjacency.get(node_id, [])
    if not successors:
        return

    src = _mermaid_node_shape(node_id, title, ntype)

    if ntype == 'if-else' and depth >= max_depth:
        branch_count = _count_branches_through(node_id, branches)
        group_id = f"group_{node_id}"
        lines.append(f'    {src} --> {group_id}["{branch_count}条分支"]')
        return

    for succ_id in successors:
        succ_node = nodes.get(succ_id)
        if not succ_node:
            continue
        succ_type = _get_node_type(succ_node)
        succ_title = _get_node_title(succ_node)
        dst = _mermaid_node_shape(succ_id, succ_title, succ_type)
        lines.append(f'    {src} --> {dst}')
        next_depth = depth + 1 if ntype == 'if-else' else depth
        _build_mermaid_tree(
            succ_id, nodes, adjacency, branches, lines, visited, next_depth, max_depth
        )


def generate_branch_summary_table(
    branches: list, nodes: dict, max_rows: int = 20
) -> str:
    lines = []
    lines.append("| 分支ID | 长度 | 经过节点类型 | 终止节点 |")
    lines.append("|--------|------|-------------|----------|")

    for branch in branches[:max_rows]:
        node_ids = branch.get('nodes', [])
        types_seen = []
        last_title = ''
        for nid in node_ids:
            node = nodes.get(nid)
            if node:
                ntype = _get_node_type(node)
                if ntype not in types_seen:
                    types_seen.append(ntype)
                last_title = _get_node_title(node)
        lines.append(f"| {branch.get('branch_id', '')} | {len(node_ids)} | {'→'.join(types_seen)} | {last_title} |")

    if len(branches) > max_rows:
        lines.append(f"| ... | | | (共 {len(branches)} 条) |")

    return "\n".join(lines)


def export_branches_detail(branches: list, nodes: dict) -> list:
    details = []
    for branch in branches:
        node_ids = branch.get('nodes', [])
        type_counts = {}
        node_details = []
        for nid in node_ids:
            node = nodes.get(nid)
            if node:
                ntype = _get_node_type(node)
                title = _get_node_title(node)
                type_counts[ntype] = type_counts.get(ntype, 0) + 1
                node_details.append({"id": nid, "type": ntype, "title": title})

        details.append({
            "branch_id": branch.get('branch_id', ''),
            "length": len(node_ids),
            "nodes": node_details,
            "type_counts": type_counts,
        })
    return details
