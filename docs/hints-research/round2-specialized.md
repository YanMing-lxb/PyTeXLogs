# 第 2 轮：BibTeX/Biber、CJK/字体、提示输出形态专项取证

## 范围与边界

- 本文件只做联网调研，对应切片：BibTeX/Biber 错误族、CJK/字体/Unicode、提示输出形态（JSON / SARIF / CSV / 终端）。
- 未修改任何 `.py` 源码，未执行 git commit，未改动 MiKTeX/TeX 配置，未安装 TeX 宏包。
- 调研前已读：`round1-real-logs.md`、`src/pytexlogs/hints.py`、`parsers/biber.py`、`parsers/bibtex.py`、`parsers/glossaries.py`、`parsers/xindy.py`。
- 口径：每条结论标注来源可信度；官方手册/规范 > 官方仓库 README 与 issue > 引擎 manpage > 社区教程。未能从官方来源核实的措辞，一律写入末尾「未检索到项」，不写成定论。

## 来源清单

| # | URL | 文档标题 | 可信度 | 取证要点 |
| --- | --- | --- | --- | --- |
| 1 | https://ctan.org/pkg/biber | CTAN: Package biber | 高（官方包页） | biber 定位为 BibLaTeX 的 BibTeX 替代后端；手册/issue/仓库入口 |
| 2 | https://ctan.org/pkg/biblatex | CTAN: Package BibLaTeX | 高（官方包页） | biblatex 后端可选 `biber`/`bibtex`/`bibtex8`；数据模型校验 |
| 3 | https://mirrors.ctan.org/macros/latex/contrib/biblatex/doc/biblatex.pdf | BibLaTeX 用户手册（CTAN 镜像） | 高（官方手册） | `crossref` 字段语义、`backend` 选项、`bibwarn`、编译顺序、inputenc/Unicode 限制 |
| 4 | https://tug.ctan.org/biblio/bibtex/contrib/doc/btxdoc.pdf | BibTeXing（btxdoc） | 高（官方用户手册） | crossref 继承规则、被引用条目在数据库中的先后顺序、字段/条目类型说明 |
| 5 | https://ctan.dcc.uchile.cl/biblio/bibtex/contrib/doc/btxFAQ.pdf | BibTeX Tips and FAQ（btxFAQ） | 中高（汇编，作者注明部分建议为观点） | 多 .bib 键名命名空间防撞、`-min-crossrefs`、括号/逗号/分号笔误触发错误、内存类报错 |
| 6 | https://raw.githubusercontent.com/plk/biber/dev/doc/biber.tex | Biber 手册源码（dev 分支） | 高（官方手册源文件） | 引用键与数据源键**大小写敏感**匹配；crossref/xref 继承；数据模型结构校验；远程数据源；日志样例 |
| 7 | https://github.com/plk/biber | plk/biber 仓库 README | 高（官方仓库） | biber 定位、环境变量、`--validate-datamodel`、文档与 issue 入口 |
| 8 | https://github.com/plk/biber/tree/dev/doc | biber 仓库 `doc/` 目录 | 高（官方仓库） | 手册仅 `biber.tex` 一个源文件；未发现按消息逐条解释的告警表 |
| 9 | https://github.com/plk/biber/tree/dev/lib/Biber | biber 仓库 `lib/Biber/` 目录 | 高（官方仓库） | 解析/数据模型/条目实现分布；消息文本定义在 Perl 源码中，手册未逐条罗列 |
| 10 | https://github.com/plk/biber/issues | plk/biber issue 列表 | 高（官方仓库跟踪器） | issue 以解析/排序/字段缺陷为主，未提供按告警消息分类的排查表 |
| 11 | https://github.com/plk/biber/issues/505 | Issue #505「pls include line number in warning message」 | 中（官方仓库内的增强讨论） | 部分 biber 告警**不带行号或条目键**；hint 不能假定每条告警都可定位到行 |
| 12 | https://manpages.ubuntu.com/manpages/jammy/man1/bibtex.original.1.html | web2c `bibtex(1)` manpage（Ubuntu jammy） | 高（发行版 manpage，源自 Web2C） | BibTeX 读 `.aux`；`.bib` 走 `BIBINPUTS`、`.bst` 走 `BSTINPUTS` 搜索路径；`-min-crossrefs` 默认 2 |
| 13 | https://www.overleaf.com/learn/latex/Bibliography_management_with_bibtex | Overleaf: Bibliography management with bibtex | 中（社区教程，事实性内容与手册一致） | 四轮编译顺序；键名大小写敏感；`.bib` 文件名/扩展名拼写；`%` 不是 .bib 注释符 |
| 14 | https://ctan.org/pkg/ctex | CTAN: Package CTeX | 高（官方包页） | ctex 同时支持 (pdf)LaTeX / XeLaTeX / LuaLaTeX；多引擎字体配置 |
| 15 | https://mirrors.ctan.org/language/chinese/ctex/ctex.pdf | CTEX 宏集手册 | 高（官方手册） | 引擎分支 `pdfTEX` / `upTEX` / `XeTeX-LuaTEX`；`fontset-unavailable` 紧急消息；按平台探测 windows/macos/fandol 字库 |
| 16 | https://ctan.org/pkg/xecjk | CTAN: Package xeCJK | 高（官方包页） | xeCJK **仅面向 XeLaTeX**；CJK/拉丁分离字体、标点压缩 |
| 17 | https://mirrors.ctan.org/macros/xetex/latex/xecjk/xeCJK.pdf | xeCJK 手册 | 高（官方手册） | `missing-glyph` 消息原文（CJKfamily 不含某字形，附 U+ 码位）；后备字体（FallBack）循环；默认 Fandol 字体 |
| 18 | https://ctan.org/pkg/fontspec | CTAN: Package Fontspec | 高（官方包页） | fontspec **仅用于 XeLaTeX 与 LuaLaTeX**；OpenType/AAT 字体统一接口 |
| 19 | https://github.com/latex3/fontspec | latex3/fontspec 仓库 README | 高（官方仓库） | 可按名字或文件名加载字体；`\setmainfont`/`\newfontfamily` 等命令；`texhash` 更新文件名数据库 |
| 20 | https://latex3.github.io/fontspec/ | fontspec 在线文档首页 | 高（官方站点） | 手册与命令摘要入口；XeTeX/LuaTeX（经 luaotfload）按名/文件直接加载 |
| 21 | https://ctan.org/pkg/luaotfload | CTAN: Package Luaotfload | 高（官方包页） | luaotfload **仅 LuaLaTeX**；ConTeXt 字体加载系统移植 |
| 22 | https://github.com/latex3/luaotfload | latex3/luaotfload 仓库 README | 高（官方仓库） | 通过元数据库按字体名（而非文件名）加载；LuaLaTeX 默认加载 |
| 23 | https://raw.githubusercontent.com/latex3/luaotfload/main/doc/luaotfload-tool.rst | `luaotfload-tool(1)` 手册源文件 | 高（官方 manpage 源） | `--update`/`--force` 重建库；`--find=NAME`/`--fuzzy` 查名；`--cache=purge|erase|show`；库文件位置 `texmf-var/luatex-cache/generic/names/` |
| 24 | https://texfaq.org/FAQ-misschar | TeX FAQ Q-misschar: Where have my characters gone? | 高（TeX FAQ） | `Missing character: There is no … in font …!` 是字体缺字形的日志告警，非致命错误；字体不含该字形 |
| 25 | https://texfaq.org/FAQ-unicode | TeX FAQ Q-unicode: Unicode and TeX | 高（TeX FAQ） | pdfTeX/旧 TeX 靠 inputenc 字节宏，覆盖限于标准编码；XeTeX/LuaTeX 原生 UTF-8 + TrueType/OpenType 字体表决定字形覆盖 |
| 26 | https://www.sharelatex.com/help/244-what-file-encodings-and-line-endings-should-i-use | Overleaf/ShareLaTeX 帮助：File encodings and line endings | 中（社区帮助） | pdfLaTeX 下 `inputenc Error: Unicode char … not set up`；XeLaTeX/LuaLaTeX 原生支持 Unicode；非 BMP 字符需改 LaTeX 命令 |
| 27 | https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html | OASIS SARIF 2.1.0 规范（OS 版） | 高（标准规范） | `result.ruleId` §3.27.5、`result.message` §3.27.11、`result.fixes` §3.27.30、property bag §3.8、`reportingDescriptor.helpUri` §3.49.12 / `help` §3.49.13、fix 链 §3.55/§3.56/§3.57 |
| 28 | https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/sarif-support-for-code-scanning | GitHub Docs: SARIF support for code scanning | 高（平台官方文档） | code scanning 实际读取的规则/结果字段；`ruleId`、`message.text`、`locations[]`、`help.markdown`、`properties.tags/precision/problem.severity` 等 |
| 29 | https://docs.astral.sh/ruff/rules/ | Ruff Rules 索引 | 高（工具官方文档） | 规则 = 代码（如 `FAST002`）+ slug 名 + 消息 + 修复/状态列；稳定/预览状态；「Automatic fix available」标记 |
| 30 | https://eslint.org/docs/latest/extend/custom-rules | ESLint: Custom Rules | 高（工具官方文档） | `context.id`；`report({messageId, data, loc, fix})`；消息集中存 `meta.messages`；`meta.fixable` 为可修复规则必备；每条消息一个修复 |
| 31 | https://doc.rust-lang.org/clippy/ | Clippy Documentation: Introduction | 高（工具官方文档） | lint 按命名空间分组（`clippy::correctness` 等），每组默认级别；800+ lint |
| 32 | https://doc.rust-lang.org/clippy/usage.html | Clippy Documentation: Usage | 高（工具官方文档） | `cargo clippy --fix` 自动应用部分建议；`-A/W/D clippy::lint_name` 级别配置 |

