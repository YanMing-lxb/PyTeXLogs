# 第 5 轮独立代码审查：hints 链路（只读）

- 审查对象：`src/pytexlogs/hints.py`、`parsers/{latex,biber,bibtex}.py` 旧提示表、
  `exporters/{json,sarif,csv}_exporter.py`、4 个 hints 测试文件、`docs/hints-reference.md`、`CHANGELOG.md`。
- 审查方式：只读通读 + 基线复跑 + 隔离探针（探针脚本位于 agent 工作区，未写入仓库）。
- 环境：Python `D:\Document YM\Desktop Document\Tools_Development\PyTeXMK\.venv\Scripts\python.exe`，
  `PYTHONPATH=D:\Document YM\Desktop Document\Tools_Development\PyTeXLogs\src`（绝对路径）。
- 范围限制：不回滚、不评价与本轮 hints 无关的历史改动；未 commit、未动 MiKTeX、未装 TeX 包。

## 结论摘要

### 基线复跑（仓库绝对路径下）

| 检查 | 结果 |
| --- | --- |
| `python -m pytest -q tests`（绝对路径） | **408 passed, 1 skipped**，与 `CHANGELOG.md:53` 一致 |
| `ruff check --config pyproject.toml src tests` | All checks passed（ruff 0.17.5） |
| `python -m compileall -q src\pytexlogs` | exit 0 |
| `python -m pytexlogs.cli --version` | `pytexlogs 0.6.1` |
| 规则数 | `len(RULE_IDS) == 41`，无重复，与 `docs/hints-reference.md` 41 行顺序一致（探针实测） |

> 备注：首次用相对路径 `tests` 跑 pytest 时收集到 321 个用例、2 个失败；定位为当前 shell 工作目录在
> PyTeXMK 仓库、相对路径解析到了 PyTeXMK 的测试目录。切到 PyTeXLogs 绝对路径后即 408 passed。
> 那 2 个失败属于 PyTeXMK 仓库，不在本轮范围，未做评价。

### 问题分级

| 级别 | 数量 | 编号 |
| --- | --- | --- |
| 阻塞 | 0 | — |
| 高 | 1 | H1 |
| 中 | 3 | M1、M2、M3 |
| 低 | 8 | L1–L8 |

**总体结论**：契约未被破坏，规则表/文档/测试三者一致，正则无灾难性回溯，基线全绿。
可合并；建议先处理 H1（死键 + 死分支），M1/M2 在下一轮顺手修掉即可。

---

## 逐项审查

### 1. 契约：`LogEntry`/`ReportEntry`、JSON/CSV/SARIF 形状、`rule_id` 追加

**结论：通过。**

- `LogEntry` 字段集合未变：`level/file/line/text/error_pos_text`
  （`src/pytexlogs/core/models.py:54-58`）；`ReportEntry` 字段 `level/file/line/text/error_pos_text/source`
  （`models.py:194-199`）。hints 链路没有向这两个 dataclass 加字段。
- JSON 条目字典仍只序列化既有字段：`level/file/line/text/error_pos_text`
  （`exporters/json_exporter.py:115-122`）；`source` 按既有约定不外泄（`json_exporter.py:107` 注释）。
  hints 以**新增顶层 `hints` 数组**方式挂载（`json_exporter.py:65-84`、`367`；载荷 `22-62`），
  `include_hints=False` 时回到旧载荷（`test_export_formats.py:57-58`）。
- CSV 表头未变：`file,line,level,category,tool,text,hint,source_path`
  （`exporters/csv_exporter.py:28`；`test_export_formats.py:98,134` 逐字断言）。
- SARIF 必填字段保留：`ruleId/level/message/locations/partialFingerprints`
  （`exporters/sarif_exporter.py:87-100`；`test_export_formats.py:75` 子集断言）；
  hint 放在 `result.properties["pytexlogs/hint"]`（`sarif_exporter.py:101-111`）。
- `rule_id` 只做追加：规则构造器一律不写 `rule_id`，由规则表统一注入
  （`hints.py:1582` `replace(hint, rule_id=rule.rule_id)`）；上下文替换与英文分支都保留 `rule_id`
  （`hints.py:1616`、`1646`）。全仓 `rule_id=` 仅这三处（grep 实测），无旁路写入。

### 2. 规则表正确性：`RULE_IDS`/`_RULES` 一致性、顺序、kind 覆盖

**结论：通过。**

- 探针实测：`_RULES` 41 条、id 唯一、`tuple(rule.rule_id for rule in _RULES) == RULE_IDS`
  （`hints.py:1550`）。
