"""提示词双语对齐：每条规则都必须给出英文说明，避免 --lang en 里冒出中文。"""

import re

import pytest

from pytexlogs.hints import _LOG_HINT_EN, collect_hints, hint_for_text

_CJK = re.compile(r"[\u4e00-\u9fff]")

#: 每条规则一个代表文本（覆盖 hints.py 里的全部 if 分支与内建表）
CORPUS = [
    ("File `booktabs.sty' not found.", "missing_package"),
    ("! LaTeX Error: File `fig.png' not found.", "missing_graphic"),
    ("Font `NotoSans' not found", "missing_font"),
    ("Unicode character μ (U+03BC) not set up for use with LaTeX.", "unicode"),
    ("Missing character: There is no α in font cmr10!", "missing_glyph"),
    ("LaTeX Warning: Citation `knuth84' on page 1 undefined on input line 9.", "undefined_citation"),
    ("LaTeX Warning: Reference `sec:intro' on page 1 undefined on input line 3.", "undefined_reference"),
    ("! LaTeX Error: Environment equationn undefined.", "undefined_environment"),
    ("I couldn't open database file refs.bib", "missing_bib"),
    ("! Too many unprocessed floats.", "float_overflow"),
    ("! TeX capacity exceeded, sorry [main memory size=3000000].", "capacity"),
    ("! No pages of output.", "no_output"),
    ("Runaway argument?", "runaway"),
    ("! Missing $ inserted.", "math_mode"),
    ("! Emergency stop.", "fatal"),
    ("! Undefined control sequence.\nl.5 ... \\badcmd\n", "undefined_control"),
    ("! LaTeX Error: \\begin{document} ended by \\end{itemize}.", "end_mismatch"),
    ("! Package inputenc Error: Invalid UTF-8 byte sequence.", "invalid_utf8"),
    ("! Extra alignment tab has been changed to \\cr.", "alignment_tab"),
    ("! Missing number, treated as zero.", "missing_number"),
    ("! LaTeX Error: Something's wrong--perhaps a missing \\item.", "missing_item"),
    ("! Package hyperref Error: Wrong driver.", "package_error"),
    ("Overfull \\hbox (12.0pt too wide) in paragraph at lines 1--2", "log_hint"),
]


@pytest.mark.parametrize(("text", "expected_kind"), CORPUS)
def test_every_rule_has_english_text(text: str, expected_kind: str) -> None:
    zh = hint_for_text(text)
    assert zh is not None, f"规则未命中：{text!r}"
    assert zh.kind == expected_kind, f"{text!r} 命中 {zh.kind}，期望 {expected_kind}"
    assert _CJK.search(zh.text), "中文说明里没有中文，检查规则是否漏写"

    en = hint_for_text(text, language="en")
    assert en is not None
    assert not _CJK.search(en.text), f"--lang en 仍返回中文：{en.text!r}"


def test_legacy_hint_table_is_translated() -> None:
    """hints 内建表（LATEX/BIBTEX/BIBER）的每个键都要有英文说明。"""
    missing = [key for key in collect_hints() if not _LOG_HINT_EN.get(key)]
    assert not missing, f"缺少英文说明的键: {missing}"


def test_context_substitution_applies_to_both_languages() -> None:
    """``<jobname>`` / ``<主文件>`` 在中文与英文文本里都要被替换。"""
    zh = hint_for_text("Citation `x' undefined", jobname="main")
    assert zh is not None and "biber main" in zh.commands[0]

    en = hint_for_text("Reference `x' undefined", root_file="paper.tex", language="en")
    assert en is not None
    assert "paper.tex" in en.commands[0]
    assert "<主文件>" not in en.text
