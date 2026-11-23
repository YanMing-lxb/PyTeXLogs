"""误报边界：良性文本、工具作用域与项目上下文替换。

这里锁定两类“不能抢答”的行为：
- 普通排版提示、Info 行、被引用讨论的样例字符串不得命中具体规则；
- 旧提示表与 biber 专项规则按工具隔离，LaTeX 日志不能套用 Biber/BibTeX 语义。
"""

from pytexlogs import LogEntry, LogLevel
from pytexlogs.hints import hint_for_entry, hint_for_text


def test_overfull_is_generic_log_hint_not_specific_rule() -> None:
    hint = hint_for_text("Overfull \\hbox (243.09511pt too wide) detected at line 3")
    assert hint is not None
    assert hint.rule_id == "log_hint"
    assert hint.kind == "log_hint"


def test_hyperref_info_line_does_not_match_pdf_string_rule() -> None:
    hint = hint_for_text("Package hyperref Info: Loading driver `hyperref.cyriz.sty'.")
    assert hint is None


def test_quoted_option_clash_string_is_not_matched() -> None:
    # 前有 ``> `` 引用符：这是在讨论样例，不是真实日志。
    hint = hint_for_text("> Option clash for package graphicx.")
    assert hint is None


def test_quoted_missing_character_string_is_not_matched() -> None:
    hint = hint_for_text("> Missing character: There is no 中 in font cmr10!")
    assert hint is None


def test_plain_benign_text_returns_none() -> None:
    assert hint_for_text("Transcript written on main.log.") is None
    assert hint_for_text("This is pdfTeX, Version 3.141592653-2.6-1.40.25") is None


def test_latex_text_does_not_match_biber_warn_table() -> None:
    hint = hint_for_text("WARN - check this", tool_name="latex")
    assert hint is None


def test_biber_warn_matches_biber_table() -> None:
    hint = hint_for_text("WARN - I didn't find a database entry for 'x'", tool_name="biber")
    assert hint is not None
    assert hint.kind == "log_hint"


def test_biber_case_mismatch_only_for_biber_tool() -> None:
    text = "WARN - Case mismatch: key `Smith' vs `smith' in refs.bib"
    biber_hint = hint_for_text(text, tool_name="biber")
    assert biber_hint is not None
    assert biber_hint.rule_id == "biber_case_mismatch"
    assert biber_hint.kind == "biber_key_case"

    latex_hint = hint_for_text(text, tool_name="latex")
    assert latex_hint is None


def test_bibtex_runaway_is_scoped_out() -> None:
    # round7 收窄：runaway 是 LaTeX 专属规则，bibtex 后端日志下不命中；
    # 旧口径（bibtex 下保留通用建议、不套 LaTeX 专属命令）已按用户要求废弃。
    hint = hint_for_text("File ended while scanning use of \\foo.", tool_name="bibtex")
    assert hint is None


def test_context_substitutes_project_jobname() -> None:
    hint = hint_for_text(
        "LaTeX Warning: Citation `Smith2020' undefined on input line 7.",
        jobname="main",
        root_file="main.tex",
    )
    assert hint is not None
    assert hint.commands == ("biber main", "bibtex main")


def test_subfile_entry_does_not_become_main_file() -> None:
    entry = LogEntry(
        level=LogLevel.WARNING,
        file="chapters/intro.tex",
        line=3,
        text="LaTeX Warning: Citation `Smith2020' undefined on input line 3.",
    )
    hint = hint_for_entry(entry, jobname="main", root_file="main.tex")
    assert hint is not None
    assert hint.commands == ("biber main", "bibtex main")
    assert not any("intro" in c for c in hint.commands)


def test_missing_bbl_substitutes_jobname_in_commands() -> None:
    hint = hint_for_text("No file main.bbl.", jobname="main", root_file="main.tex")
    assert hint is not None
    assert hint.commands == ("biber main", "bibtex main")
