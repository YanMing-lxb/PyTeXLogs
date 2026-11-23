# 第 2 轮：官方文档 + TeXSE 联网取证（日志纠错建议）

> 范围：只做取证与结论整理，不改任何 `.py` 源码，不提交 git，不安装 TeX 包。
> 取证日期：2026-11-21。下列 URL 均为本轮实际打开过的页面；未成功打开的手册列入
> 「未覆盖/不确定项」，不计入来源清单。
> 阅读约定：每条结论给出「日志特征 → 根因 → 可执行修法 → 工具作用域 → 误诊风险」，
> 来源编号对应 `## 来源清单` 中的 `S#`。

## 来源清单

| 编号 | 主题 | 来源类型 | 页面标题 | URL | 可信度 |
| --- | --- | --- | --- | --- | --- |
| S1 | Missing `\begin{document}` 成因 | 社区维护 FAQ（UK-TUG TeX FAQ） | Missing `\begin{document}` \| The TeX FAQ | https://texfaq.org/FAQ-missbegdoc | 中高 |
| S2 | Option clash 成因与修法 | 社区维护 FAQ（UK-TUG TeX FAQ） | Option clash for package \| The TeX FAQ | https://texfaq.org/FAQ-optionclash | 中高 |
| S3 | 缺少 `\item` 的非常规成因 | 社区维护 FAQ（UK-TUG TeX FAQ） | Perhaps a missing `\item`? \| The TeX FAQ | https://texfaq.org/FAQ-errmissitem | 中高 |
| S4 | 缺字形（Missing character） | 社区维护 FAQ（UK-TUG TeX FAQ） | Where have my characters gone? \| The TeX FAQ | https://texfaq.org/FAQ-misschar | 中高 |
| S5 | Option clash 内核官方解释 | 官方手册镜像（LaTeX2e Unofficial Reference Manual / usrguide，MIT 镜像） | New error messages | https://web.mit.edu/newtex/doc/latex/base/usrguide/node39.html | 高 |
| S6 | 错误帧 `l.N` 与上下文读取 | 社区书籍派生文档（Dickimaw Books, LaTeX for Complete Novices 配套） | 7 Understanding Error Messages | https://www.dickimaw-books.com/latex/minexample/html/errormessages.html | 中 |
| S7 | Missing `$` inserted 全部成因 | 发行版帮助中心（Overleaf Learn） | Missing `$` inserted - Overleaf | https://www.overleaf.com/learn/latex/Errors/Missing_$_inserted | 中高 |
| S8 | Double subscript 修法与特例 | 发行版帮助中心（Overleaf Learn） | Double subscript - Overleaf | https://www.overleaf.com/learn/latex/Errors/Double_subscript | 中高 |
| S9 | 缺少 `\item` 常见成因 | 发行版帮助中心（Overleaf Learn） | LaTeX Error: Something's wrong--perhaps a missing `\item` - Overleaf | https://www.overleaf.com/learn/latex/Errors/LaTeX_Error:_Something%27s_wrong--perhaps_a_missing_%5Citem | 中高 |
| S10 | 参考文献多轮编译流程 | 发行版帮助中心（Overleaf Learn） | Bibliography management with bibtex - Overleaf | https://www.overleaf.com/learn/latex/Bibliography_management_with_bibtex | 中高 |
| S11 | 引擎与文件编码、Unicode 支持差异 | 发行版帮助中心（Overleaf Learn） | What file encodings and line endings should I use? | https://www.overleaf.com/learn/how-to/What_file_encodings_and_line_endings_should_I_use%3F | 中高 |
| S12 | 编译配方、bib 后端选择、产物目录 | 发行版工具链官方 Wiki（LaTeX-Workshop） | Compile · James-Yu/LaTeX-Workshop Wiki · GitHub | https://github.com/James-Yu/LaTeX-Workshop/wiki/Compile | 高 |
| S13 | MiKTeX 文件名数据库（FNDB）刷新 | 发行版官方文档（MiKTeX Docs） | Chapter 4. Maintenance — Refreshing the File Name Database | https://docs.miktex.org/manual/configuring.html | 高 |
| S14 | LaTeX 内核错误消息源码 | 官方内核源码（CTAN latex2e/base 镜像, lterror.dtx） | lterror.dtx — LaTeX Kernel (errors) | https://ctan.csail.mit.edu/macros/latex2e/base/lterror.dtx | 高 |
| S15 | 8 位引擎 Unicode 限制 | 官方项目通讯（LaTeX Project, ltnews30） | Improving Unicode handling in pdfTEX (LaTeX News 30) | https://www.latex-project.org/news/latex2e-news/ltnews30.pdf | 高 |
| S16 | capacity exceeded 总体处置 | 社区维护 FAQ 原始源文件（CTAN 归档 texfaq） | Enlarging TeX (FAQ Q-enlarge, faq-t-g-wr.tex) | https://tug.ctan.org/obsolete/help/texfaq/faq-t-g-wr.tex | 中高 |
| S17 | fontspec 字体查找规则与作用域 | 官方宏包手册（fontspec v2.9g, LaTeX3 Project） | The fontspec package — Font selection for XeLaTeX and LuaLaTeX | https://latex3.github.io/fontspec/fontspec.pdf | 高 |
| S18 | Unicode 字符显式映射 | 官方宏包手册（CTAN, newunicodechar v1.2） | The newunicodechar package | https://tug.ctan.org/macros/latex/contrib/newunicodechar/newunicodechar.pdf | 高 |
| S19 | 显示数学未闭合、Bad math delimiter 关联 | 发行版帮助中心（Overleaf Learn） | Display math should end with `$$` - Overleaf | https://www.overleaf.com/learn/latex/Errors/Display_math_should_end_with_$$ | 中高 |
| S20 | 字体生态与引擎边界 | 发行组官方站点（TUG） | Fonts and TeX - TeX Users Group | https://www.tug.org/fonts/ | 高 |
| S21 | 字体安装步骤、FNDB/字体缓存命令 | 发行组官方站点（TUG） | Installing TeX fonts - TeX Users Group | https://www.tug.org/fonts/fontinstall.html | 高 |
| S22 | 各类 capacity 子类型成因 | 标准 TeX 错误帮助文本镜像（latex.el 变量，英日双语） | LaTeX-error-description-list (Emacs Documentation Online) | https://doc.emacsen.de/29.4/var/LaTeX-error-description-list.html | 中 |
| S23 | BibTeX 编译流程、crossref 语义、检索路径 | 官方程序手册（CTAN, btxdoc.pdf） | BibTeX documentation (btxdoc) | https://tug.ctan.org/biblio/bibtex/base/btxdoc.pdf | 高 |
| S24 | `\include` / `\includeonly` 行为 | 官方手册 HTML 版（LaTeX2e Unofficial Reference Manual, latexref.xyz） | `\include` & `\includeonly` | https://latexref.xyz/_005cinclude-_0026-_005cincludeonly.html | 中高 |
| S25 | 错误帧结构、UCS 与 `$` 插入原文 | 正式出版书籍章节（CTAN 托管, TeX for the Impatient 第 8 章） | Making sense of error messages (errors.tex) | https://tug.ctan.org/info/impatient/errors.tex | 中高 |

