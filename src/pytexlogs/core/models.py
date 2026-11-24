"""PyTeXLogs 核心数据模型：日志等级、条目、解析结果、报告结构与工具结果。"""

from abc import ABC, abstractmethod
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from ..utils.encoding import read_log_text

#: 严重程度排序：数字越小越严重（ERROR 最靠前）。
#: 定义在模块级而非每次比较时重建，避免排序时的字典构造开销。
_SEVERITY_RANK: dict[LogLevel, int]


class LogLevel(Enum):
    """日志等级枚举：错误/警告/信息/提示（排版、字体、图形、页面）。

    0.6.1 起 ``TYPESET`` 明确为"提示"（口径由用户确认），排序落在 ``INFO`` 之后：
    它既不该比 info 更严重，也不该被当成 warning 计入 CI 失败阈值。
    旧顺序 ``ERROR < WARNING < TYPESET < INFO`` 会让 ``min_level=INFO`` 的过滤
    把"提示"排在 info 前面，属于错得很巧的实现。
    """

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    TYPESET = "typesetting"
    FONT = "font"
    GRAPHIC = "graphic"
    PAGE = "page"

    @property
    def severity(self) -> int:
        """该等级的严重程度序号（0=最严重），用于排序与阈值过滤。"""
        return _SEVERITY_RANK[self]

    def __lt__(self, other: object) -> bool:
        """按严重程度比较两个 LogLevel 等级大小。"""
        if not isinstance(other, LogLevel):
            return NotImplemented
        return _SEVERITY_RANK[self] < _SEVERITY_RANK[other]


#: 用 declared order 生成排名：声明顺序即严重程度顺序，避免手写映射表写错。
_SEVERITY_RANK = {level: rank for rank, level in enumerate(LogLevel)}


@dataclass(slots=True)
class LogEntry:
    """单条日志条目数据结构：等级、文件、行号、文本、错误上下文。"""

    level: LogLevel
    file: str
    line: int
    text: str
    error_pos_text: str = ""


class _EntryHolder:
    """``ParsedLog`` 与 ``ToolResult`` 共同的按等级筛选逻辑。

    两者字段不完全相同（``ParsedLog`` 无 ``stats`` 对象、``ToolResult`` 无
    ``category``），但 ``errors`` / ``warnings`` / ``info`` 三个属性的实现完全
    一致；抽到这里避免三份重复代码，也保证筛选口径永远同步。
    """

    #: 子类 dataclass 提供；这里只声明类型供检查器与读者参考。
    #: 注意：基类必须把 entries 放进 __slots__，否则子类的 slots=True 会失效
    #: （实例重新获得 __dict__，内存与访问开销都退化）。
    entries: list[LogEntry]

    __slots__ = ("entries",)

    def by_level(self, level: LogLevel) -> list[LogEntry]:
        """按等级筛选条目。"""
        return [e for e in self.entries if e.level == level]

    @property
    def errors(self) -> list[LogEntry]:
        """返回所有等级为 ERROR 的条目列表。"""
        return self.by_level(LogLevel.ERROR)

    @property
    def warnings(self) -> list[LogEntry]:
        """返回所有等级为 WARNING 的条目列表。"""
        return self.by_level(LogLevel.WARNING)

    @property
    def info(self) -> list[LogEntry]:
        """返回所有等级为 INFO 的条目列表。"""
        return self.by_level(LogLevel.INFO)


@dataclass(slots=True)
class ParsedLog(_EntryHolder):
    """解析后的日志结果：条目列表、原始文本、来源、工具名、统计。"""

    entries: list[LogEntry] = field(default_factory=list)
    raw_text: str = ""
    source_path: str = ""
    tool_name: str = ""
    category: str = ""
    importance: Literal["high", "medium", "low"] = "low"
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        """判断解析结果是否为空（无条目且无原始文本）。"""
        return not self.entries and not self.raw_text


