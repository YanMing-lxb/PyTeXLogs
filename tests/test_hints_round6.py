"""第 6 轮 hints 规则修复（round6 P0-1 / P0-2）回归。

P0-1：``undefined_control`` 不得把 ``\\newcommand``/``\\def`` 等定义包装命令报成
未定义命令，也不得给出 ``newcommand.sty`` 之类的安装命令；应提取被定义的裸名称。

P0-2：``fontspec_font_not_found`` 按“字体名 / 文件名”两种模式分支给建议；
``luaotfload-tool --update`` 只在 LuaLaTeX 上下文给出。
"""

import pytest

from pytexlogs.hints import hint_for_text

# --- P0-1：定义命令裸名称提取 ---


DEFINITION_CASES = [
    # (日志 l.N 行片段, 包装命令, 修法示例)
    (r"\newcommand{dice}", "newcommand", r"\newcommand{\dice}{...}"),
    (r"\newcommand*{dice}", "newcommand", r"\newcommand*{\dice}{...}"),
    (r"\newcommand\dice", "newcommand", r"\newcommand{\dice}{...}"),
    (r"\def\dice", "def", r"\def\dice{...}"),
    (r"\newenvironment{dice}", "newenvironment", r"\newenvironment{\dice}{...}{...}"),
    (r"\renewcommand{dice}", "renewcommand", r"\renewcommand{\dice}{...}"),
    (r"\providecommand{dice}", "providecommand", r"\providecommand{\dice}{...}"),
]


@pytest.mark.parametrize(("line", "wrapper", "example"), DEFINITION_CASES)
def test_undefined_definition_extracts_bare_name(line: str, wrapper: str, example: str) -> None:
    text = f"! Undefined control sequence.\nl.2 {line}"
    hint = hint_for_text(text)
    assert hint is not None
    assert hint.rule_id == "undefined_control"
    # 被定义的裸名称 \dice 必须出现在中文与英文文案里。
    assert r"`\dice`" in hint.text
    assert r"\dice" in hint.text_en
    # 不再报包装命令为未定义，也不给 .sty 安装命令。
    assert ".sty" not in " ".join(hint.commands)
    assert not any("tlmgr" in c for c in hint.commands)
    # 修法示例按实际宏类型给出。
    assert example in hint.text
    # grep 命令只指向真实名称。
    assert any(r"\dice" in c for c in hint.commands)
    assert wrapper not in " ".join(hint.commands)


def test_undefined_definition_continuation_line() -> None:
    # l.N 行折行：定义命令出现在紧随的续行上，同样要提取裸名称。
    text = "! Undefined control sequence.\nl.2\n\\newcommand{dice}"
    hint = hint_for_text(text)
    assert hint is not None
    assert hint.rule_id == "undefined_control"
    assert r"`\dice`" in hint.text
    assert ".sty" not in " ".join(hint.commands)


def test_undefined_control_plain_command_keeps_legacy_behavior() -> None:
    # 回归：普通未定义命令仍走原逻辑，保留 tlmgr 查找建议。
    text = "! Undefined control sequence.\nl.3 Hello \\undefinedcmd\n                        world."
    hint = hint_for_text(text)
    assert hint is not None
    assert hint.rule_id == "undefined_control"
    assert "undefinedcmd" in hint.text
    assert any("undefinedcmd" in c for c in hint.commands)
    assert any("tlmgr" in c and "undefinedcmd.sty" in c for c in hint.commands)


# --- P0-1 反例：定义构造之后还有控制序列时，优先报后者 ---


DEFINITION_OVERRIDED_CASES = [
    # (日志 l.N 行片段, 被定义宏名, 真正未定义命令)
    (r"\newcommand{\foo} \badcmd", "foo", "badcmd"),
    (r"\def\foo{bar} \badcmd", "foo", "badcmd"),
    (r"\newcommand{dice} \badcmd", "dice", "badcmd"),
]