> 说明：`tex.stackexchange.com` 对自动访问启用了 robots.txt 限制，本轮无法直接打开其问答页；
> 经 SE 讨论确认过的特例（如重音符号原子上的 Double subscript）只通过 Overleaf 帮助页 S8
> 转引，未把未读的 SE 链接列入上表。详见「未覆盖/不确定项」。

## 逐族结论

### 1. `! Undefined control sequence.` 与 `l.N` 上下文读取

**日志特征**

```
! Undefined control sequence.
l.3 Hello \undefinedcmd
                        world.
```

**根因**

TeX 读到一个从未被 `\def` 的控制序列。内核帮助原文（S25）：

> "The control sequence at the end of the top line of your error message was never \def'ed. If you have misspelled it (e.g., `\hobx'), type `I' and the correct spelling (e.g., `I\hbox'). Otherwise just continue, and I'll forget about whatever was undefined."

**错误帧读法（S25、S6）**

- 以 `!` 开头的第一行说明问题性质；`?` 提示符前的最后两行说明 TeX 读到哪里出错。
- 两行上下文之间的折行位置就是 TeX 的精确位置——**未定义命令位于上方那条上下文行的末尾**；
  当源行较长被日志按约 80 列折断时，命令名会出现在下一行续行上（见 round1 样本 c01/c02）。
- 若错误发生在宏展开内部，`l.N` 可能指向调用点而不是定义点。S6 示例：`\badcommand` 写在
  `\title{...}` 里，真正报错行却是 `l.8 \maketitle`，上方还有 `\@title ->A sample ... \badcommand`
  这样的展开行。此时应先在源码中搜索该命令名，再回溯哪些宏（`\author/\title/\date` 等）
  把它带到了出错位置。
- 多文件工程里 `l.N` 属于哪个文件不直观；用 `-file-line-error` 编译可得到
  `./mydoc.tex:8: Undefined control sequence.` 形式（S6）。

**可执行修法**

1. 核对命令拼写、大小写；2. 若命令来自宏包，确认对应 `\usepackage` 已在导言区加载；
3. 若是自定义命令，检查其 `\newcommand/\def` 是否写错或被条件块跳过；4. 多文件时先用
  `-file-line-error` 定位文件。

**工具作用域**：pdflatex / xelatex / lualatex 均为同一 TeX 层错误，引擎无关。

**误诊风险**

- 直接取 `l.N` 行最后一个 `\xxx` 可能误抓已定义命令；未定义命令在「TeX 停住的位置」，
  即上方上下文行末尾（或折行续行），不一定是该行最后一个反斜杠命令。
- `l.N` 可能是宏展开调用点，按行号改源码会改错位置；要结合 `->` 展开行回溯。

### 2. 数学模式族：`Missing $ inserted.` / `Double subscript.` / `Bad math environment delimiter.`

#### 2.1 `! Missing $ inserted.`

**日志特征**

```
! Missing $ inserted.
<inserted text>
                $
l.3 Text then x^
                2 math.
```

**根因（S7 归纳三类）**

1. 数学标记本身写错（如 `$y=f(x)$$`）；
2. 只能在数学模式使用的字符/命令出现在普通文本里：`_`（catcode 8 下标）、`^`（上标）、
   `$`，以及 `\alpha`、`\spadesuit` 这类符号命令；
3. 只能在数学模式外使用的原语出现在数学材料里：`\par`、`\vskip`、`\hrule`、`\unvbox`、
   `\unvcopy`、`\valign`，或公式中出现空行（空行转成 `\par`）。

S25 的实例是普通文本里写 `\spadesuit`：TeX 在该符号前插入一个 `$` 并重新扫描当前 token。

**可执行修法**

- 若是数学内容：用 `$...$` / `\(...\)` / `\[...\]` 或 `equation`/`align` 环境包起来；
- 若是文本里的字面字符：下划线写 `\_`，脱字符写 `\textasciicircum`，`$` 写 `\$`；
  URL 里的下划线交给 `\url`/`hyperref` 处理；
- 删除数学环境内的空行；不要在 `equation`/`align` 内部再套 `$`。

**工具作用域**：引擎无关；三类引擎行为一致。

**误诊风险**

- 消息名为「缺 `$`」，但第三类成因恰恰是「数学模式里混进了文本模式命令」，方向相反；
- TeX 插入 `$` 后的恢复会级联出后续错误（如 `Display math should end with $$.`），
  应修复第一条错误，不要逐条追下游报错（S7 背景章节给出了完整级联示例）。

#### 2.2 `! Double subscript.`

**日志特征**

```
! Double subscript.
l.3 $x_1_
         2$
```

**根因（S8）**：同一个基元上连续施加两个下标、且没有用花括号分组。`$a_b_c$` 无法判断
是 `x_{i_2}` 还是别的结构。

