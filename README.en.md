# PyTeXLogs - Standalone Log Parser Library

PyTeXLogs is an independent LaTeX/BibTeX/Biber/Minted/Asymptote/Makeindex log parser library extracted from PyTeXMK v1.1.0. Zero runtime third-party dependencies, can be embedded in any Python toolchain.

Install: `uv add pytexlogs`

## Core Features

- 11 log parser classes (LaTeX/BibTeX/Biber/Minted/Asymptote/Makeindex/Glossaries/Nomencl/Xindy/PythonTeX + manager)
- Pure function utilities: format_editor_jumps / print_summary / log_editor_jumps / show_log_entries
- Rich Hint dictionaries (LATEX_LOG_HINTS / BIBTEX_ERROR_HINTS / BIBER_WARNING_HINTS)
- Four-level LogLevel hierarchy (DEBUG/INFO/WARNING/ERROR)
- Zero runtime third-party dependencies
- Unified pipeline entry point run_log_pipeline(...)

## Minimal Example

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

## License

GPL-3.0-or-later (consistent with the LICENSE file)
