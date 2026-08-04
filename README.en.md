# PyTeXLogs

PyTeXLogs is LaTeX/BibTeX/Biber/Minted/Asymptote/Makeindex log parser library. embeddable in any Python toolchain.

## Installation

```bash
# Recommended: add to project via uv
uv add pytexlogs

# Or via pip
pip install pytexlogs

# Optional enhancement: rich for pretty terminal tables
uv add pytexlogs[rich]

# CLI only: install as a global tool
uv tool install --python 3.10 pytexlogs
```

## Value Proposition · 6 Use Cases

| Scenario | Target Users | Pain Point Today | PyTeXLogs Solution |
|---|---|---|---|
| **IDE / Editor Integration** | VS Code LaTeX Workshop / Neovim users | Error parsing is scattered across each plugin's regex — error-prone and inconsistent | `parse_log_file` + `format_editor_jumps` produces `file:line:message` directly |
| **CI Quality Gate** | Research paper repos / team docs | CI logs are long, errors sink to the bottom; no Code Scanning alerts | CLI export SARIF → `github/codeql-action/upload-sarif` for visualization |
| **Local CLI Diagnostics** | Ordinary LaTeX authors | `pdflatex` output is hundreds of lines, errors are at the very end | `pytexlogs check main.log` — one-line summary + Hints, exit code = 1 |
| **Toolchain Secondary Dev** | latexmk / tectonic / arara wrapper authors | Existing tools don't diagnose; rewriting 11 parsers is costly | `parse_auxdir` one-liner gets all results + `aggregate_stats` for histograms |
| **Batch Teaching Reports** | LaTeX course TAs | Grading dozens of homework logs, manual stats are time-consuming | `pytexlogs export --format csv ./logs -o report.csv` batch summary |
| **Plugin Extension** | Custom tool developers | Missing ChkTeX / lacheck specific parsers | Entry Point mechanism: `[project.entry-points."pytexlogs.parsers"]` auto-register |

## Quick Start · 3 Copy-Paste Snippets

### 3.1 Parse a Single Log and Print Summary

```python
from pytexlogs import parse_log_file, print_summary

parsed = parse_log_file("tests/fixtures/sample.log")
print(f"Errors: {len(parsed.errors)}, Warnings: {len(parsed.warnings)}")
print_summary([parsed], use_logger=False, non_quiet=True)
```

Output:

```
Errors: 1, Warnings: 1
┌─────────────┬───────┬─────────┬──────────┐
│ Category    │ ERROR │ WARNING │ Total    │
├─────────────┼───────┼─────────┼──────────┤
│ compile     │ 1     │ 1       │ 2        │
└─────────────┴───────┴─────────┴──────────┘
```

### 3.2 CLI One-Liners

```bash
# Diagnose a single .log; exit code = 1 when ERRORs are present
pytexlogs check build/main.log

# English summary
pytexlogs summary ./main.log --lang en

# Batch export SARIF, upload alerts via GitHub Actions
pytexlogs export --format sarif ./build -o out.sarif
```

### 3.3 Entry Point Custom ChkTeX Parser

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

# Simulate entry point loading (real usage is declared in pyproject.toml)
registry = LogParserRegistry()
registry.register("mychktex", MyChktexParser)
mgr = LogParserManager(registry)
results = mgr.run("demo", ".", steps=["mychktex"],
                  captured_outputs={"mychktex": "Warning: Cmd terminated with space.\n"})
