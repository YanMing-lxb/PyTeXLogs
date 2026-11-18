"""0.6.0 等级语义回归：TYPESET 是"提示"，排在 INFO 之后，不算 warning。"""

from pytexlogs import LogEntry, LogLevel, filter_severity
from pytexlogs.cli.args import _SEVERITY_LEVEL
from pytexlogs.core.models import _SEVERITY_RANK


def test_typeset_is_below_info_in_severity() -> None:
    """ERROR < WARNING < INFO < TYPESET（0.5 把 TYPESET 排在 INFO 前面）。"""
    assert LogLevel.ERROR < LogLevel.WARNING < LogLevel.INFO < LogLevel.TYPESET
    assert _SEVERITY_RANK[LogLevel.ERROR] == 0
    assert _SEVERITY_RANK[LogLevel.TYPESET] == 3


def test_prompt_levels_after_typeset() -> None:
    """排版类提示（字体/图形/页面）比 TYPESET 更靠后，且都弱于 INFO。"""
    for level in (LogLevel.FONT, LogLevel.GRAPHIC, LogLevel.PAGE):
        assert LogLevel.INFO < level
        assert level.severity > LogLevel.TYPESET.severity


def test_all_severity_keeps_typesetting_entries() -> None:
    """``--severity all`` 必须连提示级一起输出（0.5 把它映射成 INFO，提示被丢掉）。"""
    entries = [
        LogEntry(level=LogLevel.TYPESET, file="a.tex", line=1, text="Overfull \\hbox"),
        LogEntry(level=LogLevel.INFO, file="a.tex", line=2, text="note"),
    ]
    kept = filter_severity(entries, min_level=_SEVERITY_LEVEL["all"])
    assert [e.text for e in kept] == ["Overfull \\hbox", "note"]


def test_info_severity_excludes_prompt_levels() -> None:
    """``--severity info`` 是"只要 info 及以上严重度"，提示级不进来。"""
    entries = [
        LogEntry(level=LogLevel.TYPESET, file="a.tex", line=1, text="Overfull \\hbox"),
        LogEntry(level=LogLevel.INFO, file="a.tex", line=2, text="note"),
    ]
    kept = filter_severity(entries, min_level=LogLevel.INFO)
    assert [e.text for e in kept] == ["note"]


def test_warning_filter_excludes_typesetting() -> None:
    """``--severity warning`` 只留 error/warning，Overfull 这类提示被过滤掉。"""
    entries = [
        LogEntry(level=LogLevel.ERROR, file="a.tex", line=1, text="err"),
        LogEntry(level=LogLevel.WARNING, file="a.tex", line=2, text="warn"),
        LogEntry(level=LogLevel.TYPESET, file="a.tex", line=3, text="Overfull \\hbox"),
    ]
    kept = filter_severity(entries, min_level=LogLevel.WARNING)
    assert [e.level for e in kept] == [LogLevel.ERROR, LogLevel.WARNING]
