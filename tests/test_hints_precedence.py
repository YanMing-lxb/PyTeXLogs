"""hints.py 规则表的顺序与优先级快照。

规则表的**顺序就是语义**：``Emergency stop`` 必须早于 ``Undefined control sequence``，
缺宏包必须早于缺文件，``Missing character`` 不能被“字体未找到”抢答。这个文件
把顺序钉死，任何重排都会在测试里立刻失败，而不是等到线上给出错误建议。
"""

import pytest

from pytexlogs.hints import _RULES, _hint_for_text_raw, _normalize, hint_for_text

#: 规则 id 的固定顺序。新增规则只能追加；调整顺序必须同时改这里并说明原因。
RULE_ORDER = (
    "missing_package",
    "missing_file",
    "font_not_loadable",
    "tfm_font_missing",
    "missing_font",
    "fontset_unavailable",
    "unicode",
    "cjk_missing_glyph",
    "missing_glyph",
    "missing_bbl",
    "undefined_citation",
    "undefined_reference",
    "undefined_environment",
    "missing_bib",
    "biber_case_mismatch",
    "float_overflow",
    "capacity",
    "no_output",
    "runaway",
    "math_mode",
    "double_script",
    "fatal",
    "undefined_control",
    "end_mismatch",
    "option_clash",
    "invalid_utf8",
    "alignment_tab",
    "missing_number",
    "missing_item",
    "missing_begin_document",
    "extra_close_brace",
    "missing_right",
    "bad_math_delimiter",
    "misplaced_noalign",
    "illegal_unit",
    "command_already_defined",
    "no_line_to_end",
    "hyperref_pdf_string",
    "fontspec_font_not_found",
    "package_error",
    "log_hint",
)

#: 每条规则至少一条语料：(文本, 命中规则 id, 期望 Hint.kind, 工具作用域)
#: 工具作用域为 None 时按未指定工具跑；biber 专项规则必须显式传 ``biber``。
CORPUS: list[tuple[str, str, str, str | None]] = [
    ("File `booktabs.sty' not found.", "missing_package", "missing_package", None),
    ("! LaTeX Error: File `fig.png' not found.", "missing_file", "missing_graphic", None),
    ("File `refs.bib' not found.", "missing_file", "missing_bib", None),
    ("File `chapter2.tex' not found.", "missing_file", "missing_file", None),
    (
        "! Font \\foo=NoSuchFont at 10.0pt not loadable: Metric (TFM) file not found.",
        "font_not_loadable",
        "missing_font_tfm",
        None,
    ),
    (
        "! Font T1/cmr/m/n/10=ecrm1000 at 10pt not loadable: Metric (TFM) file ecrm1000.tfm not found.",
        "tfm_font_missing",
        "tfm_font_missing",
        None,
    ),
    ("Font `NotoSans' not found", "missing_font", "missing_font", None),
    ("CTeX fontset 'fandol' is unavailable in current mode.", "fontset_unavailable", "fontset_unavailable", None),
    ("Unicode character μ (U+03BC) not set up for use with LaTeX.", "unicode", "unicode", None),
    (
        "CJKfamily 'song' ([FandolSong-Regular]) does not contain glyph '中' ( U + 4E2D )",
        "cjk_missing_glyph",
        "cjk_missing_glyph",
        None,
    ),
    ("Missing character: There is no α in font cmr10!", "missing_glyph", "missing_glyph", None),
    ("No file main.bbl.", "missing_bbl", "missing_bbl", None),
    (
        "LaTeX Warning: Citation `knuth84' on page 1 undefined on input line 9.",
        "undefined_citation",
        "undefined_citation",
        None,
    ),
    ("找不到 citation `knuth84`", "undefined_citation", "undefined_citation", None),
    (
        "LaTeX Warning: Reference `sec:intro' on page 1 undefined on input line 3.",
        "undefined_reference",
        "undefined_reference",
        None,
    ),
    ("找不到 reference `sec:intro`", "undefined_reference", "undefined_reference", None),
    ("! LaTeX Error: Environment equationn undefined.", "undefined_environment", "undefined_environment", None),
    ("I couldn't open database file refs.bib", "missing_bib", "missing_bib", None),
    ("WARN - Case mismatch: key `Smith' vs `smith' in .bib", "biber_case_mismatch", "biber_key_case", "biber"),
    ("! Too many unprocessed floats.", "float_overflow", "float_overflow", None),
    ("! TeX capacity exceeded, sorry [main memory size=3000000].", "capacity", "capacity", None),
    ("! No pages of output.", "no_output", "no_output", None),
    ("Runaway argument?", "runaway", "runaway", None),
    ("File ended while scanning use of \\foo.", "runaway", "runaway", None),
    ("! Missing $ inserted.", "math_mode", "math_mode", None),
    ("! Double subscript.", "double_script", "double_script", None),
    ("! Double superscript.", "double_script", "double_script", None),
    ("! LaTeX Error: Option clash for package graphicx.", "option_clash", "option_clash", None),
    ("! Emergency stop.", "fatal", "fatal", None),
    ("Emergency stop. Fatal error occurred, no output PDF file produced!", "fatal", "fatal", None),
    ("! Undefined control sequence.\nl.5 ... \\badcmd\n", "undefined_control", "undefined_control", None),
    ("! LaTeX Error: \\begin{document} ended by \\end{itemize}.", "end_mismatch", "end_mismatch", None),
    ("! Package inputenc Error: Invalid UTF-8 byte sequence.", "invalid_utf8", "invalid_utf8", None),
    ("! Extra alignment tab has been changed to \\cr.", "alignment_tab", "alignment_tab", None),
    ("! Misplaced alignment tab character &.", "alignment_tab", "alignment_tab", None),
    ("! Missing number, treated as zero.", "missing_number", "missing_number", None),
    ("! LaTeX Error: Something's wrong--perhaps a missing \\item.", "missing_item", "missing_item", None),
    ("! LaTeX Error: Missing \\begin{document}.", "missing_begin_document", "missing_begin_document", None),
    ("! Too many }'s.", "extra_close_brace", "extra_close_brace", None),
    ("! Missing \\right. inserted.", "missing_right", "missing_delimiter", None),
    ("! Display math should end with $$.", "bad_math_delimiter", "math_delimiter", None),
    ("! Misplaced \\noalign.", "misplaced_noalign", "misplaced_noalign", None),
    ("! Illegal unit of measure (pt inserted).", "illegal_unit", "illegal_unit", None),
    ("! LaTeX Error: Command \\foo already defined.", "command_already_defined", "command_conflict", None),
    ("! LaTeX Error: There's no line here to end.", "no_line_to_end", "no_line_to_end", None),
    (
        "Package hyperref Warning: Token not allowed in a PDF string (Unicode):",
        "hyperref_pdf_string",
        "hyperref_pdf_string",
        None,
    ),
    (
        '! Package fontspec Error: The font "NoSuchFontFamilyXYZ" cannot be found.',
        "fontspec_font_not_found",
        "missing_font_family",
        None,
    ),
    ("! Package hyperref Error: Wrong driver.", "package_error", "package_error", None),
    ("Overfull \\hbox (12.0pt too wide) in paragraph at lines 1--2", "log_hint", "log_hint", None),
]


