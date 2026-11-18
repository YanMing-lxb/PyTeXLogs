"""0.5.0 新增能力回归：报告写盘、步骤规划、hint、导出过滤、CLI 参数语义。"""

import json
from pathlib import Path

import pytest

from pytexlogs import (
    LogEntry,
    LogLevel,
    ProjectStateStore,
    ToolResult,
    ToolResultStats,
    hint_for_text,
    plan_default_steps,
    run_pipeline,
    to_csv,
    to_json,
    to_sarif,
)
from pytexlogs.cli.main import main


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_write_report_file_creates_json_and_no_tmp(tmp_path: Path) -> None:
    """write_report_file=True 必须真的落盘，且不留下 .tmp。"""
    aux = tmp_path / "aux"
    aux.mkdir()
    _write(aux / "main.log", "! LaTeX Error: File `nosuch.sty' not found.\n")
    run_pipeline(jobname="main", auxdir=aux, print_terminal=False, write_report_file=True)
    out = aux / "main.pytexmk-report.json"
    assert out.exists(), "报告未写盘"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["jobname"] == "main"
    assert list(aux.glob("*.tmp")) == []


def test_legacy_write_report_kwarg_is_rejected(tmp_path: Path) -> None:
    """0.6.0 删除了 write_report 旧名：传它必须 TypeError，而不是静默接受。"""
    aux = tmp_path / "aux"
    aux.mkdir()
    _write(aux / "main.log", "! Undefined control sequence.\n")
    with pytest.raises(TypeError):
        run_pipeline(jobname="main", auxdir=aux, print_terminal=False, write_report=True)


def test_plan_steps_avoids_duplicate_blg(tmp_path: Path) -> None:
    """有 .bcf 时只能选 biber，biber/bibtex 不能同时出现。"""
    aux = tmp_path
    _write(aux / "main.bcf", "<bcf:controlfile></bcf:controlfile>")
    _write(aux / "main.blg", "This is Biber 2.19\n")
    _write(aux / "main.log", "Output written on main.pdf (3 pages).\n")
    steps = plan_default_steps("main", aux)
    assert "biber" in steps and "bibtex" not in steps
    assert "asymptote" not in steps, ".log 不应被当成 asy 日志"


def test_bibtex_project_uses_bibtex(tmp_path: Path) -> None:
    """没有 .bcf、.blg 是 BibTeX 头 → 选 bibtex。"""
    _write(tmp_path / "main.blg", "This is BibTeX, Version 0.99d\n")
    assert "bibtex" in plan_default_steps("main", tmp_path)


def test_index_tool_sniff(tmp_path: Path) -> None:
    """`.ilg` 的头部决定 makeindex 还是 xindy。"""
    _write(tmp_path / "main.ilg", "This is xindy 6018\n")
    assert "xindy" in plan_default_steps("main", tmp_path)
    _write(tmp_path / "main.ilg", "This is makeindex, version 2.15\n")
    assert "makeindex" in plan_default_steps("main", tmp_path)


def test_index_tool_sniff_fallback_uses_any_xdy(tmp_path: Path) -> None:
    """没有头部特征时，只有真的存在 .xdy 才回退 xindy。"""
    _write(tmp_path / "main.ilg", "no tool signature here\n")
    assert "makeindex" in plan_default_steps("main", tmp_path), "无 .xdy 时不应误判 xindy"
    _write(tmp_path / "main.xdy", "(markup-locref-list)\n")
    assert "xindy" in plan_default_steps("main", tmp_path)


def test_plan_steps_sniffs_tex_engine(tmp_path: Path) -> None:
    """目录模式应按 .log 头部识别 XeLaTeX/LuaLaTeX，而不是固定 pdflatex。"""
    _write(tmp_path / "main.log", "This is XeTeX, Version 3.14159265 (MiKTeX 26.5)\n")
    assert plan_default_steps("main", tmp_path)[0] == "xelatex"

    _write(tmp_path / "main.log", "This is LuaHBTeX, Version 1.18.0\n")
    assert plan_default_steps("main", tmp_path)[0] == "lualatex"

    _write(tmp_path / "main.log", "This is pdfTeX, Version 3.14159265\n")
    assert plan_default_steps("main", tmp_path)[0] == "pdflatex"


