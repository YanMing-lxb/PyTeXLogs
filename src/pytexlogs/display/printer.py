"""终端输出逻辑：打印摘要、显示日志条目、编辑器跳转。"""

import logging
import re as _re
from collections.abc import Callable
from pathlib import Path
from typing import IO, Any

try:
    from rich.console import Console as _Console
    _RICH_AVAILABLE = True
except Exception:
    _RICH_AVAILABLE = False
    _Console: Any = None

from ..core.models import LogEntry, ParsedLog
from . import formatter as _formatter
from .formatter import (
    _LEVEL_SEP_STYLE,
    _LEVEL_SYMBOL_MARKUP,
    _LEVEL_TITLE,
    CATEGORY_LABEL,
    CATEGORY_ORDER,
    SUMMARY_TOTAL_LEN,
    _format_entry,
    _format_ref_block,
    _format_separator,
    _format_top_cited,
    _group_by,
    _strip_rich_markup,
    _t,
    _wrap_key_block,
    set_summary_language,
)

logger = logging.getLogger(__name__)

_LEVEL_LOGGER = {
    "error": logger.error,
    "warning": logger.warning,
    "info": logger.info,
}

_LEVEL_ANSI = {
    "error": "\033[1;31m",
    "warning": "\033[1;33m",
    "info": "\033[1;34m",
}

_ANSI_RESET = "\033[0m"

_RICH_CONSOLE: Any = None
if _RICH_AVAILABLE:
    _RICH_CONSOLE = _Console(highlight=False, markup=True, soft_wrap=False)
else:
    class _FallbackConsole:
        """PyTeXLogs 无 rich 时的最小兼容桩。"""
        def print(self, *objects: Any, **kwargs: Any) -> None:
            def _strip(txt: object) -> str:
                txt_s = str(txt)
                pat = _re.compile(r"\[/?[^\]]+\]")
                return pat.sub("", txt_s)
            if len(objects) == 0:
                print(end=kwargs.get("end", "\n"))
            else:
                cleaned = [_strip(o) for o in objects]
                sep = kwargs.get("sep", " ")
                end = kwargs.get("end", "\n")
                print(sep.join(cleaned), end=end)
    _RICH_CONSOLE = _FallbackConsole()


def _print_to_stream(stream: IO[str], markup: str, plain: str) -> None:
    """将输出写到 stream（去掉 markup 后写纯文本）。"""
    stripped = _strip_rich_markup(markup) if markup else plain
    stream.write(stripped)
    if not stripped.endswith("\n"):
        stream.write("\n")


def _format_separator_old(title: str, ansi_color: str) -> str:
    """旧版分隔符，仅用于 use_logger 分支。"""
    sep_len = max(40, len(title) + 8)
    line = "=" * sep_len
    return f"{line}\n{ansi_color}{title}{_ANSI_RESET}\n{line}"


