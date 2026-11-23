# 第 3 轮：规则设计与实现规格（Organizer 定稿）

## 输入证据

- 真实编译日志 31 个场景：`docs/hints-research/round1-real-logs.md`
- GitHub 取证 53 条 URL：`docs/hints-research/round2-github.md`
- 官方文档/TeX FAQ 25 条 URL：`docs/hints-research/round2-official.md`
- BibTeX/CJK/SARIF 32 条 URL：`docs/hints-research/round2-specialized.md`
- 已落地的规则基线（由 Organizer 完成）：`Hint.rule_id` 注入链路、`option_clash`、`double_script`

## 已证实缺陷（必须修，不是文案润色）

| 编号 | 缺陷 | 证据 |
| --- | --- | --- |
| D1 | XeLaTeX 的真实 `Missing character: There is no 中 (U+4E2D) in font ...` 匹配不到 `missing_glyph`，退化成旧表 `log_hint` 且建议 `T1 fontenc`（对 XeLaTeX 错误） | round1 第二批 e01/e02；实测 |
| D2 | `! Font \foo=NoSuchFont at 10.0pt not loadable: Metric (TFM) file not found.` 被 `missing_font` 贪婪捕获，提取出整句垃圾字体名 | round1 第二批 e03/d14；实测 |
| D3 | `Too many }'s`、`Double subscript`、`Option clash`、`Missing \begin{document}` 完全没有 hint | round1 c05/c17/c19、e09；实测 |
| D4 | `capacity` 把 `input stack size` 也建议调 `main_memory`，根因方向相反 | round1 c15；round2-official C2 |
| D5 | `unicode` 一律建议“改用 XeLaTeX/LuaLaTeX”，未说明该消息只来自 8 位引擎，也未区分中文/符号 | round2-official C1、round2-specialized 场景 1 |
| D6 | `missing_font` 无条件给 `fc-list`（Windows 无）和 `initexmf --update-fndb`（只刷 TeX 文件名库） | round2-official C3 |
| D7 | `missing_item` 只想到漏写 `\item`，漏掉 `\fbox`/`tabular` 单元格等成因 | round2-official C5、round2-github 族 8 |
| D8 | `no_output` 把 `\includeonly` 当作错误成因（它是正常配置） | round2-official C11 |
| D9 | `undefined_control` 只取 `l.N` 行最后一个命令，折行时命令在下一行会取错 | round2-official C10、round1 c02 折行证据 |
| D10 | `runaway` 未区分 `Runaway argument?` 与 `File ended while scanning use of \xxx`，也未利用 `\xxx` | round2-official C6 |

## 规则顺序（`RULE_IDS` 最终值，按此顺序写入 `_RULES`）

```
missing_package, missing_file, font_not_loadable, missing_font, unicode,
missing_glyph, undefined_citation, undefined_reference, undefined_environment,
missing_bib, float_overflow, capacity, no_output, runaway, math_mode,
double_script, fatal, undefined_control, end_mismatch, option_clash,
invalid_utf8, alignment_tab, missing_number, missing_item,
missing_begin_document, extra_close_brace, missing_right, bad_math_delimiter,
misplaced_noalign, illegal_unit, command_already_defined, no_line_to_end,
hyperref_pdf_string, fontspec_font_not_found, package_error, log_hint
```

顺序理由（必须写进代码注释）：
- `font_not_loadable` 早于 `missing_font`，否则 D2 的贪婪匹配继续污染；
- `fontspec_font_not_found` 早于 `package_error`，否则只得到“查看上下文”兜底；
- `missing_begin_document`/`extra_close_brace` 等具体 LaTeX 错误早于 `package_error` 与 `log_hint`；
- `capacity` 仍早于 `log_hint`，但内部按括号子类型分流。

## 新增规则规格