- 文档顺序与代码一致：解析 `docs/hints-reference.md` 41 行规则 id，与 `RULE_IDS` 逐一相等，
  无 doc-only / code-only 项（探针实测）。
- kind 映射（探针逐条语料实测）：绝大多数规则 1:1；唯一多分支是 `missing_file`，
  按后缀分流 `missing_graphic` / `missing_bib` / `missing_file`（`hints.py:286-315`），
  三个分支在 `test_hints_precedence.py` CORPUS 中均有断言。
- 非同名 kind 均有测试锁定：`biber_key_case`、`missing_delimiter`、`math_delimiter`、
  `command_conflict`、`missing_font_family`、`missing_font_tfm`、`missing_graphic`。

### 3. 正则安全：跨行贪婪、灾难性回溯、零宽/空捕获、计时

**结论：通过（无阻塞性问题）；有 1 条低风险观察 L7。**

- 计时探针（隔离脚本，仓库外）：

| 输入 | 规模 | 耗时 | 命中 |
| --- | --- | --- | --- |
| `Missing character` 无码位 ×5000 | 240 KB | 11.99 ms | missing_glyph |
| `Missing character` 带码位 ×5000 | 445 KB | 17.81 ms | missing_glyph |
| `Overfull \hbox` ×5000 | 300 KB | 45.17 ms | log_hint |
| `Citation ... undefined` ×5000 | 340 KB | 16.05 ms | undefined_citation |
| `Option clash` ×5000 | 250 KB | 22.11 ms | option_clash |
| 良性信息行 ×5000 | 320 KB | 43.73 ms | None |
| 1 MB 良性单行 | 1.00 MB | 140.87 ms | None |
| 400 KB 填充 + 未定义命令 | 400 KB | 34.11 ms | undefined_control |
| 5 万右花括号 / 1 万反斜杠 / 10 万空格 | — | 7.05 / 0.67 / 0.08 ms | None |
| 112,499 行 / 3.35 MB 混合日志 | 3.35 MB | 230.23 ms | undefined_reference |

- 未发现嵌套量词/交替导致的灾难性回溯；`.+?`/`.*?` 均未开 `DOTALL`，不跨行；
  排除换行的分组（`[^!\n]+`、`[^\n]*?`）已显式排除 `\n`（如 `hints.py:152-156`、`134-138`）。
- 零宽/空捕获：`_match_missing_number` 无 token 时返回空格串（`hints.py:1143-1150`），
  构造器内 `strip()` 兜底，不会产出空命令；其余捕获组均由 `\S+`/`[^']+`/`[^"]+` 等要求至少 1 字符。
- 观察 L7：`_MISSING_FILE_RE` 的 `[^']+`（`hints.py:124`）不排除换行，理论上可吞跨行文件名；
  真实日志文件名单行出现，概率低。

### 4. 优先级与工具隔离

**结论：白名单机制本身正确；存在 M3（部分 LaTeX 规则未挂白名单）。**

- 白名单判定（`hints.py:1567`）：
  ```python
  if rule.tools is not None and tool and tool not in rule.tools:
      continue
  ```
  `tools=None` 不限工具；工具名为空（未知上下文）放行；非空且不在白名单才跳过。
  白名单集合 `_LATEX_TOOLS = {latex, pdflatex, xelatex, lualatex, tectonic}`（`hints.py:342`）。
- 已挂白名单的规则：`float_overflow`、`no_output`、`math_mode`、`double_script`、
  `invalid_utf8`、`alignment_tab`、`package_error`（`hints.py:1521,1523,1525,1526,1531,1532,1545`），
  与 round4 F4 修复清单一致。
- `biber_case_mismatch` 作用域由匹配器把关（`hints.py:776-782`）：显式 `latex`/`bibtex`
  不命中；工具名为空时按 F6 设计放行。探针实测：`tool_name="latex"` → None，`tool_name="biber"` → 命中。
- 旧提示表按工具选择（`hints.py:1457-1475`）：未知工具返回 `{}`，避免 `WARN -` 跨工具误命中；
  `collect_hints()` 合并表仅在工具名为空时使用。
- **M3**：除上述 7 条外，其余纯 LaTeX 语法/排版规则（如 `undefined_control`、`end_mismatch`、
  `option_clash`、`missing_number`、`missing_item`、`extra_close_brace`、`missing_right`、
  `misplaced_noalign`、`illegal_unit`、`command_already_defined`、`no_line_to_end`、
  `hyperref_pdf_string`、`undefined_environment` 等）`tools=None`，在 biber/bibtex 后端日志下仍会执行匹配。
  当前后端消息文本不含这些串，实测未误报；但这与 round4 F4 的收尾方向一致地未做完
  （`round4-verify.md:152-155` 已列为观察项）。

