"""第 7 轮：引擎状态 / 忽略过滤健壮性回归（任务 7–10）。

覆盖：
- 7. 引用跟踪器初始化/抽取抛异常且 ``print_terminal=True`` 时不得 ``UnboundLocalError``；
- 8. 无 aux/bcf（unknown 模式）不得把旧引用缓存清空；
- 9. 非法 ``ignore_patterns`` 正则（``re.error``）跳过该项 + warning，不崩流水线；
- 10. 忽略过滤后 ``tool.stats`` 必须与剩余条目重算一致（含全部等级键、
  errors/warnings、盒子计数、未定义引用键）。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from pytexlogs import ProjectStateStore, run_pipeline
from pytexlogs.core.manager import LogParserManager
from pytexlogs.core.models import BaseLogParser, ParsedLog
from pytexlogs.core.registry import LogParserRegistry

SAMPLE_LOG = "! Undefined control sequence.\nl.5 \\foobar\n"

#: 96 条排版盒子 + 1 条未定义引用（citation），过滤前共 97 条。
_BOX_LINE = "Overfull \\hbox (12.3pt too wide) in paragraph at lines 40--41"
_CITE_LINE = "LaTeX Warning: Citation `wang2020' on page 1 undefined on input line 120."
_NINETY_SEVEN_LOG = "\n".join([_BOX_LINE] * 96 + [_CITE_LINE])


# ---------------------------------------------------------------- 任务 7


def test_ref_tracker_ctor_failure_returns_report_with_terminal(tmp_path: Path) -> None:
    """tracker 构造抛异常：报告仍返回，打印路径不触发 UnboundLocalError。"""
    aux = tmp_path / "aux"
    aux.mkdir()
    (aux / "main.log").write_text(SAMPLE_LOG, encoding="utf-8")

    class _BoomTracker:
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise RuntimeError("tracker ctor boom")

    with patch("pytexlogs.core.engine.RefChangeTracker", _BoomTracker):
        report = run_pipeline(
            jobname="main",
            auxdir=aux,
            print_terminal=True,
        )

    assert report is not None
    assert report.references.current_keys == []
    assert report.references.added == []
    assert report.references.removed == []
    assert report.references.unchanged == []


def test_ref_tracker_extract_failure_returns_report_with_terminal(tmp_path: Path) -> None:
    """抽取阶段抛异常：同上，``ref_unchanged`` 不得留未绑定变量。"""
    aux = tmp_path / "aux"
    aux.mkdir()
    (aux / "main.log").write_text(SAMPLE_LOG, encoding="utf-8")

    class _BoomTracker:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def detect_mode(self) -> str:
            return "bibtex"

        def extract_current_with_counts(self) -> tuple[list[str], dict[str, int]]:
            raise RuntimeError("extract boom")

        def load_cache(self) -> list[str]:
            return []

        def diff(self, now: object, old: object) -> dict[str, set[str]]:
            return {"added": set(), "removed": set(), "unchanged": set()}

    with patch("pytexlogs.core.engine.RefChangeTracker", _BoomTracker):
        report = run_pipeline(
            jobname="main",
            auxdir=aux,
            print_terminal=True,
        )

    assert report is not None
    assert report.references.removed == []


# ---------------------------------------------------------------- 任务 8


def test_no_aux_no_bcf_keeps_old_cache(tmp_path: Path) -> None:
    """无 aux/bcf（unknown 模式）：旧缓存键必须保留，不能被空集合清掉。"""
    aux = tmp_path / "aux"
    aux.mkdir()
    store = ProjectStateStore(aux, "main")
    store.update_refs(keys=["oldkey"], key_counts={"oldkey": 1})

    # 只有 .log，没有 .aux / .bcf → detect_mode() == "unknown"。
    (aux / "main.log").write_text(SAMPLE_LOG, encoding="utf-8")

    report = run_pipeline(jobname="main", auxdir=aux, print_terminal=False)

    refs = ProjectStateStore(aux, "main").get_refs()
    assert refs.get("keys") == ["oldkey"], "unknown 模式不得清空旧引用缓存"
    assert report.references.removed == []


# ---------------------------------------------------------------- 任务 9


def test_illegal_ignore_pattern_skipped_not_fatal(tmp_path: Path) -> None:
    """非法正则 ``(`` 跳过该项并告警；流水线不抛 ``re.error``。"""
    aux = tmp_path / "aux"
    aux.mkdir()
    (aux / "main.log").write_text(SAMPLE_LOG, encoding="utf-8")

    report = run_pipeline(
        jobname="main",
        auxdir=aux,
        ignore_patterns=["("],
        print_terminal=False,
    )

    # 原列表保留在报告里（可解释：用户请求过的模式原样留痕，非法项未参与过滤）。
    assert report.config_ignored.ignore_patterns == ["("]
    # 非法模式没有过滤掉任何条目。
    assert report.config_ignored.suppressed_entries == []
    assert any(e.level == "error" for tr in report.tool_results for e in tr.entries)


# ---------------------------------------------------------------- 任务 10


def test_filtered_stats_match_remaining_entries(tmp_path: Path) -> None:
    """忽略过滤后：stats 等级键 / errors / warnings / 盒子 / 未定义键与剩余条目一致。"""
    aux = tmp_path / "aux"
    aux.mkdir()

    # 未过滤基线：1 条 citation 警告 + 96 条排版盒子。
    base = run_pipeline(
        jobname="main",
        auxdir=aux,
        steps=["pdflatex"],
        captured_outputs={"pdflatex": _NINETY_SEVEN_LOG},
        print_terminal=False,
    )
    base_tr = base.tool_results[0]
    assert len(base_tr.entries) == 97
    assert base_tr.stats["undefined_cites"] == 1
    assert base_tr.stats["warnings_count"] == 1

    report = run_pipeline(
        jobname="main",
        auxdir=aux,
        steps=["pdflatex"],
        captured_outputs={"pdflatex": _NINETY_SEVEN_LOG},
        ignore_patterns=["citation"],
        print_terminal=False,
    )
    tr = report.tool_results[0]

    assert len(tr.entries) == 96
    stats = tr.stats
    assert stats["entries_count"] == 96
    assert stats["errors_count"] == 0
    assert stats["warnings_count"] == 0
    # 全部等级键都必须与剩余条目重算一致（含 typesetting/font/graphic/page）。
    assert stats["warning"] == 0
    assert stats["typesetting"] == 96
    assert stats["error"] == 0
    # 盒子计数按剩余条目重算。
    assert stats["overfull_boxes"] == 96
    assert stats["underfull_boxes"] == 0
    # 被过滤掉的 citation 不再保留过期的 1。
    assert stats["undefined_cites"] == 0
    assert stats["undefined_refs"] == 0

    # severity 桶与 stats 口径一致。
    bucket = report.severity_counts[tr.category]
    assert bucket["total"] == 96
    assert bucket["warning"] == 0
    assert bucket["typesetting"] == 96


# ---------------------------------------------------------------- 共用执行器


class _BoomParser(BaseLogParser):
    """解析必然抛异常的第三方 parser，用于验证 StepOutcome.error 语义。"""

    category = "custom"
    importance = "low"

    def parse(self, log_text: str, root_file: str | None = None) -> ParsedLog:
        raise RuntimeError("parser boom")


def test_pipeline_keeps_parse_exception_report(tmp_path: Path) -> None:
    """parser 抛异常：engine 仍产出带 parse_exception 的空工具报告，不记为 skipped。"""
    registry = LogParserRegistry()
    registry.register("boom", _BoomParser)
    manager = LogParserManager(registry)

    with patch("pytexlogs.core.engine.LogParserManager", return_value=manager):
        report = run_pipeline(
            jobname="main",
            auxdir=tmp_path,
            steps=["boom"],
            captured_outputs={"boom": "anything"},
            print_terminal=False,
        )

    assert report.pipeline.total_steps == 1
    assert report.pipeline.attempted_steps == 1
    assert report.pipeline.skipped_steps == []
    assert len(report.tool_results) == 1
    tool = report.tool_results[0]
    assert tool.entries == []
    assert tool.parse_exception == {
        "type": "RuntimeError",
        "message": "parser boom",
    }
