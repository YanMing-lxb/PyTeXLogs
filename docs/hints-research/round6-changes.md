# 第 6 轮 hints 规则修复：变更记录

- 仓库：`D:\Document YM\Desktop Document\Tools_Development\PyTeXLogs`
- 环境：Python `D:\Document YM\Desktop Document\Tools_Development\PyTeXMK\.venv\Scripts\python.exe`，
  `PYTHONPATH=D:\Document YM\Desktop Document\Tools_Development\PyTeXLogs\src`（绝对路径），
  ruff 0.17.5。
- 范围限制：本轮 hints 切片只改 `src/pytexlogs/hints.py` 与 `tests/test_hints_round6.py`；
  未 commit、未动 MiKTeX 配置、未改系统 PATH/环境变量、未装 TeX 包、未回滚既有未提交改动。

## 真实环境基线（本机 MiKTeX 实跑）

- Windows 本机装有 **MiKTeX 26.5 Portable**，bin 目录：
  `C:\Applications\Scoop\apps\miktex\current\texmfs\install\miktex\bin\x64`；`pdflatex/xelatex/lualatex/biber/bibtex/latexmk` 均在 PATH。
- 版本：`--version` 为 MiKTeX-pdfTeX 4.27 / MiKTeX-XeTeX 4.18；真实日志首行为 pdfTeX 1.40.29 / XeTeX 0.999998 / biber 2.22。
- 编译命令：`xelatex|pdflatex -interaction=nonstopmode --disable-installer main.tex`，工作目录
  `%TEMP%\pytexlogs_real_compile_r6\<场景子目录>`；未安装包、未改 MiKTeX 配置、未改 PATH/环境变量。
- kpsewhich 实查已安装：`ctex.sty`、`xeCJK.sty`、`fontspec.sty`、`biblatex.sty`、`siunitx.sty`。
- Linux TeX Live 云主机日志仅作为 round1 原始采集记录保留；本轮真实场景均为本机 MiKTeX 编译产出，
  完整命令、源码探针与逐条对比见 [`round6-real-miktex.md`](round6-real-miktex.md)。

## 真实日志矩阵（本机 MiKTeX，12 份 fixture）

| 编号 | fixture（`tests/fixtures/real_miktex/`） | 引擎/工具 | 条目数 | 命中规则与关键提取值 | 修复前 → 后 |
| --- | --- | --- | --- | --- | --- |
| B1 | `xelatex_fontspec_not_found.log` | xelatex | 103 | `fontspec_font_not_found` ×3（regular/BI/B/I 独立块，不去重、计数不变）；`font_not_loadable` ×1（字族 `NoSuchFontFamilyXYZ`，无 `or.tfm`、无 pdflatex 文案）；`missing_glyph` ×1 | `Font ... not loada\nble` 折行曾误判 `tfm_font_missing` 并抽出 `or.tfm`；修复后命中 `font_not_loadable` |
| B2 | `pdflatex_newcommand_dice.log` | pdflatex | 11 | 首错 `missing_begin_document`；`missing_number` ×3、`illegal_unit` ×1；全链 `undefined_control` ×0 | 合成 F12 帧只验证定义包装命令不报未定义；真实首错链条以本 fixture 为准 |
| B3a | `pdflatex_ctex_adobe_fontset.log` | pdflatex | 288 | `fontset_unavailable` ×1（`adobe`），无 `package_error` | `current`/`mode` 间 `(ctex)` 续行前缀曾打断正则；修复后续行括号前缀兼容 |
| B3b | `xelatex_xecjk_missing_glyph.log` | xelatex | 98 | `missing_glyph` ×1（字符 `中`，字体 `Latin Modern Roman`，无 `(U+XXXX)` 后缀，非 nullfont） | 折行缺字形消息曾解析为 0 条；修复后折行缓冲合并、码位后缀可缺省 |
| B3c | `biber_case_mismatch.blg` | biber | 2 | `biber_case_mismatch` ×1（`Key` vs `key`，`refs.bib`）、`log_hint` ×1；biber 工具下无 `undefined_citation`/`undefined_reference` 抢答 | `[220] Biber.pm:132> ` 位置前缀曾导致整份 `.blg` 0 条；修复后先剥前缀再匹配 |
| B3d | `pdflatex_undefined_cite_ref.log` | pdflatex | 30 | `undefined_citation` ×1（`key`）、`undefined_reference` ×1（`sec:intro`） | 正则兼容反引号/直单引号/双引号引用键 |
| L1 | `lualatex_fontspec_not_found.log` | lualatex | — | `fontspec_font_not_found` ×3 + `font_not_loadable` ×1，字族 `NoSuchFontFamilyXYZ`，无 `or.tfm`；OpenType/系统字体分支给 `fc-list` + `luaotfload-tool --update`，文案不含 pdflatex/TFM | 修复前 `hint_for_entry` 返回 None；规格正则覆盖 `\TU/`/`\OT1/` 等 NFSS 形式与跨行名称，reason 兼容 `metric data not found or bad` |
| L2 | `lualatex_xecjk_missing_glyph.log` | lualatex | 12 条重复聚合为 1 条 | `missing_glyph` ×1（字符 `中`，`(U+4E2D)` 保留，规范化字体 `Latin Modern Roman`，次数与去重字形列表保留）；聚合不改 results/JSON/CSV/SARIF 行数语义 | 引擎错配修复：lualatex/xelatex 分支直接给 `\setCJKmainfont{<含该字的中文字体>}`，无换引擎命令、无“若还在 pdfLaTeX”前提；原始 fontspec spec 保留在条目文本/error_pos |
| B1-bbl | `pdflatex_biblatex_before_biber.log` | pdflatex | 100 | `missing_bbl` ×2 + `undefined_citation` ×1，`missing_bbl` 在最前 | `No file main.bbl.` 原被吞；现入 WARNING 条目，`_MISSING_BBL_RE` 优先于 `undefined_citation`，`Please (re)run Biber on the file:` 也归 `missing_bbl`，文案给 `latex → biber <jobname> → latex` |
| B2-chain | `pdflatex_biber_chain_pass1.log`、`biber_chain.blg`、`pdflatex_biber_chain_final.log` | pdflatex → biber → pdflatex | 完成态 95 | 完成态 `missing_bbl`/`undefined_citation` 均 0；`.blg` 仅 INFO（0 条 warning，本场景键名匹配无 WARN）；`main.bbl` 1583B、PDF 25895B | 链路端到端回归：首遍缺 bbl + 未定义引用 → biber 收尾 → 完成态两类警告消失 |

