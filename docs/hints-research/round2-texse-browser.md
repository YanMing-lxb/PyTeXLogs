# 第 2 轮补充：TeX Stack Exchange 浏览器取证

> 切片边界：只做调研写文档；未改任何 `.py` 源码，未 commit，未动 MiKTeX/TeX 环境。
> 取证日期：2026-11-21。本轮通过内置浏览器（browser-use）只读访问
> `tex.stackexchange.com`，未登录、未投票、未点赞、未发帖、未修改任何页面状态；
> 仅使用站内搜索与问题页阅读。
> 说明：`round2-official.md` 由另一智能体维护，本文件不修改它；两条线的结论在
> 「对现有 hint 的修正建议」一节并列对照。

## 浏览器取证说明

- **入口方式**：站内搜索 `https://tex.stackexchange.com/search?tab=votes&q=<关键词>`
  （按最高票排序），命中后直接打开 `/questions/<id>/<slug>` 问题页；问题正文、采纳答案、
  票数、标签均从页面 DOM 读取。
- **检索词策略**：先短词按票排序（如 `double subscript`、`TeX capacity exceeded`），
  再用引号精确匹配错误原文（如 `"Missing $ inserted"`、`"Too many }'s"`）。
- **只读边界**：全程未触碰登录/注册入口；搜索过程中一次跳转
  `tex.stackexchange.com/nocaptcha` 人机验证页，未做任何验证交互；随后直接访问问题页
  仍可匿名读取，未因此中断取证。
- **记录口径**：票数为问题页可见的问题票数与（若有）采纳答案票数；「采纳」以页面
  accepted-answer 标记为准；未采纳/已关闭问题在表中明确标注，不作为强证据。
- **与上一轮的关系**：上一轮（`round2-official.md`）因 robots 限制未能直开 SE 页面，
  相关特例只经 Overleaf 帮助页转引；本轮补齐这些特例的 SE 原始问答。

## 来源清单