**可执行修法**：按数学意图加花括号分组：`$a_{b_c}$`（嵌套下标）、`${a_b}_c$`
（整体带下标）或 `$a_{bc}$`（并列下标）。

**特例（S8 转引 SE）**：带下标的重音原子（如 `{\vec a_b}_c`）即使有花括号也可能报错，
需要空组 `{}` 或 `accents` 宏包；该特例本轮未直接打开 SE 原帖核实。

**工具作用域**：数学模式内，引擎无关。

**误诊风险**：这不是「缺 `$`」，不要建议切引擎或补美元符；问题只在分组。

#### 2.3 `! Bad math environment delimiter.`

**根因（S14 内核源码）**：该错误由 `\@badmath` 发出，源码注释原文：

> "Called by `\[`, `\]`, `\(` or `\)` when used in wrong mode."

即分隔符命令在错误的模式被调用：已经在数学模式里又写 `\(`/`\[`，或数学模式未闭合就遇到
`\)`/`\]`，或 `$` 与 `\[`/`$$` 混用配对。S19 说明 `\( \) \[ \]` 本质是包裹 `$` 的
宏，自身带模式检查，因此会抛出这条 LaTeX 层错误。

**可执行修法**：成对检查分隔符；不要在 `equation`/`align` 内写 `$`；向上回溯第一条
未闭合的数学开启符。

**工具作用域**：引擎无关。

**误诊风险**：报错的分隔符命令本身常常没问题，根因在更早一条未闭合的 `$`/`\[`；
错误行可能是下游位置。

### 3. `! LaTeX Error: Missing \begin{document}.`

**日志特征**

```
! LaTeX Error: Missing \begin{document}.
l.2 S
     tray text before begin.
```

**根因（S14、S1、S24）**

- 内核源码 `\@nodocument` 注释原文："Error produced if paragraphs are typeset in the
  preamble." 导言区出现了被排版的内容。
- S1 列出的具体成因：导言区写了正文/牢骚文字；`\newsavebox` 后用 `\sbox` 等在导言区
  放入了内容；根本漏写 `\begin{document}`；编译错了文件；读取到上一轮遗留的 `.aux`
  文件（删除 `.aux` 从头再来）；有缺陷的类或宏包。
- S1 另列出不可见成因：`\documentclass` 之前被编辑器写入了内容；历史上 BOM（字节序标记）
  会让普通 LaTeX/pdfLaTeX 把它当成排版请求，日志形如 `l.1 <?>`，可用 `hexdump -C`
  查看开头是否为 `ef bb bf`。S1 同时指出："Fortunately XeTeX and LuaTeX know about
  BOMs and what to do with them, so LaTeX using them is 'safe'."
- S24：`\include` 出现在导言区会触发本条错误；而 `\includeonly` 只控制后续 `\include`
  哪些文件被读取，本身必须出现在导言区，**不会**产生本条错误。

**可执行修法**

1. 通读导言区，把误入的正文用 `%` 注释或移到 `\begin{document}` 之后；
2. 确认没有把正文放进 `\sbox`/盒子参数；3. 确认根文件确实有 `\begin{document}`，且当前
   编译的是根文件而不是被 `\input` 的子文件；4. 删除遗留 `.aux` 重跑；5. 检查文件开头
   不可见字节（BOM/不间断空格）。

**工具作用域**：LaTeX 层错误；BOM 的容忍度随引擎与版本不同（见误诊风险）。

**误诊风险**

- 不要把本条错误一律归因于 BOM：S1 列在最前面的成因是导言区正文、盒子内容、漏写
  `\begin{document}`、编译错文件、陈旧 `.aux`；BOM 只是不可见成因之一。
- `\includeonly` 不是本条错误的成因（S24）；现有 `no_output` 提示把它与「无输出」
  并列，语义需要区分。
- BOM 在新发行版上的行为本轮未从官方页面实测确认（见未覆盖项），建议作为末位假设。

### 4. `! LaTeX Error: Option clash for package xxx.`

**日志特征**

```
! LaTeX Error: Option clash for package graphicx.
```

**根因（S5、S2）**

- S5（usrguide）原文："The named package has been loaded twice with different options."
  交互模式敲 `h` 会给出两次加载各自的选项，并建议合并为
  `\usepackage[foo,baz]{fred}`。
- S2 规则：第一次加载确定选项集合，后续 `\usepackage`/`\RequirePackage` 的选项不能
  扩充该集合；即使选项 `b` 只是 `a` 的别名也会报错，LaTeX 不会进宏包内部核对。
- 包/类可以间接加载别的宏包，因此你可能只显式加载过一次，仍然撞选项冲突。

**可执行修法**

1. 先在导言区合并重复加载为一次，带上全部需要的选项；
2. 若冲突来自某个宏包间接加载目标宏包：在加载该宏包之前写
  `\PassOptionsToPackage{draft}{graphics}`；
3. 若冲突来自文档类加载：把 `\PassOptionsToPackage` 放到 `\documentclass` 之前（S2）；
4. 按日志括号嵌套顺序判断是谁先加载了目标宏包（S2 描述了日志中 `(<path>/foo.sty ...
  (<path>/graphics.sty ...) ...)` 的嵌套读法）。

**工具作用域**：LaTeX 宏包加载层，引擎无关。

**误诊风险**：报错点名的宏包不一定是肇事者；先加载它的可能是另一个宏包或文档类。
直接删掉第二次 `\usepackage` 会丢掉你需要的选项；正确做法是合并选项或用
`\PassOptionsToPackage` 预埋。

### 5. `! LaTeX Error: Something's wrong--perhaps a missing \item.`

**日志特征**

```
! LaTeX Error: Something's wrong--perhaps a missing \item.
l.5 \end{itemize}
```

**根因（S14、S3、S9）**

- 内核源码 `\@noitemerr` 注释原文："`\addvspace` or `\addpenalty` was called when not in
  vmode. Probably caused by a missing `\item`."
