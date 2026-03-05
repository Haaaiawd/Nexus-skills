# nexus-mapper scripts — Tree-sitter 兼容性评估

**评估日期**: 2026-03-05  
**评估对象**: `src/nexus/infrastructure/parsing/treesitter_parser.py`

---

## 结论：**核心查询可提炼，语言加载需适配**

---

## 旧代码 API 使用情况

| 项目 | 旧代码方式 | API 状态 |
|------|-----------|---------|
| 语言加载 | `from tree_sitter_language_pack import get_language` | ✅ 新 API（≥0.22） |
| Parser 初始化 | `Parser(lang)` | ✅ 新 API（≥0.22） |
| Query 执行 | `QueryCursor` / `Query` | ✅ 新 API（≥0.22） |
| ~~Language.build_library~~ | 未使用 | — |

> 旧代码**未使用**已废弃的 `Language.build_library()` 方法，采用的是 0.22+ 新式 API。

---

## 差异点（脚本 vs 旧项目）

| 维度 | 旧项目 (`treesitter_parser.py`) | 本脚本 (`extract_ast.py`) |
|------|--------------------------------|--------------------------|
| 语言包 | `tree-sitter-language-pack`（160+ 语言） | `tree-sitter-python`（仅 Python，更轻量） |
| 语言加载 | `get_language('python')` | `import tree_sitter_python; tree_sitter_python.language()` |
| 其余 API | 一致 | 一致 |

---

## 可提炼内容

- ✅ **Python Query Patterns**（`treesitter_parser.py` 第 170-200 行）：
  `class_definition`, `function_definition`, `import` 的 S-expression 查询直接复用
- ✅ **文件扩展名映射表**：过滤逻辑可复用
- ✅ **节点遍历与层级关系推断逻辑**

## 需要独立实现

- 🔄 语言加载：改用 `tree_sitter_python.language()` 而非 `get_language('python')`  
  （在 Nexus poetry 环境中两者均可，优先检测 language-pack，fallback 到 tree-sitter-python）
- 🔄 去除 structlog / Celery / DB 依赖，改为 stdout JSON 输出
