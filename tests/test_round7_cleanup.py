"""第 5 轮清理与健壮性回归。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pytexlogs import ProjectStateStore
from pytexlogs.core.report import dict_to_report, load_report
from pytexlogs.parsers import glossaries, xindy
from pytexlogs.parsers.biber import BiberParser
from pytexlogs.parsers.bibtex import BibtexParser
from pytexlogs.parsers.latex import LatexLogParser
from pytexlogs.parsers.path_utils import resolve_relative_path


def test_biblatex_continuation_standard_form_keeps_raw_line() -> None:
    """``(biblatex) main`` 是标准续行：保留原文，并提取 on input line。"""
    text = "Package biblatex Warning: Please (re)run Biber on the file:\n(biblatex) main on input line 12\n"
    parsed = LatexLogParser(root_file="main.tex").parse(text)

    assert len(parsed.entries) == 1
    entry = parsed.entries[0]
    assert "(biblatex) main on input line 12" in entry.text
    assert entry.line == 12


def test_xindy_patterns_are_shared_between_parsers() -> None:
    """Glossaries 的 xindy 分支与 XindyParser 必须共用同一扫描器。"""
    assert glossaries.scan_xindy is xindy.scan_xindy


def test_resolve_relative_path_keeps_filename_on_empty_root(tmp_path: Path) -> None:
    root = tmp_path / "main.tex"
    assert resolve_relative_path("", str(root)) == str(root)
    assert resolve_relative_path("refs.bib", str(root)).endswith("refs.bib")


def test_state_mutate_swallows_mutator_type_error(tmp_path: Path) -> None:
    """``_mutate`` 的承诺是任何异常不外抛，JSON/mutator 的 TypeError 也算。"""
    store = ProjectStateStore(tmp_path, "main")

    def boom(state: dict[str, object]) -> None:
        raise TypeError("mutator boom")

    assert store._mutate(boom) is False


def test_dict_to_report_rejects_non_object() -> None:
    with pytest.raises(TypeError, match="JSON object"):
        dict_to_report([])  # type: ignore[arg-type]


def test_load_report_rejects_json_array(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    path.write_text(json.dumps([{"schema_version": 1}]), encoding="utf-8")

    with pytest.raises(TypeError, match="JSON object"):
        load_report(path)


def test_biber_parser_accepts_crlf(tmp_path: Path) -> None:
    """捕获输出常带 CRLF；``INFO - Found BibTeX data source`` 不得因 `\\r` 失配。"""
    log = "INFO - Found BibTeX data source 'refs.bib'\r\nWARN - I didn't find a database entry for 'missing'\r\n"
    parsed = BiberParser(root_file=str(tmp_path / "main.tex")).parse(log)

    assert len(parsed.stats["database_files"]) == 1
    assert parsed.stats["database_files"][0].endswith("refs.bib")
    assert parsed.entries
    assert "\r" not in parsed.entries[0].text


def test_bibtex_parser_accepts_crlf(tmp_path: Path) -> None:
    log = 'Warning--I didn\'t find a database entry for "missing"\r\n--line 3 of file refs.bib\r\n'
    parsed = BibtexParser(root_file=str(tmp_path / "main.tex")).parse(log)

    assert len(parsed.entries) == 1
    assert parsed.stats["warnings_count"] == 1
    assert "\r" not in parsed.entries[0].text
