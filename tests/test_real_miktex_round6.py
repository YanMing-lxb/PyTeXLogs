"""第 6 轮真实 MiKTeX 日志回归（round6-real-miktex.md 证据对应）。

所有 fixture 均为本机 MiKTeX 26.5 Portable 真实编译产出（不是合成正则玩具串），
采集命令与工作目录见 ``docs/hints-research/round6-real-miktex.md``。

覆盖场景：
- B1：XeLaTeX + fontspec 找不到字族（3 个独立字形请求块 + 一条 Font not loadable）；
- B2：``\\newcommand{dice}`` 真实首错是 ``Missing \\begin{document}``，连锁不报
  ``undefined_control``；
- B3a：pdflatex + ctex ``fontset=adobe`` 续行括号前缀的 fontset 不可用；
- B3b：xeCJK 配拉丁字体，无 ``(U+XXXX)`` 后缀的真实缺字形消息；
- B3c：biber ``.blg`` 引用键大小写不匹配（含 ``[pid] file:line>`` 位置前缀）；
- B3d：LaTeX 未定义 Citation/Reference 警告（反引号/直引号/双引号兼容）；
- L1/L2：LuaLaTeX 缺字族（``metric data not found or bad``）与带码位的缺字形聚合；
- B1-bbl：biblatex 首遍 ``No file main.bbl.`` / rerun Biber 归 ``missing_bbl``；
- B2-chain：pdflatex → biber → pdflatex 端到端状态转换（首遍 / .blg / 完成态）。
"""

from pathlib import Path

import pytest

from pytexlogs.hints import hint_for_entry, hint_for_text
from pytexlogs.parsers.biber import BiberParser
from pytexlogs.parsers.latex import LatexLogParser

FIXTURES = Path(__file__).parent / "fixtures" / "real_miktex"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8", errors="replace")


def _rules(entries, tool: str) -> list[str]:
    """逐条条目给出 hint rule_id；未命中记 ``-``。"""
    rules: list[str] = []
    for entry in entries:
        hint = hint_for_entry(entry, tool_name=tool)
        rules.append(hint.rule_id if hint else "-")
    return rules


# --------------------------------------------------------------------- B1


def test_b1_fontspec_three_independent_error_blocks_kept() -> None:
    """3 个 ``Package fontspec Error`` 是 regular/BI/B/I 独立请求，不是重复入队。

    解析层/hints 层都不得去重：条目数必须与真实错误块数一致；
    此处允许同一字体族，但 3 个块都必须保留并命中 fontspec_font_not_found。
    """
    parsed = LatexLogParser(root_file="main.tex").parse(_read("xelatex_fontspec_not_found.log"))
    fontspec_entries = [e for e in parsed.entries if "Package fontspec Error" in e.text]
    assert len(fontspec_entries) == 3
    for entry in fontspec_entries:
        hint = hint_for_entry(entry, tool_name="xelatex")
        assert hint is not None
        assert hint.rule_id == "fontspec_font_not_found"
    # 原始日志里 BI/B/I 三个变体解析记录也都在。
    raw = _read("xelatex_fontspec_not_found.log")
    assert "NoSuchFontFamilyXYZ/BI" in raw
    assert "NoSuchFontFamilyXYZ/B" in raw
    assert "NoSuchFontFamilyXYZ/I" in raw


