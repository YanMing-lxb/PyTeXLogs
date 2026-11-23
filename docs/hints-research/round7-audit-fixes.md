# Round 7：审计结论落地与多轮优化记录

本文件记录 2026-11-21/22 在 `PyTeXLogs` 工作区按只读审计结论执行的多轮修复。
不是发布说明；所有改动仍未 commit，验证只使用本机临时目录与既有真实日志 fixture。

## 结论摘要

- 审计共 15 类问题，本轮完整修复 12 类、部分收敛 1 类；2 类保留边界（见“未完成/保留项”）。
- 规则总数仍为 **41**；`RULE_IDS` 与 `docs/hints-reference.md` 顺序未变。
- 最终基线：`pytest -q tests` = **660 passed, 6 skipped**；
  `CI_PERF=1 pytest -q tests/perf` = **6 passed**；`ruff` 全绿；`compileall` 退出码 0；
  `python -m pytexlogs.cli --version` = `pytexlogs 0.6.2`。
- 未修改 MiKTeX 本体、系统 PATH / 环境变量，未安装 TeX 包，未 commit，未回滚既有未提交改动。

## 第 1 轮：LaTeX 解析正确性（P0）

| 问题 | 修复 | 验证 |
| --- | --- | --- |
| `_flush_current` 后未重置，连续两条 Info/Warning 被二次入队 | flush 成功后将 `current_result` 重置为空 `_TempEntry(type=None)` | 连续两条 Info 恰好 2 条；真实 fixture 条目数下修 |
| 警告后的纯文件栈行被吞进 `text`，后续错误归属错文件 | `search_empty_line` 识别栈行先 flush，再交给 `_parse_file_stack` | `chapter.tex` 归属回归 |
| 文件栈 `\S*` 遇空格路径截断 | 栈项捕获到行尾/下一括号，`_stack_path_is_file` 只认路径形态 | `C:\Program Files\...\biblatex.sty` 完整归属 |
| `(biblatex) main` 被误判为文件栈 | 栈行需含 `/`、`\` 或已知日志后缀；续行保留原文 | `(biblatex) main` 续行回归 |
| `Missing character` 折行/截断缓冲在 EOF 丢失 | 新错误帧/空白/栈行先 flush；EOF 对非空缓冲降级 `_record_missing_character` | 截断缺字形仍产出 1 条 warning + hint |
| 字符串入口 BOM / CRLF 丢首条 | `parse` 开头去 `\ufeff`，统一 `\r\n`/`\r` | `parse_log_text("\ufeffLaTeX Warning...")` 命中 |
| 带点 jobname 的 `No file *.bbl` 漏报 | `no_file_bbl_re` 允许点号与尾随 `.;:?` | `paper.v1.bbl` 命中 `missing_bbl` |
| Biber/BibTeX 的 CRLF 输入残留 `\r` | 两个解析器入口统一 `\r\n`/`\r` 为 `\n`；`database_files` 与 warning 文本不再带 `\r` | CRLF fixture 回归 |
| 真实日志 100/404/95 等条目数含重复 | 去重后按唯一条目更新 fixture 断言；`lualatex_xecjk_missing_glyph` 404→358、`pdflatex_biber_chain_final` 95→56 | `test_real_miktex_round6.py` 全绿 |

另：`missing_glyph` 的 CJK 分支命令按实际引擎生成，LuaLaTeX 不再硬编码 `xelatex`；
`Hint.commands_en` 与 `<engine>` 槽位随之透传。

## 第 2 轮：引擎状态与 BibTeX

| 问题 | 修复 | 验证 |
| --- | --- | --- |
| tracker 异常时 `ref_unchanged` 未绑定，`print_terminal=True` 触发 `UnboundLocalError` | try 前初始化 `ref_unchanged=[]` 等列表 | 构造/抽取两类异常回归 |
| 无 `.aux/.bcf` 时 `save_cache([])` 清空旧引用缓存 | `detect_mode() != "unknown"` 才提取、diff、回写；unknown 只读旧缓存 | 旧缓存保留；`current_keys=[]`，不拿旧键冒充当前键 |
| 非法 `ignore_patterns` 正则中断流水线 | `_compile_ignore_patterns` 捕获 `re.error`，warning 后跳过该项 | `ignore_patterns=["("]` 不崩、不过滤 |
| 过滤后 `stats` 仍是过滤前计数 | `_recompute_filtered_stats` 重算 entries/全部等级/errors/warnings/盒子/未定义键 | 过滤后等级桶与剩余条目一致 |
| BibTeX 多行 `Warning--` 被单行路径二次记录 | 索引式遍历跳过“Warning 首行 + `--line` 续行”整帧 | 2 条真实警告 → 2 条目、`warnings_count=2` |
| BibTeX 单行 ERROR 去重 O(n²) | `_seen_keys` 稳定键 O(1) 去重；错误帧按行有界扫描 | 三种帧形各 5000 共 15000 帧 < 100ms |

`stats` 过滤后重算口径：`entries_count`、7 个 `LogLevel` 等级键、
`errors_count/warnings_count`、`overfull_boxes/underfull_boxes`、
`undefined_refs/undefined_cites`；无法从条目推导的整日志字段
（`entries_processed`、`pages_output`、`database_files`）保留原值。

## 第 3 轮：hints 准确性、工具作用域与英文命令

- 17 条 LaTeX 专属规则补 `tools=_LATEX_TOOLS`：
  `missing_package`、`missing_file`、`font_not_loadable`、`tfm_font_missing`、
  `missing_font`、`fontset_unavailable`、`unicode`、`cjk_missing_glyph`、
  `missing_glyph`、`missing_bbl`、`undefined_citation`、`undefined_reference`、
  `capacity`、`runaway`、`fatal`、`missing_begin_document`、`fontspec_font_not_found`。
- `missing_bib` 使用 LaTeX 引擎 + biber + bibtex 的显式集合；`biber_case_mismatch`
  仍只按 biber 文本放行；`runaway` 不再在后端日志给 LaTeX 建议。
- `missing_bbl` 文案拆分：
  - `No file *.bbl` → 明确“未找到 `<job>.bbl`”；
  - `Please (re)run Biber` → 只说后端未完成，不再重复整句，也不再声称不存在的 `.bbl` 缺失。
- `Hint.commands_en` 覆盖全部含中文命令的规则；`hint_for_text(language="en")`
  返回 `commands_en or commands`，英文命令无中文、无 `<主文件>/<引擎>/<选项>/<TeX 版>` 等残留。
- 验证：`test_hints_scope_round7.py` 17 条 × 6 工具参数化；
  `test_hints_english_commands_round7.py` 覆盖 undefined_reference、missing_glyph、
  unicode、fontset、option_clash、hyperref_pdf_string、invalid_utf8、missing_bbl、
  tfm、font_not_loadable、package_error。

## 第 4 轮：导出、CLI 与展示

- `to_json` 对 list 逐项分派 `ToolResultReport` / `ToolResult` / `ParsedLog` /
  `LogEntry`，混合列表不再对 `ToolResultStats.get` 抛 `AttributeError`；
  `[ParsedLog]` 输出结构化字段，不再是 repr；单条 `LogEntry` 也保持可用。
- `report_schema` 改用 `REPORT_SCHEMA_VERSION`，不再硬编码 `1`。
- CLI `_aggregate_stats` 直接委托 `easy.aggregate_stats`：category/parser 按条目数，
  level 动态含 `font/graphic/page`。
- 坏盒子行只匹配一次；`_strip_rich_markup` 正则模块级预编译；行为快照不变。

## 第 5 轮：死代码与重复实现收敛（行为不变）

- 删除未接线/未使用：`_FAST_PREFIXES`、`inside_box_warn`、
  `biber_warn_re`、`message_line_re`、`file_stack_close_re`、
  `encoding.resolve_path`、`csv_exporter._collect_hints`、
  `minted_package_warning_re`、`minted_empty_content_re`。
- xindy 的 6 条正则抽到 `parsers/xindy_patterns.py`，`GlossariesParser` 与
  `XindyParser` 共用同一对象。
- `BibtexParser` / `BiberParser` 的相对路径解析抽到 `parsers/path_utils.py`，
  保留各自缓存。
- 修正 `package_warning_extra_lines_re`：标准 `(biblatex) main` 现在能识别，
  续行保留原文并提取 `on input line`；旧 `(p)kg message` 异常形态不再误拆。
- `ProjectStateStore._mutate` 捕获 `Exception`（与“任何异常不外抛”承诺一致）；
  `dict_to_report` / `load_report` 对非 JSON object 顶层抛可读 `TypeError`。

## 未完成 / 保留项

1. **非中文 CJK 编码误判**：`gb18030` 仍可能把 Shift-JIS/EUC-JP 字节“成功”解成
   乱码。没有可靠检测前不强行加候选，保留为待验证项；新增日志应优先 UTF-8。
2. **展示层全量摘要**：CLI 默认 `max_entries=10` 不触发；库调用方直传 10 万条
   `ParsedLog` 时仍是逐条 `console.print`。本轮只修了正则重编译/坏盒子二次匹配，
   未改打印架构。
3. **`package_warning_extra_lines_re` 的历史 `(p)kg` 形态**：现在只识别标准
   `(pkg) text`；若遇到真实日志仍是旧异常形态，应补 fixture 后再扩，不凭猜测放宽。
4. **真实 MiKTeX 重新编译**：本轮没有新增编译探针，只回放 Round 6 的 12 份真实
   fixture；MiKTeX/PATH 未动。若需要新引擎矩阵，应另起临时目录用
   `--disable-installer` 采集。

## 附：审计 15 项对照

| # | 审计发现 | 状态 |
| --- | --- | --- |
| 1 | `_flush_current` 重复建条 | 已修 |
| 2 | 无 aux/bcf 清空引用缓存 | 已修 |
| 3 | ignore 后 stats 不重算 | 已修 |
| 4 | BibTeX 单行错误 O(n²) | 已修 |
| 5 | `to_json` 异构 list 崩溃 | 已修 |
| 6 | 英文 hint 命令残留中文/占位符 | 已修 |
| 7 | `missing_bbl` 文案/匹配边界 | 已修 |
| 8 | 17 条规则缺工具白名单 | 已修 |
| 9 | 非法 ignore 正则中断 | 已修 |
| 10 | 截断缺字形缓冲丢失 | 已修 |
| 11 | BibTeX 多行警告重复 | 已修 |
| 12 | 文件栈按空白切路径 | 已修 |
| 13 | 非中文 CJK 编码误判 | 保留待验证 |
| 14 | 冗余/重复实现 | 部分修（安全项） |
| 15 | 展示层全量摘要慢 | 保留（CLI 默认不触发） |
