"""第 7 轮（round7 任务 13）：LaTeX 专属规则的工具作用域白名单。

17 条 LaTeX 专属规则在 biber / bibtex / makeindex 等后端工具名下必须返回
``None``，不得套用 LaTeX 专属建议；在 pdflatex / xelatex / lualatex 下仍正常命中。
``missing_bib`` 是跨文献链路规则，允许 latex/biber/bibtex，在 makeindex/xindy 下不命中。
"""

import pytest

from pytexlogs.hints import hint_for_text

#: (规则 id, 触发文本) —— 与 hints.py 规则表一一对应。
LATEX_ONLY_CASES: list[tuple[str, str]] = [
    ("missing_package", "File `booktabs.sty' not found."),
    ("missing_file", "! LaTeX Error: File `fig.png' not found."),
    (
        "font_not_loadable",
        "! Font \\foo=NoSuchFont at 10.0pt not loadable: Metric (TFM) file not found.",
    ),
    (
        "tfm_font_missing",
        "! Font T1/cmr/m/n/10=ecrm1000 at 10pt not loadable: Metric (TFM) file ecrm1000.tfm not found.",
    ),
    ("missing_font", "Font `NotoSans' not found"),
    ("fontset_unavailable", "CTeX fontset 'fandol' is unavailable in current mode."),
    ("unicode", "Unicode character μ (U+03BC) not set up for use with LaTeX."),
    (
        "cjk_missing_glyph",
        "CJKfamily 'song' ([FandolSong-Regular]) does not contain glyph '中' ( U + 4E2D )",
    ),
    ("missing_glyph", "Missing character: There is no α in font cmr10!"),
    ("missing_bbl", "No file main.bbl."),
    (
        "undefined_citation",
        "LaTeX Warning: Citation `knuth84' on page 1 undefined on input line 9.",
    ),
    (
        "undefined_reference",
        "LaTeX Warning: Reference `sec:intro' on page 1 undefined on input line 3.",
    ),
    ("capacity", "! TeX capacity exceeded, sorry [main memory size=3000000]."),
    ("runaway", "Runaway argument?"),
    ("fatal", "! Emergency stop."),
    ("missing_begin_document", "! LaTeX Error: Missing \\begin{document}."),
    (
        "fontspec_font_not_found",
        '! Package fontspec Error: The font "NoSuchFontFamilyXYZ" cannot be found.',
    ),
]

BACKEND_TOOLS = ("biber", "bibtex", "makeindex")
ENGINE_TOOLS = ("pdflatex", "xelatex", "lualatex")


@pytest.mark.parametrize(("rule_id", "text"), LATEX_ONLY_CASES)
@pytest.mark.parametrize("tool", BACKEND_TOOLS)
def test_latex_only_rules_skip_backend_tools(rule_id: str, text: str, tool: str) -> None:
    hint = hint_for_text(text, tool_name=tool)
    assert hint is None, f"{rule_id} 在 {tool} 后端日志下误触发"


@pytest.mark.parametrize(("rule_id", "text"), LATEX_ONLY_CASES)
@pytest.mark.parametrize("tool", ENGINE_TOOLS)
def test_latex_only_rules_hit_latex_engines(rule_id: str, text: str, tool: str) -> None:
    hint = hint_for_text(text, tool_name=tool)
    assert hint is not None, f"{rule_id} 在 {tool} 下未命中"
    assert hint.rule_id == rule_id, f"{tool} 下命中 {hint.rule_id}，期望 {rule_id}"


@pytest.mark.parametrize("tool", ("latex", "pdflatex", "biber", "bibtex"))
def test_missing_bib_hits_bibliography_tools(tool: str) -> None:
    hint = hint_for_text("I couldn't open database file refs.bib", tool_name=tool)
    assert hint is not None
    assert hint.rule_id == "missing_bib"


@pytest.mark.parametrize("tool", ("makeindex", "xindy", "minted"))
def test_missing_bib_skips_non_bibliography_tools(tool: str) -> None:
    hint = hint_for_text("I couldn't open database file refs.bib", tool_name=tool)
    assert hint is None
