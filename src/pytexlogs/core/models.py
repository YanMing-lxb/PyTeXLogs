"""PyTeXLogs 核心数据模型：日志等级、条目、解析结果、报告结构与工具结果。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal, override  # noqa: F401  # override 仅供注解使用

#: 严重程度排序：数字越小越严重（ERROR 最靠前）。
#: 定义在模块级而非每次比较时重建，避免排序时的字典构造开销。
_SEVERITY_RANK: dict[LogLevel, int]


class LogLevel(Enum):
    """日志等级枚举：错误/警告/排版/信息/字体/图形/页面。"""

    ERROR = "error"
    WARNING = "warning"
    TYPESET = "typesetting"
    INFO = "info"
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

    _FALLBACK_ENCODINGS: tuple[str, ...] = (
        "utf-8",
        "utf-8-sig",
        "gbk",
        "gb18030",
        "latin-1",
    )

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
        result = self.parse(text, root_file or self.root_file)
        result.source_path = str(path)
        return result

    def _read_log_text(self, log_path: str | Path) -> str:
        path = Path(log_path)
        data = path.read_bytes()
        for encoding in self._FALLBACK_ENCODINGS:
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")

    def _resolve_file_path(self, filename: str) -> str:
        """将相对路径解析为绝对路径，带缓存。"""
        if not filename:
            return self.root_file or ""
        if filename in self._resolved_paths:
            return self._resolved_paths[filename]
        path = Path(filename)
        if path.is_absolute():
            resolved = str(path)
        else:
            root_dir = Path(self.root_file).parent if self.root_file else Path.cwd()
            try:
                resolved = str((root_dir / filename).resolve())
            except Exception:
                resolved = filename
        self._resolved_paths[filename] = resolved
        return resolved


# --- 报告数据模型 ---


@dataclass(slots=True)
class ReportEntry:
    """单条日志条目，仅使用 JSON 兼容类型。"""

    level: str = "info"
    file: str | None = None
    line: int | None = None
    text: str = ""
    error_pos_text: str | None = None
    source: str | None = None


@dataclass(slots=True)
class ToolResultReport:
    """单个工具的解析结果汇总。"""

    tool_name: str = ""
    category: str = ""
    importance: str = "medium"
    source_path: str | None = None
    entries: list[ReportEntry] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
    parse_exception: dict[str, str] | None = None


@dataclass(slots=True)
class PipelineMeta:
    """流水线执行元数据。"""

    total_steps: int = 0
    attempted_steps: int = 0
    skipped_steps: list[str] = field(default_factory=list)
    duration_ms: int = 0


@dataclass(slots=True)
class ReferencesReport:
    """引用跟踪变化报告。"""

    current_keys: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    previous_aux_hash: str | None = None
    current_aux_hash: str | None = None
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

    schema_version: int = 1
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
