"""追加 B：unknown 模式（无 aux/bcf）引用报告不得拿旧缓存键冒充当前键。

旧实现把 ``current_keys`` / ``unchanged`` / ``key_counts`` 填成旧缓存值，
报告会谎报“当前引用 = 旧引用”。正确口径：
- 缓存文件原样保留（不清空、不回写）；
- 报告侧 ``current_keys=[]``、``key_counts={}``、``unchanged=[]``、
  ``added=[]``、``removed=[]``。
"""

from __future__ import annotations

from pathlib import Path

from pytexlogs import ProjectStateStore, run_pipeline

SAMPLE_LOG = "! Undefined control sequence.\nl.5 \\foobar\n"


def test_unknown_mode_report_does_not_reuse_old_cache_keys(tmp_path: Path) -> None:
    """预置 oldkey 缓存 + 无 aux/bcf：缓存保留，报告当前键全部为空。"""
    aux = tmp_path / "aux"
    aux.mkdir()
    store = ProjectStateStore(aux, "main")
    store.update_refs(keys=["oldkey"], key_counts={"oldkey": 1})

    # 只有 .log，没有 .aux / .bcf → detect_mode() == "unknown"。
    (aux / "main.log").write_text(SAMPLE_LOG, encoding="utf-8")

    report = run_pipeline(jobname="main", auxdir=aux, print_terminal=False)

    refs = report.references
    # 报告侧不得把旧键当成当前键。
    assert refs.current_keys == []
    assert refs.key_counts == {}
    assert refs.unchanged == []
    assert refs.added == []
    assert refs.removed == []
    assert refs.top_cited == []

    # 缓存文件原样保留，未被空集合覆盖。
    cached = ProjectStateStore(aux, "main").get_refs()
    assert cached.get("keys") == ["oldkey"]
    assert cached.get("key_counts") == {"oldkey": 1}