- 最常见：`itemize`/`enumerate`/`description` 里第一条内容前漏写 `\item`（S9）。
- 非常规成因（S3）：在 `tabular` 单元格里套 `enumerate` 来编号单元格（用法错误，应用
  计数器手工编号）；把 `alltt`/`itemize` 这类内部含「平凡列表」的环境放进
  `\fbox`/`\mbox`/`\framebox`/`\makebox` 参数（列表需要在段落模式之间发生，盒子参数里
  不成立）；`\fbox{\section{...}}` 这类用法。

**可执行修法**：列表每个条目开头补 `\item`；表格单元格改用 `\newcounter` + 手工编号；
盒子内的列表/verbatim 先套 `minipage` 再放入盒子。

**工具作用域**：LaTeX 层，引擎无关。

**误诊风险**：消息只说「缺 `\item`」，但盒子/表格嵌套里的同类报错不能靠补 `\item` 解决；
需检查列表所处的外层环境。

### 6. `! File ended while scanning use of \xxx.` / `Runaway argument?`

**日志特征**

```
Runaway argument?
! File ended while scanning use of \@argdef.
<inserted text>
                \par
<*> main.tex
```

或（无 `Runaway argument?` 前缀）：

```
! File ended while scanning use of \textbf .
```

**根因（S6）**

- `Runaway argument?` 通常由缺失闭花括号引起；紧接其后的行显示 TeX 吞读到哪里，
  这往往是定位错误的唯一线索（常无行号）。
- 两种子形态：`File ended while scanning use of \xxx` 是读到文件尾还没收齐参数；
  `Paragraph ended before \xxx was complete` 是不允许段落的命令参数里出现了空行。
- 内核/帮助层面的判断（S25 错误帧语义 + 通用恢复文本）：命令名在 `use of \xxx` 中，
  但出错位置可能在调用方传入的未闭合参数；`->` 行展示宏展开层次，最后一对行才是输入文件位置。

**可执行修法**

1. 以 `Runaway argument?` 后续行被吞掉的文本为地图，到编辑器里搜索这段文本定位开启位置；
2. 从该位置向后配对 `{ }` 与 `\begin/\end`；3. 检查是否在不允许段落的命令（如加粗、
   标题、上下标参数）里留了空行；4. 报错宏包命令（`\@argdef`、`\textbf`）本身往往没问题，
   问题在调用方参数未闭合。

**工具作用域**：引擎无关。

**误诊风险**：本条错误的行号不可信——它报告的是 TeX「耗尽空间」的位置，不是花括号开启的
位置（S6 明确指出该错误常无行号）；不要按 `l.N` 直接改那一行。

### 7. `! TeX capacity exceeded, sorry [ ... ]` 各括号子类型

**日志特征**

```
! TeX capacity exceeded, sorry [input stack size=5000].
\a ->\a
        \a
l.4 \a
```

**总体原则（S16）**：多数情况下无需扩大 TeX 容量；最常见成因是未配对花括号、超长行
（换行符在系统间传输损坏，特征是 `buf_size` 溢出）、写得很差的宏。真要调大参数，
web2c 系发行版改 `texmf.cnf`，改完需重新生成格式文件。

**各子类型成因（S22 标准错误帮助文本）**

| 括号内类型 | 典型成因 | 修法方向 |
| --- | --- | --- |
| `input stack size` | 命令定义出错，典型是自引用的循环定义（如 `\newcommand{\gnu}{a \gnu}`），TeX 追着自己的尾巴耗尽输入栈 | 找到并断开递归/循环宏定义；不要靠调大栈容量解决 |
| `main memory size` | (1) 定义了大量超长复杂命令；(2) 单页 `\index`/`\glossary` 过多；(3) 页面过于复杂（大 `tabbing/tabular/array/picture`，堆积的浮动体） | 减少命令/索引数量；在出错位置前插 `\clearpage` 验证是否为浮动体堆积；段落中间用 `\newpage`（`\pagebreak` 无效） |
| `pool size` | 交叉引用 `\label` 和/或命令名过多、名字过长；也可能是 `\setcounter`/`\newenvironment`/`\newtheorem` 参数漏了右花括号 | 缩短命名；先排查漏写的闭括号 |
| `save size` | 命令、环境、声明作用域嵌套过深 | 拆解深层嵌套结构 |
| `buffer size` | 章节标题、`\caption`、`\addcontentsline`、`\addtocontents` 的文本参数过长；常发生在处理 `\end{document}` 或目录/图表清单时 | 缩短可选参数（目录条目）文本 |
| `hash size` | 定义的命令名/使用的交叉引用标签过多 | 精简命令与标签数量 |

补充（S24）：把根文件自身 `\include` 进自己，首次报 `Can be used only in preamble`，
后续重跑会报 `TeX capacity exceeded, sorry [text input levels=15]`；除删除自包含外，
还要删掉 `root.aux` 再重跑。

**工具作用域**：引擎层错误；各引擎容量参数与配置文件不同。

**误诊风险**

- `input stack size` 几乎总是递归/循环定义，不是内存不够；盲目调高 `main_memory` /
  `extra_mem_top` 只会让递归晚一点爆掉（S16、S22）。
- 容量参数调整只对本机生效，合著者与投稿系统仍然会失败；应先修输入文件。
- 发行版命令不同：TeX Live 改 `texmf.cnf` 后 `mktexlsr`/重新生成格式；MiKTeX 走
  `initexmf` 配置；不能把两套命令混给用户。

### 8. `Missing character: There is no ... in font ...`

**日志特征**

```
Missing character: There is no ^^a3 in font cmr10!
Missing character: There is no 3 in font rsfs10!
```

**根因（S4）**：当前选中的字体里根本没有该字符的字形；这通常不是硬错误，要读日志才
发现。S4 举例：普通 LaTeX 文档里的 £、只有大写字母的 `rsfs10` 字体里的小写字母/数字。
OT1/T1 编码的 Adobe 标准字体缺字形时，dvips 侧还会报 `missing glyph` 警告或输出黑块。

**可执行修法**

