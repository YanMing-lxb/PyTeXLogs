# 第 2 轮：GitHub / 官方文档联网取证（12 个错误族）

> 本轮切片范围：**只做联网取证与文档落盘**，未修改任何 `.py` 文件，未执行 git commit，
> 未安装 TeX 包，未改动 MiKTeX 本体或系统环境变量。
> 取证日期：2026-11-21（Asia/Shanghai）。
> 对照样本：[`round1-real-logs.md`](round1-real-logs.md) 的 c01–c19；现有规则见
> `src/pytexlogs/hints.py` 的 `_RULES` / `RULE_IDS`。

## 取证方法与可信度口径

- **A 组（HTML 页面直接打开）**：用页面正文与评论区核对日志片段、作者关联与修复建议。
- **B 组（GitHub Search API 响应读取）**：标题、编号、URL、日期来自 API 响应 JSON；
  正文为空或被截断的条目，**不摘录其日志片段**，只作存在性佐证。
- 可信度：
  - **高**：仓库 Owner / Member / Collaborator / 官方维护者在 issue 中回复、确认或提交修复。
  - **中**：用户自述经验、开放 issue 无维护者结论，或 API 列表条目。
  - **文档**：Overleaf Learn 等官方参考文档。
- 发行版相关性标签：`通用`（与发行版/引擎无关）、`TL`（TeX Live 专属）、`MiKTeX` 专属、
  `tectonic` 专属、`引擎相关`（pdflatex / xelatex / lualatex 行为不同）。
- 日期口径：仅记录本次打开页面时可见的 `created_at` 或页面标注日期；不可见记 `—`，不补猜。

## 来源清单

### 族 1：`! Undefined control sequence.`

| 错误族 | 仓库#编号 | 标题 | URL | 日期 | 可信度 / 发行版相关性 |
| --- | --- | --- | --- | --- | --- |
| UCS | latex3/latex2e#56 | `\colaction` raises error when `multicol` is not called | https://github.com/latex3/latex2e/issues/56 | 2018-07-08 | 高（Member FrankMittelbach 评论并指派）；通用 |
| UCS | tectonic-typesetting/tectonic#1096 | Undefined control sequence `\DeclareUnicodeCharacter`（#800 重开） | https://github.com/tectonic-typesetting/tectonic/issues/1096 | — | 中（Contributor ratmice）；引擎相关 |
| UCS | tectonic-typesetting/tectonic#873 | Error message improvements: undefined control sequence vs undefined macro | https://github.com/tectonic-typesetting/tectonic/issues/873 | — | 中；通用 |
| UCS | tectonic-typesetting/tectonic#969 | Undefined control sequence on `\dots` with complex subscripts | https://github.com/tectonic-typesetting/tectonic/issues/969 | — | 中；通用 |
| UCS | Overleaf Learn | Undefined control sequence（官方错误文档） | https://www.overleaf.com/learn/latex/Errors/Undefined_control_sequence | — | 文档；通用 |

### 族 2：`! Missing $ inserted.` / 数学模式不匹配

| 错误族 | 仓库#编号 | 标题 | URL | 日期 | 可信度 / 发行版相关性 |
| --- | --- | --- | --- | --- | --- |
| Missing $ | tectonic-typesetting/tectonic#1022 | Nested itemize（报 Missing $ inserted） | https://github.com/tectonic-typesetting/tectonic/issues/1022 | 2023-04-13 | 高（维护者 kpym 评论）；工具相关 |
| Missing $ | phipsgabler/guitarsongbook#2 | "Missing $ inserted" error when a verse begins with `^` | https://github.com/phipsgabler/guitarsongbook/issues/2 | 2020-05-19 | 中（Owner 自述空组 workaround）；通用 |
| Missing $ | MLopez-Ibanez/revision#7 | Strikeout paragraphs containing an equation（Missing $ 为级联错误） | https://github.com/MLopez-Ibanez/revision/issues/7 | 2024-04-02 | 中；通用 |
| Missing $ | CTeX-org/ctex-kit#1117 | xeCJK：数学下标中未分组 `\textit` 触发 `Missing { inserted` | https://github.com/CTeX-org/ctex-kit/issues/1117 | — | 中；引擎相关 |
| Missing $ | Overleaf Learn | Missing $ inserted（官方错误文档） | https://www.overleaf.com/learn/latex/Errors/Missing_%24_inserted | — | 文档；通用 |

### 族 3：`! LaTeX Error: File `xxx.sty' not found.` 与宏包安装/发行版差异

| 错误族 | 仓库#编号 | 标题 | URL | 日期 | 可信度 / 发行版相关性 |
| --- | --- | --- | --- | --- | --- |
| 缺宏包 | tectonic-typesetting/tectonic#1276 | pythontex.sty not found | https://github.com/tectonic-typesetting/tectonic/issues/1276 | 2025-06-09 | 中；tectonic 专属 |
| 缺宏包 | collective/bibliograph.rendering#3 | texnames.sty not found（Fedora 分发包定位） | https://github.com/collective/bibliograph.rendering/issues/3 | 2016-02-11 | 中（作者定位到 `texlive-beebe`）；发行版相关 |
| 缺宏包 | yanyan-cas/IEEEACCESS2018#1 | spotcolor.sty / fltpage.sty not found（MacTeX） | https://github.com/yanyan-cas/IEEEACCESS2018/issues/1 | 2018-04-01 | 中；发行版相关 |
| 缺宏包 | ARENA-education/arena-slides#4（PR） | 最小 TeX Live CI 仅安装清单内宏包 | https://github.com/ARENA-education/arena-slides/pull/4 | — | 中；TL / CI 相关 |
| 缺宏包 | MiKTeX/miktex#127 | 字体名 → 宏包名映射（inconsolata / libertine / tex-gyre） | https://github.com/MiKTeX/miktex/issues/127 | — | 中；MiKTeX 专属 |

