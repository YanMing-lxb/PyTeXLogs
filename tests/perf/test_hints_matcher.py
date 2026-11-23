"""性能门禁：hints 匹配器在大批量、重复、畸形输入下的耗时上限。

仅在环境变量 ``CI_PERF=1`` 时启用；本地默认跳过（与 ``test_100k_lines.py``
同一约定），避免拖慢开发循环。

阈值与依据（2026-11-21 在开发机 Python 3.15.2 两轮实测，均留 ≥2× 余量）：

- ``test_hints_mixed_100k_lines_under_2s``：100k 行混合日志（约 3.6MB，6.8 万
  条目）解析 + 逐条 ``hint_for_entry`` 实测约 0.88s（解析约 0.29s / 匹配约
  0.59s），门禁 2.0s ≈ 2.3× 余量；解析口径与 ``test_100k_lines.py`` 的 500ms
  解析门禁叠加，这里覆盖的是「解析 + 全量条目匹配」整条链路。
- ``test_hints_repeated_missing_glyph_under_1s``：5000 条缺字形消息（拉丁字符 +
  ``(U+4E2D)`` 码位变体各半）实测约 36ms，门禁 1.0s ≈ 27× 余量；守住热路径
  （缺字形规则）在规则表膨胀或正则回退时不退化。
- ``test_hints_malformed_long_font_line_under_100ms``：千级重复 ``Font `` 片段的
  畸形行（无 ``not found`` 结尾）单次匹配实测约 0.8ms；31k 字符的重复可加载字体帧
  实测约 4.7ms，门禁 100ms ≈ 20× 余量，防贪婪回溯把单次匹配放大成卡顿。

若任一用例实测超限：不要改 ``src/pytexlogs/hints.py``，先定位到具体规则/正则，
记录精确耗时与触发输入，回报后由协调方修复再复测。
"""

import os
import pathlib
import time

import pytest

from pytexlogs import LatexLogParser, LogEntry, LogLevel
from pytexlogs.hints import hint_for_entry, hint_for_text

#: 用例 1：100k 行混合日志（解析 + 全量条目匹配）总耗时上限（秒）。
CASE1_BUDGET_S = 2.0
#: 用例 1 的日志行数。
CASE1_LINES = 100_000
#: 用例 2：重复缺字形消息条数。
CASE2_ENTRIES = 5_000
#: 用例 2：5000 条匹配耗时上限（秒）。
CASE2_BUDGET_S = 1.0
#: 用例 3：单条畸形长行匹配耗时上限（秒）。
CASE3_BUDGET_S = 0.100


#: 混合日志样例池：覆盖信息行、文件加载、未定义引用/文献、各类错误帧、
#: 盒子警告、缺字形与致命错误；按周期重复铺到 100k 行。
_MIXED_POOL = (
    "This is pdfTeX, Version 3.141592653 (TeX Live 2024)",
    "(./main.tex",
    "Document Class: article 2024/02/08 v1.4n",
    "No file main.aux.",
    "LaTeX Warning: Reference `fig:arch' undefined on input line 56.",
    "LaTeX Warning: Citation `wang2020' undefined on input line 120.",
    "! Undefined control sequence.",
    "l.203 \\badcmd",
    "Overfull \\hbox (12.3pt too wide) at lines 40--41",
    "Underfull \\hbox (badness 1234) at lines 42--43",
    "Underfull \\vbox (badness 5678) at line 100",
    "File `siunitx.sty' not found.",
    "! Package graphicx Error: `fig.png' not found.",
    "LaTeX Error: Option clash for package graphicx.",
    "! Missing $ inserted.",
    "! Double subscript.",
    "Missing character: There is no α in font cmr10!",
    "! Emergency stop.",
    "! Fatal error occurred, no output PDF file produced!",
    "! Missing \\begin{document}.",
    "! Too many }'s.",
    "Command \\foo already defined.",
    "There's no line here to end.",
    "Token not allowed in a PDF string.",
    "Rerun to get cross-references right.",
)