def log_editor_jumps(entries: list[LogEntry], logger: logging.Logger | None = None, level: int = logging.INFO) -> None:
    logger = logger or logging.getLogger('pytexlogs')
    sorted_entries = sorted(entries, key=lambda e: (e.level.value, e.file, e.line))
    for e in sorted_entries:
        pathname = Path(str(e.file or '')).name if e.file else ''
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
) -> str:
    """按类别/等级分组打印日志摘要并返回拼接字符串。"""
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
        _len = text_len_fn or len
        grouped = _group_by(parsed_logs)
        output_lines: list[str] = []

        levels_to_show: list[str] = []
        if non_quiet:
            levels_to_show = ["error", "warning"]
            if show_info:
                levels_to_show.append("info")
        else:
            levels_to_show = ["error"]

        for level in levels_to_show:
            categories_data = grouped[level]
            has_entries = any(categories_data[cat] for cat in CATEGORY_ORDER)
            if not has_entries:
                continue

            level_title = _t(_LEVEL_TITLE[level])
            sep_markup = _format_separator(level_title, _LEVEL_SEP_STYLE[level], text_len_fn)
            sep_plain = _strip_rich_markup(sep_markup)
            output_lines.append(sep_plain)
            if use_logger:
                sep_line_old = _format_separator_old(level_title, _LEVEL_ANSI[level])
                _LEVEL_LOGGER[level](sep_line_old)
            elif stream is not None:
                _out(sep_markup, sep_plain)
            else:
                _RICH_CONSOLE.print(sep_markup)

            for cat in CATEGORY_ORDER:
                entries = categories_data[cat]
                if not entries:
                    continue

                cat_label_text = _t(CATEGORY_LABEL.get(cat, cat))
                label = f"[{cat_label_text}]"
                prefix = "[bold #d79921]+--[/] [bold]"
                suffix_part = "[/bold] [bold #d79921]"
                plain_prefix_text = f"+-- {label} "
                plain_prefix_len = _len(plain_prefix_text)
                dashes_count = max(0, SUMMARY_TOTAL_LEN - plain_prefix_len)
                dashes = "-" * dashes_count
                cat_markup = f"{prefix}{label}{suffix_part}{dashes}[/]"
                cat_plain = f"{plain_prefix_text}{dashes}"
                output_lines.append(cat_plain)
                if use_logger:
                    _LEVEL_LOGGER[level](cat_plain)
                elif stream is not None:
                    _out(cat_markup, cat_plain)
                else:
                    _RICH_CONSOLE.print(cat_markup)

                for entry in entries:
                    formatted_plain = _format_entry(entry)
                    symbol_markup = _LEVEL_SYMBOL_MARKUP[level]
                    entry_markup = f"{symbol_markup} {formatted_plain}"
                    file_line, _, text_part = formatted_plain.partition(" --> ")
                    if text_part:
                        entry_markup = (
                            f"{symbol_markup} {file_line} [bold cyan]-->[/] {text_part}"
                        )
                    entry_plain_for_logger = f"  {formatted_plain}"
                    output_lines.append(entry_plain_for_logger)
                    if use_logger:
                        _LEVEL_LOGGER[level](entry_plain_for_logger)
                    elif stream is not None:
                        _out(entry_markup, entry_plain_for_logger)
                    else:
                        _RICH_CONSOLE.print(entry_markup)

                cat_bottom_sep_markup = f"[dim]{'-' * SUMMARY_TOTAL_LEN}[/]"
                cat_bottom_sep_plain = "-" * SUMMARY_TOTAL_LEN
                output_lines.append(cat_bottom_sep_plain)
                if use_logger:
                    _LEVEL_LOGGER[level](cat_bottom_sep_plain)
                elif stream is not None:
                    _out(cat_bottom_sep_markup, cat_bottom_sep_plain)
                else:
                    _RICH_CONSOLE.print(cat_bottom_sep_markup)

        if ref_change_report:
            output_lines.append(ref_change_report)
            if use_logger:
                logger.info(ref_change_report)
            elif stream is not None:
                _out(ref_change_report, ref_change_report)
            else:
                _RICH_CONSOLE.print(ref_change_report)

        if ref_added_keys:
            ref_label = _t("参考文献")
            added_t = _t("新增")
            added_header = f"[{ref_label}] {added_t} {len(ref_added_keys)}:"
            added_block_markup = _format_ref_block(
                added_header,
                sorted(ref_added_keys),
                symbol_style="bold green",
                width=SUMMARY_TOTAL_LEN,
                indent="  ",
            )
            added_block_plain = _wrap_key_block(
                f"[{ref_label}] {added_t} {len(ref_added_keys)}:",
                sorted(ref_added_keys),
                width=SUMMARY_TOTAL_LEN,
                indent="  ",
            )
            for i, line in enumerate(added_block_markup):
                if use_logger:
                    logger.info(added_block_plain[i])
                elif stream is not None:
                    _out(line, added_block_plain[i])
                else:
                    _RICH_CONSOLE.print(line)
            output_lines.extend(added_block_plain)

        if ref_removed_keys:
            ref_label = _t("参考文献")
            removed_t = _t("移除")
            removed_header = f"[{ref_label}] {removed_t} {len(ref_removed_keys)}:"
            removed_block_markup = _format_ref_block(
                removed_header,
                sorted(ref_removed_keys),
                symbol_style="bold red",
                width=SUMMARY_TOTAL_LEN,
                indent="  ",
            )
            removed_block_plain = _wrap_key_block(
                f"[{ref_label}] {removed_t} {len(ref_removed_keys)}:",
                sorted(ref_removed_keys),
                width=SUMMARY_TOTAL_LEN,
                indent="  ",
            )
            for i, line in enumerate(removed_block_markup):
                if use_logger:
                    logger.info(removed_block_plain[i])
                elif stream is not None:
                    _out(line, removed_block_plain[i])
                else:
                    _RICH_CONSOLE.print(line)
            output_lines.extend(removed_block_plain)

        if ref_total and ref_total > 0:
            ref_label = _t("参考文献")
            total_t = _t("共")
            unchanged_t = _t("未变动")
            pian_t = _t("篇")
            pian_space = " " if pian_t else ""
            comma = _t("，")
            total_plain = (
                f"  [{ref_label}] {total_t} {ref_total} {pian_t}{pian_space}"
                f"{comma}{unchanged_t} {ref_unchanged or 0} {pian_t}"
            )
            total_markup = (
                f"[bold]  [{ref_label}] [/]{total_t} {ref_total} {pian_t}{pian_space}"
                f"{comma}{unchanged_t} {ref_unchanged or 0} {pian_t}"
            )
            output_lines.append(total_plain)
            if use_logger:
                logger.info(total_plain)
            elif stream is not None:
                _out(total_markup, total_plain)
            else:
                _RICH_CONSOLE.print(total_markup)

        if ref_key_counts and len(ref_key_counts) > 0:
            top_block_markup = _format_top_cited(ref_key_counts, top_n=5)
            for line in top_block_markup:
                plain = _strip_rich_markup(line)
                output_lines.append(plain)
                if use_logger:
                    logger.info(plain)
                elif stream is not None:
                    _out(line, plain)
                else:
                    _RICH_CONSOLE.print(line)

        return "\n".join(output_lines)
    finally:
        if prev_lang is not None:
            _formatter._LANG = prev_lang
            _formatter._TRANSLATE_FN = prev_tfn


def show_log_entries(
    entries_or_parsed_logs: Any,
    use_logger: bool = True,
    show_info: bool = False,
    non_quiet: bool = True,
    text_len_fn: Callable[[str], int] | None = None,
    *,
    language: str | None = None,
    translate_fn: Callable[[str], str] | None = None,
) -> None:
    if language is not None:
        _formatter.set_summary_language(language, translate_fn=translate_fn)
    parsed_logs: list[ParsedLog]
    if isinstance(entries_or_parsed_logs, list):
        if entries_or_parsed_logs and isinstance(entries_or_parsed_logs[0], ParsedLog):
            parsed_logs = entries_or_parsed_logs
        else:
            parsed_logs = [ParsedLog(entries=entries_or_parsed_logs)]
    elif isinstance(entries_or_parsed_logs, ParsedLog):
        parsed_logs = [entries_or_parsed_logs]
    else:
        parsed_logs = [ParsedLog(entries=[entries_or_parsed_logs])]
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
    )