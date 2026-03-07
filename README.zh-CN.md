<p align="center">
  <img src="Icon.png" alt="nexus-mapper" width="96" height="96">
</p>

<h1 align="center">nexus-mapper</h1>

<p align="center">
  为 AI Agent 生成可持续复用的代码仓库知识库。<br>
  新开对话窗口，直接上下文接续，无需重新探索。
</p>

<p align="center">
  <a href="README.md">English</a>
</p>

---

## 你能得到什么

对一个仓库运行一次 nexus-mapper，它会在项目根目录写入 `.nexus-map/` 知识库，记录架构边界、系统分工、高频变更文件和依赖关系图。之后每次打开新对话，AI 读一个文件就知道整个项目的全貌。

它不会把第一眼猜测直接写成结论。正式产出前，协议会先用代码证据和 git 线索挑战初始判断，宁可少报，也不为了“看起来全面”而凑问题或装确定。

```
.nexus-map/
├── INDEX.md              ← 冷启动入口。完整架构上下文，控制在 2000 tokens 以内。
├── arch/
│   ├── systems.md        ← 每个子系统的职责和代码位置。
│   └── dependencies.md   ← 组件间的调用关系，Mermaid 依赖图。
├── concepts/
│   ├── concept_model.json ← 机器可读的知识图谱，供程序化使用。
│   └── domains.md        ← 这个代码库使用的领域语言，人能读懂的版本。
├── hotspots/             ← 仅在存在 git 元数据时生成。
│   └── git_forensics.md  ← 变更最频繁的文件，以及总是同时变更的文件对。
│                           改动这些地方最容易出问题。
└── raw/                  ← 原始数据：AST 节点、git 统计、过滤后的文件树。
```

`INDEX.md` 是唯一的入口，刻意做得很小——AI 可以完整加载它，不会截断，需要深入时再按需读取其他文件。

---

## 前提条件

| 要求 | 说明 |
|------|------|
| Python 3.10+ | `python --version` |
| Shell 执行能力 | AI 客户端需支持运行终端命令 |

有 git 历史会更完整，但不是必须的。没有 git 历史时，`hotspots/` 的分析会被跳过，其余正常运行。

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

## 使用方式

把本地仓库路径告诉你的 AI：

```
帮我分析 /Users/me/projects/my-app 并生成知识库
```

AI 完成分析后会在仓库根目录写入 `.nexus-map/`。下次打开这个项目时，直接说：

```
读取 .nexus-map/INDEX.md
```

完整的上下文就这么接续了。

---

## 语言支持

按文件扩展名自动 dispatch，支持 17+ 语言：

Python · JavaScript · JSX · TypeScript · TSX · Java · Go · Rust · C++ · C · C# · Kotlin · Ruby · Swift · Scala · PHP · Lua · Elixir

未知扩展名静默跳过。多语言混合仓库无需任何配置。

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
    │   ├── git_detective.py  ← Git 热点与耦合分析
    │   └── requirements.txt
    └── references/
      ├── 01-probe-protocol.md
      ├── 02-output-schema.md
      ├── 03-edge-cases.md
      └── 04-object-framework.md
```

如果只是把 skill 本体复制到其他 agent 工作区，复制 `skills/nexus-mapper/` 这一层即可。

---

## License

MIT