### 5. 误报守卫：散文判定、引号/注释行剥离

**结论：主路径通过；存在 M2（整文散文线索误杀真实错误帧）。**

- 守卫链路：`_drop_quoted_lines` 剥离 `> `/`% `/`| ` 前缀行与成对引号包裹行
  （`hints.py:76-104`、`92`）；`_looks_like_prose` 按线索词判定（`hints.py:107-121`）；
  命中散文则整帧返回 None（`hints.py:1557-1562`）。
- 探针：round1 全部真实日志片段中未出现 ` means `/`says:`/` occurs`/` explained`/` tutorial`/
  ` changelog`/` in the faq`/`please fix`（grep 实测 0 命中）；帮助文本 `...for explanation.`
  不被 ` explained` 线索误杀（探针：`Missing $ inserted.` + manual/explanation 行仍命中 `math_mode`）。
- 剥离 `% ` 行：真实 TeX/biber/blg 日志不以 `%` 起行，未发现会丢真实日志的场景。
- **M2**：散文线索在**整段归一化文本**上判定（`hints.py:121`），不是按行。探针复现：
  `! Undefined control sequence.\nl.3 \\foo\nThis means you forgot a package.` → 整帧被抑制为 None。
  包警告续行里偶发 `This means ...` 时，真实错误会被一起吞掉。

### 6. 文案准确性：发行版/引擎命令与术语分工

**结论：主体正确；L1、L2、L4 为文案/规格偏差。**

- 安装命令双发行版：`tlmgr install <pkg>`（TeX Live）与 `miktex packages install <pkg>`
  （MiKTeX）成对返回（`hints.py:278-280`），由调用方按发行版挑选；未把两条命令写成“同时执行”。
- `fc-list` 平台标注：`missing_font` 与 `fontspec_font_not_found` 文案均注明 Windows 无 `fc-list`
  （`hints.py:457-462`；fontspec 分支同口径）。
- 容量命令分工正确：TeX Live 改 `texmf.cnf` 后 `fmtutil-sys --all`；MiKTeX
  `initexmf --edit-config-file=texmf.cnf` 后 `initexmf --dump`（`hints.py` capacity 构造器；
  参考 `round3-design.md:131`）。
- 文献写法差异正确：`\addbibresource{refs.bib}` 带 `.bib`；`\bibliography{refs}` 不带
  （`hints.py:703-704`、`757-758`、`765-766`）。
- 旧表未发现与结构化规则互相矛盾的残留建议；`Missing character` 旧表文案已不含 T1 fontenc 引导
  （`parsers/latex.py:56-59`）。
- **L1**：`undefined_reference` 重编译命令写死 `xelatex <主文件>.tex  # 再跑一轮`
  （`hints.py:720`），pdflatex/lualatex 项目也被建议 XeLaTeX；规则本身与引擎无关。
- **L2**：`invalid_utf8` 命令 `file --mime-encoding <主文件>`（`hints.py:1129`）是 Unix 工具，
  文案未像 `missing_font`/`fontspec` 那样标注 Windows 不可用。
- **L4**：`fontset_unavailable` 实现 `commands` 为空（`hints.py:471-488`），
  而 `round3-design.md:193` R22 规格要求命令 `xelatex <jobname>.tex`、
  `\usepackage[fontset=fandol]{ctex}`；属规格与实现漂移（低）。

### 7. 上下文替换、子文件保护、`language="en"`、`Hint` 不可变性

**结论：子文件保护与 en 分支通过；M1（裸 `<主文件>` 可被 `.log`/`.blg` 名污染）。**

- 占位符替换（`hints.py:1586-1616`）：`<jobname>` 替换 job；`<主文件>.tex` 走 `main_tex` 守卫
  （`hints.py:1601`：root 非 `.tex` 时退回 `job.tex`）；裸 `<主文件>` 直接替换成 `root`
  （`hints.py:1610-1611`）。
- **M1**：裸 `<主文件>` 没有 `.tex` 守卫。探针复现：`root_file="main.log"`（无 jobname）→
  `file --mime-encoding main.log`；`root_file="paper.log"` → `paper.log`；
  顶层 `entry.file="main.log"` 经 `hint_for_entry` 同样得到 `main.log`。
  受影响规则：`invalid_utf8`（裸占位符，`hints.py:1129`）。其余模板用 `<主文件>.tex`，已被守卫覆盖。
