#!/usr/bin/env python3
"""
extract_ast.py — 代码仓库 AST 结构提取器

用途：基于 Tree-sitter 提取 Python 代码仓库的模块/类/函数结构，输出 JSON 到 stdout
用法：python extract_ast.py <repo_path> [--max-nodes 500]
"""

import sys
import json
import argparse
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from tree_sitter import Language


EXCLUDE_DIRS = {'.git', '__pycache__', '.venv', 'venv', 'node_modules',
                'dist', 'build', '.mypy_cache', '.pytest_cache', 'site-packages'}


def _load_language() -> "Language":
    """加载 Python 语言解析器，兼容两种安装方式"""
    from tree_sitter import Language
    try:
        from tree_sitter_language_pack import get_language
        return cast(Language, get_language('python'))
    except ImportError:
        pass
    try:
        import tree_sitter_python
        return Language(tree_sitter_python.language())
    except ImportError:
        sys.stderr.write(
            "[ERROR] 缺少 tree-sitter Python 语言支持。"
            "请运行: pip install tree-sitter-python\n"
        )
        sys.exit(1)


def _file_module_id(repo_path: Path, file_path: Path) -> str:
    """将文件路径转换为点分隔的模块 ID，例如 src/nexus/api/routes.py → src.nexus.api.routes"""
    rel = file_path.relative_to(repo_path)
    parts = list(rel.parts)
    if parts[-1].endswith('.py'):
        parts[-1] = parts[-1][:-3]
    if parts[-1] == '__init__':
        parts = parts[:-1]
    return '.'.join(parts) if parts else rel.stem


def extract_file(
    repo_path: Path,
    file_path: Path,
    parser: Any,
    language: Any,
) -> tuple[list[dict], list[dict], list[str]]:
    """解析单个 Python 文件，返回 (nodes, edges, errors)"""
    nodes: list[dict] = []
    edges: list[dict] = []
    errors: list[str] = []

    try:
        source = file_path.read_bytes()
    except OSError as e:
        errors.append(f"{file_path}: read error: {e}")
        return nodes, edges, errors

    try:
        tree = parser.parse(source)
    except Exception as e:
        errors.append(f"{file_path}: parse error: {e}")
        return nodes, edges, errors

    rel_path = str(file_path.relative_to(repo_path)).replace('\\', '/')
    module_id = _file_module_id(repo_path, file_path)
    line_count = source.count(b'\n') + 1

    # Module 节点（文件级）
    nodes.append({
        'id': module_id,
        'type': 'Module',
        'label': module_id.split('.')[-1],
        'path': rel_path,
        'lines': line_count,
    })

    # 用 Tree-sitter Query 提取类、函数、import
    _extract_classes_functions(tree.root_node, module_id, rel_path, nodes, edges, language, source)

    return nodes, edges, errors


def _extract_classes_functions(
    root_node: Any,
    module_id: str,
    rel_path: str,
    nodes: list[dict],
    edges: list[dict],
    language: Any,
    source: bytes,
) -> None:
    """遍历 AST 提取类、函数节点和 import 边"""
    from tree_sitter import Query, QueryCursor

    struct_query = Query(language, """
        (class_definition name: (identifier) @class.name) @class.def
        (function_definition name: (identifier) @func.name) @func.def
    """)

    import_query = Query(language, """
        (import_statement name: (dotted_name) @mod) @import
        (import_from_statement module_name: (dotted_name) @mod) @from_import
    """)

    # 先提取类节点，记录其范围，用于判断函数是否是方法
    class_ranges: list[tuple[int, int, str]] = []

    for pattern_idx, captures in QueryCursor(struct_query).matches(root_node):
        if pattern_idx == 0:  # class_definition
            cls_node_list = captures.get('class.def', [])
            cls_name_list = captures.get('class.name', [])
            if not cls_node_list or not cls_name_list:
                continue
            cls_node = cls_node_list[0]
            cls_name_node = cls_name_list[0]
            name = source[cls_name_node.start_byte:cls_name_node.end_byte].decode('utf-8', 'replace')
            node_id = f"{module_id}.{name}"
            nodes.append({
                'id': node_id,
                'type': 'Class',
                'label': name,
                'path': rel_path,
                'parent': module_id,
                'start_line': cls_node.start_point[0] + 1,
                'end_line': cls_node.end_point[0] + 1,
            })
            class_ranges.append((cls_node.start_byte, cls_node.end_byte, node_id))
            edges.append({'source': module_id, 'target': node_id, 'type': 'contains'})

        elif pattern_idx == 1:  # function_definition
            fn_node_list = captures.get('func.def', [])
            fn_name_list = captures.get('func.name', [])
            if not fn_node_list or not fn_name_list:
                continue
            fn_node = fn_node_list[0]
            fn_name_node = fn_name_list[0]
            name = source[fn_name_node.start_byte:fn_name_node.end_byte].decode('utf-8', 'replace')
            parent_id = module_id
            for cls_start, cls_end, cls_id in class_ranges:
                if cls_start <= fn_node.start_byte and fn_node.end_byte <= cls_end:
                    parent_id = cls_id
                    break
            node_id = f"{parent_id}.{name}"
            nodes.append({
                'id': node_id,
                'type': 'Function',
                'label': name,
                'path': rel_path,
                'parent': parent_id,
                'start_line': fn_node.start_point[0] + 1,
                'end_line': fn_node.end_point[0] + 1,
            })
            edges.append({'source': parent_id, 'target': node_id, 'type': 'contains'})

    for _pattern_idx, captures in QueryCursor(import_query).matches(root_node):
        mod_list = captures.get('mod', [])
        for mod_node in mod_list:
            target = source[mod_node.start_byte:mod_node.end_byte].decode('utf-8', 'replace')
            edges.append({'source': module_id, 'target': target, 'type': 'imports'})


