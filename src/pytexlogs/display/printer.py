"""终端输出逻辑：打印摘要、显示日志条目、编辑器跳转。"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import IO, Any

from ..core.models import (
    LogEntry,
    ParsedLog,
    ReportEntry,
    ToolResult,
    ToolResultReport,
    level_from_value,
)
from . import formatter as _formatter
from .formatter import (
    _LEVEL_DISPLAY,
    CATEGORY_LABEL,
    CATEGORY_ORDER,
    ENTRY_INDENT,
    _display_path,
    _format_entry_lines,
    _format_hint_lines,
    _format_ref_block,
    _format_title_rule,
    _format_top_cited,
    _group_by,
    _markup_escape,
    _measure,
    _strip_rich_markup,
    _t,
    resolve_summary_width,
    set_summary_language,
)

logger = logging.getLogger(__name__)


def _log_fn(level: str) -> Callable[[str], None]:
    """按等级元数据取日志方法；提示级统一走 info，避免误记成 warning。"""
    return getattr(logger, _LEVEL_DISPLAY[level].logger_level)


_RICH_CONSOLE: Any = None


class _FallbackConsole:
    """PyTeXLogs 无 rich 时的最小兼容桩。

    ``emit`` 在 fallback 分支传入的是已经构造好的 plain 文本，不能再做 markup
    正则剥离，否则 ``[E]`` / ``[一般编译]`` 这类字面标签会被误删。
    """

    def print(self, *objects: Any, **kwargs: Any) -> None:
        if len(objects) == 0:
            print(end=kwargs.get("end", "\n"))
            return
        print(
            kwargs.get("sep", " ").join(str(o) for o in objects),
            end=kwargs.get("end", "\n"),
        )


def _get_console() -> Any:
    """惰性创建 rich Console；未安装 rich 时回退到纯文本桩。

    不在模块导入时急切 import rich：``run_pipeline`` 会在模块顶层 import 本模块，
    但只跑解析/导出、不打印摘要的调用方不应为可选依赖付出启动开销。
    """
    global _RICH_CONSOLE
    if _RICH_CONSOLE is not None:
        return _RICH_CONSOLE
    try:
        from rich.console import Console

        _RICH_CONSOLE = Console(highlight=False, markup=True, soft_wrap=False)
    except Exception:
        _RICH_CONSOLE = _FallbackConsole()
    return _RICH_CONSOLE


def _print_to_stream(stream: IO[str], markup: str, plain: str) -> None:
    """将输出写到 stream：优先使用调用方给定的 plain，避免误删字面方括号。

    类别标签 ``[一般编译]`` 与级别符号 ``[E]`` 在结构上也是方括号文本；再用
    rich 的正则去剥 markup 会把它们一并删掉。
    """
    stripped = plain if plain else _strip_rich_markup(markup)
    stream.write(stripped)
    if not stripped.endswith("\n"):
        stream.write("\n")


def log_editor_jumps(entries: list[LogEntry], logger: logging.Logger | None = None, level: int = logging.INFO) -> None:
    logger = logger or logging.getLogger("pytexlogs")
    sorted_entries = sorted(entries, key=lambda e: (e.level.value, e.file, e.line))
    for e in sorted_entries:
        pathname = _display_path(str(e.file or ""), str(Path.cwd()))
        msg = f"{pathname}:{e.line}: {e.text}"
        logger.log(level, msg)


def print_summary(
    parsed_logs: list[ParsedLog],
    ref_change_report: str | None = None,
    non_quiet: bool = True,
    use_logger: bool = True,
    show_info: bool = False,
    ref_added_keys: list[str] | None = None,
    ref_removed_keys: list[str] | None = None,
    ref_total: int | None = None,
    ref_unchanged: int | None = None,
    ref_key_counts: dict[str, int] | None = None,
    text_len_fn: Callable[[str], int] | None = None,
    *,
    language: str | None = None,
    translate_fn: Callable[[str], str] | None = None,
    stream: IO[str] | None = None,
    max_entries: int | None = None,
    show_hints: bool = False,
    jobname: str | None = None,
    root_file: str | None = None,
    width: int | None = None,
) -> str:
    """按类别/等级分组打印日志摘要并返回拼接字符串。

    Args:
        max_entries: 每个「等级 × 类别」分组最多展示的条目数；``None`` 表示全量。
            超出部分折叠为一行「还有 N 条」，避免几十条 overfull 淹没真正的错误。
        show_hints: 是否为 ERROR/WARNING 条目追加一行可执行建议（见 :mod:`pytexlogs.hints`）。
        jobname: 可选项目 jobname，用于把 hint 里的 ``biber <jobname>`` 替换正确。
        root_file: 可选主 ``.tex`` 路径；子文件条目不能自己充当项目根文件。
        width: 版式宽度；``None`` 沿用 :data:`SUMMARY_TOTAL_LEN`（74）。PyTeXMK 等
            调用方可按自身控制台宽度传入，小于 ``MIN_SUMMARY_WIDTH`` 时自动收敛。
    """
    prev_lang: str | None = None
    prev_tfn: Callable[[str], str] | None = None
    if language is not None or translate_fn is not None:
        prev_lang = _formatter._LANG
        prev_tfn = _formatter._TRANSLATE_FN
        set_summary_language(language or _formatter._LANG, translate_fn=translate_fn)

    def _out(markup: str, plain: str) -> None:
        if stream is not None:
            _print_to_stream(stream, markup, plain)

    try:
        layout_width = resolve_summary_width(width)
        display_cwd = str(Path.cwd())
        grouped = _group_by(parsed_logs)
        output_lines: list[str] = []
        #: ``_group_by`` 只保留 entry；hint 需要知道来源工具，才能把 Biber 的
        #: ``WARN -`` 之类规则限制在 Biber 日志里。用对象身份映射，不改 LogEntry。
        entry_tools: dict[int, str] = {}
        for plog in parsed_logs:
            tool = getattr(plog, "tool_name", "") or ""
            if tool:
                entry_tools.update({id(entry): tool for entry in plog.entries})

        def emit(markup: str, plain: str, log_fn: Callable[[str], None] | None = None) -> None:
            """三路输出的唯一入口：logger / stream / rich console，同时记进返回值。

            0.5 把这套 if/elif/else 逐条复制了 12 处，任何一处忘改就会让终端与
            日志里的同一段内容不一致；收敛到这里后只有这一份分派逻辑。
            """
            output_lines.append(plain)
            if use_logger:
                (log_fn or logger.info)(plain)
            elif stream is not None:
                _out(markup, plain)
            else:
                console = _get_console()
                if isinstance(console, _FallbackConsole):
                    console.print(plain)
                else:
                    console.print(markup, width=layout_width)

        levels_to_show: list[str] = []
        if non_quiet:
            levels_to_show = ["error", "warning"]
            if show_info:
                # 提示级：排版/字体/图形/页面只有在 --show-info 下展开，
                # 否则 Overfull、缺字体等会被整组丢弃、用户完全看不到。
                levels_to_show.extend(["info", "typesetting", "font", "graphic", "page"])
        else:
            levels_to_show = ["error"]

        for level in levels_to_show:
            categories_data = grouped[level]
            total_entries = sum(len(categories_data[cat]) for cat in CATEGORY_ORDER)
            if total_entries == 0:
                continue

            level_meta = _LEVEL_DISPLAY[level]
            log_fn = _log_fn(level)
            level_title = _t(level_meta.title)
            title_plain = f"{level_title} · {total_entries}"
            head_markup, head_plain = _format_title_rule(title_plain, layout_width, level_meta.title_style, text_len_fn)
            emit(head_markup, head_plain, log_fn)

            for cat in CATEGORY_ORDER:
                entries = categories_data[cat]
                if not entries:
                    continue

                cat_label_text = _t(CATEGORY_LABEL.get(cat, cat))
                cat_label = f"[{cat_label_text}]"
                cat_prefix = f"+-- {cat_label} · {len(entries)} "
                dashes_count = max(0, layout_width - _measure(cat_prefix, text_len_fn))
                cat_plain = f"{cat_prefix}{'-' * dashes_count}"
                cat_markup = (
                    f"[bold #d79921]+--[/] [bold]{_markup_escape(cat_label)}[/] "
                    f"[dim]· {len(entries)}[/] [bold #d79921]{'-' * dashes_count}[/]"
                )
                emit(cat_markup, cat_plain, log_fn)

                for index, entry in enumerate(entries, start=1):
                    if max_entries is not None and index > max_entries:
                        hidden = len(entries) - (index - 1)
                        more_full = " " * ENTRY_INDENT + _t("… 还有 {n} 条（--max-entries 0 查看全部）").format(
                            n=hidden
                        )
                        more_short = " " * ENTRY_INDENT + _t("… 还有 {n} 条（--max-entries 0）").format(n=hidden)
                        more_plain = more_full if _measure(more_full, text_len_fn) <= layout_width else more_short
                        emit(f"[dim]{_markup_escape(more_plain)}[/]", more_plain, log_fn)
                        break

                    for entry_markup, entry_plain in _format_entry_lines(entry, display_cwd, layout_width, text_len_fn):
                        emit(entry_markup, entry_plain, log_fn)

                    if show_hints and level in ("error", "warning"):
                        from ..hints import hint_for_entry

                        hint = hint_for_entry(
                            entry,
                            jobname=jobname,
                            root_file=root_file,
                            tool_name=entry_tools.get(id(entry)),
                            language=_formatter._LANG,
                        )
                        if hint is not None:
                            hint_body = "\n".join((hint.text, *(f"$ {command}" for command in hint.commands)))
                            for hint_markup, hint_plain in _format_hint_lines(hint_body, layout_width, text_len_fn):
                                emit(hint_markup, hint_plain)

        if ref_change_report:
            emit(ref_change_report, ref_change_report)

        if ref_added_keys:
            ref_label = _t("参考文献")
            added_t = _t("新增")
            added_header = f"[{ref_label}] {added_t} {len(ref_added_keys)}:"
            added_block_markup = _format_ref_block(
                added_header,
                sorted(ref_added_keys),
                symbol_style="bold green",
                width=layout_width,
                indent="  ",
                text_len_fn=text_len_fn,
            )
            for line, plain in added_block_markup:
                emit(line, plain)

        if ref_removed_keys:
            ref_label = _t("参考文献")
            removed_t = _t("移除")
            removed_header = f"[{ref_label}] {removed_t} {len(ref_removed_keys)}:"
            removed_block_markup = _format_ref_block(
                removed_header,
                sorted(ref_removed_keys),
                symbol_style="bold red",
                width=layout_width,
                indent="  ",
                text_len_fn=text_len_fn,
            )
            for line, plain in removed_block_markup:
                emit(line, plain)

        if ref_total and ref_total > 0:
            ref_label = _t("参考文献")
            total_t = _t("共")
            unchanged_t = _t("未变动")
            pian_t = _t("篇")
            comma = _t("，")
            comma_sep = ", " if comma == "," else comma
            if pian_t:
                body = f"{total_t} {ref_total} {pian_t}{comma_sep}{unchanged_t} {ref_unchanged or 0} {pian_t}"
            else:
                body = f"{total_t} {ref_total}{comma_sep}{unchanged_t} {ref_unchanged or 0}"
            total_plain = f"  [{ref_label}] {body}"
            total_markup = f"[bold]  {_markup_escape(f'[{ref_label}]')} [/]{_markup_escape(body)}"
            emit(total_markup, total_plain)

        if ref_key_counts and len(ref_key_counts) > 0:
            top_block_markup = _format_top_cited(
                ref_key_counts,
                top_n=5,
                width=layout_width,
                text_len_fn=text_len_fn,
            )
            for line, plain in top_block_markup:
                emit(line, plain)

        return "\n".join(output_lines)
    finally:
        if prev_lang is not None:
            _formatter._LANG = prev_lang
            _formatter._TRANSLATE_FN = prev_tfn


def _entry_as_log_entry(entry: LogEntry | ReportEntry) -> LogEntry:
    """把报告条目（字符串等级）归一成运行时条目（LogLevel 枚举）。"""
    if isinstance(entry, LogEntry):
        return entry
    return LogEntry(
        level=level_from_value(entry.level),
        file=entry.file or "",
        line=entry.line or 0,
        text=entry.text or "",
        error_pos_text=entry.error_pos_text or "",
    )


def _parsed_log_from_entries(
    entries: list[LogEntry | ReportEntry],
    *,
    tool_name: str = "",
    category: str = "",
    importance: str = "low",
    source_path: str = "",
) -> ParsedLog:
    return ParsedLog(
        entries=[_entry_as_log_entry(entry) for entry in entries],
        tool_name=tool_name,
        category=category,
        importance=importance,  # type: ignore[arg-type]
        source_path=source_path,
    )


def _parsed_log_from_report(result: ToolResultReport) -> ParsedLog:
    """把 ``ToolResultReport`` 归一成 ``ParsedLog``。"""
    return _parsed_log_from_entries(
        result.entries,
        tool_name=result.tool_name,
        category=result.category,
        importance=result.importance,
        source_path=result.source_path or "",
    )


def _parsed_log_from_result(result: ToolResult) -> ParsedLog:
    """把 ``ToolResult`` 归一成 ``ParsedLog``，供摘要打印复用。"""
    stats = {"entries_count": result.stats.entries_count, **result.stats.stats}
    return ParsedLog(
        entries=list(result.entries),
        tool_name=result.tool_name,
        category=result.category,
        importance=result.importance,
        source_path=result.source_path,
        stats=stats,
    )


def show_log_entries(
    entries_or_parsed_logs: Any,
    use_logger: bool = True,
    show_info: bool = False,
    non_quiet: bool = True,
    text_len_fn: Callable[[str], int] | None = None,
    *,
    language: str | None = None,
    translate_fn: Callable[[str], str] | None = None,
    width: int | None = None,
) -> None:
    if language is not None:
        _formatter.set_summary_language(language, translate_fn=translate_fn)
    parsed_logs: list[ParsedLog]
    if isinstance(entries_or_parsed_logs, ToolResultReport):
        parsed_logs = [_parsed_log_from_report(entries_or_parsed_logs)]
    elif isinstance(entries_or_parsed_logs, ToolResult):
        parsed_logs = [_parsed_log_from_result(entries_or_parsed_logs)]
    elif isinstance(entries_or_parsed_logs, ParsedLog):
        parsed_logs = [entries_or_parsed_logs]
    elif isinstance(entries_or_parsed_logs, list):
        parsed_logs = []
        loose_entries: list[LogEntry | ReportEntry] = []
        for item in entries_or_parsed_logs:
            if isinstance(item, ParsedLog):
                parsed_logs.append(item)
            elif isinstance(item, ToolResultReport):
                parsed_logs.append(_parsed_log_from_report(item))
            elif isinstance(item, ToolResult):
                parsed_logs.append(_parsed_log_from_result(item))
            elif isinstance(item, (LogEntry, ReportEntry)):
                loose_entries.append(item)
            else:
                raise TypeError(
                    "show_log_entries 列表项不支持 "
                    f"{type(item).__name__}；支持 ParsedLog / ToolResult / "
                    "ToolResultReport / LogEntry / ReportEntry"
                )
        if loose_entries:
            parsed_logs.append(_parsed_log_from_entries(loose_entries))
    elif isinstance(entries_or_parsed_logs, (LogEntry, ReportEntry)):
        parsed_logs = [_parsed_log_from_entries([entries_or_parsed_logs])]
    else:
        raise TypeError(
            "show_log_entries 不支持 "
            f"{type(entries_or_parsed_logs).__name__}；支持 ParsedLog / ToolResult / "
            "ToolResultReport / LogEntry / ReportEntry / 上述列表"
        )
    print_summary(
        parsed_logs=parsed_logs,
        use_logger=use_logger,
        non_quiet=non_quiet,
        show_info=show_info,
        ref_change_report=None,
        ref_added_keys=None,
        ref_removed_keys=None,
        ref_total=None,
        ref_unchanged=None,
        ref_key_counts=None,
        text_len_fn=text_len_fn,
        width=width,
    )
