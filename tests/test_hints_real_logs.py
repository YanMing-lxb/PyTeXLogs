"""用 ``docs/hints-research/round1-real-logs.md`` 的真实日志片段回归规则表。

每条样本都来自本机/云主机真实编译输出（不是凭空构造的正则玩具串），断言
命中规则 id、kind 与关键提取值（命令名/宏包名/字体名/字符/子类型）。
"""

import pytest

from pytexlogs.hints import hint_for_text

#: (样本日志, rule_id, kind, 关键提取值必须出现在文案/命令里)
REAL_LOG_CASES = [
    # c17 Double subscript
    (
        "! Double subscript.\nl.3 $x_1_\n         2$",
        "double_script",
        "double_script",
        ("下标",),
    ),
    # c19 Option clash
    (
        "! LaTeX Error: Option clash for package graphicx.\n\nl.4 \\begin\n          {document}",
        "option_clash",
        "option_clash",
        ("graphicx",),
    ),
    # c05 Missing \begin{document}
    (
        "! LaTeX Error: Missing \\begin{document}.\n\nl.2 S\n     tray text before begin.",
        "missing_begin_document",
        "missing_begin_document",
        ("\\begin{document}",),
    ),
    # e09/d06 多余右花括号
    (
        "! Too many }'s.\nl.3 \\section{a}}\nYou've closed more groups than you opened.",
        "extra_close_brace",
        "extra_close_brace",
        ("花括号",),
    ),
    # e11 \left 缺 \right
    (
        "! Missing \\right. inserted.\nl.3 $\\left[ x $",
        "missing_right",
        "missing_delimiter",
        ("\\right",),
    ),
    # e06 数学环境分隔符
    (
        "! Display math should end with $$.\nl.3 \\[ a $\n         b \\]\n"
        "! LaTeX Error: Bad math environment delimiter.",
        "bad_math_delimiter",
        "math_delimiter",
        ("定界符",),
    ),
    # e10 表格外 \hline
    (
        "! Misplaced \\noalign.\n\\hline ->\\noalign\nl.3 \\hline",
        "misplaced_noalign",
        "misplaced_noalign",
        ("\\hline",),
    ),
    # d02 非法长度单位
    (
        "! Illegal unit of measure (pt inserted).\n<to be read again>\n                   z\nl.3 \\vspace{2zz}",
        "illegal_unit",
        "illegal_unit",
        ("z",),
    ),
    # d05 命令重复定义
    (
        "! LaTeX Error: Command \\foo already defined.\n"
        "               Or name \\end... illegal, see p.192 of the manual.",
        "command_already_defined",
        "command_conflict",
        ("\\foo",),
    ),
    # d12 段落开头 \newline
    (
        "! LaTeX Error: There's no line here to end.",
        "no_line_to_end",
        "no_line_to_end",
        ("\\newline",),
    ),
    # e05 hyperref PDF 字符串
    (
        "Package hyperref Warning: Token not allowed in a PDF string (Unicode):\n"
        "(hyperref)                removing `math shift' on input line 4.\n"
        "(hyperref)                removing `superscript' on input line 4.",
        "hyperref_pdf_string",
        "hyperref_pdf_string",
        ("\\texorpdfstring",),
    ),
    # d09 空文档
    ("No pages of output.", "no_output", "no_output", ("页面",)),
    # c16 缺 \item
    (
        "! LaTeX Error: Something's wrong--perhaps a missing \\item.\n\nl.5 \\end{itemize}",
        "missing_item",
        "missing_item",
        ("\\item",),
    ),
    # c09 begin/end 不配对
    (
        "! LaTeX Error: \\begin{document} ended by \\end{itemize}.\n\nl.3 \\end{itemize}",
        "end_mismatch",
        "end_mismatch",
        ("\\end",),
    ),
    # c07 列数不匹配
    (
        "! Extra alignment tab has been changed to \\cr.\n<recently read> \\endtemplate\n\n"
        "l.4 a & b &\n            c \\\\",
        "alignment_tab",
        "alignment_tab",
        ("&",),
    ),
]


@pytest.mark.parametrize(("text", "rule_id", "kind", "expected_in"), REAL_LOG_CASES)
def test_real_log_snippets_hit_expected_rule(text: str, rule_id: str, kind: str, expected_in: tuple[str, ...]) -> None:
    hint = hint_for_text(text)
    assert hint is not None, f"未命中任何规则：{text!r}"
    assert hint.rule_id == rule_id
    assert hint.kind == kind
    for fragment in expected_in:
        assert fragment in hint.text, f"文案缺少 {fragment!r}：{hint.text}"


