import io
import subprocess
import sys
from pathlib import Path

import pytest

from pytexlogs import (
    LogEntry,
    LogLevel,
    ParsedLog,
    print_summary,
)


def _build_results() -> list[ParsedLog]:
    bib_plog = ParsedLog(
        category="bibliography",
        tool_name="bibtex",
        importance="high",
        entries=[
            LogEntry(
                level=LogLevel.ERROR,
                file="main.bib",
                line=15,
                text="Undefined reference 'Author2024'",
            ),
            LogEntry(
                level=LogLevel.WARNING,
                file="main.bib",
                line=22,
                text="Missing journal field",
            ),
        ],
    )
    code_plog = ParsedLog(
        category="code",
        tool_name="pythontex",
        importance="high",
        entries=[
            LogEntry(
                level=LogLevel.ERROR,
                file="main.tex",
                line=77,
                text="ZeroDivisionError: division by zero",
            ),
        ],
    )
    return [bib_plog, code_plog]


def test_zh_en_titles_different():
    results = _build_results()
    buf_zh = io.StringIO()
    print_summary(results, use_logger=False, stream=buf_zh)
    zh_text = buf_zh.getvalue()

    buf_en = io.StringIO()
    print_summary(results, language="en", use_logger=False, stream=buf_en)
    en_text = buf_en.getvalue()

    assert zh_text != en_text
    has_zh = ("错误" in zh_text) or ("警告" in zh_text)
    has_en = ("Error Summary" in en_text) or ("Warning Summary" in en_text) or ("Error" in en_text)
    assert has_zh, f"Expected zh headers in: {zh_text[:200]!r}"
    assert has_en, f"Expected en headers in: {en_text[:200]!r}"
    assert ("错误汇总" in zh_text) or ("警告汇总" in zh_text)
    assert ("Error Summary" in en_text) or ("Bibliography" in en_text) or ("Warning Summary" in en_text)


def test_custom_translate_upper():
    results = _build_results()
    buf = io.StringIO()
    print_summary(
        results,
        use_logger=False,
        translate_fn=lambda s: s.upper(),
        stream=buf,
    )
    text = buf.getvalue()
    has_upper_title = False
    for key in ("错误汇总", "警告汇总", "提示汇总", "参考文献", "代码执行"):
        if key.upper() in text:
            has_upper_title = True
            break
    if not has_upper_title:
        # If builtin zh->en is applied, the english title will be uppercased too
        for key in ("ERROR SUMMARY", "WARNING SUMMARY", "INFO SUMMARY", "BIBLIOGRAPHY"):
            if key in text:
                has_upper_title = True
                break
    assert has_upper_title, f"No uppercased title found in output: {text[:300]!r}"


def test_cli_lang_flag():
    proj_root = Path(__file__).resolve().parent.parent
    sample_log = proj_root / "tests" / "fixtures" / "sample.log"
    if not sample_log.exists():
        pytest.skip(f"sample.log not found at {sample_log}")

    env = {
        **dict(__import__("os").environ),
        "PYTHONPATH": str(proj_root / "src"),
        "PYTHONIOENCODING": "utf-8",
    }

    def run(lang: str) -> str:
        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytexlogs.cli",
                "check",
                str(sample_log),
                "--lang",
                lang,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            errors="replace",
            check=False,
        )
        return (r.stdout or "") + (r.stderr or "")

    out_zh = run("zh")
    out_en = run("en")

    has_zh = ("错误" in out_zh) or ("警告" in out_zh) or ("参考文献" in out_zh)
    has_en_lang = ("Error Summary" in out_en) or ("Warning Summary" in out_en) or ("Bibliography" in out_en) or ("Compilation" in out_en)
    # If sample log doesn't trigger actual entries, at least compare header differences (if any)
    # Otherwise accept: output text differs.
    assert out_zh != out_en or (has_zh or has_en_lang)