- 换用包含该字形的字体；
- 8 位引擎（pdflatex）下可用 `\newunicodechar{字符}{LaTeX 写法}` 或
  `\DeclareUnicodeCharacter{编码}{...}` 做显式映射（S18）；
- CJK 字符在 pdflatex 默认字体下不属于「换个拉丁字体」能解决的范围（见第 9 族与未覆盖项）。

**工具作用域**

- pdflatex：受字体编码（OT1/T1）与字体字形覆盖双重限制；
- xelatex/lualatex：受当前 OpenType 字体字形覆盖限制，缺字形即当前字体不含该字。

**误诊风险**

- 加 `\usepackage[T1]{fontenc}` 只切换编码槽位，不会凭空造出字体缺少的字形；字体本身
  不含该字符时 T1 无济于事（S4）。
- `\newunicodechar` 只是把字符映射到已有的 LaTeX 命令/字形，同样不产生新字形；且在
  pdflatex 下要求 `inputenc` 为 `utf8`（S18）。
- Xe/Lua 下出现本警告，含义是「当前字体缺字形」，应换字体或配置回退，而不是换引擎。

### 9. `Unicode character ... (U+...) not set up for use with LaTeX`

**日志特征**

```
! LaTeX Error: Unicode character 中 (U+4E2D)
               not set up for use with LaTeX.
```

**根因（S15、S11、S18）**

- S15（ltnews30）：8 位引擎上大部分 ASCII 限制已放宽，但前提仍是「only those utf-8
  characters for which adequate font support is loaded」；字体支持不足时就会得到
  "the particular Unicode character is not set up for use with LATEX"。命令名仍
  只能用 ASCII 字母。
- S11：pdflatex 配合 `\usepackage[utf8]{inputenc}` 只能排版大部分带重音字母和部分
  符号；TeX 并不认识全部 UTF-8 字符；XeLaTeX/LuaLaTeX 原生支持 Unicode 输入。
- S18：`utf8` 选项的 `inputenc` 定义了许多但不是全部 Unicode 字符；未定义的字符可用
  `\newunicodechar`/`\DeclareUnicodeCharacter` 补映射。

**可执行修法（按引擎分流）**

- 维持 pdflatex：把该字符替换成等价 ASCII LaTeX 命令，或用 `\newunicodechar` 显式映射；
- 改用 XeLaTeX/LuaLaTeX：直接输入 Unicode，但仍需选对包含该字符的字体；
- 非 BMP 字符（如数学字母符号 𝛼、部分 emoji）：替换为等价 LaTeX 命令（S11）。

**工具作用域**：本条消息本身来自 8 位引擎的 `inputenc`/`u8` 层；Xe/Lua 不会抛出这条
原文，其同类失败是第 8 族的 `Missing character` 警告。

**误诊风险（与现有文案直接相关，见冲突点 C1）**

- 一律建议「改用 XeLaTeX/LuaLaTeX」并不总是对：必须留在 pdflatex 的工程里，正确出路是
  映射字符或替换命令；
- 反过来，Xe/Lua 下若出现同类排印失败，症结是字体缺字形，切引擎解决不了；
- `\ensuremath{\alpha}` 这类示例只适用于希腊字母/数学符号，不能推广到中文、emoji 等
  任意字符。

### 10. fontspec 字体找不到：`The font "..." cannot be found.`

**日志特征**

```
! Package fontspec Error: The font "NoSuchFontFamilyXYZ" cannot be found.
```

**根因与查找规则（S17）**

- fontspec 只服务 XeLaTeX / LuaLaTeX；字体可按「名字」或「文件名」选择，两种引擎查找
  规则有差异。
- 按名字：字体需位于标准字体目录（macOS `~/Library/Fonts`，Windows `C:\Windows\Fonts`）；
  LuaTeX 下 TEXMF 树中的字体也可按名加载；XeTeX 下 TEXMF 树中的字体在 Windows/Linux
  只能按文件名加载。
- LuaTeX 按名加载前可能需要先跑 `luaotfload-tool` 刷新字体数据库，否则首次排版会长时间
  停顿（S17）。
- 按文件名：带 `.otf/.ttf` 扩展名即按文件识别；不在默认搜索路径时用 `Path=` 指定目录。
- 可用 `\IfFontExistsTF{...}` 预先判断字体是否可加载（S17）。

**命令适用边界（S21、S13、S20）**

- S21：若字体已被办公软件等系统程序使用，XeTeX/LuaTeX 可直接取用，无需做 TeX 专用安装；
  为 pdflatex 准备 Type1/TFM 字体才需要本地 texmf 树 + 刷新文件名数据库 + 配置 map 文件。
- MiKTeX：手动把 TeX/LaTeX 文件装进用户管理的 TEXMF 目录后，必须刷新 FNDB（MiKTeX
  Console 的 Refresh FNDB，或命令行 `initexmf --update-fndb`）（S13、S21）；TeX Live
  对应 `mktexlsr`（`texhash` 同义）。
- map 文件更新是另一步：MiKTeX `initexmf --mkmaps`，TeX Live `updmap-sys`（S21）。

**可执行修法**

1. 核对字体名拼写与空格/大小写；2. 确认字体装在系统标准字体目录，或改用文件名 + `Path=`；
3. LuaTeX 刷新 `luaotfload` 名称缓存；4. 若是往 TEXMF 树手动放文件，刷新 FNDB；
5. 确认当前引擎是 Xe/Lua——pdflatex 不加载 fontspec。

**工具作用域**：xelatex / lualatex（fontspec）；pdflatex 走另一套 Type1/TFM 机制。

**误诊风险（见冲突点 C3）**

- `initexmf --update-fndb` 刷新的是 **TeX 文件名数据库**（`.sty/.tfm/.fd/.tex` 等发现
  路径），**不是**系统 OpenType 字体表/fontconfig 缓存；没安装的系统字族刷 FNDB 不会出现。
- `fc-list` 是 fontconfig 工具（Linux/macOS），原版 Windows 不带；不能对所有平台无条件
  给出这条命令。
