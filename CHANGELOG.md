# Changelog

## v0.6.4 - 2026-11-24

### ✨ 新增

- ⏱️ **流水线分段计时**：`PipelineMeta` 新增 `parse_ms`、`refs_ms`、`render_ms`；`duration_ms` 语义保持不变（仍是解析阶段），旧消费方不受影响。PyTeXMK 可据此把「日志分析」从 Python 残差里单独核对。
- 💬 **一行版 hint**：`Hint` 新增 `brief` / `brief_en`；`print_summary(..., hint_style="brief")`（默认）只输出一行说明，`"full"` 保留完整排查步骤与 `$ 命令`，供 `-r --verbose` 或排障使用。
- 🦶 **统一页脚**：新增 `format_footer(has_errors=...)`，摘要末尾只给一条「下一步」，不再重复分组标题里的计数；无 ERROR 时不会让人去修不存在的问题。
- 🧾 **非 ASCII bib 键提示**：新规则 `bib_key_non_ascii`，把 BibTeX 的 `database entry for "…"` 告警直接指向「键名含非 ASCII 字符，改成纯 ASCII 后重跑」，不再落进通用兜底。
- 🗂️ **索引样式说明符提示**：新规则 `makeindex_style_specifier`，解释 `Unknown specifier lethead_*` 是 `.ist` 与 makeindex 版本不匹配，索引产物已生成即可忽略。

### ♻️ 变更

- 🔇 **`Unknown specifier` 降级**：MiKTeX 的 `Input style error ... Unknown specifier lethead_*` 由 ERROR 改为 WARNING；同一份 `.ilg` 已写明 `0 warnings` 且索引产物正常时，成功摘要不再凭空出现「3 个错误」。
- 🧹 **hint 去重**：同一 `(rule_id, 规范化文案)` 只显示一次；biblatex 的 undefined citation 同时出现在 `.blg` 与 `.log` 时不再重复两条提示。
- 🔤 **8-bit 日志兜底**：`read_log_text` 在 `utf-8-sig` / `gb18030` 都失败后追加 `latin-1`，TeX 直接吐出的 `Eri\xb3en` 不再被替换成 U+FFFD（GBK/Shift-JIS 仍先走 CJK 编码，不会被 latin-1 抢先误解）。

### 🧪 测试

- ✅ 全量 **762 passed, 6 skipped**；新增 `tests/test_2026_11_24_fixes.py` 覆盖 brief/full、非 ASCII 键、索引降级、页脚分支、hint 去重与 latin-1 兜底；`ruff` 全绿。

## v0.6.3 - 2026-11-23

### ✨ 新增

- 📐 **摘要宽度可配置**：`print_summary(..., width=N)`、`show_log_entries(..., width=N)`、`run_pipeline(..., summary_width=N)` 与 CLI `--width N` 统一覆盖默认 74 列版式；PyTeXMK 等调用方可按自身控制台宽度传入，低于 40 列时自动收敛到 40，避免版式被压坏。
- 🪜 **换行悬挂缩进**：条目正文、hint、可执行命令与统计行折行后，续行均与首行文本起始列对齐；路径超宽时保留 `:line` 并做中间省略，正文区至少保留 12 列。
- 🧮 **CJK 显示宽度**：标题、条目和分隔线改用 `unicodedata.east_asian_width` 计算显示列数（全角/宽字符按 2 列），修复中文标题居中/分隔线长度偏差。

### ♻️ 变更

- 🧱 **摘要版式统一**：等级标题沿用旧版 `==== 错误汇总 · 3 ====` 居中横幅（保留条数），分类标题沿用 `+-- [一般编译] · 3 ---` 框线；移除 0.6.3 开发中新增的整行 `─` 底边。条目 4 列起、hint 8 列起、命令 10 列起，宽度与悬挂缩进保持可配置。
- 🎨 **颜色收敛**：error / warning / info 保留红黄蓝，`typesetting` / `font` / `graphic` / `page` 统一 dim 灰，仅用 `[T]` / `[F]` / `[G]` / `[P]` 区分，避免弱对比色相堆叠。
- 🏷️ **标题与统计**：CLI 文本头改为本地化计数形式（如 `PyTeXLogs 摘要 · 17 条 · 0 个错误 · 3 个警告 · 14 个提示`），类别/解析器统计改为显示标签并支持按段折行。
- 📚 **参考文献块**：总计行修复中文 `篇 ，` 多空格与英文 `Total 12 ,Unchanged 8` 的逗号/行尾空格；Top 引用 key 列宽随版式宽度收缩。
- 💡 **Hint 命令**：hint 内的可执行命令单独成行并加 `$` 前缀，续行对齐命令文本；日志正文进入 rich markup 前统一转义，避免 `[foo]` 被当成样式标签。
- 🖥️ **demo 宽度**：`pytexlogs demo --width N` 的标题框与摘要同步使用指定宽度。