## 剩余真实边界

- B3c 只采集 `.blg`，未跑第二遍 pdflatex 回填 `.bbl`；不影响 biber 规则证据。
- B2 链路只验证首遍 → biber → 完成态三段；第三遍之后的额外收敛检查未单独断言；本场景 `.blg` 无 WARN，未覆盖 biber 告警在链路中间态的断言。
- 两份真实缺字形 fixture 均未出现 `nullfont` 行；nullfont 重复条目按既有 `(文件, 字体)` 桶聚合逻辑覆盖，未在真实日志中额外验证。
- 展示层按字体族聚合（BI/B/I 降噪）本轮未实现：解析层与 hints 层不去重、不改 `results` 计数；B1/L1 的 fontspec 错误块为真实独立错误。

## 四项清单

| 编号 | 主题 | 归属 | 状态 |
| --- | --- | --- | --- |
| P0-1 | `undefined_control` 定义命令裸名称提取 + 构造后控制序列反例修复 | 本切片 | 已完成 |
| P0-2 | `fontspec_font_not_found` 名称/文件名双分支；`luaotfload-tool --update` 仅 LuaLaTeX | 本切片 | 已完成 |
| P1-3 | hints 匹配器性能门禁（`tests/perf/test_hints_matcher.py`，`CI_PERF=1` 门控） | 性能切片 | 已完成（见下节） |
| P2-4 | 导出层 `language` 透传（JSON/CSV/SARIF/CLI `--lang`） | 另一负责方 | 见 `test_export_language.py` |

> P2-5（`docs/hints-reference.md` 规则表与 `RULE_IDS` 顺序锁定）同属 round6，
> 由 `tests/test_hints_docs.py` 覆盖，不在本文档展开。

---

## P0-1：`undefined_control` 定义命令提取

### 根因

`! Undefined control sequence.` 的 `l.N` 行（含折行续行）可能是一条定义命令：

```tex
\newcommand{dice}
\def\dice
\newenvironment{dice}
```

第一版修复只要 `_DEF_COMMAND_RE` 命中定义构造就直接返回定义建议，把包装命令
（`\newcommand`/`\def`/`\newenvironment`）报成未定义命令，并生成
`tlmgr search ... newcommand.sty` 这类错误安装建议。

复核阶段又发现一个反向误报：**定义构造之后还跟着别的控制序列时**，真正未定义的是后者，
旧逻辑仍报被定义的宏名：

- `\newcommand{\foo} \badcmd` → 误报“定义宏 `\foo`”，实为 `\badcmd`；
- `\def\foo{bar} \badcmd` → 误报 `\foo`，实为 `\badcmd`；
- `\newcommand{dice} \badcmd` → 误报 `\dice`，实为 `\badcmd`。

### 修复规则