def test_hints_match_single_backslash() -> None:
    """提示表里的双反斜杠键必须能匹配真实日志的单反斜杠文本。"""
    hint = hint_for_text("Overfull \\hbox (12.3pt too wide) in paragraph at lines 3--4")
    assert hint is not None
    assert "过宽" in hint.text


def test_hint_missing_package_has_commands() -> None:
    """缺宏包要给出 tlmgr / miktex 两条安装命令。"""
    hint = hint_for_text("! LaTeX Error: File `minted.sty' not found.")
    assert hint is not None
    assert hint.kind == "missing_package"
    assert "tlmgr install minted" in hint.commands
    assert any("miktex" in c for c in hint.commands)


def test_severity_filters_exports() -> None:
    """--severity 必须作用于 json/csv/sarif，而不只是文本。"""
    results = [
        ToolResult(
            tool_name="pdflatex",
            category="compile",
            entries=[
                LogEntry(level=LogLevel.ERROR, file="a.tex", line=1, text="bad"),
                LogEntry(level=LogLevel.WARNING, file="a.tex", line=2, text="warn"),
            ],
            stats=ToolResultStats(entries_count=2, stats={"error": 1, "warning": 1}),
        )
    ]
    data = json.loads(to_json(results, min_level=LogLevel.ERROR))
    texts = [e["text"] for e in data["results"][0]["entries"]]
    assert texts == ["bad"]
    sarif = to_sarif(results, min_level=LogLevel.ERROR)
    assert all(r["level"] == "error" for r in sarif["runs"][0]["results"])
    rules = sarif["runs"][0]["tool"]["driver"]["rules"]
    assert rules and rules[0]["id"] == "pytexlogs/error"
    row = to_csv(results, min_level=LogLevel.ERROR).strip().splitlines()
    assert len(row) == 2 and "warn" not in row[1]


