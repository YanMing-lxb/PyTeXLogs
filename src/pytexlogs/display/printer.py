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
    # 排版提示属"提示"级：走 info 通道，避免日志里被当成警告
    "typesetting": logger.info,
}

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
    max_entries: int | None = None,
    show_hints: bool = False,
) -> str:
    """按类别/等级分组打印日志摘要并返回拼接字符串。

    Args:
        max_entries: 每个「等级 × 类别」分组最多展示的条目数；``None`` 表示全量。
            超出部分折叠为一行「还有 N 条」，避免几十条 overfull 淹没真正的错误。
        show_hints: 是否为 ERROR/WARNING 条目追加一行可执行建议（见 :mod:`pytexlogs.hints`）。
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
        _len = text_len_fn or len
        grouped = _group_by(parsed_logs)
        output_lines: list[str] = []

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
                _RICH_CONSOLE.print(markup)

        levels_to_show: list[str] = []
        if non_quiet:
            levels_to_show = ["error", "warning"]
            if show_info:
                # typesetting 是"提示"级：与 info 一起在 --show-info 下展开，
                # 否则 Overfull/Underfull 会被整组丢弃、用户完全看不到。
                levels_to_show.extend(["info", "typesetting"])
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
            # 日志分支直接用同一份纯文本分隔符（不再另拼一套 ANSI 字符串，
            # 否则同一段标题在终端与日志里长度、颜色都不一致）
            emit(sep_markup, sep_plain, _LEVEL_LOGGER[level])

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
                emit(cat_markup, cat_plain, _LEVEL_LOGGER[level])

                shown = 0
                for entry in entries:
                    if max_entries is not None and shown >= max_entries:
                        hidden = len(entries) - shown
                        more_plain = f"  … 还有 {hidden} 条（用 --format json 导出查看全部）"
                        emit(f"[dim]{more_plain}[/]", more_plain, _LEVEL_LOGGER[level])
                        break
                    shown += 1
                    formatted_plain = _format_entry(entry)
                    symbol_markup = _LEVEL_SYMBOL_MARKUP[level]
                    entry_markup = f"{symbol_markup} {formatted_plain}"
                    file_line, _, text_part = formatted_plain.partition(" --> ")
                    if text_part:
                        entry_markup = (
                            f"{symbol_markup} {file_line} [bold cyan]-->[/] {text_part}"
                        )
                    entry_plain_for_logger = f"  {formatted_plain}"
                    emit(entry_markup, entry_plain_for_logger, _LEVEL_LOGGER[level])

                    if show_hints and level in ("error", "warning"):
                        from ..hints import hint_for_entry

                        hint = hint_for_entry(entry, language=_formatter._LANG)
                        if hint is not None:
                            hint_plain = f"      ↳ {hint.text}"
                            emit(f"[dim]{hint_plain}[/]", hint_plain)
                            if hint.commands:
                                cmd_plain = "       " + " | ".join(hint.commands)
                                emit(f"[dim cyan]{cmd_plain}[/]", cmd_plain)

                cat_bottom_sep_markup = f"[dim]{'-' * SUMMARY_TOTAL_LEN}[/]"
                cat_bottom_sep_plain = "-" * SUMMARY_TOTAL_LEN
                emit(cat_bottom_sep_markup, cat_bottom_sep_plain, _LEVEL_LOGGER[level])

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
                emit(line, added_block_plain[i])

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
                emit(line, removed_block_plain[i])

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
            emit(total_markup, total_plain)

        if ref_key_counts and len(ref_key_counts) > 0:
            top_block_markup = _format_top_cited(ref_key_counts, top_n=5)
            for line in top_block_markup:
                emit(line, _strip_rich_markup(line))

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
