# 第 4 轮：独立验证（对抗性误报与端到端）

> 验证性质：只读复核。本轮**未修改任何 `.py` 源码或测试**，未 commit，未改动 MiKTeX，
> 未安装 TeX 包，未修改系统环境变量。验证脚本与中间产物均放在 agent 工作区，未进入仓库。
>
> 验证环境：
> - Python `D:\Document YM\Desktop Document\Tools_Development\PyTeXMK\.venv\Scripts\python.exe`（CPython 3.15.2，pytest 9.2.0）
> - `PYTHONPATH=D:\Document YM\Desktop Document\Tools_Development\PyTeXLogs\src`（绝对路径，避免子进程导入 venv 旧包）
> - ruff 0.17.5（PyTeXMK venv 内未装 ruff；直接调用本机另一 venv 缓存的 `ruff.exe`，未做安装/写入）
> - 仓库版本 `pytexlogs 0.6.1`，规则表 `RULE_IDS` 实测 **41** 条（见文末附录）

## 回归结果

| 命令 | 输出尾部 | 结论 |
| --- | --- | --- |
| `python -m pytest -q tests` | `376 passed, 1 skipped in 3.97s`（二次运行 `4.08s`） | 通过；跳过项为 `tests/perf/test_100k_lines.py:41`，门控条件 `CI_PERF=1`，属预期跳过 |
| `ruff check --config pyproject.toml src tests` | `All checks passed!`（ruff 0.17.5） | 通过 |
| `python -m compileall -q src\pytexlogs` | 退出码 `0`，无报错 | 通过 |
| `python -m pytexlogs.cli --version` | `pytexlogs 0.6.1` | 通过（`--version` 未走惰性导入） |
| `CI_PERF=1 pytest -q tests/perf` | `1 passed in 0.41s` | 10 万行解析性能门通过（仅测 parser，不含 hint 正则） |

基线与任务书给定的 `376 passed, 1 skipped` 一致，未发现回归。

## 真实日志回放

样本取自 `round1-real-logs.md` 第一批/第二批，共 **39 条**，逐条实际调用 `hint_for_text`，
核对 `rule_id` / `kind` / 关键提取值。**39 条全部通过。**

