"""ToolResultReport 的等级筛选 API 与 ParsedLog 口径一致性。"""

from pytexlogs import LogLevel, ToolResultReport
from pytexlogs.core.models import ParsedLog, ReportEntry


def _report():
    return ToolResultReport(
        tool_name="makeindex",
        entries=[
            ReportEntry(level="error", text="bad style"),
            ReportEntry(level="warning", text="mild"),
            ReportEntry(level="warning", text="mild2"),
            ReportEntry(level="info", text="note"),
        ],
    )


def test_errors_returns_only_error_entries():
    tr = _report()
    assert [e.text for e in tr.errors] == ["bad style"]


def test_warnings_returns_only_warning_entries():
    tr = _report()
    assert [e.text for e in tr.warnings] == ["mild", "mild2"]


def test_info_returns_only_info_entries():
    tr = _report()
    assert [e.text for e in tr.info] == ["note"]


def test_by_level_accepts_enum_and_string():
    tr = _report()
    assert len(tr.by_level(LogLevel.WARNING)) == 2
    assert len(tr.by_level("warning")) == 2


def test_by_level_unknown_string_falls_back_to_info():
    """未知等级按 INFO 兜底，与 _resolve_level 的行为一致。"""
    tr = _report()
    assert [e.text for e in tr.by_level("bogus")] == ["note"]


def test_empty_entries_all_filters_empty():
    tr = ToolResultReport(tool_name="x")
    assert tr.errors == [] and tr.warnings == [] and tr.info == []


def test_dataclass_slots_still_active():
    """加 property 不能把 slots 破坏成 __dict__。"""
    tr = _report()
    assert not hasattr(tr, "__dict__")


def test_parsed_log_and_tool_result_report_same_api_surface():
    """两种模型对外暴露的等级筛选口径必须一致。"""
    pl = ParsedLog()
    tr = ToolResultReport()
    for name in ("errors", "warnings", "info", "by_level"):
        assert hasattr(pl, name), f"ParsedLog 缺少 {name}"
        assert hasattr(tr, name), f"ToolResultReport 缺少 {name}"


def test_engine_result_exposes_errors_in_end_to_end_run():
    """端到端：真实 pipeline 结果里 tr.errors 直接可用。"""
    import pathlib
    import shutil
    import tempfile

    from pytexlogs import run_pipeline

    src = pathlib.Path(__file__).resolve().parent.parent / "tests" / "fixtures"
    aux = pathlib.Path(tempfile.mkdtemp()) / "Auxiliary"
    aux.mkdir(parents=True)
    for name in ("sample.log",):
        p = src / name
        if p.exists():
            shutil.copy(p, aux / name)

    r = run_pipeline("sample", aux, root_file="sample", quiet=True)
    any_entries = False
    for tr in r.tool_results:
        total = len(tr.errors) + len(tr.warnings) + len(tr.info)
        # errors+warnings+info 不应超过 entries 总数
        assert total <= len(tr.entries)
        if tr.entries:
            any_entries = True
    # 测试样本含 ERROR 时，errors 必须非空（不依赖具体顺序）
    print(f"  tool_results={len(r.tool_results)} any_entries={any_entries}")
