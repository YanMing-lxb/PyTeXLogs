"""第 5 轮代码审查（round5-review.md）H1/M1/M2/M3/L1/L2/L4/L6/L7/L8 修复回归。"""

import pytest

from pytexlogs import LogEntry, LogLevel
from pytexlogs.hints import (
    RULE_IDS,
    detect_missing_package,
    hint_for_entry,
    hint_for_text,
)

# --- H1：biber 重复条目键：已核实逐字片段，旧表键与 --noskipduplicates 分支可达 ---


def test_biber_duplicate_entry_key_hits_legacy_hint() -> None:
    text = "WARN - Duplicate entry key: 'bangerth:adaptive' in file 'refs.bib', skipping ..."
    hint = hint_for_text(text, tool_name="biber")
    assert hint is not None
    assert hint.rule_id == "log_hint"
    # 最具体键优先：命中重复条目文案，而不是被通用 WARN - 兜底遮蔽。
    assert "--noskipduplicates" in hint.text
    assert "通用 Biber" not in hint.text
    # --noskipduplicates 只由追加分支给出一次，中英基文案不重复该命令。
    assert hint.text.count("--noskipduplicates") == 1
    assert hint.text_en.count("--noskipduplicates") == 1
    # 工具隔离：latex 日志不套用 biber 旧表。
    assert hint_for_text(text, tool_name="latex") is None


def test_biber_generic_warn_falls_back_to_warn_key() -> None:
    hint = hint_for_text("WARN - Something odd happened", tool_name="biber")
    assert hint is not None
    assert hint.rule_id == "log_hint"
    assert "通用 Biber" in hint.text
    assert "--noskipduplicates" not in hint.text


def test_biber_missing_entry_key_beats_generic_warn() -> None:
    hint = hint_for_text("WARN - I didn't find a database entry for 'x'", tool_name="biber")
    assert hint is not None
    assert hint.rule_id == "log_hint"
    assert "参考文献键" in hint.text
    assert "通用 Biber" not in hint.text


def test_prose_missing_character_sentence_is_suppressed() -> None:
    """说明性散文里的 `Missing character` 子串不得返回字形建议（旧表同受散文守卫）。"""
    hint = hint_for_text("The Missing character warning appears when the current font lacks a glyph.")
    assert hint is None


def test_real_layout_lines_still_hit_legacy_hint() -> None:
    for text in (
        "Overfull \\hbox (243pt too wide) detected at line 3",
        "Underfull \\hbox (badness 10000) has occurred while \\output is active",
    ):
        hint = hint_for_text(text)
        assert hint is not None and hint.rule_id == "log_hint", text


# --- M1：裸 `<主文件>` 占位符不被 .log/.blg 路径污染 ---


def test_invalid_utf8_root_log_does_not_leak_log_name() -> None:
    text = "! Package inputenc Error: Invalid UTF-8 byte sequence."
    hint = hint_for_text(text, root_file="main.log")
    assert hint is not None
    assert not any("main.log" in command for command in hint.commands)

    # 无显式 jobname、root 非 .tex 时退回 stem.tex，不把日志文件名写进命令。
    hint2 = hint_for_text(text, root_file="paper.log")
    assert hint2 is not None
    assert not any("paper.log" in command for command in hint2.commands)
    assert any("paper.tex" in command for command in hint2.commands)


def test_entry_with_log_file_does_not_become_source() -> None:
    entry = LogEntry(
        level=LogLevel.ERROR,
        file="main.log",
        line=1,
        text="! Package inputenc Error: Invalid UTF-8 byte sequence.",
    )
    hint = hint_for_entry(entry)
    assert hint is not None
    assert not any("main.log" in command for command in hint.commands)


# --- M2：错误帧优先，续行散文词不吞掉真实错误 ---


def test_error_frame_with_prose_continuation_still_matches() -> None:
    text = "! Undefined control sequence.\nl.3 \\foo\nThis means you forgot a package."
    hint = hint_for_text(text)
    assert hint is not None
    assert hint.rule_id == "undefined_control"