### R1 `font_not_loadable`
- 匹配：`Font\s+(\\[A-Za-z@]+)\s*=\s*([^\s]+)\s+at\s+[0-9.]+\s*pt\s+not\s+loadable(?::\s*([^.\n]+))?`
- 提取：字体规格（group2，如 `NoSuchFont`）、可选原因。
- 文案（中）：「字体 `<spec>` 无法加载（`<reason>`）。TeX 找不到该字体的度量/字形文件：若是 `\font\foo=<spec>` 直接指定，改用已安装字族；若是宏包内部字体，确认对应宏包完整安装（TeX Live：`tlmgr install <包名>`；MiKTeX：包管理器安装），不要手工伪造 TFM。」
- 命令：`kpsewhich <spec 小写>.tfm`
- kind：`missing_font_tfm`；需 `text_en`。

### R2 `missing_glyph`（修 D1）
- 正则改为：
  `Missing character:\s+There is no\s+(.+?)(?:\s+\(U\+([0-9A-Fa-f]+)\))?\s+in font\s+([^!\n]+)`
- 必须仍匹配旧样本 `Missing character: There is no α in font cmr10!`（char=α，font=cmr10）。
- 若 font 含 `nullfont`：文案「这是前面致命错误的连锁症状（nullfont）：`<char>` 并没有真正进入排版。先修日志里更早的第一条错误，不要在这里换字体。」kind 仍 `missing_glyph`，commands 为空。
- CJK 字符分支文案：「字体 `<font>` 没有中文字形 `<char>`。① XeLaTeX/LuaLaTeX：用 ctex（或 xeCJK）配置含中文的字体，并确认字体确实包含该字；② pdfLaTeX：中文不能交给默认拉丁字体，改用 XeLaTeX/LuaLaTeX + ctex。」
- 非 CJK 分支：保留 `\newunicodechar` 建议，但明确「它只把字符映射到已有 LaTeX 写法，不会凭空造字形；若字体本身缺该字形，要换字体」。
- **禁止**再出现「用 T1 fontenc 解决缺字形」。

### R3 `unicode`（修 D5）
- 文案必须说明：这条消息来自 pdfLaTeX/8 位引擎的 inputenc 层；XeLaTeX/LuaLaTeX 下同类问题表现为 `Missing character`。
- 中文/全角字符：优先「改用 XeLaTeX/LuaLaTeX + ctex；必须留在 pdfLaTeX 时用 CJK/ctex 的 pdfTeX 模式」。
- 非中文符号：优先「替换为等价 LaTeX 命令（如 `\ensuremath{\alpha}`）或用 `\newunicodechar` 映射」，不要无条件让用户换引擎。
- 保留 kind `unicode`。

### R4 `missing_begin_document`
- 匹配：`Missing\s+\\begin\{document\}`（忽略大小写）
- 文案：「正文或排版命令出现在 `\begin{document}` 之前。按可能性检查：① `\documentclass` 之后直接写了正文、`\maketitle`、`\section`；② 文件开头有不可见字符或 UTF-8 BOM（用“UTF-8 无 BOM”重新保存）；③ 误用 `\endinput`、或把正文写进了导言区。`\includeonly` **不是**本错误的原因。」
- kind：`missing_begin_document`。

### R5 `extra_close_brace`
- 匹配：`Too many \}'s`（注意真实文本是 `! Too many }'s.`；正则用 `Too many \}'s`）
- 文案：「右花括号比左花括号多。用编辑器括号匹配从报错行向前回溯；常见于 `\section{a}}`、`\textbf{a}}`、行尾 `\\` 后多打了一个 `}`；`\verb` 里的括号不参与配对。」
- kind：`extra_close_brace`。

### R6 `missing_right`
- 匹配：`Missing \\right\.? inserted` 或 `Missing delimiter \(\.? inserted`
- 文案：「`\left` 必须与 `\right` 成对：补 `\right)`/`\right]`/`\right.`。跨行或跨表格单元格时，把 `\left...\right` 放在同一组内，或改用 `\bigl...\bigr` 手动定尺寸。」
- kind：`missing_delimiter`。