### 族 4：`! LaTeX Error: Missing \begin{document}.`

| 错误族 | 仓库#编号 | 标题 | URL | 日期 | 可信度 / 发行版相关性 |
| --- | --- | --- | --- | --- | --- |
| Missing begin | latex3/latex2e#727 | amsmath `\Umathaccent` 触发 Missing \begin{document} | https://github.com/latex3/latex2e/issues/727 | — | 高（Member davidcarlisle 参与排查）；通用 |
| Missing begin | latex3/latex2e#1673 | `numberwithin` 触发 Missing \begin{document} | https://github.com/latex3/latex2e/issues/1673 | — | 高（Member FrankMittelbach 确认内核 bug）；通用 |

### 族 5：`! LaTeX Error: Option clash for package xxx.`

| 错误族 | 仓库#编号 | 标题 | URL | 日期 | 可信度 / 发行版相关性 |
| --- | --- | --- | --- | --- | --- |
| Option clash | haozhu233/kableExtra#274 | Option clash for package xcolor | https://github.com/haozhu233/kableExtra/issues/274 | 2018-09-24 | 高（Owner haozhu233 回复）；通用 |
| Option clash | latex3/latex2e#1589 | Local options cannot be checked using `\ProcessKeyOptions` | https://github.com/latex3/latex2e/issues/1589 | 2024-12-21 | 高（Contributor muzimuzhi + Member FrankMittelbach，works as designed）；内核版本相关 |
| Option clash | Adhumunt/NotesTeX#6 | Option clash for package xcolor. | https://github.com/Adhumunt/NotesTeX/issues/6 | 2025-02-09 | 中；通用 |
| Option clash | Journal-of-Zhejiang-University-Science/FITEE#3 | Option clash for package graphicx. | https://github.com/Journal-of-Zhejiang-University-Science/FITEE/issues/3 | 2023-04-09 | 中（正文为空）；通用 |
| Option clash | Benjamin-Loison/Curriculum-vitae#21 | hyperref 选项冲突 | https://github.com/Benjamin-Loison/Curriculum-vitae/issues/21 | — | 中（正文为空）；通用 |
| Option clash | jmablog/simple-presentations-generator#1 | tcolorbox/hyperref 冲突 | https://github.com/jmablog/simple-presentations-generator/issues/1 | — | 中；通用 |

### 族 6：`! Double subscript.` / 上下标错误

| 错误族 | 仓库#编号 | 标题 | URL | 日期 | 可信度 / 发行版相关性 |
| --- | --- | --- | --- | --- | --- |
| 上下标 | maix00/FactorTester#55 | ShiftOp LaTeX double subscript when leaf emits `_t` | https://github.com/maix00/FactorTester/issues/55 | 2026-05-22 | 中（Owner 闭环修复）；通用 |
| 上下标 | pybamm-team/PyBaMM#6043（PR） | Fix double superscript in latexify for boundary values of powers | https://github.com/pybamm-team/PyBaMM/pull/6043 | 2026-11-13 前后 | 高（Member BradyPlanden 14 组配置端到端审查）；通用 |

### 族 7：`! TeX capacity exceeded, sorry [input stack size=...]`

| 错误族 | 仓库#编号 | 标题 | URL | 日期 | 可信度 / 发行版相关性 |
| --- | --- | --- | --- | --- | --- |
| 容量超限 | gusbrs/zref-vario#8 | input stack size 递归（`\extrasenglish -> \extrasenglish ...`） | https://github.com/gusbrs/zref-vario/issues/8 | — | 中（开放 issue，无维护者结论）；引擎相关 |
| 容量超限 | gpoore/pythontex#58 | After TeX capacity exceeded PythonTeX fails | https://github.com/gpoore/pythontex/issues/58 | 2015-02-27 | 高（Owner gpoore）；通用 |
| 容量超限 | flash-tex/flashtex#2265 | 容量超限各子类型区分（grouping/stack/nest/memory） | https://github.com/flash-tex/flashtex/issues/2265 | — | 中；通用 |

### 族 8：`! LaTeX Error: Something's wrong--perhaps a missing \item.`

| 错误族 | 仓库#编号 | 标题 | URL | 日期 | 可信度 / 发行版相关性 |
| --- | --- | --- | --- | --- | --- |
| 缺 \item | hust-latex/hustthesis#42 | Something's wrong--perhaps a missing \item. `\begin{publications}` | https://github.com/hust-latex/hustthesis/issues/42 | 2021-01-17 | 中；通用 |
| 缺 \item | TeXackers/tabularray#400 | longtblr + itemize 触发 missing \item（`measure=vbox`） | https://github.com/TeXackers/tabularray/issues/400 | — | 高（Collaborator lvjr + Contributor muzimuzhi）；通用 |
| 缺 \item | latex-ninja/hipster-cv#1 | tl2019 下 missing \item 个案 | https://github.com/latex-ninja/hipster-cv/issues/1 | — | 中；发行版相关 |
| 缺 \item | nguyenvulong/QA#57 | missing \item 报告 | https://github.com/nguyenvulong/QA/issues/57 | — | 中；通用 |

### 族 9：`! File ended while scanning use of \xxx.` / `Runaway argument?`