def _matched_rule_id(text: str) -> str | None:
    """按真实规则表跑一遍，返回命中的规则 id（与 ``_hint_for_text_raw`` 同序）。"""
    normalized = _normalize(text)
    for rule in _RULES:
        context = rule.match(normalized)
        if not context:
            continue
        if rule.build(context) is not None:
            return rule.rule_id
    return None


def test_rule_order_snapshot() -> None:
    assert tuple(rule.rule_id for rule in _RULES) == RULE_ORDER
    assert len(RULE_ORDER) == len(set(RULE_ORDER)), "规则 id 不能重复"


def test_corpus_covers_every_rule() -> None:
    hits = {_matched_rule_id(text) for text, _rule_id, _kind, _tool in CORPUS}
    assert set(RULE_ORDER) - hits == set(), "有规则没有任何语料覆盖"


@pytest.mark.parametrize(("text", "rule_id", "kind", "tool"), CORPUS)
def test_corpus_hits_expected_rule(text: str, rule_id: str, kind: str, tool: str | None) -> None:
    assert _matched_rule_id(text) == rule_id
    hint = _hint_for_text_raw(text, tool_name=tool or "")
    assert hint is not None
    assert hint.kind == kind


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # 致命错误必须早于未定义命令：两条同时出现时先报“编译被中断”
        ("! Emergency stop.\n! Undefined control sequence.\nl.3 \\badcmd", "fatal"),
        # 缺 .sty 必须早于一般缺文件
        ("! LaTeX Error: File `booktabs.sty' not found.", "missing_package"),
        # “字体缺字形”不能被“字体未找到”抢答
        ("Missing character: There is no α in font cmr10!", "missing_glyph"),
        # 多行错误必须早于内建提示表（Overfull 之类的“提示”排最后）
        (
            "! Undefined control sequence.\nl.9 \\badcmd\nOverfull \\hbox (3.0pt too wide)",
            "undefined_control",
        ),
        # 具体宏包错误也晚于“缺宏包”——后者是更直接的可执行修复
        ("! LaTeX Error: File `foo.sty' not found.\n! Package foo Error: bad option", "missing_package"),
        # 选项冲突必须早于通用宏包错误，否则只剩“查看上下文”的兜底
        (
            "! LaTeX Error: Option clash for package graphicx.\n! Package graphicx Error: bad option",
            "option_clash",
        ),
        # not loadable 必须早于 missing_font，避免贪婪正则抓成垃圾字体名
        (
            "! Font \\foo=NoSuchFont at 10.0pt not loadable: Metric (TFM) file not found.",
            "font_not_loadable",
        ),
        # fontspec 找不到字体族必须早于通用 Package Error 兜底
        (
            '! Package fontspec Error: The font "Times New Roman" cannot be found.',
            "fontspec_font_not_found",
        ),
        # 缺 \begin{document} 早于未定义命令：首条具体 LaTeX 错误优先
        (
            "! LaTeX Error: Missing \\begin{document}.\n! Undefined control sequence.\nl.3 \\badcmd",
            "missing_begin_document",
        ),
        # 缺 .bbl 早于未定义引用键：先解决后端没跑
        ("No file main.bbl.\nLaTeX Warning: Citation `key1' undefined", "missing_bbl"),
    ],
)
def test_precedence_pairs(text: str, expected: str) -> None:
    assert _matched_rule_id(text) == expected


def test_hint_for_text_uses_same_order() -> None:
    """公开入口与内部实现必须命中同一条规则（避免两套顺序）。"""
    text = "! Emergency stop.\n! Undefined control sequence."
    assert hint_for_text(text).kind == "fatal"
    assert _hint_for_text_raw(text).kind == "fatal"


@pytest.mark.parametrize(("text", "rule_id", "kind", "tool"), CORPUS)
def test_hint_carries_rule_id(text: str, rule_id: str, kind: str, tool: str | None) -> None:
    """每条 hint 必须带稳定 rule_id，供 JSON/SARIF 追溯与测试断言。"""
    hint = hint_for_text(text, tool_name=tool)
    assert hint is not None
    assert hint.rule_id == rule_id
    assert hint.kind == kind