### 🐛 修复

- 🖼️ **缺文件提示跨行**：`_MISSING_FILE_RE` 不再排除换行，TeX 79 列硬折行拆开的文件名（如 `pressure_cold_` + `layer5.pdf`）重新命中 `missing_file` / `missing_graphic`，不再退回 `package_error` 兜底；提示文案与 `kpsewhich` 命令里的文件名会接回完整名称。

### 🧪 测试

- ✅ 全量 **749 passed, 6 skipped**；新增 `tests/test_summary_layout.py` **9** 个回归，覆盖宽度收敛、悬挂缩进、旧版分隔线、CJK 宽度、参考文献空格、hint/命令对齐、`run_pipeline` / `show_log_entries` / CLI `--width` 透传；`ruff` 全绿。

## v0.6.2 - 2026-11-22

### 🐛 修复

- 🧩 **解析与去重**：LaTeX 修复连续 Info/Warning 重复入队、文件栈误弹、含空格路径、`(biblatex) main` 续行、截断 `Missing character`、BOM/CRLF 与点号 jobname；BibTeX 修复多行 `Warning--` 重复记录、O(1) 去重与警告计数；Biber 接入 `Found N citekeys`，`unique_citations` 取同目录 `.bcf` 去重键数。
- 🚀 **流水线与路由**：executor 统一为 `iter_steps()` / `StepOutcome`，parser 异常保留 `parse_exception`；`run_pipeline` 未给 `jobname` 时自动推断，`steps=None` 时并入 `captured_outputs` 的 key；`.xlg` 路由 Xindy，`.blg` 按头部优先于陈旧 `.bcf`，引用追踪先读 `.aux` 标记；`.bcf` 不再作为通用日志后缀，仅作 Biber citekey 统计输入。
- 💡 **提示与展示**：17 条 LaTeX 规则补齐工具作用域，`runaway`、`missing_bbl` 不再误报；英文 `commands_en` 补全；`show_log_entries()` 支持 `ToolResult`、`ToolResultReport` 与混合列表；plain/stream 摘要保留 `[一般编译]`、`[E]` / `[W]` 和参考文献块标签。
- 📦 **导出与契约**：`to_json` 支持报告、`ParsedLog`、单条/混合条目并输出 `parse_exception`；CSV 对 `= + - @` 开头单元格加 `'` 防公式注入；`--no-hints` 对 JSON/CSV/SARIF 生效；`write_report` 失败返回 `None`，`run_pipeline` 记录 `_report_write_error`；`aggregate_stats` 非法 `group_by` 抛 `ValueError`，第三方 parser 返回 `None` 抛清晰 `TypeError`。
- 🛡️ **健壮性**：非法 `ignore_patterns` 只告警；过滤后统一重算等级桶、错误/警告、盒子与未定义引用计数；未知引用源不清空缓存；状态写入失败不穿透；`load_report` 对非 JSON object 给出可读错误。
- 🧷 **CLI 与可见性**：CLI 接受裸路径参数；解析失败通过 `parse_exception` 显式暴露，不再静默丢失。
- 🔒 **状态保护**：状态文件写入前校验版本，陌生或更高版本 schema 不会被降级覆盖。
- 🎯 **导出过滤**：`min_level` 对列表形态的 `ParsedLog` 同样生效（`to_json` / `to_csv` / `to_sarif`）。

### ♻️ 变更

- 🧹 删除未使用的正则、常量、旧转发与重复统计代码；xindy 与 BibTeX/Biber 路径处理收敛到共享模块；等级展示合并为 `_LEVEL_DISPLAY`，`_group_by` 改为 O(1) 归组。
- 🧮 **统计契约统一**：stats 结构归一为一套契约；`aggregate_stats` 纳入 `__all__` 公共 API。
- 🔤 **未定义引用文案**：提示改为英文（**BREAKING**，依赖中文文案的下游需更新）。
- 🧹 移除未使用的 `bib_empty_re`。
- ⚡ 继续 Python 3.15 现代化：移除冗余 `__future__` 导入，递归扫描用 `Path.walk()`，原子写统一 `Path.open/replace/unlink`。
- 🧩 `hints` 规则仍为 **41** 条；`CATEGORY_ORDER` 增加 `external` / `custom`；`BaseLogParser.parse_file()` 通过 `_source_path_hint` 让 Biber 定位同目录 `.bcf`。

