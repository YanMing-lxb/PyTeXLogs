"""性能：LatexLogParser 解析 10 万行 main.log 耗时 <300ms。
仅在环境变量 CI_PERF=1 时启用；本地默认跳过，避免拖慢开发。
"""
import os
import pathlib
import time

import pytest

from pytexlogs import LatexLogParser

BASE = (
    "This is pdfTeX, Version 3.141592653-2.6-1.40.25 (TeX Live 2024) (preloaded format=pdflatex 2026.7.31)\n"
    "entering extended mode\n"
    " restricted \\write18 enabled.\n"
    "(./main.tex\n"
    "LaTeX2e <2024-06-01> patch level 2\n"
    "L3 programming layer <2024-08-16>\n"
    "(/usr/local/texlive/2024/texmf-dist/tex/latex/base/article.cls\n"
    "Document Class: article 2024/02/08 v1.4n Standard LaTeX document class\n"
    "(/usr/local/texlive/2024/texmf-dist/tex/latex/base/size10.clo))\n"
    "(/usr/local/texlive/2024/texmf-dist/tex/latex/hyperref/hyperref.sty\n"
    "Package hyperref Message: Driver (autodetected): hpdftex.\n"
    ")\n"
    "No file main.aux.\n"
    "(./main.aux) (./main.out) (./main.out)\n"
    "LaTeX Warning: Reference `fig:arch' on page 1 undefined on input line 56.\n"
    "LaTeX Warning: Reference `tbl:perf' on page 2 undefined on input line 120.\n"
    "! Undefined control sequence.\n"
    "l.203 \\badcmd\n"
    "The control sequence at the end of the top line\n"
    "of your error message was never \\def'ed. If you have misspelled it (e.g., `\\def\\a'),\n"
    "type I \\def\\a{...} to define it now.\n"
    "! Emergency stop.\n"
    "l.203 \\badcmd\n"
    "!  ==> Fatal error occurred, no output PDF file produced!\n"
    "Transcript written on main.log.\n"
)


@pytest.mark.skipif(os.environ.get("CI_PERF") != "1", reason="only run when CI_PERF=1")
def test_parse_100k_lines_under_300ms(tmp_path: pathlib.Path) -> None:
    one_k = "\n".join(BASE for _ in range(40))
    log_text = "\n".join(one_k for _ in range(100))
    assert len(log_text.splitlines()) >= 100_000, len(log_text.splitlines())
    p = tmp_path / "big.log"
    p.write_text(log_text, encoding="utf-8")
    parser = LatexLogParser()
    t0 = time.perf_counter()
    parsed = parser.parse_file(p)
    elapsed = time.perf_counter() - t0
    print(f"[perf] lines={len(log_text.splitlines())} entries={len(parsed.entries)} elapsed_ms={elapsed*1000:.2f}")
    assert len(parsed.errors) >= 1
    assert elapsed < 0.300, f"LatexLogParser 100k lines too slow: {elapsed*1000:.2f}ms > 300ms"
