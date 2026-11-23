"""第 4 轮坏盒子匹配去重 + markup 正则预编译回归（任务 20）。

行为口径必须保持不变：overfull/underfull 条目数、等级、文本与旧实现一致；
优化点只是预检与 ``_parse_bad_box`` 不再对同一行二次遍历正则，以及
``_strip_rich_markup`` 的正则提到模块级预编译。
"""

from pytexlogs.display import formatter as fmt_mod
from pytexlogs.display.formatter import _strip_rich_markup
from pytexlogs.parsers import latex as latex_mod
from pytexlogs.parsers.latex import LatexLogParser

_BOX_LOG = (
    "LaTeX Warning: Something odd on input line 3.\n"
    "Overfull \\hbox (12.3pt too wide) in paragraph at lines 40--41\n"
    "Underfull \\hbox (badness 1234) in paragraph at lines 42--43\n"
)

#: 单条 overfull 帧：专供匹配次数探针，避免 underfull 行对 overfull 正则的
#: 未命中扫描干扰计数。
_SINGLE_OVERFULL_LOG = (
    "LaTeX Warning: Something odd on input line 3.\nOverfull \\hbox (12.3pt too wide) in paragraph at lines 40--41\n"
)


def test_bad_box_entries_unchanged() -> None:
    """行为快照：1 条 overfull + 1 条 underfull，等级/文本不变。"""
    parsed = LatexLogParser(root_file="main.tex").parse(_BOX_LOG)

    boxes = [e for e in parsed.entries if e.level.value == "typesetting"]
    assert len(boxes) == 2
    overfull = [e for e in boxes if "Overfull" in e.text]
    underfull = [e for e in boxes if "Underfull" in e.text]
    assert len(overfull) == 1
    assert len(underfull) == 1
    assert overfull[0].line == 40
    assert underfull[0].line == 42
    assert parsed.stats["overfull_boxes"] == 1
    assert parsed.stats["underfull_boxes"] == 1


def test_bad_box_pattern_matched_once_per_line() -> None:
    """计数探针：同一条坏盒子行的匹配正则只调用一次（预检不二次遍历）。"""

    class _CountingMatcher:
        def __init__(self, pattern: object) -> None:
            self.pattern = pattern
            self.calls = 0

        def match(self, line: str):  # noqa: ANN001 - 与 re.Pattern.match 对齐
            self.calls += 1
            return self.pattern.match(line)

    wrapped = [(_CountingMatcher(pat), is_overfull) for pat, is_overfull in latex_mod._BAD_BOX_PATTERNS]
    original = latex_mod._BAD_BOX_PATTERNS
    latex_mod._BAD_BOX_PATTERNS = tuple(wrapped)
    try:
        # 末尾换行切出的尾随空行由空白行守卫跳过正则表，探针只统计坏盒子行本身。
        LatexLogParser(root_file="main.tex").parse(_SINGLE_OVERFULL_LOG)
    finally:
        latex_mod._BAD_BOX_PATTERNS = original

    # 第一条 overfull 模式即命中；预检与解析不得各扫一遍。
    overfull_wrapper = wrapped[0][0]
    assert overfull_wrapper.calls == 1, f"overfull 正则被调用 {overfull_wrapper.calls} 次，存在二次遍历"


def test_strip_rich_markup_output_unchanged() -> None:
    """markup 剥离结果行为不变；正则在模块级预编译。"""
    assert _strip_rich_markup("[bold red]  [E][/] error text") == "   error text"
    assert _strip_rich_markup("plain line") == "plain line"
    # 模块级预编译正则存在（formatter 内不得每次调用都 re.compile）。
    assert hasattr(fmt_mod, "_RICH_MARKUP_RE")
