# PyTeXLogs

PyTeXLogs 是从 PyTeXMK v1.1.0 抽离的独立 LaTeX/BibTeX/Biber/Minted/Asymptote/Makeindex 日志解析库。零运行时第三方依赖，可嵌入任意 Python 工具链。

安装：`uv add pytexlogs`

## 核心特性

- 11 类日志 parser（LaTeX/BibTeX/Biber/Minted/Asymptote/Makeindex/Glossaries/Nomencl/Xindy/PythonTeX + 管理器）
- 纯函数工具 format_editor_jumps / print_summary / log_editor_jumps / show_log_entries
- 丰富 Hint 字典（LATEX_LOG_HINTS / BIBTEX_ERROR_HINTS / BIBER_WARNING_HINTS）
- LogLevel 四级分层（DEBUG/INFO/WARNING/ERROR）
- 零 runtime 第三方依赖
- 统一 pipeline 入口 run_log_pipeline(...)

## 最小示例

```python
from pytexlogs import (
    LatexLogParser, LogLevel, format_editor_jumps, run_log_pipeline, print_summary,
)

# 1 基本解析
p = LatexLogParser(quiet=True)
lines = [r"main.tex:42: Undefined control sequence \foo"]
parsed = p.parse_lines(lines)
assert len(parsed.entries) >= 1
assert parsed.entries[0].line == 42
assert parsed.entries[0].level == LogLevel.ERROR
print("PASS-2: parse ok")

# 2 Editor jump
jumps = format_editor_jumps(parsed.entries)
assert isinstance(jumps, list)
print(f"PASS-3: jumps={len(jumps)}")

# 3 pipeline 入口，不传 ref_tracker_translate_fn 即可
report = run_log_pipeline(
    quiet=True,
    print_terminal=False,
    pytexmk_version="0.1.0",
    ref_tracker_translate_fn=None,
)
print_summary([], use_logger=False, non_quiet=False)
print("PASS-4: pipeline ok")
```

## 许可证

GPL-3.0-or-later（与 LICENSE 文件一致）