### 🧪 测试

- ✅ 全量 **706 passed, 6 skipped**；覆盖率约 **88%**；`CI_PERF=1` 性能 **6 passed**；`ruff` 全绿；`compileall` 通过；wheel 独立安装后 `pytexlogs --version` 为 `0.6.2`。
- 📊 保留 12 份真实 MiKTeX 26.5 日志 fixture，相关测试 **38 passed**；Round 8/9 新增 **26** 个回归。

## v0.6.1 - 2026-11-18

### 破坏性变更（无兼容层，旧接口一律删除）



* `run_pipeline`**&#x20;只保留一套签名**：删除 0.4/0.5 的 `tex_engine` / `tex_output` / `bibtex_output` / `biber_output` / `other_engine_outputs` / `quiet` 旧位置参数与 `write_report` 旧名（连同其 `DeprecationWarning`）。捕获输出统一用 `steps=` + `captured_outputs=`。

* **删除&#x20;**`pytexlogs/__init__.py`**&#x20;中的别名**：`run_log_pipeline`（`run_pipeline` 的 DeprecationWarning 包装）、`Manager` / `Registry` / `Report`（`LogParserManager` / `LogParserRegistry` / `ParsedPipelineReport` 的裸别名）。请直接使用真实类名。

* **删除&#x20;**`StateFileCorrupted`：该异常从未被 `raise` 过，抛出即死代码；状态文件损坏统一降级为空骨架并记日志。

* **删除&#x20;**`reftracker`**&#x20;的&#x20;**`input_re`**&#x20;/&#x20;**`citation_command_re`：定义并导出但全库无调用者。

* `LogParserRegistry.get_instance()`**&#x20;不再返回空表**：改为委托 `get_default_registry()`；原先 `get_instance()` 返回 "什么都没注册" 的实例属于静默失效陷阱。

* `easy.parse_log_file(engine=...)`**&#x20;未知引擎直接&#x20;**`ValueError`：不再静默回退 pdflatex；可选值由 registry 的 `all_step_names()` 列出。

* `bibtex`**&#x20;注册后缀移除&#x20;**`.bcf`：`.bcf` 是 biber 的 XML 构建文件，不是 bibtex 的日志。

### 修复



* `TYPESET`**&#x20;排序错误**：`LogLevel` 重排为 `ERROR(0) WARNING(1) INFO(2) TYPESET(3) FONT(4) GRAPHIC(5) PAGE(6)`。0.5 的 `ERROR < WARNING < TYPESET < INFO` 让 "提示" 排在 `INFO` 之前，`filter_severity(min_level=INFO)` 的过滤结果与语义相反。

* **报告回读把&#x20;**`font/graphic/page`**&#x20;降级成&#x20;**`info`：`_VALID_LEVELS` 改为由 `LogLevel` 派生，CLI 的等级映射删除自建表，统一走新增的 `level_from_value()`。

* `--severity all`**&#x20;漏掉提示级**：`all` 原映射成 `LogLevel.INFO`，把 `TYPESET`/`FONT`/`GRAPHIC`/`PAGE` 一起滤掉；改为映射枚举末级（不过滤）。

* `print_summary`**&#x20;整组丢弃排版提示**：`display/formatter._group_by` 的等级表只写死 `error/warning/info`，`TYPESET` 条目虽有解析结果却从不进入摘要；改为按 `_LEVEL_ORDER` 派生映射，并在 `show_info=True` 时展开 "排版提示汇总" 分组。

* `severity_counts`**&#x20;丢桶**：分级桶按枚举动态生成，不再只写死 `error/warning/typesetting/info`（否则 `font/graphic/page` 计入 `total` 却没有自己的桶）。

* **编码兜底静默乱码**：候选顺序改为 `utf-8-sig → utf-8 → gb18030`，删除 `latin-1`（对任意字节都能解码，等于永不失败地把乱码交给解析器）与冗余 `gbk`（`gb18030` 是其超集）；全部失败时 `utf-8 + errors="replace"` 并 `warning`。`models.BaseLogParser._read_log_text` 的第二份编码列表删除，统一委托 `utils.encoding.read_log_text`。

