"""格式化逻辑：纯格式化函数与翻译系统，可独立用于 GUI/Web 输出。"""

import logging
import re as _re
import unicodedata
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
    "未知文件": "unknown file",
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
    "… 还有 {n} 条（--max-entries 0 查看全部）": "… and {n} more entries (--max-entries 0 for all)",
    "… 还有 {n} 条（--max-entries 0）": "… and {n} more entries (--max-entries 0)",
}


def _t(s: str) -> str:
    if _TRANSLATE_FN is not None:
        return _TRANSLATE_FN(s)
    if _LANG == "zh":
        return s
    if _LANG == "en":
        return _BuiltinDictTranslations.get(s, s)
    return s


# 终端摘要版式：默认宽度保持 74 列，但允许调用方（如 PyTeXMK）按自身控制台
# 宽度覆盖；最小宽度用于防止悬挂缩进和路径省略被压坏。
SUMMARY_TOTAL_LEN = 74
MIN_SUMMARY_WIDTH = 40

# 版式缩进：条目 4 列，hint 8 列，可执行命令 10 列。
ENTRY_INDENT = 4
HINT_INDENT = 8
COMMAND_INDENT = 10
MIN_ENTRY_TEXT_WIDTH = 12


def _char_cells(ch: str) -> int:
    """单个字符的终端显示列数；全角/宽字符按 2 列，组合字符按 0 列。"""
    if ch == "\t":
        return 4
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def display_width(text: str) -> int:
    """按终端显示列数测量字符串，用于 CJK 标题和悬挂缩进对齐。"""
    return sum(_char_cells(ch) for ch in text)


def _measure(text: str, text_len_fn: Callable[[str], int] | None = None) -> int:
    return text_len_fn(text) if text_len_fn is not None else display_width(text)


def resolve_summary_width(width: int | None) -> int:
    """把外部传入的宽度收敛到可用范围；None 表示沿用固定默认宽度。"""
    if width is None:
        return SUMMARY_TOTAL_LEN
    try:
        value = int(width)
    except TypeError, ValueError:
        return SUMMARY_TOTAL_LEN
    return max(MIN_SUMMARY_WIDTH, value)


def _truncate_to(text: str, width: int, text_len_fn: Callable[[str], int] | None = None) -> str:
    """按显示列截断字符串，保证截断结果不超过 width。"""
    if width <= 0:
        return ""
    out: list[str] = []
    used = 0
    for ch in text:
        cells = _char_cells(ch) if text_len_fn is None else text_len_fn(ch)
        if used + cells > width:
            break
        out.append(ch)
        used += cells
    return "".join(out)


def _shorten_middle(text: str, width: int, text_len_fn: Callable[[str], int] | None = None) -> str:
    """路径/位置超宽时优先保留末尾的 ``:line``，中间用省略号压缩。"""
    if width <= 0:
        return ""
    if _measure(text, text_len_fn) <= width:
        return text

    head, sep, tail = text.rpartition(":")
    if sep and head and _measure(tail, text_len_fn) + 2 < width:
        suffix = ":" + tail
        budget = width - _measure(suffix, text_len_fn) - 1
        if budget > 3:
            truncated = _truncate_to(head, budget, text_len_fn).rstrip("/\\")
            if truncated:
                return truncated + "…" + suffix
    return _truncate_to(text, width - 1, text_len_fn).rstrip() + "…"


_CLOSING_PUNCT = "，。；：、！？）》」』）】”’"


def _break_points(text: str) -> tuple[int | None, int | None]:
    """返回 (最后一个空格断点, 最后一个 CJK 断点)，两者均为字符下标。"""
    space_pos: int | None = None
    cjk_pos: int | None = None
    last_index = len(text) - 1
    for index, ch in enumerate(text):
        if ch == " ":
            space_pos = index + 1
        elif _char_cells(ch) == 2:
            # 不在中文收尾标点前断行，避免下一行以「，。；：」开头。
            if index == last_index or text[index + 1] not in _CLOSING_PUNCT:
                cjk_pos = index + 1
    return space_pos, cjk_pos


