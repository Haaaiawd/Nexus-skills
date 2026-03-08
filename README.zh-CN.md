<p align="center">
  <img src="Icon.png" alt="nexus-mapper" width="96" height="96">
</p>

<h1 align="center">nexus-mapper</h1>

<p align="center">
  先把仓库地图建出来。<br>
  后续每个 AI 会话都从已验证的上下文开始。
</p>

<p align="center">
  <a href="README.md">English</a>
</p>

---

## 它到底做什么

nexus-mapper 是一个给 AI Agent 用的仓库建图 skill。它分析本地代码库，写出持久化的 `.nexus-map/` 知识库，让后续会话先恢复全局上下文，再进入具体任务，而不是每次都从零摸索。

它不是一个泛泛的“总结仓库”提示词。这个 skill 会按 PROBE 协议分阶段执行，先产出证据，再挑战初始判断，最后才写正式资产。它解决的是 AI 最常见的一个问题：把第一眼印象误写成结论。

```
.nexus-map/
├── INDEX.md              ← 冷启动入口。完整架构上下文，控制在 2000 tokens 以内。
├── arch/
│   ├── systems.md        ← 每个子系统的职责和代码位置。
│   ├── dependencies.md   ← 组件间的调用关系，Mermaid 依赖图。
│   └── test_coverage.md  ← 静态测试面：哪些核心模块有测试、哪些没有、哪里证据不足。
├── concepts/
│   ├── concept_model.json ← 机器可读的知识图谱，供程序化使用。
│   └── domains.md        ← 这个代码库使用的领域语言，人能读懂的版本。
├── hotspots/             ← 仅在存在 git 元数据时生成。
│   └── git_forensics.md  ← 变更最频繁的文件，以及总是同时变更的文件对。
│                           改动这些地方最容易出问题。
└── raw/                  ← 原始数据：AST 节点、git 统计、过滤后的文件树。
```

`INDEX.md` 是唯一的冷启动入口，刻意保持很小。AI 可以一次性完整读入，先恢复全局，再按需下钻。

所有生成的 Markdown 文件都带 provenance 头部，至少写明 `verified_at` 和降级说明。若仓库包含当前未支持的语言，或某些语言只有 Module 级 AST 覆盖，nexus-mapper 必须显式说明，不能夸大解析可信度。

如果仓库需要补充超出内建范围的语言支持，优先用 `--add-extension` 和 `--add-query` 扩展本次运行。只有当配置太长、不适合塞进一条命令时，再改用 `--language-config <JSON_FILE>`。

---

## 它为什么不一样

- 它是阶段门控的，PROFILE、REASON、OBJECT、BENCHMARK、EMIT 都不能跳。
- 它强制区分 implemented、planned、inferred，避免把设计稿当成已实现代码。
- 地图生成后，还保留 `query_graph.py` 这个“放大镜”做局部验证。
- 它的目标不是当前这次回答，而是后续所有会话都能少走弯路。

---

## 前提条件

| 要求 | 说明 |
|------|------|
| Python 3.10+ | `python --version` |
| Shell 执行能力 | AI 客户端需支持运行终端命令 |

有 git 历史会更完整，但不是必须的。没有 git 历史时，`hotspots/` 分析会跳过，其余照常运行。

**首次使用前安装脚本依赖：**

```bash
pip install -r skills/nexus-mapper/scripts/requirements.txt
```

---

## 安装

```bash
npx skills add haaaiawd/nexus-mapper
```

适配 Claude Code、GitHub Copilot、Cursor、Cline，以及所有支持 `SKILL.md` 协议的 AI 客户端。

---

## 怎么使用

把本地仓库路径告诉你的 AI：

```
帮我分析 /Users/me/projects/my-app 并生成知识库
```

AI 跑完整个协议后，会在仓库根目录写入 `.nexus-map/`。下次打开这个项目时，直接说：

```
读取 .nexus-map/INDEX.md
```

这样先恢复全局上下文。

如果任务已经进入局部判断，不要只靠摘要猜。直接用按需查询工具去验证结构和依赖。

为了让这种行为在长期更稳定，建议把一小段持久规则写进宿主工具的记忆文件，例如 `AGENTS.md`、`CLAUDE.md` 或类似文件：

```md
如果仓库中存在 .nexus-map/INDEX.md，开始任务前必须先阅读它恢复全局上下文。

如果任务需要判断局部结构、依赖关系、影响半径或边界归属，优先回读 nexus-mapper 的按需查询说明，并使用 query_graph.py 基于 .nexus-map/raw/ast_nodes.json 做验证；不要重新猜结构。

当一次任务改变了项目的结构认知时，应在交付前评估是否同步更新 .nexus-map。结构认知包括：系统边界、入口、依赖关系、测试面、语言支持、路线图或阶段性进度事实。纯局部实现细节默认不更新。

不要把 .nexus-map 视为静态文档；它是项目记忆的一部分。新对话优先读取，重要变更后按需同步。
```

