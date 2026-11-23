# 第 6 轮：本机真实 MiKTeX 日志复核与修复证据



* 仓库：`D:\Document YM\Desktop Document\Tools_Development\PyTeXLogs`

* 解释器：`D:\Document YM\Desktop Document\Tools_Development\PyTeXMK\.venv\Scripts\python.exe`（Python 3.15.2）

* `PYTHONPATH=D:\Document YM\Desktop Document\Tools_Development\PyTeXLogs\src`（绝对路径）

* ruff：`C:\Applications\Scoop\persist\uv\cache\archive-v0\5BGcLFrJKq9gc1UH\ruff-0.17.5.data\scripts\ruff.exe`，0.17.5

* 范围限制：本轮只改 `src/pytexlogs/hints.py`、`src/pytexlogs/parsers/latex.py`、`src/pytexlogs/parsers/biber.py`、`tests/` 下 fixture 与测试，以及本文档；未 commit，未改既有 `docs/hints-research/*.md`、CHANGELOG、README；未动 MiKTeX 本体 / 配置，未改系统 PATH / 环境变量，未执行任何 `tlmgr` / `miktex packages install`。

## 真实环境基线（本机实跑，非推断）



* MiKTeX 26.5 Portable，bin 目录：`C:\Applications\Scoop\apps\miktex\current\texmfs\install\miktex\bin\x64`。

* 实测版本（取自各 fixture 日志首行）：pdfTeX 3.141592653-2.6-1.40.29、XeTeX 3.141592653-2.6-0.999998、LuaHBTeX 1.25.7、biber 2.22；`pdflatex`/`xelatex`/`lualatex`/`biber`/`bibtex`/`latexmk` 均在 PATH。

* 采集工作目录：`%TEMP%\pytexlogs_real_compile_r6\<场景子目录>`，全部编译加 `--disable-installer`；产物日志原样落到 `tests/fixtures/real_miktex/`。

* 历史轮次 “Windows 本机无 TeX” 的结论已被推翻，本文所有场景均为本机真实编译产出。

## 场景与 fixture 总览



| 编号       | fixture（`tests/fixtures/real_miktex/`） | 工具 / 引擎  | 临时工作目录              | 条目数（修复后）     | 命中规则（修复后）                                                                               |
| -------- | -------------------------------------- | -------- | ------------------- | ------------ | --------------------------------------------------------------------------------------- |
| B1       | `xelatex_fontspec_not_found.log`       | xelatex  | `b1_fontspec`       | 103          | `fontspec_font_not_found` ×3、`font_not_loadable` ×1、`missing_glyph` ×1                  |
| B2       | `pdflatex_newcommand_dice.log`         | pdflatex | `b2_newcommand`     | 11           | `missing_begin_document` ×2、`missing_number` ×3、`illegal_unit` ×1，无 `undefined_control` |
| B3a      | `pdflatex_ctex_adobe_fontset.log`      | pdflatex | `b3a_ctex_adobe`    | 288          | `fontset_unavailable` ×1                                                                |
| B3b      | `xelatex_xecjk_missing_glyph.log`      | xelatex  | `b3b_xecjk_glyph`   | 98           | `missing_glyph` ×1（聚合 4 个缺字形）                                                           |
| B3c      | `biber_case_mismatch.blg`              | biber    | `b3c_biber_case`    | 2            | `biber_case_mismatch` ×1、`log_hint` ×1                                                  |
| B3d      | `pdflatex_undefined_cite_ref.log`      | pdflatex | `b3d_warn_quotes`   | 30           | `undefined_citation` ×1、`undefined_reference` ×1                                        |
| L1       | `lualatex_fontspec_not_found.log`      | lualatex | `l1_lua_fontspec`   | 103          | `fontspec_font_not_found` ×3、`font_not_loadable` ×1、`missing_glyph` ×1                  |
| L2       | `lualatex_xecjk_missing_glyph.log`     | lualatex | `l2_lua_xecjk`      | 404          | `missing_glyph` ×1（聚合 12 条重复缺字形、4 个字形）                                                  |
| B1-bbl   | `pdflatex_biblatex_before_biber.log`   | pdflatex | `b1_biblatex_first` | 100          | `missing_bbl` ×2、`undefined_citation` ×1                                                |
| B2-pass1 | `pdflatex_biber_chain_pass1.log`       | pdflatex | `b2_biber_chain`    | 100          | `missing_bbl` ×2、`undefined_citation` ×1                                                |
| B2-blg   | `biber_chain.blg`                      | biber    | `b2_biber_chain`    | 0（INFO only） | 无 WARN；biber 作用域下不抢答 `undefined_citation`/`undefined_reference`                         |
| B2-final | `pdflatex_biber_chain_final.log`       | pdflatex | `b2_biber_chain`    | 95           | 无 `missing_bbl`、无 `undefined_citation`                                                  |