@pytest.mark.parametrize(("line", "defined", "broken"), DEFINITION_OVERRIDED_CASES)
def test_definition_with_trailing_command_reports_later_control(line: str, defined: str, broken: str) -> None:
    text = f"! Undefined control sequence.\nl.2 {line}"
    hint = hint_for_text(text)
    assert hint is not None
    assert hint.rule_id == "undefined_control"
    # 构造之后还有控制序列：报后者，不再报定义语法笔误。
    assert rf"`\{broken}`" in hint.text
    assert "看起来是在定义" not in hint.text
    commands = " ".join(hint.commands)
    assert broken in commands
    assert defined not in commands
    assert "newcommand.sty" not in commands


def test_definition_continuation_with_trailing_command_reports_later_control() -> None:
    # 续行上的定义构造 + 后续命令：同样取后续命令 \badcmd。
    text = "! Undefined control sequence.\nl.2\n\\newcommand{dice} \\badcmd"
    hint = hint_for_text(text)
    assert hint is not None
    assert hint.rule_id == "undefined_control"
    assert r"`\badcmd`" in hint.text
    assert "看起来是在定义" not in hint.text
    assert "dice" not in " ".join(hint.commands)


# --- P0-2：fontspec 名称 / 文件名双分支 ---


def test_fontspec_name_mode_plain_family() -> None:
    hint = hint_for_text('! Package fontspec Error: The font "NoSuchFontFamilyXYZ" cannot be found.')
    assert hint is not None
    assert hint.rule_id == "fontspec_font_not_found"
    assert hint.kind == "missing_font_family"
    # 名称模式：fc-list 核对全名；命令整体加引号，名称不被 shell 断词。
    assert any("fc-list" in c and '"NoSuchFontFamilyXYZ"' in c for c in hint.commands)
    assert not any("kpsewhich" in c for c in hint.commands)
    # 默认（未知引擎）不无条件给 luaotfload 缓存命令。
    assert not any("luaotfload" in c for c in hint.commands)
    # 名称模式提示 macOS + TEXMF 树内字体在 XeTeX 下只能按文件名加载。
    assert "macOS" in hint.text
    assert "macOS" in hint.text_en
    assert "NoSuchFontFamilyXYZ" in hint.text_en


def test_fontspec_name_mode_spaced_family_quoted() -> None:
    hint = hint_for_text('! Package fontspec Error: The font "Times New Roman" cannot be found.')
    assert hint is not None
    # 含空格的族名必须整体引用，避免 shell 把 “Times”/“New”/“Roman” 断成三段。
    commands = " ".join(hint.commands)
    assert 'grep -iF "Times New Roman"' in commands
    assert "Times New Roman" in hint.text
    assert "Times New Roman" in hint.text_en


def test_fontspec_file_mode_otf() -> None:
    hint = hint_for_text('! Package fontspec Error: The font "MyFont.otf" cannot be found.')
    assert hint is not None
    assert hint.rule_id == "fontspec_font_not_found"
    # 文件名模式：kpsewhich 核对文件位置；不再走 fc-list 名称分支。
    assert any('kpsewhich "MyFont.otf"' in c for c in hint.commands)
    assert not any("fc-list" in c for c in hint.commands)
    # 文件名模式提示 Path=、变体字体与扩展名核对。
    assert "Path=" in hint.text
    assert "BoldFont=" in hint.text
    assert "Extension=" in hint.text
    assert "MyFont.otf" in hint.text_en
    assert "kpsewhich" in hint.text_en


def test_fontspec_file_mode_path_ttf() -> None:
    hint = hint_for_text('! Package fontspec Error: The font "fonts/MyFont.ttf" cannot be found.')
    assert hint is not None
    assert any('kpsewhich "fonts/MyFont.ttf"' in c for c in hint.commands)
    assert "fonts/MyFont.ttf" in hint.text
    assert "fonts/MyFont.ttf" in hint.text_en


@pytest.mark.parametrize(("tool", "has_luaotfload"), [("xelatex", False), ("lualatex", True)])
def test_fontspec_luaotfload_only_for_lualatex(tool: str, has_luaotfload: bool) -> None:
    hint = hint_for_text(
        '! Package fontspec Error: The font "SomeFamily" cannot be found.',
        tool_name=tool,
    )
    assert hint is not None
    matched = any("luaotfload-tool --update" in c for c in hint.commands)
    assert matched == has_luaotfload
