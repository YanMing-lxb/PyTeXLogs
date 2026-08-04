"""PyTeXLogs 内置演示：解析示例日志并打印摘要。"""

import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def run_demo() -> None:
    """运行内置演示：创建示例日志 → 解析 → 打印摘要。"""
    from .core.engine import run_pipeline
    from .display import print_summary

    print("=" * 60)
    print("PyTeXLogs Integration Demo")
    print("=" * 60)

    with tempfile.TemporaryDirectory(prefix="pytexlogs_demo_") as tmpdir:
        tmp = Path(tmpdir)

        log_content = r"""
This is pdfTeX, Version 3.141592653-2.6-1.40.26 (TeX Live 2024)
entering extended mode
(./demo.tex
LaTeX2e <2024/02/28> patch level 1
(/usr/local/texlive/2024/texmf-dist/tex/latex/base/article.cls
Document Class: article 2023/07/15 v1.4n Standard LaTeX document class)
(./demo.aux)
! Undefined control sequence.
l.5 \foobar
                \bar
?
! Emergency stop.
l.5 \foobar
                \bar
!  ==> Fatal error occurred, no output PDF file produced!
"""
        log_path = tmp / "demo.log"
        log_path.write_text(log_content, encoding="utf-8")

        blg_content = r"""
This is BibTeX, Version 0.99d
The top-level auxiliary file: demo.aux
I found \citation{einstein} on the top-level auxiliary file.
I couldn't open database file references.bib
I found a \bibdata command while reading demo.aux.
Warning--I couldn't open database file references.bib
"""
        blg_path = tmp / "demo.blg"
        blg_path.write_text(blg_content, encoding="utf-8")

        results = run_pipeline(
            jobname="demo",
            auxdir=str(tmp),
            captured_outputs={
                "pdflatex": log_content,
                "bibtex": blg_content,
            },
            steps=["pdflatex", "bibtex"],
        )

        parsed_logs_list = []
        tool_results = getattr(results, 'tool_results', [])
        for r in tool_results:
            from .core.models import ParsedLog
            pl = ParsedLog(
                entries=getattr(r, "entries", []),
                raw_text=getattr(r, "raw_text", ""),
                source_path=getattr(r, "source_path", ""),
                tool_name=getattr(r, "tool_name", ""),
                category=getattr(r, "category", ""),
                importance=getattr(r, "importance", "low"),
            )
            parsed_logs_list.append(pl)

        summary = print_summary(parsed_logs_list, use_logger=False, non_quiet=True)
        print(summary)

    print("=" * 60)
    print("Demo completed.")