| 错误族 | 仓库#编号 | 标题 | URL | 日期 | 可信度 / 发行版相关性 |
| --- | --- | --- | --- | --- | --- |
| 未闭合参数 | latexstudio/LaTeXFAQ-cn#46 | File ended while scanning use of `\@xdblarg`（全角括号） | https://github.com/latexstudio/LaTeXFAQ-cn/issues/46 | 2018-10-13 | 中（中文社区 FAQ 标注“错误排查”）；通用 |
| 未闭合参数 | josephwright/beamer#360 | File ended scanning `\@xverbatim`（verbatim 含 `\end{frame}`） | https://github.com/josephwright/beamer/issues/360 | — | 高（Owner josephwright）；通用 |
| 未闭合参数 | phulin/umber#1523 | File ended scanning `\__siunitx_tmp:w`（跨引擎 parity） | https://github.com/phulin/umber/issues/1523 | — | 中；引擎相关 |

### 族 10：fontspec 找不到字体 / `Missing character`

| 错误族 | 仓库#编号 | 标题 | URL | 日期 | 可信度 / 发行版相关性 |
| --- | --- | --- | --- | --- | --- |
| 字体 | tectonic-typesetting/tectonic#157 | FontAwesome font-not-found | https://github.com/tectonic-typesetting/tectonic/issues/157 | — | 高（Collaborator pkgw）；引擎/发行版相关 |
| 字体 | tectonic-typesetting/tectonic#1265 | The font "libertinusmath-regular" cannot be found | https://github.com/tectonic-typesetting/tectonic/issues/1265 | 2025-03-05 | 中（Contributor thangleiter）；tectonic 专属 |
| 字体 | latex3/latex2e#1656 | `\textbigcircle` 在 LuaLaTeX 下缺字形（Missing character U+25EF） | https://github.com/latex3/latex2e/issues/1656 | 2025-02-10（评论日期） | 高（Member FrankMittelbach + Author randolf-scholz）；引擎相关 |
| 字体 | tectonic-typesetting/tectonic#372 | fontspec font-not-found | https://github.com/tectonic-typesetting/tectonic/issues/372 | — | 中；tectonic 专属 |

### 族 11：Unicode character ... (U+....) not set up for use with LaTeX（含 CJK）

| 错误族 | 仓库#编号 | 标题 | URL | 日期 | 可信度 / 发行版相关性 |
| --- | --- | --- | --- | --- | --- |
| Unicode | overleaf/overleaf#511 | 中 (U+4E2D) inputenc error | https://github.com/overleaf/overleaf/issues/511 | — | 中（无维护者结论）；引擎相关 |
| Unicode | gobborg/TLC-Resume-2021#2（PR） | author 字段中文；`\CJK{UTF8}{min}` workaround | https://github.com/gobborg/TLC-Resume-2021/pull/2 | 2022-04-11 | 中；引擎相关（pdflatex 时代 CJK 包） |
| Unicode | certik/fortran90.org#51 | ≤ (U+2264) not set up（Sphinx latexpdf） | https://github.com/certik/fortran90.org/issues/51 | 2023-08-14 | 中；引擎相关 |
| Unicode | swimmingbrain/texbrain#28 | UTF-8 characters crashing compiler（φ U+03C6） | https://github.com/swimmingbrain/texbrain/issues/28 | 2026-11-20 | 中；编码/引擎相关 |
| Unicode | morrisonkuhlsen/mksigma#43 | 生成器侧 Unicode 映射缺失 | https://github.com/morrisonkuhlsen/mksigma/issues/43 | — | 中；通用 |
| Unicode | QuantEcon/action-translation#181 | CJK usetex 构建中断 | https://github.com/QuantEcon/action-translation/issues/181 | — | 中；引擎相关 |
| Unicode | fedefelds/Formato-Paper-UNTREF#16 | 组合附加符触发 Unicode 错误 | https://github.com/fedefelds/Formato-Paper-UNTREF/issues/16 | — | 中（正文为空）；引擎相关 |

### 族 12：BibTeX / Biber 数据库错误

| 错误族 | 仓库#编号 | 标题 | URL | 日期 | 可信度 / 发行版相关性 |
| --- | --- | --- | --- | --- | --- |
| 文献库 | MiKTeX/miktex#541 | couldn't open database file；双 `.bib` 扩展名 | https://github.com/MiKTeX/miktex/issues/541 | — | 高（Member edocevoli，提交 strip double extension 修复）；MiKTeX 专属 |
| 文献库 | topepo/APM_Exercises#4 | couldn't open database file Ch_03_Ex_Sol.bib | https://github.com/topepo/APM_Exercises/issues/4 | 2017-02-17 | 高（Owner topepo，补提交 .bib 后关闭）；通用 |
| 文献库 | testimonyproject/testimony#269 | A bad cross reference——`.bib` 条目顺序 | https://github.com/testimonyproject/testimony/issues/269 | 2026-11-16 | 高（Collaborator deanberris，#271 关闭）；BibTeX 专属 |
| 文献库 | cr-marcstevens/dblpbibtex#13 | BibTeX crossref / 条目维护 | https://github.com/cr-marcstevens/dblpbibtex/issues/13 | — | 中；BibTeX 专属 |
| 文献库 | cryptobib/db#21 | 参考文献条目维护 | https://github.com/cryptobib/db/issues/21 | — | 中；通用 |
| 文献库 | tectonic-typesetting/tectonic#1226 | biblatex/biber 工作流问题 | https://github.com/tectonic-typesetting/tectonic/issues/1226 | — | 中；工具链相关 |