| 编号 | 主题 | 问题标题 | 完整 URL | 投票 / 采纳情况 | 关键原文短句（英文原句） | 适用引擎 / 工具 |
| --- | --- | --- | --- | --- | --- | --- |
| SE1 | Double subscript 重音原子特例 | Why am I getting a double subscript error? | https://tex.stackexchange.com/questions/253080/why-am-i-getting-a-double-subscript-error | 问题 20 票；采纳答案 26 票，已采纳 | "It's a feature in TeX."；"when a subformula happens to only contain an 'accent atom' … the braces around this atom are stripped off and TeX acts as if they had never been there"；空组 workaround `${{}\hat{a}_b}_c$` | tex-core，pdflatex/xelatex/lualatex 通用 |
| SE2 | 嵌套下标的三种合法写法 | Double Subscript for Subsequences | https://tex.stackexchange.com/questions/38100/double-subscript-for-subsequences | 问题 40 票；采纳答案 89 票，已采纳 | "`${x_n}_i$` and `$x_{n_i}$` are both valid expressions from a purely syntactic point of view. However, they do not create the same output." | math-mode，引擎通用 |
| SE3 | ctex 缺字形（CJK 字体不含该字） | Missing characters in ctex | https://tex.stackexchange.com/questions/511538/missing-characters-in-ctex | 问题 1 票；答案 2 票，**未采纳** | "According to ctex Chinese manual (page 9), changing the font can solve the character missing problem"；改法 `\setCJKmainfont[...]` 更换 CJK 字体 | xelatex + ctex |
| SE4 | xeCJK 按文件名取字体；NFSS 声明多余 | xeCJK doesn't find a font from file | https://tex.stackexchange.com/questions/205266/xecjk-doesnt-find-a-font-from-file | 问题 1 票；答案 2 票，**未采纳** | "The xeCJK package could access font file directly. That is, `\DeclareFontFamily` and `\DeclareFontShape` are superfluous here."；改法 `\setCJKmainfont{ukai.ttc}` | xelatex + xeCJK |
| SE5 | LuaLaTeX 安装/调用新字体 | How to properly install and use a new font with LuaLaTeX? | https://tex.stackexchange.com/questions/103704/how-to-properly-install-and-use-a-new-font-with-lualatex | 问题 36 票；采纳答案 33 票，已采纳 | "If you want fontspec to automatically find the path to the font and load it for you, then you need to have the font installed as a system font."；否则显式指定字体路径 | lualatex / fontspec / luaotfload，MacTeX 场景 |
| SE6 | TFM 文件找不到（pdflatex 缺宏包） | Error in TeX Live – Font … not loadable: Metric (TFM) file not found | https://tex.stackexchange.com/questions/75166/error-in-tex-live-font-not-loadable-metric-tfm-file-not-found | 问题 159 票；采纳答案 125 票，已采纳 | "the missing file is `ecrm1000.tfm` according to the error message"；`tlmgr search --file ecrm1000.tfm --global` 定位到宏包 `ec`，再 `tlmgr install ec`；或装 `collection-fontsrecommended` | pdflatex，TeX Live |
| SE7 | 引用未定义：`[?]` vs 粗体键；.blg 三级诊断 | Question mark or bold citation key instead of citation number | https://tex.stackexchange.com/questions/63852/question-mark-or-bold-citation-key-instead-of-citation-number | 问题 192 票；采纳答案 246 票，已采纳 | "If you are using biblatex you will not see a question mark, but instead you will see your citation key in bold."；.blg 三级：`I couldn't open the style file …bst` → `I couldn't open database file …bib` → `Warning--I didn't find a database entry for "yourcitation"` | BibTeX 与 biblatex/biber 通用诊断流程 |
| SE8 | biber 报条目找不到（陈旧 .bib 未覆盖） | Biber fails to find entry | https://tex.stackexchange.com/questions/646465/biber-fails-to-find-entry | 问题 3 票；采纳答案 5 票，已采纳 | biber 告警原文 `WARN - I didn't find a database entry for 'smith1983' (section 0)`；根因是内核 `filecontents` 默认不覆盖旧文件，需 `[overwrite]` | biber / biblatex，TeX Live 2022 / biber 2.17 |
| SE9 | input stack size=5000（宏包内无限循环） | Tex capacity exceeded, sorry [input stack size = 5000] | https://tex.stackexchange.com/questions/24247/tex-capacity-exceeded-sorry-input-stack-size-5000 | 问题 114 票；采纳答案 94 票，已采纳 | "the PhDbiblio-url2 bibliography style does not want the url field to contain `\url{...}`"；样式把 url 包进 `\href{...}` 形成 hyperref 无限循环；改法 `url = {http://example.com}` | BibTeX/hyperref，引擎通用 |
| SE10 | main memory size（pgfplots 外置化优先于扩内存） | How to expand TeX's "main memory size"? (pgfplots memory overload) | https://tex.stackexchange.com/questions/7953/how-to-expand-texs-main-memory-size-pgfplots-memory-overload | 问题 175 票；采纳答案 116 票，已采纳 | "that does not mean that expanding TeX's memory is the best solution. Instead, I would recommend using the 'externalization' approach … compile each plot as a separate TeX job." | pdflatex / pgfplots |
| SE11 | Missing `\begin{document}`（导言区畸形命令） | Error: Missing `\begin{document}` | https://tex.stackexchange.com/questions/29463/error-missing-begindocument | 问题 31 票；采纳答案 34 票，已采纳 | "You're just missing a backslash in the command definition, it should be `\newcommand{\dice}[1]{\ensuremath{#1}}`"；导言区把 `dice` 当成了排版文本 | LaTeX 层；提问用 XeTeX 复现，结论引擎无关 |
| SE12 | Missing `\begin{document}` 内核机制 | How does "missing `\begin{document}`" work? | https://tex.stackexchange.com/questions/59951/how-does-missing-begindocument-work | 问题 15 票；采纳答案 16 票，已采纳 | "LaTeX uses the `\everypar` token register to set up the error."；`\@nodocument` 在导言区首次进入水平模式（开始段落）时触发；`\document` 宏将其移除 | LaTeX 内核，引擎通用 |
| SE13 | 数学命令在文本模式 → Missing `$` | `\overline` outside of math mode | https://tex.stackexchange.com/questions/24132/overline-outside-of-math-mode | 问题 43 票；采纳答案 45 票，已采纳 | "`\overline` seems to only work in math mode, and when used outside of math mode, it automatically says 'Missing $ inserted'."；文本上划线 workaround `$\overline{\mbox{#1}}$` | math-mode，引擎通用 |
| SE14 | Option clash（xcolor 被先加载，全局选项路由） | Option clash for package xcolor | https://tex.stackexchange.com/questions/83101/option-clash-for-package-xcolor | 问题 176 票；采纳答案 198 票，已采纳 | "The package xcolor has already been loaded with options: [] There has now been an attempt to load it with options [table]"；LaTeX 提示把 `table` 作为全局选项加到 `\documentclass` | LaTeX 宏包加载层，引擎通用 |
| SE15 | Too many }'s（模板宏重定义所致，弱证据） | Error message: too many }'s | https://tex.stackexchange.com/questions/27042/error-message-too-many-s | 问题 9 票；答案 6 票，**已关闭、未采纳** | "Most probably it is the package xthesis that contains some pieces of code to redefine `\@xfloat` in a bad way."；大学论文模板 `doublespace.sty` 类定义引发 | 弱证据：模板/宏包层，引擎通用 |
| SE16 | `\left.`/`\right.` 空定界符语义 | What is the purpose of "`\left.`", i.e., "`\left`" followed by a period? | https://tex.stackexchange.com/questions/429437/what-is-the-purpose-of-left-i-e-left-followed-by-a-period | 问题 20 票；答案 35 票，**未采纳** | "the '.' symbol after `\right` denotes 'no fence on that side'"；单侧大括号用 `\left\{ … \right.` 配对 | math-mode 定界符，引擎通用 |
| SE17 | 典型错误合集：文本模式写希腊字母 → Missing `$` | Documents with typical LaTeX errors | https://tex.stackexchange.com/questions/33468/documents-with-typical-latex-errors | 问题 64 票；采纳答案 77 票，已采纳 | "Using math-related content without specifying it explicitly as being math"；`\alpha`/`\beta` 写在正文 → `! Missing $ inserted.`，修法是显式切换数学模式 | 教程合集，引擎通用 |

