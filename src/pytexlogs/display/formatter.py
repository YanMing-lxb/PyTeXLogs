"""格式化逻辑：纯格式化函数与翻译系统，可独立用于 GUI/Web 输出。"""

import logging
import re as _re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from ..core.models import LogLevel, ParsedLog

if TYPE_CHECKING:
    from ..core.models import LogEntry

logger = logging.getLogger(__name__)

_TRANSLATE_FN: Callable[[str], str] | None = None
_LANG: str = "zh"


def set_summary_language(lang: str, /, *, translate_fn: Callable[[str], str] | None = None) -> None:
    """全局设置摘要语言与可插拔翻译函数。

    lang: "zh" | "en"（默认 "zh"）；当 translate_fn 未注入时，用内置中英对照表。
    translate_fn: 自定义翻译函数（如 gettext.gettext），输入 str 返回 str，供外部注入。
    """
    global _LANG, _TRANSLATE_FN
    _LANG = lang.lower()
    _TRANSLATE_FN = translate_fn


_BuiltinDictTranslations: dict[str, str] = {
    "ERROR": "Error",
    "INFO": "Info",
    "WARNING": "Warning",
    "错误汇总": "Error Summary",
    "警告汇总": "Warning Summary",
    "提示汇总": "Info Summary",
    "排版提示汇总": "Typesetting Summary",
    "字体提示汇总": "Font Summary",
    "图形提示汇总": "Graphics Summary",
    "页面提示汇总": "Page Summary",
    "警告": "Warning",
    "错误": "Error",
    "提示": "Info",
    "参考文献": "Bibliography",
    "索引": "Index",
    "术语/词汇表": "Glossary",
    "代码执行": "Code Execution",
    "图形/绘图": "Graphics",
    "外部工具": "External Tools",
    "自定义解析": "Custom Parsing",
    "一般编译": "Compilation",
    "高": "High",
    "中": "Medium",
    "低": "Low",
    "引用 Top": "Top Cited",
    "次引用": "citations",
    "新增": "Added",
    "移除": "Removed",
    "共": "Total",
    "未变动": "Unchanged",
    "篇": "",
    "，": ",",
    "。": ".",
}


def _t(s: str) -> str:
    if _TRANSLATE_FN is not None:
        return _TRANSLATE_FN(s)
    if _LANG == "zh":
        return s
    if _LANG == "en":
        return _BuiltinDictTranslations.get(s, s)
    return s


SUMMARY_TOTAL_LEN = 74

CATEGORY_ORDER = [
    "bibliography",
    "index",
    "glossary",
    "code",
    "graphics",
    "external",
    "custom",
    "compile",
]

CATEGORY_LABEL: dict[str, str] = {
    "bibliography": "参考文献",
    "index": "索引",
    "glossary": "术语/词汇表",
    "code": "代码执行",
    "graphics": "图形/绘图",
    "external": "外部工具",
    "custom": "自定义解析",
    "compile": "一般编译",
}

IMPORTANCE_LABEL: dict[str, str] = {
    "high": "高",
    "medium": "中",
    "low": "低",
}


@dataclass(frozen=True, slots=True)
class _LevelDisplay:
    """一个等级的展示元数据：标题、符号、分隔色与日志通道。"""

    title: str
    symbol_markup: str
    symbol_plain: str
    sep_style: str
    logger_level: str