| 编号 | 日志片段（节选） | 期望 rule_id / kind | 实际 | 提取值核对 | 结论 |
| --- | --- | --- | --- | --- | --- |
| c01 | `! Undefined control sequence.` / `l.3 Hello \undefinedcmd` world. | undefined_control / undefined_control | undefined_control / undefined_control | 文案含 `\undefinedcmd`，命令含 `undefinedcmd` | PASS |
| c02 | `! Missing $ inserted.` … `l.3 Text then x^` / `2 math.` | math_mode / math_mode | math_mode / math_mode | — | PASS |
| c03 | `! LaTeX Error: File ` `nosuchpkgxyz.sty' not found.` + `! Emergency stop.` | missing_package / missing_package | missing_package / missing_package | 包名 `nosuchpkgxyz`；缺宏包优先于 fatal | PASS |
| c05 | `! LaTeX Error: Missing \begin{document}.` | missing_begin_document / missing_begin_document | 同左 | 文案含 `\begin{document}` | PASS |
| c06 | `Runaway argument?` + `! File ended while scanning use of \@argdef.` | runaway / runaway | runaway / runaway | 提取命令 `\@argdef` | PASS |
| c07 | `! Extra alignment tab has been changed to \cr.` | alignment_tab / alignment_tab | 同左 | 文案含 `&` | PASS |
| c08 | `! Missing number, treated as zero.` / `<to be read again>` / `x` / `\vspace{x}` | missing_number / missing_number | 同左 | 待读入 token `x` 入文案 | PASS |
| c09 | `! LaTeX Error: \begin{document} ended by \end{itemize}.` | end_mismatch / end_mismatch | 同左 | 文案含 `\end` | PASS |
| c10 | `! LaTeX Error: Unicode character 中 (U+4E2D) not set up…` | unicode / unicode | 同左 | CJK 分支含 `ctex`，并说明来自 8 位引擎 | PASS |
| c11 | `Overfull \hbox (243.09511pt too wide) detected at line 3` | log_hint / log_hint | 同左 | 通用排版提示，未抢答具体规则 | PASS |
| c12 | `LaTeX Warning: Reference ` `nosuchlabel' … undefined` | undefined_reference / undefined_reference | 同左 | 标签 `nosuchlabel` 入文案 | PASS |
| c13 | `LaTeX Warning: Citation ` `key1' … undefined` + `No file main.bbl.` | missing_bbl / missing_bbl | 同左 | 先命中后端未跑；文案同时含 `biber` 与 `bibtex` 两条流程 | PASS |
| c14 | `! Package fontspec Error: The font "NoSuchFontFamilyXYZ" cannot be found.` | fontspec_font_not_found / missing_font_family | 同左 | 字体族 `NoSuchFontFamilyXYZ`；命令含 `fc-list` | PASS |
| c15 | `! TeX capacity exceeded, sorry [input stack size=5000].` | capacity / capacity | 同左 | 根因文案先讲递归/循环，未写死 `main_memory` | PASS |
| c16 | `! LaTeX Error: Something's wrong--perhaps a missing \item.` | missing_item / missing_item | 同左 | 文案含 `\item`，并补盒子/单元格成因 | PASS |
| c17 | `! Double subscript.` / `$x_1_` / `2$` | double_script / double_script | 同左 | 下标分支；含分组意图与空组特例 | PASS |
| c18 | `! File ended while scanning use of \textbf .`（无 Runaway 前缀） | runaway / runaway | 同左 | 提取命令 `\textbf` | PASS |
| c19 | `! LaTeX Error: Option clash for package graphicx.` | option_clash / option_clash | 同左 | 包名 `graphicx` | PASS |
| e01 | `Missing character: There is no ✓ (U+2713) in font [lmroman10-regular]:mapping=tex-text;!` | missing_glyph / missing_glyph | 同左 | 符号 `✓` 入文案；无 `fontenc` 字样 | PASS |
| e02 | `Missing character: There is no 中 (U+4E2D) in font [lmroman10-regular]:mapping=tex-text;!` | missing_glyph / missing_glyph | 同左 | CJK 分支；字符 `中`、字体入文案；无 `fontenc` | PASS |
| e03 | `! Font \foo=NoSuchFont at 10.0pt not loadable: Metric (TFM) file not found.` | font_not_loadable / missing_font_tfm | 同左 | 规格 `NoSuchFont`、原因 `Metric (TFM) file not found`；命令 `kpsewhich nosuchfont.tfm` | PASS |
| d14 | `! Font \foo=NoSuchFont at 10.0pt not loadable: Metric (TFM) file or installed font not found.` | font_not_loadable / missing_font_tfm | 同左 | 规格/原因完整提取，未被贪婪抓成整句 | PASS |
| e05 | `Package hyperref Warning: Token not allowed in a PDF string (Unicode):` | hyperref_pdf_string / hyperref_pdf_string | 同左 | 命令含 `\texorpdfstring` | PASS |
| e06 | `! Display math should end with $$.` + `! LaTeX Error: Bad math environment delimiter.` | bad_math_delimiter / math_delimiter | 同左 | 文案含“定界符” | PASS |
| e09 | `! Too many }'s.` / `\section{a}}` | extra_close_brace / extra_close_brace | 同左 | 文案含“花括号” | PASS |
| e10 | `! Misplaced \noalign.` / `\hline ->\noalign` | misplaced_noalign / misplaced_noalign | 同左 | 文案含 `\hline` | PASS |
| e11 | `! Missing \right. inserted.` / `\left[ x` | missing_right / missing_delimiter | 同左 | 文案含 `\right`，说明 `.` 为隐形定界符 | PASS |
| d02 | `! Illegal unit of measure (pt inserted).` / `<to be read again>` / `z` / `\vspace{2zz}` | illegal_unit / illegal_unit | 同左 | 待读入字符 `z` 入文案 | PASS |
| d05 | `! LaTeX Error: Command \foo already defined.` | command_already_defined / command_conflict | 同左 | 命令名 `\foo` | PASS |
| d12 | `! LaTeX Error: There's no line here to end.` | no_line_to_end / no_line_to_end | 同左 | 文案含 `\newline` | PASS |
| d09 | `No pages of output.` | no_output / no_output | 同左 | 文案明确 `\includeonly` 不是成因 | PASS |
| 补充 | `! Double superscript.` | double_script / double_script | 同左 | 上标分支文案 | PASS |
| 补充 | `! Font T1/cmr/m/n/10=ecrm1000 at 10pt not loadable: Metric (TFM) file ecrm1000.tfm not found.` | tfm_font_missing / tfm_font_missing | 同左 | 文件名 `ecrm1000.tfm`；命令含 `tlmgr search`；未串成 fontspec | PASS |
| 补充 | `CTeX fontset 'adobe' is unavailable in current mode.` | fontset_unavailable / fontset_unavailable | 同左 | 文案含“当前引擎模式不支持” | PASS |
| 补充 | `CJKfamily 'song' ([FandolSong-Regular]) does not contain glyph '中' (U+4E2D)` | cjk_missing_glyph / cjk_missing_glyph | 同左 | family `song`、字 `中`、码位 `4E2D` | PASS |
| 补充 | 同上，空格变体 `( U + 4E2D )` | cjk_missing_glyph / cjk_missing_glyph | 同左 | 提取值完整 | PASS |
| 补充 | `I couldn't open database file refs.bib` | missing_bib / missing_bib | 同左 | 文案同时含 `addbibresource` 与 `bibliography` 两种写法 | PASS |
| 补充 | `找不到 citation `key1``（本地化摘要行） | undefined_citation / undefined_citation | 同左 | 键 `key1`；未过度命中其他规则 | PASS |
| 补充 | `找不到 reference `sec:intro``（本地化摘要行） | undefined_reference / undefined_reference | 同左 | 标签 `sec:intro` | PASS |

任务书点名的七类重点样本（XeLaTeX 缺字形、`Font ... not loadable`、`input stack size`、
`Double subscript`、`Too many }'s`、`Option clash`、`Missing \begin{document}`）全部命中且提取值正确。

## 对抗性误报

共 **36 条**探针（30 条基线 + 6 条补充）。判定口径：良性排版提示允许落到通用 `log_hint`；
不得命中具体规则，尤其不得返回 `missing_package` / `font_not_loadable` / `missing_bbl` /
`biber_case_mismatch` 等可执行修复类规则。