def test_xelatex_missing_glyph_with_codepoint_matches() -> None:
    """D1：XeLaTeX 真实日志带 ``(U+XXXX)``，旧正则整句失配。"""
    text = "Missing character: There is no 中 (U+4E2D) in font [lmroman10-regular]:mapping=tex-text;!"
    hint = hint_for_text(text)
    assert hint is not None
    assert hint.rule_id == "missing_glyph"
    assert hint.kind == "missing_glyph"
    # 缺字形文案禁止再把 T1 fontenc 当成解法。
    assert "fontenc" not in hint.text.lower()
    assert "中" in hint.text
    assert "ctex" in hint.text


def test_xelatex_missing_glyph_symbol_with_codepoint() -> None:
    text = "Missing character: There is no ✓ (U+2713) in font [lmroman10-regular]:mapping=tex-text;!"
    hint = hint_for_text(text)
    assert hint is not None
    assert hint.rule_id == "missing_glyph"
    assert hint.kind == "missing_glyph"
    assert "✓" in hint.text


def test_old_missing_glyph_sample_still_matches() -> None:
    """旧样本 ``There is no α in font cmr10!``（无码位）必须仍命中。"""
    hint = hint_for_text("Missing character: There is no α in font cmr10!")
    assert hint is not None
    assert hint.rule_id == "missing_glyph"
    assert "α" in hint.text


def test_font_tfm_not_loadable_extracts_spec_and_reason() -> None:
    text = "! Font \\foo=NoSuchFont at 10.0pt not loadable: Metric (TFM) file not found."
    hint = hint_for_text(text)
    assert hint is not None
    assert hint.rule_id == "font_not_loadable"
    assert hint.kind == "missing_font_tfm"
    assert "NoSuchFont" in hint.text
    assert "Metric (TFM) file not found" in hint.text
    assert hint.commands == ("kpsewhich nosuchfont.tfm",)


def test_fontspec_font_not_found_extracts_family() -> None:
    text = '! Package fontspec Error: The font "NoSuchFontFamilyXYZ" cannot be found.'
    hint = hint_for_text(text)
    assert hint is not None
    assert hint.rule_id == "fontspec_font_not_found"
    assert hint.kind == "missing_font_family"
    assert "NoSuchFontFamilyXYZ" in hint.text
    assert any("fc-list" in c for c in hint.commands)


def test_capacity_input_stack_advises_recursion_not_memory() -> None:
    """D4：input stack size 是递归问题，不能把 main_memory 写成唯一答案。"""
    text = "! TeX capacity exceeded, sorry [input stack size=5000].\n\\a ->\\a\n        \\a\nl.4 \\a"
    hint = hint_for_text(text)
    assert hint is not None
    assert hint.rule_id == "capacity"
    assert hint.kind == "capacity"
    assert "递归" in hint.text
    # 命令区允许出现发行版配置命令，但根因文案必须先讲递归。
    assert hint.text.index("递归") < hint.text.index("容量") if "容量" in hint.text else True


def test_citation_and_reference_extract_keys() -> None:
    cite = hint_for_text("LaTeX Warning: Citation `key1' on page 1 undefined on input line 3.\nNo file main.bbl.")
    # missing_bbl 早于 undefined_citation：先解决后端。
    assert cite is not None and cite.rule_id == "missing_bbl"

    ref = hint_for_text("LaTeX Warning: Reference `nosuchlabel' on page 1 undefined on input line 3.")
    assert ref is not None and ref.rule_id == "undefined_reference"
    assert "nosuchlabel" in ref.text


def test_missing_number_extracts_token() -> None:
    text = "! Missing number, treated as zero.\n<to be read again>\n                   x\nl.3 \\vspace{x}"
    hint = hint_for_text(text)
    assert hint is not None
    assert hint.rule_id == "missing_number"
    assert "x" in hint.text


def test_runaway_extracts_scanned_command() -> None:
    text = "Runaway argument?\n! File ended while scanning use of \\@argdef.\n<inserted text>\n                \\par\n<*> main.tex"
    hint = hint_for_text(text)
    assert hint is not None
    assert hint.rule_id == "runaway"
    assert "\\@argdef" in hint.text


def test_runaway_file_ended_without_runaway_prefix() -> None:
    text = "! File ended while scanning use of \\textbf .\n<inserted text>\n                \\par\n<*> main.tex"
    hint = hint_for_text(text)
    assert hint is not None
    assert hint.rule_id == "runaway"
    assert "\\textbf" in hint.text


