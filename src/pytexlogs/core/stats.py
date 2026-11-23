"""过滤后的统计重算：所有导出/CLI/流水线路径共用同一口径。

背景：过滤会改变条目集合，若只改 ``entries_count`` 而保留原来的
``typesetting`` / ``overfull_boxes`` 等计数，导出的 JSON/CSV/SARIF 会自相矛盾。
本模块只做纯函数计算，不依赖具体容器类型，便于报告模型与运行时模型复用。
"""

from collections import Counter
from collections.abc import Iterable
from typing import Any

from .models import LogLevel, level_from_value

__all__ = ["recompute_stats"]

#: 未定义引用 / 文献条目在条目文本里的稳定前缀。
#: latex 解析器的文案已从中文（``找不到 reference``）迁移为英文
#: （``Undefined reference``），两种历史文案必须同时计数，避免旧日志/
#: 旧导出在重算后出现 ``undefined_refs`` 归零。
_UNDEFINED_REF_PREFIXES = ("Undefined reference", "找不到 reference")
_UNDEFINED_CITE_PREFIXES = ("Undefined citation", "找不到 citation")

#: 所有等级键，按枚举派生；``error``/``warning`` 同时也是旧版兼容键。
_LEVEL_VALUES: tuple[str, ...] = tuple(level.value for level in LogLevel)


def _level_value(entry: Any) -> str:
    """取条目的等级字符串；未知等级按 INFO 归类，避免产生无意义的键。"""
    level = getattr(entry, "level", LogLevel.INFO)
    if isinstance(level, str):
        return level_from_value(level).value
    return level_from_value(getattr(level, "value", level)).value


def recompute_stats(entries: Iterable[Any], stats: dict[str, Any]) -> None:
    """原地重算 ``stats`` 中可由条目集合推导的字段。

    会重算：
    - ``entries_count``；
    - 全部 ``LogLevel`` 等级键、``errors_count`` / ``warnings_count``；
    - 若原 stats 中存在 ``overfull_boxes`` / ``underfull_boxes``，按文本标记重算；
    - 若原 stats 中存在 ``undefined_refs`` / ``undefined_cites``，按本地化前缀重算。

    无法从单条目推导的整日志统计（页数、已处理条目数、数据库文件等）保持原值，
    因此调用方可以安全地在过滤前后复用同一份 stats 字典。
    """
    entry_list = list(entries)
    level_counts: Counter[str] = Counter(_level_value(e) for e in entry_list)

    stats["entries_count"] = len(entry_list)
    for level_value in _LEVEL_VALUES:
        stats[level_value] = level_counts.get(level_value, 0)
    stats["errors_count"] = level_counts.get(LogLevel.ERROR.value, 0)
    stats["warnings_count"] = level_counts.get(LogLevel.WARNING.value, 0)

    if "overfull_boxes" in stats:
        stats["overfull_boxes"] = sum(1 for e in entry_list if "Overfull" in str(getattr(e, "text", "")))
    if "underfull_boxes" in stats:
        stats["underfull_boxes"] = sum(1 for e in entry_list if "Underfull" in str(getattr(e, "text", "")))
    if "undefined_refs" in stats:
        stats["undefined_refs"] = sum(
            1 for e in entry_list if str(getattr(e, "text", "")).startswith(_UNDEFINED_REF_PREFIXES)
        )
    if "undefined_cites" in stats:
        stats["undefined_cites"] = sum(
            1 for e in entry_list if str(getattr(e, "text", "")).startswith(_UNDEFINED_CITE_PREFIXES)
        )