def _wrap_text(
    text: str,
    width: int,
    text_len_fn: Callable[[str], int] | None = None,
) -> list[str]:
    """按终端显示列折行，保留空格/CJK 断点，超长拉丁 token 强制断行。"""
    text = " ".join(str(text).split())
    if width <= 0:
        return [text]
    if not text:
        return [""]

    lines: list[str] = []
    current = ""
    current_width = 0

    for ch in text:
        ch_width = _char_cells(ch) if text_len_fn is None else text_len_fn(ch)
        if current and current_width + ch_width > width:
            space_break, cjk_break = _break_points(current)
            break_at = space_break if space_break is not None and 0 < space_break <= len(current) else cjk_break
            if break_at is not None and 0 < break_at < len(current) + 1:
                head = current[:break_at].rstrip()
                tail = current[break_at:].lstrip()
                if head:
                    lines.append(head)
                    current = tail
                    current_width = _measure(current, text_len_fn)
                else:
                    lines.append(current.rstrip())
                    current = ""
                    current_width = 0
            else:
                lines.append(current.rstrip())
                current = ""
                current_width = 0
        current += ch
        current_width += ch_width

    if current.strip() or (not lines and current):
        lines.append(current.rstrip())
    return lines or [""]


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
    """一个等级的展示元数据：标题、符号、标题色与日志通道。"""

    title: str
    symbol_markup: str
    symbol_plain: str
    title_style: str
    logger_level: str