- 子文件保护：显式 jobname/root_file 时不以条目文件反推主文件；条目 file 含路径分隔符时不推导
  （`hints.py:1675-1680`）；`test_hints_false_positive.py:44-56` 覆盖 `chapters/intro.tex` 场景。
- en 分支：`language="en"` 用 `text_en` 展示，保留 `kind`/`commands`/`rule_id`
  （`hints.py:1640-1647`）；探针实测 `missing_bbl` en 输出 `rule_id=missing_bbl`、`text_en` 非空。
- 不可变性：`Hint` 为 frozen slots dataclass；上下文替换与 legacy 拼接均走 `dataclasses.replace`
  / 构造新 `Hint`（`hints.py:1494-1498`、`1616`、`1641-1647`），未发现原地改字段。

### 8. 国际化：`text_en` 覆盖、中英混排

**结论：通过。**

- 探针逐条喂 41 条语料（en 语言）：全部命中预期 `rule_id`，无 `text_en` 缺失；
  唯一被中文检测器命中的是 `cjk_missing_glyph` 文案里被引用的字形字符 `中`（U+4E2D），
  属数据而非翻译散文，不算夹生英文。
- 中文文案抽查：`biber`、`biblatex`、`fontspec`、`xeCJK`、`ctex`、`.bbl`/`.blg`、
  `kpsewhich`、`fc-list`、`initexmf` 均为专有名词/命令，未发现成句英文混入中文说明。
- 旧表英文键集合与 `collect_hints()` 一一对应（`test_hints_bilingual.py:51-55` 回归锁定）。

### 9. 测试质量：空断言、覆盖维度、实现细节写死

**结论：通过；无空测试。**

- 6 个 hints 测试文件中，每个测试函数都有明确 `assert`；未发现“只调用不抛异常”的空测试。
  `test_hints_deep.py:191-194` 只断言 `runaway`，`capacity` 在 `test_hints_real_logs.py` 另有覆盖，
  不算漏断言。
- 覆盖维度核对：
  - 匹配：`test_hints_precedence.py` CORPUS 41 条逐条断言 rule_id/kind；
  - 优先级：优先级对（`test_hints_precedence.py:197`）；
  - 无匹配：`test_hints_false_positive.py` 良性/散文/引号探针（`:12-37`）；
  - 工具作用域：biber/latex/bibtex 三向隔离（`test_hints_round4.py:94-100,134-141`、
    `test_hints_false_positive.py:40-65`）；
  - 项目上下文：jobname 替换、子文件保护（`test_hints_false_positive.py:70-93`、
    `test_export_formats.py:44-55`）；
  - false positive：引用块/注释/成对引号/说明性 FAQ 文本。
- 实现细节写死程度：CORPUS 快照锁定 rule_id/kind/提取值，属设计内快照（`round3-design.md:143`）；
  断言落在稳定契约（rule_id/kind/命令名/宏包名）上，未把正则分组号等内部细节写进断言。

### 10. 文档一致性：规则数、顺序、kind、CHANGELOG

**结论：主体一致；L3、L6、L8 为低优先级文档偏差。**

- `hints-reference.md`：41 行，规则 id 与顺序同代码一致（探针实测）；文档未列 kind 列，
  故不存在 kind 不一致问题。
- `CHANGELOG.md:52` 规则总数 **41**（`len(RULE_IDS)` 实测一致）；`:53` 测试数 **408 passed, 1 skipped**，
  与本轮复跑一致；`:103` 称旧表“共 15 键”，实测 LaTeX 9 + BibTeX 4 + Biber 3 = **16 键**（L6）。
- **L3**：参考表“工具作用域”列把多数 `tools=None` 的规则标成 `latex`/`pdflatex`
  （如 `missing_package` 行 15、`tfm_font_missing` 行 18、`capacity` 行 31），
  但代码对这些规则不做工具白名单限制，文档表述强于实际 enforcement。
- **L8**：`undefined_environment` 行（`hints-reference.md:27`）样例写 `Equationn undefined.`，
  而正则要求 `Environment <name> undefined`（`hints.py:729-730`）；样例缺 `Environment` 前缀，
  照抄不会命中。
- 用户可感知行为变化：工具隔离、散文守卫、双语言、规则数、F1–F13 回归均已在 CHANGELOG
  （`:15-53`）记录；未发现遗漏的对外行为变更。

---

## 发现的问题

### 阻塞（0）

无。

### 高（1）

#### H1 旧表重复条目键是死键，`--noskipduplicates` 追加分支为死代码