### R7 `bad_math_delimiter`
- 匹配：`Bad math environment delimiter` 或 `Display math should end with \$\$`
- 文案：「数学定界符交叉/嵌套：`$...$`、`\(...\)`、`\[...\]` 不能互相包含。先修首条 `Display math should end with $$`，下游的 delimiter 报错多为连锁，不要单独改。」
- kind：`math_delimiter`。

### R8 `misplaced_noalign`
- 匹配：`Misplaced \\noalign`
- 文案：「`\hline`/`\toprule` 只能出现在表格行之间：放在某行 `\\` 之后，或 `\begin{tabular}` 后、第一行之前；表格外或单元格内使用会报此错。」
- kind：`misplaced_noalign`。

### R9 `illegal_unit`
- 匹配：`Illegal unit of measure \(pt inserted\)`
- 文案：「长度缺单位或单位拼错：`\vspace{2}` 会被当成 2pt；写 `2pt/2mm/2cm/2em/2ex`。报错里 `<to be read again>` 后面的字符就是拼错的单位首字母。」
- kind：`illegal_unit`。

### R10 `command_already_defined`
- 匹配：`Command\s+(\\[A-Za-z@]+)\s+already defined`
- 文案：「命令 `\foo` 已被定义（来自宏包、文档类或前文）。① 自己重复定义：用 `\renewcommand` 或 `\providecommand`；② 与宏包命令重名：换名（如 `\myfoo`）；③ 不要用 `\def` 覆盖内核命令。」
- kind：`command_conflict`。

### R11 `no_line_to_end`
- 匹配：`There's no line here to end`
- 文案：「`\newline`/`\\` 出现在没有内容的段落开头。删掉它，或先写内容；段落之间用 `\par`/`\medskip`，不要用 `\newline` 代替空行。」
- kind：`no_line_to_end`。

### R12 `hyperref_pdf_string`
- 匹配：`Token not allowed in a PDF string`
- 文案：「PDF 书签只接受纯文本，`\textbf`、数学、`^`/`_` 等 token 会被移除。给标题/章节写 `\texorpdfstring{排版版}{书签纯文本}`；或在导言区用 `\pdfstringdefDisableCommands` 统一降级。」
- 命令：`\texorpdfstring{<TeX 版>}{<纯文本>}`
- kind：`hyperref_pdf_string`。

### R13 `fontspec_font_not_found`
- 匹配：`The font\s+"([^"]+)"\s+cannot be found`（同时覆盖 `Package fontspec Error:` 与 tectonic 风格）
- 文案：「fontspec 找不到字体族 `<name>`。① 用系统字体名而不是字体文件名（Linux/macOS：`fc-list : family | grep -i <name>`；Windows：在“字体设置”里核对完整名称）；② 确认字体已安装（Linux `fc-cache -f` 后重开应用）；③ LuaLaTeX 还需要 `luaotfload-tool --update`；④ 先用 TeX Live 自带字体（Latin Modern）验证文档本身没问题。」
- 命令：`fc-list : family | grep -i <name>`、`luaotfload-tool --update`
- kind：`missing_font_family`。**必须早于 `package_error`。**

### 修改既有规则

- **R14 `capacity`**：解析 `TeX capacity exceeded, sorry \[([^\]]+)\]`，按子类型给根因：
  - `input stack size` → 循环/递归宏定义（如 `\def\a{\a\a}`），先断开递归，**不要**调大容量；
  - `main memory size` → 超长宏、过多 `\index`/`\glossary`、复杂表格/浮动体堆积（可先插 `\clearpage` 验证）；
  - `pool size` → 标签/命令名过多过长，或 `\newenvironment` 等漏右花括号；
  - `save size` → 环境/宏嵌套过深；
  - `buffer size` → `\caption`/章节可选参数/目录条目文本过长；
  - `hash size` → 命令名或标签数量过多；
  - 未知 → 通用排查。
  只有确认不是结构问题才调容量；命令区分发行版：TeX Live 编辑 `kpsewhich texmf.cnf` 指向的文件后 `fmtutil-sys --all`；MiKTeX `initexmf --edit-config-file=texmf.cnf` 后 `initexmf --dump`。**不要把 `main_memory` 写成唯一答案。**