* **状态文件并发丢键**：`ProjectStateStore.update_build/update_refs` 改为 `_update_section()` 全程锁内读 - 改 - 写；0.5 在锁外读快照、锁内合并，会把过期快照覆盖别人刚写的键。

* `clear()`**&#x20;抹掉别人的命名空间**：改为 `remove_namespace("pytexmk")` + `_prune_if_empty()`（仅剩 `schema_version/timestamp/jobs` 才删文件），不再整份 `unlink`。

* **CLI 异常无任何可见输出**：`_configure_logging()` 挂 stderr handler（`PYTEXLOGS_DEBUG=1` 开 `DEBUG` 含堆栈），`except Exception` 同时向 stderr 打印类型与消息。

* `explain`**&#x20;文案硬编码中文**：空输入 / 无匹配 / 无结果三条提示走新增 `_MSG`（zh/en）。

* `LogParserManager`**&#x20;死分支**：删除 `_fallback_registered` 与 `discover_log_path` 中两条都 `return None` 的分支；`run()` 统一走 `discover_log_path`。

* `RefChangeTracker.detect_mode`**&#x20;整份读 aux**：改为逐行流式扫描，命中即返回。

* **报告反序列化吞掉&#x20;**`TypeError`：删除 `_from_dict_simple` 的 `try/except TypeError` 兜底与 `_unknown_keys_*` 污染键；未知字段直接进 `custom_fields`。

* `schema_version`**&#x20;两处字面量**：新增 `models.REPORT_SCHEMA_VERSION = 1`，写盘 / 回读共用同一常量。

### 变更



* 覆盖率不再 `omit` 12 个核心模块（`engine` / `report` / `manager` / `reftracker` / 6 个 parser 等）；覆盖率低就补测试，而不是隐藏被测对象。

* `display/printer.py` 删除仅供日志分支使用的 `_format_separator_old`（连同 `_LEVEL_ANSI` / `_ANSI_RESET`），日志与终端共用同一份分隔符。

* `display/printer.py::print_summary` 的 12 处 `if use_logger / elif stream / else` 三路分派收敛为单一 `emit()`：原先每加一段输出就要抄一遍三分支，漏改一处就会让终端与日志里的同一段内容不一致（返回字符串也可能漏记）。

* `core/state.py` 内联 `_monotonic/_time_now/_sleep` 三个纯转发封装。

* `hints.py`**&#x20;改为规则表**：28 条匹配模式收敛成 23 条 `_Rule(rule_id, match, build)`，`_hint_for_text_raw` 只按表顺序跑一遍；顺序本身是语义（`Emergency stop` 必须先于 `Undefined control sequence`），因此新增 `RULE_IDS` 快照供测试断言。原先是一段 250 行的 if 阶梯，新增规则要手工找插入位置，改错顺序不会有任何提示。

* **CLI 聚合层直接建在报告模型上**：`_collect_from_paths` 统一返回 `list[ToolResultReport]`，删除 CLI 内的 `ToolResultReport → ToolResult` 转换（以及 `_aggregate_stats`/`_filter_against_baseline`/ 文本摘要对它二次拆装的代码）。两套模型之间只保留一个转换点 `ToolResultReport.from_parsed_log()`（单文件 `ParsedLog` 并进报告列表时用），`_as_parsed_logs()` 只服务展示层（`print_summary` 需要枚举等级）。

* **导出器支持报告列表**：`to_json` / `to_csv` / `to_sarif` / `filter_by_level` / `_flatten_to_entries` 均可接受 `list[ToolResultReport]`；`ReportEntry → LogEntry` 的等级映射抽成 `_report_entry_to_log_entry()` 一处，替代各导出器自建映射表。

* **README API 表与真实导出对齐**：删掉 0.6.1 已删除的别名（`run_log_pipeline` / `Manager` / `Registry` / `Report`，照文档抄会直接 `ImportError`），补上 `ToolResultReport`（含 `from_parsed_log`）、`level_from_value`，`LogLevel` 枚举补齐到 7 级。

### 修复



* `--baseline`**&#x20;指向不存在的文件**：原先 `FileNotFoundError` 冒到 CLI 顶层，用户只看到 “CLI 异常” 与堆栈；现在打印 `基线报告不存在：<path>（先用 --output 导出一次 JSON 报告）`（中英双语）并以 2 退出。

