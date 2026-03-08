<p align="center">
  <img src="Icon.png" alt="nexus-mapper" width="96" height="96">
</p>

<h1 align="center">nexus-mapper</h1>

<p align="center">
  Map a repository once.<br>
  Give every later AI session a verified starting point.
</p>

<p align="center">
  <a href="README.zh-CN.md">中文文档</a>
</p>

---

## What It Does

nexus-mapper is a repository-mapping skill for AI agents. It analyzes a local codebase, writes a persistent `.nexus-map/` knowledge base, and gives the next session a concrete place to start instead of forcing it to rediscover architecture from scratch.

This is not a generic "summarize the repo" prompt. The skill runs a gated PROBE workflow, challenges its own first-pass assumptions, and only then writes final assets. That design matters: it reduces the usual AI failure mode of turning first impressions into fake certainty.

```
.nexus-map/
├── INDEX.md              ← Load this first. Full architectural context, under 2000 tokens.
├── arch/
│   ├── systems.md        ← Every subsystem: what it owns, exactly where it sits in the repo.
│   ├── dependencies.md   ← How components connect. Rendered as a Mermaid dependency graph.
│   └── test_coverage.md  ← Static test surface: what is tested, what is not, and where evidence is thin.
├── concepts/
│   ├── concept_model.json ← Machine-readable knowledge graph. Structured for programmatic use.
│   └── domains.md        ← The domain language this codebase speaks, in plain terms.
├── hotspots/             ← Present when git metadata is available.
│   └── git_forensics.md  ← Files that change constantly, and pairs that always change together.
│                           These are where bugs hide and where changes break things.
└── raw/                  ← Source data: AST nodes, git statistics, filtered file tree.
```

`INDEX.md` is the entry point. It stays small on purpose so an AI can load it in full, recover global context quickly, and then drill into deeper files only when needed.

Every generated Markdown file carries a provenance header with `verified_at` and downgrade notes. If the repository contains known-but-unsupported languages, or languages that only have module-level AST coverage, nexus-mapper says so explicitly instead of overstating parser confidence.

If a repository needs extra language support beyond the built-in language set, extend the run with `--add-extension` and `--add-query` first. If the configuration becomes too large for one command, switch to `--language-config <JSON_FILE>`.

---

## Why It Is Different

- It is phase-gated. PROFILE, REASON, OBJECT, BENCHMARK, and EMIT are not optional.
- It separates implemented, planned, and inferred systems so generated maps do not blur design docs with real code.
- It keeps a second tool, `query_graph.py`, for on-demand structural checks after the map exists.
- It is optimized for future sessions, not just the current one.

---

## Prerequisites

| Requirement | Check |
|-------------|-------|
| Python 3.10+ | `python --version` |
| Shell execution | Your AI client must support running terminal commands |

A git repository is recommended but not required. Without git history, the `hotspots/` analysis is skipped and the rest still runs.

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

## How To Use It

Point your AI at a local repository path:

```
Analyze /Users/me/projects/my-app and generate a knowledge map
```

The AI runs the protocol and writes `.nexus-map/` into the repository root. The next time you, or any other AI, needs to work on that codebase, start with:

```
Read .nexus-map/INDEX.md
```

That restores the global picture first.

When a task becomes local and precise, do not guess from the summary alone. Use the on-demand query tool against the generated AST data.

For the best long-term behavior, add a short persistent instruction to your host tool's memory file such as `AGENTS.md`, `CLAUDE.md`, or an equivalent file:

```md
If .nexus-map/INDEX.md exists, read it before starting work to restore global project context.

If the task requires local structure, dependency, impact, or boundary validation, return to the nexus-mapper skill's on-demand query guidance and use query_graph.py against .nexus-map/raw/ast_nodes.json instead of guessing.

When a task changes the project's structural understanding, assess whether .nexus-map should be updated before delivery. Structural understanding includes system boundaries, entrypoints, dependencies, test surface, language support, roadmap, and stage/progress facts. Pure local implementation details do not require a map update by default.

Treat .nexus-map as part of the project's memory, not as static documentation.
```