class BaseLogParser(ABC):
    """日志解析器抽象基类：定义 parse/parse_file 接口与编码兜底读取。"""

    def __init__(self, root_file: str | None = None) -> None:
        """初始化 BaseLogParser：缓存 root_file。"""
        self.root_file: str = root_file or ""
        self._resolved_paths: dict[str, str] = {}

    @abstractmethod
    def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
        """解析日志字符串，返回 ParsedLog（由子类实现）。"""
        ...

    def parse_file(self, log_path: str | Path, root_file: str | None = None) -> ParsedLog:
        """读取日志文件并委托 parse 方法解析，多编码兜底。"""
        path = Path(log_path)
        if not path.exists():
            return ParsedLog(source_path=str(path))
        text = self._read_log_text(path)
        # 让解析器在 parse 期间能看到真实日志路径：Biber 用它找同目录 .bcf，
        # Glossaries 用它区分 .glg/.ilg，其它 parser 用它推导 source_path。
        self._source_path_hint = str(path)
        try:
            result = self.parse(text, root_file or self.root_file)
        finally:
            with suppress(AttributeError):
                delattr(self, "_source_path_hint")
        if result is None:
            raise TypeError(f"{type(self).__name__}.parse() 返回 None；必须返回 ParsedLog")
        result.source_path = str(path)
        return result

    def _read_log_text(self, log_path: str | Path) -> str:
        """读取日志文本；编码候选与兜底策略统一由 :func:`utils.encoding.read_log_text` 维护。"""
        return read_log_text(log_path)


# --- 报告数据模型 ---

#: 报告 JSON 的 schema 版本（与状态文件 ``SCHEMA_VERSION`` 相互独立，各管一条版本轴）。
#: 单点定义，写盘与回读都从这里取，避免"写 1、读 1"两处字面量漂移。
REPORT_SCHEMA_VERSION = 1

#: 报告层条目等级的可比较类型（兼容枚举与纯字符串两种来源）。
ReportLevelLike = LogLevel | str

#: 等级字符串 → LogLevel 的查找表（构建一次，避免每次筛选都重建字典）。
_LEVEL_LOOKUP: dict[str, LogLevel] = {lv.value: lv for lv in LogLevel}


def level_from_value(level_value: ReportLevelLike) -> LogLevel:
    """把等级值（枚举或字符串）归一化成 LogLevel；未知等级按 INFO 兜底。

    ``ReportEntry.level`` 存的是字符串（为了 JSON 兼容），而 ``ParsedLog`` 用的是
    ``LogLevel`` 枚举。两种模型对外暴露同一套 ``errors/warnings/info/by_level``
    口径，这里负责把两种输入都折成枚举。0.6.1 起公开导出，替代各处自建的
    ``{字符串: 枚举}`` 映射表（那些表正是把 font/graphic/page 压平成 info 的根源）。
    """
    if isinstance(level_value, LogLevel):
        return level_value
    return _LEVEL_LOOKUP.get(str(level_value), LogLevel.INFO)


#: 向后兼容的内部别名（同模块内旧调用点仍可用）。
_resolve_level = level_from_value


@dataclass(slots=True)
class ReportEntry:
    """单条日志条目，仅使用 JSON 兼容类型。"""

    level: str = "info"
    file: str | None = None
    line: int | None = None
    text: str = ""
    error_pos_text: str | None = None


