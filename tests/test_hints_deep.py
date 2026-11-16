"""PyTeXLogs 可执行建议（hints）的深度回归测试。"""

from pytexlogs import LogEntry, LogLevel
from pytexlogs.hints import detect_missing_package, hint_for_entry, hint_for_text


def test_unicode_character_suggests_xelatex_or_pack():
    hint = hint_for_text("! LaTeX Error: Unicode character α (U+03B1) not set up for use with LaTeX.")
    assert hint is not None
    assert hint.kind == "unicode"
    assert any("xelatex" in command for command in hint.commands)


def test_undefined_citation_gives_biber_and_bibtex():
    hint = hint_for_text("LaTeX Warning: Citation `Smith2020' on page 3 undefined on input line 42.")
    assert hint is not None and hint.kind == "undefined_citation"
    assert any("biber" in c for c in hint.commands)
    assert any("bibtex" in c for c in hint.commands)

    # parser 翻译后的展示文本也必须能命中，否则 CLI 摘要里的 warning 没有建议。
    localized = hint_for_text("找不到 citation `Smith2020`", jobname="main")
    assert localized is not None and localized.kind == "undefined_citation"
    assert localized.commands == ("biber main", "bibtex main")


def test_undefined_environment_and_reference():
    env = hint_for_text("! LaTeX Error: Environment tikzpicture undefined.")
    assert env is not None and env.kind == "undefined_environment"
    ref = hint_for_text("LaTeX Warning: Reference `sec:intro' on page 1 undefined.")
    assert ref is not None and ref.kind == "undefined_reference"


def test_missing_bib_database_command_not_duplicated():
    hint = hint_for_text("I couldn't open database file refs.bib")
    assert hint is not None and hint.kind == "missing_bib"
    assert hint.commands == ("kpsewhich refs.bib",)


def test_package_error_does_not_claim_missing_package():
    hint = hint_for_text('Package fontspec Error: The font "Times New Roman" cannot be found.')
    assert hint is not None
    assert hint.kind == "package_error"
    assert hint.commands == ()
    assert detect_missing_package('Package fontspec Error: The font "X" cannot be found.') is None


def test_missing_file_still_gives_install_commands():
    assert detect_missing_package("! LaTeX Error: File `siunitx.sty' not found.") == "siunitx"
    assert detect_missing_package(r"! LaTeX Error: File `C:\tex\siunitx.sty' not found.") == "siunitx"
    hint = hint_for_text("! LaTeX Error: File `siunitx.sty' not found.")
    assert hint is not None and hint.kind == "missing_package"
    assert "tlmgr install siunitx" in hint.commands


def test_missing_image_is_not_a_package():
    """缺图片不能被当成缺宏包，否则会给出 tlmgr install fig.png。"""
    text = "! LaTeX Error: File `fig.png' not found."
    assert detect_missing_package(text) is None
    hint = hint_for_text(text)
    assert hint is not None and hint.kind == "missing_graphic"
    assert not any("tlmgr" in c for c in hint.commands)
    assert any("kpsewhich fig.png" in c for c in hint.commands)


def test_missing_bib_file_is_classified_as_bib():
    """File `refs.bib' not found 应给文献库建议，而不是宏包安装命令。"""
    text = "! LaTeX Error: File `refs.bib' not found."
    assert detect_missing_package(text) is None
    hint = hint_for_text(text)
    assert hint is not None and hint.kind == "missing_bib"
    assert any("refs.bib" in c for c in hint.commands)


def test_hint_context_substitutes_real_jobname_and_root():
    """提示里的 <jobname>/<主文件> 要能用条目自带的文件信息替换。"""
    entry = LogEntry(
        level=LogLevel.ERROR,
        file="chapters/main.tex",
        line=7,
        text="LaTeX Warning: Citation `Smith2020' undefined on input line 7.",
    )
    hint = hint_for_entry(entry)
    assert hint is not None
    assert "biber main" in hint.commands
    assert "bibtex main" in hint.commands

    ref_entry = LogEntry(
        level=LogLevel.WARNING,
        file="chapters/main.tex",
        line=9,
        text="LaTeX Warning: Reference `sec:intro' undefined on input line 9.",
    )
    ref_hint = hint_for_entry(ref_entry)
    assert ref_hint is not None and any("main.tex" in c for c in ref_hint.commands)

    unicode_hint = hint_for_text(
        "! LaTeX Error: Unicode character α (U+03B1) not set up for use with LaTeX.",
        jobname="paper",
    )
    assert unicode_hint is not None
    assert "xelatex paper.tex" in unicode_hint.commands
    assert "lualatex paper.tex" in unicode_hint.commands
    assert not any("pytexmk" in c for c in unicode_hint.commands)


def test_utf8_hint_does_not_depend_on_pytexmk():
    hint = hint_for_text("! Invalid UTF-8 byte sequence.")
    assert hint is not None and hint.kind == "invalid_utf8"
    assert not any("pytexmk" in c for c in hint.commands)


def test_english_hint_text():
    """--lang en 时 hint 正文也要是英文，而不是只翻译摘要标题。"""
    pkg = hint_for_text("! LaTeX Error: File `siunitx.sty' not found.", language="en")
    assert pkg is not None and pkg.text.startswith("Missing package/class")

    localized = hint_for_text("找不到 citation `Smith2020`", language="en", jobname="main")
    assert localized is not None and "Citation key" in localized.text
    assert localized.commands == ("biber main", "bibtex main")

    log_hint = hint_for_text("Overfull \\hbox (12.3pt too wide)", language="en")
    assert log_hint is not None and "exceeds the text width" in log_hint.text


def test_runaway_and_capacity_hints():
    runaway = hint_for_text("Runaway argument? {\\bfseries x")
    assert runaway is not None and runaway.kind == "runaway"


def test_undefined_control_end_mismatch_and_encoding():
    control = hint_for_text("! Undefined control sequence.\nl.5 \\foo")
    assert control is not None and control.kind == "undefined_control"
    assert any("foo" in command for command in control.commands)

    end = hint_for_text("! LaTeX Error: \\begin{document} ended by \\end{itemize}.")
    assert end is not None and end.kind == "end_mismatch"

    utf8 = hint_for_text("! Invalid UTF-8 byte sequence.")
    assert utf8 is not None and utf8.kind == "invalid_utf8"


def test_table_and_number_hints():
    table = hint_for_text("! Extra alignment tab has been changed to \\cr.")
    assert table is not None and table.kind == "alignment_tab"

    number = hint_for_text("! Missing number, treated as zero.")
    assert number is not None and number.kind == "missing_number"

    item = hint_for_text("! LaTeX Error: Something's wrong--perhaps a missing \\item.")
    assert item is not None and item.kind == "missing_item"
    fatal = hint_for_text("! Emergency stop.")
    assert fatal is not None and fatal.kind == "fatal"
