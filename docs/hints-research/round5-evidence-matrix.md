# 第 5 轮：证据矩阵与交付说明

## 结论摘要

- PyTeXLogs 的 `hints` 从 **23 条规则**扩展到 **41 条**：新增 18 条，另修改 9 条既有规则的匹配与文案；第 4 轮验证发现的 13 项缺陷中 F1–F11、F13 已修，F12 作为低优先观察项保留。
- 每条建议新增稳定 `rule_id`，JSON（`hints[].hint.rule_id`）与 SARIF（`properties["pytexlogs/hint"].rule_id`）均可追溯；CSV 表头、JSON `results` 形状、SARIF 必填字段未变。
- 最终回归：`433 passed, 1 skipped`；ruff `All checks passed`；`compileall` 退出码 0。
- 关键真实缺陷已修：XeLaTeX 缺字形正则失配、`Font ... not loadable` 误抽取、`input stack size` 错误归因、旧表 `Missing character` 残留 T1 fontenc 建议、`missing_font` 灾难性回溯（11.7s → 5ms 级）。
- 真实日志在 Linux + TeX Live 云主机临时目录采集（未安装任何包、未改任何 TeX 配置）。**环境前提更正**：当时误判 Windows 工作站“没有 TeX 可执行文件”；实测本机装有 MiKTeX 26.5 Portable，`pdflatex/xelatex/lualatex/biber/bibtex/latexmk` 均在 PATH；round6 已用本机 MiKTeX 真实日志复核，见 [`round6-real-miktex.md`](round6-real-miktex.md)。上述 Linux 采集口径是历史记录，不是代码回归结论。

## 五轮流程

| 轮次 | 执行者 | 输入 | 产出 | 结论 |
| --- | --- | --- | --- | --- |
| 1 现状与真实日志 | Organizer | 本机仓库、`hints.py`、真实编译 | `round1-real-logs.md`（31 个场景） | 确认 10 类缺陷 |
| 2 联网取证 | 3 个并行智能体 + Organizer | GitHub / TeXSE / 官方手册 | `round2-github.md`（53 URL）、`round2-official.md`（25 URL + 10 SE）、`round2-specialized.md`（32 URL）、`round2-texse-browser.md`（17 页） | 110+ 条可核验来源；4 份手册原文由主智能体直接抓取 |
| 3 规则设计与实现 | Organizer 定规格 + 1 个实现智能体 | 第 1/2 轮证据 | 41 条规则、`rule_id`、5 个测试文件、`hints-reference.md` | 376 passed |
| 4 独立对抗验证 | 1 个验证智能体 + 实现智能体修复 | 最终代码 | `round4-verify.md`（36 探针） | 发现 13 项问题；F1–F11、F13 已修，F12 明确保留 |
| 5 代码审查与交付 | 1 个审查智能体 + Organizer | 最终代码与文档 | `round5-review.md`、本文件 | 回归 433 passed |

## 证据矩阵（规则族 → 证据 → 测试）