- **R15 `runaway`**：提取 `File ended while scanning use of\s+(\\[A-Za-z@]+)` 的命令名并写进文案；说明「报错行号是 TeX 耗尽空间的位置，常常不可信；真正线索是 `Runaway argument?` 后面被吞掉的文本」；区分“参数没闭合（EOF）”与“段落/环境提前结束”。
- **R16 `missing_number`**：提取 `<to be read again>` 后面的 token，写进文案（如 `\vspace{x}` 的 `x`），并提示 `\includegraphics[width=...]`、`\hspace`、`\rule` 同类问题。
- **R17 `missing_item`**：补充「列表被放进 `\fbox/\mbox/\makebox`、或 `enumerate` 放进 `tabular` 单元格也会触发；此时补 `\item` 无效，应把列表移出盒子/单元格」。
- **R18 `no_output`**：删除 `\includeonly` 作为错误成因；改为「检查 `\documentclass`/`\begin{document}` 是否完整；空文档本来就不产生页面；陈旧 `.aux` 可删除后重跑」。
- **R19 `undefined_control`**：`l.N` 行可能折行，命令在下一行。实现为：取 `l.N` 行 + 紧随的一行拼成窗口，优先取 `l.N` 行内最后一个控制序列；若该行没有控制序列，取续行第一个控制序列；仍无则回退全文。保留现有 CORPUS 行为（`l.5 ... \badcmd` 必须仍得到 `\badcmd`）。
- **R20 `undefined_citation`**：文案补充「若日志出现 `No file <jobname>.bbl`，说明文献后端还没成功跑过：biber 路线用 `\addbibresource` + `biber <jobname>`；bibtex 路线用 `\bibliography` + `bibtex <jobname>`；然后再编译两轮」；保留现有 commands。
- **R21 `missing_font`**：命令改为带平台标注：Linux/macOS `fc-list | grep -i '<family>'`；Windows 无 `fc-list`，先核对系统字体名；`initexmf --update-fndb` 只刷新 TeX 文件名数据库，不等于刷新系统字体缓存。文案要写清这一点。

## 测试要求（实现时必须同时写）

1. `tests/test_hints_precedence.py`
   - `RULE_ORDER` 更新为上面的最终顺序；`CORPUS` 为每条规则至少补一条语料（新规则必须有）。
   - 优先级对：`Option clash` 早于 `package_error`；`fontspec ... cannot be found` 早于 `package_error`；`Font ... not loadable` 早于 `missing_font`；`Missing \begin{document}` + `Undefined control sequence` → `missing_begin_document`。
2. 新建 `tests/test_hints_real_logs.py`
   - 用 `round1-real-logs.md` 的真实日志片段（至少 18 条）参数化断言：命中规则 id、kind、关键提取值（命令名/宏包名/字体名/字符/上下标子类型）。
   - 重点断言 XeLaTeX 缺字形样本命中 `missing_glyph` 且文案不再出现 `fontenc`。
3. 新建 `tests/test_hints_false_positive.py`
   - 良性文本不得命中具体规则：普通 `Overfull \hbox` 仍是 `log_hint`；`Package hyperref Info:`、`Missing character` 出现在引号包裹的说明文本中、`Option clash` 作为被讨论的字符串（前有 `> ` 引用符）等。
   - 工具作用域：`hint_for_text("WARN - ...", tool_name="latex") is None`；Biber 的 `WARN -` 在 `tool_name="biber"` 时命中旧表；`File ended while scanning use of \foo` 在 `tool_name="bibtex"` 下不得套用 LaTeX 专属语义（如仍返回通用 runaway 可以，但不能返回 `\include` 类建议）。
   - 项目上下文：`hint_for_text(..., jobname="main", root_file="main.tex")` 时，biber/bibtex 命令替换为 `biber main`；子文件 `chapters/intro.tex` 不得被当作主文件。
