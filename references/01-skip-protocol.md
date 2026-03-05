# SKIP 协议 — 各阶段详细步骤

> L1 技术层 — 在执行对应阶段时按需加载

---

## S — SCAN 阶段

**前置验证**
1. 确认 `$repo_path` 目录存在
2. 确认 `$repo_path/.git` 目录存在 → 否则 `[!ERROR: NOT_A_GIT_REPO]` 停止

**执行步骤**
```bash
# 步骤 1: 运行 AST 提取器
python .agent/skills/nexus-mapper/scripts/extract_ast.py $repo_path \
  > $repo_path/.nexus-map/raw/ast_nodes.json

# 步骤 2: 运行 git 热点分析
python .agent/skills/nexus-mapper/scripts/git_detective.py $repo_path --days 90 \
  > $repo_path/.nexus-map/raw/git_stats.json

# 步骤 3: 生成文件树（AI Agent 执行，使用 list_dir 工具）
# 遍历目录，排除: .git/, node_modules/, __pycache__/, .venv/, dist/, build/, .nexus-map/
# 写入 $repo_path/.nexus-map/raw/file_tree.txt
```

**完成检查（任一失败 → 停止）**
- [ ] `raw/ast_nodes.json` 非空，包含 `nodes` 字段
- [ ] `raw/git_stats.json` 非空，包含 `hotspots` 字段
- [ ] `raw/file_tree.txt` 非空

---

## H — HYPOTHESIS 阶段

**阅读策略（优先级从高到低）**
1. `README.md` / `README.rst` — 项目总体描述
2. `pyproject.toml` / `package.json` / `pom.xml` — 技术栈与依赖
3. 主入口文件（`main.py`, `index.ts`, `Application.java`）
4. `raw/file_tree.txt` — 目录结构感知
5. `raw/git_stats.json` hotspots Top 5 — 最活跃文件

**产出假说**
- 使用 sequentialthinking 思考 3-5 步
- 识别 **≥3 个 System 级节点**，每个有初步的 `code_path` 假设

**记录格式**（工作记忆，不写文件）
```
[HYPOTHESIS LOG]
- System A: 推断职责=X, 代码位置=Y（置信度: 高/中/低）
- System B: 推断职责=X, 代码位置=Y（置信度: 高/中/低）
- 疑问: Z 目录归属不确定（将在 CHALLENGE 中质疑）
```

---

## C — CHALLENGE 阶段

**质疑协议 — 必须提出 ≥3 个质疑点**

每个质疑点格式：
```
Q{N}: [质疑陈述]
证据线索: [在哪里发现了矛盾或可疑之处]
验证计划: [EVIDENCE 阶段如何验证]
```

**质量要求**
- ❌ 禁止空洞质疑：「也许我理解得不够深入」
- ✅ 合格示例：「`git_stats` 显示 `services/auth.py` 变更频率是 `api/` 的 3 倍，这与我假设的业务逻辑集中在 `api/` 相矛盾」

---

## E — EVIDENCE 阶段

**对每个质疑点执行验证**
1. 用 `grep_search` / `view_file` 查找具体证据
2. 判断结果：
   - 质疑成立 → 修正节点的 `code_path` 或 `type`
   - 质疑不成立 → 确认原假说，标记验证通过

**最终节点校验（全部 System 节点逐一检查）**
- [ ] 每个节点 `code_path` 在 repo 中实际存在
- [ ] 无空洞 `responsibility`（不含禁止词，见 `02-output-schema.md`）
- [ ] 节点 `id` 全局唯一（无重复）

> 发现重大误判（关键系统完全识别错误）→ 允许返回 HYPOTHESIS 重建模型

---

## C — CRYSTALLIZE 阶段

**幂等性检查（写入前必做）**

| 检查结果 | 处理方式 |
|---------|----------|
| `.nexus-map/` 不存在 | 直接继续 |
| `.nexus-map/` 存在且 INDEX.md 有效 | 询问用户：「检测到已有分析结果，是否覆盖？[y/n]」|
| `.nexus-map/` 存在但文件不完整 | 提示「检测到未完成的分析，将重新生成」，继续 |

**写入顺序（先写 `.tmp/`，全部成功后移动到正式目录）**
```
1. .nexus-map/.tmp/concepts/concept_model.json   ← Schema V1
2. .nexus-map/.tmp/INDEX.md                       ← L0 摘要, < 2000 tokens
3. .nexus-map/.tmp/arch/systems.md                ← 各 System 边界
4. .nexus-map/.tmp/arch/dependencies.md           ← Mermaid 依赖图
5. .nexus-map/.tmp/concepts/domains.md            ← Domain 节点自然语言描述
6. .nexus-map/.tmp/hotspots/git_forensics.md      ← git 热点摘要
```
全部写入成功 → 移动 `.tmp/` 内容到 `.nexus-map/` → 删除 `.tmp/`

**edges 合并协议（写入 concept_model.json 前执行）**
1. 先导入 `raw/ast_nodes.json` 中的 edges（`imports`/`contains` 类型，机器层精确）
2. 追加 EVIDENCE 阶段推断的语义边（`depends_on`/`calls`）
3. 去重：`(source, target, type)` 三元组相同的边保留一条

**完成自检**
- [ ] `INDEX.md` 存在，无禁止词，< 2000 tokens
- [ ] `concept_model.json` 所有 System 节点有 `code_path`
- [ ] `arch/dependencies.md` 包含 ≥1 个 Mermaid 图