| 规则 / 族 | 真实日志证据（round1） | 联网/手册证据 | 自动化测试 |
| --- | --- | --- | --- |
| `missing_package` | c03 `File 'nosuchpkgxyz.sty' not found` | GitHub `MiKTeX/miktex#127`、`collective/bibliograph.rendering#3`；round2-github 族 3 | precedence CORPUS |
| `missing_file` / `missing_graphic` / `missing_bib` | C03 相邻分支 | 同上 | precedence CORPUS |
| `font_not_loadable` | e03/d14 `Font \foo=... not loadable`；round6 第二轮 L1：lualatex `metric data not found or bad` + `\TU/` NFSS 规格命中（`round6-real-miktex.md` L1） | round2-official C3；SE 75166（TFM 链路） | `test_hints_real_logs.py`、`test_real_miktex_round6.py` L1 |
| `tfm_font_missing` | d14 `Metric (TFM) file not found` | SE 75166（159/125 采纳）：“the missing file is `ecrm1000.tfm`”；TUG 字体安装页 | `test_hints_real_logs.py`、`test_hints_round4.py` |
| `fontset_unavailable` | round6 本机 MiKTeX 实跑：`pdflatex_ctex_adobe_fontset.log`（288 条目）命中 `adobe`，无 `package_error`（`round6-real-miktex.md` B3a） | `ctex.pdf` 第 14 节：`CTeX fontset '`#1' is unavailable in current mode`（主智能体核实） | `test_hints_round4.py`（三种引号变体）、`test_hints_round5.py`（`xelatex <主文件>.tex` + `\usepackage[fontset=fandol]{ctex}` 命令）、`test_real_miktex_round6.py` B3a |
| `cjk_missing_glyph` | —（B3b 本机日志只出普通 `Missing character`，归 `missing_glyph`，未出现 `CJKfamily ... does not contain glyph` 消息） | `xeCJK.pdf` §5：`missing-glyph` 模板 + AutoFallBack（主智能体核实） | `test_hints_round4.py`（`(U+4E2D)` 与 `( U + 4E2D )`） |
| `missing_glyph` | e01/e02 XeLaTeX 缺字形（旧正则失配）；round6 第二轮 L2：lualatex 缺字形 12 条聚合 1 条，引擎分支错配已修（`round6-real-miktex.md` L2） | TeX FAQ `FAQ-misschar`；`xeCJK.pdf` FallBack | 真实日志回放 39/39、`test_real_miktex_round6.py` L2 |
| `unicode` | c10 `Unicode character 中 (U+4E2D)` | LaTeX News 30（ltnews30）；Overleaf 编码页；round2-official C1 | `test_hints_real_logs.py` |
| `missing_bbl` | c13 `No file main.bbl.`；round6 第二轮 B1-bbl/B2：`.bbl` 缺失入 WARNING、`missing_bbl` 优先于 `undefined_citation`，完整链路完成态 0 条 bbl/未定义引用（`round6-real-miktex.md` B1-bbl、B2） | `biblatex.pdf` §3.1.1/§3.8.1：`backend=biber`、`bibwarn`、`\addbibresource` 需带扩展名 | `test_hints_round4.py`、上下文替换测试、`test_real_miktex_round6.py` B1-bbl/B2 |
| `undefined_citation` | round6 本机 MiKTeX 实跑：`pdflatex_undefined_cite_ref.log` 命中 `Citation 'key'`（B3d） | SE 63852（192/246）：“biblatex … citation key in bold”；biber.tex 大小写敏感 | `test_hints_deep.py`、`test_hints_round4.py`、`test_real_miktex_round6.py` B3d |
| `biber_case_mismatch` | round6 本机 MiKTeX 实跑：`biber_case_mismatch.blg`（2 条目）命中 `Key` vs `key`（`refs.bib`）（B3c） | `biber.tex`：“Matching of citation keys and datasource entry keys is now case-sensitive”；`--validate-datamodel` | 工具作用域测试（biber 命中、latex 不命中）、`test_real_miktex_round6.py` B3c |
| `missing_bib` | — | bibtex(1) manpage 搜索路径；`biblatex.pdf` §3.8.1 扩展名规定；`MiKTeX#541` | `test_hints_round4.py` |
| `capacity` | c15 `[input stack size=5000]` | SE 24247（input stack 宏包链递归）、SE 7953（pgfplots 外置化）；round2-official 容量表 | `test_hints_real_logs.py` |
| `double_script` | c17 `! Double subscript.` | SE 253080（20/26 采纳，重音原子空组 `${{}\hat{a}_b}_c$`）、SE 38100 | `test_hints_real_logs.py` + 文案断言 |
| `option_clash` | c19 `Option clash for package graphicx` | SE 83101（176/198）；`kableExtra#274`；`latex2e#1589` | `test_hints_precedence.py` |
| `missing_begin_document` | c05 | SE 29463；`latex2e#727`、`latex2e#1673`；round2-official C9/C11 | `test_hints_real_logs.py` |
| `extra_close_brace` | e09/d06 `Too many }'s` | SE 27042；round2-texse-browser | `test_hints_real_logs.py` |
| `missing_right` | e11 `Missing \right. inserted` | round2-official 第 2 族；SE 未找到同题高票帖（已如实记录） | `test_hints_round4.py`（左右括号变体） |
| `bad_math_delimiter` | e06 `Display math should end with $$` + `Bad math environment delimiter` | Overleaf 显示数学页；round2-official 第 2 族 | `test_hints_real_logs.py` |
| `misplaced_noalign` / `illegal_unit` / `command_already_defined` / `no_line_to_end` / `hyperref_pdf_string` | e10 / d02 / d05 / d12 / e05 | 逐一对应 round1 第二批真实日志；`tabularray#400`、`beamer#360` 作旁证 | `test_hints_real_logs.py` |
| `fontspec_font_not_found` | c14 `The font "NoSuchFont" cannot be found` | fontspec 包页/README（S17）；`tectonic#157`、`tectonic#1265` | `test_hints_real_logs.py` |
| `runaway` | c06/c18 | `beamer#360`（`\@xverbatim`）；round2-official C6 | `test_hints_real_logs.py` |
| `math_mode` | c02 `Missing $ inserted`（`l.3` 折行） | SE 24132；Overleaf Missing `$` 页 | `test_hints_real_logs.py` |
| `no_output` | d09 空文档 `No pages of output` | `\includeonly` 官方语义（latexref.xyz）；round2-official C11 | `test_hints_real_logs.py` |
| `package_error` / `log_hint` | 旧表 | 既有实现 | precedence CORPUS |