def test_b1_font_not_loadable_nfss_spec_no_tfm_false_positive() -> None:
    """``Font TU/Family(0)/m/n/10=Family ... not loada\\nble`` 命中 font_not_loadable。

    - 规格提取真实字族 ``NoSuchFontFamilyXYZ``；
    - 不得落到 tfm_font_missing，不得抽出 ``or.tfm``；
    - XeLaTeX 文案不得写死 pdflatex / ec 字体包建议。
    """
    parsed = LatexLogParser(root_file="main.tex").parse(_read("xelatex_fontspec_not_found.log"))
    loadable = [e for e in parsed.entries if "not loada" in e.text or "not loadable" in e.text]
    assert len(loadable) == 1
    entry = loadable[0]
    hint = hint_for_entry(entry, tool_name="xelatex")
    assert hint is not None
    assert hint.rule_id == "font_not_loadable"
    assert "NoSuchFontFamilyXYZ" in hint.text
    assert "or.tfm" not in hint.text
    assert "pdflatex" not in hint.text.lower()
    # 整条日志不得有 tfm_font_missing 误命中。
    assert "tfm_font_missing" not in _rules(parsed.entries, "xelatex")
    # Xe/Lua 的 installed-font 变体不走 kpsewhich *.tfm。
    assert not any("tfm" in c for c in hint.commands)


# --------------------------------------------------------------------- B2


def test_b2_real_first_error_missing_begin_document_no_undefined_control() -> None:
    """真实 ``\\newcommand{dice}`` 首错是 Missing \\begin{document}，连锁不报未定义命令。

    注意：``tests/test_hints_round6.py`` 里的 ``\\newcommand{dice}`` 用例是合成错误帧，
    只验证“定义包装命令不被报成未定义”，不等于真实编译首错；真实链条见本 fixture。
    """
    parsed = LatexLogParser(root_file="main.tex").parse(_read("pdflatex_newcommand_dice.log"))
    rules = _rules(parsed.entries, "pdflatex")
    assert rules[0] == "missing_begin_document"
    # 连锁的 Missing number / Illegal unit 等不得被识别成 undefined_control。
    assert "undefined_control" not in rules
    first = parsed.entries[0]
    assert "Missing \\begin{document}" in first.text


# --------------------------------------------------------------------- B3a


def test_b3a_ctex_fontset_continuation_prefix_matches() -> None:
    """``... in current\\n(ctex) mode.`` 续行前缀不得打断 fontset_unavailable。"""
    parsed = LatexLogParser(root_file="main.tex").parse(_read("pdflatex_ctex_adobe_fontset.log"))
    fontset = [e for e in parsed.entries if "fontset" in e.text.lower() and "unavailable" in e.text]
    assert len(fontset) == 1
    hint = hint_for_entry(fontset[0], tool_name="pdflatex")
    assert hint is not None
    assert hint.rule_id == "fontset_unavailable"
    assert "adobe" in hint.text
    assert hint.rule_id != "package_error"


# --------------------------------------------------------------------- B3b


def test_b3b_xecjk_missing_glyph_no_codepoint_suffix() -> None:
    """xeCJK 配拉丁字体：真实 ``Missing character`` 无 ``(U+XXXX)`` 后缀。"""
    parsed = LatexLogParser(root_file="main.tex").parse(_read("xelatex_xecjk_missing_glyph.log"))
    glyph = [e for e in parsed.entries if "Missing character" in e.text]
    assert glyph, "折行的缺字形消息必须被解析成条目"
    rules = _rules(glyph, "xelatex")
    assert "missing_glyph" in rules
    glyph_index = rules.index("missing_glyph")
    entry = glyph[glyph_index]
    hint = hint_for_entry(entry, tool_name="xelatex")
    assert hint is not None
    assert "中" in hint.text
    assert "Latin Modern Roman" in hint.text
    # 不是 nullfont 连锁分支。
    assert "nullfont" not in entry.text


# --------------------------------------------------------------------- B3c