---

## On-demand queries

`scripts/query_graph.py` reads the generated `ast_nodes.json` and answers structural questions without re-parsing.

```bash
# File structure and imports
python scripts/query_graph.py .nexus-map/raw/ast_nodes.json --file src/server/handler.py

# Who imports a module?
python scripts/query_graph.py .nexus-map/raw/ast_nodes.json --who-imports src.server.handler

# Impact radius (upstream + downstream)
python scripts/query_graph.py .nexus-map/raw/ast_nodes.json --impact src/server/handler.py

# Enrich with git risk and coupling data
python scripts/query_graph.py .nexus-map/raw/ast_nodes.json --impact src/server/handler.py \
  --git-stats .nexus-map/raw/git_stats.json

# Top fan-in / fan-out hubs
python scripts/query_graph.py .nexus-map/raw/ast_nodes.json --hub-analysis

# Per-directory summary
python scripts/query_graph.py .nexus-map/raw/ast_nodes.json --summary
```

Zero extra dependencies. Pure Python stdlib.

Use it when you need facts such as:

- What is inside this file?
- Who imports this module?
- If I change this file, what else moves?
- Which internal modules behave like hubs?

The PROBE protocol uses it during REASON, OBJECT, and EMIT. You can also call it directly during development.

---

## PROFILE Stage Command

If you are running the scripts directly, the current baseline flow is:

```bash
python skills/nexus-mapper/scripts/extract_ast.py <repo_path> \
  --file-tree-out .nexus-map/raw/file_tree.txt \
  > <repo_path>/.nexus-map/raw/ast_nodes.json

python skills/nexus-mapper/scripts/git_detective.py <repo_path> --days 90 \
  > <repo_path>/.nexus-map/raw/git_stats.json
```

`--file-tree-out` uses the same exclusion rules as AST collection, so the file tree and AST scan stay aligned.

---

## Language support

Parses 17+ languages automatically by file extension.

Python · JavaScript · JSX · TypeScript · TSX · Bash · Java · Go · Rust · C++ · C · C# · Kotlin · Ruby · Swift · Scala · PHP · Lua · Elixir · GDScript · Dart · Haskell · Clojure · SQL · Proto · Solidity · Vue · Svelte · R · Perl

Not every listed language has the same depth. Some are full structural parses, some are currently module-only, and some may be explicitly requested but still unavailable if no parser can be loaded. The output metadata tells you which is which.

Unknown extensions are skipped silently. Mixed-language repositories work without any configuration.

### Extending language support

If built-in coverage is not enough, first extend the run directly from the command line:

```bash
python skills/nexus-mapper/scripts/extract_ast.py <repo_path> \
  --add-extension .templ=templ \
  --add-query templ struct "(component_declaration name: (identifier) @class.name) @class.def"
```

If the configuration is too large for a single command, pass a JSON file explicitly:

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

This keeps every language on the same contract: structural coverage if a parser and query exist, module-only if only the parser is available, configured-but-unavailable if the agent explicitly asked for a language but the environment cannot load it, unsupported if it is explicitly marked as such.

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
    │   ├── query_graph.py    ← On-demand AST query tool (file, impact, hub-analysis…)
    │   ├── git_detective.py  ← Git hotspot and coupling analysis
    │   ├── languages.json    ← Shared language config (extensions + Tree-sitter queries)
    │   └── requirements.txt
    └── references/
      ├── 01-probe-protocol.md
      ├── 02-output-schema.md
      ├── 03-edge-cases.md
      ├── 04-object-framework.md
      └── 05-language-customization.md
```

If you are copying just the skill payload into another agent workspace, copy the `skills/nexus-mapper/` directory.

---

## License

MIT