| # | 输入 | tool | 实际 hint（rule_id/kind） | 期望 | 是否误报 | 严重度 |
| --- | --- | --- | --- | --- | --- | --- |
| fp01 | `Overfull \hbox (243.09511pt too wide) detected at line 3` | — | log_hint / log_hint | 通用 log_hint | 否 | — |
| fp02 | `Underfull \hbox (badness 10000) in paragraph at lines 1--2` | — | log_hint / log_hint | 通用 log_hint | 否 | — |
| fp03 | `Package hyperref Info: Loading driver ` `hyperref.cyriz.sty'.` | — | None | None | 否 | — |
| fp04 | `LaTeX Font Info:    Font shape ` `OT1/cmr/m/n/10' will be scaled.` | — | None | None | 否 | — |
| fp05 | `INFO - This is Biber 2.19` | biber | None | None | 否 | — |
| fp06 | `WARN - I didn't find a database entry for 'x'` | latex | None | None | 否 | — |
| fp07 | `> Option clash for package graphicx.` | — | None | None（引用行已剥离） | 否 | — |
| fp08 | `% Missing character: There is no 中 in font cmr10!` | — | **missing_glyph / missing_glyph** | None | **是**：`% ` 注释前缀未被剥离（剥离逻辑只认 `> `） | 中 |
| fp09 | `"Missing character: There is no 中 in font cmr10!"`（引号包裹） | — | **missing_glyph / missing_glyph** | None | **是**：内联引号不构成保护 | 中低 |
| fp10 | `The Missing character warning appears when the current font lacks a glyph.` | — | **log_hint / log_hint**，文案为“…或用 `\usepackage[T1]{fontenc}` 等。” | None | **是**：散文句子命中旧表 `Missing character` 子串；且旧表文案仍残留被规格禁止的 T1 fontenc 建议（见 F2） | 中 |
| fp11 | `"File ` `foo.sty' not found"`（引号包裹） | — | **missing_package / missing_package**，包名 `foo` | None | **是**：引号不保护；给出 `tlmgr install foo` 类建议 | 中低 |
| fp12 | `Looking in D:\我的 文档\figures for files referenced by the document.`（中文/空格/反斜杠路径） | — | None | None | 否 | — |
| fp13 | 空字符串 `""` | — | None | None | 否 | — |
| fp14 | 仅空白 `"   \n\t  "` | — | None | None | 否 | — |
| fp15 | `找不到 citation ` `key1``（中文摘要行） | — | undefined_citation / undefined_citation | 允许命中本地化规则 | 否（命中正确，未过度命中） | — |
| fp16 | `In this section we discuss the missing package issue and how to install it.` | — | None | None | 否 | — |
| fp17 | `INFO - Processing file 'main.bcf'` | biber | None | None | 否 | — |
| fp18 | `Package hyperref Warning: Using fallback driver hpdftex.` | — | None | None | 否 | — |
| fp19 | `> LaTeX Warning: Citation ` `key' on page 1 undefined on input line 3.` | — | None | None（引用行已剥离） | 否 | — |
| fp20 | `No file main.aux.` | — | None | None（`.aux` 不得按 `.bbl` 处理） | 否 | — |
| fp21 | `! LaTeX Error: File ` `fig.png' not found.` | — | missing_file / missing_graphic | 缺图片，非缺宏包 | 否 | — |
| fp22 | `File ` `refs.bib' not found.` | — | missing_file / missing_bib | 缺文献库，非缺宏包 | 否 | — |
| fp23 | `The tutorial says: The font "Arial" cannot be found when the family name is mistyped.` | — | **fontspec_font_not_found / missing_font_family** | None | **是**：正则不要求 `Package fontspec Error:` 前缀，散文中的 `"..." cannot be found` 即抢答 | 中 |
| fp24 | `A Double subscript error occurs when two underscores follow a single atom.` | — | **double_script / double_script** | None | **是**：裸子串 `Double subscript` 命中 | 中低 |
| fp25 | `In the FAQ: Too many }'s means an extra closing brace.` | — | **extra_close_brace / extra_close_brace** | None | **是**：裸子串 `Too many }'s` 命中 | 中低 |
| fp26 | `Transcript written on main.log.` | — | None | None | 否 | — |
| fp27 | `This is pdfTeX, Version 3.141592653-2.6-1.40.25` | — | None | None | 否 | — |
| fp28 | `> ! Emergency stop.` / `> ! Undefined control sequence.` | — | None | None（引用行整体剥离） | 否 | — |
| fp29 | `File ` `chapter2.tex' not found.` | — | missing_file / missing_file | 缺输入文件，非缺宏包 | 否 | — |
| fp30 | `Font ` `NotoSans' not found is discussed in the manual.` | — | **missing_font / missing_font** | None | **是**：裸子串 `Font ... not found` 命中 | 中低 |
| ex1 | `The Option clash for package graphicx error is explained in the manual.` | — | **option_clash / option_clash** | None | **是**：散文提及即命中 | 中低 |
| ex2 | `Please fix the Missing \begin{document} issue.` | — | **missing_begin_document / missing_begin_document** | None | **是**：裸子串命中 | 中低 |
| ex3 | `The font "Times New Roman" cannot be found in the FAQ.` | — | **fontspec_font_not_found** | None | **是**：同 fp23 | 中 |
| ex4 | `Font ` `OldFont' not found appears in the changelog.` | — | **missing_font** | None | **是**：同 fp30 | 中低 |
| ex5 | `% File ` `foo.sty' not found.` | — | **missing_package** | None | **是**：`% ` 注释前缀未剥离（同 fp08） | 中 |
| ex6 | `No file refs.bbl.` | — | missing_bbl / missing_bbl | 观察项：`.bbl` 文件名非常规 jobname，但“后端未跑”建议仍适用，不判误报 | 否（边界观察） | 低 |