- FNDB 刷新解决的是「文件不在 TeX 搜索路径」；fontspec 报「font cannot be found」更多是
  字体名/安装位置/引擎查找规则问题，两者不要混为一谈。

### 11. Reference / Citation undefined、`No file main.bbl.`、`Rerun to get cross-references right`

**流程事实（S10、S23、S12）**

标准 BibTeX 流程（S10 以 `main.tex` 为例）：

1. `pdflatex main`：`\cite` 暂时显示 `[?]`，引用键、文献样式、`.bib` 文件名写入 `main.aux`；
2. `bibtex main`：读 `.aux`，从 `.bib` 取条目，生成 `main.bbl`；
3. 第二次 `pdflatex main`：插入 `.bbl` 内容，文献列表出现，但文内引用可能仍是 `[?]`；
4. 第三次 `pdflatex main`：文内引用标号收敛。

S23（btxdoc）表述一致：先跑 LaTeX 产生 aux，再跑 BibTeX 产生 bbl，然后再跑两次 LaTeX；
极少数情况需要再加一轮。S12：LaTeX-Workshop 配方示例为
`pdflatex → bibtex → pdflatex → pdflatex`；biblatex 工程要在配方里选对 bib 后端
（`% !BIB program` 或工具配置），`outDir/auxDir` 不一致也会导致找不到辅助文件。

**各日志含义**

- `LaTeX Warning: Reference `x' ... undefined`：标签尚未被记录，或 `\label`/`\ref` 名不一致；
  先再跑一轮引擎，仍未定义再查拼写。
- `LaTeX Warning: Citation `key' ... undefined`：本轮读到的文献数据里没有该键。
- `No file main.bbl.`：本轮运行时 `.bbl` 尚不存在——BibTeX/Biber 还没成功跑过（或上一步
  失败了）；它本身不等于 `.bib` 缺失。
- `Rerun to get cross-references right`：`.aux` 中的页码/链接需要再跑一轮引擎收敛。

**可执行修法**

1. 交叉引用：核对 `\label`/`\ref` 拼写后重跑引擎；
2. 文献：核对 `.bib` 中 `@xxx{key,` 与 `\cite{key}` 一致 → 跑 bibtex/biber → 再跑引擎
  两次；3. 检查配方后端与 biblatex 声明一致；4. 确认 `.bib`/`.aux`/`.bbl` 在同一工作目录
  或正确搜索路径下。

**工具作用域**：pdflatex/xelatex/lualatex + bibtex/biber。

**误诊风险**

- 只跑一轮后仍 undefined，可能纯粹是轮次不够；但 `.blg` 已报「entry not found」时，
  再跑引擎不会修复键名不匹配。
- `No file main.bbl.` 是「文献工具未产出」的信号，应先看 bibtex/biber 是否成功执行，
  而不是直接判断 `.bib` 丢失。

### 12. BibTeX：`I couldn't open database file` / `I didn't find a database entry` / `A bad cross reference`

**12.1 `I couldn't open database file xxx.bib`**

**根因**：BibTeX 按 `.aux` 里的 `\bibdata{...}` 找不到数据库文件。S23 说明 BibTeX 对
找不到的样式文件用 `TEXINPUTS` 逻辑区、对数据库文件用 `TEXBIB` 逻辑区检索。

**可执行修法**：核对 `\bibliography{refs}`/`\bibdata` 中的文件名（按惯例不带 `.bib`
后缀）；确认 `.bib` 位于主文件同目录或 TeX 搜索路径（含 `TEXBIB`）；检查文件名大小写
与子目录路径。

**工具作用域**：BibTeX（`.blg`）；biber 的对应报错是 `ERROR - Cannot find database file!`
（本轮未打开 biber 手册核实原文，见未覆盖项）。

**误诊风险**：这是「数据库打不开」，与「条目找不到」修法不同；不要把路径问题当成键名
问题处理。

**12.2 `I didn't find a database entry for "key"`**

**根因**：本轮读取的数据库中没有与该引用键匹配的条目。常见三种：键名拼写不一致；
`.bib` 中该条目因更早的语法错误被跳过；BibTeX 读的是另一个 `.bib` 文件（S10 流程 +
既有排查经验；SE/论坛转引未直接打开）。

**可执行修法**：在 `.bib` 中搜索该键；先清掉 `.bib` 里更早的
`I'm skipping whatever remains of this entry` 语法错误；确认 `\bibliography` 指向的
就是你修改的那个文件。

**工具作用域**：BibTeX 警告（`Warning--I didn't find a database entry for "key"`）；
biber 对应 `WARN - I didn't find a database entry for 'key'`。

**误诊风险**：条目「找不到」可能是上游语法错误的连带结果；只改当前键而不看前面的
skipping 行，会反复修不好。

**12.3 `A bad cross reference`**

**根因（S23）**：`crossref` 字段指向的条目在数据库中不存在。btxdoc 说明 `crossref` 的值
是另一个条目的数据库键；被交叉引用的条目必须排在引用它的条目之后；`crossref` 嵌套本身
不可靠。

**可执行修法**：核对 `crossref = {xxx}` 中的 `xxx` 是否在同一 `.bib` 中存在；把被引用
条目放到数据库后部；不要嵌套 `crossref`。

**工具作用域**：BibTeX 标准样式机制；biblatex/biber 的继承字段机制另有手册规定。

**误诊风险**：这是条目间引用断裂，不是 `.bib` 文件打不开；方向不要搞反。

## 与现有 hints 的冲突点

> 对照文件：`src/pytexlogs/hints.py`、`src/pytexlogs/parsers/{latex,bibtex,biber}.py`。
> 以下只指出现有文案与本轮取证不一致或覆盖不足之处，不含改动建议的实现步骤。

