"""第 7 轮（round7 任务 14 / 15）：missing_bbl 文案修正与英文命令本地化。

- 任务 14：`No file *.bbl` 分支才说 `.bbl` 缺失；`Please (re)run Biber` 分支只说
  后端尚未完成；中文两句不重复；英文无 jobname 时不得出现 `<jobname>.bbl is missing`。
- 任务 15：`--lang en` 返回的命令不得含中文，也不得残留中文槽位；`lang=zh` 的
  中文文案/命令保持不变。
"""

import re

import pytest

from pytexlogs.hints import hint_for_text

CJK_RE = re.compile(r"[一-鿿　-ヿ＀-￯]")
#: 英文命令中不允许出现的中文槽位（`<main file>` / `<engine>` 等英文槽位除外）。
ZH_SLOTS = (
    "<主文件>",
    "<引擎>",
    "<含该字的中文字体>",
    "<选项>",
    "<TeX 版>",
    "<纯文本>",
    "<LaTeX 写法>",
)


# --- 任务 14：missing_bbl 文案 ---


def test_missing_bbl_no_file_zh_has_no_duplicated_sentence() -> None:
    hint = hint_for_text("No file main.bbl.", jobname="main", language="zh")
    assert hint is not None
    assert hint.rule_id == "missing_bbl"
    assert "未找到 `main.bbl`" in hint.text
    # 开头短语与正文首句不得整句重复。
    assert "后端还没有成功跑过：后端还没有成功跑过" not in hint.text
    assert hint.text.count("文献后端还没有成功跑过") == 1


def test_missing_bbl_no_file_english_says_missing() -> None:
    hint = hint_for_text("No file main.bbl.", jobname="main", language="en")
    assert hint is not None
    assert "main.bbl" in hint.text_en
    assert "is missing" in hint.text_en


def test_missing_bbl_rerun_zh_has_no_duplicated_sentence() -> None:
    hint = hint_for_text(
        "Package biblatex Warning: Please (re)run Biber on the file:",
        language="zh",
    )
    assert hint is not None
    assert hint.rule_id == "missing_bbl"
    assert "后端还没有成功跑过：后端还没有成功跑过" not in hint.text
    assert hint.text.count("文献后端还没有成功跑过") == 1


def test_missing_bbl_rerun_english_does_not_claim_bbl_missing() -> None:
    hint = hint_for_text(
        "Package biblatex Warning: Please (re)run Biber on the file:",
        language="en",
    )
    assert hint is not None
    # 触发消息里没有 .bbl 文件名：英文不得断言 ".bbl is missing"，也不得拼出
    # `<jobname>.bbl` 这种文件名槽位；编译顺序说明里的 `<jobname>` 由上下文回填。
    assert "is missing" not in hint.text_en
    assert "<jobname>.bbl" not in hint.text_en
    assert "backend has not completed" in hint.text_en


@pytest.mark.parametrize("jobname", [None, "main"])
def test_missing_bbl_rerun_english_no_bbl_placeholder(jobname: str | None) -> None:
    hint = hint_for_text(
        "Package biblatex Warning: Please (re)run Biber on the file:",
        jobname=jobname,
        language="en",
    )
    assert hint is not None
    assert "<jobname>.bbl" not in hint.text_en
    assert ".bbl" not in hint.text_en.split("backend", 1)[0]


# --- 任务 15：英文命令无中文 / 无中文槽位 ---