## GitHub 重点来源（可核验）

| 仓库/编号 | 用途 | URL |
| --- | --- | --- |
| `MiKTeX/miktex#127` | 字体名→宏包名映射 | https://github.com/MiKTeX/miktex/issues/127 |
| `MiKTeX/miktex#541` | `couldn't open database file` 双扩展名 | https://github.com/MiKTeX/miktex/issues/541 |
| `latex3/latex2e#727` | `Missing \begin{document}` 内核级联 | https://github.com/latex3/latex2e/issues/727 |
| `latex3/latex2e#1673` | `numberwithin` 触发同一错误 | https://github.com/latex3/latex2e/issues/1673 |
| `latex3/latex2e#1589` | Option clash / `\ProcessKeyOptions` | https://github.com/latex3/latex2e/issues/1589 |
| `latex3/latex2e#1656` | LuaLaTeX 缺字形（U+25EF） | https://github.com/latex3/latex2e/issues/1656 |
| `haozhu233/kableExtra#274` | xcolor Option clash（Owner 回复） | https://github.com/haozhu233/kableExtra/issues/274 |
| `tectonic-typesetting/tectonic#1022` | 嵌套 itemize 触发 Missing `$` | https://github.com/tectonic-typesetting/tectonic/issues/1022 |
| `tectonic-typesetting/tectonic#157` | FontAwesome 字体找不到 | https://github.com/tectonic-typesetting/tectonic/issues/157 |
| `gpoore/pythontex#58` | TeX capacity 后续失败 | https://github.com/gpoore/pythontex/issues/58 |
| `TeXackers/tabularray#400` | longtblr + itemize → missing `\item` | https://github.com/TeXackers/tabularray/issues/400 |
| `josephwright/beamer#360` | `\@xverbatim` 扫描到文件尾 | https://github.com/josephwright/beamer/issues/360 |
| `testimonyproject/testimony#269` | `A bad cross reference` 条目顺序 | https://github.com/testimonyproject/testimony/issues/269 |
| `pybamm-team/PyBaMM#6043` | double superscript 端到端修复 | https://github.com/pybamm-team/PyBaMM/pull/6043 |

## 手册 / TeXSE 重点来源

- biber: https://raw.githubusercontent.com/plk/biber/dev/doc/biber.tex
- biblatex: https://mirrors.ctan.org/macros/latex/contrib/biblatex/doc/biblatex.pdf
- ctex: https://mirrors.ctan.org/language/chinese/ctex/ctex.pdf
- xeCJK: https://mirrors.ctan.org/macros/xetex/latex/xecjk/xeCJK.pdf （大写目录 `xeCJK` 实测 404，小写可用）
- TeXSE：253080、38100、63852、75166、83101、7953、24247、29463、24132、27042
  （完整清单与票数见 `round2-texse-browser.md`；浏览器只读访问，未登录/未投票）

## 环境前提与剩余边界（必须如实说明）

1. **环境前提更正（原误判）**：本轮曾判断“Windows 工作站无 TeX，`xelatex/pdflatex/lualatex/biber/bibtex/latexmk` 均不在 `PATH`、常见安装目录未命中”，该判断有误。实测本机装有 MiKTeX 26.5 Portable（bin：`C:\Applications\Scoop\apps\miktex\current\texmfs\install\miktex\bin\x64`），上述引擎均在 PATH；本轮编译未在用户机器上执行，未改 `PATH`、未动 MiKTeX 配置。
2. **真实日志来自另一台 Linux 云主机**（TeX Live 自带引擎，本轮原始记录）：31 个场景编译于临时目录，只读系统 TeX；未执行 `tlmgr install`。该环境缺包跳过：`biber`、`biblatex`、`siunitx` 未安装，相关消息只能靠 fixture/手册原文验证。（历史记录；round6 本机 MiKTeX 复核结果见 B3a–B3d、L1/L2/B1-bbl/B2-chain 与下条。）
3. 该 Linux 环境为 Python 3.12，PyTeXLogs 要求 3.15；因此编译与解析分机完成：云主机只产日志，Windows 3.15.2 上跑解析与测试（历史分工记录，保留）。
4. `xeCJK.pdf` 大写目录路径 `.../latex/xeCJK/xeCJK.pdf` 实测 404，规范小写路径可用（已在文献中记录）。

## 仍未覆盖的边界