def collect_python_files(repo_path: Path) -> list[Path]:
    """收集 repo 中所有 Python 文件，跳过排除目录"""
    files = []
    for p in repo_path.rglob('*.py'):
        if not any(part in EXCLUDE_DIRS for part in p.parts):
            files.append(p)
    return sorted(files)


def apply_max_nodes(
    nodes: list[dict],
    edges: list[dict],
    max_nodes: int,
) -> tuple[list[dict], list[dict], bool, int]:
    """
    节点数超出 max_nodes 时，优先保留 Module/Class，截断 Function。
    返回 (filtered_nodes, filtered_edges, truncated, truncated_count)
    """
    if len(nodes) <= max_nodes:
        return nodes, edges, False, 0

    # 优先保留 Module 和 Class
    priority_nodes = [n for n in nodes if n['type'] in ('Module', 'Class')]
    func_nodes = [n for n in nodes if n['type'] == 'Function']

    remaining_slots = max_nodes - len(priority_nodes)
    if remaining_slots < 0:
        # 即使 Module/Class 超出，也全部保留（不截断核心节点）
        kept_nodes = priority_nodes
        kept_ids = {n['id'] for n in kept_nodes}
        truncated_count = len(func_nodes)
    else:
        kept_funcs = func_nodes[:remaining_slots]
        kept_nodes = priority_nodes + kept_funcs
        kept_ids = {n['id'] for n in kept_nodes}
        truncated_count = len(func_nodes) - len(kept_funcs)

    # 过滤 edges：两端都在 kept_ids 内才保留（import edges target 是外部包名，也保留）
    kept_edges = [
        e for e in edges
        if e['source'] in kept_ids or e['type'] == 'imports'
    ]

    return kept_nodes, kept_edges, True, truncated_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Extract AST structure from a Python repository'
    )
    parser.add_argument('repo_path', help='Target repository path')
    parser.add_argument('--max-nodes', type=int, default=500,
                        help='Max nodes in output (default: 500). Truncates Function nodes first.')
    args = parser.parse_args()

    repo_path = Path(args.repo_path).resolve()
    if not repo_path.exists():
        sys.stderr.write(f"[ERROR] repo_path not found: {repo_path}\n")
        sys.exit(1)
    if not (repo_path / '.git').exists():
        sys.stderr.write(f"[WARNING] .git not found in {repo_path}, may not be a git repo\n")

    language = _load_language()

    from tree_sitter import Parser as TSParser
    ts_parser = TSParser(language)

    py_files = collect_python_files(repo_path)

    all_nodes: list[dict] = []
    all_edges: list[dict] = []
    all_errors: list[str] = []
    total_lines = 0

    for file_path in py_files:
        nodes, edges, errors = extract_file(repo_path, file_path, ts_parser, language)
        all_nodes.extend(nodes)
        all_edges.extend(edges)
        all_errors.extend(errors)
        if nodes:
            total_lines += nodes[0].get('lines', 0)  # Module node has lines

    final_nodes, final_edges, truncated, truncated_count = apply_max_nodes(
        all_nodes, all_edges, args.max_nodes
    )

    result = {
        'language': 'python',
        'stats': {
            'total_files': len(py_files),
            'total_lines': total_lines,
            'parse_errors': len(all_errors),
            'truncated': truncated,
            'truncated_nodes': truncated_count,
        },
        'nodes': final_nodes,
        'edges': final_edges,
    }

    if all_errors:
        result['_errors'] = all_errors[:20]  # 最多记录 20 条

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