## BibTeX/Biber 对照表

> 说明：消息分两类后端。**biber** 日志前缀 `INFO - / WARN - / ERROR -`，键用单引号；**传统 BibTeX** 日志多为 `Warning--…` 或多行 `---line N of file …`，键用双引号。同一族问题两边措辞不同，hint 匹配必须按 `tool_name` 隔离（现状 `hints.py:_legacy_hint_table` 已如此做）。

| 日志特征（常见写法） | 出现后端 | 根因 | 推荐修法（取证结论） | 是否适用于 bibtex（非 biber） |
| --- | --- | --- | --- | --- |
| `WARN - I didn't find a database entry for '<key>' (section 0)` | biber | ① `.bib` 里没有该条目键；② 键名/大小写与 `\cite`/`\autocite` 不一致；③ 数据源没被 `\addbibresource` 加载；④ 该 section 的依赖条目未实例化 | 核对 `.bib` 中 `@type{key, …}` 与引用键**逐字符（含大小写）一致**；确认 biber 已成功运行；确认数据源已加载。biber 手册明确：引用键与数据源键的匹配是**大小写敏感**的，出现疑似大小写不匹配时 biber 会告警（来源 6） | 部分适用。传统 BibTeX 对应消息为 `Warning--I didn't find a database entry for "<key>"`，同类根因（缺条目/拼写/未跑 bibtex）；但 bibtex 不走 `.bcf` section 机制，无 `section N` 概念（来源 4、12、13） |
| `WARN - entry '<key>' has: …`（缺必填字段、字段重复、姓名尾逗号等数据校验类） | biber | 条目不符合 biblatex 数据模型：缺必填字段、同字段重复定义、姓名/日期/ISBN 等格式校验失败 | 按告警所列字段逐条改 `.bib`；可用 biber `--validate-datamodel` 做结构校验（来源 7）；biblatex 默认把后端数据告警转成 LaTeX 警告，可由 `bibwarn` 控制（来源 3） | 弱适用。BibTeX 只做很有限的检查（如 crossref 父条目缺 author/title 时的空字段警告，btxdoc 说明可忽略部分此类告警，来源 4）；没有等价的数据模型校验，不要把 biber 的校验告警口径套到 bibtex 输出上 |
| `WARN - Duplicate entry key: '<key>' in file '<file>.bib', skipping …` | biber（待核实措辞，见「未检索到项」） | 同一引用键在一个或多个 `.bib` 中定义两次；后一条被跳过，引用可能落到第一条上 | 合并/改名重复条目；多文件场景用带前缀的键名防命名空间冲突（btxFAQ Q5 建议唯一私有前缀，来源 5）；检查是否合并了合作者导出的重复库 | 概念适用，消息不同。传统 BibTeX 对重复键另有消息（第三方资料写作 `Repeated entry---line N of file …`），**该措辞本轮未从官方来源核实**，见「未检索到项」 |
| `A bad cross reference---entry "<child>" refers to entry "<parent>", which doesn't exist` | bibtex（biber 对应 crossref/xref 解析告警） | `crossref = {parent}` 指向的父条目不存在、未被加载，或键名拼错 | 确认父条目在被加载的 `.bib` 中存在且键名一致；biblatex/biber 下父条目可由子条目自动继承字段，嵌套 crossref 受支持（来源 3、6）。**传统 BibTeX 额外约束**：被 crossref 的条目必须排在引用它的条目之后，且不建议嵌套 crossref（btxdoc §2.1，来源 4） | 本条消息本身是 bibtex 运行时消息；biber 不再用 `A bad cross reference` 文案，而走数据模型/继承解析路径 |
| `I couldn't open database file <name>.bib ---line N of file <aux>: \bibdata{…}` | bibtex | `.bib` 文件找不到：文件名/扩展名拼写、路径不在主文件目录或 `BIBINPUTS` 搜索路径内、部分系统上大小写敏感 | 核对文件存在且路径相对主文件正确；`\bibliography{…}`/`\addbibresource{…}` 不带 `.bib` 扩展名；检查大小写；用 `kpsewhich <name>.bib` 验证可被搜索到（路径机制来源 12；文件名/大小写来源 13） | 即 bibtex 消息。biber 侧等价问题是数据源找不到/未定义，但消息前缀与措辞不同，未在本轮官方文档中逐字核实（见「未检索到项」） |
| `Illegal, another \bibdata command---line N of file <aux>: \bibdata: {…}` + `I'm skipping whatever remains of this command` | bibtex | 同一个 `.aux` 里写进了第二条 `\bibdata`（或 `\bibstyle`）：文档中多次调用 `\bibliography`/`\bibliographystyle`，或 chapterbib/multibib 场景下对主 `.aux` 而不是各章节 `.aux` 跑了 BibTeX | 单一文献列表只保留一组 `\bibliographystyle`+`\bibliography`；多文献列表改用 multibib/chapterbib 等宏包，并对对应的每个章节 `.aux` 分别运行 BibTeX，不要对主 `.aux` 重复运行。**注意**：该消息的逐条官方解释本轮未在手册中定位到，处置依据为 manpage 描述的单 aux 流程（来源 12）与 biblatex 对 `\bibliography` 的重定义（来源 3） | 即 bibtex 消息。biblatex/biber 走 `.bcf` 与 `\addbibresource`，不生成 `\bibdata`，不会出现此消息 |

