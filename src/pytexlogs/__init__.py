"""pytexlogs 公共 API；下划线前缀模块为内部实现，外部禁止 import。.

Architecture rule (DO NOT BREAK):
  - 本包为「潜在独立第三方库 pytexlogs」：未来可直接整体复制到任意 Python 项目，作为顶级包 import。
  - **禁止使用双点级别的相对 import（任何跳出子包的 from <parent-pkg> ...）**，因为当它作为顶级包时上级目录不存在。
  - 禁止直接 `import pytexmk.language / pytexmk.version / pytexmk.config ...`
    的任何主包非子包模块；外部依赖必须通过 run_pipeline 的可空参数注入（默认纯英文/unknown）。
  - 禁止在本包外新建 `log_parser.py` 薄转发文件；所有外部使用必须走本 __all__ 列表中的公共 API。
"""

import warnings as _warnings

from .core.engine import run_pipeline as _run_pipeline_raw
from .core.manager import LogParserManager
from .core.models import (
    BaseLogParser,
    LogEntry,
    LogLevel,
    ParsedLog,
    ParsedPipelineReport,
    ToolResult,
    ToolResultStats,
)
from .core.reftracker import RefChangeTracker
from .core.registry import LogParserRegistry, LogParserSpec, load_entry_points
from .core.report import load_report, write_report
from .display import (
    CATEGORY_LABEL,
    CATEGORY_ORDER,
    IMPORTANCE_LABEL,
    format_editor_jumps,
    log_editor_jumps,
    print_summary,
    set_summary_language,
    show_log_entries,
)
from .easy import (
    aggregate_stats,  # noqa: F401
    filter_severity,
    parse_auxdir,
    parse_log_file,
    parse_log_text,
)
from .exporters import to_csv, to_json, to_sarif
from .integration_demo import run_demo
from .parsers.asymptote import AsymptoteParser
from .parsers.biber import BIBER_WARNING_HINTS, BiberParser
from .parsers.bibtex import BIBTEX_ERROR_HINTS, BibtexParser
from .parsers.glossaries import GlossariesParser
from .parsers.latex import LATEX_LOG_HINTS, LatexLogParser
from .parsers.makeindex import MakeindexParser
from .parsers.minted import MintedParser
from .parsers.nomencl import NomenclParser
from .parsers.pythontex import PythontexParser
from .parsers.xindy import XindyParser


def _deprecating_alias(wrapped, old_name, new_name):
    def _wrapper(*args, **kwargs):
        _warnings.warn(
            f"{old_name}() is deprecated since pytexlogs 0.3.0; use {new_name}() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return wrapped(*args, **kwargs)

    _wrapper.__name__ = old_name
    _wrapper.__wrapped__ = wrapped
    return _wrapper


run_pipeline = _run_pipeline_raw
run_log_pipeline = _deprecating_alias(_run_pipeline_raw, "run_log_pipeline", "run_pipeline")

Manager = LogParserManager
Registry = LogParserRegistry
Report = ParsedPipelineReport

__all__ = [
    "BIBER_WARNING_HINTS",
    "BIBTEX_ERROR_HINTS",
    "CATEGORY_LABEL",
    "CATEGORY_ORDER",
    "IMPORTANCE_LABEL",
    "LATEX_LOG_HINTS",
    "AsymptoteParser",
    "BaseLogParser",
    "BiberParser",
    "BibtexParser",
    "GlossariesParser",
    "LatexLogParser",
    "LogEntry",
    "LogLevel",
    "LogParserManager",
    "LogParserRegistry",
    "LogParserSpec",
    "MakeindexParser",
    "Manager",
    "MintedParser",
    "NomenclParser",
    "ParsedLog",
    "ParsedPipelineReport",
    "PythontexParser",
    "RefChangeTracker",
    "Registry",
    "Report",
    "ToolResult",
    "ToolResultStats",
    "XindyParser",
    "filter_severity",
    "format_editor_jumps",
    "load_entry_points",
    "load_report",
    "log_editor_jumps",
    "parse_auxdir",
    "parse_log_file",
    "parse_log_text",
    "print_summary",
    "run_demo",
    "run_log_pipeline",
    "run_pipeline",
    "set_summary_language",
    "show_log_entries",
    "to_csv",
    "to_json",
    "to_sarif",
    "write_report",
]