"""pytexlogs 公共 API；下划线前缀模块为内部实现，外部禁止 import。.

Architecture rule (DO NOT BREAK):
  - 本包为「潜在独立第三方库 pytexlogs」：未来可直接整体复制到任意 Python 项目，作为顶级包 import。
  - **禁止使用双点级别的相对 import（任何跳出子包的 from <parent-pkg> ...）**，因为当它作为顶级包时上级目录不存在。
  - 禁止直接 `import pytexmk.language / pytexmk.version / pytexmk.config ...`
    的任何主包非子包模块；外部依赖必须通过 run_pipeline 的可空参数注入（默认纯英文/unknown）。
  - 禁止在本包外新建 `log_parser.py` 薄转发文件；所有外部使用必须走本 __all__ 列表中的公共 API。
"""

from .core.engine import run_pipeline
from .core.logkind import (
    plan_default_steps,
    sniff_bib_tool,
    sniff_index_tool,
    sniff_tex_engine,
)
from .core.manager import LogParserManager
from .core.models import (
    BaseLogParser,
    LogEntry,
    LogLevel,
    ParsedLog,
    ParsedPipelineReport,
    ToolResult,
    ToolResultReport,
    ToolResultStats,
    level_from_value,
)
from .core.reftracker import RefChangeTracker
from .core.registry import LogParserRegistry, LogParserSpec, load_entry_points
from .core.report import load_report, write_report
from .core.state import (
    PROJECT_STATE_FILENAME,
    SCHEMA_VERSION,
    ProjectStateStore,
)
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
from .exporters.json_exporter import filter_by_level
from .hints import Hint, detect_missing_package, hint_for_entry, hint_for_text
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
from .version import __version__

__all__ = [
    "__version__",
    "BIBER_WARNING_HINTS",
    "BIBTEX_ERROR_HINTS",
    "CATEGORY_LABEL",
    "CATEGORY_ORDER",
    "IMPORTANCE_LABEL",
    "LATEX_LOG_HINTS",
    "PROJECT_STATE_FILENAME",
    "SCHEMA_VERSION",
    "AsymptoteParser",
    "BaseLogParser",
    "BiberParser",
    "BibtexParser",
    "GlossariesParser",
    "Hint",
    "LatexLogParser",
    "LogEntry",
    "LogLevel",
    "LogParserManager",
    "LogParserRegistry",
    "LogParserSpec",
    "MakeindexParser",
    "MintedParser",
    "NomenclParser",
    "ParsedLog",
    "ParsedPipelineReport",
    "ProjectStateStore",
    "PythontexParser",
    "RefChangeTracker",
    "ToolResult",
    "ToolResultReport",
    "ToolResultStats",
    "XindyParser",
    "detect_missing_package",
    "filter_by_level",
    "filter_severity",
    "format_editor_jumps",
    "hint_for_entry",
    "hint_for_text",
    "load_entry_points",
    "load_report",
    "log_editor_jumps",
    "level_from_value",
    "parse_auxdir",
    "parse_log_file",
    "parse_log_text",
    "plan_default_steps",
    "print_summary",
    "run_demo",
    "run_pipeline",
    "set_summary_language",
    "show_log_entries",
    "sniff_bib_tool",
    "sniff_index_tool",
    "sniff_tex_engine",
    "to_csv",
    "to_json",
    "to_sarif",
    "write_report",
]