- 证据：
  - `parsers/biber.py:25-26`：`"entry `.+?' has"` 作为旧表键；
  - `hints.py:1478-1482`：旧表匹配是**子串**判定 `_normalize(key) in text`，`.+?` 被当字面量；
  - `hints.py:1491-1498`：`key.startswith("entry")` 时追加 `--noskipduplicates` 说明；
  - 对应英文条目 `hints.py:_LOG_HINT_EN` 同键。
- 复现（仓库外探针）：
  - `entry `Smith' has duplicate field` → 旧表 None，`hint_for_text(..., tool_name="biber")` → None；
  - `Duplicate entry key: 'Smith' in file 'refs.bib', skipping` → None；
  - `WARN - entry `Smith' has a duplicate key` → 只落到通用 `WARN -` 桶（`log_hint`）。
  即该键在任何真实/合成输入下都不可能命中，追加分支与英文条目均不可达。
- 背景：round2 已如实记录 `Duplicate entry key` 逐字告警未在 biber 手册定位，只证实“默认跳过重复键、
  `--noskipduplicates` 保留”行为（`round5-evidence-matrix.md:92`、`round2-specialized.md:189`）。
- 建议：二选一——① 待核实真实逐字文案后，把子串键换成已核实片段（如 `duplicate entry key`），
  或把旧表匹配升级为正则；② 在文案核实前，删除不可达的键、英文条目与 `key.startswith("entry")`
  死分支，避免误导后续维护者以为该建议已接线。不要在未核实文案前把猜测串写进匹配器。

### 中（3）

#### M1 裸 `<主文件>` 占位符会被 `.log`/`.blg` 路径污染

- 证据：`hints.py:1601` 只对 `<主文件>.tex` 做 `main_tex` 守卫；`hints.py:1610-1611`
  裸 `<主文件>` 直接替换成 `root`；受影响模板 `hints.py:1129`（`file --mime-encoding <主文件>`）。
- 复现：
  - `hint_for_text("! Package inputenc Error: Invalid UTF-8 byte sequence.", root_file="main.log")`
    → 命令 `file --mime-encoding main.log`；
  - `root_file="paper.log"`（无 jobname）→ `paper.log`；
  - 顶层 `LogEntry(file="main.log", ...)` 经 `hint_for_entry` → 同样 `main.log`。
- 影响：给用户的诊断命令指向日志文件而非源码；真实导出路径下 `root_file` 通常是 `.tex`，
  直接调库或条目文件为日志名时才触发。
- 建议：裸 `<主文件>` 也走 `main_tex` 守卫（root 非 `.tex` 时用 job.tex 或保留占位符），
  与 `<主文件>.tex` 口径一致。

#### M2 散文守卫按整段文本判定，续行中的说明性词语会误杀真实错误帧

- 证据：线索表 `hints.py:107-119`；整文判定 `hints.py:121`；提前返回 `hints.py:1561-1562`。
- 复现：`hint_for_text("! Undefined control sequence.\nl.3 \\foo\nThis means you forgot a package.")`
  → None（被 ` means ` 线索整帧抑制）。
- 影响：包警告/帮助续行偶发 `This means ...`、`... says ...` 等措辞时，首条真实错误拿不到规则建议；
  当前 round1 真实语料未触发，属潜在误报方向。
- 建议：线索按行判定（错误帧首行含 `!`/`Warning:`/`Error:` 时优先匹配规则），或把整文抑制改为
  “仅当整段不含任何错误标志词时才判为散文”；补一条“错误帧 + 散文续行”回归探针。

#### M3 部分 LaTeX 专属规则未挂工具白名单，后端日志下仍会执行匹配

- 证据：白名单判定 `hints.py:1567`；已挂白名单 7 条（见逐项 4）；其余纯语法/排版规则 `tools=None`，
  规则表 `hints.py:1505-1548`。
- 复现/现状：后端 `.blg`/`.blg` 文本实测不含这些串，暂未误报；但机制上 biber/bibtex 日志只要出现
  对应子串就会命中 LaTeX 规则（空工具名同样放行）。
- 背景：round4 F4 只收尾了 7 个类别，`round4-verify.md:152-155` 已把剩余规则列为观察项。
- 建议：按 F4 清单把纯 LaTeX 语法规则（`undefined_control`、`end_mismatch`、`option_clash`、
  `missing_number`、`missing_item`、`extra_close_brace`、`missing_right`、`bad_math_delimiter`、
  `misplaced_noalign`、`illegal_unit`、`command_already_defined`、`no_line_to_end`、
  `hyperref_pdf_string`、`undefined_environment` 等）补挂 `_LATEX_TOOLS`；
  `runaway` 按设计保持通用（见 `hints.py` 规则注释与 `test_hints_false_positive.py:36-39`）。

