"""
tests/test_extract_ast.py — extract_ast.py 单元测试

覆盖：Module 提取、Class 提取、import 边生成、max-nodes 截断逻辑
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

# conftest.py 已将 scripts/ 加入 sys.path
from extract_ast import (
    _file_module_id,
    apply_max_nodes,
    collect_python_files,
    extract_file,
    _load_language,
)

# ─────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────

@pytest.fixture(scope="session")
def language():
    return _load_language()


@pytest.fixture(scope="session")
def parser(language):
    from tree_sitter import Parser as TSParser
    return TSParser(language)


# ─────────────────────────────────────────
# _file_module_id
# ─────────────────────────────────────────

def test_module_id_simple(tmp_path):
    f = tmp_path / "foo.py"
    f.touch()
    assert _file_module_id(tmp_path, f) == "foo"


def test_module_id_nested(tmp_path):
    (tmp_path / "a" / "b").mkdir(parents=True)
    f = tmp_path / "a" / "b" / "bar.py"
    f.touch()
    assert _file_module_id(tmp_path, f) == "a.b.bar"


def test_module_id_init_stripped(tmp_path):
    (tmp_path / "pkg").mkdir()
    f = tmp_path / "pkg" / "__init__.py"
    f.touch()
    assert _file_module_id(tmp_path, f) == "pkg"


# ─────────────────────────────────────────
# apply_max_nodes
# ─────────────────────────────────────────

def _make_nodes(modules=2, classes=2, funcs=5):
    nodes = []
    for i in range(modules):
        nodes.append({"id": f"mod{i}", "type": "Module"})
    for i in range(classes):
        nodes.append({"id": f"cls{i}", "type": "Class"})
    for i in range(funcs):
        nodes.append({"id": f"fn{i}", "type": "Function"})
    return nodes


def _make_edges(nodes):
    return [{"source": n["id"], "target": "x", "type": "imports"} for n in nodes]


def test_no_truncation_under_limit():
    nodes = _make_nodes(2, 2, 3)
    edges = _make_edges(nodes)
    out_nodes, out_edges, truncated, count = apply_max_nodes(nodes, edges, max_nodes=100)
    assert not truncated
    assert count == 0
    assert len(out_nodes) == len(nodes)


def test_truncation_removes_functions_first():
    nodes = _make_nodes(modules=1, classes=2, funcs=10)
    edges = _make_edges(nodes)
    out_nodes, _, truncated, count = apply_max_nodes(nodes, edges, max_nodes=5)
    assert truncated
    assert count == 8  # 10 funcs, 2 slots left after 1 Module + 2 Class
    types = [n["type"] for n in out_nodes]
    assert types.count("Module") == 1
    assert types.count("Class") == 2
    assert types.count("Function") == 2


def test_truncation_exact_limit():
    nodes = _make_nodes(modules=1, classes=1, funcs=3)
    edges = _make_edges(nodes)
    # max_nodes=5 → all 5 fit
    out_nodes, _, truncated, _ = apply_max_nodes(nodes, edges, max_nodes=5)
    assert not truncated
    assert len(out_nodes) == 5


def test_truncation_stats_truncated_true():
    nodes = _make_nodes(modules=1, classes=0, funcs=20)
    edges = _make_edges(nodes)
    _, _, truncated, count = apply_max_nodes(nodes, edges, max_nodes=10)
    assert truncated is True
    assert count == 11  # 1 Module takes 1 slot, 9 Function slots remain, 11 truncated


# ─────────────────────────────────────────
# extract_file — Module 节点
# ─────────────────────────────────────────

def test_extract_module_node(tmp_path, parser, language):
    src = tmp_path / "mymod.py"
    src.write_text("x = 1\n", encoding="utf-8")
    nodes, edges, errors = extract_file(tmp_path, src, parser, language)
    assert not errors
    module_nodes = [n for n in nodes if n["type"] == "Module"]
    assert len(module_nodes) == 1
    assert module_nodes[0]["id"] == "mymod"
    assert module_nodes[0]["label"] == "mymod"
    assert module_nodes[0]["path"] == "mymod.py"


# ─────────────────────────────────────────
# extract_file — Class 节点
# ─────────────────────────────────────────

def test_extract_class_node(tmp_path, parser, language):
    src = tmp_path / "classes.py"
    src.write_text(
        "class Alpha:\n    pass\n\nclass Beta:\n    pass\n",
        encoding="utf-8",
    )
    nodes, edges, errors = extract_file(tmp_path, src, parser, language)
    assert not errors
    class_nodes = [n for n in nodes if n["type"] == "Class"]
    names = {n["label"] for n in class_nodes}
    assert names == {"Alpha", "Beta"}
    for cn in class_nodes:
        assert cn["parent"] == "classes"
        assert cn["start_line"] >= 1
        assert cn["end_line"] >= cn["start_line"]


def test_method_parent_is_class(tmp_path, parser, language):
    src = tmp_path / "methods.py"
    src.write_text(
        "class Foo:\n    def bar(self): pass\n",
        encoding="utf-8",
    )
    nodes, edges, errors = extract_file(tmp_path, src, parser, language)
    assert not errors
    fn_nodes = [n for n in nodes if n["type"] == "Function"]
    assert len(fn_nodes) == 1
    assert fn_nodes[0]["parent"] == "methods.Foo"


def test_top_level_function_parent_is_module(tmp_path, parser, language):
    src = tmp_path / "funcs.py"
    src.write_text("def top(): pass\n", encoding="utf-8")
    nodes, edges, errors = extract_file(tmp_path, src, parser, language)
    fn_nodes = [n for n in nodes if n["type"] == "Function"]
    assert len(fn_nodes) == 1
    assert fn_nodes[0]["parent"] == "funcs"


# ─────────────────────────────────────────
# extract_file — import 边
# ─────────────────────────────────────────

def test_import_edges(tmp_path, parser, language):
    src = tmp_path / "imports.py"
    src.write_text(
        "import os\nimport os.path\nfrom typing import List\n",
        encoding="utf-8",
    )
    nodes, edges, errors = extract_file(tmp_path, src, parser, language)
    assert not errors
    import_edges = [e for e in edges if e["type"] == "imports"]
    targets = {e["target"] for e in import_edges}
    assert "os" in targets
    assert "os.path" in targets
    assert "typing" in targets


# ─────────────────────────────────────────
# extract_file — 解析错误不崩溃
# ─────────────────────────────────────────

def test_parse_error_does_not_crash(tmp_path, parser, language):
    """tree-sitter 对语法错误有容错，解析结果应该不崩溃"""
    src = tmp_path / "broken.py"
    # 语法错误（不完整的函数定义），tree-sitter 会产出带 ERROR 节点的树
    src.write_text("def foo(\n", encoding="utf-8")
    nodes, edges, errors = extract_file(tmp_path, src, parser, language)
    # 无论如何都不应该抛异常；Module 节点应该存在
    module_nodes = [n for n in nodes if n["type"] == "Module"]
    assert len(module_nodes) == 1


def test_unreadable_file_returns_error(tmp_path, parser, language):
    """不存在的文件应该返回 errors，不崩溃"""
    ghost = tmp_path / "ghost.py"
    # 不创建文件，直接 extract
    nodes, edges, errors = extract_file(tmp_path, ghost, parser, language)
    assert nodes == []
    assert len(errors) == 1


# ─────────────────────────────────────────
# collect_python_files
# ─────────────────────────────────────────

def test_collect_python_files(tmp_path):
    (tmp_path / "a.py").write_text("pass")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_text("pass")
    # 排除目录
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "c.pyc").write_text("")
    (tmp_path / "__pycache__" / "c.py").write_text("pass")

    files = collect_python_files(tmp_path)
    paths = {f.name for f in files}
    assert "a.py" in paths
    assert "b.py" in paths
    # __pycache__ 内的文件应被排除
    assert not any("__pycache__" in str(f) for f in files)


# ─────────────────────────────────────────
# CLI 集成测试 (subprocess)
# ─────────────────────────────────────────

def test_cli_max_nodes_truncation(tmp_path):
    """--max-nodes 10 时结果中节点数 ≤ 10 且 stats.truncated=true"""
    # 创建足够多的类/函数让节点数超过 10
    src = tmp_path / "big.py"
    lines = []
    for i in range(20):
        lines.append(f"def func_{i}(): pass")
    src.write_text("\n".join(lines), encoding="utf-8")

    # 需要 .git 目录（extract_ast.py 只发 WARNING，不崩溃）
    script = Path(__file__).parent.parent / "extract_ast.py"
    result = subprocess.run(
        [sys.executable, str(script), str(tmp_path), "--max-nodes", "10"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert len(data["nodes"]) <= 10
    assert data["stats"]["truncated"] is True


def test_cli_basic_output(tmp_path):
    """基本输出包含 nodes, edges, stats 三个顶层字段"""
    src = tmp_path / "simple.py"
    src.write_text("class Foo:\n    def bar(self): pass\n", encoding="utf-8")

    script = Path(__file__).parent.parent / "extract_ast.py"
    result = subprocess.run(
        [sys.executable, str(script), str(tmp_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "nodes" in data
    assert "edges" in data
    assert "stats" in data
    assert "parse_errors" in data["stats"]