1. 识别包装命令：`\newcommand` / `\renewcommand` / `\providecommand` / `\def` /
   `\newenvironment`（可带 `*`）；命令名支持花括号内（带或不带反斜杠）与直接
   `\csname` 两种形式。
2. 命中构造后，用 `_skip_definition_groups` 切掉命令名与紧随的可选 `[...]` 参数、
   平衡 `{...}` 定义体分组；**定义体内部的控制序列**（如 `\def\foo{\textbf{x}}` 里的
   `\textbf`）属于构造内部，不计入“构造之后”。
3. 剩余文本仍能找到控制序列 → 走常规未定义命令分支，报后者（`\badcmd`），commands
   保留 grep + tlmgr 查找；只有剩余为空时才报定义语法笔误。
4. 定义笔误分支：commands 只保留指向真名的 grep，不再给 `<name>.sty` 安装命令；
   修法示例按宏类型给出（`\newcommand{\dice}{...}` / `\newcommand*{\dice}{...}` /
   `\def\dice{...}` / `\newenvironment{\dice}{...}{...}`）。

### 限制（最小实现）

- 分组跳过只做括号配平，不解析宏体语义；遇未闭合分组即停在当前位置，剩余文本交常规提取。
- 判定基于 `l.N` 行及其紧随续行；构造跨行展开的极端形态不在本轮覆盖。

### 正例（定义笔误，报 `\dice`）

| 输入 `l.N` 行 | 输出要点 |
| --- | --- |
| `\newcommand{dice}` | 文案含 `` `\dice` ``；示例 `\newcommand{\dice}{...}`；无 `.sty` 命令 |
| `\newcommand*{dice}` | 示例 `\newcommand*{\dice}{...}`；无 `.sty` 命令 |
| `\newcommand\dice` | 提取 `\dice`；示例 `\newcommand{\dice}{...}` |
| `\def\dice` | 示例 `\def\dice{...}` |
| `\newenvironment{dice}` | 判为环境；示例 `\newenvironment{\dice}{...}{...}` |
| `\renewcommand{dice}` / `\providecommand{dice}` | 同 `\newcommand` 分支 |
| 折行续行 `\newcommand{dice}` | 续行同样提取 `\dice` |

### 反例（构造后另有命令，报 `\badcmd`）

| 输入 `l.N` 行 | 输出要点 |
| --- | --- |
| `\newcommand{\foo} \badcmd` | 文案含 `` `\badcmd` ``；不含“看起来是在定义”；commands 含 `badcmd`，不含 `foo`、不含 `newcommand.sty` |
| `\def\foo{bar} \badcmd` | 同上；定义体 `{bar}` 被切掉，不干扰判定 |
| `\newcommand{dice} \badcmd` | 同上；commands 不含 `dice` |
| 续行 `\newcommand{dice} \badcmd` | 同样取续行剩余的 `\badcmd` |

回归：普通 `l.3 Hello \undefinedcmd` 仍走原逻辑，commands 含
`tlmgr search --global --file undefinedcmd.sty`。

---

## P0-2：fontspec 名称 / 文件名双分支

依据 fontspec 手册 §2（两种引擎都支持按字体名或按文件名加载）、§2.1（By font name）、
§2.2（By file name）。

### 分支判定

