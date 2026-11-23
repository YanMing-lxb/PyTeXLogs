"""第 7 轮：BibTeX 警告去重与多行帧二次记录回归（任务 11）。"""

from pytexlogs.parsers.bibtex import BibtexParser

#: 一条多行 ``Warning--`` 帧 + 一条单行 ``Warning--``。
_MIXED_WARNINGS = (
    "Warning--Duplicate entry key: smith2020\n"
    "--line 12 of file refs.bib\n"
    "Warning--empty author in entry foo in file refs.bib\n"
)

#: 同一单行警告重复两次，必须按稳定键去重成一条。
_DUP_SINGLE_WARNING = (
    "Warning--empty author in entry foo in file refs.bib\nWarning--empty author in entry foo in file refs.bib\n"
)

#: 同一单行错误帧重复两次。
_DUP_ERROR = (
    "I'm skipping whatever remains of this entry.\n"
    "---line 12 of file refs.bib\n"
    "I'm skipping whatever remains of this entry.\n"
    "---line 12 of file refs.bib\n"
)


def test_multiline_warning_not_recorded_twice() -> None:
    """多行 ``Warning--`` 不得再被单行路径二次记录：2 条真实警告 → 2 条目、计数 2。"""
    parsed = BibtexParser(root_file="main.tex").parse(_MIXED_WARNINGS)
    warnings = [e for e in parsed.entries if e.level.value == "warning"]
    assert len(parsed.entries) == 2
    assert len(warnings) == 2
    assert parsed.stats["warnings_count"] == 2


def test_single_line_warning_dedup_by_stable_key() -> None:
    """WARNING 按 ``(file, line, normalized text)`` 去重：重复单行只留一条。"""
    parsed = BibtexParser(root_file="main.tex").parse(_DUP_SINGLE_WARNING)
    assert len(parsed.entries) == 1
    assert parsed.stats["warnings_count"] == 1


def test_single_line_error_dedup() -> None:
    """重复单行错误帧去重成一条 ERROR。"""
    parsed = BibtexParser(root_file="main.tex").parse(_DUP_ERROR)
    errors = [e for e in parsed.entries if e.level.value == "error"]
    assert len(parsed.entries) == 1
    assert len(errors) == 1
