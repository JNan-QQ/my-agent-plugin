from parser import NodeInfo, EdgeInfo

FORK_NODE_TYPES = {'if-else', 'question-classifier'}


def build_graph_list(nodes: dict, edges: list, adjacency: dict, edges_from_node: dict | None = None) -> list:
    if edges_from_node is None:
        edges_from_node = {}
        for edge in edges:
            edges_from_node.setdefault(edge.source, []).append(edge)

    start_id = None
    for nid, node in nodes.items():
        if node.type == 'start':
            start_id = nid
            break

    if start_id is None:
        return []

    branches = []
    branch_counter = [0]
    stack = [([start_id], [], set())]

    while stack:
        queue, path, visited = stack.pop()
        forked = False

        while queue:
            node_id = queue.pop(0)
            if node_id in visited:
                continue

            path.append(node_id)
            visited.add(node_id)

            successors = adjacency.get(node_id, [])
            new_succs = [s for s in successors if s not in visited]

            if not new_succs:
                continue
            elif nodes[node_id].type in FORK_NODE_TYPES:
                handle_to_succs = {}
                for edge in edges_from_node.get(node_id, []):
                    if edge.target in visited:
                        continue
                    handle = edge.source_handle or '__default__'
                    handle_to_succs.setdefault(handle, []).append(edge.target)

                remaining = list(queue)
                for succs in handle_to_succs.values():
                    stack.append((remaining + succs, list(path), set(visited)))
                forked = True
                break
            else:
                queue.extend(new_succs)

        if path and not forked:
            branches.append({
                "branch_id": f"branch_{branch_counter[0]}",
                "nodes": list(path),
            })
            branch_counter[0] += 1

    return branches