- **名称模式**：字体名不含 `.otf/.ttf/.ttc/.otc` 扩展名，也不含路径分隔符。
- **文件名模式**：含上述扩展名，或含 `/`、`\` 路径分隔符。

### 名称模式建议

- `fc-list : family | grep -iF "<name>"`：名称整体双引号引用（含空格不断词，
  `-F` 固定字符串）；Windows 在“字体设置”核对全名；提醒注意大小写与重音。
- TEXMF 树内字体：LuaTeX 可按名加载；XeTeX 在 Windows/Linux 可以，**macOS 不行**——
  macOS 上 TEXMF 树内字体只能按文件名加载（手册 §2.1 原文事实）。
- `luaotfload-tool --update` **仅在 `tool_name="lualatex"` 时进入 commands**；
  XeLaTeX 不走该缓存；未知引擎不 unconditional 给出。文案说明首次排版可能停顿数分钟。

### 文件名模式建议

- `kpsewhich "<name>"` 核对文件是否在 TeX 搜索路径（TEXMF 树或当前目录）。
- 核对扩展名与拼写；fontspec 靠 `.otf` 扩展名判定按文件名加载，也可用 `Extension=`
  单独指定（§2.2）。
- 不在默认搜索路径时用 `Path=<目录>`（旧名 `ExternalLocation` 已弃用）。
- 按文件名加载必须显式给出 `UprightFont=`/`BoldFont=`/`ItalicFont=` 等变体；
  用 `*` 缩写时 `UprightFont=` 为必需，除非提供 `.fontspec` 文件。

### 覆盖输入

| 输入字体 | 分支 | commands 要点 |
| --- | --- | --- |
| `NoSuchFontFamilyXYZ` | 名称 | `fc-list : family | grep -iF "NoSuchFontFamilyXYZ"` |
| `Times New Roman` | 名称 | `grep -iF "Times New Roman"` 整体引号 |
| `MyFont.otf` | 文件名 | `kpsewhich "MyFont.otf"` |
| `fonts/MyFont.ttf` | 文件名 | `kpsewhich "fonts/MyFont.ttf"` |
| 引擎 `xelatex` / `lualatex` | 名称 | 仅 `lualatex` 含 `luaotfload-tool --update` |

中英文案同步；`kind="missing_font_family"`、`rule_id="fontspec_font_not_found"` 不变。

---

## P2-4 / P2-5：导出层语言透传与文档顺序锁定

- `to_json` / `to_csv` / `to_sarif` 新增可选 `language: str | None = None`，默认 `None`
  时行为与之前逐字一致（中文）。`language="en"` 时：JSON `hints[].hint.text`、
  SARIF `properties["pytexlogs/hint"].text`、CSV `hint` 列取英文（缺失回退中文）；
  JSON/SARIF 仍保留 `text`/`text_en` 双字段，`kind`/`commands`/`rule_id` 不变；
  CSV 表头不变。
- CLI `export` 把既有 `--lang`（zh/en）透传给三个导出器，未新增参数；实测
  `export sample.log --format json --lang en` 的 hint 文案为英文，默认仍中文。
- `tests/test_hints_docs.py` 锁定 `docs/hints-reference.md` 的 41 行 rule_id 成员与顺序
  与 `RULE_IDS` 完全一致（缺项/多项/错位/重复均失败）。

---

## P1-3：hints 匹配器性能门禁

新增 `tests/perf/test_hints_matcher.py`，与 `tests/perf/test_100k_lines.py` 同一门控
（`CI_PERF=1`，默认 skip）。三个用例都带**硬断言**，不是只打印时间：

| 用例 | 负载 | 阈值 | 实测（`CI_PERF=1`，两支） |
| --- | --- | --- | --- |
| 混合日志解析 + 全量匹配 | 100k 行 / ≈3.58MB / 68,001 条目 | 总 < 2.0s | 963ms（parse 310ms + hint 653ms）；1021ms（parse 362ms + hint 659ms） |
| 重复缺字形 | 5,000 条（拉丁 + `(U+4E2D)` 变体各半），5,000 命中 | < 1.0s | 39.7ms / 42.6ms |
| 超长畸形 `Font` 行 | 5,005 字符 / 31,000 字符 | 单次 < 100ms | 0.86ms / 6.0ms（另一轮 4.9ms） |

阈值依据：实测值之上留 ≥2×（大多数 20× 以上）余量，覆盖 CI 机器抖动；输入构造用
列表 + `"\n".join`，不用字符串 `+=`。超限时的约定是先定位具体规则/正则并记录耗时，
不直接改 `hints.py`。

---

## 实测复验数字（实跑，非估算）

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 全量测试 | `python -m pytest -q tests` | **486 passed, 4 skipped**（0 failed；4 个 skip 仅在未设 `CI_PERF` 时出现） |
| 性能门禁 | `CI_PERF=1 pytest tests/perf` | **4 passed** |
| lint | `ruff check --config pyproject.toml src tests` | **All checks passed!** |
| 字节码编译 | `python -m compileall -q src\pytexlogs` | **exit 0** |
| 版本 | `python -m pytexlogs.cli --version` | `pytexlogs 0.6.1` |

- 4 个 skip 均为 `tests/perf` 下 `CI_PERF=1` 门控的性能用例；无缺包/缺环境类跳过。
- 真实 MiKTeX 用例 `tests/test_real_miktex_round6.py` 共 **19** 例：第一轮 10 + 第二轮 7 + 引擎分支补丁 2；
  对应 `tests/fixtures/real_miktex/` **12 份**真实日志 fixture。
- 此前 round6 切片新增 33 个：`test_hints_round6.py` 19 + `test_export_language.py` 9 +
  `test_hints_docs.py` 2 + `tests/perf/test_hints_matcher.py` 3。
- `tests/test_hints_round6.py` 共 **19** 个用例：定义正例 7（参数化）+ 定义折行正例 1 +
  普通命令回归 1 + 构造后反例 3（参数化）+ 续行反例 1 + fontspec 名称 2 + 文件名 2 +
  引擎条件命令 2（参数化）。