## 编译命令与源码

统一命令模板（工作目录设在场景子目录内）：



```
& "C:\Applications\Scoop\apps\miktex\current\texmfs\install\miktex\bin\x64\xelatex.exe" `
    -interaction=nonstopmode --disable-installer main.tex
# pdflatex / biber 同理；biber 无 installer 开关，直接 `biber main`。
```

### B1（xelatex + fontspec 找不到字族）

`main.tex`：



```
\documentclass{article}
\usepackage{fontspec}
\setmainfont{NoSuchFontFamilyXYZ}
\begin{document}
Hello
\end{document}
```

命令：`xelatex -interaction=nonstopmode --disable-installer main.tex`。

### B2（`\newcommand{dice}` 真实首错）

`main.tex`：



```
\documentclass{article}
\newcommand{dice}
\begin{document}
Hello
\end{document}
```

命令：`pdflatex -interaction=nonstopmode --disable-installer main.tex`。

### B3a（ctex `fontset=adobe`，pdflatex）

`main.tex`：



```
\documentclass{article}
\usepackage[fontset=adobe]{ctex}
\begin{document}
Hello 中文
\end{document}
```

命令：`pdflatex -interaction=nonstopmode --disable-installer main.tex`。

### B3b（xeCJK 配不含汉字的拉丁字体）

`main.tex`：



```
\documentclass{article}
\usepackage{xeCJK}
\setCJKmainfont{Latin Modern Roman}
\begin{document}
中文测试 abc
\end{document}
```

命令：`xelatex -interaction=nonstopmode --disable-installer main.tex`。

### B3c（biber 引用键大小写不匹配）

`main.tex`：



```
\documentclass{article}
\usepackage[backend=biber]{biblatex}
\addbibresource{refs.bib}
\begin{document}
\cite{Key}
\printbibliography
\end{document}
```

`refs.bib`：



```
@article{key,
  author = {Doe, John},
  title = {Sample Title},
  year = {2020}
}
```

命令顺序：`pdflatex -interaction=nonstopmode --disable-installer main.tex` → `biber main`（取 `.blg` 即可；第二遍 pdflatex 未跑，不影响 `.blg` 证据）。

### B3d（未定义 Citation / Reference 警告）

`main.tex`：



```
\documentclass{article}
\begin{document}
\cite{key}
See \ref{sec:intro}.
\end{document}
```

命令：`pdflatex -interaction=nonstopmode --disable-installer main.tex`。

### L1（lualatex + fontspec 找不到字族）

`main.tex`：



```
\documentclass{article}
\usepackage{fontspec}
\setmainfont{NoSuchFontFamilyXYZ}
\begin{document}
Hello
\end{document}
```

命令：`lualatex -interaction=nonstopmode --disable-installer main.tex`。

### L2（lualatex/ctexart 用拉丁字体当 CJK 主字体）

`main.tex`：



```
\documentclass{ctexart}
\setCJKmainfont{Latin Modern Roman}
\begin{document}
中文测试
\end{document}
```

命令：`lualatex -interaction=nonstopmode --disable-installer main.tex`。

### B1-bbl / B2（biblatex + backend=biber 完整链路）

`main.tex`：



```
\documentclass{article}
\usepackage[backend=biber]{biblatex}
\addbibresource{refs.bib}
\begin{document}
\cite{key}
\printbibliography
\end{document}
```

`refs.bib`：



```
@article{key,
  author = {Doe, John},
  title = {Sample Title},
  year = {2020}
}
```

链路命令（工作目录设在 `b2_biber_chain` 子目录内）：



```
pdflatex -interaction=nonstopmode --disable-installer main.tex  # 首遍：缺 main.bbl
biber main                                                        # 生成 main.bbl
pdflatex -interaction=nonstopmode --disable-installer main.tex  # 第二遍
pdflatex -interaction=nonstopmode --disable-installer main.tex  # 第三遍（收敛）
```

B1-bbl fixture 只取首遍 `.log`（未跑 biber）；B2 链路分别留存首遍 `.log`、`.blg`、完成态 `.log`。



***

## B1：fontspec 缺字族 + `Font ... not loadable`

### 1. 三个 `Package fontspec Error` 是真实独立错误，不是重复入队

真实日志第 60、96、117 行各有一个独立错误块，对应字体形状解析过程中的多次请求；第 82/87/92 行的 Info 记录分别是 `NoSuchFontFamilyXYZ/BI`、`/B`、`/I`：



```
60: ! Package fontspec Error:
61: (fontspec)                The font "NoSuchFontFamilyXYZ" cannot be found;
...
82: Package fontspec Info:
83: (fontspec)             Could not resolve font "NoSuchFontFamilyXYZ/BI" (it
84: (fontspec)             probably doesn't exist).
87: (fontspec)             Could not resolve font "NoSuchFontFamilyXYZ/B" (it
92: (fontspec)             Could not resolve font "NoSuchFontFamilyXYZ/I" (it
96: ! Package fontspec Error:
117: ! Package fontspec Error:
```

**结论与约定**：这 3 条是真实独立错误，解析层与 hints 层都**没有**去重、没有合并、没有改变 `results` 计数；测试断言 fontspec 条目数 == 3，三条均命中 `fontspec_font_not_found`。若后续做摘要降噪，只能在展示层按字体族聚合，且必须保留 BI/B/I 形状信息，不得影响 `LogEntry`/`ReportEntry` 集合、JSON `results`、CSV 行数与 SARIF 结果数；本轮未做聚合。

### 2. `Font ... not loada\nble` 折行与 NFSS 规格

真实日志第 150–151 行（`max_print_line` 79 列把 `loadable` 拆成 `loada` / `ble`）：



```
150: ! Font TU/NoSuchFontFamilyXYZ(0)/m/n/10=NoSuchFontFamilyXYZ at 10.0pt not loada
151: ble: Metric (TFM) file or installed font not found.
```

### 修复前后对比（同一条目，tool=`xelatex`）



| 项           | 修复前                                                | 修复后                                                                       |
| ----------- | -------------------------------------------------- | ------------------------------------------------------------------------- |
| 命中 rule\_id | `tfm_font_missing`（误判）                             | `font_not_loadable`                                                       |
| 抽取字体名       | `or.tfm`（从 “or installed” 抓 `or` 再补 `.tfm`）        | `NoSuchFontFamilyXYZ`（NFSS 规格 `TU/NoSuchFontFamilyXYZ(0)/m/n/10` 保留在条目原文） |
| 原因          | 走 pdfTeX 缺 TFM 度量包链路                               | `Metric (TFM) file or installed font not found`（OpenType / 系统字体族找不到）      |
| 文案          | “pdflatex 找不到 TFM 度量文件 `or.tfm` … ec/cm-super 字体包” | 不出现 `pdflatex`、不出现 `or.tfm`；提示核对字体全名 / 拼写 / 安装与扩展名 /`Path=`               |
| 建议命令        | `tlmgr search --file or.tfm --global`              | \`fc-list : family                                                        |
| kind        | `tfm_font_missing`                                 | `missing_font`                                                            |

### 代码改动点



* `_FONT_NOT_LOADABLE_RE`：规格段允许 `\command` 或任意不含空白 / 等号的 NFSS 串（覆盖 `TU/...(0)/m/n/10`）；`loadable` 容忍 `loada\s*ble` 折行。

* `_match_font_not_loadable`：显式 `.tfm` 文件名的消息拒绝命中，交给 `tfm_font_missing`（保证 `font_not_loadable` 优先但不抢占 pdfTeX 缺包链路）。

* `_TFM_MISSING_RE`：只认明确带 `.tfm` 文件名的 `Metric (TFM) file <name>.tfm not found`；`Metric (TFM) file or installed font not found` 不再进入该规则，也不会把 `or` 当文件名。

* `_build_font_not_loadable`：reason 含 “installed font” 或引擎为 xelatex/lualatex 时走 OpenType / 系统字体分支，不给 `kpsewhich *.tfm` /ec 包建议。

* `_build_tfm_missing`：按 `tool_name` 区分引擎；xelatex/lualatex 下不再写死 “pdflatex 找不到 TFM”，文案说明 TFM 属 8 位 pdfTeX 链路。

* 规则生成器把 `tool_name` 透传给 `font_not_loadable` / `tfm_font_missing` 构建器。

### 回归断言（`test_real_miktex_round6.py`）



* fontspec 错误条目恰为 3 条，均 `fontspec_font_not_found`；原始日志含 `/BI`、`/B`、`/I` 三个变体。

* `Font ... not loada` 条目命中 `font_not_loadable`，文案含 `NoSuchFontFamilyXYZ`；无 `or.tfm`、无 `pdflatex`；整条日志无 `tfm_font_missing`；命令不含 `.tfm`。

## B2：`\newcommand{dice}` 真实首错不是未定义命令

真实错误链（日志行号 → 规则）：



```
31: ! LaTeX Error: Missing \begin{document}.        → missing_begin_document
42: ! Missing number, treated as zero.              → missing_number
51: ! Missing = inserted for \ifnum.               → -
58: ! Missing number, treated as zero.              → missing_number
67: ! Missing number, treated as zero.              → missing_number
76: ! Illegal unit of measure (pt inserted).        → illegal_unit
88: ! Missing control sequence inserted.            → -
99: ! You already have nine parameters.            → -
107: ! Argument of \begin has an extra }.          → -
120: ! Paragraph ended before \begin was complete.   → -
130: ! LaTeX Error: Missing \begin{document}.       → missing_begin_document
```



* 首条错误规则为 `missing_begin_document`；整条日志**不出现** `undefined_control`。

* **合成用例标注**：`tests/test_hints_round6.py` 中 `\newcommand{dice}` 用例是**合成错误帧**，只验证 “定义包装命令不被报成未定义控制序列”，**不等于**真实编译首错；真实首错链条以本 fixture 为准。文档不得写成 “真实日志已覆盖 `\newcommand{dice}` → undefined\_control”。

## B3a：ctex fontset 不可用（续行括号前缀）

真实日志第 496–497 行：



```
496: ! Critical Package ctex Error: CTeX fontset `adobe' is unavailable in current
497: (ctex)                         mode.
```



* 修复前：`current` 与 `mode` 之间被 `(ctex)` 续行前缀打断，`_FONTSET_UNAVAILABLE_RE` 失配，落到兜底 `package_error`。

* 修复后：正则允许 `current` 与 `mode` 之间出现换行 + 任意 `(<pkg/class>)` 前缀与空格；命中 `fontset_unavailable`，文案含 `adobe`，不再落 `package_error`。

* 本机该消息前缀为 `Critical Package ctex Error`（任务书示例的 `Critical Class ctexart Error` / `(ctexart)` 为另一变体）；正则同时保留 `Package`/`Class`/`Critical Package`/`Critical Class` 识别，括号前缀宽度限制 1–40 字符。

## B3b：xeCJK 缺字形（无 `(U+XXXX)` 后缀 + 折行）

真实日志第 281–288 行，4 个汉字 `中文测试`，每条被 79 列折成两行，且**没有** `(U+XXXX)` 码位后缀：



```
281: Missing character: There is no 中 in font Latin Modern Roman 10 Regular/OT:scrip
282: t=hani;language=dflt;!
283: Missing character: There is no 文 in font Latin Modern Roman 10 Regular/OT:scrip
284: t=hani;language=dflt;!
285: Missing character: There is no 测 in font Latin Modern Roman 10 Regular/OT:scrip
286: t=hani;language=dflt;!
287: Missing character: There is no 试 in font Latin Modern Roman 10 Regular/OT:scrip
288: t=hani;language=dflt;!
```



* 修复前：折行首行不以 `!/?` 结尾，解析器按行匹配 `Missing character:` 正则失败，续行被丢弃，0 条缺字形条目。

* 修复后：解析器增加折行缓冲，攒到行尾 `!/?` 再合并（词内断行直接粘合，不在 `script` 里插空格）；hints 的 `Missing character` 正则允许码位后缀缺失，字体组允许跨行。命中 `missing_glyph`，字符 `中`，字体 `Latin Modern Roman`；不是 nullfont 连锁分支。

* 本 MiKTeX/xeCJK 版本只输出普通 `Missing character` 行，未出现 `CJKfamily ... does not contain glyph` 消息；`cjk_missing_glyph` 规则保留，覆盖其它发行版 / 版本的 CJKfamily 文本（既有 round4 测试维持不变）。

## B3c：真实 biber `.blg` 大小写不匹配

真实 `.blg` 两个 WARN（行首带 `[220] Biber.pm:132> ` 位置前缀）：



```
[220] Biber.pm:132> WARN - Possible typo (case mismatch) between citation and datasource keys: 'Key' and 'key' in file 'refs.bib'
[220] Biber.pm:132> WARN - I didn't find a database entry for 'Key' (section 0)
```



* 修复前：biber 解析器正则锚定 `^WARN -`，位置前缀未剥离，整份 `.blg` 解析出 0 条。

* 修复后：先剥离 `[<pid>] <file>:<line>> ` 前缀再匹配；两条分别命中：


  * `biber_case_mismatch`（键 `Key` vs `key`，文件 `refs.bib`）；

  * `log_hint`（biber 旧表 “I didn't find a database entry” 分支）。

* 在 tool=`biber` 下，第二条**不**被 `undefined_citation` / `undefined_reference` 抢答；整条 biber 日志无这两条规则。

## B3d：未定义 Citation / Reference 引号兼容

本机真实日志使用 LaTeX 传统反引号写法（已命中）：



```
53: LaTeX Warning: Citation `key' on page 1 undefined on input line 3.
56: LaTeX Warning: Reference `sec:intro' on page 1 undefined on input line 4.
```

正则同时兼容直单引号 `'key'` 与双引号 `"key"`（其它引擎 / 版本可能输出直引号）；测试用合成串覆盖 `Citation 'key'` → `undefined_citation`、`Reference "sec:intro"` → `undefined_reference`，本地化 “找不到 citation/reference” 兼容分支保留。解析器 `undefined_reference_re` 同步放宽引号字符集。



***

## L1：LuaLaTeX `Font not loadable` 完全无 hint

### 真实日志

`lualatex` + fontspec + `\setmainfont{NoSuchFontFamilyXYZ}`，第 193–194 行（`max_print_line` 把 `language` 折成 `lang` / `uage`）：



```
193: ! Font \TU/NoSuchFontFamilyXYZ(0)/m/n/10=name:NoSuchFontFamilyXYZ:mode=node;lang
194: uage=dflt;+tlig; at 10pt not loadable: metric data not found or bad.
```

另有第 98、136、157 行三个独立 `Package fontspec Error:` 块（与 B1 同口径，逐条保留、不去重）。

### 修复前后对比（同一条目，tool=`lualatex`）



| 项                   | 修复前                                                  | 修复后                                                                          |
| ------------------- | ---------------------------------------------------- | ---------------------------------------------------------------------------- |
| `hint_for_entry` 返回 | `None`（规则失配，无任何建议）                                   | `font_not_loadable`，kind `missing_font`                                      |
| 规格识别                | 旧正则只认 `\\[A-Za-z@]+=`，不认 `\TU/...(0)/m/n/10` NFSS 规格 | 规格段允许 `\TU/...`、`\OT1/...` 等 `\\[A-Za-z0-9@]+/...` 形式；名称与 `=` 之间容忍折行         |
| 原因识别                | 只认 `Metric (TFM) file ...`                           | 兼容 `metric data not found or bad`（及 `font file not found` 等价形态）              |
| 字族抽取                | 失配                                                   | 优先 `name:<family>:...`，其次 NFSS `\TU/<family>(0)/...` → `NoSuchFontFamilyXYZ` |
| 文案 / 命令             | 无                                                    | OpenType / 系统字体分支：\`fc-list : family                                         |

### 代码改动点



* `_FONT_NOT_LOADABLE_RE`：规格段放宽为 `\\[^\s=]+|[^\s=]+`；等号后描述组按行内 + 至多两行续行匹配（不使用跨全文的 `[\s\S]*?`，避免长畸形行回溯）；`loadable` 容忍折行。

* `_match_font_not_loadable`：先做 `"loadable"/"loada"` 快速短路，不含该片段的条目（缺字形、畸形 Font 行等）直接跳过；显式 `.tfm` 文件名仍拒绝命中，交给 `tfm_font_missing`。

* 新增 `_font_family_from_match()`：优先 `name:<family>:...`，其次 NFSS 规格段，最后回退等号后原文。

* `_build_font_not_loadable`：tool ∈ {xelatex, lualatex} 或 reason 含 `installed font`/`metric data`/`font file not found`/`not found or bad` 时走 OpenType 分支；lualatex 命令追加 `luaotfload-tool --update`。

### 回归断言（`test_real_miktex_round6.py`）



* 3 条 `Package fontspec Error` 均命中 `fontspec_font_not_found`；

* 1 条 `not loadable` 命中 `font_not_loadable`，文案含 `NoSuchFontFamilyXYZ`；无 `or.tfm`、无 `pdflatex`；命令含 `fc-list` 与 `luaotfload-tool`、不含 `tfm`；整条日志无 `tfm_font_missing`。

## L2：LuaLaTeX 缺字形真实格式与 nullfont 聚合决策

### 真实日志

`ctexart` + `\setCJKmainfont{Latin Modern Roman}`，lualatex；12 行 `Missing character`（4 个汉字 `中文测试` × 三遍编译），带 `(U+XXXX)` 码位，字体名被折行：



```
1179: Missing character: There is no 中 (U+4E2D) in font "name:Latin Modern Roman:mod
1180: ne=node;script=latn;language=dflt;jfm=zh_CN/{quanjiao}"!
1181: Missing character: There is no 文 (U+6587) in font "name:Latin Modern Roman:mod
...
```

### 聚合决策（含 nullfont）



* **沿用既有按&#x20;**`(文件, 字体)`**&#x20;桶聚合的口径**，与 B3b（XeLaTeX）一致，不另设 nullfont 特例：同一字体下重复的 `Missing character` 在 parse 结束时合并为一条可读警告；桶内按字符累计次数、保留各自码位。

* 聚合条目保留：代表字符、字体名、码位 `(U+4E2D)`、总次数与去重字形列表。本 fixture 聚合后条目文本：



```
Missing character: There is no 中 (U+4E2D) in font "name:Latin Modern Roman:mode=node;script=latn;language=dflt;jfm=zh_CN/{quanjiao}"! (12 occurrences, 4 distinct glyphs: 中, 文, 测, 试)
```



* **不改变既有&#x20;**`results`**&#x20;计数规则**：聚合只发生在 parser 展示条目层，底层 `LogEntry` 集合、JSON `results`、CSV 行数、SARIF 结果数的语义不变；没有为去噪私自改行数。nullfont 重复条目若出现，同样落 `(文件, nullfont)` 桶聚合，字符 / 字体名 / 码位不丢。

* 本轮两份真实 fixture（XeLaTeX B3b、LuaLaTeX L2）均未出现 `nullfont` 行；nullfont 分支按既有桶逻辑覆盖，未在真实日志中额外验证。

### hint 引擎分支与字体显示规范化（第二轮复核补丁）

修复前（tool=lualatex 时）存在引擎错配：文案首句是 “① 若还在 pdfLaTeX … 改用 XeLaTeX/LuaLaTeX”，命令给出 `xelatex <主文件>.tex`—— 日志已经来自 LuaLaTeX，再建议换 XeLaTeX 是误导；字体还把 fontspec 内部 spec 原样塞进建议：`"name:Latin Modern Roman:mode=node;script=latn;..."`，噪声过大。



* **按&#x20;**`tool_name`**&#x20;分支**（`_build_missing_glyph`）：


  * `xelatex` / `lualatex` / `tectonic`：已在 Unicode 引擎，直接进入 “当前 CJK 字体不含该字” 的第二步；命令只给 `\setCJKmainfont{<含该字的中文字体>}`（可按实际用 `\setCJKsansfont`），**不**出现引擎二进制、`xelatex <主文件>.tex` 换引擎命令，也不写 “若还在 pdfLaTeX” 前提；`\usepackage{ctex}` 不作为换引擎命令放入该分支。

  * `pdflatex` / 空 / 未知：保留既有两步排查与换引擎建议；编译命令写 `XeLaTeX/LuaLaTeX <主文件>.tex` 两个可选引擎，不写死单一 `xelatex`；`\usepackage{ctex}` 命令保留。

* **字体显示规范化**：`name:Latin Modern Roman:mode=node;...` 在建议文案中显示为 `Latin Modern Roman`（去 `name:` 前缀与 `:key=value`/`;...` 参数段）；原始 spec 完整保留在条目文本 /error\_pos 中，不丢信息；`(U+4E2D)` 与规范化字体名同时可见。英文 `text_en` 同口径。

### 代码改动点



* `_missing_char_detail_re`：字符与 `in font` 之间增加可选 `(U+<codepoint>)` 分组；字体组允许跨行折行。

* `_missing_characters` 桶结构改为 `dict[str, tuple[int, str | None]]`（字符 → (次数，码位)）；`_flush_missing_characters` 代表字符带码位标签 `中 (U+4E2D)`。

* `_normalize_font_spec()`：剥离 `name:` 前缀与参数段；`_build_missing_glyph` 增加 `tool_name` 参数并按引擎分支；规则分发把 `tool` 透传给 `missing_glyph` 构建器。

### 回归断言



* 至少 1 条 `missing_glyph`；字符 `中`、规范化字体 `Latin Modern Roman`；条目文本保留 `(U+4E2D)`；同一字体的 12 条重复缺字形聚合为 1 条。

* `tool_name="lualatex"`：commands 不含 `xelatex`/`lualatex`/`<主文件>`，文案不含 “若还在 pdfLaTeX”；`tool_name="xelatex"` 同样无硬编码换引擎命令；`tool_name="pdflatex"` 仍保留 `\usepackage{ctex}` 与 XeLaTeX/LuaLaTeX 换引擎建议。

## B1-bbl：首遍 pdflatex 的 `No file main.bbl.` 未入条目，`missing_bbl` 不触发

### 真实日志（biblatex + backend=biber，未跑 biber）



```
366: No file main.bbl.
370: LaTeX Warning: Citation 'key' on page 1 undefined on input line 5.
388: Package biblatex Warning: Please (re)run Biber on the file:
     (biblatex)                main
```

### 修复前后对比



| 项                      | 修复前                                       | 修复后                                                                                                                                             |
| ---------------------- | ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `No file main.bbl.` 条目 | 未进入条目集合（被吞）                               | parser 记为 WARNING，文本含 `No file main.bbl`，保留为可诊断条目                                                                                               |
| 规则命中                   | 只给 `undefined_citation`，`missing_bbl` 未命中 | `missing_bbl` 优先于 `undefined_citation`：`No file main.bbl.` 与 `Please (re)run Biber` 两条均归 `missing_bbl`；`undefined_citation` 作为独立条目保留但不抢答 bbl 条目 |
| 文案                     | 仅提示引用未定义                                  | 给出 `latex → biber <jobname> → latex`（按 backend 区分 biber/bibtex）流程，先确认声明的 backend 与实际命令一致                                                        |

### 代码改动点



* parser 新增 `no_file_bbl_re`（`^No file\s+([^\s.]+\.bbl)\.?$`），WARNING 分支入队；加入 `_ENTRY_START_PATTERNS`。

* `rerun_to_get_citations_re` 放宽匹配 `Please (re)run Biber on the file:` 变体，条目文本保留原始行（含 `(biblatex) main` 续行）。

* hints：`_MISSING_BBL_RE` 旁加 `_RERUN_BIBLATEX_RE`；规则表 `missing_bbl` 排在 `undefined_citation` 之前；`_build_missing_bbl` 用 `match.lastindex` 防无分组正则 `group(1)` 越界，无 job 时 opening 用 “文献后端还没有成功跑过：”。

### 回归断言



* 首遍日志：`No file main.bbl` 条目命中 `missing_bbl`；`Please (re)run Biber` 条目命中 `missing_bbl`；`undefined_citation` 仍在规则集合中但不抢答。

* 跑完 biber 并收敛后的完成态日志：无 `missing_bbl`、无 `Citation ... undefined`。

## B2：biber 完整链路端到端回归

真实编译链路：首遍 pdflatex → `biber main` → 第二 / 三遍 pdflatex，全部 exit 0，`main.bbl` 生成（1583 字节）。三段产物分别落 fixture：



| 阶段           | fixture                          | 规则与作用域断言                                                                                       |
| ------------ | -------------------------------- | ---------------------------------------------------------------------------------------------- |
| 首遍 `.log`    | `pdflatex_biber_chain_pass1.log` | `missing_bbl` 命中、`undefined_citation` 命中（优先级正确：bbl 条目先归 `missing_bbl`）                         |
| biber `.blg` | `biber_chain.blg`                | 本场景键名匹配、无 WARN（0 条目，INFO only）；tool=`biber` 下不出现 `undefined_citation`/`undefined_reference` 抢答 |
| 完成态 `.log`   | `pdflatex_biber_chain_final.log` | 无 `missing_bbl`、无 `Citation ... undefined`                                                     |



* 工具作用域：biber `.blg` 的 “未找到数据库条目” 类消息归 biber 自身规则 /`log_hint`，不被 latex 的 `undefined_citation`/`undefined_reference` 抢答（与 B3c 同口径）。

* 状态转换断言：首遍（缺 bbl + 未定义引用）→ biber（INFO 收尾）→ 完成态（两类警告均消失）。

* 边界：本 `.blg` 无 WARN，未覆盖 biber 告警在链路中间态的断言；B3c fixture 单独覆盖 `biber_case_mismatch`。



***

## 改动文件（绝对路径）



* `D:\Document YM\Desktop Document\Tools_Development\PyTeXLogs\src\pytexlogs\hints.py`

* `D:\Document YM\Desktop Document\Tools_Development\PyTeXLogs\src\pytexlogs\parsers\latex.py`

* `D:\Document YM\Desktop Document\Tools_Development\PyTeXLogs\src\pytexlogs\parsers\biber.py`

* `D:\Document YM\Desktop Document\Tools_Development\PyTeXLogs\tests\test_real_miktex_round6.py`（新建，19 条用例：第一轮 10 条 + 第二轮 7 条 + 引擎分支补丁 2 条）

* `D:\Document YM\Desktop Document\Tools_Development\PyTeXLogs\tests\fixtures\real_miktex\`（新建目录，12 份真实日志 fixture）

* `D:\Document YM\Desktop Document\Tools_Development\PyTeXLogs\docs\hints-research\round6-real-miktex.md`（本文档）

第二轮新增 fixture：`lualatex_fontspec_not_found.log`、`lualatex_xecjk_missing_glyph.log`、`pdflatex_biblatex_before_biber.log`、`pdflatex_biber_chain_pass1.log`、`biber_chain.blg`、`pdflatex_biber_chain_final.log`。

未改：`src/pytexlogs/parsers/bibtex.py`、既有 `docs/hints-research/*.md`、CHANGELOG、README。

## 验证结果（实跑数字）



| 检查                                             | 第一轮收尾                 | 第二轮收尾（含引擎补丁）                                    |
| ---------------------------------------------- | --------------------- | ----------------------------------------------- |
| `pytest tests` 全量                              | 477 passed, 4 skipped | **486 passed, 4 skipped**（第二轮 7 条 + 引擎分支补丁 2 条） |
| `ruff check --config pyproject.toml src tests` | All checks passed     | **All checks passed**                           |
| `python -m compileall -q src/pytexlogs`        | 退出码 0                 | 退出码 0                                           |
| `CI_PERF=1 pytest tests/perf`                  | 4 passed（1.46s）       | **4 passed（1.50s）**，性能门禁未退化                     |
| `python -m pytexlogs.cli --version`            | —                     | `pytexlogs 0.6.1`                               |



* 4 个 skipped 全部为性能门禁用例（`CI_PERF=1` 才运行）：`tests/perf/test_100k_lines.py:41`、`tests/perf/test_hints_matcher.py:75/112/147`；无 “缺包 / 缺 TeX 环境” 类跳过。

* 本轮未触发缺包跳过：`ctex.sty`、`xeCJK.sty`、`fontspec.sty`、`biblatex.sty`、`luaotfload` 在本机 MiKTeX 26.5 Portable 中均已存在，L1/L2/B1-bbl/B2 均为真实编译。

* 第二轮放宽 `_FONT_NOT_LOADABLE_RE` 后曾出现两处性能回归（码位变体 2000 行样本 1.996s、畸形长 Font 行超时），已通过 “快速短路 + 行内 / 至多两行续行匹配” 收窄正则修复；既有 TFM 契约（`\foo=NoSuchFont` → `missing_font_tfm` + `kpsewhich nosuchfont.tfm`、显式 `.tfm` 样本归 `tfm_font_missing`）保持不变。

### 收口确认（本轮最终复核）



* **回归规模**：`pytest tests` = **486 passed, 4 skipped**；`tests/test_real_miktex_round6.py` = **19 passed**（第一轮 10 + 第二轮 7 + 引擎分支补丁 2）；`CI_PERF=1 pytest tests/perf` = 4 passed。

* **fixture 规模**：`tests/fixtures/real_miktex/` 共 **12 份**；第二轮新增 L1/L2/B1/B2 六份：`lualatex_fontspec_not_found.log`、`lualatex_xecjk_missing_glyph.log`、`pdflatex_biblatex_before_biber.log`、`pdflatex_biber_chain_pass1.log`、`biber_chain.blg`、`pdflatex_biber_chain_final.log`。

* `missing_bbl`**&#x20;状态转换**：首遍 `pdflatex_biblatex_before_biber.log` 命中 `No file main.bbl.` 与 `Please (re)run Biber on the file:`，`missing_bbl` ×2 且排在 `undefined_citation` 之前；biber 完成后 `pdflatex_biber_chain_final.log` 中 `missing_bbl` = 0、`undefined_citation` = 0。

* **LuaLaTeX&#x20;**`\TU/...`**&#x20;命中**：`lualatex_fontspec_not_found.log` 中 `Font \TU/NoSuchFontFamilyXYZ(0)/m/n/10=name:... at 10pt not loadable: metric data not found or bad.` 命中 `font_not_loadable`（kind `missing_font`），字族 `NoSuchFontFamilyXYZ`，同文件另有 3×`fontspec_font_not_found`；不命中 `tfm_font_missing`，无 `or.tfm`。

## 边界与未覆盖



* B3c 只采集 `.blg`，未跑第二遍 pdflatex 回填 `.bbl`；不影响 biber 规则证据。

* B2 链路只验证首遍 → biber → 完成态三段；第三遍之后的额外收敛检查未单独断言。

* L2 本机版本只输出普通 `Missing character` 行，无 `CJKfamily does not contain glyph` 行；`cjk_missing_glyph` 规则保留给其它发行版 / 版本。

* 两份真实缺字形 fixture 均未出现 `nullfont` 行；nullfont 重复条目按既有 `(文件, 字体)` 桶聚合逻辑覆盖，未在真实日志中额外验证。

* 展示层按字体族聚合（BI/B/I 降噪）本轮未实现：规则要求 view-only、不改变底层计数；如后续实现，需另加 “聚合视图不丢 shape、底层条目数不变” 的测试。

* fixture 日志含本机绝对安装路径（与既有 fixture 口径一致）；解析断言只依赖规则命中、键名与字体名，不依赖机器路径。