def test_undefined_control_extracts_broken_command() -> None:
    text = "! Undefined control sequence.\nl.3 Hello \\undefinedcmd\n                        world."
    hint = hint_for_text(text)
    assert hint is not None
    assert hint.rule_id == "undefined_control"
    assert "undefinedcmd" in hint.text
    assert any("undefinedcmd" in c for c in hint.commands)


def test_unicode_cjk_branch_mentions_ctex() -> None:
    text = "! LaTeX Error: Unicode character 中 (U+4E2D)\n               not set up for use with LaTeX."
    hint = hint_for_text(text)
    assert hint is not None
    assert hint.rule_id == "unicode"
    assert "ctex" in hint.text
    # 必须说明该消息只来自 8 位引擎。
    assert "pdfLaTeX" in hint.text or "8 位" in hint.text


def test_cjk_missing_glyph_both_space_variants() -> None:
    plain = "CJKfamily 'song' ([FandolSong-Regular]) does not contain glyph '中' (U+4E2D)"
    spaced = "CJKfamily 'song' ([FandolSong-Regular]) does not contain glyph '中' ( U + 4E2D )"
    for text in (plain, spaced):
        hint = hint_for_text(text)
        assert hint is not None
        assert hint.rule_id == "cjk_missing_glyph"
        assert hint.kind == "cjk_missing_glyph"
        assert "song" in hint.text
        assert "中" in hint.text
        assert "4E2D" in hint.text


def test_fontset_unavailable_message() -> None:
    hint = hint_for_text("CTeX fontset 'adobe' is unavailable in current mode.")
    assert hint is not None
    assert hint.rule_id == "fontset_unavailable"
    assert "当前引擎模式不支持" in hint.text


def test_missing_bbl_substitutes_jobname() -> None:
    hint = hint_for_text("No file main.bbl.", jobname="main")
    assert hint is not None
    assert hint.rule_id == "missing_bbl"
    assert hint.commands == ("biber main", "bibtex main")
    # 两条文献流程都要写清。
    assert "biber" in hint.text and "bibtex" in hint.text
    assert "addbibresource" in hint.text and "bibliography" in hint.text


def test_missing_bib_documents_both_resource_syntaxes() -> None:
    hint = hint_for_text("I couldn't open database file refs.bib")
    assert hint is not None
    assert hint.rule_id == "missing_bib"
    assert "addbibresource" in hint.text
    assert "bibliography" in hint.text


def test_double_subscript_accent_atom_empty_group() -> None:
    """SE253080：重音原子的外层花括号会被剥掉，需空组 workaround。"""
    hint = hint_for_text("! Double subscript.")
    assert hint is not None
    assert hint.rule_id == "double_script"
    assert "空组" in hint.text
    assert "${{}" in hint.text
    # 同时区分嵌套下标与整体分组两种意图。
    assert "x_{n_i}" in hint.text
    assert "${x_n}_i$" in hint.text


def test_tfm_missing_is_pdftex_font_package_not_fontspec() -> None:
    """SE75166：TFM not found 是 pdflatex 缺字体宏包，不串成 fontspec 族找不到。"""
    text = "! Font T1/cmr/m/n/10=ecrm1000 at 10pt not loadable: Metric (TFM) file ecrm1000.tfm not found."
    hint = hint_for_text(text)
    assert hint is not None
    assert hint.rule_id == "tfm_font_missing"
    assert hint.kind == "tfm_font_missing"
    assert "ecrm1000.tfm" in hint.text
    assert any("tlmgr search" in c for c in hint.commands)
    # 与 fontspec 规则互不串扰。
    assert hint.rule_id != "fontspec_font_not_found"


def test_fontspec_sample_does_not_become_tfm_rule() -> None:
    hint = hint_for_text('! Package fontspec Error: The font "Times New Roman" cannot be found.')
    assert hint is not None
    assert hint.rule_id == "fontspec_font_not_found"
    assert hint.rule_id != "tfm_font_missing"


def test_capacity_input_stack_blames_loop_not_memory() -> None:
    """SE24247：input stack 可能是宏包/样式链循环，不能写成调大 main_memory。"""
    text = "! TeX capacity exceeded, sorry [input stack size=5000].\n\\a ->\\a\nl.4 \\a"
    hint = hint_for_text(text)
    assert hint is not None
    assert hint.rule_id == "capacity"
    assert "递归" in hint.text
    assert "宏包" in hint.text
    assert "样式" in hint.text
    assert "main_memory" not in hint.text


def test_missing_begin_document_mentions_preamble_command_typo() -> None:
    hint = hint_for_text("! LaTeX Error: Missing \\begin{document}.")
    assert hint is not None
    assert hint.rule_id == "missing_begin_document"
    assert "反斜杠" in hint.text
