# 第 1 轮：真实 LaTeX 编译日志样本（样本在 Linux TeX Live 环境采集；Windows 本机 TeX 环境系后续复核）

## 环境说明

> **环境前提更正（后续复核）**：本轮当时误判 Windows 工作站“无 TeX，`xelatex/pdflatex/lualatex/biber/bibtex/latexmk`
> 均不在 `PATH`、常见安装目录未命中”。实测本机装有 MiKTeX 26.5 Portable（bin：
> `C:\Applications\Scoop\apps\miktex\current\texmfs\install\miktex\bin\x64`），上述引擎均在 PATH，
> 后续已用本机真实日志复核。下列 Linux 采集记录为当时原始事实，日志样本与结论予以保留，未作改动。

- 采集环境（本轮原始记录）：另一台 Linux 云主机，TeX Live 自带 `xelatex/pdflatex/lualatex/bibtex`，未执行任何 `tlmgr install`，
  未修改任何 TeX 配置；仅编译临时目录下的探针文档。
- 下文每段都是真实日志原文（已删除内存统计等无关尾部）。

## 样本与现有 hint 覆盖情况

| 编号 | 触发源码 | 真实首条错误 | 现有规则 | 结论 |
| --- | --- | --- | --- | --- |
| c01 | `Hello \undefinedcmd world.` | `! Undefined control sequence.` | `undefined_control` | 覆盖，但命令名提取依赖 `l.N` 行 |
| c02 | `Text then x^2 math.` | `! Missing $ inserted.` | `math_mode` | 覆盖，文案过泛，未指出 `^`/`_` |
| c03 | `\usepackage{nosuchpkgxyz}` | ``! LaTeX Error: File `nosuchpkgxyz.sty' not found.`` | `missing_package` | 覆盖 |
| c05 | `\begin{document}` 前有正文 | `! LaTeX Error: Missing \begin{document}.` | **无** | 新增 |
| c06 | `\newcommand{\foo}[1]{#1` 未闭合 | `Runaway argument?` + `! File ended while scanning use of \@argdef.` | `runaway`（只认 `Runaway argument`） | 部分覆盖，`File ended...` 单独出现时漏 |
| c07 | `a & b & c` 三列 | `! Extra alignment tab has been changed to \cr.` | `alignment_tab` | 覆盖 |
| c08 | `\vspace{x}` | `! Missing number, treated as zero.` | `missing_number` | 覆盖，未提取 `x` |
| c09 | 顶层 `\end{itemize}` | `! LaTeX Error: \begin{document} ended by \end{itemize}.` | `end_mismatch` | 覆盖 |
| c10 | pdfLaTeX 直接写“中文测试” | `! LaTeX Error: Unicode character 中 (U+4E2D) not set up for use with LaTeX.` | `unicode` | 覆盖但**建议写死“改用 XeLaTeX”**，xelatex 下同样报错时给出错误建议 |
| c11 | 超宽 `\hbox` | `Overfull \hbox (243.09511pt too wide) detected at line 3` | `log_hint` | 覆盖 |
| c12 | `\ref{nosuchlabel}` | `LaTeX Warning: Reference `nosuchlabel' ... undefined` | `undefined_reference` | 覆盖 |
| c13 | `\cite{key1}` 未跑 bibtex | `LaTeX Warning: Citation `key1' ... undefined` + `No file main.bbl.` | `undefined_citation` | 覆盖，未利用 `No file main.bbl` |
| c14 | fontspec 指定不存在字体 | `! Package fontspec Error: The font "NoSuchFontFamilyXYZ" cannot be found.` | `package_error` | 兜底命中，但建议过于笼统 |
| c15 | `\def\a{\a\a}` 无限递归 | `! TeX capacity exceeded, sorry [input stack size=5000].` | `capacity` | 覆盖但建议写死 `main_memory`，与 `input stack size` 不符 |
| c16 | itemize 无 `\item` | `! LaTeX Error: Something's wrong--perhaps a missing \item.` | `missing_item`（匹配 `missing \item`） | 覆盖 |
| c17 | `$x_1_2$` | `! Double subscript.` | **无** | 新增 |
| c18 | `\textbf{unclosed` | `! File ended while scanning use of \textbf .` | **无**（`runaway` 只认 `Runaway argument`） | 新增匹配 |
| c19 | graphicx 选项冲突 | `! LaTeX Error: Option clash for package graphicx.` | **无**（`package_error` 要求 `Package X Error:`） | 新增 |

## 真实日志原文

### c01 Undefined control sequence

```
! Undefined control sequence.
l.3 Hello \undefinedcmd
                        world.
```

### c02 Missing $ inserted

```
! Missing $ inserted.
<inserted text>
                $
l.3 Text then x^
                2 math.
```

### c03 File not found (+ Emergency stop)

```
! LaTeX Error: File `nosuchpkgxyz.sty' not found.

Type X to quit or <RETURN> to proceed,
or enter new name. (Default extension: sty)

Enter file name:
! Emergency stop.
<read *>

l.3 \begin
```

### c05 Missing \begin{document}

```
! LaTeX Error: Missing \begin{document}.

See the LaTeX manual or LaTeX Companion for explanation.
Type  H <return>  for immediate help.
 ...

l.2 S
     tray text before begin.
```

### c06 File ended while scanning (macros)

```
Runaway argument?
! File ended while scanning use of \@argdef.
<inserted text>
                \par
<*> main.tex
```

### c07 Extra alignment tab

```
! Extra alignment tab has been changed to \cr.
<recently read> \endtemplate

l.4 a & b &
            c \\
```

### c08 Missing number

```
! Missing number, treated as zero.
<to be read again>
                   x
l.3 \vspace{x}
```

### c09 begin/end mismatch

```
! LaTeX Error: \begin{document} ended by \end{itemize}.

l.3 \end{itemize}
```

### c10 Unicode character not set up

```
! LaTeX Error: Unicode character 中 (U+4E2D)
               not set up for use with LaTeX.

l.3 中
        文测试
```

### c11 Overfull hbox

```
Overfull \hbox (243.09511pt too wide) detected at line 3
\OT1/cmr/m/n/10 AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
 []
```

### c12/c13 undefined ref/citation

```
LaTeX Warning: Reference `nosuchlabel' on page 1 undefined on input line 3.
LaTeX Warning: There were undefined references.
LaTeX Warning: Citation `key1' on page 1 undefined on input line 3.
No file main.bbl.
```

### c14 fontspec font not found

```
! Package fontspec Error: The font "NoSuchFontFamilyXYZ" cannot be found.

For immediate help type H <return>.
 ...

l.4 \begin
          {document}
```

### c15 capacity exceeded

```
! TeX capacity exceeded, sorry [input stack size=5000].
\a ->\a
        \a
l.4 \a
```

### c16 missing \item

```
! LaTeX Error: Something's wrong--perhaps a missing \item.

l.5 \end{itemize}
```

### c17 Double subscript

```
! Double subscript.
l.3 $x_1_
         2$
```

### c18 File ended while scanning use of \textbf

```
Runaway argument?
! File ended while scanning use of \textbf .
<inserted text>
                \par
<*> main.tex
```

### c19 Option clash

```
! LaTeX Error: Option clash for package graphicx.

l.4 \begin
          {document}
```

## 第 1 轮结论

1. 现有规则对“首条错误”覆盖尚可，但**建议内容与实际子类型不匹配**（unicode、capacity、fontspec）。
2. 明显缺口：`Missing \begin{document}`、`Double subscript`、`Option clash`、
   `File ended while scanning use of ...`（无 `Runaway argument` 前缀时）、
   `Missing character: There is no ... in font ...`（本批未触发，需 fixture）。
3. 真实日志里 `l.N` 行经常**换行折断**（`l.3 Text then x^` 下一行才是 `2 math.`），
   提取上下文时必须把 `l.N` 后两行一起看。

## 第二批真实日志（新增候选规则证据）

采集方式同上：Linux + TeX Live，临时目录，未安装任何包。

### e01/e02 XeLaTeX 缺字形（当前正则匹配失败）

```
Missing character: There is no ✓ (U+2713) in font [lmroman10-regular]:mapping=tex-text;!
Missing character: There is no 中 (U+4E2D) in font [lmroman10-regular]:mapping=tex-text;!
```

**关键**：真实 XeLaTeX 日志在字符与 `in font` 之间插入了 ` (U+2713)`，
现有 `_MISSING_CHAR_RE = Missing character:\\s+There is no\\s+(\\S+)\\s+in font`
因中间的 `(U+XXXX)` 而**匹配不到**，即缺字形规则在 XeLaTeX 日志上实际失效。

### e03/d14 字体 TFM 不可加载

```
! Font \\foo=NoSuchFont at 10.0pt not loadable: Metric (TFM) file not found.
! Font \\foo=NoSuchFont at 10.0pt not loadable: Metric (TFM) file or installed font not found.
```

现有 `_FONT_NOT_FOUND_RE` 只认 `not found|undefined`，`not loadable` 不匹配 → 无 hint。

### e05 hyperref PDF 字符串

```
Package hyperref Warning: Token not allowed in a PDF string (Unicode):
(hyperref)                removing `math shift' on input line 4.
(hyperref)                removing `superscript' on input line 4.
```

### e06 数学环境分隔符

```
! Display math should end with $$.
l.3 \\[ a $
         b \\]
! LaTeX Error: Bad math environment delimiter.
```

### e09/d06 多余右花括号

```
! Too many }'s.
l.3 \\section{a}}
You've closed more groups than you opened.
```

### e10 表格外 \\hline

```
! Misplaced \\noalign.
\\hline ->\\noalign
l.3 \\hline
```

### e11 \\left 缺 \\right

```
! Missing \\right. inserted.
l.3 $\\left[ x $
```

### d02 非法长度单位

```
! Illegal unit of measure (pt inserted).
<to be read again>
                   z
l.3 \\vspace{2zz}
```

### d05 命令重复定义

```
! LaTeX Error: Command \\foo already defined.
               Or name \\end... illegal, see p.192 of the manual.
```

### d12 段落开头 \\newline

```
! LaTeX Error: There's no line here to end.
```

### d09 空文档

```
No pages of output.
```

### 第二批结论

1. **缺字形正则在 XeLaTeX 真实日志上失效**，这是本轮最重要的实际缺陷（不是文案问题）。
2. `not loadable: Metric (TFM) file not found` 完全无提示。
3. 新增可高置信匹配（整句唯一、不会误报）：
   `Too many }'s`、`Misplaced \\noalign`、`Missing \\right. inserted`、
   `Illegal unit of measure (pt inserted)`、`Command \\foo already defined`、
   `There's no line here to end`、`No pages of output`（已有）、
   `Token not allowed in a PDF string`、`Bad math environment delimiter`。