补充核对：`.cls` / `.cfg` / `.ldf` 后缀均正确归入 `missing_package`（符合后缀表设计）；
未知工具名（`xindy`）下旧表返回空，`WARN -` 与数据库条目键均不命中。

## 优先级与工具作用域

### 规则优先级（混合文本，8 对全部符合规格顺序）

| # | 混合文本 | 期望 | 实际 | 结论 |
| --- | --- | --- | --- | --- |
| p01 | `! Emergency stop.` + `! Undefined control sequence.` / `\badcmd` | fatal | fatal | PASS |
| p02 | `File ` `booktabs.sty' not found.` + `! Package foo Error: bad option` | missing_package | missing_package | PASS |
| p03 | `Option clash for package graphicx.` + `! Package graphicx Error: bad option` | option_clash | option_clash | PASS |
| p04 | `! Package fontspec Error: The font "Times New Roman" cannot be found.` | fontspec_font_not_found | fontspec_font_not_found | PASS |
| p05 | `No file main.bbl.` + `Citation ` `key1' undefined` | missing_bbl | missing_bbl | PASS |
| p06 | `Missing \begin{document}.` + `Undefined control sequence.` | missing_begin_document | missing_begin_document | PASS |
| p07 | `! Font \foo=NoSuchFont at 10.0pt not loadable: …` | font_not_loadable | font_not_loadable（未被 missing_font 贪婪污染） | PASS |
| p08 | `Missing character: There is no α in font cmr10!` | missing_glyph | missing_glyph（未被 missing_font 抢答） | PASS |

### 工具作用域矩阵（同一文本在四种 tool_name 下的结果）

| 文本 | biber | bibtex | latex | None（未指定） |
| --- | --- | --- | --- | --- |
| `WARN - I didn't find a database entry for 'x'` | log_hint（biber 表） | None | None | log_hint（合并表） |
| `WARN - Case mismatch: key ` `Smith' vs ` `smith' in refs.bib` | **biber_case_mismatch / biber_key_case** | None | None | log_hint（合并表兜底，见 F6） |
| `! Missing $ inserted.` | math_mode | math_mode | math_mode | math_mode |
| `File ended while scanning use of \foo.` | runaway | runaway | runaway | runaway |
| `! Double subscript.` | double_script | double_script | double_script | double_script |

作用域结论：

- 旧提示表隔离正确：bibtex 键（skipping entry/command、bad cross reference、`---while reading file`）
  只在 `bibtex` 或未指定工具下命中；`latex`/`biber`/`xindy` 下均为 None。
- `biber_case_mismatch` 仅在工具名以 `biber` 开头时命中，`bibtex`/`latex` 不命中，符合规格。
- **观察项（F4）**：结构化 LaTeX 规则（`math_mode`、`double_script`、`float_overflow`、
  `invalid_utf8`、`alignment_tab`、`no_output`、`runaway`）**未按工具隔离**，在
  `biber`/`bibtex` 日志下同样会触发。实际后端日志极少出现这些 TeX 错误串，现实风险低，
  但匹配器层没有工具守卫。

## 项目上下文与导出链路

### 项目上下文替换

| 用例 | 调用 | 实际命令 / rule_id | 结论 |
| --- | --- | --- | --- |
| 显式主文件 | `hint_for_text(Citation undefined, jobname="main", root_file="main.tex")` | 命令 `('biber main', 'bibtex main')`，rule_id `undefined_citation` | PASS |
| 条目带显式 jobname/root_file | `hint_for_entry(entry, jobname="main", root_file="main.tex")`，entry.file=`chapters/intro.tex` | 命令 `('biber main', 'bibtex main')`，不含 `intro` | PASS |
| **仅传子文件** | `hint_for_entry(entry)`，entry.file=`chapters/intro.tex`，无 jobname/root_file | **命令 `('biber intro', 'bibtex intro')`**，rule_id `undefined_citation` | **FAIL（F5）**：子文件 stem `intro` 被当成主文件 jobname |
| 英文语言保留 rule_id | `hint_for_text("No file main.bbl.", jobname="main", root_file="main.tex", language="en")` | rule_id `missing_bbl`，kind `missing_bbl`，命令 `('biber main', 'bibtex main')`，文案为英文 | PASS |
| 英文语言保留 rule_id（双下标） | `hint_for_text("! Double subscript.", language="en")` | rule_id `double_script`，文案为英文 | PASS |

### 导出链路（`tests/fixtures/sample.log`，CLI `export --format json/sarif/csv`，退出码均 0，无 stderr）

**JSON**（`pytexlogs 0.6.1`，`__format__=pytexlogs-json-v1`）：