4. 导出层：JSON `hints[].hint.rule_id` 非空且与规则一致；SARIF `properties["pytexlogs/hint"]["rule_id"]` 存在；CSV 表头不变。

## 交付与验收

- 只改 `src/pytexlogs/hints.py`、`src/pytexlogs/exporters/json_exporter.py`（如已改则核对）、`tests/`、`CHANGELOG.md`、`docs/hints-reference.md`（新建）。
- 不改 MiKTeX、不装 TeX 包、不改系统环境变量、不 commit、不回滚既有未提交改动。
- 跑测试必须 `PYTHONPATH=src`，否则导入的是 venv 里的旧包（会假失败）。
- 必须运行：`python -m pytest -q tests`、`ruff check --config pyproject.toml src tests`、`python -m compileall -q src\pytexlogs`。
- 完成后汇报：改动文件、测试数量与结果、ruff 结果、每条新规则的 rule_id/kind、仍未覆盖项。

---

## 追加规格（主智能体已用 web_fetch 核实的一手手册原文，第 3 轮必须纳入）

来源与原文短句（写入证据矩阵时必须保留 URL + 短引文）：

1. `https://raw.githubusercontent.com/plk/biber/dev/doc/biber.tex`
   - “Matching of citation keys and datasource entry keys is now case-sensitive ... If biber detects what looks like a case mismatch between citation keys, it will warn you.”
   - “The `--validate-structure` option is now called `--validate-datamodel`”
   - “Fields which are not defined in the data model ... are ignored ... If you would like to have ignored fields reported on, use the `--validate-datamodel` option.”
   - crossref 达到 `mincrossrefs`、xref 达到 `minxrefs` 后提升为 cited，两者分别计数。

2. `https://mirrors.ctan.org/macros/latex/contrib/biblatex/doc/biblatex.pdf`
   - `backend=bibtex, bibtex8, biber`，默认 `biber`；biber 支持 utf-8、on-the-fly reencoding、locale sorting；传统 BibTeX 仅 us-ascii，排序总是 case-insensitive。
   - `\addbibresource` 在导言区声明数据源；`\bibliography`/`\bibliographystyle` 是传统流程；biblatex 用 `.bcf`，流程 latex → biber → latex。
   - “while the biber/BibTeX input site is not case sensitive when it comes to entry types and field names ... the LaTeX side is case sensitive ...”

3. `https://mirrors.ctan.org/language/chinese/ctex/ctex.pdf`
   - 支持 eTeX/pdfTeX/XeTeX/LuaTeX/upTeX；`fontset` 可取 adobe/fandol/founder/mac/macnew/macold/ubuntu/windows/none/自定义。
   - 未指定 fontset 时按操作系统自动检测；`adobe/fandol/mac/ubuntu` 不支持 pdfLaTeX。
   - 源码消息：`\msg_critical:nnn { ctex } { fontset-unavailable }`，原文 `CTeX fontset '`#1' is unavailable in current mode.`

4. `https://mirrors.ctan.org/macros/xetex/latex/xecjk/xeCJK.pdf`
   - `missing-glyph` 消息源码：`CJKfamily '...' (...) does not contain glyph '...' ( U + \int_to_Hex:n { `#3 } ) ...`
   - `AutoFallBack`/`FallBack`：当前字体无字形时逐个后备字体查找，全部失败才发 `missing-glyph`；`\setCJKfallbackfamilyfont` 可设备用字体。

### 据此新增的规则（在 R1–R21 之外继续做）

