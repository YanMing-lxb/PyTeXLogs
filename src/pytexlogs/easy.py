"""PyTeXLogs 高阶便捷函数（5 个 one-liner 公共 API）。

面向新用户的「1 行代码用起来」快速入口：
  - parse_log_file(path) / parse_log_text(text)：一键解析单个日志；
  - parse_auxdir(jobname, auxdir)：一键跑整个 latexmk/PyTeX 辅助目录；
  - filter_severity(entries, min_level=WARNING)：按严重度裁剪日志条目；
  - aggregate_stats(obj, group_by="category")：聚合统计，直接给直方图/CSV 报表用。
"""

from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Literal, overload

from .core.manager import LogParserManager, ToolResult
from .core.models import BaseLogParser, LogEntry, LogLevel, ParsedLog, ParsedPipelineReport
from .parsers.asymptote import AsymptoteParser
from .parsers.biber import BiberParser
from .parsers.bibtex import BibtexParser
from .parsers.glossaries import GlossariesParser
from .parsers.latex import LatexLogParser
from .parsers.makeindex import MakeindexParser
from .parsers.minted import MintedParser
from .parsers.nomencl import NomenclParser
from .parsers.pythontex import PythontexParser
from .parsers.xindy import XindyParser

__all__ = [
    "aggregate_stats",
    "filter_severity",
    "parse_auxdir",
    "parse_log_file",
    "parse_log_text",
]


_ENGINE_DEFAULT_PARSER: dict[str, type[BaseLogParser]] = {
    "pdflatex": LatexLogParser,
    "xelatex": LatexLogParser,
    "lualatex": LatexLogParser,
    "latex": LatexLogParser,
    "bibtex": BibtexParser,
    "biber": BiberParser,
    "makeindex": MakeindexParser,
    "xindy": XindyParser,
    "makeglossaries": GlossariesParser,
    "glossaries": GlossariesParser,
    "nomencl": NomenclParser,
    "pythontex": PythontexParser,
    "minted": MintedParser,
    "asymptote": AsymptoteParser,
}


def _guess_parser_from_path(path: Path) -> type[BaseLogParser]:
    """根据日志文件后缀名/小写 stem 猜最合适的 parser。找不到就回退 LatexLogParser。"""
    name = path.name.lower()
    if name.endswith(".blg"):
        return _ENGINE_DEFAULT_PARSER["bibtex"]
    if name.endswith((".bcf", ".blg-biber")):
        return _ENGINE_DEFAULT_PARSER["biber"]
    if name.endswith((".idx", ".ind", ".ilg")):
        return _ENGINE_DEFAULT_PARSER["makeindex"]
    if name.endswith((".xdy", ".xlg")):
        return _ENGINE_DEFAULT_PARSER["xindy"]
    if name.endswith((".glo", ".gls")) or "glossary" in name:
        return _ENGINE_DEFAULT_PARSER["glossaries"]
    if "nomencl" in name or name.endswith((".nls", ".nlo")):
        return _ENGINE_DEFAULT_PARSER["nomencl"]
    if "pythontex" in name:
        return _ENGINE_DEFAULT_PARSER["pythontex"]
    if "minted" in name or ".pyg" in name:
        return _ENGINE_DEFAULT_PARSER["minted"]
    if "asy" in name or name.endswith(".log") and (path.stem.lower().endswith("_asy")):
        return _ENGINE_DEFAULT_PARSER["asymptote"]
    return _ENGINE_DEFAULT_PARSER["pdflatex"]


def parse_log_file(
    path: str | Path,
    *,
    engine: str | None = None,
    root_file: str | None = None,
) -> ParsedLog:
    """一行代码解析单个日志文件。

    Args:
        path: .log / .blg / .ilg / .xlg 等日志文件路径
        engine: 可选，显式指定 engine（pdflatex/bibtex/biber/...）；不写时按后缀名猜
        root_file: 可选，传给 parser 的主 .tex 路径（与 parse_file 语义一致）
    """
    p = Path(path)
    parser_cls: type[BaseLogParser]
    if engine is not None:
        parser_cls = _ENGINE_DEFAULT_PARSER.get(engine.lower(), _ENGINE_DEFAULT_PARSER["pdflatex"])
    else:
        parser_cls = _guess_parser_from_path(p)
    parser = parser_cls(root_file=root_file)
    return parser.parse_file(p, root_file=root_file)


def parse_log_text(
    text: str,
    *,
    engine: str = "pdflatex",
    root_file: str | None = None,
) -> ParsedLog:
    """一行代码解析日志字符串（用于 captured_outputs / subprocess.stdout 场景）。"""
    parser_cls = _ENGINE_DEFAULT_PARSER.get(engine.lower(), _ENGINE_DEFAULT_PARSER["pdflatex"])
    parser = parser_cls(root_file=root_file)
    return parser.parse(text, root_file=root_file)


def parse_auxdir(
    jobname: str,
    auxdir: str | Path,
    steps: list[str] | None = None,
    captured_outputs: dict[str, str] | None = None,
) -> list[ToolResult]:
    """一行代码扫描整个 LaTeX 辅助目录，拿到所有解析结果。

    Returns:
        list[ToolResult]：与 LogParserManager.run 返回类型一致
    """
    return LogParserManager().run(
        jobname=jobname,
        auxdir=auxdir,
        steps=steps,
        captured_outputs=captured_outputs,
    )


def filter_severity(
    entries: Iterable[LogEntry],
    *,
    min_level: LogLevel = LogLevel.WARNING,
) -> list[LogEntry]:
    """按严重度过滤条目：保留 entry.level <= min_level（ERROR < WARNING < INFO）。"""
    return [e for e in entries if not (min_level < e.level)]


@overload
def aggregate_stats(
    obj: list[ToolResult] | ParsedPipelineReport,
    *,
    group_by: Literal["category"] = "category",
) -> dict[str, int]: ...


@overload
def aggregate_stats(
    obj: list[ToolResult] | ParsedPipelineReport,
    *,
    group_by: Literal["level"],
) -> dict[str, int]: ...


@overload
def aggregate_stats(
    obj: list[ToolResult] | ParsedPipelineReport,
    *,
    group_by: Literal["parser"],
) -> dict[str, int]: ...


def aggregate_stats(
    obj: list[ToolResult] | ParsedPipelineReport,
    *,
    group_by: Literal["category", "level", "parser"] = "category",
) -> dict[str, int]:
    """对一组 ToolResult 或整个 ParsedPipelineReport 聚合统计。

    group_by="category" → key 是 category（bibliography/index/code/...），value 是条目数
    group_by="level" → key 是 level.value（error/warning/info/...），value 是条目数
    group_by="parser" → key 是 tool_name（pdflatex/bibtex/...），value 是条目数
    """
    if isinstance(obj, ParsedPipelineReport):
        raw_results: list[Any] = list(obj.tool_results or [])
    else:
        raw_results = list(obj)
    counter: Counter[str] = Counter()
    for r in raw_results:
        cat = getattr(r, "category", None) or "unknown"
        tname = getattr(r, "tool_name", None) or "unknown"
        entries = getattr(r, "entries", [])
        if group_by == "category":
            counter[cat] += len(entries)
        elif group_by == "parser":
            counter[tname] += len(entries)
        else:  # level
            for e in entries:
                lvl = getattr(e, "level", "info")
                if hasattr(lvl, "value"):
                    counter[str(lvl.value)] += 1
                else:
                    counter[str(lvl)] += 1
    return dict(counter)