## 逐条结论

### SE1 Double subscript：重音原子的花括号会被 TeX 剥掉

- **SE 结论**：`${a_b}_c$` 合法，但 `${\hat a_b}_c$` 报 Double subscript；再套一层
  `${{\hat a}_b}_c$` 也无效。采纳答案解释：按 Knuth 的设计，当一个子公式（花括号组）
  只含一个「重音原子」（如 `\hat{x}` 及其上下标）时，外层花括号会被剥离，
  `${\hat a_b}_c$` 等价于 `$\hat a_b_c$`。可行 workaround 是在重音前插一个空组：
  `${{}\hat{a}_b}_c$`。
- **与 Overleaf 简化说法的差异**：Overleaf Double subscript 页只给了「加花括号分组」
  的通用建议；SE 补充了一个反直觉特例——**对重音原子加花括号不生效**，必须用空组
  或 `accents` 宏包类手段。
- **对现有 hint 的修正建议**：现有 `double_script` 文案（`x_1_2` 加花括号）覆盖普通
  嵌套下标；可在特例分支补充：重音符号（`\hat/\bar/\vec/\tilde` 等）作用于带下标的
  原子时，外层花括号会被剥离，需写 `${{}\hat{a}_b}_c$` 形式。
- **误诊边界**：不要把该特例当成「括号加得不够多」；再多花括号也救不回被剥离的组。
  该行为是 tex-core 设计而非发行版 bug（提问者最初怀疑是自己 TeX 发行版的 bug）。

### SE2 嵌套下标：三种写法语法都合法，但排版结果不同

- **SE 结论**：`x_{ni}`、`${x_n}_i$`、`x_{n_i}` 三者语法均合法；区别在于外层下标
  挂在哪个基元上，下标下沉位置与视觉层级不同。
- **与 Overleaf 简化说法的差异**：Overleaf 把分组写法列为唯一修法；SE 强调选择哪种
  分组取决于「外层下标属于谁」，不是单纯消错。
- **对现有 hint 的修正建议**：`double_script` 文案可区分两种分组意图：
  嵌套下标 `x_{n_i}`；整体带下标 `${x_n}_i`。
- **误诊边界**：消错后仍应核对视觉层级；语法合法 ≠ 排版符合意图。

### SE3 ctex 缺字形：先换 CJK 字体，而不是换引擎

