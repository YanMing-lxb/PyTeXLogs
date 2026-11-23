"""LaTeX 解析器生命周期回归。

覆盖第 1 轮 P0 修复：
- flush 后重置缓冲，连续条目不得二次入队；
- 文件栈行不得被吞进警告续行，嵌套文件归属正确；
- 含空格路径的文件栈归属完整路径；
- 截断（无尾 ``!/?``）的缺字形缓冲在 EOF 兜底 flush；
- 直接传文本的调用边界去 BOM / CRLF；
- 缺 ``.bbl`` 规则允许点号 jobname 与尾随标点。
"""

import pytest

from pytexlogs import LatexLogParser, parse_log_text
from pytexlogs.hints import hint_for_text

# --- 1. 连续条目不得二次 flush ---------------------------------------------


def test_consecutive_warnings_not_double_flushed() -> None:
    text = "Package foo Info: first.\nPackage foo Info: second.\n"
    parsed = LatexLogParser(root_file="main.tex").parse(text)

    assert len(parsed.entries) == 2
    assert parsed.entries[0].text == "Package foo Info: first."
    assert parsed.entries[1].text == "Package foo Info: second."


# --- 2. 文件栈行不吞续行；嵌套文件归属 --------------------------------------


def test_file_stack_open_attributes_warning_to_nested_file() -> None:
    text = "(./chapter.tex\nLaTeX Warning: Something odd on input line 3.\n)\n"
    parsed = LatexLogParser(root_file="main.tex").parse(text)

    assert len(parsed.entries) == 1
    entry = parsed.entries[0]
    assert entry.file == "chapter.tex"
    assert "(./" not in entry.text


def test_stack_line_after_warning_not_appended_to_text() -> None:
    text = "LaTeX Warning: Something odd on input line 3.\n(./appendix.tex\n"
    parsed = LatexLogParser(root_file="main.tex").parse(text)

    assert len(parsed.entries) == 1
    entry = parsed.entries[0]
    assert entry.text == "LaTeX Warning: Something odd."
    assert "(./" not in entry.text


def test_biblatex_continuation_prefix_not_treated_as_stack() -> None:
    """``(biblatex) main`` 是警告续行前缀，不是文件栈项：必须追加到上一条警告。"""
    text = "Package biblatex Warning: Please (re)run Biber on the file:\n(biblatex) main\n"
    parsed = LatexLogParser(root_file="main.tex").parse(text)

    assert len(parsed.entries) == 1
    entry = parsed.entries[0]
    assert "(biblatex) main" in entry.text
    assert entry.file == "main.tex"


# --- 3. 含空格路径的文件栈归属 ---------------------------------------------


def test_file_stack_path_with_spaces_attributed_whole() -> None:
    text = (
        r"(C:\Program Files\miktex\tex\latex\biblatex\biblatex.sty" + "\n"
        "LaTeX Warning: Label(s) may have changed. Rerun to get cross-references right.\n"
        ")\n"
    )
    parsed = LatexLogParser(root_file="main.tex").parse(text)

    assert len(parsed.entries) == 1
    entry = parsed.entries[0]
    assert entry.file.endswith("biblatex.sty")
    assert "Program Files" in entry.file
    assert entry.text.rstrip() == ("LaTeX Warning: Label(s) may have changed. Rerun to get cross-references right.")


# --- 4. 截断缺字形缓冲 EOF 兜底 flush ---------------------------------------


def test_truncated_missing_glyph_flushed_at_eof() -> None:
    text = 'Missing character: There is no 中 (U+4E2D) in font "name:Latin Modern Roman:mode=node;lang'
    parsed = LatexLogParser(root_file="main.tex").parse(text)

    glyph = [e for e in parsed.entries if "Missing character" in e.text]
    assert len(glyph) == 1
    assert "中" in glyph[0].text
    assert "4E2D" in glyph[0].text
    hint = hint_for_text(glyph[0].text, tool_name="lualatex")
    assert hint is not None and hint.rule_id == "missing_glyph"


# --- 5. 直接传文本：去 BOM / CRLF -------------------------------------------


def test_parse_text_strips_bom_and_crlf() -> None:
    parsed = parse_log_text("\ufeffLaTeX Warning: Marginpar on page 1 moved.\r\n")

    assert len(parsed.entries) == 1
    assert parsed.entries[0].text == "LaTeX Warning: Marginpar on page 1 moved."


# --- 6. 缺 .bbl：点号 jobname 与尾随标点 ------------------------------------


def test_missing_bbl_dotted_jobname_parser_entry() -> None:
    parsed = LatexLogParser(root_file="main.tex").parse("No file paper.v1.bbl.\n")

    bbl = [e for e in parsed.entries if "paper.v1.bbl" in e.text]
    assert len(bbl) == 1


def test_missing_bbl_dotted_jobname_hint() -> None:
    hint = hint_for_text("No file paper.v1.bbl.", tool_name="pdflatex")

    assert hint is not None and hint.rule_id == "missing_bbl"
    assert "paper.v1" in hint.text


def test_missing_bbl_trailing_semicolon() -> None:
    parsed = LatexLogParser(root_file="main.tex").parse("No file paper.v1.bbl;\n")

    bbl = [e for e in parsed.entries if "paper.v1.bbl" in e.text]
    assert len(bbl) == 1


# --- B. missing_glyph CJK 分支命令 tool-aware --------------------------------


_SPEC_CJK_GLYPH = (
    'Missing character: There is no 中 (U+4E2D) in font "name:Latin Modern Roman:mode=node;script=latn;language=dflt;"!'
)


@pytest.mark.parametrize("tool", ["pdflatex", "xelatex", "lualatex"])
def test_missing_glyph_commands_tool_scoped(tool: str) -> None:
    hint = hint_for_text(_SPEC_CJK_GLYPH, tool_name=tool, root_file="main.tex")

    assert hint is not None and hint.rule_id == "missing_glyph"
    joined = " ".join(hint.commands)
    if tool == "xelatex":
        assert "lualatex" not in joined
    if tool == "lualatex":
        assert "xelatex" not in joined
    assert "<engine>" not in joined
    assert "<主文件>" not in joined


@pytest.mark.parametrize("tool", ["pdflatex", "xelatex", "lualatex"])
def test_missing_glyph_english_commands_have_no_cjk_or_slot(tool: str) -> None:
    hint = hint_for_text(_SPEC_CJK_GLYPH, tool_name=tool, root_file="main.tex", language="en")

    assert hint is not None
    joined_en = " ".join(hint.commands)
    # 英文命令不得夹带中文，不得残留未替换占位符。
    assert not any("一" <= c <= "鿿" for c in joined_en)
    assert "<engine>" not in joined_en
    assert "<主文件>" not in joined_en
    assert "<jobname>" not in joined_en
