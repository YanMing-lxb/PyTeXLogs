"""CJK 文档缺少字体时的缺字形警告聚合与提示。"""

from pytexlogs import LatexLogParser
from pytexlogs.hints import hint_for_text


def _log_with_missing_chars(lines: list[str]) -> str:
    body = "\n".join(lines)
    return f"This is pdfTeX, Version 3.141592653-2.6-1.40.25\n(./main.tex\n{body}\n)\nTranscript written on main.log.\n"


def test_cjk_missing_characters_are_aggregated_by_file_and_font() -> None:
    lines = [f"Missing character: There is no {char} in font cmr10!" for char in "中文测试内容" * 100]

    result = LatexLogParser(root_file="main.tex", quiet=True).parse(_log_with_missing_chars(lines))

    assert len(result.warnings) == 1
    warning = result.warnings[0]
    assert warning.file == "main.tex"
    assert warning.text.startswith("Missing character: There is no 中 in font cmr10!")
    assert "600 occurrences" in warning.text
    assert "6 distinct glyphs" in warning.text
    assert "中, 文, 测, 试, 内, 容" in warning.text


def test_single_missing_character_keeps_original_text() -> None:
    result = LatexLogParser(root_file="main.tex", quiet=True).parse(
        _log_with_missing_chars(["Missing character: There is no α in font cmr10!"])
    )

    assert len(result.warnings) == 1
    assert result.warnings[0].text == "Missing character: There is no α in font cmr10!"


def test_missing_characters_for_different_fonts_stay_separate() -> None:
    lines = [
        "Missing character: There is no 中 in font cmr10!",
        "Missing character: There is no 文 in font cmr10!",
        "Missing character: There is no 中 in font NotoSansCJK!",
    ]

    result = LatexLogParser(root_file="main.tex", quiet=True).parse(_log_with_missing_chars(lines))

    assert len(result.warnings) == 2
    assert all("main.tex" == warning.file for warning in result.warnings)
    assert any("cmr10" in warning.text and "2 occurrences" in warning.text for warning in result.warnings)
    assert any("NotoSansCJK" in warning.text for warning in result.warnings)


def test_cjk_missing_glyph_hint_points_to_ctex_and_xelatex() -> None:
    hint = hint_for_text("Missing character: There is no 中 in font cmr10!")

    assert hint is not None
    assert hint.kind == "missing_glyph"
    assert "ctex" in hint.text
    assert "XeLaTeX" in hint.text
    assert "\\usepackage{ctex}" in hint.commands