#: 等级展示的单一事实源；新增等级只改这里，标题/符号/分隔线/日志通道自动派生。
_LEVEL_DISPLAY: dict[str, _LevelDisplay] = {
    "error": _LevelDisplay(
        title="错误汇总",
        symbol_markup="[bold red]  [E][/]",
        symbol_plain="  [E]",
        sep_style="bold red",
        logger_level="error",
    ),
    "warning": _LevelDisplay(
        title="警告汇总",
        symbol_markup="[bold yellow]  [W][/]",
        symbol_plain="  [W]",
        sep_style="bold yellow",
        logger_level="warning",
    ),
    "info": _LevelDisplay(
        title="提示汇总",
        symbol_markup="[bold blue]  [I][/]",
        symbol_plain="  [I]",
        sep_style="bold blue",
        logger_level="info",
    ),
    "typesetting": _LevelDisplay(
        title="排版提示汇总",
        symbol_markup="[dim]  [T][/]",
        symbol_plain="  [T]",
        sep_style="dim",
        logger_level="info",
    ),
    "font": _LevelDisplay(
        title="字体提示汇总",
        symbol_markup="[dim magenta]  [F][/]",
        symbol_plain="  [F]",
        sep_style="dim magenta",
        logger_level="info",
    ),
    "graphic": _LevelDisplay(
        title="图形提示汇总",
        symbol_markup="[dim cyan]  [G][/]",
        symbol_plain="  [G]",
        sep_style="dim cyan",
        logger_level="info",
    ),
    "page": _LevelDisplay(
        title="页面提示汇总",
        symbol_markup="[dim green]  [P][/]",
        symbol_plain="  [P]",
        sep_style="dim green",
        logger_level="info",
    ),
}

_LEVEL_ORDER: tuple[str, ...] = tuple(_LEVEL_DISPLAY)

#: 枚举 → 显示名，供 _group_by 做 O(1) 归组，避免每条 entry 扫全部等级。
_LEVEL_NAME = {LogLevel(name): name for name in _LEVEL_ORDER}

_RICH_MARKUP_RE = _re.compile(r"\[/?[^\]]+\]")


def _group_by(
    parsed_logs: list[ParsedLog],
) -> dict[str, dict[str, list[LogEntry]]]:
    result: dict[str, dict[str, list[LogEntry]]] = {}
    for lv in _LEVEL_ORDER:
        result[lv] = {}
        for cat in CATEGORY_ORDER:
            result[lv][cat] = []

    level_name_map = _LEVEL_NAME

    for plog in parsed_logs:
        category = plog.category if plog.category in CATEGORY_ORDER else "compile"
        for entry in plog.entries:
            lv_name = level_name_map.get(entry.level)
            if lv_name is not None:
                result[lv_name][category].append(entry)
    return result


def _format_separator(title: str, style: str, text_len_fn: Callable[[str], int] | None = None) -> str:
    """返回单行居中的 rich markup 字符串，总宽 SUMMARY_TOTAL_LEN，左右 === 填充。"""
    _len = text_len_fn or len
    total_width = SUMMARY_TOTAL_LEN
    title_plain = title
    padding_size = total_width - _len(title_plain) - 2
    left_len = padding_size // 2
    right_len = padding_size - left_len
    left_sep = "=" * left_len
    right_sep = "=" * right_len
    return f"[{style}]{left_sep} {title_plain} {right_sep}[/{style}]"


@lru_cache(maxsize=4096)
def _display_path(file_part: str, cwd: str) -> str:
    """把日志里的文件路径转成摘要展示路径；按 (path, cwd) 缓存。

    同一份大日志里几千条 entry 往往只来自几十个文件，旧实现为每条 entry
    重新做 ``Path.cwd() / relative_to()``，是 summary 的主要热点。
    """
    if not file_part:
        return ""
    p = Path(file_part)
    try:
        return str(p.relative_to(cwd)).replace("\\", "/")
    except ValueError:
        return p.name


def _format_entry(entry: LogEntry, cwd: str | None = None) -> str:
    """返回纯字符串（不含 ANSI/rich）：file:line --> text。

    ``cwd`` 可由批量调用方传入，避免每条 entry 都重复 ``Path.cwd()``。
    """
    file_part = _display_path(entry.file or "", cwd or str(Path.cwd()))
    return f"{file_part}:{entry.line} --> {entry.text}"


def _strip_rich_markup(s: str) -> str:
    """临时去掉 rich markup 标签，用于计算纯文本宽度。"""
    return _RICH_MARKUP_RE.sub("", s)