### 低（8）

| 编号 | 问题 | 证据 | 建议 |
| --- | --- | --- | --- |
| L1 | `undefined_reference` 重编译命令写死 `xelatex`，与引擎无关的规则给了引擎专属命令 | `hints.py:720` | 改为中性命令（如 `<engine> <主文件>.tex`/`latexmk`），或文案注明“用原引擎重跑一轮” |
| L2 | `invalid_utf8` 的 `file --mime-encoding` 为 Unix 工具，未标注 Windows 不可用 | `hints.py:1129-1131` | 参照 `missing_font` 文案补平台说明，或换成跨平台可执行动作 |
| L3 | 参考表工具作用域列强于代码 enforcement：多数 `tools=None` 规则被标 `latex`/`pdflatex` | `hints-reference.md:15,18,31` 等；`hints.py:1567` | 文档改“不限工具（当前未强制隔离）”，或代码补齐白名单 |
| L4 | `fontset_unavailable` 规格要求带两条命令，实现 `commands` 为空 | `hints.py:471-488`；`round3-design.md:193` | 补命令或更新设计文档口径 |
| L5 | 导出层不透传 `language`：CSV hint 列恒中文；JSON/SARIF 载荷虽同时存 `text`/`text_en`，但不按语言选择 | `csv_exporter.py:33-37`；`json_exporter.py:22-62`；`sarif_exporter.py:101-111` | 后续给导出器加可选 `language` 参数；当前 JSON 消费者可读 `text_en`，记录为既有行为 |
| L6 | CHANGELOG 称旧表“共 15 键”，实测 16 键（9+4+3） | `CHANGELOG.md:103`；探针实测 | 改为 16，或按表名分列计数 |
| L7 | `_MISSING_FILE_RE` 引号分组 `[^']+` 不排除换行，理论可吞跨行文件名 | `hints.py:124` | 改为 `[^'\n]+`；真实日志单行，优先级低 |
| L8 | 参考表 `undefined_environment` 样例缺 `Environment` 前缀，照抄不命中 | `hints-reference.md:27`；`hints.py:729-730` | 样例改为 `Environment equationn undefined.` |

---

## 与证据矩阵的一致性

### 有 round1 真实日志 + round2 手册/社区来源（证据充分）

`missing_package`、`missing_file`（图片/.bib/一般文件分支）、`font_not_loadable`、`tfm_font_missing`、
`unicode`、`missing_glyph`、`missing_bbl`、`undefined_citation`、`undefined_reference`、
`capacity`、`double_script`、`option_clash`、`missing_begin_document`、`extra_close_brace`、
`missing_right`、`bad_math_delimiter`、`misplaced_noalign`、`illegal_unit`、
`command_already_defined`、`no_line_to_end`、`hyperref_pdf_string`、`fontspec_font_not_found`、
`runaway`、`math_mode`、`no_output`、`alignment_tab`、`missing_number`、`missing_item`、
`end_mismatch`、`undefined_control`、`invalid_utf8`（仅 round1 无样例，见下）。

### 仅手册/官方文档来源，无 round1 真实日志

| 规则 | 来源 | 说明 |
| --- | --- | --- |
| `fontset_unavailable` | `ctex.pdf` §14 消息模板（`round5-evidence-matrix.md:29`） | round6 本机 MiKTeX 已实跑命中：B3a `adobe`（`round6-real-miktex.md`）；ctex/xeCJK 包 kpsewhich 已装 |
| `cjk_missing_glyph` | `xeCJK.pdf` §5 模板 + AutoFallBack（矩阵 :30） | 两种空格变体由 round4 测试锁定 |
| `missing_bib` | bibtex(1) manpage、`biblatex.pdf` §3.8.1、MiKTeX#541（矩阵 :36） | 无 round1 样本 |
| `biber_case_mismatch` | `biber.tex` 大小写敏感原文（矩阵 :35） | round6 本机 MiKTeX 已采真实 `.blg`：B3c `Key` vs `key`（`round6-real-miktex.md`）；重复条目键逐字文案仍以 dealii issue #389 样本为准 |
| `missing_right` | round2-official 数学族；SE 无同题高票帖（矩阵 :42，已如实记录） | 左右括号变体由 round4 测试覆盖 |

### 证据薄弱（仅合成语料，round1/round2 均无一手来源）

- `undefined_environment`：矩阵表未列来源；正则与文案基于内核通用消息形态，无真实日志回放。
- `invalid_utf8`：round1 无对应场景，round2 检索仅命中 inputenc/utf8 一般性讨论，未定位
  `Invalid UTF-8 byte sequence` 逐字消息来源；测试为合成串。
