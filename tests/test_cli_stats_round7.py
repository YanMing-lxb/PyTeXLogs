"""第 4 轮 CLI 聚合口径回归（任务 19）。

CLI ``_aggregate_stats`` 必须与 ``easy.aggregate_stats`` 同口径：
- category / parser 按**条目数**聚合（不是工具结果 +1）；
- level 动态包含 font / graphic / page 等全部等级，不写死四档。
"""

from pytexlogs import ToolResultReport, aggregate_stats
from pytexlogs.cli.main import _aggregate_stats
from pytexlogs.core.models import ReportEntry


def _results() -> list[ToolResultReport]:
    return [
        ToolResultReport(
            tool_name="pdflatex",
            category="compile",
            entries=[
                ReportEntry(level="error", file="a.tex", line=1, text="e1"),
                ReportEntry(level="error", file="a.tex", line=2, text="e2"),
                ReportEntry(level="font", file="a.tex", line=3, text="f1"),
            ],
            stats={"entries_count": 3, "error": 2, "font": 1},
        ),
        ToolResultReport(
            tool_name="bibtex",
            category="bibliography",
            entries=[
                ReportEntry(level="warning", file="refs.bib", line=10, text="w1"),
                ReportEntry(level="graphic", file="refs.bib", line=20, text="g1"),
            ],
            stats={"entries_count": 2, "warning": 1, "graphic": 1},
        ),
    ]


def test_cli_category_matches_easy_entry_count() -> None:
    """category 按条目数：compile=3、bibliography=2（不是两个工具各 +1）。"""
    results = _results()
    cli_stats = _aggregate_stats(results, group_by="category")
    easy_stats = aggregate_stats(results, group_by="category")

    assert cli_stats == easy_stats == {"compile": 3, "bibliography": 2}


def test_cli_parser_matches_easy_entry_count() -> None:
    """parser 按条目数：pdflatex=3、bibtex=2。"""
    results = _results()
    cli_stats = _aggregate_stats(results, group_by="parser")
    easy_stats = aggregate_stats(results, group_by="parser")

    assert cli_stats == easy_stats == {"pdflatex": 3, "bibtex": 2}


def test_cli_level_includes_font_graphic_and_matches_easy() -> None:
    """level 动态覆盖 font/graphic；CLI 与 easy 数字一致。"""
    results = _results()
    cli_stats = _aggregate_stats(results, group_by="level")
    easy_stats = aggregate_stats(results, group_by="level")

    assert cli_stats == easy_stats
    assert cli_stats == {"error": 2, "font": 1, "warning": 1, "graphic": 1}
