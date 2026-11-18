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
    "missing_font",
    "unicode",
    "missing_glyph",
    "undefined_citation",
    "undefined_reference",
    "undefined_environment",
    "missing_bib",
    "float_overflow",
    "capacity",
    "no_output",
    "runaway",
    "math_mode",
    "fatal",
    "undefined_control",
    "end_mismatch",
    "invalid_utf8",
    "alignment_tab",
    "missing_number",
    "missing_item",
    "package_error",
    "log_hint",
)

#: 每条规则至少一条语料：(文本, 命中规则 id, 期望 Hint.kind)
CORPUS = [
    ("File `booktabs.sty' not found.", "missing_package", "missing_package"),
    ("! LaTeX Error: File `fig.png' not found.", "missing_file", "missing_graphic"),
    ("File `refs.bib' not found.", "missing_file", "missing_bib"),
    ("File `chapter2.tex' not found.", "missing_file", "missing_file"),
    ("Font `NotoSans' not found", "missing_font", "missing_font"),
    ("Unicode character μ (U+03BC) not set up for use with LaTeX.", "unicode", "unicode"),
    ("Missing character: There is no α in font cmr10!", "missing_glyph", "missing_glyph"),
    ("LaTeX Warning: Citation `knuth84' on page 1 undefined on input line 9.", "undefined_citation", "undefined_citation"),
    ("找不到 citation `knuth84`", "undefined_citation", "undefined_citation"),
    ("LaTeX Warning: Reference `sec:intro' on page 1 undefined on input line 3.", "undefined_reference", "undefined_reference"),
    ("找不到 reference `sec:intro`", "undefined_reference", "undefined_reference"),
    ("! LaTeX Error: Environment equationn undefined.", "undefined_environment", "undefined_environment"),
    ("I couldn't open database file refs.bib", "missing_bib", "missing_bib"),
    ("! Too many unprocessed floats.", "float_overflow", "float_overflow"),
    ("! TeX capacity exceeded, sorry [main memory size=3000000].", "capacity", "capacity"),
    ("! No pages of output.", "no_output", "no_output"),
    ("Runaway argument?", "runaway", "runaway"),
    ("File ended while scanning use of \\foo.", "runaway", "runaway"),
    ("! Missing $ inserted.", "math_mode", "math_mode"),
    ("! Emergency stop.", "fatal", "fatal"),
    ("Emergency stop. Fatal error occurred, no output PDF file produced!", "fatal", "fatal"),
    ("! Undefined control sequence.\nl.5 ... \\badcmd\n", "undefined_control", "undefined_control"),
    ("! LaTeX Error: \\begin{document} ended by \\end{itemize}.", "end_mismatch", "end_mismatch"),
    ("! Package inputenc Error: Invalid UTF-8 byte sequence.", "invalid_utf8", "invalid_utf8"),
    ("! Extra alignment tab has been changed to \\cr.", "alignment_tab", "alignment_tab"),
    ("! Misplaced alignment tab character &.", "alignment_tab", "alignment_tab"),
    ("! Missing number, treated as zero.", "missing_number", "missing_number"),
    ("! LaTeX Error: Something's wrong--perhaps a missing \\item.", "missing_item", "missing_item"),
    ("! Package hyperref Error: Wrong driver.", "package_error", "package_error"),
    ("Overfull \\hbox (12.0pt too wide) in paragraph at lines 1--2", "log_hint", "log_hint"),
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
    hits = {_matched_rule_id(text) for text, _rule_id, _kind in CORPUS}
    assert set(RULE_ORDER) - hits == set(), "有规则没有任何语料覆盖"


@pytest.mark.parametrize(("text", "rule_id", "kind"), CORPUS)
def test_corpus_hits_expected_rule(text: str, rule_id: str, kind: str) -> None:
    assert _matched_rule_id(text) == rule_id
    hint = _hint_for_text_raw(text)
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
    ],
)
def test_precedence_pairs(text: str, expected: str) -> None:
    assert _matched_rule_id(text) == expected


def test_hint_for_text_uses_same_order() -> None:
    """公开入口与内部实现必须命中同一条规则（避免两套顺序）。"""
    text = "! Emergency stop.\n! Undefined control sequence."
    assert hint_for_text(text).kind == "fatal"
    assert _hint_for_text_raw(text).kind == "fatal"