- `float_overflow`：`Too many unprocessed floats` 细分明确列入“未专门取证”
  （`round5-evidence-matrix.md:90`）；建议文案（`\clearpage`/`float` 宏包 `[H]`）属通用经验。

### 与矩阵不一致 / 矩阵未覆盖项

- H1（重复条目死键）在矩阵 :92 被标注为“逐字告警未定位”，但代码仍保留了一条不可达旧表键与
  死分支；矩阵没有把“该键当前不可达”这一实现状态记录下来，建议下一轮补记。
- L4（fontset 命令规格漂移）未在矩阵“仍未覆盖边界”中出现。

---

## 未覆盖边界

1. **真实 biber/BibTeX `.blg` 端到端日志**：round6 已在本机 MiKTeX 26.5 Portable 采到真实 `.blg`（B3c，biber 2.22，`Key` vs `key` 命中 `biber_case_mismatch`，biber 工具下无 `undefined_citation`/`undefined_reference` 抢答；见 `round6-real-miktex.md`）。本轮重复条目、`validate-datamodel` 等消息仍只靠手册原文与合成串验证；重复键逐字文案以 dealii issue #389 样本为准。round6 第二轮另补 LuaLaTeX 缺字体/缺字形与 biber 完整链路（L1/L2/B1-bbl/B2），细节见同一证据文档。
2. **证据薄弱规则的真实回放**：`undefined_environment`、`invalid_utf8`、`float_overflow` 缺 round1
   级别真实样本；合成语料不能证明正则对真实换行/续行/标点变体稳健。
3. **hints 匹配器性能门禁缺失**：`tests/perf/test_100k_lines.py` 只测解析器（<300ms），
   未对 hints 规则表做 10 万行级性能断言；本轮探针 3.35 MB / 112k 行 230 ms，无回归信号，
   但持续增长的规则表缺少 CI 护栏。
4. **非 BMP 字符 / emoji / nullfont 更多连锁形态**：矩阵 :90 已记录未专门取证；当前
   `nullfont` 分支仅覆盖探针列出的形态。
5. **MiKTeX 安装命令与 Windows 字体缓存路径**：B3c 已用真实 `.blg` 验证 biber 解析；文案中的 MiKTeX 命令（`miktex packages install`、
   `initexmf`）未在本机 MiKTeX 实机执行；Windows 下 `fc-list`/`file` 命令的可用性仅作文字说明。
6. **未知工具名的放行路径**：白名单对空工具名与未识别工具名放行（`hints.py:1567`）；
   第三方/自定义后端工具名进来时，`tools=None` 规则一律参与匹配，该组合未被测试穷举。
7. **导出层语言一致性**：CSV/JSON/SARIF 不接收 `language` 参数（L5），多语言导出场景未覆盖。
8. **超长/畸形输入 DoS**：本轮只测 1 MB 单行、5000 行重复、5 万括号等探针；未测 GB 级日志、
   深度嵌套花括号/括号序列、超长命令名等极端输入。
9. **F12 遗留**：`\newcommand{dice}` 这类漏反斜杠笔误，`undefined_control` 仍会提取
   `\newcommand`（矩阵 :88，低优先级未修），本轮确认现状未变。

## 修复结果（实现智能体）

> 本节由实现智能体在修复后回填；未改上述审查结论。环境与基线一致：
> `PYTHONPATH=D:\Document YM\Desktop Document\Tools_Development\PyTeXLogs\src`（绝对路径）。