- **C1（unicode 规则把「换引擎」写成默认出路）**：`_build_unicode` 文案为「pdflatex
  没有为字符配置字形：改用 XeLaTeX/LuaLaTeX，或替换成 ASCII LaTeX 命令」。取证结论：
  本条消息来自 8 位引擎 `inputenc`/`u8` 层（S15、S18）；必须留在 pdflatex 时，正确出路
  是映射字符或替换命令，切引擎并非首选；Xe/Lua 下同类失败是 `Missing character` 警告而
  非本条消息；示例 `\ensuremath{\alpha}` 只覆盖数学符号，不能推广到中文/emoji。
  现有规则也未区分「该消息只应出现在 8 位引擎」这一作用域。

- **C2（capacity 规则把子类型笼统归到 main_memory）**：`_build_capacity` 文案为「排查
  无限递归或超长表格；确属容量问题再调高 main_memory / extra_mem_top」，命令给的是
  `initexmf --edit-config-file=texmf.cfg` 与 `fmtutil-sys --all`。取证结论：括号内
  子类型决定根因——`input stack size` 是循环/递归宏定义（S22），`save size` 是作用域
  嵌套过深，`pool size` 是命名过长或漏闭括号，`buffer size` 是标题/目录参数过长，
  `main memory size` 才是长宏/索引/复杂页面（S22、S16）。现有文案把所有容量问题都引向
  main_memory；且 MiKTeX（`initexmf`）与 TeX Live（`fmtutil-sys`/`mktexlsr`）命令被
  并列给出，未按发行版分流。

- **C3（missing_font 命令无条件跨平台）**：`_build_font` 固定给出
  `fc-list | grep -i 'family'` 与 `initexmf --update-fndb`。取证结论：`fc-list` 属
  fontconfig（Linux/macOS），原版 Windows 不可用；`initexmf --update-fndb` 只刷新
  TeX 文件名数据库，不等于刷新系统字体表/fontconfig 缓存，未安装的系统字族刷 FNDB 不会
  出现（S13、S21、S17）。LuaTeX 按名加载还可能需要 `luaotfload-tool` 刷新，现有命令未
  覆盖。

- **C4（missing_glyph 中/非中分支的作用域偏差）**：CJK 分支建议「改用 XeLaTeX/LuaLaTeX
  并加载 ctex/xeCJK」；取证显示 Xe/Lua 下 `Missing character` 含义是当前 CJK 字体缺字形
  （应换字体/配回退），而非引擎选择问题（S4、S17）。非 CJK 分支建议 `\newunicodechar`，
  但该手段在 pdflatex 下要求 `inputenc=utf8`，且只是映射到已有 LaTeX 写法，不产生新字形
  （S18）。旧表 `Missing character` 条目还建议 `\usepackage[T1]{fontenc}`——T1 只改
  编码槽位，补不出字体本身缺的字形（S4）。

- **C5（missing_item 只考虑漏写 `\item`）**：`_build_missing_item` 文案为「列表环境里
  缺少 `\item`」。取证补充：列表套进 `\fbox/\mbox/\framebox/\makebox`、`enumerate` 套进
  `tabular` 单元格也会触发同一消息，补 `\item` 不能修复（S3、S14）。

- **C6（runaway 行号可信度提示不足）**：`_build_runaway` 文案「从报错行往前找最近未配对
  `{ }`」。取证结论：`Runaway argument`/`File ended while scanning` 的报告行是
  TeX 耗尽空间的位置，常无行号；真正的地图是 `Runaway argument?` 后续被吞掉的文本
  （S6）。另：规则元组已同时匹配 `Runaway argument` 与 `File ended while scanning`，
  但两种子形态（EOF 未收齐参数 vs 段落提前结束）现有文案未区分。

- **C7（math_mode 成因过窄）**：`_build_math_mode` 文案聚焦「漏写 `$`、`\text` 中特殊
  字符、`\ensuremath`」。取证结论还包括：数学模式外的符号命令/`_`/`^`、数学模式内的
  文本原语（`\par`/`\vskip`/空行）、数学环境内再写 `$`（S7）；且首条错误会引发级联，
  下游 `Display math should end with $$` 不应单独修（S7、S19）。

- **C8（Option clash 无专门规则）**：现有 `package_error` 正则要求 `Package X Error:`
  形式；而本条原文是 `LaTeX Error: Option clash for package graphicx.`，命不中专门规则，
  只能落到兜底。取证成因与修法见第 4 族（S5、S2）。

- **C9（Missing `\begin{document}`、Double subscript 无规则）**：round1 已标注缺口；
  本轮补充了成因细分与误诊边界（第 3、2.2 族）。其中 `\includeonly` 不应被列为本条错误
  成因（S24）。

- **C10（undefined_control 的命令名提取）**：现有实现取 `l.N` 行最后一个反斜杠命令。
  取证结论：未定义命令位于 TeX 停住位置（上方上下文行末尾），折行时在续行；宏展开场景
  下 `l.N` 指向调用点，上方 `->` 行才是展开层次（S25、S6）。提取逻辑需把续行与展开行
  纳入考虑，避免抓到已定义命令。

- **C11（no_output 中 `\includeonly` 的语义）**：现有 `no_output` 提示把
  `\includeonly` 与漏写 `\documentclass`/`\begin{document}` 并列。取证：`\includeonly`
  只选择哪些 `\include` 文件被读取，未列出的文件不排版，但保留其 `.aux` 交叉引用信息
  （S24）；它不是错误成因，而是「只编译部分章节」的正常配置。陈旧 `.aux` 引发的问题则应
  通过删除 `.aux` 重跑解决（S1、S24）。

- **C12（undefined_citation 未分流 bibtex/biber 与诊断层级）**：现有提示合并要求「检查
  `.bib` 键并确认 biber/biber 跑过」。取证：`.blg` 要先区分「打不开数据库」与「找不到
  条目」，后者还可能是上游语法错误连带跳过条目（第 12 族，S23、S10）；bibtex 与 biber
  消息措辞不同，工具作用域应标注。


## TeX Stack Exchange 浏览器取证（并入来源清单）

网络恢复后，`tex.stackexchange.com` 已可在内置浏览器中匿名只读访问；此前“robots 限制”的结论作废。
完整 17 个问题页与逐条结论见 `round2-texse-browser.md`，以下为进入本清单的关键来源：

