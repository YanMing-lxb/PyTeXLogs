"""第 10 轮解析器修复回归：文件栈弹栈、output 坏盒子页号、文案中性化。

覆盖四类行为：
- 同一行/连续行的多个 ``)`` 必须逐个弹栈，结束后栈为空，后续错误归属主文件；
- ``has occurred while \\output is active (7)`` 的括号是页号，不能冒充行号；
- 删除 ``bib_empty_re`` 死代码后，空 thebibliography 仍输出 WARNING；
- 未定义引用文案改为语言中性的 ``Undefined reference/citation `key```，
  hints 同时识别新旧两种文案。
"""

from pytexlogs import LatexLogParser
from pytexlogs.core.models import LogLevel
from pytexlogs.hints import hint_for_text
from pytexlogs.parsers import latex as latex_mod

# --- 1. 文件栈弹栈 -----------------------------------------------------------


def test_stack_pops_all_files_closed_on_following_line() -> None:
    """``(./b.tex) )`` 中的第二个 ``)`` 是回退弹栈，不能残留上一行的 a.tex。"""
    parser = LatexLogParser(root_file="main.tex")
    parsed = parser.parse("(./a.tex\n(./b.tex) )\n! Undefined control sequence.\n")

    assert parser.file_stack == []
    errors = [e for e in parsed.entries if e.level == LogLevel.ERROR]
    assert len(errors) == 1
    assert errors[0].file == "main.tex"


def test_stack_pops_nested_files_opened_and_closed_on_one_line() -> None:
    """同一行的 ``(./a.tex) (./b.tex))`` 有两个本行开括号，两个 ``)`` 必须都弹。"""
    parser = LatexLogParser(root_file="main.tex")
    parsed = parser.parse("(./main.tex (./a.tex) (./b.tex))\n! Undefined control sequence.\n")

    assert parser.file_stack == []
    errors = [e for e in parsed.entries if e.level == LogLevel.ERROR]
    assert len(errors) == 1
    assert errors[0].file == "main.tex"


def test_plain_text_stray_close_does_not_pop_stack() -> None:
    """普通文本里的孤立 ``)``（前缀无 ``(`` 或含非路径 token）不得弹栈。"""
    parser = LatexLogParser(root_file="main.tex")
    parser.parse("(./chapter.tex\nSome text with ) closing\nLaTeX Warning: something )\n")

    assert parser.file_stack == ["./chapter.tex"]


# --- 2. output-active 坏盒子的页号不是行号 ----------------------------------


def test_output_active_overfull_box_uses_page_not_line() -> None:
    parsed = LatexLogParser(root_file="main.tex").parse(
        "Overfull \\hbox (12.0pt too wide) has occurred while \\output is active (7)\n"
    )

    boxes = [e for e in parsed.entries if e.level == LogLevel.TYPESET]
    assert len(boxes) == 1
    assert boxes[0].line == 1
    assert "(7)" in boxes[0].text
    assert parsed.stats["overfull_boxes"] == 1


# --- 3. 删除 bib_empty_re 死代码 --------------------------------------------


def test_empty_bibliography_still_reported_as_warning() -> None:
    parsed = LatexLogParser(root_file="main.tex").parse(
        "LaTeX Warning: Empty `thebibliography' environment on input line 5.\n"
    )

    warnings = [e for e in parsed.entries if e.level == LogLevel.WARNING]
    assert len(warnings) == 1
    assert "thebibliography" in warnings[0].text


def test_bib_empty_re_removed_from_public_api() -> None:
    assert "bib_empty_re" not in latex_mod.__all__
    assert not hasattr(latex_mod, "bib_empty_re")


# --- 4. 未定义引用文案语言中性 ----------------------------------------------


def test_undefined_reference_text_is_language_neutral() -> None:
    parsed = LatexLogParser(root_file="main.tex").parse(
        "LaTeX Warning: Reference `sec:intro' on page 1 undefined on input line 3.\n"
    )

    assert len(parsed.entries) == 1
    entry = parsed.entries[0]
    assert entry.text == "Undefined reference `sec:intro`"
    assert entry.error_pos_text == "sec:intro"
    assert parsed.stats["undefined_refs"] == 1


def test_hints_accept_language_neutral_undefined_text() -> None:
    hint = hint_for_text("Undefined citation `k`", jobname="main")
    assert hint is not None
    assert hint.rule_id == "undefined_citation"

    en_hint = hint_for_text("Undefined citation `k`", jobname="main", language="en")
    assert en_hint is not None
    assert en_hint.rule_id == "undefined_citation"
    assert "Citation key `k` is undefined" in en_hint.text

    ref_hint = hint_for_text("Undefined reference `sec:intro`", jobname="main")
    assert ref_hint is not None
    assert ref_hint.rule_id == "undefined_reference"
