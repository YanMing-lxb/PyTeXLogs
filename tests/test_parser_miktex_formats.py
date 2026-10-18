"""MiKTeX 与 TeX Live 输出格式差异的回归测试。

背景：MiKTeX 的 makeindex / glossaries 不写 ``##`` 前缀，而是
``....done (95 entries accepted, 0 rejected)``；错误用 ``** Input style error
(file = ..., line = N):`` + ``   -- 说明`` 两行报。只有 TeX Live 写法的
解析器在 MiKTeX 上会把全部统计与 style error 静默丢弃（entries=0）。
"""

from pytexlogs.parsers.bibtex import BibtexParser
from pytexlogs.parsers.glossaries import GlossariesParser
from pytexlogs.parsers.makeindex import MakeindexParser
from pytexlogs.parsers.nomencl import NomenclParser

TEXLIVE_ILG = """\
This is makeindex version 2.15 [TeX Live 2024].
Scanning style file /tmp/nomencl.ist...
## 12 lines read
## 95 entries accepted, 0 rejected
Generating output file main.nls...done (103 lines written, 0 warnings).
Output written in main.nls.
"""

#: 摘录自 MiKTeX 26.5 + nomencl.ist 的真实 .ilg（3 个 Unknown specifier）。
MIKTEX_ILG = """\
This is makeindex, version 2.18 [MiKTeX 26.5 Portable].
Scanning style file C:/miktex/makeindex/nomencl/nomencl.ist........
** Input style error (file = C:/miktex/makeindex/nomencl/nomencl.ist, line = 36):
   -- Unknown specifier lethead_prefix.
** Input style error (file = C:/miktex/makeindex/nomencl/nomencl.ist, line = 37):
   -- Unknown specifier lethead_suffix.
** Input style error (file = C:/miktex/makeindex/nomencl/nomencl.ist, line = 38):
   -- Unknown specifier lethead_flag.
....done (12 attributes redefined, 3 ignored).
Scanning input file main.nlo....done (95 entries accepted, 0 rejected).
Sorting entries....done (607 comparisons).
Generating output file main.nls....done (103 lines written, 0 warnings).
Output written in main.nls.
Transcript written in main.ilg.
"""

TEXLIVE_BLG = "This is BibTeX 0.99d\n39 entries, 2 warnings\n"
MIKTEX_BLG = (
    "This is BibTeX, Version 0.99e\r\n"
    "The top-level auxiliary file: main.aux\r\n"
    "The style file: elsarticle-num.bst\r\n"
    "Database file #1: References.bib\r\n"
    "You've used 39 entries,\r\n"
    "             2952 wiz_defined-function locations,\r\n"
    "             warning$ -- 0\r\n"
)


# ---------------------------------------------------------------- makeindex

def test_makeindex_texlive_format():
    """TeX Live 的 ## 前缀统计必须继续工作（不可回归）。"""
    r = MakeindexParser(root_file="main").parse(TEXLIVE_ILG, root_file="main")
    assert r.stats["entries_accepted"] == 95
    assert r.stats["entries_rejected"] == 0
    assert len(r.entries) == 0


def test_makeindex_miktex_entries_stat():
    """MiKTeX 的 ``done (95 entries accepted, 0 rejected)`` 必须被识别。"""
    r = MakeindexParser(root_file="main").parse(MIKTEX_ILG, root_file="main")
    assert r.stats["entries_accepted"] == 95
    assert r.stats["entries_rejected"] == 0
    assert r.stats["redefined_count"] == 12
    assert r.stats["ignored_count"] == 3


def test_makeindex_miktex_style_error_two_line_pair():
    """``** Input style error (...):`` 标题行必须与 ``   -- 说明`` 续行合并成一条。"""
    r = MakeindexParser(root_file="main").parse(MIKTEX_ILG, root_file="main")
    assert r.stats["style_errors_count"] == 3
    assert len(r.errors) == 3
    first = r.errors[0]
    assert first.line == 36
    assert "Input style error" in first.text
    assert "Unknown specifier lethead_prefix" in first.text
    assert "nomencl.ist" in first.file


def test_makeindex_miktex_style_error_without_continuation():
    """标题后紧跟下一个标题（无续行）时不能吞掉后一条。"""
    text = (
        "** Input style error (file = a.ist, line = 10):\n"
        "** Input style error (file = a.ist, line = 11):\n"
    )
    r = MakeindexParser(root_file="main").parse(text, root_file="main")
    assert r.stats["style_errors_count"] == 2
    assert [e.line for e in r.errors] == [10, 11]


# ------------------------------------------------------------------ nomencl

def test_nomencl_miktex_entries_and_style_errors():
    r = NomenclParser(root_file="main").parse(MIKTEX_ILG, root_file="main")
    assert r.stats["nomenclature_entries"] == 95
    assert r.stats["style_errors_count"] == 3
    assert len(r.entries) == 3

def test_nomencl_texlive_format():
    r = NomenclParser(root_file="main").parse(TEXLIVE_ILG, root_file="main")
    assert r.stats["nomenclature_entries"] == 95


# --------------------------------------------------------------- glossaries

def test_glossaries_miktex_style_errors():
    text = MIKTEX_ILG.replace("main.nlo", "main.glo").replace("main.nls", "main.gls")
    r = GlossariesParser(root_file="main").parse(text, root_file="main")
    assert len(r.entries) == 3
    assert all(e.level.value == "error" for e in r.entries)
    assert r.entries[0].line == 36


def test_glossaries_miktex_entries_stat():
    text = "Scanning input file main.glo....done (42 entries accepted, 2 rejected).\n"
    r = GlossariesParser(root_file="main").parse(text, root_file="main")
    stats = r.stats
    # .glo 是主术语表，统计落在 main_entries
    assert stats["main_entries"] == 42


# ------------------------------------------------------------------ bibtex

def test_bibtex_texlive_single_line_stat():
    """TeX Live 单行 ``39 entries, 2 warnings``：数字前无空白也算。"""
    r = BibtexParser(root_file="main").parse(TEXLIVE_BLG, root_file="main")
    assert r.stats["entries_processed"] == 39
    assert r.stats["warnings_count"] == 2


def test_bibtex_miktex_used_entries_stat():
    """MiKTeX 的 ``You've used 39 entries,`` 带缩进、行尾逗号。"""
    r = BibtexParser(root_file="main").parse(MIKTEX_BLG, root_file="main")
    assert r.stats["entries_processed"] == 39
    assert r.stats["database_files"]


if __name__ == "__main__":
    for name, fn in sorted(list(globals().items())):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  OK  {name}")
    print("\nMiKTeX / TeX Live 格式差异回归全部通过！")
