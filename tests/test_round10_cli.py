"""Round 10 CLI 修复回归：裸路径等价 ``check``、解析失败在所有格式可见。"""

import importlib
import io
import json
import sys
from pathlib import Path

import pytest

from pytexlogs.cli.main import main
from pytexlogs.core.models import ToolResultReport

#: 包的 ``__init__`` 把 ``main`` 暴露成函数，模块对象要从 sys.modules 里取。
_cli_main_module = importlib.import_module("pytexlogs.cli.main")

#: 与 tests/fixtures/sample.log 同构：pdfTeX 头 + 一个可识别的 ERROR。
_LOG_TEXT = (
    "This is pdfTeX, Version 3.141592653-2.6-1.40.26 (TeX Live 2024)\n"
    "entering extended mode\n"
    "(./main.tex\n"
    "LaTeX2e <2024/02/28> patch level 1\n"
    "(./main.aux)\n"
    "! Undefined control sequence.\n"
    "l.5 \\foobar\n"
    "!  ==> Fatal error occurred, no output PDF file produced!\n"
)


def _run(argv: list[str]) -> tuple[int, str, str]:
    """捕获 stdout/stderr 后直接调用 CLI 入口。"""
    out, err = io.StringIO(), io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = main(argv)
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    return rc, out.getvalue(), err.getvalue()


@pytest.fixture
def main_log(tmp_path: Path) -> Path:
    log = tmp_path / "main.log"
    log.write_text(_LOG_TEXT, encoding="utf-8")
    return log


@pytest.fixture
def parse_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """让收集层直接返回一条“解析器抛异常”的报告。"""

    def _fake_collect(paths, args):
        return [
            ToolResultReport(
                tool_name="pdflatex",
                category="compile",
                entries=[],
                parse_exception={"type": "RuntimeError", "message": "boom"},
                stats={"entries_count": 0},
            )
        ]

    monkeypatch.setattr(_cli_main_module, "_collect_from_paths", _fake_collect)


def test_bare_path_matches_check(main_log: Path) -> None:
    """``pytexlogs main.log`` 与 ``pytexlogs check main.log`` 输出/退出码一致。"""
    rc_bare, out_bare, err_bare = _run([str(main_log)])
    rc_check, out_check, err_check = _run(["check", str(main_log)])

    assert rc_bare == rc_check == 1, (rc_bare, rc_check, err_bare, err_check)
    assert out_bare == out_check
    assert "Undefined control sequence" in out_bare


def test_bare_path_with_lang_en(main_log: Path) -> None:
    """裸路径前的 ``--lang en`` 生效，且与显式 check 完全一致。"""
    rc_bare, out_bare, _ = _run(["--lang", "en", str(main_log)])
    rc_check, out_check, _ = _run(["check", "--lang", "en", str(main_log)])

    assert rc_bare == rc_check == 1
    assert out_bare == out_check
    assert "Error Summary" in out_bare


def test_bare_path_with_open_dry_run(main_log: Path) -> None:
    """``pytexlogs main.log --open`` 可用（尾随选项不能被当成路径）。"""
    rc, _out, err = _run(
        [
            str(main_log),
            "--open",
            "--editor",
            "custom:code --goto %f:%l",
            "--dry-run",
        ]
    )
    assert rc == 1
    assert "[dry-run open]" in err


def test_parse_failure_visible_in_text(parse_failure: None) -> None:
    """text：解析失败必须出现在 stdout，不能谎称是 baseline/severity 过滤为空。"""
    rc, out, _err = _run(["check", "broken.log", "--lang", "zh"])

    assert rc == 0
    assert "pdflatex" in out
    assert "RuntimeError" in out
    assert "boom" in out
    assert "没有新增条目" not in out
    assert "存在解析失败" in out


def test_parse_failure_visible_in_json(parse_failure: None) -> None:
    """json：结果对象保留，parse_exception 字段可见。"""
    rc, out, _err = _run(["check", "broken.log", "--format", "json"])

    assert rc == 0
    payload = json.loads(out)
    assert len(payload["results"]) == 1
    assert payload["results"][0]["parse_exception"] == {
        "type": "RuntimeError",
        "message": "boom",
    }
    assert "RuntimeError" in out


@pytest.mark.parametrize("fmt", ["csv", "sarif"])
def test_parse_failure_warns_on_stderr(parse_failure: None, fmt: str) -> None:
    """csv/sarif：失败信息走 stderr 的 warning，stdout 载荷保持干净。"""
    rc, out, err = _run(["check", "broken.log", "--format", fmt])

    assert rc == 0
    assert "warning" in err
    assert "pdflatex" in err
    assert "RuntimeError" in err
    assert "RuntimeError" not in out
    # stdout 仍是可解析的载荷。
    if fmt == "csv":
        assert out.startswith(("file,line,level", "\ufefffile,line,level"))
    else:
        assert "$schema" in json.loads(out)


def test_subcommands_and_version_unaffected(main_log: Path) -> None:
    """裸路径支持不能破坏 --version / --help / 既有子命令。"""
    rc, out, _ = _run(["--version"])
    assert rc == 0 and "pytexlogs" in out

    rc, out, _ = _run(["--help"])
    assert rc == 0
    assert all(name in out for name in ("check", "summary", "export", "demo"))

    rc, out, _ = _run([])
    assert rc == 0 and "check" in out

    rc, out, _ = _run(["summary", str(main_log)])
    assert rc == 0

    rc, out, _ = _run(["export", str(main_log), "--format", "json"])
    assert rc == 0 and json.loads(out)["results"]

    rc, _out, _ = _run(["explain", "Missing character"])
    assert rc in (0, 1)