- **SE 结论**：XeLaTeX + `ctex` 下个别汉字（例：`祂`）缺字形，按 ctex 手册第 9 页
  更换 CJK 字体（`\setCJKmainfont` 等）解决。该帖票数低且未采纳，仅作方向参考。
- **与 Overleaf/上一轮说法的差异**：上一轮 `missing_glyph` CJK 分支建议「改用
  Xe/Lua 并加载 ctex/xeCJK」；SE 场景已经在 XeLaTeX+ctex 下，症结是**当前 CJK 字体
  不含该字**，换字体才是直接修法。
- **对现有 hint 的修正建议**：CJK 缺字形提示应分两步：① 引擎/宏包是否就位
  （pdflatex 无 CJK 字体链）；② 已在 Xe/Lua+ctex/xeCJK 时，检查当前 CJK 字体覆盖，
  用 `\setCJKmainfont`/`\setCJKsansfont` 换字库。
- **误诊边界**：低票未采纳答案，具体字体名（STSong 等）是 macOS 场景，不能照搬
  到 Windows/Linux；字体集选择需结合发行版。

### SE4 xeCJK 直接按文件名取字体；NFSS 字体族声明多余

- **SE 结论**：同一字体文件在裸 fontspec 下可用，切到 xeCJK 后报
  `fontspec error: "font-not-found"`（族名 `ukai` 找不到）。答案指出 xeCJK 可直接
  访问字体文件，`\DeclareFontFamily`/`\DeclareFontShape`（EU1 NFSS 声明）在此场景
  多余；正确写法 `\setCJKmainfont{ukai.ttc}`。
- **与上一轮说法的差异**：上一轮 fontspec 规则区分「按名 / 按文件名 + Path」；SE 补充
  xeCJK 通道同样按文件名加载，且不要把 pdflatex 时代的 NFSS 字体族声明搬过来。
- **对现有 hint 的修正建议**：CJK 字体找不到时，提示核对 `\setCJKmainfont` 用的是
  族名还是文件名；文件在当前目录时直接写文件名（含扩展名）。
- **误诊边界**：该帖未采纳；报错文本里的 `fontspec error: "font-not-found"` 是
  xeCJK 内部调用 fontspec 抛出，不要误判为 xeCJK 自身缺宏包。

### SE5 LuaLaTeX 自动找字体的前提：字体装进系统；否则显式给路径

- **SE 结论**：fontspec 想自动按名定位字体，字体必须作为系统字体安装（macOS 可在
  Font Book 改安装位置为 Computer）；不想动系统字体时，把字体文件放在工程目录并显式
  指定路径/文件名。luaotfload 会扫描 OS 字体与 TEXMF 字体生成名称数据库。
- **与上一轮说法的差异**：上一轮 fontspec 手册结论（标准字体目录、LuaTeX 名称缓存）
  与 SE 一致；SE 补充了「用户字体 vs 系统字体」的安装位置这一常见坑。
- **对现有 hint 的修正建议**：font-not-found 排查顺序可写为：族名拼写 → 字体是否在
  系统标准目录 → 不在则改文件名 + `Path=` → LuaTeX 刷新 luaotfload 名称缓存。
- **误诊边界**：答案场景为 MacTeX/macOS；Linux 走 fontconfig，Windows 走系统字体表，
  安装位置与刷新命令不同（上一轮已记 FC-list 与 FNDB 的边界）。

### SE6 TFM not found ≠ fontspec font-not-found：pdflatex 缺编码字体宏包

- **SE 结论**：TeX Live basic 安装下，`\usepackage[T1]{fontenc}` 报
  `Font T1/cmr/m/n/10=ecrm1000 … not loadable: Metric (TFM) file not found`。
  修法：按日志里的 `.tfm` 文件名 `tlmgr search --file ecrm1000.tfm --global` 定位
  宏包（`ec`），`tlmgr install ec`；或直接装 `collection-fontsrecommended` /
  `collection-latexrecommended`；也可用 texliveonfly 自动补宏包。
- **与上一轮说法的差异**：上一轮把两类字体错误都收在 missing_font/missing_glyph
  框架下；SE 明确区分：TFM not found 是 **pdflatex 缺 Type1/TFM 支持文件（宏包缺失）**，
  与 Xe/Lua 的 OpenType 字体找不到是两条不同链路。