### 附：解析器侧观察（误报对照）

| 错误族 | 仓库#编号 | 标题 | URL | 日期 | 可信度 |
| --- | --- | --- | --- | --- | --- |
| 解析误报 | latex-lsp/texlab#828 | 解析器对 `}` 类消息的误判讨论 | https://github.com/latex-lsp/texlab/issues/828 | — | 中 |

---

## 按错误族的可执行修法

> 每条结构：**日志特征 → 根因（证据编号）→ 可执行步骤 → 常见误诊**。
> 证据编号对应上方“来源清单”的仓库#编号。

### 1. `! Undefined control sequence.`（现有规则 `undefined_control`）

**日志特征**

- 首行 `! Undefined control sequence.`；随后 `l.N <上下文>`，未定义命令名出现在
  `<recently read>` 标记后或行尾。
- 命令名可能是内部宏（含 `@`，如 `\mc@set@col@status`、`\@xdblarg`、`\__siunitx_tmp:w`）。

**根因**

1. 命令拼写错误（Overleaf 官方文档：`\Zlpha` 类笔误）。
2. 忘记加载提供该命令的宏包（Overleaf 官方文档：`\xspace` 需 `\usepackage{xspace}`）。
3. 正文误用反斜杠（Overleaf 官方文档：路径 `C:\Users` 被解析为 `\Users` 命令）。
4. 引擎/发行版不支持该命令：tectonic 基于 xelatex，inputenc 被忽略，
   `\DeclareUnicodeCharacter` 报未定义（tectonic#1096）。
5. 宏包内部宏在错误上下文被调用：latex2e#56 中 `\docolaction` 仅应在 multicol 环境内调用，
   Member 建议用 `\ifnum \doublecol@number>\z@` 做守卫。

**可执行步骤**

1. 读取 `l.N` 行与报错命令名；先在该行核对拼写。
2. 命令名含 `@` 或下划线/双下划线内部宏 → 优先向上找**第一条**用户可见错误；
   本条多为级联，不要直接让用户改内部宏。
3. 外部命令（`\xspace`、`\SI`、`\ce`、`\SIrange` 等）→ 在导言区补对应宏包；
   包名以 CTAN 上该命令所属宏包为准，**不要把命令名当包名**。
4. 路径/URL 中的反斜杠 → 改用 `\url{...}` 或正文 `\backslash`。
5. 引擎相关命令（inputenc 系列、`\DeclareUnicodeCharacter` 出现在 xelatex/lualatex 日志）
   → 给 `\newunicodechar` 或对应引擎方案，不要建议装包。

**常见误诊**

- 把内部宏报错当成用户拼写错误，提示“检查命令拼写”。
- 在 `.aux` 残留触发的二次报错上反复改源码，未清理中间文件重跑。
- 引擎不兼容被误判为宏包缺失。

### 2. `! Missing $ inserted.`（现有规则 `math_mode`）

**日志特征**

`! Missing $ inserted.` + `<inserted text> $` + `l.N`；常在 `^`、`_`、希腊字母、
数学重音命令出现在正文时触发。

**根因**

1. 数学命令/字符在数学模式外使用（Overleaf 官方文档：`\alpha`、`\vec`、`\tilde`、`\hat`、
   `^`、`_`）。
2. 正文中文件名含 `_`（Overleaf 官方文档：应写 `\_`）。
3. 级联错误：先出现 `Extra }, or forgotten \endgroup`（ulem/soul 包裹公式失败），
   后续才报 Missing $（MLopez-Ibanez/revision#7）。
4. 环境活动字符：verse 行首 `^` 被当上下标（guitarsongbook#2，空组 `{}` 前置规避）。
5. 工具停继续行为不同：同一 MWE latexmk 继续编译，tectonic 直接 halt（tectonic#1022）；
   维护者 kpym 指出问题不在展示片段，需查用户自己的 LaTeX 代码。

**可执行步骤**

1. 定位 `l.N`；检查该行 `^ _ \alpha \beta \vec \tilde \hat` 等是否在
   `$...$` / `\(...\)` / `\[...\]` 内。
2. 正文语境下的 `_` 改写为 `\_`。
3. **向上回溯**第一条括号/分组错误（`Extra }`、`Missing }`），先修首错。
4. 特殊环境（verse/诗歌、代码清单）行首活动字符：用空组前置或转义。
5. 多工具复现：先在同一引擎下最小化，再判断是代码问题还是工具停继续策略差异。

**常见误诊**

- 只改报错所在行，忽略上方首个分组错误。
- 把级联 Missing $ 当数学模式根因。
- 建议“给整段加 `$...$`”而不核对是否已有未闭合的数学模式。

### 3. ``! LaTeX Error: File `xxx.sty' not found.``（现有规则 `missing_package`）

**日志特征**

