"""LaTeX 错误帧与警告文本的回归测试。"""

from pathlib import Path

from pytexlogs import LatexLogParser, parse_log_text
from pytexlogs.hints import hint_for_entry

_SAMPLE = Path(__file__).parent / "fixtures" / "sample.log"


def test_bang_error_frame_sets_line_and_error_pos_without_prefix() -> None:
    parsed = LatexLogParser(root_file="sample.tex", quiet=True).parse_file(_SAMPLE)
    first = parsed.errors[0]

    assert first.line == 5
    assert first.text == "Undefined control sequence."
    assert first.error_pos_text == r"\foobar"

    hint = hint_for_entry(first, jobname="sample")
    assert hint is not None
    assert any("foobar" in command for command in hint.commands)


def test_fatal_bang_error_has_no_leading_colon_or_blank_tail() -> None:
    parsed = LatexLogParser(root_file="sample.tex", quiet=True).parse_file(_SAMPLE)

    fatal = parsed.errors[-1]
    assert fatal.text == "==> Fatal error occurred, no output PDF file produced!"
    assert not fatal.text.startswith(":")
    assert not fatal.text.endswith("\n")


def test_latex_warning_suffix_is_not_duplicated() -> None:
    period = parse_log_text("LaTeX Warning: Something odd on input line 3.")
    question = parse_log_text("LaTeX Warning: Something odd on input line 3?")

    assert period.entries[0].text == "LaTeX Warning: Something odd."
    assert question.entries[0].text == "LaTeX Warning: Something odd?"