| 编号 | 主题 | 页面标题（浏览器实际打开） | URL | 票数/采纳 | 可信度 |
| --- | --- | --- | --- | --- | --- |
| SE1 | Double subscript 的重音原子特例 | double subscript error | https://tex.stackexchange.com/questions/253080 | Q20 / A26 已采纳 | 高 |
| SE2 | 嵌套下标的分组写法 | nested subscripts | https://tex.stackexchange.com/questions/38100 | Q40 / 已采纳 | 高 |
| SE3 | biblatex 未定义引用与 .blg 三级诊断 | biblatex citation undefined | https://tex.stackexchange.com/questions/63852 | Q192 / A246 已采纳 | 高 |
| SE4 | pdflatex 缺 TFM（字体宏包） | Metric (TFM) file not found | https://tex.stackexchange.com/questions/75166 | Q159 / A125 已采纳 | 高 |
| SE5 | Option clash 与全局选项 | Option clash for package xcolor | https://tex.stackexchange.com/questions/83101 | Q176 / A198 已采纳 | 高 |
| SE6 | 容量子类型：main memory 与 pgfplots | TeX capacity exceeded, main memory size | https://tex.stackexchange.com/questions/7953 | Q175 / A116 已采纳 | 高 |
| SE7 | 容量子类型：input stack 递归（宏包链） | TeX capacity exceeded, input stack size=5000 | https://tex.stackexchange.com/questions/24247 | 已采纳 | 高 |
| SE8 | Missing `\begin{document}` 的导言区笔误 | Missing \begin{document} | https://tex.stackexchange.com/questions/29463 | 高票 | 中高 |
| SE9 | 文本模式中的 `^`/`_` 触发 Missing `$` | Missing $ inserted | https://tex.stackexchange.com/questions/24132 | 高票 | 中高 |
| SE10 | 多余右花括号 | Too many }'s | https://tex.stackexchange.com/questions/27042 | 高票 | 中高 |

关键原文短句（须与上表配套引用）：
- SE1：“when a subformula happens to only contain an ‘accent atom’ … the braces around this atom are stripped off”
- SE3：“If you are using biblatex you will not see a question mark, but instead you will see your citation key in bold.”
- SE4：“the missing file is `ecrm1000.tfm` according to the error message”
- SE5：“The package xcolor has already been loaded with options: [] There has now been an attempt to load it with options [table]”
- SE6：“that does not mean that expanding TeX's memory is the best solution. Instead … externalization … compile each plot as a separate TeX job.”
- SE7：input stack size 耗尽可来自宏包/样式链内的循环调用（如 hyperref 与书目样式），不只是自写宏递归。

## 未覆盖/不确定项

1. **TeX StackExchange：已改为浏览器直接核实**。17 个问题页由内置浏览器匿名只读打开（未登录、未投票、未发帖），来源见上表与 `round2-texse-browser.md`。**仍缺**：以 `Missing \right. inserted` 为标题的高票问答、biblatex `xref` 字段继承专门帖、biber 数据模型校验报错帖、引用键大小写敏感专门帖；这些主题的结论仍以手册原文为准，不用社区帖补。
2. **biber / biblatex 官方手册：已在第 2 轮补充核验**。网络恢复后，`biblatex.pdf` 与
   `biber.tex` 手册源码已重新抓取并对照原文，见
   `PyTeXLogs/docs/hints-research/round2-specialized.md` 的「手册重试结果（第 2 轮补充）」
   一节；`backend` 选项、`bibwarn`、编译流程、引用键大小写敏感、数据模型校验、
   crossref/xref 继承均有原文佐证。**仍未证实**：biber 侧
   `ERROR - Cannot find database file`、`No data sources defined` 等告警逐字文案；
   biber 手册未逐条罗列 WARN 消息，消息文本在 Perl 源码；`Duplicate entry key` 告警串
   未在手册中定位（仅「默认跳过重复键、`--noskipduplicates` 保留」行为已由 biblatex.pdf
   §3.8.1 证实）。
3. **xeCJK / ctex 主手册：已在第 2 轮补充核验**。`ctex.pdf`、`xeCJK.pdf` 已重新抓取并
   对照原文，见同上小节；引擎分支、fontset 平台探测、`fontset-unavailable` 紧急消息、
   AutoFallBack/多层后备、`missing-glyph` 消息模板均有原文佐证。**仍未证实**：
   fontspec.pdf 手册正文（包页/README/在线文档之外的「找不到字体」逐字建议）；第 8、9 族
   中其余依赖 fontspec 手册（S17）与 Overleaf 编码说明（S11）外推的 CJK 结论，保持原
   置信度。
4. **BOM 的版本相关行为未实测**：S1 记载历史上普通 LaTeX/pdfLaTeX 会被 BOM 卡住、
   Xe/Lua 可识别；较新发行版是否在所有引擎下都跳过 BOM，本轮未从官方页面实测确认。
   建议在提示文案中把 BOM 作为末位假设，而非首因。
5. **TeX Book 附录 / TeX by Topic 错误附录未直接抓取**：容量子类型描述依据标准 TeX 错误
   帮助文本镜像（S22，源自 plain TeX/LaTeX 交互帮助）与 TeX FAQ 源文件（S16）；未对照
   Knuth 原书页码。
6. **未覆盖的日志类别**：非 BMP 字符与 emoji、`nullfont` 缺字形级联、`No room for a
   new \dimen/\read/\write` 等寄存器耗尽、`Too many unprocessed floats` 的细分、
   MiKTeX 自动安装缺失宏包/字体的交互行为，本轮未取证。
7. **平台命令差异未穷举**：`fc-list`、`luaotfload-tool`、`mktexlsr`、`initexmf`、
   `updmap` 各属不同发行版/引擎，本轮只核实了 TUG 与 MiKTeX 官方页面记载的适用边界；
   Windows 下 fontconfig 的有无、WSL/双发行版共存场景未单独验证。