### 补充取证结论

- 编译顺序：bibtex 链路为 `pdflatex → bibtex → pdflatex → pdflatex`；biblatex/biber 链路把第二步换成 biber（来源 13、3）。提示中「先跑后端再重跑两轮 LaTeX」的口径与之一致。
- biber 仓库 issue 跟踪器以解析缺陷、排序、字段处理为主，**没有按告警消息组织的官方排查表**（来源 10）；手册层面可引用的机制性依据是大小写敏感匹配、crossref/xref 继承、数据模型校验（来源 6、3）。
- btxFAQ 提醒：`.bib` 里 misplaced/omitted/extra braces、commas、semicolons 常触发后续一连串报错（来源 5）；与现有 hint「条目语法错误：缺逗号/括号不配对/字段名拼写」方向一致。

## CJK/字体三场景

> 关键边界（来源 14、16、18、21）：
> - **ctex**：跨引擎（pdfTeX / upTeX / XeTeX / LuaTeX），内部按引擎切换字库方案。
> - **xeCJK**：仅 XeLaTeX。
> - **fontspec**：仅 XeLaTeX / LuaLaTeX；pdfLaTeX 下不能用 fontspec 选 OpenType 字体。
> - **luaotfload**：仅 LuaLaTeX，是 fontspec 在 LuaTeX 侧的字体加载后端。

### 场景 1：pdfLaTeX + CJK / 非 ASCII 字符

- 典型日志：
  - `! LaTeX Error: Unicode character 中 (U+4E2D) not set up for use with LaTeX.`
  - `Package inputenc Error: Unicode char \u8:… not set up for use with LaTeX.`
- 官方解释：pdfTeX 属「旧式」引擎，Unicode 字节靠 inputenc 宏序列转成字体编码内的字形号，覆盖范围限于 LaTeX 标准编码能表达的字符（来源 25）；pdfLaTeX 下多数重音字母和部分符号可直排，但不是全部 UTF-8 字符都支持，不认识的字符即报未设置错误（来源 26）。
- 正确建议（按优先级）：
  1. 全文中文/非拉丁脚本：改用 **XeLaTeX 或 LuaLaTeX**，并加载 ctex（或 xeCJK，限 XeLaTeX）配置 CJK 字体；这是原生 Unicode 路径（来源 25、14、16）。
  2. 必须留在 pdfLaTeX：中文走 **CJK 宏包 / ctex 的 pdfTeX 模式**，不要把中文交给默认 OT1/T1 拉丁字体；个别符号改用等价 LaTeX 命令（来源 14、26）。
  3. 个别不支持的字符：替换为 LaTeX 命令；非 BMP 字符（如数学斜体字母 𝛼 U+1D6FC）无论引擎都建议改命令（来源 26）。