- ``! LaTeX Error: File `xxx.sty' not found.``，常后跟 `Type X to quit or <RETURN> to proceed`。
- 旧版/被 `\input` 触发时可能是 `! I can't find file `xxx.sty'.`（collective#3）。

**根因**

1. 当前发行版未收录或未安装该宏包：Fedora 把 `texnames.sty` 放在 `texlive-beebe` 而不是
   `texlive-collection-latexextra`（collective#3）；最小化 CI 需把宏包列入安装清单
   （arena-slides#4 PR）。
2. 引擎打包侧缺失：tectonic bundle 未带 `pythontex.sty`（tectonic#1276）；
   tectonic 默认不读取系统字体/目录（tectonic#1265 关联 #1238）。
3. 上游模板仓库本身漏提交文件（yanyan-cas/IEEEACCESS2018#1 类）。
4. 字体名与宏包名不一致：MiKTeX#127 给出映射——`Inconsolatazi4` → 包 `inconsolata`，
   `LinuxLibertineO` → 包 `libertine`，`TeXGyreTermes` → 包 `tex-gyre` / `tex-gyre-math`。

**可执行步骤（发行版相关，必须标注）**

1. 先判断 `.sty` 是项目内文件还是发行版宏包：项目内缺失 → 检查仓库是否漏提交，
   不要直接建议装包（topepo#4 同型问题是仓库缺 `.bib`）。
2. TeX Live：`tlmgr install <pkg>`；包名 ≠ 文件名，先在 CTAN 查该 `.sty` 所属宏包。
3. MiKTeX：开启自动安装时编译即装；手动命令为 `miktex packages install <pkg>`
   （旧版文档/历史 issue 用 `mpm --install=<pkg>`，见 MiKTeX#127，注意版本漂移）。
4. tectonic：`tectonic -X bundle search "<name>"` 查 bundle 内可用项；系统目录中的
   包/字体默认不参与查找。
5. 系统包管理器发行版（Fedora/Ubuntu/Debian）：按发行版包名安装，包划分与 TL collection
   不完全对应（collective#3）。

**常见误诊**

- 把 `.sty` 文件名直接当宏包名去安装。
- 在 tectonic 上建议 `tlmgr install`；在 MiKTeX 上建议 TeX Live 命令。
- 上游模板缺文件被当成本机发行版问题。

### 4. `! LaTeX Error: Missing \begin{document}.`（round1 c05：现有规则表未单列）

**日志特征**

`! LaTeX Error: Missing \begin{document}.`；用户侧常见场景为导言区后混入正文、文件 BOM、
`\includeonly` 误写。本轮打开的两例 GitHub 报告均为**宏包/内核内部触发的次级错误**。

**根因**

1. 内核/宏包内部宏笔误吞参数：latex2e#1673 中 `numberwithin` 内部
   `\@nocnterr{#3}` 把后续内容误当参数，Member FrankMittelbach 确认为内核 bug。
2. 包内部命令在错误模式下使用：latex2e#727，amsmath `\Umathaccent` 相关，
   Member davidcarlisle 参与排查。
3. 用户侧：`\begin{document}` 之前出现正文/标点；文件带 BOM 或非 UTF-8 编码
   （round1 c05 场景；本轮未检索到对应 GitHub 原始报告，见末节）。

**可执行步骤**

1. 先看报错前是否已有另一条内核/宏包错误；若命令名是内部宏，本条按级联处理。
2. 检查 `\begin{document}` 之前是否混入正文、孤立标点或注释未闭合。
3. 检查文件编码与 BOM；用编辑器另存为 UTF-8（无 BOM 视模板要求而定）。
4. 内部宏触发：升级宏包/内核版本，或回退到报告可复现的旧版本；不要在正文里找
   “不存在的 `\begin{document}`”。

**常见误诊**

- 把内部宏次级报错一律提示“正文写在了 `\begin{document}` 之前”。
- 与 round1 c05 的用户正文提前场景混用同一套文案；hint 需区分“内部宏级联”与“导言区正文”。

### 5. `! LaTeX Error: Option clash for package xxx.`（round1 c19：现有规则表未单列）

**日志特征**

`! LaTeX Error: Option clash for package xxx.`；冲突包常被另一包（tikz/pgfplots/beamer/
eso-pic/kableExtra/tcolorbox/hyperref 等）以无选项或不同选项预先加载。

**根因**

1. 同一包被两次以不同选项加载；预加载来自其它包内部（kableExtra#274 Owner 回复：
   先关闭生成器自动装包，再手动带选项加载；NotesTeX#6 日志先有无定义颜色警告，再报 clash）。
2. 2024-11-01 LaTeX2e 起，类选项默认不再自动传给包；新机制需 `.pass-to-packages`
   （latex2e#1589，Contributor muzimuzhi 给出键属性写法，Member FrankMittelbach 标注
   works as designed；参考 `texdoc clsguide` 4.4、`texdoc ltnews40` 章节）。

**可执行步骤**

1. 在导言区最前用 `\PassOptionsToPackage{<opts>}{<pkg>}`，或直接
   `\usepackage[<opts>]{<pkg>}`，抢在内部预加载之前。
2. 文档类可接收的选项（如 beamer 的 `xcolor={...}`）走类选项，不要二次 `\usepackage`。
3. 生成器/模板（R Markdown、kableExtra 类）：先关闭其自动装包开关，再手动加载对应宏包
   （kableExtra#274：`options(kableExtra.latex.load_packages = FALSE)`）。
4. LaTeX2e 2024-11 之后：类 → 包的选项传递需显式 `.pass-to-packages`，旧教程修法失效。

**常见误诊**

- 反复 `\usepackage` 同一包叠加选项，clash 依旧。
- 建议“删掉冲突包”而不是调整加载顺序/选项传递。
- 把新版内核的刻意行为变化当成 bug。

### 6. `! Double subscript.` / `! Double superscript.`（round1 c17：现有规则表未单列）

**日志特征**

`! Double subscript.` 或 `! Double superscript.`；形如 `x_1_2`、
`\epsilon^{b}^{right}`、`\tilde{O}_t_{t-N}`。注意 MathJax 文案为
“Double subscripts”，与 TeX 引擎文本不同。

**根因**

连续两个下标/上标未用花括号分组（FactorTester#55：叶节点发 `_t`，ShiftOp 再 append
`_{t-N}`；PyBaMM#6043：子表达式已有上标时，需把孩子包成组 `{\epsilon^{b}}^{side}`；
Member 审查同时记录同族遗留 double subscript 在 `prettify_print_name`）。

**可执行步骤**

1. 已有上下标的子表达式整体加花括号：`{\epsilon^{b}}^{\mathrm{right}}`。
2. 语义可合并时合并为 `x_{12}`，不要简单删一个下标。
3. 代码生成 LaTeX 的场景：输出前检查字符串中是否已有 `_`/`^`，再决定是否补分组括号
   （PyBaMM#6043 的判定方式）。

**常见误诊**

- 建议“删掉一个下标/上标”而不保留原语义。
- 规则只匹配 `Double subscript`，漏掉 `Double superscript`；反之亦然。
- 把 MathJax 的 “Double subscripts” 文案与 TeX 引擎文案混为一条匹配。

### 7. `! TeX capacity exceeded, sorry [input stack size=...]`（现有规则 `capacity`）

**日志特征**

`! TeX capacity exceeded, sorry [<pool>=<n>].`；方括号内子类型包括
`input stack size`、`main memory`、`grouping levels`、`save stack size`、
`param stack size`、`nest_size`、`buf_size` 等（flash-tex#2265 区分各子类型）。

**根因**

1. 宏递归展开：zref-vario#8 日志可见
   `\extrasenglish -> \extrasenglish ...` 栈自展开，`input stack size=10000`；
   同一 MWE 在 lualatex/book 可用、pdflatex/scrbook 失败；issue 开放，无维护者结论。
2. 单次返回内容块过长：pythontex#58，Owner gpoore 说明 Python 返回代码块过长导致超限；
   恢复手段是清理 pythontex 临时目录（`pythontex-files-<jobname>`）或用 `debug` 选项，
   而非先抬 TeX 内存。

**可执行步骤**

1. 先读方括号内子类型，按子类型分流建议（现有规则文案写死 `main_memory` 与
   `input stack size` 不符，见 round1 c15）。
2. `input stack size` → 找宏自递归/循环调用，沿 `->` 展开链定位自引用宏。
3. `main memory` / 块过大 → 拆分内容、清理中间临时文件后重跑。
4. 带代码执行的宏包（pythontex 等）：先清临时产物目录，再判断是否需要调内存。

**常见误诊**

- 所有容量问题都建议“增大 main_memory / 编译内存”。
- 忽略临时目录残留导致后续编译持续失败。
- 忽略引擎/文档类差异（zref-vario#8 的 lualatex vs pdflatex 分化）。

### 8. `! LaTeX Error: Something's wrong--perhaps a missing \item.`（现有规则 `missing_item`）

**日志特征**

`! LaTeX Error: Something's wrong--perhaps a missing \item.`；多出现于
itemize/enumerate/自定义列表/表格内部。

**根因**

1. 自定义列表环境内部问题：hustthesis#42，`publications` 环境包裹 enumerate，
   作者贴出环境定义排查。
2. 表格包内部测量路径误判：tabularray#400，Collaborator lvjr / Contributor muzimuzhi
   给出修法 `\SetTblrInner[tblr,longtblr]{measure=vbox}`；此处缺 `\item` 是包内部
   测量 bug，**不是用户漏写 `\item`**。
3. 模板/旧发行版个案：hipster-cv#1（tl2019）、nguyenvulong/QA#57。

**可执行步骤**

1. 确认报错是否位于 list 环境；纯正文列表先补 `\item`。
2. tabularray `longtblr` 场景：尝试 `\SetTblrInner[tblr,longtblr]{measure=vbox}`。
3. 自定义环境：检查 enumerate/itemize 包裹、enumitem 可选参数与 `\chapter*` 交互。
4. 旧发行版个案：核对模板要求的 TeX 发行版版本。

**常见误诊**

- 一律提示用户“补一个 `\item`”，忽略表格包内部测量 bug。
- 把自定义环境内部错误归因为正文排版。

### 9. `! File ended while scanning use of \xxx.` / `Runaway argument?`（现有规则 `runaway`）

**日志特征**

`Runaway argument?` 段落后接 `! File ended while scanning use of \xxx .`；
命令名在 `use of \xxx` 后。

**根因**

1. 全角中文括号：LaTeXFAQ-cn#46，`\section{title｝` 右括号为中文输入法全角；
   `\@xdblarg` 扫参数直到 EOF；修法改为 ASCII 括号。
2. verbatim / 脆弱帧：beamer#360，Owner josephwright 定位 verbatim 内容含
   `\end{frame}`，触发 `\@xverbatim` 扫描到 EOF；规避用自定义 `slide` 环境或
   semiverbatim。
3. 跨引擎 parity：phulin/umber#1523，`\__siunitx_tmp:w` 文件结束扫描。

**可执行步骤**

1. 先看 `Runaway argument?` 段定位未闭合参数；再核对报错命令的括号是否成对、
   是否混入全角 `（）｛｝`。
2. beamer 帧内 verbatim/代码：检查是否有 `\end{frame}` 文本、脆弱命令未加 `[fragile]`。
3. 宏包内部宏名（`\@xdblarg`、`\__..._tmp:w`）触发时，向上找用户侧首个未闭合参数。

**常见误诊**

- 只盯 `File ended` 行，不看 `Runaway argument?` 的参数回显。
- 把全角标点当普通括号缺失，提示“补 `}`”。
- beamer verbatim 场景给出补 `\item` 之类无关修法。

### 10. `! Package fontspec Error: The font "xxx" cannot be found.` / `Missing character`（round1 c14：现有 `package_error` 兜底）

**日志特征**

- `! Package fontspec Error: The font "xxx" cannot be found.`
- 警告：`Missing character: There is no <char> (U+....) in font <name>!`

**根因**

1. 系统字体缺失或版本不符：tectonic#157，Collaborator pkgw 区分三类——系统未装字体
   （`apt install fonts-font-awesome`、`fc-cache` 刷新）、FontAwesome 4/5 命名差异、
   tectonic bundle 缺字体文件（bundle 侧补丁见该 issue 链接的
   tectonic-texlive-bundles#10）。
2. tectonic 不读系统字体目录：tectonic#1265，Contributor thangleiter 建议
   `tectonic -X bundle search "<name>"`；系统字体不可见见 #1238。
3. 字体名 ≠ 安装包名：MiKTeX#127 映射见族 3。
4. 字形在字体里但 Unicode 槽位错误（PUA）：latex2e#1656，Author randolf-scholz 指出
   字符在 PUA 而非正确槽位；Member FrankMittelbach 标注内核长期项，修法在字体侧。

**可执行步骤**

1. 先判引擎：fontspec 只服务 xelatex/lualatex；pdflatex 日志出现 fontspec 报错本身异常。
2. 核对字体族名拼写与版本（FA4 vs FA5 命名）；系统侧装字体后刷新字体缓存。
3. tectonic：用 bundle 搜索查可用字体，不要指向系统目录。
4. `Missing character`：先换含该字形的字体；若同家族多字体仍缺，查 Unicode 槽位/编码，
   不要无脑换字体。

**常见误诊**

- pdflatex 下建议安装 OpenType 字体。
- 把字体族名当安装包名。
- Missing character 一律建议换字体，忽略槽位/编码问题（latex2e#1656）。

### 11. `Unicode character ... (U+....) not set up for use with LaTeX`（现有规则 `unicode`，含 CJK）

**日志特征**

`! LaTeX Error: Unicode character <char> (U+....) not set up for use with LaTeX.`，
常带 `(inputenc)`；CJK 字符典型为 U+4E2D。

**根因**

1. pdflatex + inputenc 不支持该 Unicode：overleaf#511（中 U+4E2D，无维护者结论）、
   certik#51（≤ U+2264，Sphinx latexpdf）。
2. pdflatex 时代 CJK 包 workaround：gobborg#2 PR，author 字段中文用
   `\CJK{UTF8}{min}`（CJK 包，非 ctex/xeCJK 路线）。
3. 文件编码损坏：swimmingbrain#28，φ U+03C6 被按非 UTF-8 读入；建议重打字符/另存 UTF-8。
4. 生成器侧缺 Unicode 映射：mksigma#43；CJK 目标构建中断：QuantEcon#181；
   组合附加符个案：fedefelds#16（正文空）。

**可执行步骤**

1. 先判引擎：pdflatex+inputenc → 换 xelatex/lualatex + ctex/xeCJK/fontspec 路线；
   或在 pdflatex 下使用对应语言包/命令。
2. CJK 场景不要建议 `\usepackage[utf8]{inputenc}` 解决；先确认引擎是否为 XeLaTeX/LuaLaTeX。
3. 先查文件是否真为 UTF-8（编辑器编码、复制来源），再判断是否缺语言宏包。
4. 数学符号（≤、≥、≈ 等）按数学模式问题处理，不要归入 CJK。

**常见误诊**

- xelatex 下仍建议“改用 XeLaTeX”（round1 c10 已标注此误导）。
- 把编码损坏（非 UTF-8）当成缺语言宏包。
- 把数学符号当 CJK 处理，或反之。

### 12. BibTeX / Biber：打不开库、找不到条目、bad cross reference

**日志特征**

- `I couldn't open database file xxx.bib` / `I found no database files---while reading file xxx.aux`
- `Warning--I didn't find a database entry for "key"`
- `A bad cross reference---entry "a" refers to entry "b", which doesn't exist`

**根因**

1. 双 `.bib` 扩展名：MiKTeX#541，Member edocevoli 提交 strip double extension 修复；
   `\bibliography{file.bib}` 这类写法在旧 MiKTeX-BibTeX 打不开，TeX Live 容忍扩展名
   （发行版差异）。
2. 仓库漏提交 `.bib`：topepo#4，Owner 补提交 bib 文件后关闭；日志同时伴随多条
   `I didn't find a database entry`。
3. `.bib` 条目顺序：testimony#269，Collaborator deanberris 说明 BibTeX 的 `crossref`
   只解析“被引条目排在引用它的条目之后”的顺序；重排 `.bib`（#271）后修复；
   提示 “doesn't exist” 可能是顺序问题而非条目缺失；tectonic 会忽略 BibTeX 错误继续出 PDF。
4. 工具链：biblatex/biber 工作流问题见 tectonic#1226；dblpbibtex#13、cryptobib#21 为
   crossref/条目维护类（API 正文未展开，仅作存在性佐证）。

**可执行步骤**

1. 打不开 `.bib`：核对文件是否在工程内、`\bibliography`/`\addbibresource` 键名与扩展名；
   MiKTeX 下先去掉 `.bib` 扩展名重试。
2. 找不到条目：核对 `.bib` 是否被加载、key 拼写、是否跑完 bibtex/biber；区分当前工具链。
3. bad cross reference：检查被 `crossref` 引用的条目是否存在，且在 `.bib` 中排在引用它的
   条目之前。
4. PDF 看似正常但文献缺失：检查编辑器/引擎是否静默忽略了 BibTeX/Biber 错误
   （testimony#269 的 tectonic 行为）。

**常见误诊**

- 把缺文件当成宏包缺失，建议装 TeX 包。
- biber 与 bibtex 的提示文案/规则混用。
- crossref 顺序问题被当成条目被删除。
- 引擎静默跳过文献错误，导致漏跑文献工具链。

---

## 风险与误报

### 引擎维度（pdflatex / xelatex / lualatex）

- inputenc、Unicode 字符、CJK、fontspec、OpenType 字体建议**不可跨引擎互通**：
  fontspec 报错只在 Xe/LuaLaTeX 语境有效；pdflatex 走 NFSS/Type1 字体路线。
- 同一 MWE 不同引擎结果可能分化：zref-vario#8 的 lualatex/book 可用而 pdflatex/scrbook 失败；
  phulin/umber#1523 为跨引擎 parity 个案。
- tectonic 有独立 bundle 可见性：系统目录中的包/字体默认不参与查找（tectonic#1265、#157）。

### 工具链维度（bibtex / biber；latexmk / tectonic / 编辑器内置）

- BibTeX 与 biber 的日志文案、crossref 解析规则不同；hint 文案需标注当前工具链。
- 各工具遇错是否继续编译不同：latexmk 遇错可继续，tectonic 默认 halt on recoverable error
  （tectonic#1022）；继续编译会让首条错误位置漂移，Missing $ 等次级报错可能不在根因行。
- tectonic 会忽略 BibTeX 错误继续出 PDF（testimony#269），不能以“PDF 生成成功”判断文献无误。

### 级联维度

- Missing $、Missing \begin{document}、Undefined control sequence 都可能是上游首错的
  次级表现；规则排序与文案应体现“首错优先”，不要把级联错误当根因。
- 解析器侧也存在消息误判先例（texlab#828），规则匹配需保留上下文与首错位置校验。

### 发行版维度

- 四套包/字体安装途径不可互换：TeX Live `tlmgr install`、MiKTeX `miktex packages install`
  （旧 `mpm`）、tectonic bundle 搜索、Linux 系统包管理器；字体名与宏包名常不一致
  （MiKTeX#127）。
- 同一宏包在不同发行版的 collection 划分不同（collective#3：Fedora `texlive-beebe` vs
  `texlive-collection-latexextra`）。

### 生成器维度

- MathJax 报错 “Double subscripts” 与 TeX 引擎 `! Double subscript.` 文本不同，匹配规则需
  分别覆盖。
- 代码生成 LaTeX 的上下标分组 bug（FactorTester#55、PyBaMM#6043）修法在生成器侧，
  与手写 LaTeX 的修法位置不同；hint 文案不应假设用户直接编辑生成的公式串。

### 内核版本维度

- LaTeX2e 2024-11-01 起，类选项默认不再自动传给包，需显式 `.pass-to-packages`
  （latex2e#1589）；旧教程“把选项放文档类即可传给包”的修法在新版失效。

---

## 未检索到的族 / 未覆盖边界

1. **TeX StackExchange 原始问答**：tex.stackexchange.com 对自动化访问返回 robots.txt
   禁止，本轮未打开任何 tex.se 页面。搜索摘要中可见 Egreg 对 xcolor clash 的建议
   （提前加载 xcolor / 走类选项 / `\PassOptionsToPackage`），但因未打开原页，未列入上方
   来源清单；后续轮次如需社区高票答案，需人工浏览器核验 URL 与回答日期。
2. **Biber 专属 `I didn't find a database entry` GitHub issue**：API 检索 0 命中；现有规则
   按日志文本覆盖该串，biber 侧真实样本（含 biber 自身 `WARN -` 前缀变体）待后续补样。
3. **BOM 触发 `Missing \begin{document}` 的 GitHub 原始报告**：未检索到；本轮两例
   latex2e 均为内部宏级联，用户侧 BOM/正文提前场景目前只有 round1 c05 样本（采集自 round1 Linux TeX Live 环境）。
4. **TeX-Live/texlive 仓库 issue**：该镜像仓库无对应 issue tracker 命中；发行版差异证据
   来自 MiKTeX 仓库与下游仓库（collective#3、arena-slides#4）。
5. **日志解析类仓库规则对照**：latex-log-parser、texloganalyser、TeXiFy、latex-utensils 本轮
   未打开其规则定义或 issue；现有分类映射与消息优先级需后续轮次对照这些仓库的 parser 实现。
6. **overleaf/overleaf 仓库**：平台侧 issue 居多，编译器内部行为证据有限，仅 overleaf#511
   一条进入清单。
7. **正文为空的 API 条目**：FITEE#3、Curriculum-vitae#21、fedefelds#16 正文为空，未摘录
   日志片段；如需引用其结论需重新打开页面补证。
8. **本轮未做的事**：未运行编译验证、未改任何 `.py`、未补 fixture/测试；规则设计与回归
   属后续轮次。（环境前提更正：round1 曾误判本机 `xelatex/pdflatex/lualatex/biber/bibtex/latexmk`
   不在 PATH；实测本机 MiKTeX 26.5 Portable 下这些引擎均在 PATH。本轮为联网调研，当时编译验证
   在 Linux TeX Live 临时目录或 fixture 中进行；本机真实编译复核已在 round6 完成（见 `round6-real-miktex.md`）。）
