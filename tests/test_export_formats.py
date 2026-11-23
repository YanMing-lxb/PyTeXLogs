"""Task 5 三种结构化导出（JSON/CSV/SARIF）测试（TR-5.1/5.2/5.3 + Check-5.5）。"""

import json

from pytexlogs import (
    LogEntry,
    LogLevel,
    ToolResult,
    run_pipeline,
    to_csv,
    to_json,
    to_sarif,
)

_SAMPLE_LOG_TEXT = """This is pdfTeX, Version 3.14159265-2.6-1.40.25
(./sample.tex
LaTeX Warning: Reference `missing' on page 1 undefined on input line 3.
! Undefined control sequence.
l.5 \\badcmd
Output written on sample.pdf (1 page, 1000 bytes).
Transcript written on sample.log.
"""

_CITATION_LOG_TEXT = """This is pdfTeX, Version 3.14159265-2.6-1.40.25
LaTeX Warning: Citation `Smith2020' undefined on input line 3.
Transcript written on main.log.
"""


def test_to_json_has_keys():
    """TR-5.1：to_json 结果解析成功，含 __format__ / pytexlogs_version / meta / tool_results。"""
    from pytexlogs import version as _version

    report = run_pipeline(captured_outputs={"pdflatex": _SAMPLE_LOG_TEXT})
    raw = to_json(report)
    data = json.loads(raw)

    assert data["__format__"] == "pytexlogs-json-v1"
    assert data["pytexlogs_version"] == _version.__version__
    assert data.get("report_schema") == 1
    assert "meta" in data
    assert "tool_results" in data


def test_to_json_includes_structured_hints():
    """JSON 顶层 hints 必须能拿到工具作用域与项目 jobname。"""
    report = run_pipeline(
        jobname="main",
        captured_outputs={"pdflatex": _CITATION_LOG_TEXT},
    )
    data = json.loads(to_json(report))
    assert data["hints"], "JSON 没有导出任何 hint"
    hint = data["hints"][0]
    assert hint["hint"]["kind"] == "undefined_citation"
    assert hint["hint"]["commands"] == ["biber main", "bibtex main"]
    assert hint["tool"] == "pdflatex"

    no_hints = json.loads(to_json(report, include_hints=False))
    assert "hints" not in no_hints


def test_to_sarif_includes_structured_hints():
    """SARIF 的 hint 放在 result.properties，且不改变既有必填字段。"""
    report = run_pipeline(
        jobname="main",
        captured_outputs={"pdflatex": _CITATION_LOG_TEXT},
    )
    sarif = to_sarif(report)
    result = next(r for r in sarif["runs"][0]["results"] if "properties" in r)
    hint = result["properties"]["pytexlogs/hint"]
    assert hint["kind"] == "undefined_citation"
    assert hint["commands"] == ["biber main", "bibtex main"]
    assert {"ruleId", "level", "message", "locations", "partialFingerprints"} <= set(result)

    no_hints = to_sarif(report, include_hints=False)
    assert all("properties" not in r for r in no_hints["runs"][0]["results"])


def test_to_csv_header():
    """TR-5.2：to_csv 输出表头第一行严格等于 file,line,level,category,tool,text,hint,source_path。"""
    single_tool_result = ToolResult(
        tool_name="pdflatex",
        category="compile",
        source_path="captured:pdflatex",
        entries=[
            LogEntry(
                level=LogLevel.ERROR,
                file="main.tex",
                line=42,
                text="Undefined control sequence \\foo",
            )
        ],
    )
    csv_text = to_csv([single_tool_result])
    first_line = csv_text.splitlines()[0]
    assert first_line == "file,line,level,category,tool,text,hint,source_path"


def test_to_sarif_schema():
    """TR-5.3：to_sarif 返回合法 SARIF v2.1.0 最小子集关键字段。"""
    report = run_pipeline(captured_outputs={"pdflatex": _SAMPLE_LOG_TEXT})
    has_error = False
    for tr in report.tool_results:
        for e in tr.entries:
            if e.level == "error":
                has_error = True
                break
        if has_error:
            break
    if not has_error:
        report.tool_results.append(report.tool_results[0])
        report.tool_results[-1].entries[0].level = "error"
        report.tool_results[-1].entries[0].line = 5
        report.tool_results[-1].entries[0].file = "./sample.tex"

    sarif = to_sarif(report)

    assert sarif["$schema"] == (
        "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"
    )
    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["tool"]["driver"]["name"] == "pytexlogs"
    assert sarif["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["region"]["startLine"] >= 1


def test_empty_no_crash():
    """Check-5.5：空输入 to_csv / to_sarif 不抛异常，返回合法结构。"""
    csv_out = to_csv([])
    assert csv_out.splitlines()[0] == "file,line,level,category,tool,text,hint,source_path"

    sarif_out = to_sarif([])
    assert sarif_out["runs"][0]["results"] == []
    assert sarif_out["version"] == "2.1.0"
    assert sarif_out["runs"][0]["tool"]["driver"]["name"] == "pytexlogs"