- 风险：若文档**已经**在 XeLaTeX/LuaLaTeX 下仍出现字符类告警，根因通常是字体缺字形，不应再给「改用 XeLaTeX」的建议（与 round1 c10 记录的口径风险一致）。

### 场景 2：XeLaTeX + 找不到字体 / 缺 CJK 字体

- 典型日志：
  - `! Package fontspec Error: The font "NoSuchFontFamilyXYZ" cannot be found.`
  - xeCJK：`CJKfamily '…' (…) does not contain glyph '…' ( U+… )`（手册原文，来源 17）。
- 官方解释：fontspec 在 XeTeX/LuaTeX 下可按字体名或文件名加载，无需手工安装 TFM 一类字体文件（来源 19、20）；字体名拼错、字体未安装、名族与系统安装名不一致时加载失败。
- 正确建议：
  1. 核对 fontspec/xeCJK 里写的字族名是否与系统实际安装名一致（可用 `fc-list` 查询）；必要时改用文件名方式加载（来源 19、18）。
  2. CJK 文档：用 ctex 按平台自动探测字库（windows / mac / fandol），或显式设置 CJK 字体；xeCJK 有 FallBack 后备字体机制，主字体缺字形时回退到后备字体，全部后备都缺才发 `missing-glyph` 告警（来源 15、17）。
  3. `missing-glyph` 是「当前字体族不含该字形」，先判断是整段中文没配 CJK 字体，还是个别特殊字符缺字形，再分别给建议（来源 17、24）。
- 注意：fontspec 报错只在 Xe/Lua 语境成立；pdfLaTeX 的缺文件/缺宏包错误不要套用字体建议。

### 场景 3：LuaLaTeX + 字体名数据库（缓存）故障

- 典型现象：字体按名加载失败，但文件本身存在；或新装字体后 LuaLaTeX 仍找不到。
- 官方解释：luaotfload 通过**索引字体元数据的数据库**支持按 proper name 而非文件名加载（来源 22）；数据库通常位于 `texmf-var/luatex-cache/generic/names/`，文件 `luaotfload-names.lua.gz`，另有 lookup 缓存，二者删除后下次 LuaTeX 运行会重建（来源 23）。
- 排查/修法（`luaotfload-tool`，来源 23）：
  - 查名字能否解析：`luaotfload-tool --find=FONTNAME`；`--fuzzy` 在查不到时给近似匹配。
  - 增量更新索引：`luaotfload-tool --update`；强制重建全部索引：`luaotfload-tool --force`。
  - 清缓存：`luaotfload-tool --cache=purge`（删 Lua 缓存）/ `--cache=erase`（删 Lua 与 Luc 缓存）/ `--cache=show`（看缓存统计）；`--flush-lookups` 清名字查找缓存。
- 边界：这是 **LuaLaTeX 专属**路径；XeLaTeX 走 fontconfig/系统字体枚举，没有同名 luaotfload 数据库概念，提示命令不能串场景。

### `Missing character: There is no <char> in font <font>!` 的归类

- TeX FAQ 定性：字体里没有该字符的字形，日志告警、不中断编译；常见于选错字体或字体编码与预期不符（来源 24）。
- 与场景 1 的区别：该告警说明**引擎已在排版**、字形层面缺字；`Unicode character … not set up` 是输入/编码层面引擎根本没配置该字符。两者修法不同，hint 应分流。
- 次级症状陷阱：`nullfont` 下的一串 `Missing character` 往往是前面致命错误后的连锁输出，根因要往更早的错误行找（round1 c15 同类教训）。

## SARIF/CLI 提示形态建议

> 目的：为 PyTeXLogs 的 hint 增加 `rule_id`、`help_uri`、`commands` 等字段提供规范依据。以下只给字段映射与组织方式建议，不涉及代码改动。

### SARIF 2.1.0 规范依据（带条款号）

| 拟新增概念 | SARIF 对应位置 | 规范要点（来源 27） |
| --- | --- | --- |
| `rule_id` | `result.ruleId`（§3.27.5）；规则元数据在 `toolComponent.rules[]` 的 `reportingDescriptor.id`（§3.19.23、§3.49.3） | ruleId 是**稳定、宜不透明**的层次化字符串；直接生产者 SHALL 输出 `ruleId` 或 `rule.id`，两者同时出现 SHALL 相等；转换器可从其他信息合成 ruleId。现有 `RULE_IDS`（如 `missing_package`）天然对应这一层 |
| 说明文字（中/英） | `result.message`（§3.27.11，message 对象 §3.11）；`message.text`（§3.11.8）、`message.markdown`（§3.11.9） | message **SHALL** 存在；SHOULD 包含定位信息、触发条件、不修的风险、可行处理范围（含「可判定为误报」的条件）。markdown 存在时 text **SHALL** 同时存在，保证纯文本上下文可读。现有 `text` / `text_en` 可对应 text 与（可选）markdown/另一语言消息串 |
| `help_uri` | `reportingDescriptor.helpUri`（§3.49.12）；规则帮助正文 `reportingDescriptor.help`（§3.49.13） | helpUri 指向规则文档的绝对 URI；help 为 message 对象，放规则级长期说明（区别于 result.message 的单次告警描述）。规则级信息放 descriptor，结果级信息放 result |
| 自定义扩展字段（含 `commands`） | property bag（§3.8）：每个对象 MAY 含 `properties` | 未在标准中定义的信息放 `properties`，键名层次化、SHOULD camelCase；值可为任意 JSON 类型。`commands`（可执行命令模板）属工具自定义数据，应放 `properties.commands`，而不是塞进标准字段 |
| 可执行修复 | `result.fixes`（§3.27.30）→ `fix`（§3.55）→ `artifactChanges`（§3.55.3）→ `artifactChange`（§3.56：`artifactLocation` §3.56.2、`replacements` §3.56.3）→ `replacement`（§3.57：`deletedRegion` §3.57.3、`insertedContent` §3.57.4） | fixes 是**源码级精确替换**模型（删除区域 + 插入内容）。PyTeXLogs 现有 `commands` 多为终端命令/TeX 导言建议，不是对源码区域的替换；除非未来能定位到精确源码区间，否则不要硬套 fixes 结构 |
| 级别 | `result.level`（§3.27.10）；规则默认级别 `reportingDescriptor.defaultConfiguration.level`（§3.49.14） | 取值 `error` / `warning` / `note` / `none`；结果级别可覆盖规则默认级别。可对应现有 LogLevel 的 error/warning/info 映射 |

