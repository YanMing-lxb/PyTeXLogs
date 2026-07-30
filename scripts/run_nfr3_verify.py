#!/usr/bin/env python3
"""PyTeXLogs NFR-3 standalone verify (G6 namespace B)."""
from __future__ import annotations

import argparse
import importlib
import shutil
import sys
import tempfile
from pathlib import Path


def _run_checks(pytexlogs):
    required_symbols = [
        "LatexLogParser", "BibtexParser", "BiberParser", "AsymptoteParser",
        "MintedParser", "PythontexParser", "GlossariesParser", "MakeindexParser",
        "NomenclParser", "XindyParser", "LogParserManager", "LogLevel",
        "LogEntry", "ParsedLog", "ParsedPipelineReport", "RefChangeTracker",
        "BaseLogParser", "LogParserRegistry", "LogParserSpec", "print_summary",
        "format_editor_jumps", "log_editor_jumps", "show_log_entries",
        "run_log_pipeline", "LATEX_LOG_HINTS", "BIBTEX_ERROR_HINTS",
        "BIBER_WARNING_HINTS", "CATEGORY_LABEL", "CATEGORY_ORDER",
        "IMPORTANCE_LABEL", "load_report", "write_report", "run_demo",
    ]

    all_count = len(pytexlogs.__all__) if hasattr(pytexlogs, "__all__") else 0
    symbols_ok = all_count >= 33
    for sym in required_symbols:
        if not hasattr(pytexlogs, sym):
            symbols_ok = False
            break
    if symbols_ok:
        print("PASS-1: symbols full (len(__all__)=%d, key symbols present)" % all_count)
    else:
        print("FAIL-1: symbols missing (len(__all__)=%d)" % all_count)
        sys.exit(1)

    LatexLogParser = pytexlogs.LatexLogParser
    LogLevel = pytexlogs.LogLevel
    lines_data = [r"main.tex:42: Undefined control sequence \foo"]
    parsed = LatexLogParser(quiet=True).parse_lines(lines_data)
    ok = (
        len(parsed.entries) >= 1
        and parsed.entries[0].line == 42
        and parsed.entries[0].level == LogLevel.ERROR
    )
    if ok:
        print("PASS-2: LatexLogParser parsed line=42, level=ERROR")
    else:
        print("FAIL-2: LatexLogParser basic parse failed")
        sys.exit(1)

    format_editor_jumps = pytexlogs.format_editor_jumps
    parsed2 = LatexLogParser(quiet=True).parse_lines([
        r"chapters/intro.tex:7: LaTeX Error: Something\'s wrong--perhaps a missing \item."
    ])
    jumps = format_editor_jumps(parsed2.entries)
    ok = isinstance(jumps, list) and len(jumps) >= 1
    if ok:
        print("PASS-3: format_editor_jumps returned non-empty list")
    else:
        print("FAIL-3: format_editor_jumps failed")
        sys.exit(1)

    run_log_pipeline = pytexlogs.run_log_pipeline
    try:
        report = run_log_pipeline(
            quiet=True,
            print_terminal=False,
            pytexmk_version="0.1.0",
            ref_tracker_translate_fn=None,
        )
        ok = report is not None
    except Exception as exc:
        ok = False
        print("run_log_pipeline exception:", exc)
    if ok:
        print("PASS-4: run_log_pipeline no exception")
    else:
        print("FAIL-4: run_log_pipeline raised exception or returned None")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="NFR-3 pytexlogs standalone verify")
    parser.add_argument("--isolated", action="store_true", help="strict isolated mode")
    args = parser.parse_args()

    if args.isolated:
        project_root = Path(__file__).resolve().parent.parent
        src_pytexlogs_dir = project_root / "src" / "pytexlogs"
        tmpdir = tempfile.mkdtemp(prefix="pytexlogs_nfr3_")
        try:
            dst = Path(tmpdir) / "pytexlogs"
            shutil.copytree(str(src_pytexlogs_dir), str(dst))
            src_pytexlogs_str = str(src_pytexlogs_dir.resolve())
            src_dir_str = str((project_root / "src").resolve())
            filtered = []
            for p in sys.path:
                try:
                    pp = str(Path(p).resolve())
                except Exception:
                    pp = p
                is_src_pytexlogs = (
                    pp == src_pytexlogs_str
                    or pp.startswith(src_pytexlogs_str + "\\\\")
                    or pp.startswith(src_pytexlogs_str + "/")
                )
                is_src_dir = (
                    pp == src_dir_str
                    or pp.startswith(src_dir_str + "\\\\")
                    or pp.startswith(src_dir_str + "/")
                )
                is_pth_pytexlogs = (
                    "pytexlogs.egg-info" in pp
                    or "__editable__.pytexlogs" in pp
                )
                if is_src_pytexlogs or is_src_dir or is_pth_pytexlogs:
                    continue
                filtered.append(p)
            sys.path = [tmpdir] + filtered
            if "pytexlogs" in sys.modules:
                del sys.modules["pytexlogs"]
            for k in list(sys.modules.keys()):
                if k.startswith("pytexlogs."):
                    del sys.modules[k]
            pytexlogs = importlib.import_module("pytexlogs")
            _run_checks(pytexlogs)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    else:
        project_root = Path(__file__).resolve().parent.parent
        src_dir = project_root / "src"
        sys.path.insert(0, str(src_dir))
        pytexlogs = importlib.import_module("pytexlogs")
        _run_checks(pytexlogs)

    print("G6_PASS_NAMESPACE_B: pytexlogs standalone OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
