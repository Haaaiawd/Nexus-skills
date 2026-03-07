<p align="center">
  <img src="Icon.png" alt="nexus-mapper" width="96" height="96">
</p>

<h1 align="center">nexus-mapper</h1>

<p align="center">
  Build a persistent knowledge base for any codebase.<br>
  New AI session, zero re-exploration.
</p>

<p align="center">
  <a href="README.zh-CN.md">中文文档</a>
</p>

---

## What you get

Run nexus-mapper on a repository once. It writes a `.nexus-map/` directory with everything an AI needs to understand the codebase — architecture, boundaries, hot files, dependency graph. Next time you open a chat window, the AI reads one file and already knows where everything lives.

The mapper challenges its own first-pass hypothesis before it writes final assets. It prefers a small number of evidence-backed corrections over padded issue lists or fake certainty.

```
.nexus-map/
├── INDEX.md              ← Load this first. Full architectural context, under 2000 tokens.
├── arch/
│   ├── systems.md        ← Every subsystem: what it owns, exactly where it sits in the repo.
│   └── dependencies.md   ← How components connect. Rendered as a Mermaid dependency graph.
├── concepts/
│   ├── concept_model.json ← Machine-readable knowledge graph. Structured for programmatic use.
│   └── domains.md        ← The domain language this codebase speaks, in plain terms.
├── hotspots/             ← Present when git metadata is available.
│   └── git_forensics.md  ← Files that change constantly, and pairs that always change together.
│                           These are where bugs hide and where changes break things.
└── raw/                  ← Source data: AST nodes, git statistics, filtered file tree.
```

`INDEX.md` is the entry point. It is intentionally small — an AI can load it in full without truncation, and then navigate to deeper files as needed.

---

## Prerequisites

| Requirement | Check |
|-------------|-------|
| Python 3.10+ | `python --version` |
| Shell execution | Your AI client must support running terminal commands |

A git repository is recommended but not required. Without git history, the `hotspots/` analysis is skipped; everything else runs normally.

**Install script dependencies before first use:**

```bash
pip install -r skills/nexus-mapper/scripts/requirements.txt
```
---

## Install

```bash
npx skills add haaaiawd/nexus-mapper
```

Works with Claude Code, GitHub Copilot, Cursor, Cline, and any client that reads `SKILL.md`.

---

## Usage

Point your AI at a local repository path:

```
Analyze /Users/me/projects/my-app and generate a knowledge map
```

The AI runs the analysis, then writes `.nexus-map/` into the repository root. The next time you — or any other AI — needs to work on that codebase, start with:

```
Read .nexus-map/INDEX.md
```

That's the full context, compressed and ready.

---

## Language support

Parses 17+ languages automatically by file extension.

Python · JavaScript · JSX · TypeScript · TSX · Java · Go · Rust · C++ · C · C# · Kotlin · Ruby · Swift · Scala · PHP · Lua · Elixir

Unknown extensions are skipped silently. Mixed-language repositories work without any configuration.

---

## Repository structure

```
nexus-mapper/
├── README.md
├── README.zh-CN.md
├── Icon.png
├── evals/                        ← Evaluation assets and test plans for iterating on the skill
└── skills/
  └── nexus-mapper/
    ├── SKILL.md              ← Execution protocol and guardrails
    ├── scripts/
    │   ├── extract_ast.py    ← Multi-language AST extractor
    │   ├── git_detective.py  ← Git hotspot and coupling analysis
    │   └── requirements.txt
    └── references/
      ├── 01-probe-protocol.md
      ├── 02-output-schema.md
      ├── 03-edge-cases.md
      └── 04-object-framework.md
```

If you are copying just the skill payload into another agent workspace, copy the `skills/nexus-mapper/` directory.

---

## License

MIT

