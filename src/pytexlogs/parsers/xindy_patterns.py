"""Xindy 日志的共享正则模式与扫描器。

``XindyParser`` 与 ``GlossariesParser`` 的 xindy 分支必须识别同一套输出；
把模式与逐行扫描集中在同一个小模块里，避免两份逐字重复的正则再次漂移。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

xindy_error_re = re.compile(r"^ERROR:\s*(.+)")
xindy_warning_re = re.compile(r"^WARNING:\s*(.+)")
xindy_loading_module_re = re.compile(r"Loading module\s+(.+)")
xindy_letter_groups_re = re.compile(r"Added\s+(\d+)\s+letter groups")
xindy_markup_rules_re = re.compile(r"Markup( \S+)?\s*.*?(\d+)\s+rules?")
xindy_total_entries_re = re.compile(r"Total entries:\s*(\d+)")
xindy_fallback_entries_re = re.compile(r"(\d+)\s+entries?")


@dataclass(frozen=True)
class XindyScan:
    """一次 xindy 日志扫描的中间结果。

    调用方决定如何把 ``modules``/``letter_groups``/``markup_rule_counts``
    映射成 LogEntry；两个解析器的条目语义不同，但原始观测必须一致。
    """

    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    modules: tuple[str, ...] = ()
    letter_groups: tuple[int, ...] = ()
    markup_rule_counts: tuple[int, ...] = ()
    total_entries: int = 0


def scan_xindy(log_text: str) -> XindyScan:
    """扫描 xindy 文本，返回错误、警告、模块与统计观测。"""
    errors: list[str] = []
    warnings: list[str] = []
    modules: list[str] = []
    letter_groups: list[int] = []
    markup_rule_counts: list[int] = []
    total_entries = 0

    for raw_line in log_text.split("\n"):
        line = raw_line.strip("\x00")

        match = xindy_error_re.match(line)
        if match:
            errors.append(match.group(1).strip())
            continue

        match = xindy_warning_re.match(line)
        if match:
            warnings.append(match.group(1).strip())
            continue

        match = xindy_loading_module_re.match(line)
        if match:
            modules.append(match.group(1).strip())
            continue

        match = xindy_letter_groups_re.search(line)
        if match:
            letter_groups.append(int(match.group(1)))
            continue

        match = xindy_markup_rules_re.search(line)
        if match:
            markup_rule_counts.append(int(match.group(2)))
            continue

        match = xindy_total_entries_re.search(line)
        if match:
            total_entries = max(total_entries, int(match.group(1)))
            continue

        match = xindy_fallback_entries_re.search(line)
        if match:
            total_entries = max(total_entries, int(match.group(1)))

    return XindyScan(
        errors=tuple(errors),
        warnings=tuple(warnings),
        modules=tuple(modules),
        letter_groups=tuple(letter_groups),
        markup_rule_counts=tuple(markup_rule_counts),
        total_entries=total_entries,
    )