### GitHub Code Scanning 对 SARIF 的字段要求（来源 28）

- 规则对象（`rules[]` / reportingDescriptor）：
  - `id`：规则唯一标识，其他部分引用，用于在 GitHub 上生成规则链接。
  - `name`：规则名，供按规则过滤（≤255 字符）。
  - `shortDescription.text`：简短描述，结果旁展示（≤1024 字符）。
  - `fullDescription.text`：完整描述（≤1024 字符）。
  - `defaultConfiguration.level`：规则默认严重级别（note/warning/error，默认 warning）。
  - `help.text` / `help.markdown`：规则文档；**有 markdown 时优先展示 markdown**。
  - `properties.tags[]`：过滤标签；`properties.precision`（very-high/high/medium/low，反映真阳性率）；`properties.problem.severity`（error/warning/recommendation）；安全规则用 `properties.security-severity`（0.1–10.0）。
- 结果对象（`results[]`）：
  - `ruleId`、`ruleIndex`、`rule`：关联到规则。
  - `level`：覆盖规则默认级别。
  - `message.text`：结果标题；空间受限时只显示第一句。
  - `locations[]`：**至少一个**位置才会展示结果；GitHub 只用数组第一项做文件标注。
  - `partialFingerprints.primaryLocationLineHash`：跨提交/分支追踪同一告警。
  - `relatedLocations[]`：消息内嵌链接跳转的相关位置。
- 注意：GitHub 文档明确「其余未列出的支持字段会被忽略」；`fixes` 未列入本轮访问到的展示字段，不要假设 fixes 会在 code scanning 界面渲染。

### 常见 linter 的规则组织方式（可借鉴的 3 条）

1. **稳定规则代码 + 人读 slug + 消息 + 修复状态分离**（Ruff，来源 29）
   - 每条规则四列：规则代码（前缀+编号，如 `FAST002`）、slug 名（`fast-api-non-annotated-dependency`）、消息模板、修复/状态列。
   - 修复能力独立成标记（「Automatic fix available」），另标稳定/预览状态。
   - 借鉴：PyTeXLogs 的 `rule_id` 用稳定短码，`kind`/类别与可修复能力分开标记；消息模板与规则元数据分存，便于快照测试与国际化。

2. **消息 ID 集中管理 + 占位符数据 + 可选修复函数**（ESLint，来源 30）
   - 报告时 `report({messageId, data, loc, fix})`；文案集中在 `meta.messages`，用 `{{placeholder}}` 占位、`data` 填值，避免规则文件与测试里重复写文案。
   - 可修复规则必须声明 `meta.fixable`；`fix(fixer)` 只返回小范围、不改变运行时行为的修复；**一条消息只给一个修复**；修复后会重跑规则。
   - 借鉴：hint 的中英文案可按 messageId 集中登记；`commands` 数组对应「可选修复建议」，并显式区分「可自动执行」与「仅人工参考」；命令模板保留占位符（`<jobname>` 等）由上下文填充。

3. **命名空间分组 + 分组默认级别 + 批量修复入口**（Clippy，来源 31、32）
   - lint 以 `clippy::<group>::<name>` 命名空间组织（correctness / suspicious / style / complexity / perf / pedantic / restriction / nursery / cargo），每组有默认级别（deny/warn/allow）。
   - 用户按组或单条调整 `-A/W/D`；`cargo clippy --fix` 只自动应用部分建议。
   - 借鉴：规则可按族分组（如 `bibtex` / `biber` / `font` / `unicode` / `math`），组级默认严重级别，单条结果可覆盖；自动修复要标注适用范围，不承诺全部建议可机器执行。

### 对字段设计的落地建议（调研结论，非实现）

- `rule_id`：稳定、不透明、层次化；与现有 `RULE_IDS` 一一对应，不随文案修改而变。
- `help_uri`：规则级长期文档链接（手册章节/FAQ 条目），挂在规则描述符上；结果消息里只放单次说明。
- `commands`：放 property bag 式自定义字段；每条命令标注是否可自动执行、适用后端（tex/bibtex/biber/xelatex/lualatex）。
- 文案：`text` 必填，`text_en`/markdown 可选；消息中保留定位键（文件名、行号、条目键、字符码位），并写明「什么情况下可视为误报/可忽略」。
- 级别：error/warning/note 映射现有 LogLevel；次级连锁告警（nullfont 缺字形等）降为 note/warning，避免掩盖首条错误。

## 风险与误报

