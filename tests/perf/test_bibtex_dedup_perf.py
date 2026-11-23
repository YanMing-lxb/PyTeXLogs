"""性能门禁：BibTeX 多行错误帧扫描与去重的回归基准（任务 12）。

仅在 ``CI_PERF=1`` 时启用；本地默认跳过。覆盖三种真实帧形：

- ``_SKIP_FIRST_FRAME``：收尾行在前、``---line`` 头在后（单行路径记录）；
- ``_ENTRY_FRAME``：``消息---line N of file`` 头 + 正文 + ``... skipping ... entry``；
- ``_COMMAND_FRAME``：同上，但收尾是 ``... skipping ... command``（宏定义错误）。

旧实现两条多行错误正则在全文范围找各自收尾关键词，另一帧形的每一个起始行
都会失败并扫到文末，呈 O(n²) 回溯；这里用 200 vs 2000 的耗时比例兜底，
防止二次增长复发。阈值宽松（5000 帧/种 < 2s，比例 < 16×），只防数量级退化。
"""

import os
import time

import pytest

from pytexlogs.parsers.bibtex import BibtexParser

CASE_FRAMES = 5_000
BUDGET_S = 2.0
#: 线性增长下 200→2000（×10）耗时比应在个位数到十几；二次增长约 ×100。
RATIO_BUDGET = 16.0

_SKIP_FIRST_FRAME = "I'm skipping whatever remains of this entry.\n---line 12 of file refs.bib\n"
_ENTRY_FRAME = "error---line 1 of file refs.bib\nbad text\nI'm skipping whatever remains of this entry\n"
_COMMAND_FRAME = "macro---line 1 of file refs.bib\nbody line\nI'm skipping whatever remains of this command\n"


def _parse(text: str) -> object:
    return BibtexParser(root_file="main.tex").parse(text)


@pytest.mark.skipif(os.environ.get("CI_PERF") != "1", reason="only run when CI_PERF=1")
def test_bibtex_repeated_frames_dedup_fast() -> None:
    """三种帧形各 5000 条：去重后条目数正确，解析耗时在线性门禁内。"""
    log_text = (_SKIP_FIRST_FRAME + _ENTRY_FRAME + _COMMAND_FRAME) * CASE_FRAMES

    t0 = time.perf_counter()
    parsed = _parse(log_text)
    elapsed = time.perf_counter() - t0

    # 正确性：三种帧形各重复 5000 次，稳定键去重后各留一条 ERROR。
    assert len(parsed.entries) == 3, f"去重后条目数错误: {len(parsed.entries)}"
    assert all(e.level.value == "error" for e in parsed.entries)

    print(f"[perf-bibtex] frames={CASE_FRAMES * 3} entries={len(parsed.entries)} elapsed_ms={elapsed * 1000:.2f}")
    assert elapsed < BUDGET_S, f"BibTeX 错误帧扫描回退成 O(n²): {elapsed * 1000:.2f} ms > {BUDGET_S * 1000:.0f} ms"


@pytest.mark.skipif(os.environ.get("CI_PERF") != "1", reason="only run when CI_PERF=1")
def test_bibtex_frame_scaling_linear() -> None:
    """200 vs 2000（×10 帧）耗时比不得接近二次增长（×100）。"""
    small = (_ENTRY_FRAME + _COMMAND_FRAME) * 200
    large = (_ENTRY_FRAME + _COMMAND_FRAME) * 2_000

    t0 = time.perf_counter()
    small_parsed = _parse(small)
    t1 = time.perf_counter()
    large_parsed = _parse(large)
    t2 = time.perf_counter()

    small_ms = (t1 - t0) * 1000
    large_ms = (t2 - t1) * 1000
    ratio = large_ms / small_ms if small_ms > 0 else float("inf")

    assert len(small_parsed.entries) == 2
    assert len(large_parsed.entries) == 2

    print(f"[perf-bibtex-scale] 200={small_ms:.2f}ms 2000={large_ms:.2f}ms ratio={ratio:.2f}")
    assert ratio < RATIO_BUDGET, f"帧扫描呈二次增长: 200→2000 耗时比 {ratio:.2f} > {RATIO_BUDGET}"