def test_b3c_biber_case_mismatch_blg_prefix_stripped() -> None:
    """.blg 带 ``[220] Biber.pm:132> `` 前缀；大小写不匹配命中 biber_case_mismatch。"""
    parsed = BiberParser(root_file="main.tex").parse(_read("biber_case_mismatch.blg"))
    assert len(parsed.entries) == 2
    by_text = {e.text: e for e in parsed.entries}
    case_entry = next(e for e in parsed.entries if "case mismatch" in e.text)
    case_hint = hint_for_entry(case_entry, tool_name="biber")
    assert case_hint is not None
    assert case_hint.rule_id == "biber_case_mismatch"
    assert "Key" in case_entry.text and "key" in case_entry.text
    # 缺条目告警在 biber 工具下走 biber 旧表（log_hint），不得被 undefined_citation 抢答。
    missing_entry = next(e for e in parsed.entries if "database entry" in e.text)
    missing_hint = hint_for_entry(missing_entry, tool_name="biber")
    assert missing_hint is not None
    assert missing_hint.rule_id != "undefined_citation"
    assert missing_hint.rule_id != "undefined_reference"
    # 整条 biber 日志不得出现 undefined_citation / undefined_reference。
    assert "undefined_citation" not in _rules(parsed.entries, "biber")
    assert "undefined_reference" not in _rules(parsed.entries, "biber")
    assert by_text  # 防未使用告警


# --------------------------------------------------------------------- B3d


def test_b3d_undefined_citation_reference_quotes() -> None:
    """反引号传统写法在本机真实日志命中；直引号/双引号变体由正则兼容。"""
    parsed = LatexLogParser(root_file="main.tex").parse(_read("pdflatex_undefined_cite_ref.log"))
    rules = _rules(parsed.entries, "pdflatex")
    assert "undefined_citation" in rules
    assert "undefined_reference" in rules

    cite = hint_for_text("LaTeX Warning: Citation 'key' on page 1 undefined.", tool_name="pdflatex")
    assert cite is not None and cite.rule_id == "undefined_citation"
    assert "key" in cite.text

    ref = hint_for_text('LaTeX Warning: Reference "sec:intro" on page 1 undefined.', tool_name="pdflatex")
    assert ref is not None and ref.rule_id == "undefined_reference"
    assert "sec:intro" in ref.text


# ------------------------------------------------------- hint 层合成加固用例


def test_wrapped_loadable_nfss_spec_synthetic() -> None:
    """合成：79 列折行 ``loada\\nble`` + NFSS 规格，显式 .tfm 仍归 tfm_font_missing。"""
    text = (
        "Font TU/NoSuchFontFamilyXYZ(0)/m/n/10=NoSuchFontFamilyXYZ at 10.0pt "
        "not loada\nble: Metric (TFM) file or installed font not found."
    )
    hint = hint_for_text(text, tool_name="xelatex")
    assert hint is not None
    assert hint.rule_id == "font_not_loadable"
    assert "NoSuchFontFamilyXYZ" in hint.text

    explicit_tfm = "! Font T1/cmr/m/n/10=ecrm1000 at 10pt not loadable: Metric (TFM) file ecrm1000.tfm not found."
    tfm_hint = hint_for_text(explicit_tfm, tool_name="pdflatex")
    assert tfm_hint is not None
    assert tfm_hint.rule_id == "tfm_font_missing"
    assert "ecrm1000.tfm" in tfm_hint.text


def test_fontset_continuation_prefix_synthetic() -> None:
    text = (
        "! Critical Package ctex Error: CTeX fontset `adobe' is unavailable in current\n"
        "(ctex)                         mode."
    )
    hint = hint_for_text(text, tool_name="pdflatex")
    assert hint is not None
    assert hint.rule_id == "fontset_unavailable"
    assert "adobe" in hint.text


def test_missing_glyph_symbol_no_codepoint() -> None:
    """无码位后缀的符号缺字形（xeCJK/部分引擎不打印 U+XXXX）。"""
    text = "Missing character: There is no ✓ in font Latin Modern Roman 10 Regular/OT:script=latn;language=dflt;!"
    hint = hint_for_text(text, tool_name="xelatex")
    assert hint is not None
    assert hint.rule_id == "missing_glyph"
    assert "✓" in hint.text


# ----------------------------------------------------------------- L1 Lua