1. **后端措辞串场景**：biber 的 `WARN -`/单引号与 bibtex 的 `Warning--`/双引号、多行 `---line N` 结构不同；跨工具套用匹配会误命中。现有按 `tool_name` 隔离旧表的做法应保留。
2. **biber 告警可能缺位置信息**：issue #505 说明部分 biber 告警不带行号/条目键（来源 11）；解析器不应把「无行号」推断成「全局问题」，hint 也不要编造行号。
3. **缺字形可能是次级症状**：`nullfont` 或致命错误后的一串 `Missing character` 不是字体根因；应提示回溯到更早的首条错误。
4. **Unicode 告警的引擎前提**：`not set up` 建议「换 Xe/Lua」只在 pdfLaTeX 语境成立；引擎已为 Xe/Lua 时应走缺字体/缺字形分支（round1 c10 已记录此风险）。
5. **字体命令的引擎边界**：fontspec/xeCJK/luaotfload 各有适用引擎；`fc-list`、`luaotfload-tool` 等命令不能跨引擎给建议。
6. **重复键措辞部分核实**：重复键行为已由 biblatex.pdf §3.8.1 佐证（biber 默认跳过后续重复条目，`--noskipduplicates` 可保留），但告警逐字串 `Duplicate entry key` 未在手册中定位（见下）；规则匹配应保持宽松子串，不依赖逐字文案断言后端。
7. **crossref 两套语义**：传统 BibTeX 有父条目排序与不可靠嵌套约束；biber/biblatex 支持嵌套继承。给 crossref 建议时要区分后端。
8. **SARIF/GitHub 展示落差**：标准 `fixes` 是源码替换模型，GitHub code scanning 本轮文档未列入 fixes 展示支持；自定义 `properties` 字段在平台侧可能被忽略，导出 CSV/终端时才是一等公民。
9. **CJK 字符区间判定**：按 Unicode 区块猜 CJK 可能误伤全角标点、兼容表意文字等边界；判定结果应作为提示而非定论。
10. **社区教程事实性**：Overleaf/ShareLaTeX 帮助用于补充操作流程，根因解释以手册/FAQ/manpage 为准；冲突时以后者为准。

## 未检索到项

- **bibtex.web 运行时消息的官方逐条解释**：`A bad cross reference`、`I couldn't open database file`、`Illegal, another \bibdata command`、`I'm skipping whatever remains of this entry/command` 等消息源自 BibTeX/Web2C 程序源码（`bibtex.web`），本轮未获取该源码；CTAN 的 btxdoc/btxFAQ、biblatex.pdf、biber 手册均未按这些消息逐条列官方释义。对照表中的根因/修法系结合 manpage 流程、手册机制描述与社区教程交叉推断，置信度已在表中标注。
- **biber「Duplicate entry key」告警逐字串未核实（行为已核实）**：biblatex.pdf §3.8.1 已证实重复条目键行为——"by default biber will ignore further occurrence of entrykeys unless its --noskipduplicates options is used"；但 `biber.tex` 手册源码本地 grep 未命中 `Duplicate entry`/`database entry` 等告警串，biber 手册不逐条罗列 WARN 消息，消息文本在 Perl 源码（`lib/Biber/...`）。传统 BibTeX 重复条目的消息文案同理未核实。
- **fontspec.pdf 手册正文**：本轮重试范围不含 fontspec；两个 CTAN 镜像的 PDF 仍被 robots.txt 拒绝或链接抓取失败；fontspec 的能力边界与命令依据来自 CTAN 包页、仓库 README 与在线文档首页，手册正文内「找不到字体」一节的逐字建议未读到。
- **论坛级复现证据**：latex.org / latex-community 论坛页面本轮不可访问（site not supported / link dead）；multibib、chapterbib 与「another \bibdata command」的复现/处置讨论未取得可引用的访问页面。
- **biber 数据源找不到的等价消息**：biber 侧 `Cannot find <database file>` / `No data sources defined` 等写法来自未访问的第三方教程页面，未在官方文档中逐字核实，对照表中未展开。
- **luaotfload.conf 配置手册**：仅访问到 `luaotfload-tool(1)` manpage 源文件；`luaotfload.conf(5)` 的 `update-live`、`scan-local` 等配置项未读取，缓存自动重载行为以 manpage 命令选项为准。
- **SARIF 校验器与附录 D 转换器约定**：GitHub 文档提及 Microsoft SARIF validator，本轮未访问校验器站点；附录 D（转换器合成 ruleId 的约定）未展开取证。

## 手册重试结果（第 2 轮补充）

> 补充取证日期：2026-11-21。网络恢复后对四份一手手册定向重试；本节引文均为手册原文（英文/中文照录，未转述）。抓取渠道分开记录：`web_fetch` 为调研工具读取正文，本地直连为本 agent 在本机用 `Invoke-WebRequest` 探测的 HTTP 状态，Organizer 复核为主智能体独立抓取。两者结果不一致时如实分列，不合并为假结论。

### 抓取结果

| URL | 抓取结果（web_fetch / 本地直连 / Organizer 复核） | 实际标题 | 读取到的章节或位置 |
| --- | --- | --- | --- |
| https://mirrors.ctan.org/macros/latex/contrib/biblatex/doc/biblatex.pdf | web_fetch 成功（正文已读）；本地直连 GET **200**，1,744,449 字节；Organizer 复核成功 | BibLaTeX 用户手册 | §3.1.1 Load-time Options（`backend`、`bibwarn`）、§3.8.1 Resources（`\addbibresource`）、§2 数据模型、文献处理流程 1–3 步 |
| https://raw.githubusercontent.com/plk/biber/dev/doc/biber.tex | web_fetch 成功；本地直连 GET **200**，144,169 字节，已落盘本地 grep 复核；Organizer 复核成功 | biber 手册 LaTeX 源码（dev 分支） | 变更记录 §0.9.6/0.9.8/1.0/1.9、功能概述、兼容矩阵、数据模型、inheritance 配置、§5 代码实现对照 |
| https://mirrors.ctan.org/language/chinese/ctex/ctex.pdf | web_fetch 成功（正文已读）；本地直连首次 SSL 握手失败，重试 **200**，1,426,774 字节；备选镜像 `tug.ctan.org` 同路径 **200**；Organizer 复核成功 | 《CTEX 宏集手册》 | §4.1 编译方式（表 2）、§4.3 中文字库（表 3 自动配置字体策略）、`fontset` 选项说明、第 14 节代码实现（`\ctex_fontset_error:n`） |
| https://mirrors.ctan.org/macros/xetex/latex/xecjk/xeCJK.pdf | web_fetch 成功（正文已读）；本地直连一次 **200**，1,453,533 字节，两次间歇性 SSL 握手失败；Organizer 复核成功 | xeCJK 宏包 v3.9.1（2022/08/05，ctex-kit rev. c4ccfae） | §1 简介、§3.1 宏包选项（`AutoFallBack`、`LoadFandol`）、§3.2 字体设置与选择（`\setCJKfallbackfamilyfont`、`FallBack`）、§5.11 后备字体代码实现 |
| https://mirrors.ctan.org/macros/xetex/latex/xeCJK/xeCJK.pdf | 本地直连 **404 Not Found**（目录大小写错误）；web_fetch 未采用此路径 | — | CTAN 规范目录名为小写 `xecjk`，见上一行 |

