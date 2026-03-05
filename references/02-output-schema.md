# 输出 Schema 规范

> ⛔ **EMIT 阶段硬门控**：本文件由 `01-probe-protocol.md` 的 EMIT 阶段门控强制触发读取，
> 写入任何 `.nexus-map/` 文件前必须完成本文阅读。
> 本文 Schema 均基于实际运行输出校正，与脚本当前版本保持一致。

---

## raw/ast_nodes.json（extract_ast.py 产出）

### 顶层结构
```json
{
  "languages": ["cpp", "python"],
  "stats": {
    "total_files": 101,
    "total_lines": 23184,
    "parse_errors": 0,
    "truncated": true,
    "truncated_nodes": 298
  },
  "nodes": [...],
  "edges": [...]
}
```

### Module 节点
```json
{
  "id": "src.nexus.application.weaving.treesitter_parser",
  "type": "Module",
  "label": "treesitter_parser",
  "path": "src/nexus/application/weaving/treesitter_parser.py",
  "lines": 320,
  "lang": "python"
}
```

### Class 节点
```json
{
  "id": "src.nexus.application.weaving.treesitter_parser.TreeSitterParser",
  "type": "Class",
  "label": "TreeSitterParser",
  "path": "src/nexus/application/weaving/treesitter_parser.py",
  "parent": "src.nexus.application.weaving.treesitter_parser",
  "start_line": 15,
  "end_line": 287
}
```

### Edge
```json
{
  "source": "src.nexus.infrastructure",
  "target": "src.nexus.infrastructure.db_client",
  "type": "contains"
}
```

**Edge 类型**：`contains`（模块→类，类→方法）/ `imports`（import 语句解析）

---

## raw/git_stats.json（git_detective.py 产出）

```json
{
  "analysis_period_days": 90,
  "stats": {
    "total_commits": 42,
    "total_authors": 1
  },
  "hotspots": [
    {"path": "src/nexus/tasks/analysis_tasks.py", "changes": 21, "risk": "high"}
  ],
  "coupling_pairs": [
    {"file_a": "...", "file_b": "...", "co_changes": 5, "coupling_score": 0.71}
  ]
}
```

**risk 阈值**：`changes < 5` → `low` / `5–15` → `medium` / `> 15` → `high`

---

## concepts/concept_model.json — Schema V1（EMIT 产出）

```json
{
  "$schema": "nexus-mapper/concept-model/v1",
  "generated_at": "2026-03-05T15:00:00Z",
  "repo_path": "/absolute/path/to/repo",
  "generator": "nexus-mapper v2",
  "nodes": [
    {
      "id": "nexus.ast-extractor",
      "type": "System",
      "label": "AST Extractor",
      "responsibility": "使用 Tree-sitter 解析 Python 仓库，提取模块/类/函数节点及 import 关系，输出机器可读 JSON",
      "code_path": "src/nexus/application/weaving/",
      "tech_stack": ["tree-sitter", "python"],
      "related_reqs": ["REQ-101"],
      "complexity": "medium",
      "hotspot": true
    }
  ],
  "edges": [
    {
      "source": "nexus.ast-extractor",
      "target": "nexus.task-dispatcher",
      "type": "depends_on",
      "description": "可选说明"
    }
  ],
  "metadata": {
    "total_files": 101,
    "total_lines": 23184,
    "languages": ["python"],
    "git_commits_analyzed": 42,
    "analysis_days": 90
  }
}
```

### 节点字段校验规则

| 字段 | 必需 | 触发 `[!ERROR]` 的情况 |
|------|:----:|-----------------------|
| `id` | ✅ | 全局重复；含大写字母或空格（必须为 kebab-case 小写）|
| `type` | ✅ | 不在枚举 `System / Domain / Module / Class / Function` 中 |
| `label` | ✅ | 空字符串 |
| `responsibility` | ✅ | 含禁止词；字数 < 10 或 > 100 |
| `code_path` | ✅ | 路径在 repo 中不实际存在（必须亲手验证，见 SKILL.md 守则2）|

---

## 🚫 禁止词列表

> 出现在任意输出文件的 `responsibility` 或正文叙述中 → `[!ERROR]` 必须返工

```
中文：待确认 · 可能是 · 疑似 · 也许 · 待定 · 暂不清楚 · 需要进一步 · 不确定
英文：pending · maybe · possibly · perhaps · TBD · to be confirmed
```
