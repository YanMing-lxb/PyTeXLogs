# PyTeXLogs

PyTeXLogs v0.3.0 是 LaTeX/BibTeX/Biber/Minted/Asymptote/Makeindex 日志解析库。可嵌入任意 Python 工具链。

## 安装

```bash
# 推荐：uv 项目内添加
uv add pytexlogs

# 或 pip
pip install pytexlogs

# 可选增强：rich 美化终端表格
uv add pytexlogs[rich]

# 仅 CLI：作为全局工具安装
uv tool install --python 3.10 pytexlogs
```

## 应用价值 · 6 大场景

| 场景 | 目标用户 | 今日痛点 | PyTeXLogs 的解法 |
|---|---|---|---|
| **IDE / 编辑器集成** | VS Code LaTeX Workshop / Neovim 用户 | 错误解析散落在各插件的正则里，易漏、不一致 | `parse_log_file` + `format_editor_jumps` 直接产出 `file:line:message` |
| **CI 质量门禁** | 科研论文仓库 / 团队文档 | CI 日志长，错误沉底；无 Code Scanning 告警 | CLI 导出 SARIF → `github/codeql-action/upload-sarif` 可视化 |
| **本地 CLI 诊断** | 普通 LaTeX 作者 | `pdflatex` 输出几百行，错误在末尾 | `pytexlogs check main.log` 一行摘要 + Hint，退出码=1 |
| **工具链二次开发** | latexmk / tectonic / arara 封装者 | 已有工具不诊断，重写 11 套 parser 成本高 | `parse_auxdir` 一行拿全结果 + `aggregate_stats` 直方图 |
| **批量教学报表** | LaTeX 课程助教 | 批改几十个作业日志，人工统计耗时 | `pytexlogs export --format csv ./logs -o report.csv` 一键汇总 |
| **插件化扩展** | 自定义工具开发者 | 缺少 ChkTeX / lacheck 等专属 parser | Entry Point 机制：`[project.entry-points."pytexlogs.parsers"]` 自动注册 |

## 快速开始 · 3 段复制粘贴

### 3.1 解析单个日志并打印摘要

```python
from pytexlogs import parse_log_file, print_summary

parsed = parse_log_file("tests/fixtures/sample.log")
print(f"错误 {len(parsed.errors)} 条，警告 {len(parsed.warnings)} 条")
print_summary([parsed], use_logger=False, non_quiet=True)
```

输出：

```
错误 1 条，警告 1 条
┌─────────────┬───────┬─────────┬──────────┐
│ 类别         │ ERROR │ WARNING │ 合计     │
├─────────────┼───────┼─────────┼──────────┤
│ compile     │ 1     │ 1       │ 2        │
└─────────────┴───────┴─────────┴──────────┘
```

### 3.2 CLI 一行使用

```bash
# 诊断单个 .log；有 ERROR 时退出码=1
pytexlogs check build/main.log

# 英文摘要
pytexlogs summary ./main.log --lang en

# 批量导出 SARIF，配合 GitHub Actions 上传告警
pytexlogs export --format sarif ./build -o out.sarif
```

### 3.3 Entry Point 自定义 ChkTeX parser

```python
from pytexlogs import (
    BaseLogParser, LogEntry, LogLevel, ParsedLog,
    LogParserRegistry, LogParserManager,
)

class MyChktexParser(BaseLogParser):
    category = "lint"
    importance = "medium"

    def parse(self, log_text: str, root_file=None):
        entries = []
        for i, line in enumerate(log_text.splitlines(), 1):
            if "Cmd terminated with space" in line:
                entries.append(LogEntry(LogLevel.WARNING, root_file or "main.tex", i, line))
        return ParsedLog(entries=entries, raw_text=log_text,
                         category=self.category, importance=self.importance)

# 模拟 entry point 加载效果（真实场景写在 pyproject.toml 中）
registry = LogParserRegistry()
registry.register("mychktex", MyChktexParser)
mgr = LogParserManager(registry)
results = mgr.run("demo", ".", steps=["mychktex"],
                  captured_outputs={"mychktex": "Warning: Cmd terminated with space.\n"})
print(f"自定义 parser 产出 {len(results[0].warnings)} 条 lint 警告")
```

## 公共 API 索引

按 `__all__` 六分组：

### 1. 顶层便捷 API（High-level entrypoints）

| 符号 | 用途 |
|---|---|
| `parse_log_file(path)` | 一行解析单个 .log / .blg / .ilg 等文件（按后缀自动猜 parser） |
| `parse_log_text(text, engine="pdflatex")` | 一行解析字符串（captured_outputs / subprocess.stdout 场景） |
| `parse_auxdir(jobname, auxdir, steps, captured_outputs)` | 一行扫描整个 LaTeX 辅助目录 |
| `filter_severity(entries, min_level=WARNING)` | 按严重度裁剪日志条目 |
| `aggregate_stats(obj, group_by="category\|level\|parser")` | 聚合统计 → 直方图/报表数据源 |
| `run_pipeline(...)` | 完整 pipeline：发现→解析→汇总→摘要→报告一体化（推荐） |
| `run_log_pipeline(...)` | `run_pipeline` 的向后兼容别名（0.1.0 原名） |
| `print_summary(results, ...)` | 终端友好的摘要打印（含错误/警告汇总、HINT 字典） |
| `show_log_entries(entries, ...)` | 逐条日志条目可视化展示 |
| `format_editor_jumps(entries)` | 生成 `file:line: message` 的编辑器跳转列表 |
| `log_editor_jumps(entries)` | 通过 logging 输出编辑器跳转列表 |
| `set_summary_language(lang, translate_fn=None)` | 全局设置摘要语言（zh/en）或自定义翻译函数 |

