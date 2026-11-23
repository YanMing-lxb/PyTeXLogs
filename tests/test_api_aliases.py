"""公共 API 表：0.6.0 起只保留真实名字，兼容别名必须不存在。"""

import importlib

import pytest

PUBLIC_API = [
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
    "MintedParser",
    "NomenclParser",
    "ParsedLog",
    "ParsedPipelineReport",
    "PythontexParser",
    "RefChangeTracker",
    "XindyParser",
    "format_editor_jumps",
    "level_from_value",
    "load_report",
    "log_editor_jumps",
    "print_summary",
    "run_demo",
    "run_pipeline",
    "show_log_entries",
    "write_report",
]

#: 0.5 及更早的兼容别名；0.6.0 明确删除，留在这里做"不许回来"的回归哨兵。
REMOVED_ALIASES = ["run_log_pipeline", "Manager", "Registry", "Report"]


@pytest.mark.parametrize("name", PUBLIC_API)
def test_public_symbols_exist(name):
    pkg = importlib.import_module("pytexlogs")
    assert getattr(pkg, name, None) is not None, f"公共 API 缺少 {name}"


@pytest.mark.parametrize("name", REMOVED_ALIASES)
def test_compat_aliases_are_gone(name):
    pkg = importlib.import_module("pytexlogs")
    assert not hasattr(pkg, name), f"{name} 是 0.5 的兼容别名，0.6.0 应已删除"
    assert name not in pkg.__all__, f"{name} 不应出现在 __all__ 中"


def test_run_pipeline_is_not_wrapped():
    """run_pipeline 必须是 engine 里的真实函数，而不是别名包装。"""
    import pytexlogs as pkg
    from pytexlogs.core.engine import run_pipeline as engine_run_pipeline

    assert pkg.run_pipeline is engine_run_pipeline


def test_aggregate_stats_is_public():
    """aggregate_stats 是公共 API：既在 __all__ 中，也可直接调用。"""
    import pytexlogs

    assert "aggregate_stats" in pytexlogs.__all__
    assert callable(pytexlogs.aggregate_stats)


def test_star_import_exposes_every_all_name():
    """`from pytexlogs import *` 必须把 __all__ 里的每个名字都带出来。"""
    import pytexlogs

    ns: dict[str, object] = {}
    exec("from pytexlogs import *", ns)
    assert "aggregate_stats" in ns
    for name in pytexlogs.__all__:
        assert getattr(pytexlogs, name, None) is not None, f"__all__ 中的 {name} 无法访问"