def test_plain_prose_still_suppressed() -> None:
    # 无错误标志词的散文续行仍按散文抑制（round4 11 条探针的代表项）。
    assert hint_for_text("A Double subscript error occurs when two underscores follow a single atom.") is None
    assert hint_for_text("The Option clash for package graphicx error is explained in the manual.") is None


# --- M3：纯 LaTeX 规则在 biber/bibtex 后端日志下不触发 ---


LATEX_ONLY_ROUND5 = [
    ("! Undefined control sequence.", "undefined_control"),
    ("! LaTeX Error: \\begin{document} ended by \\end{itemize}.", "end_mismatch"),
    ("! LaTeX Error: Option clash for package graphicx.", "option_clash"),
    ("! Missing number, treated as zero.", "missing_number"),
    ("! LaTeX Error: Something's wrong--perhaps a missing \\item.", "missing_item"),
    ("! Too many }'s.", "extra_close_brace"),
    ("! Missing \\right. inserted.", "missing_right"),
    ("! Bad math environment delimiter.", "bad_math_delimiter"),
    ("Misplaced \\noalign in table cell.", "misplaced_noalign"),
    ("! Illegal unit of measure (pt inserted).", "illegal_unit"),
    ("! Command \\foo already defined.", "command_already_defined"),
    ("! There's no line here to end.", "no_line_to_end"),
    ("! Token not allowed in a PDF string.", "hyperref_pdf_string"),
    ("! LaTeX Error: Environment equationn undefined.", "undefined_environment"),
]


@pytest.mark.parametrize(("text", "rule_id"), LATEX_ONLY_ROUND5)
def test_latex_only_rules_skip_backend_tools_round5(text: str, rule_id: str) -> None:
    for backend in ("biber", "bibtex"):
        assert hint_for_text(text, tool_name=backend) is None, f"{rule_id} 在 {backend} 下误触发"
    latex_hint = hint_for_text(text, tool_name="latex")
    assert latex_hint is not None and latex_hint.rule_id == rule_id
    assert hint_for_text(text) is not None


# --- L1：交叉引用重编译命令不写死 xelatex ---


def test_undefined_reference_command_is_engine_neutral() -> None:
    hint = hint_for_text("LaTeX Warning: Reference `sec:intro' undefined on input line 3.")
    assert hint is not None
    assert not any("xelatex" in c or "lualatex" in c for c in hint.commands)
    assert any("<引擎>" in c for c in hint.commands)


# --- L2：invalid_utf8 标注 `file` 工具的 Windows 替代 ---


def test_invalid_utf8_notes_windows_alternative() -> None:
    hint = hint_for_text("! Package inputenc Error: Invalid UTF-8 byte sequence.")
    assert hint is not None
    assert "Windows" in hint.text
    assert "PowerShell" in hint.text


# --- L4：fontset 规则补齐引擎命令与 ctex fontset 命令 ---


def test_fontset_unavailable_has_commands() -> None:
    hint = hint_for_text("CTeX fontset 'adobe' is unavailable in current mode.")
    assert hint is not None
    assert any("xelatex" in c and "主文件" in c for c in hint.commands)
    assert any("fontset=fandol" in c for c in hint.commands)


# --- L7：缺文件正则分组不跨行 ---


def test_missing_file_name_does_not_swallow_newline() -> None:
    stem = detect_missing_package("File `a.sty' not found.\nFile `b.sty' not found.")
    assert stem == "a"


# --- L8：环境样例带 `Environment` 前缀，照抄可命中 ---


def test_undefined_environment_prefixed_sample_matches() -> None:
    hint = hint_for_text("! LaTeX Error: Environment equationn undefined.")
    assert hint is not None and hint.rule_id == "undefined_environment"


# --- 规则数口径保持实测 41 ---


def test_rule_count_stays_41() -> None:
    assert len(RULE_IDS) == 41
    assert len(RULE_IDS) == len(set(RULE_IDS))