def test_sarif_uri_is_posix_and_encoded() -> None:
    """Windows 反斜杠路径必须转成合法 URI。"""
    entry = ToolResult(
        tool_name="pdflatex",
        category="compile",
        entries=[LogEntry(level=LogLevel.ERROR, file="chapters\\a b.tex", line=7, text="x")],
    )
    sarif = to_sarif([entry])
    uri = sarif["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
    assert "\\" not in uri and "%20" in uri


def test_sarif_fingerprint_ignores_line_shift() -> None:
    """同一文件同一条消息换行号后，SARIF 指纹应保持不变。"""
    first = ToolResult(
        tool_name="pdflatex",
        category="compile",
        entries=[LogEntry(level=LogLevel.ERROR, file="main.tex", line=2, text="same message")],
    )
    second = ToolResult(
        tool_name="pdflatex",
        category="compile",
        entries=[LogEntry(level=LogLevel.ERROR, file="main.tex", line=20, text="same message")],
    )
    f1 = to_sarif([first])["runs"][0]["results"][0]["partialFingerprints"]["pytexlogs/v1"]
    f2 = to_sarif([second])["runs"][0]["results"][0]["partialFingerprints"]["pytexlogs/v1"]
    assert f1 == f2
    line1 = to_sarif([first])["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["region"]["startLine"]
    line2 = to_sarif([second])["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["region"]["startLine"]
    assert (line1, line2) == (2, 20)


def test_baseline_ignores_line_shift(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """baseline 只该比较问题本身，正文插入空行不应产生“新增错误”。"""
    aux = tmp_path / "aux"
    aux.mkdir()
    _write(aux / "main.log", "! LaTeX Error: File `siunitx.sty' not found.\n")
    run_pipeline(jobname="main", auxdir=aux, print_terminal=False, write_report_file=True)
    report = aux / "main.pytexmk-report.json"
    assert report.exists()

    _write(aux / "main.log", "\n\n\n! LaTeX Error: File `siunitx.sty' not found.\n")
    code = main(["check", str(aux), "--baseline", str(report)])
    assert code == 0
    out = capsys.readouterr().out
    assert "siunitx" not in out


def test_explain_uses_jobname_context(capsys: pytest.CaptureFixture[str]) -> None:
    """explain 应能用 --jobname/--root-file 给出真实可复制命令。"""
    code = main([
        "explain",
        "LaTeX Warning: Citation `Smith2020' undefined on input line 7.",
        "--jobname", "main",
        "--root-file", "main.tex",
    ])
    assert code == 0
    out = capsys.readouterr().out
    assert "biber main" in out and "bibtex main" in out


def test_explain_supports_english(capsys: pytest.CaptureFixture[str]) -> None:
    """explain --lang en 的说明和命令都应可直接使用。"""
    code = main([
        "explain",
        "! LaTeX Error: File `siunitx.sty' not found.",
        "--lang", "en",
    ])
    assert code == 0
    out = capsys.readouterr().out
    assert "Missing package/class" in out
    assert "tlmgr install siunitx" in out


def test_summary_english_hint(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """摘要里的 hint 跟随 --lang en，而不是固定中文。"""
    log = tmp_path / "main.log"
    _write(log, "! LaTeX Error: File `siunitx.sty' not found.\n")
    assert main(["summary", str(log), "--lang", "en"]) == 0
    out = capsys.readouterr().out
    assert "Missing package/class `siunitx`" in out


def test_recursive_directory_scan(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """--recursive 应同时处理多个子项目，而不是只看根目录。"""
    for name in ("proj_a", "proj_b"):
        sub = tmp_path / name
        sub.mkdir()
        _write(sub / "main.log", f"! LaTeX Error: File `{name}.sty' not found.\n")
    assert main(["summary", str(tmp_path), "--recursive"]) == 0
    out = capsys.readouterr().out
    assert "proj_a" in out and "proj_b" in out


def test_cli_global_option_before_subcommand(tmp_path: Path) -> None:
    """`pytexlogs --severity error check x.log` 的 severity 不能被默认值覆盖。"""
    log = tmp_path / "main.log"
    _write(
        log,
        "! LaTeX Error: File `x.sty' not found.\n"
        "LaTeX Warning: Reference `foo' on page 1 undefined on input line 2.\n"
    )
    assert main(["--severity", "error", "check", str(log)]) == 1


def test_cli_prints_each_entry_once(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """同一条警告只能出现一次（此前目录模式会打印 2~3 遍）。"""
    aux = tmp_path / "aux"
    aux.mkdir()
    _write(
        aux / "main.log",
        "LaTeX Warning: Reference `foo' on page 1 undefined on input line 2.\n",
    )
    assert main(["summary", str(aux)]) == 0
    out = capsys.readouterr().out
    assert out.count("找不到 reference") == 1


def test_state_lock_failure_skips_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """拿不到锁时不能写盘（否则锁形同虚设）。"""
    aux = tmp_path
    store = ProjectStateStore(aux, "main", lock_timeout=0.01)
    # 先写一次建立文件
    assert store.update_namespace("pytexlogs", refs={"keys": ["a"]})
    before = store.load()
    monkeypatch.setattr(store, "_try_acquire", lambda: False)
    assert store.update_namespace("pytexlogs", refs={"keys": ["b"]}) is False
    assert store.load() == before


def test_no_tmp_file_when_report_write_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """报告序列化失败时不能留下 .tmp 残留。"""
    aux = tmp_path
    _write(aux / "main.log", "! error\n")
    import pytexlogs.core.report as _report

    def _boom(*a, **k):
        raise TypeError("boom")

    monkeypatch.setattr(_report, "write_report", _boom)
    run_pipeline(jobname="main", auxdir=aux, print_terminal=False, write_report_file=True)
    assert list(aux.glob("*.tmp")) == []