print(f"Custom parser produced {len(results[0].warnings)} lint warnings")
```

## Public API Index

Grouped by `__all__` six sections:

### 1. High-level Entrypoints

| Symbol | Purpose |
|---|---|
| `parse_log_file(path)` | One-liner to parse a single .log / .blg / .ilg etc. (auto-detects parser by extension) |
| `parse_log_text(text, engine="pdflatex")` | One-liner to parse text string (captured_outputs / subprocess.stdout scenarios) |
| `parse_auxdir(jobname, auxdir, steps, captured_outputs)` | One-liner to scan entire LaTeX auxiliary directory |
| `filter_severity(entries, min_level=WARNING)` | Filter log entries by severity |
| `aggregate_stats(obj, group_by="category\|level\|parser")` | Aggregated statistics → histogram / report data source |
| `run_pipeline(...)` | Full pipeline: discover → parse → aggregate → summarize → report (recommended) |
| `run_log_pipeline(...)` | Backward-compatible alias for `run_pipeline` (original 0.1.0 name) |
| `print_summary(results, ...)` | Terminal-friendly summary printing (includes error/warning totals, HINT dicts) |
| `show_log_entries(entries, ...)` | Visualize log entries one by one |
| `format_editor_jumps(entries)` | Generate editor jump list as `file:line: message` |
| `log_editor_jumps(entries)` | Output editor jump list via logging |
| `set_summary_language(lang, translate_fn=None)` | Set summary language globally (zh/en) or custom translation function |

### 2. Parser Manager / Custom Registration (Extension API)

| Symbol | Purpose |
|---|---|
| `LogParserManager` / `Manager` | Manager that dispatches multiple parsers by step/suffix |
| `LogParserRegistry` / `Registry` | Parser registry: 11 built-in + Entry Point auto-loading |
| `LogParserSpec` | Single parser spec structure |
| `load_entry_points()` | Manually trigger `pytexlogs.parsers` Entry Point loading |

### 3. Structured Data Types & Report API

| Symbol | Purpose |
|---|---|
| `ParsedPipelineReport` / `Report` | `run_pipeline` return value: aggregated report + metadata |
| `ParsedLog` | Single parser result for one parse |
| `ToolResult` | Single tool parse result (returned by Manager.run / parse_auxdir) |
| `ToolResultStats` | Counter structure for a single ToolResult |
| `LogEntry` | Single log entry: level / file / line / text / error_pos_text |
| `LogLevel` | Enum: ERROR / WARNING / INFO / ... |
| `BaseLogParser` | Abstract base class for all custom parsers |
| `RefChangeTracker` | Reference citation change tracker |
| `load_report(path)` | Restore `ParsedPipelineReport` from JSON |
| `write_report(report, path)` | Write `ParsedPipelineReport` to JSON |
| `to_json(obj)` | Structured export: JSON string |
| `to_csv(obj)` | Structured export: CSV string (header `file,line,level,category,tool,text,hint,source_path`) |
| `to_sarif(obj)` | Structured export: SARIF v2.1.0 minimal subset dict (CI / GitHub Code Scanning) |

### 4. Constants / Hint Dictionaries (Human-facing)

| Symbol | Purpose |
|---|---|
| `CATEGORY_LABEL` | 6 categories → Chinese labels |
| `CATEGORY_ORDER` | 6 categories sorted order |
| `IMPORTANCE_LABEL` | importance high/medium/low → Chinese |
| `LATEX_LOG_HINTS` | Common pdflatex errors → fix suggestions |
| `BIBTEX_ERROR_HINTS` | Common bibtex errors → fix suggestions |
| `BIBER_WARNING_HINTS` | Common biber warnings → fix suggestions |

### 5. 11 Built-in Parser Classes

| Class Name | Corresponding Tool | category |
|---|---|---|
| `LatexLogParser` | pdflatex / xelatex / lualatex | compile |
| `BibtexParser` | bibtex | bibliography |
| `BiberParser` | biber | bibliography |
| `MakeindexParser` | makeindex | index |
| `XindyParser` | xindy | index |
| `GlossariesParser` | makeglossaries | index |
| `NomenclParser` | nomencl | index |
| `PythontexParser` | pythontex | code |
| `MintedParser` | minted (Pygments) | code |
| `AsymptoteParser` | asymptote (Asymptote graphics) | graphic |

### 6. Demo Entrypoint

| Symbol | Purpose |
|---|---|
| `run_demo()` | Built-in demo: generate sample log + parse + print summary |

## Plugin System · Entry Point Extension

Third-party packages can declare Entry Points via `pyproject.toml`, loaded automatically by PyTeXLogs on startup:

```toml
[project.entry-points."pytexlogs.parsers"]
mychktex = "my_latex_tools.chktex:MyChktexParser"
mylacheck = "my_latex_tools.lacheck:MyLacheckParser"
```

Once loaded, `LogParserRegistry().lookup("mychktex")` finds the custom parser, and `LogParserManager().run(steps=["mychktex"], captured_outputs=...)` executes parsing. See full example in `examples/custom_parser_entrypoint.py`.

## CI · SARIF Upload Alert Example

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
      - name: Compile paper
        run: latexmk -pdf -outdir=build main.tex || true
      - name: Export SARIF
        run: pytexlogs export --format sarif ./build -o pytexlogs.sarif
      - name: Upload to GitHub Code Scanning
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: pytexlogs.sarif
```

## Links

- [CHANGELOG.md](./CHANGELOG.md) · Release notes
- License: **GPL-3.0-or-later** (consistent with the [LICENSE](./LICENSE) file)
- PyPI: <https://pypi.org/project/pytexlogs/>
