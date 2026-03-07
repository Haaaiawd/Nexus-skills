# 边界案例与处理规范

> ⛔ **REASON 阶段硬门控**：本文件由 `01-probe-protocol.md` 的 REASON 阶段门控强制触发读取，
> 开始阅读项目文件前必须完成本文阅读，以提前识别边界场景（无 git 历史、monorepo 等）。

---

## §1 合法的"跳过"情况

### 无 git 历史的新仓库
- 现象：`$repo_path/.git` 存在但只有 1 次提交
- 处理：跳过 `git_detective.py`，在执行日志或最终输出中写明 `git analysis skipped: insufficient history`
- PROFILE 仍然完成（只需 `ast_nodes.json` + `file_tree.txt` 非空即可通过检查）

### 非 git 仓库
- 现象：`$repo_path/.git` 不存在
- 处理：跳过 `git_detective.py`，继续执行后续阶段
- 在最终输出中明确标注：`hotspots skipped because repository has no git metadata`

---

## §2 大型 Monorepo

- 文件数 > 1000 时：
  - 告知用户建议使用 `--max-nodes 200 --max-depth 3`
  - 命令：`python extract_ast.py $repo_path --max-nodes 200`
  - `stats.truncated=true` 是预期行为，不是错误

- Git 历史过长（> 3000 commits）时：
  - 使用 `--days 30` 缩短分析窗口代替默认 90 天
  - 命令：`python git_detective.py $repo_path --days 30`

---

## §3 截断行为（truncation）

当 `stats.truncated=true` 时：
- `extract_ast.py` **优先保留 Module 和 Class 节点**
- Function 节点被直接丢弃，`stats.truncated_nodes` 记录丢弃数量
- EMIT 阶段仍可基于 Module/Class 节点产出完整的 `concept_model.json`

> [!DEVIATION]
> **已知实现偏差**：截断的 Function 节点被**直接丢弃**，**不会生成** `raw/functions.json`。
> 如任何文档描述截断节点写入单独文件，均以本实际行为为准。

---

## §4 多语言混合 repo

- `extract_ast.py` 基于 `tree-sitter-language-pack`，支持 **17+ 语言**自动 dispatch（按文件扩展名）：
  `.py` / `.js` / `.jsx` / `.ts` / `.tsx` / `.java` / `.go` / `.rs` / `.cs` / `.cpp` / `.hpp` / `.cc` / `.c` / `.kt` / `.rb` / `.swift` / `.scala` / `.php` / `.lua` / `.ex` / `.exs`
- **未知扩展名**：静默跳过，不报错；`stats.languages` 仅记录实际解析到节点的语言
- 若所有已知语言文件数 < 3 → stderr 输出警告，仍继续，但分析质量可能偏低
- `ast_nodes.json` 每个 Module 节点含 `"lang"` 字段（如 `"lang": "cpp"`），方便后续按语言过滤

> [!NOTE]
> **不支持的语言** 在 `ast_nodes.json` 中表现为 `nodes: []`（空列表）。这是正常降级行为，
> PROFILE 完成检查只要求 `ast_nodes.json` 文件非空，空节点列表视为合法。

---

## §5 特殊目录结构

### 无 README 的项目
- REASON 阶段直接跳至 `pyproject.toml` / `package.json`
- 假说日志中注明：「无 README，evidence gap 在项目入口说明，OBJECT 阶段需额外质疑入口点」

### 目录过深嵌套
- Python 文件超过 8 层嵌套：AST 解析正常工作，不受目录层级影响
- `file_tree.txt` 行数 > 500 时：REASON 阶段仅读取前 300 行感知结构

---

## §6 EMIT 幂等性保障

- 多次执行会触发覆盖确认，不会静默覆盖已有分析
- 写入路径：先写 `.nexus-map/.tmp/`，全部成功后整体移动 → 避免中途失败留半成品
- 中途中断（如 Agent 超时）：下次执行检测到 `.tmp/` 目录 → 清理后重新生成