### 逐条补证

#### A. biber（`biber.tex`，dev 分支）

- **A1 手册是否逐条解释 `WARN -` 消息：否。** 对落盘的 `biber.tex`（144,169 字节）本地 grep，未命中 `database entry`、`Duplicate entry`、`didn't find`、`doesn't exist` 等告警串；手册只有总体性 "it will warn you" 表述与变更记录中的「Summary of warnings/errors is now a new format」一条。**结论：手册未逐条罗列 WARN 消息，消息文本在 Perl 源码（`lib/Biber/...`）；hint 文案不能引用手册作为逐条告警释义来源。**
- **A2 引用键匹配大小写敏感：成立。** 原文（`biber.tex` L195–203，变更记录 §0.9.6）：

  > "Matching of citation keys and datasource entry keys is now **case-sensitive**. This is to enforce consistency across the entire biblatex and biber processing chain. All of the usual referencing mechanisms in latex are case-sensitive and so is the matching in biblatex of citations to entries in the `.bbl` file generated by biber. … If biber detects what looks like a case mismatch between citation keys, it will warn you."

  边界（biblatex.pdf 数据模型一节）："while the biber/BibTeX input site is not case sensitive when it comes to entry types and field names (Perl's Unicode case folding is used to normalise field names and entry types), the LaTeX side is case sensitive and uses the exact capitalisation from the data model." 即**条目类型名、字段名输入端不区分大小写；只有引用键 ↔ 数据源条目键匹配区分大小写**。
- **A3 crossref/xref 继承与提升：成立。** 原文 L370–374：

  > "«Semantic» inheritance via a generalisation of the BibTeX crossreference mechanism. This is highly customisable by the user … Nested crossreferences are also supported."

  原文 L459–463：

  > "Entries instantiated by being mentioned as a CROSSREF are promoted to cited status if CROSSREF'ed at least mincrossrefs times, and entries mentioned as an XREF if XREF'ed at least minxrefs times. The two are counted separately."

- **A4 数据模型校验与 `--validate-datamodel`：成立。** 原文 L130–135：

  > "Fields which are not defined in the data model described in the default `biber-tool.conf` are ignored and are neither read nor output. … If you would like to have ignored fields reported on, use the `--validate-datamodel` option."

  原文 L153（§1.8 选项更名）："The `--validate-structure` option is now called `--validate-datamodel`。" 另 L2847："`--validate-datamodel` which, among other things, will use the module `Business::ISBN` to validate ISBNs."
- **A5 重复条目键：行为已证实，告警逐字串未证实。** biblatex.pdf §3.8.1 原文：

  > "If the resources contain duplicate entries (that is, duplicate entrykeys), it is backend dependent what then happens. For example, by default biber will ignore further occurrence of entrykeys unless its --noskipduplicates options is used."

  `biber.tex` 中未出现 `Duplicate entry key` 字样；该告警逐字文案仍属未检索到项。

#### B. biblatex（`biblatex.pdf`）

- **B1 `backend` 选项：成立。** §3.1.1 原文：

  > "backend=bibtex, bibtex8, biber — default: biber. Specifies the database backend. … biber, the default backend of biblatex, supports us-ascii, 8bit encodings, utf-8, on-the-fly reencoding, locale-specific sorting … bibtex — Legacy BibTeX. Traditional BibTeX supports us-ascii encoding only. Sorting is always case-insensitive."

- **B2 `bibwarn` 行为：成立。** §3.1.1 原文：

  > "bibwarn=true, false — default: true. By default, biblatex will report warnings issued by the backend concerning the data in the bib file as LaTeX warnings. Use this option to suppress such warnings."

- **B3 编译顺序：成立。** 文献处理流程原文："1. Run latex … 2. Run biber … 3. Run latex"；bbl 像 aux 一样在第二轮运行开头读入内存。biblatex 流程在导言区用 `\addbibresource` 声明数据源，`.bcf` 替代 `.aux` 中的 `\bibstyle`/`\bibdata`；`\bibliography`/`\bibliographystyle` 属传统流程。
- **B4 资源扩展名规则：成立，但要分流。** §3.8.1 原文：

  > "`\addbibresource[⟨options⟩]{⟨resource⟩}` Adds a resource, such as a .bib file, to the default resource list. This command is only available in the preamble. It replaces the `\bibliography` legacy command. Note that files must be specified with their full name, including the extension."

  即 **biblatex/biber 的 `\addbibresource` 要写 `.bib` 扩展名**；传统 BibTeX 流程的 `\bibliography{refs}` 按惯例不带扩展名。两类提示不可混用。
- **B5 大小写边界**：见 A2 引文（输入端条目类型/字段名不区分大小写，LaTeX 侧区分大小写）。

#### C. ctex（`ctex.pdf`）

- **C1 引擎分支：成立。** §4.1 原文："CTEX 宏集支持 ETEX、pdfTEX、XeTEX、LuaETEX、upETEX 等多种不同的编译方式, 并为它们提供了统一的界面。" 表 2 中文支持方式：`(pdf)LATEX` → CJK；`XeLATEX` → xeCJK；`LuaLATEX` → LuaTeX-ja；`upLATEX` → 原生。
- **C2 `fontset` 选项与平台探测：成立。** 选项原文：

  > "fontset = ⟨adobe|fandol|founder|mac|macnew|macold|ubuntu|windows|none|...⟩ 指定 CTEX 宏集加载的字库。如果没有指定 fontset 的值, CTEX 宏集将自动检测用户使用的操作系统, 配置相应的字体(参见表 3)。"

  表 3 与代码实现 `\ctex_detect_platform:`：Windows → `windows`；macOS → `mac`；其他系统 → `fandol`。
