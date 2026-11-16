# Changelog

## v0.5.0 - 2026-11-16

### 新增
- **可执行建议（hints）**：新增 `pytexlogs/hints.py`。`Hint(text, commands, kind)` 把每条错误/警告映射为"人话解释 + 可直接复制的命令"：
  - 缺宏包抓 ``File `x.sty' not found`` 与 `Package X Error:`，给出 `tlmgr install X` / `miktex packages install X` 两条命令；
  - `hint_for_text` / `hint_for_entry` 支持 `jobname` / `root_file` 上下文，把 `biber <jobname>`、`xelatex <主文件>.tex` 替换成 `biber main`、`xelatex main.tex`；
  - 未定义控制序列、`Overfull \\hbox`、缺字体、biber/bibtex 常见错误等均有对应建议；
  - 匹配前做反斜杠归一化，日志里的 `\hbox` 与提示表里的 `\\hbox` 不再错配；
  - 新增高频规则：`Unicode character ...`、未定义 `Citation`/`Reference`/`Environment`、找不到 `.bib`、`Missing character`、`Too many unprocessed floats`、`TeX capacity exceeded`、`No pages of output`、`Runaway argument`、`Missing $ inserted`、`Emergency stop`、`Package ... Error`；
  - **修正误判**：不再把任何 `Package X Error:` 都当成"缺宏包 X"（fontspec 找不到字体时曾误报 `tlmgr install fontspec`）。
  - **中英双语**：`hint_for_text` / `hint_for_entry` 新增 `language` 参数；`Hint.text_en` 覆盖全部内置规则，`--lang en` 下摘要与 `explain` 的建议正文都是英文，不再是中文。
- **日志类型嗅探**：新增 `core/logkind.py`。`sniff_bib_tool()` 按 `.bcf` 优先判断 biber、再看日志头；`sniff_index_tool()` 区分 xindy/makeindex；`sniff_tex_engine()` 从 `.log` 头部识别 pdflatex/xelatex/lualatex；`plan_default_steps()` 按实际存在的 `.blg/.bcf/.ilg/.glg/.alg/.slg/.nlg/.pytxcode/*.asy/*.pygmented` 规划步骤，每份日志只归一个 step，并用真实引擎名作为首个 step。
- **Shell 补全**：新增 `--completion bash|zsh|fish|powershell`，选项从 argparse 自动提取，输出纯文本脚本后退出，不混入摘要。
- **递归目录扫描**：新增 `--recursive`，批量检查时只进入真正含 `.log/.tex` 的子目录，支持一个仓库多个子项目。
- **报告与过滤**：`write_report_file()`（`write_report` 保留为兼容别名并 `DeprecationWarning`）；`language` / `summary_max_entries` 参数；`--jobname`、`--severity` 同时作用于 text/json/csv/sarif；`--baseline` 只保留新增/变化条目；`--max-entries`、`--no-hints`、`--open-all`。
- **`explain` 子命令**：对单条日志/单条消息给出归类与建议，不生成整篇报告。
- **SARIF 升级**：`tool.driver.rules`、`partialFingerprints`、相对路径 + 正斜杠 + `quote`，可直接被 GitHub Code Scanning 消费；非 error/warning 映射为 `note`。

### 修复
- **`sniff_index_tool` 回退永远判成 xindy**：`Path.glob()` 返回生成器，`if parent.glob("*.xdy")` 恒为真；改为 `any(...)`，只有真的存在 `.xdy` 才回退 xindy。
- **缺图片被误判成缺宏包**：`detect_missing_package` 只认 `.sty/.cls/.def/.cfg/.clo/.ldf`；`fig.png` / `refs.bib` 分别给出 `missing_graphic` / `missing_bib` 建议，不再输出 `tlmgr install fig.png`。
- **Windows 编辑器路径被 `shlex` 吃掉反斜杠**：`shlex_split` 在 Windows 使用 `posix=False`，`custom:` 也走同一分词逻辑。
- **本地化条目没有 hint**：LaTeX parser 把引用/交叉引用条目翻译成“找不到 citation/reference `key`”，hint 现在同时匹配英文原文和本地化文本。
- **baseline / SARIF 行号漂移误报**：baseline 去重键与 SARIF `partialFingerprints` 不再包含行号，正文插入几行不会把旧问题当成新增告警；行号仍保留在 `region.startLine` 和展示中。
- **`explain` 无上下文**：`pytexlogs explain ... --jobname main --root-file main.tex` 现在会把建议里的占位符替换成真实命令。
- **报告写盘 100% 失败**：`core/report.py` 误写 `from .exporters`（应为 `..exporters`），异常被吞后一直表现为"没有报告"。
- **状态锁形同虚设**：`core/state.py::_mutate` 未获锁时仍然写盘；现在直接返回 `False`，不写。
- **JSON/CSV 列表输入崩溃**：`json.dumps(default=...)` 处理 `LogLevel` 枚举；CSV 换行压成空格、列序固定。
- **同一条警告打印两遍**：`print_summary(stream=...)` 支持 CLI 捕获，不再"先流式打一遍、再汇总打一遍"。

### 变更
- 目录模式 `run_pipeline(..., print_terminal=False)`；无 `.tex` 时用最大 `.log` 的 stem 推断 jobname；`_default_lang()` 读 `PYTEXLOGS_LANG`/`LANG`/locale。
- `print_summary` 支持分组截断（"… 还有 N 条"）与 `↳ 建议` 行。
- 公共 API 新增导出：`Hint`、`detect_missing_package`、`hint_for_entry`、`hint_for_text`、`filter_by_level`、`plan_default_steps`、`sniff_bib_tool`、`sniff_index_tool`。

### 测试
- 新增 `tests/test_050_features.py`（21 例）、`tests/test_hints_deep.py`（14 例）与 `tests/test_completion.py`（6 例）：报告落盘无 `.tmp`、旧 kwarg 兼容、步骤不重复、index 嗅探（含无 `.xdy` 回退）、引擎嗅探、单反斜杠匹配、缺宏包命令、缺图片/缺 bib 分类、hint 上下文替换、中英文 hint、多格式 severity 过滤、SARIF URI/指纹、baseline 行号漂移、递归目录扫描、全局选项位置、同条警告只打一次、锁失败不写盘、报告失败无 `.tmp`、补全脚本；以及 Unicode/引用/环境/缺 bib/容量/致命错误等新建议。
- 全量：**162 passed, 1 skipped**。


## v0.4.0 - 2026-10-18

### 破坏性变更
- **最低 Python 版本提升到 3.15**：`requires-python` 从 `>=3.14` 改为 `>=3.15`；CI 矩阵由 `3.10–3.14` 收敛为 `3.15`（原矩阵与 `requires-python` 本就矛盾，3.10–3.13 的 job 无法安装本包）
- **状态文件格式升级到 schema v3，不兼容旧版**：`.pytexmk_refcache.json` 由"扁平结构"改为"命名空间结构"。旧版 PyTeXLogs 读写新文件、或新版读旧文件，都会得到空的引用缓存（表现为"首次运行，新增 N 篇"）。此取舍是为了让文件结构只有一种形态，避免长期维护双写逻辑

### 新增
- **`ProjectStateStore`：单文件多命名空间状态存储**（`pytexlogs.core.state`，已加入公共 API）
  - 解决的问题：多个工具共用一个状态文件时，"整文件覆写"会导致后写者抹掉先写者。改造前 `RefChangeTracker.save_cache()` 就是整文件覆写，PyTeXMK 想持久化任何构建状态都会被冲掉
  - 做法：每个写入者只拥有自己的顶层键（`pytexlogs` / `pytexmk` / 第三方），写入时**读-改-写**，只替换自己命名空间内的键
  - **原子写**：同目录临时文件 + `os.replace`，Ctrl+C 中断不会留下半截 JSON
  - **轻量文件锁**：`O_CREAT | O_EXCL` 哨兵 + 超时降级（拿不到锁就跳过本次写入，最多退化为下次多编一轮，绝不阻塞或报错）；30 秒以上的陈旧锁会被自动清理
  - **容错**：文件缺失 / JSON 损坏 / 顶层非对象 / schema 版本不符，一律降级为空骨架，不删除文件、不中断主流程
  - 公共方法：`load` / `get_namespace` / `update_namespace` / `replace_namespace` / `get_build` / `update_build` / `get_refs` / `update_refs` / `clear`

### 变更
- **`RefChangeTracker` 改用 `ProjectStateStore`**：`load_cache()` / `load_cache_counts()` / `save_cache()` 读写 `pytexlogs.refs` 命名空间，不再整文件覆写。`self.cache_path` 保留以兼容外部读取路径
- `pytexlogs.__init__` 新增导出：`ProjectStateStore`、`PROJECT_STATE_FILENAME`、`SCHEMA_VERSION`、`StateFileCorrupted`
- `pyproject.toml`：`tool.ruff` 增加 `target-version = "py315"`；`tool.mypy.python_version` 改为 `"3.15"`；classifier 改为 `Python :: 3.15`

### 新增文件
- 状态文件结构（schema v3）：
  ```jsonc
  {
    "schema_version": 3,
    "timestamp": "2026-10-18T13:59:04+08:00",
    "pytexlogs": { "refs": { "keys": [...], "key_counts": {...} } },
    "pytexmk":   { "build": { "fingerprint": "...", "artifacts": {...}, "sources": {...} } },
    "jobs":      { "main": { "updated_at": "..." } }
  }
  ```

### 测试
- 新增 `tests/test_state_store.py`（19 例）：命名空间隔离、v2 丢弃、v3 自动升级、原子写无残留、锁释放、并发交替写、坏 JSON 降级、`clear()` 幂等
- 全量：**100 passed, 1 skipped**（Python 3.15.0）
- 端到端验证：`run_pipeline()` 写入 `pytexlogs.refs` 后，预先放在 `pytexmk.build` 里的数据原样保留

---

## v0.3.0 - 2026-08-04

### 架构重构
- 按功能模块重新组织代码：core/、parsers/、cli/、display/、exporters/、utils/
- 消除薄层转发层，简化调用链
- formatter 与 printer 分离为独立模块，支持 GUI/Web 输出

### Python 3.14 兼容性
- 移除所有 `from __future__` 兼容性残留
- 全面采用现代类型注解（`|` 联合类型）
- 使用 `datetime.UTC`、`slots=True` 等新特性
- requires-python 更新为 `>=3.14`

### 功能改进
- 10 种日志解析器功能完善（LaTeX、BibTeX、Biber、Makeindex、Xindy、Glossaries、Nomencl、PythonTeX、Minted、Asymptote）
- SARIF 导出符合 v2.1.0 规范
- Minted 解析器添加高亮计数检测
- Nomencl 解析器支持 Warning-- 格式
- LaTeX 解析器修复 assert 语句安全问题
- 参考文献追踪修复首次运行判断逻辑
- 报告加载添加异常处理
- 解析器注册冲突添加警告日志

### 代码质量
- ruff 检查通过，无 E/F 级别错误
- 类型注解完整
- 文档字符串清晰

## v0.2.0 - 2026-08-01

### FR-1: Public API 命名分层 + 兼容别名
新增 run_pipeline / Manager / Registry / Report 四个高频短别名；run_log_pipeline 等旧名通过 DeprecationWarning 向后兼容；__all__ 按「便捷 API / 解析器 / 数据结构 / 常量 / 解析器类 / 演示」六段注释清晰分层。

### FR-2: 类型注解完整补齐 + mypy --strict 通关
所有公共函数、私有变量、11 个 *Parser 子类签名严格对齐 BaseLogParser；pyproject.toml [tool.mypy] 配置 strict=true、python_version="3.10"，mypy --strict src/pytexlogs 零错误。

### FR-3: 高阶便捷函数组（一行搞定常见场景）
新增 easy.py 五个顶层函数：parse_log_file（按后缀自猜 parser）、parse_log_text（captured_outputs 场景）、parse_auxdir（整辅助目录扫描）、filter_severity（按严重度裁剪条目）、aggregate_stats（category/level/parser 分组统计）。

### FR-4: 统计聚合 API
aggregate_stats(obj, group_by="category" | "level" | "parser") 接受 ParsedPipelineReport | list[ToolResult]，返回直方图 dict，可直接用于 CLI 打印或可视化。

### FR-5: 三种结构化导出（JSON / CSV / SARIF）
在 _report.py 新增 to_json / to_csv / to_sarif 三个公共函数；SARIF 为 v2.1.0 最小子集，可直接喂 GitHub Code Scanning；CSV 严格表头 file,line,level,category,tool,text,hint,source_path。

### FR-6: Entry Point 插件化机制
LogParserRegistry.get_default_registry() 首次构造时自动扫描 pytexlogs.parsers Entry Point 组；外部包可在自己 pyproject.toml 中注册自定义解析器，无需改动 pytexlogs 源码。

### FR-7: CLI（argparse）开箱即用
新增 pytexlogs = "pytexlogs.cli:main" 入口脚本，支持全局 --version / --lang / --format / --output / --severity / --root-file / --open / --editor 参数；退出码 0=无 error，1=有 error，2=参数/IO 错。

### FR-8: 编辑器跳转打开能力
--open + --editor auto|code|subl|nvim|gvim|custom:<template>，自动按 VISUAL > EDITOR > code > subl > nvim > gvim 优先级选编辑器，失败仅 warning 不中断；支持 %f:%l 模板替换。

### FR-9: i18n 可插拔翻译（中英文摘要）
set_summary_language(lang, translate_fn=None) 全局切换；CLI --lang zh/en 直接生效；translate_fn 参数允许注入任意自定义翻译逻辑，无 gettext 依赖。

### FR-10: summary 子命令
pytexlogs summary [LOG ...] 等价 check 但专注摘要输出，忽略退出码；检测到 rich 时用 rich.table 彩色表格，无 rich 退化为纯文本对齐。

### FR-11: export 子命令
pytexlogs export --format=json|csv|sarif LOG/DIR --output PATH 一步生成结构化报告；--output 缺省则打印到 stdout，方便 shell 管道。

### FR-12: filter_severity 便捷过滤
filter_severity(entries, min_level=WARNING) 利用 LogLevel.__lt__ 比较，一行保留 min_level 以上条目，常用于 CI 告警筛选。

本次共实现 49 条公共 API；新增 check / summary / export / demo 四类 CLI 子命令；wheel 体积控制在 <= 70KB；requires-python>=3.10 提高 PyPI 覆盖率。

## v0.1.0 - 2026-07-30

- 新增：从 PyTeXMK v1.1.0 抽离日志解析子包为独立 PyPI 库 pytexlogs
- 改进：移除对 pytexmk.* 的反向依赖，成为纯标准库可运行的包；独立库 logger 名改为 pytexlogs
- 测试：独立命名空间 B 验证（NFR-3）4 PASS，可单独解析 LaTeX/BibTeX 等日志