#### R22 `fontset_unavailable`
- 匹配：`CTeX fontset\s+[\\'`]([^'`]+)[\\'`]\s+is unavailable in current mode`（容忍引号/反引号变体）
- 文案：「ctex 的 fontset `<name>` 在当前引擎模式下不可用（adobe/fandol/mac/ubuntu 不支持 pdfLaTeX）。按引擎选择：XeLaTeX/LuaLaTeX 可用 fandol 或 windows/mac（按平台）；必须用 pdfLaTeX 时改用 windows/fandol 中支持 pdfTeX 的组合，或 `fontset=none` + 自定义 `\setCJKmainfont`。」
- 命令：`xelatex <jobname>.tex`、`\usepackage[fontset=fandol]{ctex}`
- kind：`fontset_unavailable`；必须早于 `package_error`。

#### R23 `cjk_missing_glyph`（xeCJK 字形缺失）
- 匹配：`CJKfamily\s+'([^']*)'\s*\(([^)]*)\)\s+does not contain glyph\s+'([^']*)'\s*\(\s*U\s*\+\s*([0-9A-Fa-f]+)\s*\)`
- 必须同时容忍两种写法：`( U + 4E2D )`（手册源码）与 `(U+4E2D)`（日志常见压缩形式）。
- 文案：「CJKfamily `<family>` 的字体 `<font>` 不含字形 `<char>` (U+`<code>`)。按顺序处理：① 确认该 CJKfamily 是否真的配置了字体（`\setCJKfamilyfont`）；② 检查 FallBack/`\setCJKfallbackfamilyfont` 是否覆盖该字；③ 以上都没有才换字体或用 `\newunicodechar` 映射。」
- kind：`cjk_missing_glyph`；必须早于 `log_hint`，且不要与 `missing_glyph`（TeX 引擎消息）混淆。

#### R24 `missing_bbl`（文献后端未运行）
- 匹配：`No file\s+([^\s.]+)\.bbl`
- 文案：「还没有生成 `<jobname>.bbl`：文献后端尚未成功运行。biblatex+biber 流程是 latex → biber → latex（数据源用 `\addbibresource` 在导言区声明，走 `.bcf`）；传统 BibTeX 流程是 latex → bibtex → latex（用 `\bibliography`/`\bibliographystyle`）。确认文档用的 backend 与实际运行的命令一致，然后再编译两轮。」
- 命令：`biber <jobname>`、`bibtex <jobname>`
- kind：`missing_bbl`；必须早于 `undefined_citation`（有 bbl 缺失时先解决后端）。

#### 既有 biber/biblatex 文案修正
- `_build_legacy_hint` 返回的 Biber 提示（`I didn't find a database entry`）必须补充：
  「biber 对引用键与数据源条目键的匹配是**大小写敏感**的；但 entrytype/fieldname 在输入侧不区分大小写，不要混为一谈。数据模型外字段默认被忽略，需要报告时加 `--validate-datamodel`。」
- 若日志文本含 `case mismatch`（biber 的大小写不匹配告警），优先走专门文案：提示逐字符核对 `\cite{Key}` 与 `@type{Key,` 的大小写，而不是笼统“检查 .bib”。
- 由于旧提示表是 `dict[str,str]`，无法按日志动态插入；允许在 `hints.py` 中为 biber 增加独立规则 `biber_case_mismatch`（匹配 `case mismatch`，kind=`biber_key_case`，tools 限 biber），并把 biber 旧表文案同步改写。

### 测试追加
- `fontset_unavailable` 命中与文案包含“当前引擎模式不支持”。
- `cjk_missing_glyph` 两种空格变体都命中且提取 family/font/char/code。
- `missing_bbl` 命中且 jobname 上下文替换为 `biber main`。
- biber 大小写：`hint_for_text("... case mismatch ...", tool_name="biber")` 命中新规则；`tool_name="latex"` 不命中。
- biblatex backend 流程差异出现在 `missing_bbl` 文案中（断言同时包含 `biber` 与 `bibtex` 两条流程）。