@pytest.mark.skipif(os.environ.get("CI_PERF") != "1", reason="only run when CI_PERF=1")
def test_hints_mixed_100k_lines_under_2s(tmp_path: pathlib.Path) -> None:
    """100k 行混合日志：解析 + 对每个条目调用 ``hint_for_entry``，总耗时 <2s。"""
    # 列表拼接成 100k 行，避免字符串 ``+=`` 反复拷贝放大内存。
    lines = [_MIXED_POOL[i % len(_MIXED_POOL)] for i in range(CASE1_LINES)]
    log_text = "\n".join(lines)
    log_path = tmp_path / "mixed_100k.log"
    log_path.write_text(log_text, encoding="utf-8")

    parser = LatexLogParser()
    t0 = time.perf_counter()
    parsed = parser.parse_file(log_path)
    t_parse = time.perf_counter() - t0

    t0 = time.perf_counter()
    hint_hits = 0
    for entry in parsed.entries:
        if hint_for_entry(entry) is not None:
            hint_hits += 1
    t_hint = time.perf_counter() - t0
    elapsed = t_parse + t_hint

    # 确认负载真实落在解析与匹配上，防止条目为空把性能测试变成空跑。
    assert len(parsed.entries) > 0
    assert hint_hits > 0
    print(
        f"[perf-hints] lines={len(lines)} bytes={len(log_text.encode('utf-8'))} "
        f"entries={len(parsed.entries)} parse_ms={t_parse * 1000:.2f} "
        f"hint_ms={t_hint * 1000:.2f} total_ms={elapsed * 1000:.2f}"
    )
    assert elapsed < CASE1_BUDGET_S, (
        f"100k mixed log parse+hint too slow: total {elapsed * 1000:.2f}ms "
        f"(parse {t_parse * 1000:.2f}ms, hint {t_hint * 1000:.2f}ms) "
        f"> {CASE1_BUDGET_S * 1000:.0f}ms"
    )


@pytest.mark.skipif(os.environ.get("CI_PERF") != "1", reason="only run when CI_PERF=1")
def test_hints_repeated_missing_glyph_under_1s() -> None:
    """5000 条重复缺字形消息（拉丁字符 + U+ 码位变体各半），匹配 <1s。"""
    plain = "Missing character: There is no X in font cmr10!"
    variant = "Missing character: There is no 中 (U+4E2D) in font cjkfont!"
    entries = [
        LogEntry(
            level=LogLevel.WARNING,
            file="main.tex",
            line=1,
            text=plain if i % 2 == 0 else variant,
        )
        for i in range(CASE2_ENTRIES)
    ]

    t0 = time.perf_counter()
    hits = 0
    for entry in entries:
        if hint_for_entry(entry) is not None:
            hits += 1
    elapsed = time.perf_counter() - t0

    # 两组变体都必须命中缺字形规则；任一变体失配说明匹配退化，性能数字无意义。
    plain_hint = hint_for_entry(entries[0])
    variant_hint = hint_for_entry(entries[1])
    assert plain_hint is not None and plain_hint.kind == "missing_glyph"
    assert variant_hint is not None and variant_hint.kind == "missing_glyph"
    assert hits == CASE2_ENTRIES
    print(f"[perf-hints] entries={len(entries)} hits={hits} elapsed_ms={elapsed * 1000:.2f}")
    assert elapsed < CASE2_BUDGET_S, (
        f"repeated missing-glyph matching too slow: {elapsed * 1000:.2f}ms > {CASE2_BUDGET_S * 1000:.0f}ms"
    )


@pytest.mark.skipif(os.environ.get("CI_PERF") != "1", reason="only run when CI_PERF=1")
def test_hints_malformed_long_font_line_under_100ms() -> None:
    """超长畸形 Font 行单次匹配 <100ms，防贪婪回溯。"""
    # 第一条：千级重复 ``Font `` 片段、结尾不含 ``not found``/``undefined``；
    # 第二条：重复的可加载字体帧但缺失 ``not loadable`` 结尾（31k 字符量级）。
    malformed_lines = (
        "Font " * 1000 + "cmr10",
        "Font \\foo=NoSuchFont at 10.0pt " * 1000,
    )

    for line in malformed_lines:
        t0 = time.perf_counter()
        hint = hint_for_text(line)
        elapsed = time.perf_counter() - t0
        # 畸形行不应误命中任何字体规则；命中即说明规则被垃圾输入抢答。
        assert hint is None
        print(f"[perf-hints] malformed len={len(line)} elapsed_ms={elapsed * 1000:.3f}")
        assert elapsed < CASE3_BUDGET_S, (
            f"malformed Font line match too slow: {elapsed * 1000:.3f}ms "
            f"(len={len(line)}) > {CASE3_BUDGET_S * 1000:.0f}ms"
        )
