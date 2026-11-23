"""第 4 轮独立验证（round4-verify.md）F1–F11 修复回归。

每条探针对应验证报告里的一个失败项：正则回溯、旧表残留文案、散文/引号/注释
误报、LaTeX 规则工具隔离、子文件 jobname 推导、biber 空工具作用域、unicode
符号分支命令、fontset 引号变体、定界符左右变体、Underfull vbox 旧表键。
"""

import time

import pytest

from pytexlogs import LogEntry, LogLevel
from pytexlogs.hints import RULE_IDS, hint_for_entry, hint_for_text

# --- F1：missing_font 正则灾难性回溯 -----------------------------------------


def test_missing_font_regex_no_catastrophic_backtrack() -> None:
    """2000 行重复缺字形样本必须在 1 s 内返回，且仍命中 missing_glyph。"""
    sample = "Missing character: There is no α in font cmr10!"
    text = "\n".join([sample] * 2000)
    start = time.perf_counter()
    hint = hint_for_text(text)
    elapsed = time.perf_counter() - start
    assert elapsed < 1.0, f"耗时 {elapsed:.3f} s 超过预算"
    assert hint is not None
    assert hint.rule_id == "missing_glyph"


def test_missing_font_regex_handles_codepoint_variant_fast() -> None:
    sample = "Missing character: There is no 中 (U+4E2D) in font [lmroman10-regular]:mapping=tex-text;!"
    text = "\n".join([sample] * 2000)
    start = time.perf_counter()
    hint = hint_for_text(text)
    elapsed = time.perf_counter() - start
    assert elapsed < 1.0, f"耗时 {elapsed:.3f} s 超过预算"
    assert hint is not None and hint.rule_id == "missing_glyph"


# --- F2：旧表 Missing character 不得再建议 T1 fontenc -------------------------


def test_legacy_missing_character_has_no_fontenc_advice() -> None:
    hint = hint_for_text("Missing character: there is no X")
    assert hint is not None
    assert "fontenc" not in hint.text.lower()


# --- F3：散文 / 引号 / 注释中的错误字符串不得抢答 -----------------------------


F3_PROBE_STRINGS = [
    "% Missing character: There is no 中 in font cmr10!",
    "% File `foo.sty' not found.",
    '"Missing character: There is no 中 in font cmr10!"',
    '"File `foo.sty\' not found"',
    'The tutorial says: The font "Arial" cannot be found when the family name is mistyped.',
    'The font "Times New Roman" cannot be found in the FAQ.',
    "Font `OldFont' not found appears in the changelog.",
    "A Double subscript error occurs when two underscores follow a single atom.",
    "In the FAQ: Too many }'s means an extra closing brace.",
    "The Option clash for package graphicx error is explained in the manual.",
    "Please fix the Missing \\begin{document} issue.",
]


@pytest.mark.parametrize("text", F3_PROBE_STRINGS)
def test_prose_and_quoted_samples_do_not_match_specific_rule(text: str) -> None:
    hint = hint_for_text(text)
    assert hint is None, f"散文/注释/引号样例被误判为 {hint.rule_id if hint else None}"


def test_fontspec_prose_needs_package_error_context() -> None:
    # 散文里提到字体找不到不算 fontspec 报错；必须带 Package fontspec Error 前缀。
    assert hint_for_text('The font "Arial" cannot be found in the FAQ.') is None
    hint = hint_for_text('! Package fontspec Error: The font "Arial" cannot be found.')
    assert hint is not None and hint.rule_id == "fontspec_font_not_found"


# --- F4：LaTeX 专属规则在 biber/bibtex 日志下不触发 --------------------------


LATEX_ONLY_CASES = [
    ("! Missing $ inserted.", "math_mode"),
    ("! Double subscript.", "double_script"),
    ("! Too many unprocessed floats.", "float_overflow"),
    ("! Package inputenc Error: Invalid UTF-8 byte sequence.", "invalid_utf8"),
    ("! Extra alignment tab has been changed to \\cr.", "alignment_tab"),
    ("! No pages of output.", "no_output"),
]


@pytest.mark.parametrize(("text", "rule_id"), LATEX_ONLY_CASES)
def test_latex_only_rules_skip_backend_tools(text: str, rule_id: str) -> None:
    for backend in ("biber", "bibtex"):
        assert hint_for_text(text, tool_name=backend) is None, f"{rule_id} 在 {backend} 下误触发"
    # latex 工具与未知上下文（空 tool_name）正常放行。
    latex_hint = hint_for_text(text, tool_name="latex")
    assert latex_hint is not None and latex_hint.rule_id == rule_id
    assert hint_for_text(text) is not None


# --- F5：子文件条目不得把自身 stem 当成主文件 jobname -------------------------


def test_subfile_entry_without_context_keeps_placeholder() -> None:
    entry = LogEntry(
        level=LogLevel.WARNING,
        file="chapters/intro.tex",
        line=3,
        text="LaTeX Warning: Citation `Smith2020' undefined on input line 3.",
    )
    hint = hint_for_entry(entry)
    assert hint is not None
    assert any("<jobname>" in command for command in hint.commands)
    assert not any("intro" in command for command in hint.commands)


def test_top_level_entry_still_derives_jobname() -> None:
    entry = LogEntry(
        level=LogLevel.WARNING,
        file="main.tex",
        line=3,
        text="LaTeX Warning: Citation `Smith2020' undefined on input line 3.",
    )
    hint = hint_for_entry(entry)
    assert hint is not None
    assert "biber main" in hint.commands


# --- F6：case mismatch 在工具名为空时放行，latex 下仍不得命中 ------------------


def test_biber_case_mismatch_allowed_without_tool_context() -> None:
    text = "WARN - Case mismatch: key `Smith' vs `smith' in refs.bib"
    hint = hint_for_text(text)
    assert hint is not None
    assert hint.rule_id == "biber_case_mismatch"
    assert hint.kind == "biber_key_case"

    assert hint_for_text(text, tool_name="latex") is None


# --- F9：fontset 三种引号变体都命中 ------------------------------------------


FONTSET_VARIANTS = [
    "CTeX fontset 'adobe' is unavailable in current mode.",
    "CTeX fontset `adobe' is unavailable in current mode.",
    'CTeX fontset "adobe" is unavailable in current mode.',
]


@pytest.mark.parametrize("text", FONTSET_VARIANTS)
def test_fontset_unavailable_quote_variants(text: str) -> None:
    hint = hint_for_text(text)
    assert hint is not None
    assert hint.rule_id == "fontset_unavailable"
    assert "adobe" in hint.text


# --- F10：Missing delimiter 左右两侧都覆盖 ------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "! Missing delimiter (. inserted.",
        "! Missing delimiter ) inserted.",
    ],
)
def test_missing_delimiter_both_sides(text: str) -> None:
    hint = hint_for_text(text)
    assert hint is not None
    assert hint.rule_id == "missing_right"
    assert hint.kind == "missing_delimiter"


# --- F11：Underfull \vbox 进入旧提示表 ----------------------------------------


def test_underfull_vbox_hits_legacy_hint() -> None:
    hint = hint_for_text("Underfull \\vbox (badness 10000) has occurred while \\output is active")
    assert hint is not None
    assert hint.rule_id == "log_hint"


# --- F13：规则数量口径与快照自洽 ---------------------------------------------


def test_rule_count_matches_snapshot() -> None:
    assert len(RULE_IDS) == len(set(RULE_IDS))
    # 实测口径写进文档；快照顺序见 test_hints_precedence.py。
    assert len(RULE_IDS) == 41