### 2. 解析器管理器 / 自定义注册（Extension API）

| 符号 | 用途 |
|---|---|
| `LogParserManager` / `Manager` | 按 step/suffix 调度多个解析器的管理器 |
| `LogParserRegistry` / `Registry` | 解析器注册表：默认 11 项 + Entry Point 自动加载 |
| `LogParserSpec` | 单条解析器规格结构 |
| `load_entry_points()` | 手动触发 `pytexlogs.parsers` Entry Point 加载 |

### 3. 结构化数据类型 & 报告 API

| 符号 | 用途 |
|---|---|
| `ParsedPipelineReport` / `Report` | `run_pipeline` 返回值：汇总报告 + 元数据 |
| `ParsedLog` | 单个 parser 的单次解析结果 |
| `ToolResult` | 单个工具解析结果（Manager.run / parse_auxdir 返回） |
| `ToolResultStats` | 单个 ToolResult 的统计计数器结构 |
| `LogEntry` | 单条日志条目：level / file / line / text / error_pos_text |
| `LogLevel` | 枚举：ERROR / WARNING / INFO / ... |
| `BaseLogParser` | 所有自定义解析器的抽象基类 |
| `RefChangeTracker` | 参考文献引用变更跟踪器 |
| `load_report(path)` | 从 JSON 恢复 `ParsedPipelineReport` |
| `write_report(report, path)` | 把 `ParsedPipelineReport` 写入 JSON |
| `to_json(obj)` | 结构化导出：JSON 字符串 |
| `to_csv(obj)` | 结构化导出：CSV 字符串（表头 `file,line,level,category,tool,text,hint,source_path`） |
| `to_sarif(obj)` | 结构化导出：SARIF v2.1.0 最小子集 dict（CI / GitHub Code Scanning） |

### 4. 常量 / Hint 字典（面向人类）

| 符号 | 用途 |
|---|---|
| `CATEGORY_LABEL` | 6 大类别 → 中文标签 |
| `CATEGORY_ORDER` | 6 大类排序顺序 |
| `IMPORTANCE_LABEL` | importance high/medium/low → 中文 |
| `LATEX_LOG_HINTS` | pdflatex 常见错误 → 修复建议 |
| `BIBTEX_ERROR_HINTS` | bibtex 常见错误 → 修复建议 |
| `BIBER_WARNING_HINTS` | biber 常见警告 → 修复建议 |

### 5. 11 个内置 Parser 类

| 类名 | 对应工具 | category |
|---|---|---|
| `LatexLogParser` | pdflatex / xelatex / lualatex | compile |
| `BibtexParser` | bibtex | bibliography |
| `BiberParser` | biber | bibliography |
| `MakeindexParser` | makeindex | index |
| `XindyParser` | xindy | index |
| `GlossariesParser` | makeglossaries | glossary |
| `NomenclParser` | nomencl | glossary |
| `PythontexParser` | pythontex | code |
| `MintedParser` | minted (Pygments) | code |
| `AsymptoteParser` | asymptote (Asymptote 绘图) | graphic |

### 6. 演示入口

| 符号 | 用途 |
|---|---|
| `run_demo()` | 内置演示：生成样本日志 + 解析 + 打印摘要 |

## 插件化 · Entry Point 扩展

第三方包可通过 `pyproject.toml` 声明 Entry Point，PyTeXLogs 启动时自动加载：

```toml
[project.entry-points."pytexlogs.parsers"]
mychktex = "my_latex_tools.chktex:MyChktexParser"
mylacheck = "my_latex_tools.lacheck:MyLacheckParser"
```

加载后 `LogParserRegistry().lookup("mychktex")` 即可查找到自定义 parser，`LogParserManager().run(steps=["mychktex"], captured_outputs=...)` 即可执行解析。完整示例见 `examples/custom_parser_entrypoint.py`。

## CI · SARIF 上传告警示例

```yaml
# .github/workflows/ci.yml
name: LaTeX CI

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install uv && uv tool install --python 3.10 pytexlogs
      - name: 编译论文
        run: latexmk -pdf -outdir=build main.tex || true
      - name: 导出 SARIF
        run: pytexlogs export --format sarif ./build -o pytexlogs.sarif
      - name: 上传到 GitHub Code Scanning
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: pytexlogs.sarif
```

## 链接

- [CHANGELOG.md](./CHANGELOG.md) · 版本变更记录
- 许可证：**GPL-3.0-or-later**（与 [LICENSE](./LICENSE) 文件一致）
- PyPI：<https://pypi.org/project/pytexlogs/>