- `\newcommand{dice}` 这类“命令名漏反斜杠”的 `undefined_control` 提取偏差（F12）：成因写进了 `missing_begin_document`，但 `undefined_control` 仍会报 `\newcommand`；低优先级，未修。
- `Underfull \vbox` 与 `LaTeX Warning: There were undefined references.` 汇总行：前者已补旧表键；后者本身无具体键，提示价值低，未单列规则。
- `No room for a new \dimen/\read/\write`、`Too many unprocessed floats` 的细分、非 BMP 字符/emoji、`nullfont` 连锁的更多形态：未专门取证。
- BOM 触发 `Missing \begin{document}` 的版本差异未实机验证；文案已把 BOM 放在末位假设。
- biber 手册未逐条解释所有 `WARN -` 消息（消息文本在 Perl 源码）；`Duplicate entry key` 逐字片段后由真实 biber `.blg` 日志定位（https://github.com/dealii/publication-list/issues/389 ，成员粘贴的 109 行同格式输出：`WARN - Duplicate entry key: '<key>' in file '<file>.bib', skipping ...`）。第 5 轮已把旧表死键 `` entry `.+?' has `` 换成该子串片段，`--noskipduplicates` 追加分支随之可达；二轮补强后匹配策略为**最长键优先、`WARN -` 兜底**（不依赖字典插入顺序），`Duplicate entry key`、`I didn't find a database entry` 稳定压过通用 `WARN -`；旧表兜底同受散文守卫。手册仍只证实“默认跳过重复键、`--noskipduplicates` 保留”的行为，未逐条释义 WARN；其余未逐条取证的 biber `WARN -` 消息仍落通用兜底桶。
- fontset 命令规格漂移（round5 L4）已修复：`fontset_unavailable` commands 补齐 `xelatex <主文件>.tex` 与 `\usepackage[fontset=fandol]{ctex}`，与 round3 R22 对齐。
- 导出层语言透传（round5 L5）仍未做：CSV hint 列恒中文，JSON/SARIF 载荷同时存 `text`/`text_en`，消费者可读 `text_en`；留待后续给导出器加可选 `language` 参数。
- fontspec 手册正文中“找不到字体”的逐字建议未读到（包页/README/在线文档已读）。
- 本机 MiKTeX 包状态（kpsewhich 实查）：`ctex.sty`、`xeCJK.sty`、`fontspec.sty`、`biblatex.sty`、`siunitx.sty` 均已安装。`biblatex` + biber 真实 `.blg` 已采（B3c，biber 2.22，大小写不匹配 `Key`/`key`）；`siunitx.sty` 虽已安装，但本轮未构造触发 `Package siunitx Error` 的探针文档，该规则仍无真实错误日志（未采，非缺包）。
- round6 第二轮补充：LuaLaTeX 缺字体/缺字形、biblatex 首遍缺 `.bbl` 与 biber 完整链路已在本机 MiKTeX 实跑；场景、条目数与修复前后对比见 `round6-real-miktex.md` L1/L2/B1-bbl/B2，本矩阵不复制大段。

## 复现方式

```powershell
cd "D:\Document YM\Desktop Document\Tools_Development\PyTeXLogs"
$env:PYTHONPATH="D:\Document YM\Desktop Document\Tools_Development\PyTeXLogs\src"  # 必须绝对路径
& "D:\Document YM\Desktop Document\Tools_Development\PyTeXMK\.venv\Scripts\python.exe" -m pytest -q tests
& "C:\Applications\Scoop\persist\uv\cache\archive-v0\5BGcLFrJKq9gc1UH\ruff-0.17.5.data\scripts\ruff.exe" check --config pyproject.toml src tests
& "D:\Document YM\Desktop Document\Tools_Development\PyTeXMK\.venv\Scripts\python.exe" -m pytexlogs.cli explain "! Double subscript."
```

> 注意：`PYTHONPATH=src`（相对）会让测试里的 CLI 子进程导入 venv 中的旧安装包，产生假失败；必须用绝对路径。

## 交付文件

| 文件 | 说明 |
| --- | --- |
| `src/pytexlogs/hints.py` | 41 条规则、`rule_id`、工具白名单、误报守卫 |
| `src/pytexlogs/parsers/latex.py` | 旧表 `Missing character` 文案、`Underfull \vbox` |
| `src/pytexlogs/exporters/json_exporter.py`、`sarif_exporter.py` | `rule_id` 追加导出 |
| `tests/test_hints_precedence.py` | 顺序快照、语料覆盖、优先级 |
| `tests/test_hints_real_logs.py` | 真实日志回放 |
| `tests/test_hints_false_positive.py` | 良性文本/工具作用域/上下文 |
| `tests/test_hints_round4.py` | F1–F11、F13 回归 |
| `tests/test_hints_round5.py` | H1/M1/M2/M3/L1/L2/L4/L6/L7/L8 回归 |
| `docs/hints-reference.md` | 用户向 41 条规则参考 |
| `docs/hints-research/round1`–`round5` | 五轮证据与审查 |
| `CHANGELOG.md`、`README.md`、`README.en.md` | 用户可感知变化 |
