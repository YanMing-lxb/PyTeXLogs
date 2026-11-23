"""CLI 聚合层直接建在报告模型（``ToolResultReport``）上（L13 收敛）。

0.5 的 CLI 先把 ``ToolResultReport`` 转成 ``ToolResult``，再在导出时转回 dict，
同一份数据被抄了三次；这里锁定收敛后的三件事：

1. ``_collect_from_paths`` 返回的就是报告模型，不再有 ``ToolResult`` 中间层；
2. ``--format json`` 的对外形状保持不变（``results`` / 条目字段 / ``stats``），
   唯一的差异是 ``raw_text`` 不再随 CLI 导出（文件模式下它会把整份日志再抄一遍）；
3. ``--baseline`` 的路径不存在时给出可读报错（而不是 FileNotFoundError 冒到顶层）。
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from pytexlogs.core.models import LogEntry, LogLevel, ParsedLog, ToolResultReport

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SAMPLE_LOG = _PROJECT_ROOT / "tests" / "fixtures" / "sample.log"


def _run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytexlogs.cli", *args],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        check=False,
    )


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """最小项目：主文件 + 带错误/致命错误的 sample 日志。"""
    shutil.copy(_SAMPLE_LOG, tmp_path / "main.log")
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\n\\foobar\n\\end{document}",
        encoding="utf-8",
    )
    return tmp_path


def test_collect_returns_report_models(project: Path) -> None:
    """``_collect_from_paths`` 的返回类型必须是报告模型（无 ToolResult 中间层）。"""
    from pytexlogs.cli.main import _collect_from_paths

    class _Args:
        recursive = False
        jobname = None
        root_file = None

    results = _collect_from_paths([str(project / "main.log")], _Args())
    assert results, "没有收集到任何结果"
    assert all(isinstance(r, ToolResultReport) for r in results)


def test_from_parsed_log_is_single_conversion_point() -> None:
    """运行时模型 → 报告模型只在 ``ToolResultReport.from_parsed_log`` 里做。"""
    parsed = ParsedLog(
        entries=[
            LogEntry(level=LogLevel.ERROR, file="main.tex", line=5, text="! Undefined control sequence."),
            LogEntry(level=LogLevel.WARNING, file="main.tex", line=9, text="LaTeX Warning: x"),
        ],
        tool_name="latex",
        category="compile",
        importance="low",
    )
    report = ToolResultReport.from_parsed_log(parsed)
    assert [e.level for e in report.entries] == ["error", "warning"]
    assert report.importance == "high"  # 有 error 就必须是 high
    # stats 现在由 recompute_stats 统一补齐（等级键 + *_count），这里只锁定
    # 与条目集合直接相关的关键字段，不锁定完整键集合。
    assert report.stats["entries_count"] == 2
    assert report.stats["error"] == 1
    assert report.stats["errors_count"] == 1
    assert report.stats["warning"] == 1
    assert report.stats["warnings_count"] == 1


def test_cli_json_shape_is_stable(project: Path) -> None:
    """``--format json`` 仍是 ``{"results": [...]}``，条目字段与旧版一致。"""
    proc = _run_cli("export", "main.log", "--format", "json", cwd=project)
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)

    assert payload["__format__"] == "pytexlogs-json-v1"
    assert len(payload["results"]) == 1
    tr = payload["results"][0]
    assert set(tr) == {
        "tool_name",
        "category",
        "importance",
        "source_path",
        "entries",
        "stats",
    }, "CLI JSON 的字段名变了（raw_text 已从 CLI 导出中移除）"
    assert tr["tool_name"] == "latex"  # 由解析器给出，而不是文件后缀
    assert tr["stats"]["entries_count"] == len(tr["entries"])
    assert {"level", "file", "line", "text", "error_pos_text"} == set(tr["entries"][0])
    assert tr["entries"][0]["level"] == "error"


def test_cli_baseline_missing_file_is_readable(project: Path) -> None:
    """基线不存在：可读报错 + 退出码 2，而不是 FileNotFoundError 堆栈。"""
    proc = _run_cli("check", "main.log", "--baseline", "nope.json", cwd=project)
    assert proc.returncode == 2
    assert "FileNotFoundError" not in proc.stderr
    assert "nope.json" in proc.stderr


def test_cli_baseline_filters_everything(project: Path) -> None:
    """同一个日志先导出报告，再以它为基线：结论必须是“没有新增条目”。"""
    from pytexlogs import run_pipeline

    run_pipeline(
        jobname="main",
        auxdir=str(project),
        print_terminal=False,
        write_report_file=True,
        report_path=str(project / "baseline.json"),
    )
    assert (project / "baseline.json").exists()

    proc = _run_cli("check", "main.log", "--baseline", "baseline.json", cwd=project)
    assert proc.returncode == 0, proc.stderr
    assert "没有新增条目" in proc.stdout
    # 过滤到空之后不能再打印“By category: compile=1”这种会误导人的统计
    assert "By category" not in proc.stdout

    proc = _run_cli("export", "main.log", "--baseline", "baseline.json", "--format", "json", cwd=project)
    assert json.loads(proc.stdout)["results"] == []