---

## 按需查询

`scripts/query_graph.py` 读取已生成的 `ast_nodes.json`，无需重新解析即可回答结构问题。

```bash
# 查看文件结构与 import
python scripts/query_graph.py .nexus-map/raw/ast_nodes.json --file src/server/handler.py

# 查询谁引用了某个模块
python scripts/query_graph.py .nexus-map/raw/ast_nodes.json --who-imports src.server.handler

# 影响半径（上游依赖 + 下游被引用者）
python scripts/query_graph.py .nexus-map/raw/ast_nodes.json --impact src/server/handler.py

# 叠加 git 风险与耦合数据
python scripts/query_graph.py .nexus-map/raw/ast_nodes.json --impact src/server/handler.py \
  --git-stats .nexus-map/raw/git_stats.json

# 高扇入/高扇出核心节点
python scripts/query_graph.py .nexus-map/raw/ast_nodes.json --hub-analysis

# 按目录聚合的结构摘要
python scripts/query_graph.py .nexus-map/raw/ast_nodes.json --summary
```

零额外依赖。纯 Python 标准库。

适合拿它回答这类问题：

- 这个文件里到底有什么？
- 谁在引用这个模块？
- 我改这个文件，会影响到哪里？
- 哪些模块是真正的内部枢纽？

PROBE 协议会在 REASON / OBJECT / EMIT 阶段使用它，你也可以在开发过程中直接调用。

---

## PROFILE 阶段命令

如果你是直接跑脚本，当前推荐的基础流程是：

```bash
python skills/nexus-mapper/scripts/extract_ast.py <repo_path> \
  --file-tree-out .nexus-map/raw/file_tree.txt \
  > <repo_path>/.nexus-map/raw/ast_nodes.json

python skills/nexus-mapper/scripts/git_detective.py <repo_path> --days 90 \
  > <repo_path>/.nexus-map/raw/git_stats.json
```

`--file-tree-out` 和 AST 收集共用同一套排除规则，因此 file tree 不会和 AST 扫描结果漂移。

---

## 语言支持

按文件扩展名自动 dispatch，支持 17+ 语言：

Python · JavaScript · JSX · TypeScript · TSX · Bash · Java · Go · Rust · C++ · C · C# · Kotlin · Ruby · Swift · Scala · PHP · Lua · Elixir · GDScript · Dart · Haskell · Clojure · SQL · Proto · Solidity · Vue · Svelte · R · Perl

这些语言的覆盖深度并不完全相同：有些是完整结构提取，有些当前只有 Module 级别，还有些虽然被显式要求支持了，但当前环境无法加载 parser。最终输出里的 metadata 会诚实标出这一点。

未知扩展名静默跳过。多语言混合仓库无需任何配置。

### 扩展语言支持

如果内建覆盖还不够，优先直接在命令行扩展本次运行：

```bash
python skills/nexus-mapper/scripts/extract_ast.py <repo_path> \
  --add-extension .templ=templ \
  --add-query templ struct "(component_declaration name: (identifier) @class.name) @class.def"
```

如果配置较多，不适合直接写在一条命令中，再显式传入 JSON 文件：

```json
{
  "extensions": {
    ".templ": "templ",
    ".gd": "gdscript"
  },
  "queries": {
    "templ": {
      "struct": "(component_declaration name: (identifier) @class.name) @class.def",
      "imports": ""
    }
  },
  "unsupported_extensions": {
    ".legacydsl": "legacydsl"
  }
}
```

```bash
python skills/nexus-mapper/scripts/extract_ast.py <repo_path> \
  --language-config /custom/path/to/language-config.json
```

这样所有语言都走同一套契约：有 parser 且有 query 就是 `structural coverage`，只有 parser 没有 query 就是 `module-only`，agent 明确要求支持但当前环境加载不到 parser 就是 `configured-but-unavailable`，明确标记不支持的仍然归为 `unsupported`。

---

## 仓库结构

```
nexus-mapper/
├── README.md
├── README.zh-CN.md
├── Icon.png
├── evals/                        ← 评测集与测试计划，用于持续迭代 skill
└── skills/
  └── nexus-mapper/
    ├── SKILL.md              ← 执行协议与守则
    ├── scripts/
    │   ├── extract_ast.py    ← 多语言 AST 提取器
    │   ├── query_graph.py    ← 按需 AST 查询工具（文件结构、影响半径、核心节点…）
    │   ├── git_detective.py  ← Git 热点与耦合分析
    │   ├── languages.json    ← 共享语言配置（扩展名映射 + Tree-sitter 查询）
    │   └── requirements.txt
    └── references/
      ├── 01-probe-protocol.md
      ├── 02-output-schema.md
      ├── 03-edge-cases.md
      ├── 04-object-framework.md
      └── 05-language-customization.md
```

如果只是把 skill 本体复制到其他 agent 工作区，复制 `skills/nexus-mapper/` 这一层即可。

---

## License

MIT
