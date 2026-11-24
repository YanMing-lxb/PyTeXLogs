"""Round 10 回归：默认报告落盘位置与脏行号容错。"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from pytexlogs import run_pipeline
from pytexlogs.core.engine import _entry_to_report


def test_default_report_written_to_cwd_when_auxdir_is_ephemeral(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """不传 auxdir 时 finally 会删掉临时目录，报告必须落在 cwd。"""
    monkeypatch.chdir(tmp_path)

    report = run_pipeline(
        jobname="main",
        print_terminal=False,
        write_report_file=True,
    )

    report_path = Path(report.custom_fields["_report_path"])
    try:
        assert report_path.exists()
        assert report_path.parent.resolve() == tmp_path.resolve()
        assert report_path.name == "main.pytexmk-report.json"
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        assert payload["jobname"] == "main"
    finally:
        # cwd 就是 tmp_path，但显式删除，避免测试依赖 tmp_path 清理。
        report_path.unlink(missing_ok=True)


def test_default_report_written_to_auxdir_when_auxdir_is_real(tmp_path: Path) -> None:
    (tmp_path / "main.log").write_text("! Undefined control sequence.\nl.5 \\badcmd\n", encoding="utf-8")

    report = run_pipeline(auxdir=tmp_path, print_terminal=False, write_report_file=True)

    report_path = Path(report.custom_fields["_report_path"])
    try:
        assert report_path == tmp_path / "main.pytexmk-report.json"
        assert report_path.exists()
    finally:
        report_path.unlink(missing_ok=True)


def test_report_write_failure_still_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """显式 report_path 写入失败时仍走 ``_report_write_error``。"""
    monkeypatch.chdir(tmp_path)
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")

    report = run_pipeline(
        jobname="main",
        print_terminal=False,
        write_report_file=True,
        report_path=blocker / "sub" / "report.json",
    )

    assert "_report_path" not in report.custom_fields
    assert report.custom_fields["_report_write_error"]


def test_entry_to_report_tolerates_dirty_line() -> None:
    dirty = SimpleNamespace(level="error", file="a.tex", line="12a", text="x")
    numeric = SimpleNamespace(level="error", file="a.tex", line="12", text="x")
    missing = SimpleNamespace(level="error", file="a.tex", line=None, text="x")

    assert _entry_to_report(dirty).line == 0
    assert _entry_to_report(numeric).line == 12
    assert _entry_to_report(missing).line is None


def test_pipeline_meta_exposes_stage_timings(tmp_path: Path) -> None:
    """0.6.4：解析/引用/渲染三段可分别读取，``duration_ms`` 仍是解析段。"""
    report = run_pipeline(
        jobname="main",
        auxdir=tmp_path,
        print_terminal=False,
        write_report_file=False,
    )
    pipeline = report.pipeline
    assert pipeline.parse_ms == pipeline.duration_ms
    assert pipeline.parse_ms >= 0
    assert pipeline.refs_ms >= 0
    assert pipeline.render_ms == 0  # 未渲染终端时保持默认值
