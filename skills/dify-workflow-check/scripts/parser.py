import yaml
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NodeInfo:
    id: str
    type: str
    title: str
    variables: list = field(default_factory=list)
    outputs: dict = field(default_factory=dict)
    code: str = ''
    code_language: str = ''
    prompt: list = field(default_factory=list)
    cases: list = field(default_factory=list)
    answer: str = ''
    tool_parameters: dict = field(default_factory=dict)
    param_schemas: list = field(default_factory=list)
    model_config: dict = field(default_factory=dict)
    raw_data: dict = field(default_factory=dict)


@dataclass
class EdgeInfo:
    id: str
    source: str
    source_handle: str
    target: str
    target_handle: str
    source_type: str = ''
    target_type: str = ''


def parse_workflow(yml_path: str) -> dict:
    with open(yml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or 'workflow' not in data:
        raise ValueError(f'文件不像 Dify 工作流：缺少顶层 workflow 字段 ({yml_path})')

    workflow = data.get('workflow') or {}
    graph = workflow.get('graph')
    if not isinstance(graph, dict) or 'nodes' not in graph or 'edges' not in graph:
        raise ValueError(f'文件不像 Dify 工作流：workflow.graph 缺少 nodes/edges ({yml_path})')

    raw_nodes = graph['nodes']
    raw_edges = graph['edges']

    nodes = {}
    for raw_node in raw_nodes:
        node_data = raw_node['data']
        node_id = str(raw_node['id'])
        node = NodeInfo(
            id=node_id,
            type=node_data.get('type', ''),
            title=node_data.get('title', ''),
            variables=node_data.get('variables', []),
            outputs=node_data.get('outputs', {}),
            code=node_data.get('code', ''),
            code_language=node_data.get('code_language', ''),
            prompt=node_data.get('prompt_template', []),
            cases=node_data.get('cases', []),
            answer=node_data.get('answer', ''),
            tool_parameters=node_data.get('tool_parameters', {}),
            param_schemas=node_data.get('paramSchemas', []),
            model_config=node_data.get('model', {}),
            raw_data=raw_node,
        )
        nodes[node_id] = node

    edges = []
    for raw_edge in raw_edges:
        edge = EdgeInfo(
            id=raw_edge['id'],
            source=str(raw_edge['source']),
            source_handle=raw_edge.get('sourceHandle', ''),
            target=str(raw_edge['target']),
            target_handle=raw_edge.get('targetHandle', ''),
            source_type=raw_edge.get('data', {}).get('sourceType', ''),
            target_type=raw_edge.get('data', {}).get('targetType', ''),
        )
        edges.append(edge)

    adjacency = {}
    edges_from_node = {}
    for edge in edges:
        adjacency.setdefault(edge.source, [])
        if edge.target not in adjacency[edge.source]:
            adjacency[edge.source].append(edge.target)
        edges_from_node.setdefault(edge.source, []).append(edge)

    return {
        'nodes': nodes,
        'edges': edges,
        'adjacency': adjacency,
        'edges_from_node': edges_from_node,
        'raw_data': data,
    }
