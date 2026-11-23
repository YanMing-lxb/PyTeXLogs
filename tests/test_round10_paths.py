"""第 10 轮：数据库路径锚定与既有解析契约回归。"""

from __future__ import annotations

from pathlib import Path

from pytexlogs import run_pipeline
from pytexlogs.parsers.biber import BiberParser
from pytexlogs.parsers.bibtex import BibtexParser
from pytexlogs.parsers.path_utils import (
    resolve_relative_path,
    resolve_relative_path_from,
)

_BIBER_BLG = (
    "[0] Biber.pm:1002> INFO - Found BibTeX data source 'refs.bib'\n"
    "[1] Biber.pm:1003> WARN - I didn't find a database entry for 'missing'\n"
)


def _write_biber_case(auxdir: Path) -> Path:
    (auxdir / "main.blg").write_text(_BIBER_BLG, encoding="utf-8")
    (auxdir / "refs.bib").write_text("@book{k, title={T}}", encoding="utf-8")
    (auxdir / "main.log").write_text("This is pdfTeX, Version 3.141592653\n", encoding="utf-8")
    return auxdir / "refs.bib"


def test_resolve_relative_path_contract_unchanged(tmp_path: Path) -> None:
    root = str(tmp_path / "main.tex")
    assert resolve_relative_path("", root) == root
    assert resolve_relative_path("refs.bib", root).endswith("refs.bib")


def test_resolve_relative_path_from_prefers_source_hint(tmp_path: Path) -> None:
    aux = tmp_path / "aux"
    aux.mkdir()
    bib = aux / "refs.bib"
    bib.write_text("@book{k, title={T}}", encoding="utf-8")

    resolved = resolve_relative_path_from("refs.bib", "main.tex", source_hint=str(aux / "main.blg"))

    assert resolved == str(bib.resolve())


def test_pipeline_biber_database_file_anchored_to_auxdir(tmp_path: Path) -> None:
    """auxdir 里的 refs.bib 不能被解析成进程 CWD 下的同名文件。"""
    bib = _write_biber_case(tmp_path)

    report = run_pipeline("main", tmp_path, print_terminal=False)

    biber_results = [tr for tr in report.tool_results if tr.tool_name == "biber"]
    assert biber_results
    entries = biber_results[0].entries
    assert entries
    expected = str(bib.resolve())
    assert {entry.file for entry in entries} == {expected}
    assert Path(entries[0].file).exists()


def test_biber_parse_file_anchors_to_log_directory(tmp_path: Path) -> None:
    bib = _write_biber_case(tmp_path)

    parsed = BiberParser().parse_file(tmp_path / "main.blg", root_file=None)

    assert parsed.entries
    assert parsed.entries[0].file == str(bib.resolve())


def test_bibtex_parse_file_anchors_to_log_directory(tmp_path: Path) -> None:
    (tmp_path / "main.blg").write_text(
        "This is BibTeX, Version 0.99d\nDatabase file #1: refs.bib\n",
        encoding="utf-8",
    )
    bib = tmp_path / "refs.bib"
    bib.write_text("@book{k, title={T}}", encoding="utf-8")

    parsed = BibtexParser().parse_file(tmp_path / "main.blg", root_file=None)

    assert parsed.stats["database_files"] == [str(bib.resolve())]