* **过滤到空仍打印统计**：`--baseline` 把条目全部过滤掉后，摘要依旧输出 `By category: compile=1`（统计的是 “结果个数”，看着像有内容）；现在空结果不再参与统计，文本模式提示 “没有新增条目”，JSON 输出 `results: []`。

### 行为变化（`--format json`）



* CLI 导出的 `results[*]` **不再包含&#x20;**`raw_text`：文件模式下它会把整份日志原文再抄一遍，与 `entries` 重复；库 API `to_json(list[ToolResult])` 形状不变。

* 单文件输入的 `tool_name` 改为解析器标识（如 `latex`），不再取文件后缀（如 `log`）；`category` 仍为 `compile`。

### 测试



* `test_state_store.py::test_state_file_corrupted_exception_is_exportable` 改写为 `test_broken_json_degrades_to_empty_skeleton`（验证损坏 JSON 降级为空骨架）。

* 新增 `tests/test_level_semantics.py`：锁定 `ERROR < WARNING < INFO < TYPESET < FONT < GRAPHIC < PAGE`、"`--severity all` 保留提示级 "、"`--severity warning` 过滤 Overfull" 三条语义。

* 新增 `tests/test_hints_bilingual.py`：23 条语料覆盖 `hints.py` 全部规则分支，断言每条规则中文含汉字、`--lang en` 输出无汉字；并锁定内建提示表（LaTeX 9 + BibTeX 4 + Biber 3，共 16 键）英文说明无缺口，避免英文环境回退到中文。

* 新增 `tests/test_hints_precedence.py`：`RULE_IDS` 顺序快照 + 30 条语料逐条断言命中规则（要求每条规则都有覆盖）+ 5 组优先级对（致命 > 未定义命令、缺 `.sty` > 缺文件、缺字形不被 “字体未找到” 抢答、多行错误 > 内建提示、缺宏包 > 宏包错误）。

* 新增 `tests/test_cli_report_pipeline.py`：锁定 CLI 收集返回报告模型、`from_parsed_log` 是唯一转换点、`--format json` 字段形状、`--baseline` 缺文件的可读报错、基线过滤到空后的输出。

* `test_summary.py` 新增 `test_typesetting_entries_are_grouped`（`show_info=True` 时 Overfull 进入 "排版提示汇总" 分组）。

* 全量：**239 passed, 1 skipped**。

## v0.5.0 - 2026-11-16

### 新增