- **C3 各 fontset 的引擎支持边界：成立。** 手册标注 `adobe`/`fandol`/`mac`/`ubuntu` **不支持 pdfLATEX**；`windows`、`founder` 可在 pdfLATEX 下走 CJK + zhmetrics。
- **C4 fontset 不可用时的用户可见行为：成立，定性为「当前引擎模式不支持」。** 第 14 节代码实现原文："`\ctex_fontset_error:n` 字库不可用时给出紧急错误信息,停止读取定义文件。" 消息定义源码：

  > `\msg_critical:nnn { ctex } { fontset-unavailable } {#1}`
  > `"CTeX~fontset~`#1'~is~unavailable~in~current~mode."`

  判定：这是 **critical 紧急错误，停止读取定义文件**；触发条件是所选 fontset 在当前编译方式下不可用，**不等于系统里没装字体文件**。

#### D. xeCJK（`xeCJK.pdf`）

- **D1 仅 XeLaTeX：成立。** §1 原文："xeCJK 是一个XeLATEX 宏包,用于排版中日韩(CJK)文字。" "xeCJK 使用了XƎTEX 的一些最新特性,需要XƎTEX 0.9995.0 (2009/06/29) 以后的版本。" "xeCJK 还需要通过fontspec 宏包来调用系统字体。"
- **D2 `missing-glyph` 消息模板：成立。** §5 代码实现原文：

  > `\__xeCJK_msg_new:nn { missing-glyph }`
  > `CJKfamily~`#2'~(#1)~ does~not~contain~glyph~`#3'~ ( U + \int_to_Hex:n { `#3 } )~\msg_line_context:.`

  对应日志形态：`CJKfamily '<family>' (<engine>) does not contain glyph '<char>' ( U+<hex> )`。
- **D3 FallBack 兜底机制：成立（带机制前提）。** §5.11 后备字体：
  - `\__xeCJK_fallback_symbol:NN`："测试当前字体中是否存在当前字符,如存在则直接输出,否则启用后备字体。"
  - `\__xeCJK_fallback_loop:nnNN`："循环测试后备字体是否包含字符。若后备字体中存在该字符或者再没有后备字体,则结束循环。当前字体族没有备用字体时,使用 `\CJKfamilydefault` 的设置。"
  - `\setCJKfallbackfamilyfont {⟨family⟩} {⟨font name⟩}` 或主字体声明中的 `FallBack=` 选项设备用字体，支持多层后备（手册例 12：KaiTi_GB2312 → SimSun → SimSun-ExtB）。
  - 判定：`missing-glyph` 是**后备字体链全部耗尽之后**才发出的告警；含义为当前 CJKfamily 及其后备均不含该字形。
- **D4 默认行为：** `AutoFallBack .default:n = { true }`（后备字体机制默认开启）；`LoadFandol` 控制导言区未声明 CJK 字体时是否回退 Fandol。

### 四点判定（直接影响 hint 文案）

| 判定项 | 结论 | 依据与边界 |
| --- | --- | --- |
| biber 引用键是否大小写敏感 | **成立** | `biber.tex` L195–203 原文；仅作用于引用键 ↔ 数据源条目键。条目类型名/字段名输入端不区分大小写（biblatex.pdf 数据模型节），不要把大小写敏感结论推广到字段名 |
| xeCJK `missing-glyph` 是否表示「当前字体族缺字形、可由 FallBack 兜底」 | **成立**（机制前提：先查当前字体 → 逐个后备字体 → `\CJKfamilydefault` 后备，链耗尽才告警） | `xeCJK.pdf` §5.11 后备字体代码与消息模板；`AutoFallBack` 默认 true。提示应建议配置 `\setCJKfallbackfamilyfont`/`FallBack`，而非直接建议换引擎 |
| ctex `fontset` 不可用时的用户可见行为 | **成立：当前引擎模式不支持该 fontset（critical 错误，停止读取定义文件），不是「字体未安装」** | `ctex.pdf` 第 14 节 `fontset-unavailable` 消息源码；adobe/fandol/mac/ubuntu 在 pdfLaTeX 下不可用即属此类 |
| fontspec 只能在 Xe/Lua 使用、xeCJK 只能 XeLaTeX | **成立** | xeCJK 手册 §1 原文限定 XeLaTeX；fontspec 边界依据 CTAN 包页与 latex3/fontspec 仓库 README（fontspec.pdf 正文本轮仍未读到，见下） |

### 仍不可达 / 仍未证实

- **fontspec.pdf 手册正文**：本轮重试范围不含 fontspec；此前两个镜像 PDF 仍被 robots/链接拦截，「找不到字体」一节的逐字建议未读到，结论依据包页、仓库 README 与在线文档首页。
- **biber 是否逐条解释所有 WARN 消息**：本地 grep `biber.tex` 确认手册未罗列；消息文本位于 Perl 源码 `lib/Biber/...`，本轮未逐文件读取源码，逐条消息释义仍未取证。
- **`Duplicate entry key` 告警逐字串**：手册与 biblatex.pdf 均未出现该字符串；仅「biber 默认跳过后续重复键、`--noskipduplicates` 可保留」的行为由 biblatex.pdf §3.8.1 证实。
- **bibtex.web 运行时消息**（`A bad cross reference`、`I couldn't open database file`、`Illegal, another \bibdata command` 等）：仍未获取 `bibtex.web` 源码，官方逐条释义缺失，维持原「未检索到项」结论。
- **论坛级复现证据**：latex.org / latex-community 仍不可访问；multibib、chapterbib 与 `another \bibdata command` 的讨论未取得可引用页面。
- **biber 数据源找不到的等价消息**（`Cannot find <database file>` / `No data sources defined`）：未在官方文档中逐字核实。
- **luaotfload.conf(5)、SARIF 校验器与附录 D**：维持原结论，未展开取证。
- **路径大小写**：组织者列表中的 `.../latex/xeCJK/xeCJK.pdf` 实测 404；CTAN 规范目录为小写 `xecjk`。