def _format_ref_block(
    header: str,
    keys: list[str],
    symbol_style: str,
    width: int = SUMMARY_TOTAL_LEN,
    indent: str = "  ",
) -> list[tuple[str, str]]:
    """返回 ``(rich markup, plain)`` 行：``[+]/[-]`` header + 按宽度换行的 keys。"""
    if not keys:
        return []
    symbol = "[+]" if "green" in symbol_style else "[-]"
    header_line = f"[{symbol_style}]{symbol}[/{symbol_style}] [bold]{header}[/]"
    header_plain = f"{symbol} {header}"
    result: list[tuple[str, str]] = [(header_line, header_plain)]
    sorted_keys = sorted(keys)
    effective_plain_width = width - len(indent)

    wrapped_rich: list[str] = []
    wrapped_plain: list[str] = []
    current_plain = ""
    current_rich = ""
    key_idx = 0
    while key_idx < len(sorted_keys):
        k = sorted_keys[key_idx]
        is_last = key_idx == len(sorted_keys) - 1
        sep_plain = ", " if not is_last else ""
        k_rich = f"[cyan]{k}[/]"
        sep_rich = "[dim], [/]" if not is_last else ""

        piece_plain = k + sep_plain
        piece_rich = k_rich + sep_rich

        if len(current_plain) + len(piece_plain) <= effective_plain_width:
            current_plain += piece_plain
            current_rich += piece_rich
            key_idx += 1
        else:
            if current_plain:
                wrapped_rich.append(current_rich)
                wrapped_plain.append(current_plain)
            if len(k) > effective_plain_width:
                k_trunc = k[: effective_plain_width - 3] + "..."
                wrapped_rich.append(f"[cyan]{k_trunc}[/]")
                wrapped_plain.append(k_trunc)
                key_idx += 1
            current_plain = ""
            current_rich = ""
    if current_plain:
        wrapped_rich.append(current_rich)
        wrapped_plain.append(current_plain)

    result.extend((indent + rich, indent + plain) for rich, plain in zip(wrapped_rich, wrapped_plain, strict=True))
    return result


def _format_top_cited(key_counts: dict[str, int], top_n: int = 10) -> list[tuple[str, str]]:
    """返回 ``(rich markup, plain)`` 行：TopN 引用排行块。"""
    if not key_counts or top_n <= 0:
        return []
    items = Counter(key_counts).most_common(top_n)
    if not items:
        return []
    sep_line = f"[dim]{'-' * SUMMARY_TOTAL_LEN}[/]"
    sep_plain = "-" * SUMMARY_TOTAL_LEN
    result: list[tuple[str, str]] = [(sep_line, sep_plain)]
    title_line = f"[bold magenta](*)[/] [bold][{_t('参考文献')}] {_t('引用 Top')} {top_n}:[/]"
    title_plain = f"(*) [{_t('参考文献')}] {_t('引用 Top')} {top_n}:"
    result.append((title_line, title_plain))

    max_key_plain = 40
    count_width = 3
    for rank, (key, count) in enumerate(items, 1):
        key_plain = key
        if len(key_plain) > max_key_plain:
            key_plain = key_plain[: max_key_plain - 3] + "..."
        key_padded = key_plain.ljust(max_key_plain)
        rank_str = f"({rank})"
        count_str = str(count).rjust(count_width)
        line = f"    {rank_str} [cyan]{key_padded}[/]  [bold magenta]{count_str}[/] {_t('次引用')}"
        line_plain = f"    {rank_str} {key_padded}  {count_str} {_t('次引用')}"
        result.append((line, line_plain))

    result.append((sep_line, sep_plain))
    return result


def format_editor_jumps(entries: list[LogEntry]) -> list[str]:
    result: list[str] = []
    for e in entries:
        pathname = Path(str(e.file or "")).name if e.file else ""
        result.append(f"{pathname}:{e.line}: {e.text}")
    return result