def test_l1_lualatex_fontspec_not_found() -> None:
    """LuaLaTeX 缺字族：3 个独立 fontspec 块 + 一条 metric data not loadable。"""
    parsed = LatexLogParser(root_file="main.tex").parse(_read("lualatex_fontspec_not_found.log"))
    spec_entries = [e for e in parsed.entries if "Package fontspec Error" in e.text]
    assert len(spec_entries) == 3
    for entry in spec_entries:
        hint = hint_for_entry(entry, tool_name="lualatex")
        assert hint is not None
        assert hint.rule_id == "fontspec_font_not_found"

    loadable = [e for e in parsed.entries if "not loadable" in e.text or "not loada" in e.text]
    assert len(loadable) == 1
    hint = hint_for_entry(loadable[0], tool_name="lualatex")
    assert hint is not None
    assert hint.rule_id == "font_not_loadable"
    assert "NoSuchFontFamilyXYZ" in hint.text
    assert "or.tfm" not in hint.text
    assert "pdflatex" not in hint.text.lower()
    assert any("fc-list" in cmd for cmd in hint.commands)
    assert any("luaotfload-tool" in cmd for cmd in hint.commands)
    assert not any("tfm" in cmd for cmd in hint.commands)
    assert "tfm_font_missing" not in _rules(parsed.entries, "lualatex")


# ----------------------------------------------------------------- L2 Lua


def test_l2_lualatex_missing_glyph_codepoint_retained() -> None:
    """LuaLaTeX 缺字形：重复条目按字体聚合，码位 (U+4E2D) 随条目保留。"""
    parsed = LatexLogParser(root_file="main.tex").parse(_read("lualatex_xecjk_missing_glyph.log"))
    glyph = [e for e in parsed.entries if "Missing character" in e.text]
    assert glyph
    rules = _rules(glyph, "lualatex")
    assert "missing_glyph" in rules
    entry = glyph[rules.index("missing_glyph")]
    hint = hint_for_entry(entry, tool_name="lualatex")
    assert hint is not None
    assert "中" in hint.text
    assert "4E2D" in hint.text
    assert "Latin Modern Roman" in hint.text
    assert "U+4E2D" in entry.text
    # 字体 spec 规范化：建议文案不塞 name: 前缀与 mode/script/language 参数；
    # 原始 spec 仍留在条目文本里。
    assert "name:" not in hint.text
    assert "mode=node" not in hint.text
    # 已在 LuaLaTeX：不再建议换引擎，命令里不出现引擎二进制或换引擎前提。
    assert not any("xelatex" in c or "lualatex" in c for c in hint.commands)
    assert "若还在 pdfLaTeX" not in hint.text
    # 同一字体的 12 条重复缺字形聚合为一条，不逐条刷屏。
    lm_entries = [e for e in glyph if "Latin Modern Roman" in e.text]
    assert len(lm_entries) == 1


_SPEC_GLYPH = (
    'Missing character: There is no 中 (U+4E2D) in font "name:Latin Modern Roman:mode=node;script=latn;language=dflt;"!'
)


def test_missing_glyph_xelatex_no_engine_switch() -> None:
    """XeLaTeX 上下文：只建议换 CJK 字体，不给硬编码 xelatex 换引擎命令。"""
    hint = hint_for_text(_SPEC_GLYPH, tool_name="xelatex")
    assert hint is not None and hint.rule_id == "missing_glyph"
    assert "Latin Modern Roman" in hint.text
    assert "中" in hint.text and "4E2D" in hint.text
    assert not any("xelatex" in c or "lualatex" in c for c in hint.commands)
    assert not any("主文件" in c for c in hint.commands)
    assert "若还在 pdfLaTeX" not in hint.text


def test_missing_glyph_pdflatex_keeps_engine_switch() -> None:
    """pdflatex / 未知上下文：保留两步排查与换引擎建议（引擎不写死单一）。"""
    hint = hint_for_text(_SPEC_GLYPH, tool_name="pdflatex")
    assert hint is not None and hint.rule_id == "missing_glyph"
    assert "\\usepackage{ctex}" in hint.commands
    assert "XeLaTeX" in hint.text and "LuaLaTeX" in hint.text
    # 编译命令给出两个可选引擎，不是单一 xelatex。
    assert any("XeLaTeX/LuaLaTeX" in c for c in hint.commands)