| 编号 | 状态 | 修复要点 | 回归测试 |
| --- | --- | --- | --- |
| H1 | 已修（接线，未删除；二轮补强匹配优先级） | 联网核实到真实 biber 日志逐字片段：`WARN - Duplicate entry key: '<key>' in file '<file>.bib', skipping ...`（来源：dealii/publication-list#389 中成员粘贴的 biber 2.x 真实 `.blg` 输出，109 行同格式）。旧表死键 `` entry `.+?' has `` 换成子串键 `Duplicate entry key`；`--noskipduplicates` 追加分支改为 `key == "Duplicate entry key"` 真正可达；英文条目同键替换。二轮补强：`_match_legacy_hint` 不再按字典插入顺序返回首个命中，改为**多命中取最长键（最具体优先）**，通用兜底键 `WARN -` 显式排最后；`Duplicate entry key`、`I didn't find a database entry` 稳定优先于 `WARN -`，不依赖字典顺序 | `test_biber_duplicate_entry_key_hits_legacy_hint`（含 `--noskipduplicates`、不含通用文案；latex 不命中）、`test_biber_generic_warn_falls_back_to_warn_key`、`test_biber_missing_entry_key_beats_generic_warn` |
| M1 | 已修 | 裸 `<主文件>` 与 `<主文件>.tex` 同走 `.tex` 守卫：root 非 `.tex` 时退回 `job.tex`，无 job 且 root 非 `.tex` 时保留占位符；诊断命令不再指向 `.log/.blg` | `test_invalid_utf8_root_log_does_not_leak_log_name`、`test_entry_with_log_file_does_not_become_source` |
| M2 | 已修 | 散文守卫改为错误帧优先：首行含 `!` / `LaTeX Error:` / `LaTeX Warning:` / `Package <x> Error:` 即视为错误帧，续行散文词不整帧抑制；仅整段无错误标志词才按散文抑制。二轮补强：旧表兜底同受散文守卫约束，线索补 ` appears`、`the current font`；说明句里的 `Missing character` 子串不再返回字形建议，`Overfull/Underfull \hbox` 真实排版行不受影响 | `test_error_frame_with_prose_continuation_still_matches`、`test_plain_prose_still_suppressed`、`test_prose_missing_character_sentence_is_suppressed`、`test_real_layout_lines_still_hit_legacy_hint` |
| M3 | 已修 | 14 条纯 LaTeX 规则补挂 `_LATEX_TOOLS`：`undefined_control`、`end_mismatch`、`option_clash`、`missing_number`、`missing_item`、`extra_close_brace`、`missing_right`、`bad_math_delimiter`、`misplaced_noalign`、`illegal_unit`、`command_already_defined`、`no_line_to_end`、`hyperref_pdf_string`、`undefined_environment`；`runaway` 按设计保持通用；空工具名仍放行 | `test_latex_only_rules_skip_backend_tools_round5`（14 条 × biber/bibtex None，latex/空工具命中） |
| L1 | 已修 | `undefined_reference` 重编译命令由写死 `xelatex` 改为中性 `<引擎> <主文件>.tex`；英文同步 | `test_undefined_reference_command_is_engine_neutral` |
| L2 | 已修 | `invalid_utf8` 文案标注 `file --mime-encoding` 为 Unix/Linux 工具，Windows 替代为编辑器状态栏查看编码 / PowerShell 读字节 | `test_invalid_utf8_notes_windows_alternative` |
| L3 | 已修（随 M3 代码补白名单解决） | 审查提出的两条路线选了代码路线：所列纯 LaTeX 规则补挂白名单后，参考表“工具作用域”列与 enforcement 对齐；未改文档口径 | 同 M3 测试 |
| L4 | 已修 | `fontset_unavailable` commands 补齐 `xelatex <主文件>.tex` 与 `\usepackage[fontset=fandol]{ctex}`，对齐 round3 R22 | `test_fontset_unavailable_has_commands` |
| L5 | **本轮不做**（保留为已记录边界） | 导出层 `language` 透传未改：CSV hint 列恒中文；JSON/SARIF 载荷仍同时存 `text`/`text_en`，消费者可读 `text_en`。留待后续给导出器加可选 `language` 参数 | — |
| L6 | 已修 | 旧表键数口径改为实测 **16**（LaTeX 9 + BibTeX 4 + Biber 3） | 计数由 `collect_hints()` 实测；`test_legacy_hint_table_is_translated` 锁定英文无缺口 |
| L7 | 已修 | `_MISSING_FILE_RE` 引号分组 `[^']+` 改为 `[^'\n]+`，不再跨行吞文件名 | `test_missing_file_name_does_not_swallow_newline` |
| L8 | 已修 | 参考表 `undefined_environment` 样例改为 `! LaTeX Error: Environment equationn undefined.`，照抄可命中 | `test_undefined_environment_prefixed_sample_matches` |

### 修复后复验

- `python -m pytest -q tests`：**437 passed, 1 skipped**（跳过项仍为 `CI_PERF=1` 门控性能测试；二轮补强新增 4 条回归）。
- `ruff check --config pyproject.toml src tests`：**All checks passed!**（exit 0）。
- `python -m compileall -q src\pytexlogs`：退出码 **0**。
- `python -m pytexlogs.cli --version`：`pytexlogs 0.6.1`。
- `len(RULE_IDS)` 实测 **41**，无重复；H1 为旧表键替换，未增删结构化规则。
- 未 commit、未动 MiKTeX/系统环境变量、未安装 TeX 包；除本节约定回填的文档外，调研目录其余文件未改动。
- 遗留：F12（`\newcommand{dice}` 命令提取偏差）、L5（导出层语言透传）维持上一轮记录的未修状态。
