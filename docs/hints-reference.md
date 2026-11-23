# PyTeXLogs 提示规则参考（hints）

本页面向使用者：列出每条可执行建议（hint）的触发日志、建议要点、适用工具
与误报边界。规则按 `src/pytexlogs/hints.py` 中的 `_RULES` 顺序匹配，先命中的
具体规则优先于兜底规则；`rule_id` 同时出现在 JSON/SARIF 导出里，便于追溯。
规则总数以 `len(RULE_IDS)` 实测为准，当前为 **41** 条。

工具作用域：`latex` 规则仅在 LaTeX 引擎日志（pdflatex/xelatex/lualatex/tectonic）
上生效；`biber`/`bibtex` 旧提示表按工具隔离，避免跨工具误判。

## 规则表

| rule_id | 触发日志（典型） | 建议要点 | 工具作用域 | 误报边界 |
| --- | --- | --- | --- | --- |
| `missing_package` | `File \`siunitx.sty' not found.` | 缺宏包/文档类：TeX Live `tlmgr install <包>`，MiKTeX 包管理器安装 | latex | 只认 `.sty/.cls/.def/.cfg/.clo/.ldf`；图片、`.bib` 不归此规则 |
| `missing_file` | `File \`fig.png' not found.` | 按类型分流：图片核对相对路径与 `\graphicspath`；`.bib` 核对路径大小写；一般文件核对 `\input/\include/\includegraphics` 路径 | latex | 宏包后缀已由 `missing_package` 处理 |
| `font_not_loadable` | `! Font \foo=NoSuchFont at 10.0pt not loadable: Metric (TFM) file not found.` | 字体度量/字形文件找不到：直接指定的改用已安装字族；宏包内部字体确认宏包完整安装，不要手工伪造 TFM；可用 `kpsewhich <spec>.tfm` 核查 | latex | 先于 `missing_font`，避免整句被贪婪抓成字体名 |
| `tfm_font_missing` | `Metric (TFM) file ecrm1000.tfm not found`（pdflatex，无 `\font=` 控制名形式） | pdflatex 缺 TFM 通常是缺编码字体宏包（`ecrm1000.tfm` 属 `ec`/`cm-super`），不是 fontspec 字体族问题，不要去系统字体目录找 OpenType；TeX Live `tlmgr search --file <name>.tfm --global` 定位包后 `tlmgr install <包>`（或 `collection-fontsrecommended`），MiKTeX 包管理器装对应字体包 | pdflatex | 与 `font_not_loadable`（`\foo=` 直指定形式）、`fontspec_font_not_found`（Xe/Lua OpenType 族找不到）分属三条链路 |
| `missing_font` | `Font \`NotoSans' not found` | 核对字体是否安装、字族名是否正确；Linux/macOS 用 `fc-list \| grep -i '<family>'`；Windows 在字体设置里核对完整名称 | latex | `Missing character` 归 `missing_glyph`；`initexmf --update-fndb` 只刷新 TeX 文件名库，不等于刷新系统字体缓存 |
| `fontset_unavailable` | `CTeX fontset 'fandol' is unavailable in current mode.` | 当前引擎模式不支持该 fontset（adobe/fandol/mac/ubuntu 不支持 pdfLaTeX）：按引擎选择匹配 fontset（`xelatex <主文件>.tex`），或 `fontset=none` 后用 `\setCJKmainfont` 自定义；备选 `\usepackage[fontset=fandol]{ctex}` | latex / ctex | 不是字体文件缺失，而是引擎与 fontset 不匹配 |
| `unicode` | `! LaTeX Error: Unicode character 中 (U+4E2D) not set up for use with LaTeX.` | 该消息只来自 pdfLaTeX/8 位引擎的 inputenc 层；Xe/Lua 下同类问题表现为 `Missing character`。中文/全角：优先 XeLaTeX/LuaLaTeX + ctex，必须留 pdfLaTeX 时用 CJK/ctex 的 pdfTeX 模式；符号：优先替换为等价 LaTeX 命令或 `\newunicodechar` 映射 | latex（8 位引擎） | 不要把 Xe/Lua 缺字形也归到本规则 |
| `cjk_missing_glyph` | `CJKfamily 'song' ([FandolSong-Regular]) does not contain glyph '中' (U+4E2D)` | xeCJK 字体族缺字，按顺序排查：① `\setCJKmainfont`/`\newCJKfontfamily` 给该 family 配的字体是否含此字；② FallBack（`\setCJKfallbackfamilyfont` / fallback 列表）是否覆盖；③ 仍缺再换中文字体或 `\newunicodechar` 局部映射 | xelatex / lualatex | 与引擎级 `missing_glyph` 分开：本条是 xeCJK 字体族消息 |
| `missing_glyph` | `Missing character: There is no 中 (U+4E2D) in font [lmroman10-regular]:mapping=tex-text;!` | 引擎缺字形：先判引擎是否就位——已在 XeLaTeX/LuaLaTeX + ctex/xeCJK 时，首要动作是换含该字的 CJK 字体或补 FallBack（xeCJK 可按字体文件名加载，无需 NFSS `\DeclareFontFamily`）；仍在 pdflatex 时才切 Xe/Lua 并配中文字体；非 CJK 换含该字形的字体或 `\newunicodechar`（只映射到已有写法，不造字形）；`nullfont` 缺字是前置致命错误的连锁，先修更早的第一条错误 | latex 各引擎 | 不再建议用 T1 `fontenc` 解决缺字形 |
| `missing_bbl` | `No file main.bbl.` | 文献后端还没成功跑过。biblatex+biber：`\addbibresource{refs.bib}`（**带 `.bib`**），latex → biber → latex 两轮，走 `.bcf`；传统 BibTeX：`\bibliography{refs}`（**不带 `.bib`**）+ `\bibliographystyle`，latex → bibtex → latex；先确认 backend 与实际命令一致 | latex | 先于 `undefined_citation`：后端没跑时先解决后端 |
| `undefined_citation` | `LaTeX Warning: Citation \`key1' undefined on input line 3.` | 核对 `.bib` 条目键与 `\cite{key}`；biblatex 未定义引用在 PDF 里显示为粗体引用键；先读 `.blg` 原始消息，按三级诊断：bst 打不开 → bib 打不开 → entry not found，再查 `.bib` 是否被 `filecontents` 覆盖或陈旧；确认 biber/bibtex 已成功运行。`bibwarn` 默认开启，同一条告警可能在 `.blg` 与 `.log` 各出现一次，不是两个独立问题 | latex | `.bbl` 缺失归 `missing_bbl` |
| `undefined_reference` | `LaTeX Warning: Reference \`sec:intro' ... undefined` | 核对 `\label`/`\ref` 拼写，再编译一轮让 `.aux` 收敛 | latex | 多为需要重跑，不是删除标签 |
| `undefined_environment` | `! LaTeX Error: Environment equationn undefined.` | 确认提供该环境的宏包已 `\usepackage`，或检查环境名拼写/大小写 | latex | — |
| `missing_bib` | `I couldn't open database file refs.bib` | 核对 `.bib` 路径（相对主文件目录）与大小写。写法差异：`\addbibresource{refs.bib}` 必须带扩展名；`\bibliography{refs}` 不带 | bibtex / biber / latex | 图片缺失不归此规则 |
| `biber_case_mismatch` | biber 日志中的 `case mismatch` | biber 对引用键与数据源条目键**大小写敏感**：逐字符核对 `\cite{Key}` 与 `.bib` 的 `@type{Key,}`；entrytype/fieldname 输入侧不区分大小写；数据模型外字段默认忽略，需要报告时加 `--validate-datamodel` | 仅 biber | latex/bibtex 日志不命中；普通拼写不一致不归此规则 |
| `float_overflow` | `! Too many unprocessed floats.` | 章节间加 `\clearpage`，或用 `float` 宏包的 `[H]` 位置 | latex | — |
| `capacity` | `! TeX capacity exceeded, sorry [input stack size=5000].` | 按括号子类型分流：`input stack size` 循环点可能是自写宏/环境无限递归，也可能在宏包/书目样式展开链里（如 hyperref 与书目样式互包链接命令），顺着日志 `->` 展开行定位，先断递归，不要调容量；`main memory size` 查长宏、过多索引/术语条目、浮动体堆积，pgfplots 场景优先外置化（每图单独编译、主任务只插图）、降点数、插 `\clearpage`；`pool size` 查过长标签/命令名或未闭合定义；`save size` 查嵌套过深；`buffer size` 查过长标题/可选参数；`hash size` 查命令名/标签数量。确认非结构问题后再按发行版调容量（TeX Live 改 `texmf.cnf` 后 `fmtutil-sys --all`；MiKTeX `initexmf --edit-config-file=texmf.cnf` 后 `initexmf --dump`） | latex | `input stack size` 不是内存不足，调 `main_memory` 方向相反 |
| `no_output` | `No pages of output.` | 检查 `\documentclass`/`\begin{document}` 是否完整；空文档本来就不产生页面；可删除陈旧 `.aux` 后重跑 | latex | `\includeonly` 是正常配置，不是本错误成因 |
| `runaway` | `Runaway argument?`；`! File ended while scanning use of \textbf .` | 参数/环境未闭合：报错行号是 TeX 耗尽空间的位置，常不可信，真正线索是 `Runaway argument?` 后被吞掉的文本；从被扫描命令的参数向前回溯未配对 `{}` 或未闭合环境 | latex | biber/bibtex/makeindex 后端日志下不命中 |
| `math_mode` | `! Missing $ inserted.` | 数学模式不匹配：检查漏写的 `$`、`\text` 内特殊字符、`\ensuremath` 使用 | latex | — |
| `double_script` | `! Double subscript.` / `! Double superscript.` | 上下标重复非法：多字符上下标加花括号 `x_{1,2}`；上下标并存写成 `x_{1}^{2}`。注意分组意图：`${x_n}_i$` 是外层整体再加下标，`x_{n_i}` 是下标内再套下标；重音原子特例——`${\hat{a}_b}_c$` 外层花括号会被 TeX 剥掉仍报 Double subscript，需空组保留分组 `${{}\hat{a}_b}_c$` | latex | — |
| `fatal` | `! Emergency stop.`；`Fatal error occurred` | 编译被致命错误中断：先修复 `Emergency stop` 上方的第一条错误 | latex | 本条是中断信号，不解释具体根因 |
| `undefined_control` | `! Undefined control sequence.` + `l.5 ... \badcmd`；`l.2 \newcommand{dice}` | 普通未定义命令检查拼写/大小写，宏包提供的命令确认 `\usepackage` 已加载；`l.N` 行是 `\newcommand`/`\renewcommand`/`\providecommand`/`\def`/`\newenvironment` 时提取被定义裸名称并提示补反斜杠；定义构造后仍有控制序列时优先报后者 | latex | `Missing \begin{document}` 等具体错误优先于本兜底；定义行不误报包装命令，也不生成 `<name>.sty` 安装命令 |
| `end_mismatch` | `! LaTeX Error: \begin{document} ended by \end{itemize}.` | 环境嵌套有误：每个 `\begin` 都要有同名 `\end` | latex | — |
| `option_clash` | `! LaTeX Error: Option clash for package graphicx.` | 宏包被加载两次且选项不同：先读错误文本两组选项（`already been loaded with options: [...]` 与 `attempt to load with options [...]`）；修法任选：合并为单次 `\usepackage`、首次加载前 `\PassOptionsToPackage{<选项>}{<包>}`、或把冲突选项提升为 `\documentclass[...,<选项>]{<类>}` 全局选项；先加载者可能被其他宏包间接拉入 | latex | 先于通用 `package_error` 兜底 |
| `invalid_utf8` | `! Package inputenc Error: Invalid UTF-8 byte sequence.` | 报错文件另存为 UTF-8（无 BOM），检查是否混入 GBK 字符；`file --mime-encoding` 为 Unix/Linux 工具，Windows 可在编辑器状态栏查看编码或用 PowerShell 读字节 | latex | — |
| `alignment_tab` | `! Extra alignment tab has been changed to \cr.`；`Misplaced alignment tab character &.` | 每行 `&` 数量与列格式（如 `lcr`）一致 | latex | — |
| `missing_number` | `! Missing number, treated as zero.` | 长度/数字参数缺失或漏单位；提取 `<to be read again>` 后的待读 token；同类位置：`\vspace`、`\hspace`、`\rule`、`\includegraphics[width=...]` | latex | — |
| `missing_item` | `! LaTeX Error: Something's wrong--perhaps a missing \item.` | itemize/enumerate 每个条目开头补 `\item`；列表被放进 `\fbox/\mbox/\makebox` 或 enumerate 放进表格单元格也会触发，此时补 `\item` 无效，应把列表移出盒子/单元格 | latex | — |
| `missing_begin_document` | `! LaTeX Error: Missing \begin{document}.` | 正文或排版命令出现在 `\begin{document}` 之前：① 文档类后直接写正文/`\maketitle`/`\section`；② 文件开头有不可见字符或 UTF-8 BOM（另存 UTF-8 无 BOM）；③ 误用 `\endinput` 或正文写进导言区；④ 导言区 `\newcommand`/`\def`/`\newenvironment` 定义笔误（命令名漏写反斜杠），命令名被当成正文排版 | latex | `\includeonly` 不是本错误成因 |
| `extra_close_brace` | `! Too many }'s.` | 右花括号比左花括号多：用编辑器括号匹配从报错行回溯；常见于 `\section{a}}`、`\textbf{a}}`、行尾 `\\` 后多打 `}`；`\verb` 内括号不参与配对 | latex | — |
| `missing_right` | `! Missing \right. inserted.`；`Missing delimiter (. inserted)` | `\left` 必须与 `\right` 成对：补 `\right)`/`\right]`/`\right.`；其中 `.` 是合法隐形定界符（该侧无可见围栏，如单侧大括号 `\left\{ ... \right.`），不是漏写标点，不要删掉；跨行或跨单元格时把 `\left...\right` 放在同一组，或改用 `\bigl...\bigr` 手动定尺寸 | latex | — |
| `bad_math_delimiter` | `! Bad math environment delimiter.`；`! Display math should end with $$.` | 数学定界符交叉/嵌套：`$...$`、`\(...\)`、`\[...\]` 不能互相包含；先修首条 `Display math should end with $$`，下游 delimiter 报错多为连锁 | latex | 不要单独改下游连锁报错 |
| `misplaced_noalign` | `! Misplaced \noalign.` | `\hline`/`\toprule` 只能出现在表格行之间：放在某行 `\\` 之后，或 `\begin{tabular}` 后、第一行之前；表格外/单元格内使用会报错 | latex | — |
| `illegal_unit` | `! Illegal unit of measure (pt inserted).` | 长度缺单位或单位拼错：`\vspace{2}` 会被当成 2pt，应写 `2pt/2mm/2cm/2em/2ex`；`<to be read again>` 后的字符就是拼错的单位首字母 | latex | — |
| `command_already_defined` | `! LaTeX Error: Command \foo already defined.` | 命令已被宏包/文档类/前文定义：自己重复定义改用 `\renewcommand`/`\providecommand`；与宏包命令重名则换名（如 `\myfoo`）；不要用 `\def` 覆盖内核命令 | latex | — |
| `no_line_to_end` | `! LaTeX Error: There's no line here to end.` | `\newline`/`\\` 出现在没有内容的段落开头：删掉它或先写内容；段落之间用 `\par`/`\medskip`，不要用 `\newline` 代替空行 | latex | — |
| `hyperref_pdf_string` | `Package hyperref Warning: Token not allowed in a PDF string (Unicode):` | PDF 书签只接受纯文本，`\textbf`、数学、`^`/`_` 等 token 会被移除：标题/章节写 `\texorpdfstring{排版版}{书签纯文本}`，或导言区用 `\pdfstringdefDisableCommands` 统一降级 | latex / hyperref | 这是书签降级警告，不影响正文排版 |
| `fontspec_font_not_found` | `! Package fontspec Error: The font "NoSuchFontFamilyXYZ" cannot be found.` | fontspec 找不到字体，先分“按名/按文件”：按名核对 family 全名（Linux/macOS `fc-list : family \| grep -iF "<name>"`；Windows 在字体设置核对）；字体在 TEXMF 树内时 LuaTeX 可按名，XeTeX 在 Windows/Linux 可、macOS 只能按文件名。按文件核对扩展名、`Path=`、`UprightFont/BoldFont` 等变体，并用 `kpsewhich "<name>"` 定位。`luaotfload-tool --update` 仅 LuaLaTeX | xelatex / lualatex | 先于 `package_error` 兜底；不是缺 fontspec 宏包；不能笼统要求“用系统字体名而非文件名” |
| `package_error` | `! Package hyperref Error: Wrong driver.` | 通用宏包错误：查看该行上下文与宏包选项，必要时升级/降级该宏包 | latex | 兜底规则；更具体的字体/选项/定界符规则已在前面命中 |
| `log_hint` | `Overfull \hbox ...`、`Underfull \hbox/\vbox ...`、`Rerun to get cross-references right`、bibtex/biber 通用警告等内建提示表 | 按旧提示表给出通用建议；表内条目按工具（LaTeX/BibTeX/Biber）隔离 | 按工具 | 兜底桶；被引用块（`> `）、注释（`% `）、成对引号包裹或解释性散文提及的样例字符串不参与匹配 |

## 误报与边界说明

- **引用块样例不匹配**：以 `> ` 开头的行视为讨论/引用文本，不参与规则匹配，避免把文档里摘录的错误样例当成真实日志。
- **工具隔离**：未指定工具时合并三张旧提示表；指定 `tool_name` 后只使用对应工具的表。Biber 的 `WARN -` 不会命中 LaTeX 规则，反之亦然。
- **上下文替换**：命令模板里的 `<jobname>`、`<主文件>` 会在传入项目名/主文件路径后替换为真实值；子文件（如 `chapters/intro.tex`）不会被当作主文件。
- **追加信息不改变数据模型**：`rule_id` 只追加在结构化 hint 上；条目字段集合、JSON `results` 形状、CSV 表头、SARIF 必填字段均保持不变。