* **可执行建议（hints）**：新增 `pytexlogs/hints.py`。`Hint(text, commands, kind)` 把每条错误 / 警告映射为 "人话解释 + 可直接复制的命令"：


  * 缺宏包抓 ``File `x.sty' not found`` 与 `Package X Error:`，给出 `tlmgr install X` / `miktex packages install X` 两条命令；

  * `hint_for_text` / `hint_for_entry` 支持 `jobname` / `root_file` 上下文，把 `biber <jobname>`、`xelatex <主文件>.tex` 替换成 `biber main`、`xelatex main.tex`；

  * 未定义控制序列、`Overfull \\hbox`、缺字体、biber/bibtex 常见错误等均有对应建议；

  * 匹配前做反斜杠归一化，日志里的 `\hbox` 与提示表里的 `\\hbox` 不再错配；

  * 新增高频规则：`Unicode character ...`、未定义 `Citation`/`Reference`/`Environment`、找不到 `.bib`、`Missing character`、`Too many unprocessed floats`、`TeX capacity exceeded`、`No pages of output`、`Runaway argument`、`Missing $ inserted`、`Emergency stop`、`Package ... Error`；

  * **修正误判**：不再把任何 `Package X Error:` 都当成 "缺宏包 X"（fontspec 找不到字体时曾误报 `tlmgr install fontspec`）。

  * **中英双语**：`hint_for_text` / `hint_for_entry` 新增 `language` 参数；`Hint.text_en` 覆盖全部内置规则，`--lang en` 下摘要与 `explain` 的建议正文都是英文，不再是中文。

* **日志类型嗅探**：新增 `core/logkind.py`。`sniff_bib_tool()` 按 `.bcf` 优先判断 biber、再看日志头；`sniff_index_tool()` 区分 xindy/makeindex；`sniff_tex_engine()` 从 `.log` 头部识别 pdflatex/xelatex/lualatex；`plan_default_steps()` 按实际存在的 `.blg/.bcf/.ilg/.glg/.alg/.slg/.nlg/.pytxcode/*.asy/*.pygmented` 规划步骤，每份日志只归一个 step，并用真实引擎名作为首个 step。

* **Shell 补全**：新增 `--completion bash|zsh|fish|powershell`，选项从 argparse 自动提取，输出纯文本脚本后退出，不混入摘要。

* **递归目录扫描**：新增 `--recursive`，批量检查时只进入真正含 `.log/.tex` 的子目录，支持一个仓库多个子项目。

* **报告与过滤**：`write_report_file()`（`write_report` 保留为兼容别名并 `DeprecationWarning`）；`language` / `summary_max_entries` 参数；`--jobname`、`--severity` 同时作用于 text/json/csv/sarif；`--baseline` 只保留新增 / 变化条目；`--max-entries`、`--no-hints`、`--open-all`。

* `explain`**&#x20;子命令**：对单条日志 / 单条消息给出归类与建议，不生成整篇报告。

* **SARIF 升级**：`tool.driver.rules`、`partialFingerprints`、相对路径 + 正斜杠 + `quote`，可直接被 GitHub Code Scanning 消费；非 error/warning 映射为 `note`。

### 修复



* `sniff_index_tool`**&#x20;回退永远判成 xindy**：`Path.glob()` 返回生成器，`if parent.glob("*.xdy")` 恒为真；改为 `any(...)`，只有真的存在 `.xdy` 才回退 xindy。

* **缺图片被误判成缺宏包**：`detect_missing_package` 只认 `.sty/.cls/.def/.cfg/.clo/.ldf`；`fig.png` / `refs.bib` 分别给出 `missing_graphic` / `missing_bib` 建议，不再输出 `tlmgr install fig.png`。

* **Windows 编辑器路径被&#x20;**`shlex`**&#x20;吃掉反斜杠**：`shlex_split` 在 Windows 使用 `posix=False`，`custom:` 也走同一分词逻辑。

* **本地化条目没有 hint**：LaTeX parser 把引用 / 交叉引用条目翻译成 “找不到 citation/reference `key`”，hint 现在同时匹配英文原文和本地化文本。

* **baseline / SARIF 行号漂移误报**：baseline 去重键与 SARIF `partialFingerprints` 不再包含行号，正文插入几行不会把旧问题当成新增告警；行号仍保留在 `region.startLine` 和展示中。

* `explain`**&#x20;无上下文**：`pytexlogs explain ... --jobname main --root-file main.tex` 现在会把建议里的占位符替换成真实命令。

* **报告写盘 100% 失败**：`core/report.py` 误写 `from .exporters`（应为 `..exporters`），异常被吞后一直表现为 "没有报告"。

* **状态锁形同虚设**：`core/state.py::_mutate` 未获锁时仍然写盘；现在直接返回 `False`，不写。

* **JSON/CSV 列表输入崩溃**：`json.dumps(default=...)` 处理 `LogLevel` 枚举；CSV 换行压成空格、列序固定。

* **同一条警告打印两遍**：`print_summary(stream=...)` 支持 CLI 捕获，不再 "先流式打一遍、再汇总打一遍"。

### 变更



* 目录模式 `run_pipeline(..., print_terminal=False)`；无 `.tex` 时用最大 `.log` 的 stem 推断 jobname；`_default_lang()` 读 `PYTEXLOGS_LANG`/`LANG`/locale。

* `print_summary` 支持分组截断（"… 还有 N 条"）与 `↳ 建议` 行。

* 公共 API 新增导出：`Hint`、`detect_missing_package`、`hint_for_entry`、`hint_for_text`、`filter_by_level`、`plan_default_steps`、`sniff_bib_tool`、`sniff_index_tool`。

### 测试



* 新增 `tests/test_050_features.py`（21 例）、`tests/test_hints_deep.py`（14 例）与 `tests/test_completion.py`（6 例）：报告落盘无 `.tmp`、旧 kwarg 兼容、步骤不重复、index 嗅探（含无 `.xdy` 回退）、引擎嗅探、单反斜杠匹配、缺宏包命令、缺图片 / 缺 bib 分类、hint 上下文替换、中英文 hint、多格式 severity 过滤、SARIF URI / 指纹、baseline 行号漂移、递归目录扫描、全局选项位置、同条警告只打一次、锁失败不写盘、报告失败无 `.tmp`、补全脚本；以及 Unicode / 引用 / 环境 / 缺 bib / 容量 / 致命错误等新建议。

* 全量：**162 passed, 1 skipped**。

## v0.4.0 - 2026-10-18

### 破坏性变更



* **最低 Python 版本提升到 3.15**：`requires-python` 从 `>=3.14` 改为 `>=3.15`；CI 矩阵由 `3.10–3.14` 收敛为 `3.15`（原矩阵与 `requires-python` 本就矛盾，3.10–3.13 的 job 无法安装本包）

* **状态文件格式升级到 schema v3，不兼容旧版**：`.pytexmk_refcache.json` 由 "扁平结构" 改为 "命名空间结构"。旧版 PyTeXLogs 读写新文件、或新版读旧文件，都会得到空的引用缓存（表现为 "首次运行，新增 N 篇"）。此取舍是为了让文件结构只有一种形态，避免长期维护双写逻辑

### 新增



* `ProjectStateStore`**：单文件多命名空间状态存储**（`pytexlogs.core.state`，已加入公共 API）


  * 解决的问题：多个工具共用一个状态文件时，"整文件覆写" 会导致后写者抹掉先写者。改造前 `RefChangeTracker.save_cache()` 就是整文件覆写，PyTeXMK 想持久化任何构建状态都会被冲掉

  * 做法：每个写入者只拥有自己的顶层键（`pytexlogs` / `pytexmk` / 第三方），写入时**读 - 改 - 写**，只替换自己命名空间内的键

  * **原子写**：同目录临时文件 + `os.replace`，Ctrl+C 中断不会留下半截 JSON

  * **轻量文件锁**：`O_CREAT | O_EXCL` 哨兵 + 超时降级（拿不到锁就跳过本次写入，最多退化为下次多编一轮，绝不阻塞或报错）；30 秒以上的陈旧锁会被自动清理

  * **容错**：文件缺失 / JSON 损坏 / 顶层非对象 /schema 版本不符，一律降级为空骨架，不删除文件、不中断主流程

  * 公共方法：`load` / `get_namespace` / `update_namespace` / `replace_namespace` / `get_build` / `update_build` / `get_refs` / `update_refs` / `clear`

### 变更



* `RefChangeTracker`**&#x20;改用&#x20;**`ProjectStateStore`：`load_cache()` / `load_cache_counts()` / `save_cache()` 读写 `pytexlogs.refs` 命名空间，不再整文件覆写。`self.cache_path` 保留以兼容外部读取路径

* `pytexlogs.__init__` 新增导出：`ProjectStateStore`、`PROJECT_STATE_FILENAME`、`SCHEMA_VERSION`、`StateFileCorrupted`

* `pyproject.toml`：`tool.ruff` 增加 `target-version = "py315"`；`tool.mypy.python_version` 改为 `"3.15"`；classifier 改为 `Python :: 3.15`

### 新增文件



* 状态文件结构（schema v3）：



```
{
  "schema_version": 3,
  "timestamp": "2026-10-18T13:59:04+08:00",
  "pytexlogs": { "refs": { "keys": [...], "key_counts": {...} } },
  "pytexmk":   { "build": { "fingerprint": "...", "artifacts": {...}, "sources": {...} } },
  "jobs":      { "main": { "updated_at": "..." } }
}
```

### 测试



* 新增 `tests/test_state_store.py`（19 例）：命名空间隔离、v2 丢弃、v3 自动升级、原子写无残留、锁释放、并发交替写、坏 JSON 降级、`clear()` 幂等

* 全量：**100 passed, 1 skipped**（Python 3.15.0）

* 端到端验证：`run_pipeline()` 写入 `pytexlogs.refs` 后，预先放在 `pytexmk.build` 里的数据原样保留



***

## v0.3.0 - 2026-08-04

### 架构重构



* 按功能模块重新组织代码：core/、parsers/、cli/、display/、exporters/、utils/

* 消除薄层转发层，简化调用链

* formatter 与 printer 分离为独立模块，支持 GUI/Web 输出

### Python 3.14 兼容性



* 移除所有 `from __future__` 兼容性残留

* 全面采用现代类型注解（`|` 联合类型）

* 使用 `datetime.UTC`、`slots=True` 等新特性

* requires-python 更新为 `>=3.14`

### 功能改进



* 10 种日志解析器功能完善（LaTeX、BibTeX、Biber、Makeindex、Xindy、Glossaries、Nomencl、PythonTeX、Minted、Asymptote）

* SARIF 导出符合 v2.1.0 规范

* Minted 解析器添加高亮计数检测

* Nomencl 解析器支持 Warning-- 格式

* LaTeX 解析器修复 assert 语句安全问题

* 参考文献追踪修复首次运行判断逻辑

* 报告加载添加异常处理

* 解析器注册冲突添加警告日志

### 代码质量



* ruff 检查通过，无 E/F 级别错误

* 类型注解完整

* 文档字符串清晰

## v0.2.0 - 2026-08-01

### FR-1: Public API 命名分层 + 兼容别名

新增 run\_pipeline / Manager / Registry / Report 四个高频短别名；run\_log\_pipeline 等旧名通过 DeprecationWarning 向后兼容；**all** 按「便捷 API / 解析器 / 数据结构 / 常量 / 解析器类 / 演示」六段注释清晰分层。

### FR-2: 类型注解完整补齐 + mypy --strict 通关

所有公共函数、私有变量、11 个 \*Parser 子类签名严格对齐 BaseLogParser；pyproject.toml \[tool.mypy] 配置 strict=true、python\_version="3.10"，mypy --strict src/pytexlogs 零错误。

### FR-3: 高阶便捷函数组（一行搞定常见场景）

新增 easy.py 五个顶层函数：parse\_log\_file（按后缀自猜 parser）、parse\_log\_text（captured\_outputs 场景）、parse\_auxdir（整辅助目录扫描）、filter\_severity（按严重度裁剪条目）、aggregate\_stats（category/level/parser 分组统计）。

### FR-4: 统计聚合 API

aggregate\_stats (obj, group\_by="category" | "level" | "parser") 接受 ParsedPipelineReport | list \[ToolResult]，返回直方图 dict，可直接用于 CLI 打印或可视化。

### FR-5: 三种结构化导出（JSON / CSV / SARIF）

在 \_report.py 新增 to\_json /to\_csv/to\_sarif 三个公共函数；SARIF 为 v2.1.0 最小子集，可直接喂 GitHub Code Scanning；CSV 严格表头 file,line,level,category,tool,text,hint,source\_path。

### FR-6: Entry Point 插件化机制

LogParserRegistry.get\_default\_registry () 首次构造时自动扫描 pytexlogs.parsers Entry Point 组；外部包可在自己 pyproject.toml 中注册自定义解析器，无需改动 pytexlogs 源码。

### FR-7: CLI（argparse）开箱即用

新增 pytexlogs = "pytexlogs.cli:main" 入口脚本，支持全局 --version /--lang/--format /--output/--severity /--root-file/--open /--editor 参数；退出码 0 = 无 error，1 = 有 error，2 = 参数 / IO 错。

### FR-8: 编辑器跳转打开能力

\--open + --editor auto|code|subl|nvim|gvim|custom:，自动按 VISUAL > EDITOR > code > subl > nvim > gvim 优先级选编辑器，失败仅 warning 不中断；支持 % f:% l 模板替换。

### FR-9: i18n 可插拔翻译（中英文摘要）

set\_summary\_language (lang, translate\_fn=None) 全局切换；CLI --lang zh/en 直接生效；translate\_fn 参数允许注入任意自定义翻译逻辑，无 gettext 依赖。

### FR-10: summary 子命令

pytexlogs summary \[LOG ...] 等价 check 但专注摘要输出，忽略退出码；检测到 rich 时用 rich.table 彩色表格，无 rich 退化为纯文本对齐。

### FR-11: export 子命令

pytexlogs export --format=json|csv|sarif LOG/DIR --output PATH 一步生成结构化报告；--output 缺省则打印到 stdout，方便 shell 管道。

### FR-12: filter\_severity 便捷过滤

filter\_severity (entries, min\_level=WARNING) 利用 LogLevel.**lt** 比较，一行保留 min\_level 以上条目，常用于 CI 告警筛选。

本次共实现 49 条公共 API；新增 check /summary/export /demo 四类 CLI 子命令；wheel 体积控制在 <= 70KB；requires-python>=3.10 提高 PyPI 覆盖率。

## v0.1.0 - 2026-07-30



* 新增：从 PyTeXMK v1.1.0 抽离日志解析子包为独立 PyPI 库 pytexlogs

* 改进：移除对 pytexmk.\* 的反向依赖，成为纯标准库可运行的包；独立库 logger 名改为 pytexlogs

* 测试：独立命名空间 B 验证（NFR-3）4 PASS，可单独解析 LaTeX/BibTeX 等日志