- `results[]` 形状未变：条目含 `tool_name / category / importance / source_path / entries / stats`；
  `entries[]` 含 `level / file / line / text / error_pos_text`。
- 顶层 `hints[]` 存在，3 条 hint 全部 `hint.rule_id` 非空：
  `undefined_control`（提取 `\foobar`）、`fatal`、`fatal`；`kind/text/text_en/commands` 字段齐全。
- 未发现空 `rule_id` 的 hint。

**SARIF v2.1.0**：

- `properties["pytexlogs/hint"]["rule_id"]` 存在（`undefined_control` / `fatal` / `fatal`），
  `kind/text/text_en/commands` 齐全，无空 rule_id。
- 必填字段仍在：`ruleId`、`level`、`message.text`、`locations[0].physicalLocation.artifactLocation.uri`、
  `region.startLine`、`partialFingerprints.pytexlogs/v1`；`tool.driver.rules` 完整。

**CSV**：

- 表头严格为 `file,line,level,category,tool,text,hint,source_path`，与规格一致；3 行数据 hint 列已填充。

## 失败项与修复建议

> 以下问题均由本轮独立复核复现；本轮未改代码，留给实现智能体处理。

### F1【高】`missing_font` 正则贪婪跨行，多行日志灾难性回溯（11.7–18.5 s）

- **复现**：
  - `hint_for_text("\n".join(["Missing character: There is no α in font cmr10!"] * 5000))` → **11 660 ms**
  - 带码位变体（`中 (U+4E2D) in font [lmroman10-regular]:mapping=tex-text;!` × 5000）→ **18 530 ms**
