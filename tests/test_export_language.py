"""round6 P2-4：导出层（JSON/CSV/SARIF）可选 ``language`` 透传测试。

锁定三件事：
- ``language="en"`` 时 hint 文案取英文（缺失英文时回退中文）；不传或传其他值
  时保持默认中文，旧断言不破；
- JSON/SARIF 始终保留 ``text``/``text_en`` 双字段，``kind``/``commands``/
  ``rule_id`` 不受语言影响；
- CSV 表头、JSON ``results`` 形状、SARIF 必填字段回归不变。
"""

import csv
import io
import json
import re
import sys
from pathlib import Path

import pytest

from pytexlogs import run_pipeline, to_csv, to_json, to_sarif

_CJK = re.compile(r"[\u4e00-\u9fff]")

_CITATION_LOG = """This is pdfTeX, Version 3.14159265-2.6-1.40.25
LaTeX Warning: Citation `Smith2020' undefined on input line 3.
Transcript written on main.log.
"""


@pytest.fixture
def citation_report():
    """含一条 ``undefined_citation`` 可命中 hint 的报告。"""
    return run_pipeline(
        jobname="main",
        captured_outputs={"pdflatex": _CITATION_LOG},
    )


def _json_hint(report, **kwargs):
    data = json.loads(to_json(report, **kwargs))
    assert data["hints"], "JSON 没有导出任何 hint"
    return data["hints"][0]["hint"]


# ---------------------------------------------------------------- CSV


def test_csv_hint_default_is_chinese(citation_report) -> None:
    """不传 language：CSV ``hint`` 列仍是中文（默认行为不变）。"""
    rows = list(csv.reader(io.StringIO(to_csv(citation_report))))
    assert rows[0] == ["file", "line", "level", "category", "tool", "text", "hint", "source_path"]
    hint_cell = next(row[6] for row in rows[1:] if row[6])
    assert _CJK.search(hint_cell), "默认 CSV hint 应为中文"


def test_csv_hint_language_en(citation_report) -> None:
    """``language="en"``：CSV ``hint`` 列是英文；表头与其他列不变。"""
    rows = list(csv.reader(io.StringIO(to_csv(citation_report, language="en"))))
    assert rows[0] == ["file", "line", "level", "category", "tool", "text", "hint", "source_path"]
    hint_cell = next(row[6] for row in rows[1:] if row[6])
    assert not _CJK.search(hint_cell), f"en 下 CSV hint 不应含中文：{hint_cell!r}"


# ---------------------------------------------------------------- JSON


def test_json_hint_default_is_chinese(citation_report) -> None:
    """不传 language：JSON hint ``text`` 为中文，``text_en`` 双字段仍在。"""
    hint = _json_hint(citation_report)
    assert _CJK.search(hint["text"]), "默认 JSON hint.text 应为中文"
    assert hint["text_en"], "text_en 字段必须保留"
    assert hint["kind"] == "undefined_citation"
    assert hint["commands"] == ["biber main", "bibtex main"]


def test_json_hint_language_en(citation_report) -> None:
    """``language="en"``：``text`` 取英文，``text_en`` 仍在；kind/commands 不变。"""
    hint = _json_hint(citation_report, language="en")
    assert not _CJK.search(hint["text"]), f"en 下 JSON hint.text 不应含中文：{hint['text']!r}"
    assert hint["text_en"], "text_en 字段必须保留"
    assert hint["text"] == hint["text_en"]
    assert hint["kind"] == "undefined_citation"
    assert hint["commands"] == ["biber main", "bibtex main"]


def test_json_results_shape_regression(citation_report) -> None:
    """JSON ``results`` 形状回归：list 输入仍导出 ``results`` 数组。"""
    from pytexlogs import LogEntry, LogLevel, ToolResult

    tr = ToolResult(
        tool_name="pdflatex",
        category="compile",
        source_path="captured:pdflatex",
        entries=[LogEntry(level=LogLevel.ERROR, file="main.tex", line=42, text="Undefined control sequence \\foo")],
    )
    data = json.loads(to_json([tr]))
    assert isinstance(data["results"], list)
    assert data["results"][0]["tool_name"] == "pdflatex"
    # 语言参数不影响 results 顶层形状
    data_en = json.loads(to_json([tr], language="en"))
    assert isinstance(data_en["results"], list)


# ---------------------------------------------------------------- SARIF


def _sarif_hint(result: dict) -> dict:
    return result["properties"]["pytexlogs/hint"]


def test_sarif_hint_default_is_chinese(citation_report) -> None:
    """不传 language：SARIF hint ``text`` 为中文。"""
    sarif = to_sarif(citation_report)
    result = next(r for r in sarif["runs"][0]["results"] if "properties" in r)
    hint = _sarif_hint(result)
    assert _CJK.search(hint["text"]), "默认 SARIF hint.text 应为中文"
    assert hint["text_en"]
    assert {"ruleId", "level", "message", "locations", "partialFingerprints"} <= set(result)


def test_sarif_hint_language_en(citation_report) -> None:
    """``language="en"``：SARIF ``properties["pytexlogs/hint"].text`` 为英文。"""
    sarif = to_sarif(citation_report, language="en")
    result = next(r for r in sarif["runs"][0]["results"] if "properties" in r)
    hint = _sarif_hint(result)
    assert not _CJK.search(hint["text"]), f"en 下 SARIF hint.text 不应含中文：{hint['text']!r}"
    assert hint["text_en"]
    assert hint["kind"] == "undefined_citation"
    assert hint["commands"] == ["biber main", "bibtex main"]
    # SARIF 必填字段回归
    assert {"ruleId", "level", "message", "locations", "partialFingerprints"} <= set(result)


def test_sarif_required_fields_regression(citation_report) -> None:
    """无 hint 的结果也保持 SARIF 必填字段；不传 language 不改变结构。"""
    sarif = to_sarif(citation_report)
    for result in sarif["runs"][0]["results"]:
        assert {"ruleId", "level", "message", "locations", "partialFingerprints"} <= set(result)


# ---------------------------------------------------------------- CLI 透传


def test_cli_export_json_passes_lang_en(tmp_path: Path) -> None:
    """CLI ``--lang en`` 必须把语言透传到 JSON 导出的 hint。"""
    from pytexlogs.cli import main as cli_main

    log_file = tmp_path / "main.log"
    log_file.write_text(_CITATION_LOG, encoding="utf-8")

    def _run(args: list[str]) -> str:
        out, err = io.StringIO(), io.StringIO()
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = out, err
        try:
            code = cli_main(args)
        finally:
            sys.stdout, sys.stderr = old_out, old_err
        assert code == 0, err.getvalue()
        return out.getvalue()

    en_payload = json.loads(_run(["export", str(log_file), "--format", "json", "--lang", "en"]))
    en_hint = en_payload["hints"][0]["hint"]
    assert not _CJK.search(en_hint["text"]), f"CLI en 导出 hint 仍含中文：{en_hint['text']!r}"

    zh_payload = json.loads(_run(["export", str(log_file), "--format", "json", "--lang", "zh"]))
    zh_hint = zh_payload["hints"][0]["hint"]
    assert _CJK.search(zh_hint["text"]), "CLI zh 导出 hint 应为中文"
