"""PyTeXLogs 高阶便捷函数（5 个 one-liner 公共 API）。

面向新用户的「1 行代码用起来」快速入口：
  - parse_log_file(path) / parse_log_text(text)：一键解析单个日志；
  - parse_auxdir(jobname, auxdir)：一键跑整个 latexmk/PyTeX 辅助目录；
  - filter_severity(entries, min_level=WARNING)：按严重度裁剪日志条目；
  - aggregate_stats(obj, group_by="category")：聚合统计，直接给直方图/CSV 报表用。

0.6.1 起，"step/后缀 → 解析器"的映射只由 :class:`LogParserRegistry` 维护，
本模块不再自带第二份 ``_ENGINE_DEFAULT_PARSER`` 表（历史问题是两表漂移，
`engine="asy"` 会静默回退到 LaTeX 解析器并返回空结果）。
"""

from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Literal, overload

from .core.manager import LogParserManager, ToolResult
from .core.models import BaseLogParser, LogEntry, LogLevel, ParsedLog, ParsedPipelineReport
from .core.registry import LogParserRegistry

__all__ = [
    "aggregate_stats",
    "filter_severity",
    "parse_auxdir",
    "parse_log_file",
    "parse_log_text",
]

#: spec 重要性排序：同后缀命中多个解析器时，优先高重要性，其次按注册顺序。
_IMPORTANCE_RANK: dict[str, int] = {"high": 0, "medium": 1, "low": 2}


def _registry() -> LogParserRegistry:
    return LogParserRegistry.get_instance()


def _parser_for_engine(engine: str) -> type[BaseLogParser]:
    """按 step 名取解析器；名字非法时直接报错，不再静默回退。"""
    spec = _registry().lookup(engine.lower())
    if spec is None:
        available = ", ".join(_registry().all_step_names())
        raise ValueError(f"未知引擎 {engine!r}；可选：{available}")
    return spec.parser_cls


def _guess_parser_from_path(path: Path) -> type[BaseLogParser]:
    """按日志文件后缀与头部特征在注册表里找解析器；找不到时回退 LaTeX。

    说明：
    - 后缀匹配一律以注册表为准（最长后缀优先），不再维护第二份映射表；
    - ``.blg`` 在 bibtex/biber 之间本身有歧义：先看日志头部，再用同名 ``.bcf``
      兜底判定；
    - ``.bcf`` 不是日志，只是 Biber 的 XML 控制文件；显式传入时交给 Biber
      提取 citekey 统计，不产生日志条目；
    - ``.ilg`` 用头部区分 makeindex/xindy；
    - ``.glg/.alg/.slg`` 统一交给 GlossariesParser（它内部兼容 xindy 输出），
      与目录模式的 step 规划保持一致。
    """
    name = path.name.lower()
    registry = _registry()
    from .core.logkind import sniff_bib_tool, sniff_index_tool

    if name.endswith(".blg"):
        return _parser_for_engine(sniff_bib_tool(path))
    if name.endswith(".bcf"):
        return _parser_for_engine("biber")
    if name.endswith(".ilg"):
        return _parser_for_engine(sniff_index_tool(path))
    if name.endswith((".glg", ".alg", ".slg")):
        return _parser_for_engine("makeglossaries")

    for suffix in registry.all_suffixes():
        if not name.endswith(suffix):
            continue
        specs = sorted(
            registry.lookup_by_suffix(suffix),
            key=lambda s: _IMPORTANCE_RANK.get(s.importance, 3),
        )
        if specs:
            return specs[0].parser_cls

    return _parser_for_engine("pdflatex")


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
    parser_cls = _parser_for_engine(engine) if engine is not None else _guess_parser_from_path(p)
    parser = parser_cls(root_file=root_file)
    return parser.parse_file(p, root_file=root_file)


def parse_log_text(
    text: str,
    *,
    engine: str = "pdflatex",
    root_file: str | None = None,
) -> ParsedLog:
    """一行代码解析日志字符串（用于 captured_outputs / subprocess.stdout 场景）。"""
    parser = _parser_for_engine(engine)(root_file=root_file)
    return parser.parse(text, root_file=root_file)


def parse_auxdir(
    jobname: str,
    auxdir: str | Path,
    steps: list[str] | None = None,
    captured_outputs: dict[str, str] | None = None,
    *,
    root_file: str | None = None,
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
        root_file=root_file,
    )


def filter_severity(
    entries: Iterable[LogEntry],
    *,
    min_level: LogLevel = LogLevel.WARNING,
) -> list[LogEntry]:
    """按严重度过滤条目：保留 ``entry.level <= min_level``。

    顺序按 :class:`LogLevel` 的 severity：
    ``ERROR < WARNING < INFO < TYPESET < FONT < GRAPHIC < PAGE``。
    """
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
    group_by="level" → key 是 level.value（error/warning/typesetting/...），value 是条目数
    group_by="parser" → key 是 tool_name（pdflatex/bibtex/...），value 是条目数
    """
    if isinstance(obj, ParsedPipelineReport):
        raw_results: list[Any] = list(obj.tool_results or [])
    else:
        raw_results = list(obj)
    if group_by not in ("category", "level", "parser"):
        raise ValueError(f"未知 group_by={group_by!r}；可选：category/level/parser")
    counter: Counter[str] = Counter()
    for r in raw_results:
        cat = getattr(r, "category", None) or "unknown"
        tname = getattr(r, "tool_name", None) or "unknown"
        entries = getattr(r, "entries", [])
        if group_by == "category":
            counter[cat] += len(entries)
        elif group_by == "parser":
            counter[tname] += len(entries)
        elif group_by == "level":
            for e in entries:
                lvl = getattr(e, "level", "info")
                if hasattr(lvl, "value"):
                    counter[str(lvl.value)] += 1
                else:
                    counter[str(lvl)] += 1
        else:
            raise ValueError(f"未知 group_by={group_by!r}；可选：category/level/parser")
    return dict(counter)