- **定位**：`src/pytexlogs/hints.py` `_FONT_NOT_FOUND_RE`
  `Font(?: shape)?\s+`?([^'`]+)'?\s+(?:not found|undefined)`。字符类 `[^'`]+` 不排除换行，
  在含 `in font …` 但无引号、且不含 `not found/undefined` 的多行文本上，贪婪匹配后逐层回退尝试
  交替分支。逐条规则计时显示：`missing_font` 匹配器单条 **11 727 ms**，而 `_MISSING_CHAR_RE.search`
  仅 0.00 ms——瓶颈不在缺字形规则。`_match_font` 里 `"Missing character" in text` 的保护判断
  在正则搜索**之后**才执行，拦不住回溯成本。
- **期望**：单次调用 < 1 s；5000 行重复样本应在数十毫秒级。
- **建议**：把字体 token 限定为不含空白/引号/换行的短词，例如
  `Font(?: shape)?\s+`?([^\s'`]+)'?\s+(?:not found|undefined)`。实测该改写在同样 5000 行样本上
  **1.87 ms**，且三条规范样本（``Font `NotoSans' not found``、
  `Font shape ` `OT1/cmr/m/n/10' undefined`、`Font NotoSans not found`）仍全部命中；
  或先做 `"Missing character" in text` 短路，再跑正则。

### F2【中】旧表 `Missing character` 兜底仍输出被规格禁止的 T1 fontenc 建议（D1 残留）

- **复现**：
  - `hint_for_text("Missing character: there is no X")` → `log_hint`，文案
    “当前字体不含该字形：更换支持该字符的字体，或用 `\usepackage[T1]{fontenc}` 等。”
  - CLI 端到端：`python -m pytexlogs.cli explain "Missing character: there is no X"` 直接输出同上文案。
- **期望**：规格 R2 明确“禁止再出现用 T1 fontenc 解决缺字形”。结构化 `missing_glyph` 规则已修，
  但 `parsers/latex.py` `LATEX_LOG_HINTS["Missing character"]` 旧表文案未同步，只要文本只含
  `Missing character` 子串、未凑齐 `… in font …` 完整格式，就会落到这条旧建议。
- **建议**：改写 `LATEX_LOG_HINTS["Missing character"]` 文案，删除 `\usepackage[T1]{fontenc}`，
  与结构化规则的“换字体 / `\newunicodechar` 映射”口径对齐；或让结构化 `missing_glyph` 在
  仅有 `Missing character` 子串时也兜底接管。

### F3【中】散文 / 引号 / 注释中的错误字符串被结构化规则抢答

- **复现与实际**：

  | 复现字符串 | 实际命中 |
  | --- | --- |
  | `% Missing character: There is no 中 in font cmr10!` | missing_glyph |
  | `% File ` `foo.sty' not found.` | missing_package（包名 `foo`） |
  | `"Missing character: There is no 中 in font cmr10!"` | missing_glyph |
  | `"File ` `foo.sty' not found"` | missing_package |
  | `The tutorial says: The font "Arial" cannot be found …` | fontspec_font_not_found |
  | `The font "Times New Roman" cannot be found in the FAQ.` | fontspec_font_not_found |
  | `Font ` `OldFont' not found appears in the changelog.` | missing_font |
  | `A Double subscript error occurs …` | double_script |
  | `In the FAQ: Too many }'s means …` | extra_close_brace |
  | `The Option clash for package graphicx error is explained …` | option_clash |
  | `Please fix the Missing \begin{document} issue.` | missing_begin_document |

- **期望**：被 `> ` 引用、`% ` 注释、成对引号包裹，或出现在解释性散文里的错误样例字符串，
  不应产出可执行修复建议。
- **建议**：
  1. `_drop_quoted_lines` 增加 `% ` 注释前缀剥离（与 `> ` 同类）；
  2. 高风险规则（`missing_package`、`fontspec_font_not_found`、`missing_font`、`option_clash`、
     `missing_begin_document`、`extra_close_brace`、`double_script`）要求错误串处于行首错误格式
     （`! ` / `LaTeX Error:` / `Package … Error:` / `LaTeX Warning:`），或排除引号/反引号包裹的提及；
  3. `fontspec_font_not_found` 正则要求上下文含 `Package fontspec Error`（或 tectonic 风格前缀），
     不要仅凭 `The font "..." cannot be found` 抢答。

### F4【中低】结构化 LaTeX 规则未做工具隔离

- **复现**：`! Missing $ inserted.`、`! Double subscript.`、`! Too many unprocessed floats.`、
  `Invalid UTF-8 byte sequence`、`Extra alignment tab`、`No pages of output.`、
  `File ended while scanning use of \foo.` 在 `tool_name="biber"` / `"bibtex"` 下均照常命中。
- **期望**：LaTeX 专属规则不应被 bibtex/biber 日志误触发（规格测试要求“通用 runaway 可保留，
  但不能套 LaTeX 专属语义”）。
- **建议**：为结构化规则增加可选工具白/黑名单；至少把纯 LaTeX 排版类规则（math_mode、
  double_script、alignment_tab、float_overflow、invalid_utf8、no_output）限制在
  `latex/pdflatex/xelatex/lualatex/tectonic` 工具名下；runaway 可保持通用。

### F5【中低】无子文件上下文时，子文件 stem 被当作主文件 jobname

- **复现**：`LogEntry(file="chapters/intro.tex", text="LaTeX Warning: Citation ` `Smith2020' undefined …")`，
  调用 `hint_for_entry(entry)`（不传 jobname/root_file）→ 命令 `('biber intro', 'bibtex intro')`。
- **期望**：只知道子文件时，不应把 `chapters/intro.tex` 当成可单独编译的主文件；
  要么保留 `<jobname>` 占位符，要么从日志源文件（`.log/.blg`）stem 推断，而不是从条目 `file` 推断。
- **建议**：`hint_for_entry` 在无显式 jobname 时，优先使用 `source_path`（日志文件）stem；
  条目 `file` 含路径分隔符（疑似子文件）时不据此推导 jobname，保留占位符。导出链路经
  `source_path` stem 推导，目前行为正确；缺口仅在直接条目调用路径。

### F6【低】`tool_name=None` 时 case mismatch 退化为 biber 通用警告文案

- **复现**：`hint_for_text("WARN - Case mismatch: key ` `Smith' vs ` `smith' …")`（不传工具）
  → `log_hint`（`WARN -` 通用 biber 文案），未走 `biber_case_mismatch` 的逐字符大小写核对建议；
  传 `tool_name="biber"` 才命中专项规则。
- **期望**：未指定工具但文本明确含 `case mismatch` 时，至少保留专项文案；或在文档中明确
  “专项 biber 规则必须带工具上下文”。
- **建议**：`_match_biber_case_scoped` 在工具名为空时也放行子串匹配；或合并表兜底文案中补充
  大小写敏感提示。

### F7【低】unicode 符号分支仍附带换引擎命令

- **复现**：`Unicode character μ (U+03BC) not set up…` → 规则 `unicode`（符号分支），
  commands 仍含 `xelatex <主文件>.tex`、`lualatex <主文件>.tex`。
- **期望**：规格 R3：非中文符号优先替换为等价 LaTeX 命令 / `\newunicodechar`，“确有必要再考虑
  切换引擎”。当前命令列表把换引擎与命令映射并列。
- **建议**：符号分支 commands 去掉引擎切换项，仅保留 `\ensuremath{…}` 与 `newunicodechar`；
  引擎建议留在文案末尾即可。

### F9【中低】`fontset_unavailable` 漏反引号/双引号变体（规格 R22 要求容忍）

- **复现**：
  - `CTeX fontset ` `adobe' is unavailable in current mode.`（反引号 + 直引号，ctex 源码消息格式）→ **None**
  - `CTeX fontset "adobe" is unavailable in current mode.`（双引号）→ **None**
  - 仅直引号 `'adobe'` 形式命中（既有测试只覆盖这一种）。
- **期望**：规格 R22 明确“容忍引号/反引号变体”；ctex 源码消息为
  `` CTeX fontset '`#1' is unavailable in current mode. ``，即左反引号、右直引号。
- **建议**：`_FONTSET_UNAVAILABLE_RE` 分隔符改为字符类，如
  `` CTeX fontset\s+[`'\"]([^`'\"]+)[`'\"]\s+is unavailable in current mode ``。

### F10【低】`Missing delimiter ) inserted.` 变体未匹配

- **复现**：`! Missing delimiter ) inserted.` → **None**；
  对照 `! Missing delimiter (. inserted.` → `missing_right` 正常命中。
- **期望**：R6 同时覆盖左/右定界符缺失；当前正则 `Missing delimiter \(\.?\s+inserted` 只认 `(`。
- **建议**：正则改为 `Missing delimiter\s+([()])\.?\s+inserted`，与 `Missing \right. inserted` 同规则。

### F11【低】`Underfull \vbox` 与汇总告警行无提示（观察项）

- **复现**：`Underfull \vbox (badness 10000) has occurred while \output is active` → None；
  `LaTeX Warning: There were undefined references.`（汇总行）→ None。
- **判定**：旧表只收 `Underfull \hbox`；汇总行本身不带具体标签/键，提示价值低。
  记录为覆盖缺口，不阻塞本轮；若要补齐，可把旧表 `Underfull \\\\hbox` 扩展为
  `Underfull \[hv]box`。

### F12【低观察】`\newcommand{dice}` 笔误场景命令名提取偏差

- **复现**：`! Undefined control sequence.` / `l.5 \newcommand{dice}` → 命中 `undefined_control`，
  但提取到的是包装命令 `\newcommand`（文案“未定义命令 `\newcommand`”，命令 `tlmgr search … newcommand.sty`），
  真正笔误是漏写反斜杠的 `dice`。
- **期望**：R19 的折行/续行窗口未覆盖“命令名本身缺反斜杠”的情形；该场景在
  `missing_begin_document` 文案里已被列为成因④，但 `undefined_control` 提取器无法回溯。
- **建议**：低优先级；可在 `l.N` 行同时检测 `\newcommand/\def/\newenvironment` 后紧跟的裸单词，
  将裸单词作为候选命令名。

### F13【观察】规则数量口径：实现 41 条，任务书称 42 条

- `RULE_IDS` 实测 **41** 条唯一 id（清单见附录）。内部快照测试 `test_rule_order_snapshot`
  通过，代码自洽；与任务书“23 → 42”的口径差 1 条，请 Organizer 核对是计数口径（是否把
  `tfm_font_missing` 拆分项另计）还是规格表漏列。本轮未据此判失败。

## 鲁棒性

计时口径：单次 `hint_for_text` 墙钟，Python 3.15.2；预算每项 < 1 s。

| 输入 | 长度 | 耗时 | 命中 | 结论 |
| --- | --- | --- | --- | --- |
| 1 MB 级良性单行（重复信息行） | 592 000 字符 | 86.78 ms | None | PASS |
| 1 MB 级单行含一条未定义命令 | 450 042 字符 | 34.52 ms | undefined_control | PASS |
| **5000 行重复 `Missing character: … cmr10!`** | 239 999 字符 | **11 660.55 ms** | missing_glyph | **FAIL（F1）** |
| **5000 行重复带码位缺字形** | 404 999 字符 | **18 529.97 ms** | missing_glyph | **FAIL（F1）** |
| 5000 行重复 Overfull hbox | 154 999 字符 | 26.81 ms | log_hint | PASS |
| 5000 行重复 undefined citation | 244 999 字符 | 9.59 ms | undefined_citation | PASS |
| 5000 行重复 Option clash | 249 999 字符 | 20.86 ms | option_clash | PASS |
| 5000 行纯良性填充 | 184 999 字符 | 27.45 ms | None | PASS |
| 20 000 个左括号 + 错误串 | 20 021 字符 | 1.32 ms | math_mode | PASS |
| 50 000 个右花括号 | 50 000 字符 | 6.68 ms | None | PASS |
| 1–255 全字符范围 ×40 | 10 200 字符 | 1.49 ms | None | PASS |
| 单字符 `x` | 1 字符 | 0.01 ms | None | PASS |
| 10 000 个连续反斜杠 | 20 000 字符 | 1.42 ms | None | PASS |
| 100 000 空格 | 100 000 字符 | 14.61 ms | None | PASS |
| 100 000 个 `a` | 100 000 字符 | 14.39 ms | None | PASS |

未观察到崩溃、异常退出或正则死循环；唯一超预算项即 F1 的 `missing_font` 正则回溯，
定位与改写方案见 F1。逐条规则计时确认：慢规则为 `missing_font` 匹配器（11 727 ms），
缺字形正则本身 0.00 ms；改写后同一样本 1.87 ms。

## 附录：实测 RULE_IDS 顺序（41 条）

```
1  missing_package          2  missing_file            3  font_not_loadable
4  tfm_font_missing         5  missing_font             6  fontset_unavailable
7  unicode                  8  cjk_missing_glyph       9  missing_glyph
10 missing_bbl             11  undefined_citation     12  undefined_reference
13 undefined_environment   14  missing_bib            15  biber_case_mismatch
16 float_overflow          17  capacity              18  no_output
19 runaway                 20  math_mode              21  double_script
22 fatal                   23  undefined_control     24  end_mismatch
25 option_clash            26  invalid_utf8          27  alignment_tab
28 missing_number          29  missing_item          30  missing_begin_document
31 extra_close_brace       32  missing_right         33  bad_math_delimiter
34 misplaced_noalign       35  illegal_unit          36  command_already_defined
37 no_line_to_end          38  hyperref_pdf_string   39  fontspec_font_not_found
40 package_error           41  log_hint
```

## 验证统计

- 真实日志回放：**39/39 PASS**
- 优先级对：**8/8 PASS**
- 对抗性探针：36 条；明确误报 **13 条**（中 5、中低 8），边界观察 1 条，其余 22 条符合预期
- 漏报探针：`Missing delimiter ) inserted.`、fontset 反引号/双引号变体、`Underfull \vbox` 未命中（F9–F11）
- 工具作用域：旧表隔离与 biber 专项规则符合规格；结构化 LaTeX 规则未隔离（F4）
- 导出链路：JSON / SARIF / CSV 形状与字段全部通过
- 回归：pytest `376 passed, 1 skipped`；ruff `All checks passed!`；compileall 退出码 0
- 失败项：**F1–F13**（高 1、中 2、中低 3、低 5、观察 1），详见“失败项与修复建议”

## 修复结果（实现智能体）

> 本节由实现智能体在修复后回填；未改上述验证结论。环境：同一 venv，
> `PYTHONPATH=<repo>/src`，pytest 9.2.0 / ruff 0.17.5。

| 编号 | 状态 | 修复要点 | 回归测试 |
| --- | --- | --- | --- |
| F1 | 已修 | `_FONT_NOT_FOUND_RE` 字体 token 改为 `[^\s'`]+`；`Missing character` 短路移到正则搜索之前。2000 行无码位/带码位样本均 <1 s 且仍命中 `missing_glyph` | `test_missing_font_regex_no_catastrophic_backtrack`、`test_missing_font_regex_handles_codepoint_variant_fast` |
| F2 | 已修 | `parsers/latex.py` 与 `hints.py` 英文表的 `Missing character` 文案删除 T1 `fontenc`，改为换含字形字体 / `\newunicodechar`；中文/全角指向 ctex/xeCJK | `test_legacy_missing_character_has_no_fontenc_advice` |
| F3 | 已修 | 预处理剥离 `% `/`> `/`| ` 前缀行与成对引号（`"…"`/弯引号）包裹整行；新增散文线索拦截（faq/tutorial/changelog/means/explained/occurs/please fix/says:）；`fontspec_font_not_found` 要求 `Package fontspec Error` 前缀或 `! The font` 行首；`double_script`/`extra_close_brace`/`option_clash`/`missing_begin_document` 要求错误串处于日志行首语境 | `test_prose_and_quoted_samples_do_not_match_specific_rule`（11 条探针全 None）、`test_fontspec_prose_needs_package_error_context` |
| F4 | 已修 | `_Rule` 增加可选 `tools` 白名单；`math_mode`/`double_script`/`alignment_tab`/`float_overflow`/`invalid_utf8`/`no_output`/`package_error` 限定 LaTeX 引擎；`tool_name` 为空放行，biber/bibtex 下跳过；`runaway` 保持通用 | `test_latex_only_rules_skip_backend_tools`（6 类规则 × biber/bibtex None，latex/空工具命中） |
| F5 | 已修 | `hint_for_entry` 无显式 jobname/root_file 时，条目 `file` 含 `/` 或 `\` 视为子文件，不推导主文件 jobname，保留 `<jobname>` 占位符；顶层文件名行为不变 | `test_subfile_entry_without_context_keeps_placeholder`、`test_top_level_entry_still_derives_jobname` |
| F6 | 已修 | `biber_case_mismatch` 在工具名为空时按文本放行；`tool_name="latex"` 仍不命中，bibtex 不命中 | `test_biber_case_mismatch_allowed_without_tool_context` |
| F7 | 已修 | unicode 符号分支 commands 去掉 `xelatex/lualatex`，只保留 `\ensuremath{…}` 与 `\newunicodechar`；中文分支保留引擎切换命令 | `test_unicode_symbol_branch_keeps_command_mapping_not_engine`、`test_unicode_cjk_branch_keeps_engine_switch_commands` |
| F8 | 不适用 | 报告未单列 F8（编号跳过）。 | — |
| F9 | 已修 | fontset 正则分隔符改为字符类，容忍 `` `adobe' ``、`'adobe'`、`"adobe"` 三种引号 | `test_fontset_unavailable_quote_variants`（3 条变体） |
| F10 | 已修 | 定界符正则改为 `Missing delimiter\s+([()])\.?\s+inserted`，左右两侧都命中，文案不写死方向 | `test_missing_delimiter_both_sides` |
| F11 | 已修（可选小补） | 旧表补 `Underfull \vbox` 键（文案同 hbox“通常可接受”），同步 `_LOG_HINT_EN` 英文表 | `test_underfull_vbox_hits_legacy_hint` |
| F12 | 未修（观察项，不在本轮必修清单） | `\newcommand{dice}` 漏写反斜杠场景的裸单词命令提取仍未覆盖；`undefined_control` 提取包装命令 `\newcommand`。该成因已在 `missing_begin_document` 文案④中列出。保留现状，留待后续轮次。 | — |
| F13 | 已修 | 规则总数以 `len(RULE_IDS)` 实测 **41** 为准；CHANGELOG/reference 不再写 42，测试固化 `len(RULE_IDS) == 41` | `test_rule_count_matches_snapshot` |

### 修复后复验

- `python -m pytest -q tests`：**408 passed, 1 skipped**（跳过项仍为 `CI_PERF=1` 门控的性能测试）。
- `ruff check --config pyproject.toml src tests`：**All checks passed!**（exit 0）。
- `python -m compileall -q src\pytexlogs`：退出码 **0**。
- 未 commit、未改 MiKTeX/系统环境变量、未安装 TeX 包；`docs/hints-research/` 仅本节回填，其余调研文档未改动。

