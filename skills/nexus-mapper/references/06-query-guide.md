# query_graph.py — 五个查询模式详解

> 当你需要在 PROBE 各阶段（REASON/OBJECT/EMIT）或日常开发中使用 `query_graph.py` 做精准局部查询时，读本文件。
>
> **零额外依赖**，纯标准库，输入 `ast_nodes.json` 即可运行。

---

## 命令速查

```bash
# 文件骨架：类、方法、行号、import 清单
python query_graph.py ast_nodes.json --file <path>
python query_graph.py ast_nodes.json --file <path> --git-stats git_stats.json

# 反向依赖：谁引用了该模块（区分源码文件和测试文件）
python query_graph.py ast_nodes.json --who-imports <module_or_path>

# 影响半径：上游依赖 + 下游被依赖（X upstream, Y downstream）
python query_graph.py ast_nodes.json --impact <path>
python query_graph.py ast_nodes.json --impact <path> --git-stats git_stats.json

# 全仓库核心节点：按扇入（被引用最多）和扇出（引用最多）排序
python query_graph.py ast_nodes.json --hub-analysis
python query_graph.py ast_nodes.json --hub-analysis --top 10

# 按顶层目录聚合：模块数/类数/函数数/行数 + import 方向关系
python query_graph.py ast_nodes.json --summary
```

---

## 各模式核心价值

### --file — 文件骨架解剖

用于：在不逐行读源码的情况下掌握文件结构。一个 3000 行的 legacy 模块有数十个类时，`--file` 秒出骨架，再按行号精准跳转读 `view_file`。

PROBE 阶段对应：EMIT（为 `dependencies.md` 生成结构数据）

### --who-imports — 反向依赖追踪

用于：改接口之前必须跑的命令。任何修改公共函数签名、删除方法、重命名类的操作如果跳过这步，都是在赌不会炸。

PROBE 阶段对应：OBJECT（验证「这个模块是否真的边界清晰」）

### --impact — 影响半径量化

用于：`0 upstream, 24 downstream` 一眼告诉你这是基础层，改动影响最广。与 git-stats 叠加后：**high-risk + high downstream = 当前最危险的改动点**。

PROBE 阶段对应：OBJECT（验证边界假设）

### --hub-analysis — 架构核心节点识别

用于：目录名 ≠ 重要性。命名为 `core/` 的不一定是实际核心；真正的高耦合节点往往藏在不起眼的工具类或数据模型里。

PROBE 阶段对应：REASON（数据验证核心系统假说）

### --summary — 全局目录聚合

用于：用一条命令建立系统分层意识。从 import 关系图里直接读出哪个目录是业务逻辑层、哪个是基础设施层，比读任何文档都客观。两个顶层目录互相 import → 循环依赖红旗。

PROBE 阶段对应：EMIT（为 `systems.md` / `dependencies.md` 提供数据支撑）

---

## 使用时机速查

| 问题                              | PROBE 阶段 | 开发中                       |
| --------------------------------- | ---------- | ---------------------------- |
| 这个文件有哪些类/方法，各在哪几行 | EMIT       | 改动前摸底                   |
| 改这个接口/删函数，哪些文件跟着改 | OBJECT     | 必检，否则炸                 |
| 这个改动最终影响多少模块          | OBJECT     | 估工作量                     |
| 这个改动 + git 热度 = 风险有多高  | OBJECT     | Sprint 决策                  |
| 项目中谁是真正的核心依赖节点      | REASON     | 架构评审                     |
| 整个项目的模块分布和层级          | EMIT       | 项目交接                     |
| 连续重构，改完一处查影响链        | —          | `--who-imports` → `--impact` |

---

## 前提说明

`ast_nodes.json` 通常位于 `.nexus-map/raw/ast_nodes.json`，`git_stats.json` 通常位于 `.nexus-map/raw/git_stats.json`。支持绝对或相对路径：

```bash
python $SKILL_DIR/scripts/query_graph.py /tmp/ast_nodes.json --file src/core/vision.py
```

路径片段匹配支持（如 `vision.py` 可匹配 `src/core/vision.py`）。当结果返回 `[NOT FOUND]` 时，先用 `--summary` 确认仓库中存在的模块路径格式，再重新查询。