#: 等级展示的单一事实源；error/warning/info 保留红黄蓝，其余统一 dim 灰，
#: 避免同一段输出里出现四种弱对比色相。
_LEVEL_DISPLAY: dict[str, _LevelDisplay] = {
    "error": _LevelDisplay(
        title="错误汇总",
        symbol_markup="[bold red][E][/]",
        symbol_plain="[E]",
        title_style="bold red",
        logger_level="error",
    ),
    "warning": _LevelDisplay(
        title="警告汇总",
        symbol_markup="[bold yellow][W][/]",
        symbol_plain="[W]",
        title_style="bold yellow",
        logger_level="warning",
    ),
    "info": _LevelDisplay(
        title="提示汇总",
        symbol_markup="[bold blue][I][/]",
        symbol_plain="[I]",
        title_style="bold blue",
        logger_level="info",
    ),
    "typesetting": _LevelDisplay(
        title="排版提示汇总",
        symbol_markup="[dim][T][/]",
        symbol_plain="[T]",
        title_style="dim",
        logger_level="info",
    ),
    "font": _LevelDisplay(
        title="字体提示汇总",
        symbol_markup="[dim][F][/]",
        symbol_plain="[F]",
        title_style="dim",
        logger_level="info",
    ),
    "graphic": _LevelDisplay(
        title="图形提示汇总",
        symbol_markup="[dim][G][/]",
        symbol_plain="[G]",
        title_style="dim",
        logger_level="info",
    ),
    "page": _LevelDisplay(
        title="页面提示汇总",
        symbol_markup="[dim][P][/]",
        symbol_plain="[P]",
        title_style="dim",
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


def _format_title_rule(
    title_plain: str,
    width: int,
    style: str,
    text_len_fn: Callable[[str], int] | None = None,
) -> tuple[str, str]:
    """返回 ``(markup, plain)``：沿用旧版的 ``==== 标题 ====`` 居中横幅。"""
    padding = width - _measure(title_plain, text_len_fn) - 2
    left_len = max(0, padding // 2)
    right_len = max(0, padding - left_len)
    plain = f"{'=' * left_len} {title_plain} {'=' * right_len}"
    return f"[{style}]{_markup_escape(plain)}[/]", plain


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
    """返回纯字符串（不含 ANSI/rich）：file:line --> text。"""
    file_part = _display_path(entry.file or "", cwd or str(Path.cwd()))
    return f"{file_part}:{entry.line} --> {entry.text}"


_ESCAPE_FN: Callable[[str], str] | None = None


def _markup_escape(text: str) -> str:
    """转义日志正文里的 ``[...]``，避免被 rich 当成样式标签。"""
    global _ESCAPE_FN
    if _ESCAPE_FN is None:
        try:
            from rich.markup import escape
        except Exception:
            _ESCAPE_FN = lambda value: value  # noqa: E731
        else:
            _ESCAPE_FN = escape
    return _ESCAPE_FN(text)


def _format_entry_lines(
    entry: LogEntry,
    cwd: str,
    width: int,
    text_len_fn: Callable[[str], int] | None = None,
) -> list[tuple[str, str]]:
    """返回 ``(rich markup, plain)`` 行；续行缩进与首行文本起始列对齐。"""
    level_name = getattr(entry.level, "value", str(entry.level))
    meta = _LEVEL_DISPLAY.get(level_name, _LEVEL_DISPLAY["info"])

    file_part = _display_path(entry.file or "", cwd)
    file_line = f"{file_part}:{entry.line}" if file_part else f"{_t('未知文件')}:{entry.line}"
    max_file_width = width - ENTRY_INDENT - len(meta.symbol_plain) - 1 - len(" --> ") - MIN_ENTRY_TEXT_WIDTH
    file_line = _shorten_middle(file_line, max_file_width, text_len_fn)

    prefix_plain = f"{' ' * ENTRY_INDENT}{meta.symbol_plain} {file_line} --> "
    text_start = _measure(prefix_plain, text_len_fn)
    text_width = max(4, width - text_start)
    chunks = _wrap_text(entry.text or "", text_width, text_len_fn)

    first_plain = prefix_plain + chunks[0]
    first_markup = (
        f"{' ' * ENTRY_INDENT}{meta.symbol_markup} "
        f"{_markup_escape(file_line)} [bold cyan]-->[/] {_markup_escape(chunks[0])}"
    )
    result: list[tuple[str, str]] = [(first_markup, first_plain)]

    continuation = " " * text_start
    for chunk in chunks[1:]:
        result.append((continuation + _markup_escape(chunk), continuation + chunk))
    return result


def _format_hint_lines(
    hint: str,
    width: int,
    text_len_fn: Callable[[str], int] | None = None,
) -> list[tuple[str, str]]:
    """返回 ``(markup, plain)`` 行：hint 挂到 8 列，命令行挂到 10 列。"""
    if not hint:
        return []
    result: list[tuple[str, str]] = []
    for raw_line in hint.splitlines():
        raw = raw_line.strip()
        if not raw:
            continue
        if raw.startswith("$ "):
            command = raw[2:]
            prefix_plain = " " * COMMAND_INDENT + "$ "
            chunks = _wrap_text(
                command,
                max(4, width - _measure(prefix_plain, text_len_fn)),
                text_len_fn,
            )
            first_plain = prefix_plain + chunks[0]
            first_markup = f"{' ' * COMMAND_INDENT}[bold]$[/] {_markup_escape(chunks[0])}"
            result.append((first_markup, first_plain))
            continuation = " " * _measure(prefix_plain, text_len_fn)
            for chunk in chunks[1:]:
                result.append((continuation + _markup_escape(chunk), continuation + chunk))
        else:
            prefix_plain = " " * HINT_INDENT + "↳ "
            chunks = _wrap_text(
                raw,
                max(4, width - _measure(prefix_plain, text_len_fn)),
                text_len_fn,
            )
            first_plain = prefix_plain + chunks[0]
            first_markup = f"{' ' * HINT_INDENT}[cyan]↳[/] {_markup_escape(chunks[0])}"
            result.append((first_markup, first_plain))
            continuation = " " * _measure(prefix_plain, text_len_fn)
            for chunk in chunks[1:]:
                result.append((continuation + _markup_escape(chunk), continuation + chunk))
    return result


def _strip_rich_markup(s: str) -> str:
    """临时去掉 rich markup 标签，用于计算纯文本宽度。"""
    return _RICH_MARKUP_RE.sub("", s)


def _format_ref_block(
    header: str,
    keys: list[str],
    symbol_style: str,
    width: int = SUMMARY_TOTAL_LEN,
    indent: str = "  ",
    text_len_fn: Callable[[str], int] | None = None,
) -> list[tuple[str, str]]:
    """返回 ``(rich markup, plain)`` 行：``[+]/[-]`` header + 按宽度换行的 keys。"""
    if not keys:
        return []
    symbol = "[+]" if "green" in symbol_style else "[-]"
    header_line = f"[{symbol_style}]{symbol}[/] [bold]{_markup_escape(header)}[/]"
    header_plain = f"{symbol} {header}"
    result: list[tuple[str, str]] = [(header_line, header_plain)]
    sorted_keys = sorted(keys)
    effective_plain_width = width - _measure(indent, text_len_fn)

    wrapped_rich: list[str] = []
    wrapped_plain: list[str] = []
    current_plain = ""
    current_rich = ""
    key_idx = 0
    while key_idx < len(sorted_keys):
        k = sorted_keys[key_idx]
        is_last = key_idx == len(sorted_keys) - 1
        sep_plain = ", " if not is_last else ""
        k_rich = f"[cyan]{_markup_escape(k)}[/]"
        sep_rich = "[dim], [/]" if not is_last else ""

        piece_plain = k + sep_plain
        piece_rich = k_rich + sep_rich

        if _measure(current_plain, text_len_fn) + _measure(piece_plain, text_len_fn) <= effective_plain_width:
            current_plain += piece_plain
            current_rich += piece_rich
            key_idx += 1
        else:
            if current_plain:
                wrapped_rich.append(current_rich)
                wrapped_plain.append(current_plain)
            if _measure(k, text_len_fn) > effective_plain_width:
                k_trunc = _shorten_middle(k, effective_plain_width, text_len_fn)
                wrapped_rich.append(f"[cyan]{_markup_escape(k_trunc)}[/]")
                wrapped_plain.append(k_trunc)
                key_idx += 1
            current_plain = ""
            current_rich = ""
    if current_plain:
        wrapped_rich.append(current_rich)
        wrapped_plain.append(current_plain)

    result.extend((indent + rich, indent + plain) for rich, plain in zip(wrapped_rich, wrapped_plain, strict=True))
    return result


def _format_top_cited(
    key_counts: dict[str, int],
    top_n: int = 10,
    width: int = SUMMARY_TOTAL_LEN,
    text_len_fn: Callable[[str], int] | None = None,
) -> list[tuple[str, str]]:
    """返回 ``(rich markup, plain)`` 行：TopN 引用排行块。"""
    if not key_counts or top_n <= 0:
        return []
    items = Counter(key_counts).most_common(top_n)
    if not items:
        return []

    sep_plain = "-" * width
    sep_line = f"[dim]{sep_plain}[/]"
    title_plain = f"(*) [{_t('参考文献')}] {_t('引用 Top')} {top_n}:"
    title_line = f"[bold](*)[/] [bold]{_markup_escape(title_plain[4:])}[/]"
    result: list[tuple[str, str]] = [(sep_line, sep_plain), (title_line, title_plain)]

    max_count = max(count for _, count in items)
    count_width = max(3, len(str(max_count)))
    rank_width = len(f"({top_n})")
    tail_width = 2 + count_width + 1 + _measure(_t("次引用"), text_len_fn)
    key_width = width - 4 - rank_width - 1 - tail_width
    key_width = max(8, min(28, key_width))

    for rank, (key, count) in enumerate(items, 1):
        key_plain = _truncate_to(key, key_width, text_len_fn)
        key_padded = key_plain.ljust(key_width)
        rank_str = f"({rank})".ljust(rank_width)
        count_str = str(count).rjust(count_width)
        line = f"    {rank_str} [cyan]{_markup_escape(key_padded)}[/]  [bold]{count_str}[/] {_t('次引用')}"
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