- **对现有 hint 的修正建议**：`Metric (TFM) file not found` 应有独立提示：按日志
  `.tfm` 名查宏包并安装（TL `tlmgr`；MiKTeX 对应包管理/自动安装），不要引导用户去
  系统字体目录找 OpenType 字体。
- **误诊边界**：basic 版 TeX Live 缺字体集合是发行版裁剪问题；不要建议换引擎来解决
  TFM 缺失。

### SE7 引用未定义：biblatex 显示粗体键而非 `[?]`；先读 .blg 三级诊断

- **SE 结论**：经典 BibTeX 未定义引用显示 `[?]`；biblatex/biber 显示**粗体引用键**。
  诊断先跑完整流程（LaTeX → bibtex/biber → LaTeX ≥2 次，都作用于主文件basename，
  不在 `.bib` 上跑命令）；然后打开 `.blg`，按三级定位：① `I couldn't open the style
  file …bst`（样式文件问题）；② `I couldn't open database file …bib`（数据库路径/
  拼写问题）；③ `Warning--I didn't find a database entry for "key"`（条目/键不匹配）。
- **与上一轮说法的差异**：上一轮 Overleaf 流程只讲多轮编译；SE 给出了 .blg 内部的
  三级错误分流，并区分了两种未定义引用的可见形态。
- **对现有 hint 的修正建议**：undefined_citation 提示应引导先看 `.blg`，并区分
  bst 打不开 / bib 打不开 / 条目找不到三种处置；提示 biblatex 下 PDF 里是粗体键而非
  问号，避免用户误以为「没报错」。
- **误诊边界**：`.blg` 没生成说明文献工具根本没跑成功；此时改键名无效。条目找不到
  也可能是更早的 `.bib` 语法错误连带跳过（见 SE8）。

### SE8 biber 条目找不到：陈旧/未覆盖的 .bib 会伪装成条目缺失

- **SE 结论**：biber 2.17 报 `WARN - I didn't find a database entry for 'smith1983'
  (section 0)`，MWE 键名明明一致；根因是内核 `filecontents` 默认**不覆盖**旧
  `.bib`，读到的是残留空文件；加 `[overwrite]`（或 `force`）后正常。
- **与上一轮说法的差异**：上一轮把「条目找不到」归因于键名拼写/条目被语法错误跳过；
  SE 补充第三种：**读到了错误的/陈旧的 .bib 文件**（工程目录残留、filecontents 未覆盖）。
- **对现有 hint 的修正建议**：biber/database entry 提示可增加：删除工程目录陈旧
  `.bib`/辅助文件后重跑；`filecontents` 写嵌入式数据库时用 `[overwrite]`。
- **误诊边界**：biber 告警带 `(section 0)` 段号；该现象依赖 TL2022 内核 filecontents
  行为，新版本表现可能不同。

### SE9 input stack size=5000：可以是宏包/样式内部的无限循环，不只是自写宏递归

- **SE 结论**：加新参考文献后报 `input stack size = 5000`；根因是书目样式
  （PhDbiblio-url2）把 url 字段内容再包进 `\href`，而字段里已手写 `\url{...}`，
  在 hyperref 内形成无限循环；修法是 url 字段只写裸 URL：`url = {http://example.com}`。
- **与上一轮说法的差异**：上一轮容量子类型把 input stack 归为「循环/递归宏定义」；
  SE 实例说明循环点可能在**宏包/样式展开链**里（hyperref ↔ 书目样式），用户宏本身
  没有自引用。
- **对现有 hint 的修正建议**：input stack 提示除「检查自引用宏」外，补充：顺着
  日志 `->` 展开行看是哪个宏包进入循环；书目/链接字段里不要嵌套重复的链接命令。
- **误诊边界**：调大栈容量只会推迟爆栈；先断循环。该例由 BibTeX 样式触发，与引擎
  内存参数关系不大。

### SE10 main memory size：pgfplots 优先外置化，扩内存是次选

- **SE 结论**：`main memory size=3000000` 出现在多幅 pgfplots 噪声图；采纳答案建议
  用 pgfplots externalization（每幅图单独编译成图形，主任务只插图），通常无需扩大
  TeX 内存；扩内存只是备选。
- **与上一轮说法的差异**：上一轮 main memory 成因列举长宏/索引/复杂页面与堆积浮动体；
  SE 补充大数据量图形这一高发场景，且首选解法是任务拆分而非调参数。
