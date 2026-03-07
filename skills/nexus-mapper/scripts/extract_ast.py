#!/usr/bin/env python3
"""
extract_ast.py — 多语言代码仓库 AST 结构提取器

用途：基于 Tree-sitter 提取代码仓库的模块/类/函数结构，输出 JSON 到 stdout
支持：Python, JavaScript, TypeScript, TSX, Java, Go, Rust, C#, C/C++, Kotlin, Ruby, Swift, PHP, Lua ...
用法：python extract_ast.py <repo_path> [--max-nodes 500]
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Any, Optional


EXCLUDE_DIRS = {'.git', '__pycache__', '.venv', 'venv', 'node_modules',
                'dist', 'build', '.mypy_cache', '.pytest_cache', 'site-packages',
                '.nexus-map', '.tox', '.eggs', 'target', 'cmake-build-debug',
                '.vs', 'out', '_build', 'vendor'}

# 文件扩展名 → tree-sitter-language-pack 语言名
EXTENSION_MAP: dict[str, str] = {
    '.py': 'python', '.pyw': 'python', '.pyi': 'python',
    '.js': 'javascript', '.mjs': 'javascript', '.cjs': 'javascript', '.jsx': 'javascript',
    '.ts': 'typescript', '.mts': 'typescript',
    '.tsx': 'tsx',
    '.java': 'java',
    '.go': 'go',
    '.rs': 'rust',
    '.cs': 'csharp',
    '.c': 'c', '.h': 'c',
    '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp', '.hpp': 'cpp', '.hxx': 'cpp',
    '.kt': 'kotlin', '.kts': 'kotlin',
    '.rb': 'ruby',
    '.php': 'php',
    '.lua': 'lua',
    '.swift': 'swift',
    '.scala': 'scala', '.sc': 'scala',
    '.ex': 'elixir', '.exs': 'elixir',
}

# 每语言的 Tree-sitter Query：结构（类/函数）+ 导入
# struct captures: class.def/class.name, func.def/func.name
# imports captures: mod
LANG_QUERIES: dict[str, dict[str, str]] = {
    'python': {
        'struct': """
            (class_definition name: (identifier) @class.name) @class.def
            (function_definition name: (identifier) @func.name) @func.def
        """,
        'imports': """
            (import_statement name: (dotted_name) @mod)
            (import_from_statement module_name: (dotted_name) @mod)
        """,
    },
    'javascript': {
        'struct': """
            (class_declaration name: (identifier) @class.name) @class.def
            (function_declaration name: (identifier) @func.name) @func.def
            (method_definition name: (property_identifier) @func.name) @func.def
        """,
        'imports': """
            (import_statement source: (string (string_fragment) @mod))
        """,
    },
    'typescript': {
        'struct': """
            (class_declaration name: (type_identifier) @class.name) @class.def
            (function_declaration name: (identifier) @func.name) @func.def
            (method_definition name: (property_identifier) @func.name) @func.def
        """,
        'imports': """
            (import_statement source: (string (string_fragment) @mod))
        """,
    },
    'tsx': {
        'struct': """
            (class_declaration name: (type_identifier) @class.name) @class.def
            (function_declaration name: (identifier) @func.name) @func.def
            (method_definition name: (property_identifier) @func.name) @func.def
        """,
        'imports': """
            (import_statement source: (string (string_fragment) @mod))
        """,
    },
    'java': {
        'struct': """
            (class_declaration name: (identifier) @class.name) @class.def
            (method_declaration name: (identifier) @func.name) @func.def
            (interface_declaration name: (identifier) @class.name) @class.def
        """,
        'imports': """
            (import_declaration (scoped_identifier) @mod)
        """,
    },
    'go': {
        'struct': """
            (type_declaration (type_spec name: (type_identifier) @class.name)) @class.def
            (function_declaration name: (identifier) @func.name) @func.def
            (method_declaration name: (field_identifier) @func.name) @func.def
        """,
        'imports': """
            (import_spec path: (interpreted_string_literal) @mod)
        """,
    },
    'rust': {
        'struct': """
            (struct_item name: (type_identifier) @class.name) @class.def
            (enum_item name: (type_identifier) @class.name) @class.def
            (function_item name: (identifier) @func.name) @func.def
        """,
        'imports': """
            (use_declaration argument: (scoped_identifier) @mod)
            (use_declaration argument: (identifier) @mod)
        """,
    },
    'csharp': {
        'struct': """
            (class_declaration name: (identifier) @class.name) @class.def
            (method_declaration name: (identifier) @func.name) @func.def
            (interface_declaration name: (identifier) @class.name) @class.def
        """,
        'imports': """
            (using_directive (qualified_name) @mod)
            (using_directive (identifier) @mod)
        """,
    },
    'cpp': {
        'struct': """
            (class_specifier name: (type_identifier) @class.name) @class.def
            (function_definition
                declarator: (function_declarator
                    declarator: (identifier) @func.name)) @func.def
        """,
        'imports': """
            (preproc_include path: (system_lib_string) @mod)
            (preproc_include path: (string_literal) @mod)
        """,
    },
    'c': {
        'struct': """
            (struct_specifier name: (type_identifier) @class.name) @class.def
            (function_definition
                declarator: (function_declarator
                    declarator: (identifier) @func.name)) @func.def
        """,
        'imports': """
            (preproc_include path: (system_lib_string) @mod)
            (preproc_include path: (string_literal) @mod)
        """,
    },
    'kotlin': {
        'struct': """
            (class_declaration (type_identifier) @class.name) @class.def
            (function_declaration (simple_identifier) @func.name) @func.def
        """,
        'imports': """
            (import_header (identifier) @mod)
        """,
    },
    'ruby': {
        'struct': """
            (class name: (constant) @class.name) @class.def
            (method name: (identifier) @func.name) @func.def
        """,
        'imports': '',  # Ruby require 语法较复杂，暂跳过
    },
    'swift': {
        'struct': """
            (class_declaration name: (type_identifier) @class.name) @class.def
            (function_declaration name: (simple_identifier) @func.name) @func.def
        """,
        'imports': """
            (import_declaration (identifier) @mod)
        """,
    },
    'scala': {
        'struct': """
            (class_definition name: (identifier) @class.name) @class.def
            (function_definition name: (identifier) @func.name) @func.def
        """,
        'imports': """
            (import_declaration importees: (import_selectors selector: (import_selector name: (identifier) @mod)))
        """,
    },
    'lua': {
        'struct': """
            (function_declaration name: (identifier) @func.name) @func.def
        """,
        'imports': '',
    },
    'php': {
        'struct': """
            (class_declaration name: (name) @class.name) @class.def
            (method_declaration name: (name) @func.name) @func.def
            (function_definition name: (name) @func.name) @func.def
        """,
        'imports': """
            (namespace_use_declaration (namespace_use_clause (qualified_name (name) @mod)))
        """,
    },
    'elixir': {
        'struct': """
            (call target: (identifier) @_keyword
                  arguments: (arguments (alias) @class.name)
                  (#match? @_keyword "^(defmodule|defprotocol)$")) @class.def
            (call target: (identifier) @_keyword
                  arguments: (arguments (identifier) @func.name)
                  (#match? @_keyword "^(def|defp)$")) @func.def
        """,
        'imports': '',
    },
}


def _load_languages(requested: Optional[list[str]] = None) -> dict[str, Any]:
    """
    加载 Tree-sitter 语言对象，返回 {lang_name: Language} 字典。
    优先使用 tree-sitter-language-pack（160+ 语言），不可用时回退单语言包。
    """
    try:
        from tree_sitter_language_pack import get_language as _get
        def get_language(name: str) -> Any:
            return _get(name)
    except ImportError:
        # 仅 Python 单语言包 fallback
        try:
            import tree_sitter_python
            from tree_sitter import Language
            def get_language(name: str) -> Any:
                if name == 'python':
                    return Language(tree_sitter_python.language())
                raise LookupError(name)
        except ImportError:
            sys.stderr.write(
                "[ERROR] 缺少 tree-sitter 语言支持。\n"
                "请运行: pip install tree-sitter-language-pack\n"
            )
            sys.exit(1)

    targets = requested if requested else list(LANG_QUERIES.keys())
    languages: dict[str, Any] = {}
    for name in targets:
        if name not in LANG_QUERIES:
            continue
        try:
            languages[name] = get_language(name)
        except (LookupError, KeyError):
            # 该语言包未安装，优雅跳过
            pass

    if not languages:
        sys.stderr.write("[ERROR] 没有可用的语言解析器，请安装 tree-sitter-language-pack\n")
        sys.exit(1)
    return languages


def _file_module_id(repo_path: Path, file_path: Path) -> str:
    """将文件路径转换为点分隔的模块 ID。
    例：src/nexus/api/routes.py → src.nexus.api.routes
        src/core/parser.hpp   → src.core.parser
    """
    rel = file_path.relative_to(repo_path)
    parts = list(rel.parts)
    stem = Path(parts[-1]).stem  # 去掉扩展名
    parts[-1] = stem
    # Python 特殊处理：__init__ 合并到包路径
    if stem == '__init__' and len(parts) > 1:
        parts = parts[:-1]
    return '.'.join(parts) if parts else stem




def extract_file(
    repo_path: Path,
    file_path: Path,
    lang_name: str,
    language: Any,
) -> tuple[list[dict], list[dict], list[str]]:
    """解析单个源文件，返回 (nodes, edges, errors)"""
    from tree_sitter import Parser as TSParser, Query, QueryCursor

    nodes: list[dict] = []
    edges: list[dict] = []
    errors: list[str] = []

    try:
        source = file_path.read_bytes()
    except OSError as e:
        errors.append(f"{file_path}: read error: {e}")
        return nodes, edges, errors

    try:
        parser = TSParser(language)
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
        'lang': lang_name,
    })

    queries = LANG_QUERIES.get(lang_name, {})

    # ── 结构：类 / 函数 ──────────────────────────────────────────
    struct_q_text = queries.get('struct', '')
    if struct_q_text.strip():
        try:
            struct_query = Query(language, struct_q_text)
            class_ranges: list[tuple[int, int, str]] = []

            for pattern_idx, captures in QueryCursor(struct_query).matches(tree.root_node):
                capture_names = list(captures.keys())
                is_class = any('class' in k for k in capture_names)
                def_key = 'class.def' if is_class else 'func.def'
                name_key = 'class.name' if is_class else 'func.name'

                def_nodes = captures.get(def_key, [])
                name_nodes = captures.get(name_key, [])
                if not def_nodes or not name_nodes:
                    continue

                def_node = def_nodes[0]
                name_node = name_nodes[0]
                name = source[name_node.start_byte:name_node.end_byte].decode('utf-8', 'replace')

                if is_class:
                    node_id = f"{module_id}.{name}"
                    nodes.append({
                        'id': node_id,
                        'type': 'Class',
                        'label': name,
                        'path': rel_path,
                        'parent': module_id,
                        'start_line': def_node.start_point[0] + 1,
                        'end_line': def_node.end_point[0] + 1,
                    })
                    class_ranges.append((def_node.start_byte, def_node.end_byte, node_id))
                    edges.append({'source': module_id, 'target': node_id, 'type': 'contains'})
                else:
                    parent_id = module_id
                    for cls_start, cls_end, cls_id in class_ranges:
                        if cls_start <= def_node.start_byte and def_node.end_byte <= cls_end:
                            parent_id = cls_id
                            break
                    node_id = f"{parent_id}.{name}"
                    nodes.append({
                        'id': node_id,
                        'type': 'Function',
                        'label': name,
                        'path': rel_path,
                        'parent': parent_id,
                        'start_line': def_node.start_point[0] + 1,
                        'end_line': def_node.end_point[0] + 1,
                    })
                    edges.append({'source': parent_id, 'target': node_id, 'type': 'contains'})

        except Exception as e:
            errors.append(f"{file_path}: struct query error: {e}")

    # ── 导入：imports 边 ─────────────────────────────────────────
    import_q_text = queries.get('imports', '')
    if import_q_text.strip():
        try:
            import_query = Query(language, import_q_text)
            for _pattern_idx, captures in QueryCursor(import_query).matches(tree.root_node):
                for mod_node in captures.get('mod', []):
                    target = source[mod_node.start_byte:mod_node.end_byte].decode('utf-8', 'replace').strip('"\'<> ')
                    if target:
                        edges.append({'source': module_id, 'target': target, 'type': 'imports'})
        except Exception as e:
            errors.append(f"{file_path}: import query error: {e}")

    return nodes, edges, errors


def collect_source_files(repo_path: Path, languages: dict[str, Any]) -> list[tuple[Path, str]]:
    """收集 repo 中所有已知语言的源文件，跳过排除目录。
    返回 [(file_path, lang_name)] 列表。
    """
    files: list[tuple[Path, str]] = []
    for p in repo_path.rglob('*'):
        if not p.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        lang = EXTENSION_MAP.get(p.suffix.lower())
        if lang and lang in languages:
            files.append((p, lang))
    return sorted(files, key=lambda x: x[0])



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

    priority_nodes = [n for n in nodes if n['type'] in ('Module', 'Class')]
    func_nodes = [n for n in nodes if n['type'] == 'Function']

    remaining_slots = max_nodes - len(priority_nodes)
    if remaining_slots < 0:
        kept_nodes = priority_nodes
        truncated_count = len(func_nodes)
    else:
        kept_funcs = func_nodes[:remaining_slots]
        kept_nodes = priority_nodes + kept_funcs
        truncated_count = len(func_nodes) - len(kept_funcs)

    kept_ids = {n['id'] for n in kept_nodes}
    kept_edges = [
        e for e in edges
        if e['source'] in kept_ids or e['type'] == 'imports'
    ]
    return kept_nodes, kept_edges, True, truncated_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Extract AST structure from a multi-language repository'
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

    languages = _load_languages()
    source_files = collect_source_files(repo_path, languages)

    if not source_files:
        sys.stderr.write(f"[WARNING] No supported source files found in {repo_path}\n")

    all_nodes: list[dict] = []
    all_edges: list[dict] = []
    all_errors: list[str] = []
    detected_langs: set[str] = set()
    total_lines = 0

    for file_path, lang_name in source_files:
        nodes, edges, errors = extract_file(repo_path, file_path, lang_name, languages[lang_name])
        all_nodes.extend(nodes)
        all_edges.extend(edges)
        all_errors.extend(errors)
        if nodes:
            detected_langs.add(lang_name)
            total_lines += nodes[0].get('lines', 0)

    final_nodes, final_edges, truncated, truncated_count = apply_max_nodes(
        all_nodes, all_edges, args.max_nodes
    )

    result = {
        'languages': sorted(detected_langs),
        'stats': {
            'total_files': len(source_files),
            'total_lines': total_lines,
            'parse_errors': len(all_errors),
            'truncated': truncated,
            'truncated_nodes': truncated_count,
        },
        'nodes': final_nodes,
        'edges': final_edges,
    }

    if all_errors:
        result['_errors'] = all_errors[:20]

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

