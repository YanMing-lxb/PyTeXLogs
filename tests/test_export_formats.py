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


def test_to_json_has_keys():
    """TR-5.1：to_json 结果解析成功，含 __format__ / pytexlogs_version / meta / tool_results。"""
    report = run_pipeline(captured_outputs={"pdflatex": _SAMPLE_LOG_TEXT})
    raw = to_json(report)
    data = json.loads(raw)

    assert data["__format__"] == "pytexlogs-json-v1"
    assert data["pytexlogs_version"] == "0.3.0"
    assert "meta" in data
    assert "tool_results" in data


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
        "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/"
        "Schemata/sarif-schema-2.1.0.json"
    )
    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["tool"]["driver"]["name"] == "pytexlogs"
    assert sarif["runs"][0]["results"][0]["locations"][0]["physicalLocation"][
        "region"
    ]["startLine"] >= 1


def test_empty_no_crash():
    """Check-5.5：空输入 to_csv / to_sarif 不抛异常，返回合法结构。"""
    csv_out = to_csv([])
    assert csv_out.splitlines()[0] == "file,line,level,category,tool,text,hint,source_path"

    sarif_out = to_sarif([])
    assert sarif_out["runs"][0]["results"] == []
    assert sarif_out["version"] == "2.1.0"
    assert sarif_out["runs"][0]["tool"]["driver"]["name"] == "pytexlogs"