#: (标签, 触发文本, 工具, 主文件, 期望规则 id, 英文命令必含子串)
EN_COMMAND_CASES: list[tuple[str, str, str, str | None, str, str | None]] = [
    (
        "undefined_reference",
        "LaTeX Warning: Reference `sec:intro' undefined",
        "xelatex",
        "paper.tex",
        "undefined_reference",
        "xelatex paper.tex",
    ),
    (
        "missing_glyph cjk xe",
        "Missing character: There is no 中 (U+4E2D) in font [lmroman10-regular]:mapping=tex-text;!",
        "xelatex",
        None,
        "missing_glyph",
        "<CJK font containing the glyph>",
    ),
    (
        "missing_glyph cjk pdflatex",
        "Missing character: There is no 中 (U+4E2D) in font cmr10!",
        "pdflatex",
        None,
        "missing_glyph",
        "<main file>",
    ),
    (
        "missing_glyph symbol",
        "Missing character: There is no α in font cmr10!",
        "pdflatex",
        None,
        "missing_glyph",
        "<LaTeX command>",
    ),
    (
        "unicode cjk",
        "Unicode character 中 (U+4E2D) not set up for use with LaTeX.",
        "pdflatex",
        None,
        "unicode",
        "<main file>",
    ),
    (
        "fontset",
        "CTeX fontset 'fandol' is unavailable in current mode.",
        "pdflatex",
        None,
        "fontset_unavailable",
        "<main file>",
    ),
    (
        "option_clash",
        "! LaTeX Error: Option clash for package graphicx.",
        "pdflatex",
        None,
        "option_clash",
        "<option>",
    ),
    (
        "pdf_string",
        "Package hyperref Warning: Token not allowed in a PDF string (Unicode):",
        "pdflatex",
        None,
        "hyperref_pdf_string",
        "<TeX version>",
    ),
    (
        "invalid_utf8",
        "! Package inputenc Error: Invalid UTF-8 byte sequence.",
        "pdflatex",
        None,
        "invalid_utf8",
        "<main file>",
    ),
    (
        "missing_bbl",
        "No file main.bbl.",
        "pdflatex",
        "main.tex",
        "missing_bbl",
        "biber main",
    ),
    (
        "tfm_font_missing",
        "! Font T1/cmr/m/n/10=ecrm1000 at 10pt not loadable: Metric (TFM) file ecrm1000.tfm not found.",
        "pdflatex",
        None,
        "tfm_font_missing",
        None,
    ),
    (
        "font_not_loadable",
        "! Font \\foo=NoSuchFont at 10.0pt not loadable: Metric (TFM) file not found.",
        "pdflatex",
        None,
        "font_not_loadable",
        None,
    ),
    (
        "package_error",
        "! Package hyperref Error: Wrong driver.",
        "pdflatex",
        None,
        "package_error",
        None,
    ),
]


@pytest.mark.parametrize(("label", "text", "tool", "root", "rule_id", "substr"), EN_COMMAND_CASES)
def test_english_commands_have_no_cjk_or_zh_slot(
    label: str,
    text: str,
    tool: str,
    root: str | None,
    rule_id: str,
    substr: str | None,
) -> None:
    hint = hint_for_text(text, tool_name=tool, root_file=root, language="en")
    assert hint is not None, label
    assert hint.rule_id == rule_id, label
    joined = " ".join(hint.commands)
    assert not CJK_RE.search(joined), f"{label} 英文命令含中文: {hint.commands}"
    for slot in ZH_SLOTS:
        assert slot not in joined, f"{label} 英文命令残留中文槽位 {slot}: {hint.commands}"
    if substr is not None:
        assert substr in joined, f"{label} 英文命令缺 {substr!r}: {hint.commands}"


def test_undefined_reference_english_command_drops_chinese_comment() -> None:
    hint = hint_for_text(
        "Reference `sec:intro' undefined",
        tool_name="xelatex",
        root_file="paper.tex",
        language="en",
    )
    assert hint is not None
    joined = " ".join(hint.commands)
    assert "#" not in joined
    assert "用当前引擎再跑一轮" not in joined


def test_chinese_commands_keep_zh_slots_and_comment() -> None:
    """lang=zh 的命令保持原样，不被英文化回填破坏。"""
    ref = hint_for_text("Reference `sec:intro' undefined", root_file="paper.tex")
    assert ref is not None
    assert "用当前引擎再跑一轮" in " ".join(ref.commands)

    glyph = hint_for_text(
        "Missing character: There is no 中 (U+4E2D) in font [lmroman]:mapping=tex-text;!",
        tool_name="xelatex",
    )
    assert glyph is not None
    assert "<含该字的中文字体>" in " ".join(glyph.commands)

    clash = hint_for_text("! LaTeX Error: Option clash for package graphicx.")
    assert clash is not None
    assert "<选项>" in " ".join(clash.commands)

    pdf = hint_for_text("Package hyperref Warning: Token not allowed in a PDF string (Unicode):")
    assert pdf is not None
    assert "<TeX 版>" in " ".join(pdf.commands)
    assert "<纯文本>" in " ".join(pdf.commands)
