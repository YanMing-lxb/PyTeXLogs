"""格式化逻辑：纯格式化函数与翻译系统，可独立用于 GUI/Web 输出。"""

import logging
import re as _re
import textwrap
from collections import Counter
from collections.abc import Callable
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
    "警告": "Warning",
    "错误": "Error",
    "提示": "Info",
    "参考文献": "Bibliography",
    "索引": "Index",
    "术语/词汇表": "Glossary",
    "代码执行": "Code Execution",
    "图形/绘图": "Graphics",
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
    "compile",
]

CATEGORY_LABEL: dict[str, str] = {
    "bibliography": "参考文献",
    "index": "索引",
    "glossary": "术语/词汇表",
    "code": "代码执行",
    "graphics": "图形/绘图",
    "compile": "一般编译",
}

IMPORTANCE_LABEL: dict[str, str] = {
    "high": "高",
    "medium": "中",
    "low": "低",
}

_LEVEL_ORDER = ["error", "warning", "info"]

_LEVEL_TITLE = {
    "error": "错误汇总",
    "warning": "警告汇总",
    "info": "提示汇总",
}

_LEVEL_SYMBOL_MARKUP = {
    "error": "[bold red]  [E][/]",
    "warning": "[bold yellow]  [W][/]",
    "info": "[bold blue]  [I][/]",
}

_LEVEL_SEP_STYLE = {
    "error": "bold red",
    "warning": "bold yellow",
    "info": "bold blue",
}

_ANSI_RE = _re.compile(r"\x1b\[[0-9;]*[mK]")


def _group_by(
    parsed_logs: list[ParsedLog],
) -> dict[str, dict[str, list[LogEntry]]]:
    result: dict[str, dict[str, list[LogEntry]]] = {}
    for lv in _LEVEL_ORDER:
        result[lv] = {}
        for cat in CATEGORY_ORDER:
            result[lv][cat] = []

    level_map = {
        "error": LogLevel.ERROR,
        "warning": LogLevel.WARNING,
        "info": LogLevel.INFO,
    }

    for plog in parsed_logs:
        category = plog.category if plog.category in CATEGORY_ORDER else "compile"
        for entry in plog.entries:
            for lv_name, lv_enum in level_map.items():
                if entry.level == lv_enum:
                    result[lv_name][category].append(entry)
                    break
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


def _format_entry(entry: LogEntry) -> str:
    """返回纯字符串（不含 ANSI/rich）：file:line --> text。"""
    file_part = entry.file or ""
    if file_part:
        p = Path(file_part)
        try:
            file_part = str(p.relative_to(Path.cwd())).replace("\\", "/")
        except ValueError:
            file_part = p.name
    return f"{file_part}:{entry.line} --> {entry.text}"


def _strip_rich_markup(s: str) -> str:
    """临时去掉 rich markup 标签，用于计算纯文本宽度。"""
    pat = _re.compile(r"\[/?[^\]]+\]")
    return pat.sub("", s)


def _wrap_key_block(
    header: str,
    keys: list[str],
    width: int = SUMMARY_TOTAL_LEN,
    indent: str = "  ",
) -> list[str]:
    """将标题与完整 key 列表按宽度换行输出。"""
    if not keys:
        return []
    result: list[str] = [header]
    joined = ", ".join(keys)
    effective_width = width - len(indent)
    wrapped = textwrap.wrap(joined, width=effective_width, break_long_words=False, break_on_hyphens=False)
    for line in wrapped:
        result.append(indent + line)
    return result


def _format_ref_block(
    header: str,
    keys: list[str],
    symbol_style: str,
    width: int = SUMMARY_TOTAL_LEN,
    indent: str = "  ",
) -> list[str]:
    """返回 rich markup 字符串 list：[+]/[-] header + keys 按宽度换行。"""
    if not keys:
        return []
    symbol = "[+]" if "green" in symbol_style else "[-]"
    header_line = f"[{symbol_style}]{symbol}[/{symbol_style}] [bold]{header}[/]"
    result: list[str] = [header_line]
    sorted_keys = sorted(keys)
    effective_plain_width = width - len(indent)

    wrapped_lines: list[str] = []
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
                wrapped_lines.append(current_rich)
            if len(k) > effective_plain_width:
                k_trunc = k[: effective_plain_width - 3] + "..."
                wrapped_lines.append(f"[cyan]{k_trunc}[/]")
                key_idx += 1
            current_plain = ""
            current_rich = ""
    if current_plain:
        wrapped_lines.append(current_rich)

    for wl in wrapped_lines:
        result.append(indent + wl)
    return result


def _format_top_cited(key_counts: dict[str, int], top_n: int = 10) -> list[str]:
    """返回 rich markup 字符串 list：TopN 引用排行块。"""
    if not key_counts or top_n <= 0:
        return []
    items = Counter(key_counts).most_common(top_n)
    if not items:
        return []
    sep_line = f"[dim]{'-' * SUMMARY_TOTAL_LEN}[/]"
    result: list[str] = [sep_line]
    title_line = f"[bold magenta](*)[/] [bold][{_t('参考文献')}] {_t('引用 Top')} {top_n}:[/]"
    result.append(title_line)

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
        result.append(line)

    result.append(sep_line)
    return result


def format_editor_jumps(entries: list[LogEntry]) -> list[str]:
    result: list[str] = []
    for e in entries:
        pathname = Path(str(e.file or '')).name if e.file else ''
        result.append(f"{pathname}:{e.line}: {e.text}")
    return result