@dataclass(slots=True)
class ToolResultReport:
    """单个工具的解析结果汇总。

    ``errors`` / ``warnings`` / ``info`` / ``by_level`` 与 :class:`ParsedLog`
    保持同一套口径，下游不必再自己按等级过滤 ``entries``。
    """

    tool_name: str = ""
    category: str = ""
    importance: str = "medium"
    source_path: str | None = None
    entries: list[ReportEntry] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
    parse_exception: dict[str, str] | None = None

    def by_level(self, level: ReportLevelLike) -> list[ReportEntry]:
        """按等级筛选条目（枚举或字符串均可）。"""
        wanted = _resolve_level(level).value
        return [e for e in self.entries if e.level == wanted]

    @property
    def errors(self) -> list[ReportEntry]:
        """所有 ERROR 级条目。"""
        return self.by_level(LogLevel.ERROR)

    @property
    def warnings(self) -> list[ReportEntry]:
        """所有 WARNING 级条目。"""
        return self.by_level(LogLevel.WARNING)

    @property
    def info(self) -> list[ReportEntry]:
        """所有 INFO 级条目。"""
        return self.by_level(LogLevel.INFO)

    @classmethod
    def from_parsed_log(cls, parsed: ParsedLog) -> ToolResultReport:
        """把运行时模型（枚举等级）折成报告模型（JSON 兼容等级）。

        两个模型的分工：``run_pipeline`` 产出报告模型（写盘/导出/CLI 聚合都
        用它），``easy.parse_log_file`` 产出运行时模型（单文件解析、展示层）。
        需要把单个 ``ParsedLog`` 并进报告列表时走这里——这是两套模型之间
        **唯一**的转换点，0.5 的 CLI 里原本还另抄了一份。
        """
        entries = [
            ReportEntry(
                level=_resolve_level(e.level).value,
                file=e.file or None,
                line=e.line or None,
                text=e.text or "",
                error_pos_text=e.error_pos_text or None,
            )
            for e in parsed.entries
        ]
        error_count = sum(1 for e in entries if e.level == LogLevel.ERROR.value)
        warning_count = sum(1 for e in entries if e.level == LogLevel.WARNING.value)
        importance: str = "high" if error_count else "medium" if warning_count else parsed.importance
        # 保留 parser 产出的整日志统计（页数、未定义引用、盒子等），再按条目集合
        # 重算可推导字段（等级键 / errors_count / warnings_count / entries_count）。
        # 这样单文件入口与目录 pipeline 的 stats 键集合一致；局部 import 规避
        # core.stats 已在模块级导入 core.models 造成的循环导入。
        stats: dict[str, Any] = dict(parsed.stats)
        from .stats import recompute_stats

        recompute_stats(entries, stats)
        return cls(
            tool_name=parsed.tool_name,
            category=parsed.category,
            importance=importance,
            source_path=parsed.source_path or None,
            entries=entries,
            stats=stats,
        )


@dataclass(slots=True)
class PipelineMeta:
    """流水线执行元数据。"""

    total_steps: int = 0
    attempted_steps: int = 0
    skipped_steps: list[str] = field(default_factory=list)
    #: 解析阶段耗时（语义等同旧字段 ``duration_ms``，保留后者兼容旧消费方）
    duration_ms: int = 0
    #: 解析阶段；与 ``duration_ms`` 同值，名字更明确，便于分阶段相加
    parse_ms: int = 0
    #: 引用跟踪（aux/bcf + 缓存 diff）
    refs_ms: int = 0
    #: 终端汇总渲染（``print_summary``）
    render_ms: int = 0


@dataclass(slots=True)
class ReferencesReport:
    """引用跟踪变化报告。"""

    current_keys: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    key_counts: dict[str, int] = field(default_factory=dict)
    top_cited: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class ConfigIgnoredReport:
    """配置忽略条目与抑制统计。"""

    ignore_patterns: list[str] = field(default_factory=list)
    suppressed_entries: list[ReportEntry] = field(default_factory=list)
    original_severity_counts: dict[str, dict[str, int]] = field(default_factory=dict)


@dataclass(slots=True)
class ParsedPipelineReport:
    """顶层流水线解析报告。"""

    schema_version: int = REPORT_SCHEMA_VERSION
    generated_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())
    pytexmk_version: str = "unknown"
    jobname: str = ""
    root_file: str = ""
    auxdir: str = ""
    pipeline: PipelineMeta = field(default_factory=PipelineMeta)
    severity_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    tool_results: list[ToolResultReport] = field(default_factory=list)
    references: ReferencesReport = field(default_factory=ReferencesReport)
    config_ignored: ConfigIgnoredReport = field(default_factory=ConfigIgnoredReport)
    custom_fields: dict[str, Any] = field(default_factory=dict)


# --- 工具结果模型 ---


@dataclass(slots=True)
class ToolResultStats:
    """单个解析结果的统计计数器结构。"""

    entries_count: int = 0
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolResult(_EntryHolder):
    """单个工具解析结果与条目聚合。"""

    tool_name: str = ""
    category: str = ""
    importance: Literal["high", "medium", "low"] = "low"
    source_path: str = ""
    raw_text: str = ""
    entries: list[LogEntry] = field(default_factory=list)
    stats: ToolResultStats = field(default_factory=ToolResultStats)

    @property
    def is_empty(self) -> bool:
        """判断 ToolResult 是否无任何条目。"""
        return not self.entries and not self.raw_text