# ------------------------------------------------- B1-bbl 首遍缺 .bbl


def test_biblatex_first_pass_missing_bbl_not_preempted_by_citation() -> None:
    """首遍未跑 biber：``No file main.bbl.`` 与 rerun Biber 均归 missing_bbl。"""
    parsed = LatexLogParser(root_file="main.tex").parse(_read("pdflatex_biblatex_before_biber.log"))
    bbl = [e for e in parsed.entries if "No file main.bbl" in e.text]
    assert len(bbl) == 1
    bbl_hint = hint_for_entry(bbl[0], tool_name="pdflatex")
    assert bbl_hint is not None
    assert bbl_hint.rule_id == "missing_bbl"

    rerun = [e for e in parsed.entries if "run biber" in e.text.lower()]
    assert rerun
    rerun_hint = hint_for_entry(rerun[0], tool_name="pdflatex")
    assert rerun_hint is not None
    assert rerun_hint.rule_id == "missing_bbl"

    # undefined_citation 作为独立条目存在，但 bbl 条目本身不得被它抢答。
    assert "undefined_citation" in _rules(parsed.entries, "pdflatex")


def test_after_biber_completed_missing_bbl_gone() -> None:
    """跑完 biber 并收敛后的完成态日志：无 missing_bbl、无未定义引用。"""
    parsed = LatexLogParser(root_file="main.tex").parse(_read("pdflatex_biber_chain_final.log"))
    rules = _rules(parsed.entries, "pdflatex")
    assert "missing_bbl" not in rules
    assert "undefined_citation" not in rules


# ------------------------------------------------- B2 端到端链路


def test_biber_chain_pass1_blg_final_state_transition() -> None:
    """端到端：首遍 .log → .blg → 完成态 .log 的规则与工具作用域。"""
    pass1 = LatexLogParser(root_file="main.tex").parse(_read("pdflatex_biber_chain_pass1.log"))
    pass1_rules = _rules(pass1.entries, "pdflatex")
    assert "missing_bbl" in pass1_rules
    assert "undefined_citation" in pass1_rules

    blg = BiberParser(root_file="main.tex").parse(_read("biber_chain.blg"))
    blg_rules = [
        hint_for_entry(e, tool_name="biber").rule_id if hint_for_entry(e, tool_name="biber") else "-"
        for e in blg.entries
    ]
    assert "undefined_citation" not in blg_rules
    assert "undefined_reference" not in blg_rules

    final = LatexLogParser(root_file="main.tex").parse(_read("pdflatex_biber_chain_final.log"))
    final_rules = _rules(final.entries, "pdflatex")
    assert "missing_bbl" not in final_rules
    assert "undefined_citation" not in final_rules


# ------------------------------------------------- hint 层合成加固


def test_lua_wrapped_loadable_synthetic() -> None:
    """合成：``\\TU/...=name:...:mode=node;`` 折行 + metric data not found or bad。"""
    text = (
        "Font \\TU/Family(0)/m/n/10=name:Family:mode=node;language=dflt; "
        "at 10pt not loadable: metric data not found or bad."
    )
    hint = hint_for_text(text, tool_name="lualatex")
    assert hint is not None
    assert hint.rule_id == "font_not_loadable"
    assert "Family" in hint.text
    assert any("luaotfload-tool" in cmd for cmd in hint.commands)


def test_rerun_biber_message_missing_bbl_synthetic() -> None:
    """合成：biblatex ``Please (re)run Biber on the file:`` 归 missing_bbl。"""
    text = "Package biblatex Warning: Please (re)run Biber on the file:"
    hint = hint_for_text(text, tool_name="pdflatex")
    assert hint is not None
    assert hint.rule_id == "missing_bbl"
    assert "biber" in " ".join(hint.commands).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