- **对现有 hint 的修正建议**：main memory 提示在 pgfplots/大表格场景优先建议外置化、
  降点数、`\clearpage` 释放浮动体；扩容命令后置。
- **误诊边界**：externalization 需要正确配置辅助编译目录与两次编译；不是所有图形包
  都有等价机制。

### SE11 Missing `\begin{document}`：导言区一条畸形命令即可触发

- **SE 结论**：`\newcommand{dice}[1]{...}` 漏了命令名反斜杠，TeX 把导言区的 `dice`
  当作要排版的正文，触发本条错误；补成 `\newcommand{\dice}...` 即修复。
- **与上一轮说法的差异**：上一轮成因列举「导言区正文/盒子内容/BOM/陈旧 aux」；SE
  补充：**导言区命令定义写错**（缺反斜杠、命令名打到导言区）同样会被当成正文排版。
- **对现有 hint 的修正建议**：missing_begin_document 排查清单可加入「检查导言区
  `\newcommand/\def/\newenvironment` 定义是否笔误（命令名缺 `\`）」。
- **误诊边界**：报错行号指向导言区那条畸形命令，而不是 `\begin{document}` 本身；
  不要去文件末尾找漏写的 `\begin{document}`。

### SE12 机制：`\@nodocument` 挂在 `\everypar` 上，导言区首个水平材料触发

- **SE 结论**：`\everypar` 寄存器里预置 `\@nodocument`；TeX 在垂直模式遇到水平材料
  开始段落时插入 `\everypar`，从而抛出本错误；`\document` 宏负责把 `\@nodocument`
  移除。这解释了为什么「导言区任意一个被排版的字符」都会触发，而不只是某条特定命令。
- **与上一轮说法的差异**：与上一轮引用的 lterror.dtx 注释（"Error produced if
  paragraphs are typeset in the preamble."）互相印证；SE 给出了寄存器层面的机制。
- **对现有 hint 的修正建议**：无新增规则需求；可作为文案依据——本条错误的本质是
  「导言区进入了段落/水平模式」，排查应聚焦导言区第一条被排版的内容。
- **误诊边界**：纯宏包选项、声明类语句不触发；只有产生水平模式内容的语句才触发。

### SE13 数学专用命令写进正文 → Missing `$`

- **SE 结论**：`\overline` 只在数学模式合法；写进正文直接报 Missing `$ inserted`。
  需要在文本上加划线时，包一层数学盒子：`$\overline{\mbox{#1}}$`（或 `\hbox` +
  `\m@th`）。
- **与上一轮说法的差异**：上一轮 Missing `$` 成因已含「数学符号/命令在文本模式」；
  SE 给出具体命令实例（`\overline` 类重音/分式/括号命令）与文本包装 workaround。
- **对现有 hint 的修正建议**：math_mode 提示可点名：`\overline/\underline/\sqrt/
  \frac/\vec/\hat` 等命令只在数学模式；文本需要类似效果时用 `\mbox` 包进数学模式。
- **误诊边界**：反过来，数学模式里出现文本原语（空行、`\par`、`\vskip`）也会报同类
  错误，方向相反，不要一律按「补 `$`」处理。

### SE14 Option clash：先加载者定选项集合；可把冲突选项提升为文档类全局选项

- **SE 结论**：xcolor 已被其他宏包以空选项 `[]` 先加载，后续 `\usepackage[table]`
  冲突；错误文本直接给出两次选项："already been loaded with options: [] … attempt to
  load it with options [table]"。采纳路线：把 `table` 作为全局选项加到
  `\documentclass[...,table]{memoir}`。
- **与上一轮说法的差异**：上一轮 usrguide/TeX FAQ 已载「合并选项」与
  `\PassOptionsToPackage`；SE 补充第三种官方建议路由：**文档类全局选项**（错误文本
  自身提示 "Adding the global options … to your \documentclass declaration may fix this"）。
- **对现有 hint 的修正建议**：option clash 提示可并列三条修法：合并为单次
  `\usepackage`；`\PassOptionsToPackage` 预埋；冲突选项提升为 `\documentclass`
  全局选项。并引导读错误文本里已加载/尝试加载的两组选项。
- **误诊边界**：报错点名的包往往是被间接先加载的；先加载者来自日志括号嵌套顺序，
  不一定是导言区显式写的那条。

### SE15 Too many }'s：可能来自模板宏的错误重定义（弱证据）

- **SE 结论**：加图片与题注后报 Too many }'s；答案怀疑论文模板宏包（xthesis /
  doublespace.sty）对 `\@xfloat` 的重定义有问题，需正确重定义该内部命令。帖子已
  关闭、答案未采纳，仅作可能性参考。
- **与现有文案的差异**：现有 `extra_close_brace` 只引导从报错行向前回溯源码花括号；
  SE 提示另一条路径：源码配对无误时，排查模板/宏包对浮动体、盒子内部命令的重定义。
- **对现有 hint 的修正建议**：extra_close_brace 可加一句兜底：源码括号配对仍报错时，
  临时注释最近加载的模板/样式宏包定位肇事者。
- **误诊边界**：证据等级低（关闭、未采纳）；不得把「模板宏问题」写成首因，仍以源码
  多打 `}` 为首要排查方向。

### SE16 `\left.`/`\right.`：点号表示该侧无可见定界符

- **SE 结论**：`\left`/`\right` 必须成对；只需要单侧大括号时，另一侧用 `.` 作隐形
  定界符配对，如 `\left\{ \begin{array}… \end{array} \right.`。
- **与现有文案的差异**：现有 `missing_right` 已建议补 `\right.`；SE 解释了 `.` 的
  语义，说明 TeX 恢复时插入的空 `\right.` 就是这个隐形配对。
- **对现有 hint 的修正建议**：可在文案中注明 `\right.`/`\left.` 是「无可见围栏」的
  合法配对，不是漏写标点。
- **误诊边界**：该答案未采纳；单侧定界符仍受 `\left...\right` 不得跨组/跨单元格限制
  （现有文案已覆盖）。

### SE17 典型错误合集：正文里写希腊字母是最高发的 Missing `$` 场景

- **SE 结论**：教学合集把「数学内容未显式放进数学模式」列为头号典型错误：正文写
  `\alpha`/`\beta` 触发 Missing `$ inserted`，修法是显式切换数学模式。
- **与上一轮说法的差异**：与 Overleaf Missing `$` 页一致，SE 高票合集佐证这是最高频
  成因；无新增分歧。
- **对现有 hint 的修正建议**：math_mode 提示可把「正文出现希腊字母/数学符号命令」
  列为第一顺位检查项。
- **误诊边界**：合集示例为命令形式；正文直接写 `_`/`^`/`$` 触发的同类错误同理，
  但字面下划线在文本中应转义为 `\_`，不要一律进数学模式。

## 浏览器可访问但未找到

1. **直接以 `Missing \right. inserted` 为标题的高票问答**：站内检索只命中
   `\left.` 用途解释（SE16）与合集帖（SE17），未找到专门讨论该恢复性报错的
   高质量问答；现有 `missing_right` 文案暂无 SE 实证补充。
2. **biblatex `xref` 字段继承语义**：以 `biblatex xref`/`crossref field inherit`
   检索，结果均为 shorthand、缩写表等无关主题；未找到专门问答。BibTeX 的
   `crossref` 字段语义上一轮已由 btxdoc 手册覆盖，biblatex `xref` 字段留待手册补证。
3. **biber 数据模型校验报错**（entry type/field 不合规、数据模型缺失）：未检索到
   高质量专门问答；现有 biber 提示中的数据模型相关分支本轮无 SE 实证。
4. **引用键大小写敏感的专门问答**：未找到独立高票帖；键名不匹配由 SE7 的
   「条目找不到」诊断间接覆盖。BibTeX/biber 键名大小写敏感这一点本轮未在 SE 页面
   直接核实，需以 biblatex/biber 手册为准。
5. **Double superscript 对照帖**：检索到 `/questions/32165/double-superscript-error`
   （45 票，已采纳），本轮未逐页打开；其上标分组规则与 SE2 下标情形同构，未计入
   已打开页面。
6. **站内人机验证**：一次搜索跳转 `/nocaptcha`，未交互、未绕过；之后问题页仍匿名
   可读。未登录状态下站内搜索结果排序与完整度可能受限，未找到不等于站内不存在相关
   问答。
