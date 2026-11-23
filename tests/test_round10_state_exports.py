"""第 10 轮修复回归：状态版本保护 / 列表 ParsedLog 过滤 / stats 契约统一。

覆盖四类已确认缺陷：
1. ``ProjectStateStore`` 读到未来版本（如 v4）文件时，``_mutate`` 不得把空骨架
   写回磁盘，从而覆盖 ``pytexmk.build`` 等其它命名空间；
2. ``filter_by_level`` 的 list 分支必须过滤 ``ParsedLog``（此前原样透传）；
3. ``ToolResultReport.from_parsed_log`` 保留 parser 的整日志 stats，并与
   目录 pipeline 的 stats 键集合一致；
4. ``recompute_stats`` 同时兼容英文与旧中文的未定义引用/文献前缀。
"""

import json
from pathlib import Path

from pytexlogs import (
    PROJECT_STATE_FILENAME,
    SCHEMA_VERSION,
    LogEntry,
    LogLevel,
    ParsedLog,
    ProjectStateStore,
    ToolResultReport,
    parse_log_file,
    run_pipeline,
    to_csv,
    to_json,
)
from pytexlogs.core.stats import recompute_stats

#: 未来版本状态文件：v4 + pytexmk.build + 一个本库不认识的顶层键。
_V4_STATE = {
    "schema_version": 4,
    "timestamp": "2030-01-01T00:00:00+00:00",
    "pytexmk": {"build": {"fingerprint": "sha256:abc", "round": 3}},
    "future_tool": {"payload": [1, 2, 3]},
}

#: 同时带 ERROR 与 WARNING 的运行时解析结果，stats 里含整日志键。
_SAMPLE_LOG = """This is pdfTeX, Version 3.14159265-2.6-1.40.25
(./main.tex
! Undefined control sequence.
l.5 \\foobar
Output written on main.pdf (3 pages, 1000 bytes).
Transcript written on main.log.
"""


def _parsed_with_two_levels() -> ParsedLog:
    return ParsedLog(
        entries=[
            LogEntry(
                level=LogLevel.ERROR,
                file="main.tex",
                line=5,
                text="! Undefined control sequence.",
            ),
            LogEntry(
                level=LogLevel.WARNING,
                file="main.tex",
                line=9,
                text="Overfull \\hbox (2pt too wide) in paragraph at lines 9--10",
            ),
        ],
        tool_name="latex",
        category="compile",
        importance="high",
        stats={
            "pages_output": 3,
            "overfull_boxes": 1,
            "undefined_refs": 0,
            "undefined_cites": 0,
        },
    )


# ------------------------------------------------------------ 任务 1：版本保护


def test_incompatible_state_file_is_never_overwritten(tmp_path: Path) -> None:
    """v4 文件：update_refs/clear 都必须返回 False，且文件字节完全不变。"""
    path = tmp_path / PROJECT_STATE_FILENAME
    path.write_text(json.dumps(_V4_STATE, ensure_ascii=False), encoding="utf-8")
    before = path.read_bytes()

    store = ProjectStateStore(tmp_path, "main")
    assert store.update_refs(keys=["new-key"]) is False
    assert path.read_bytes() == before, "版本不兼容时不得写盘覆盖原文件"

    # prune=True 路径（clear 会删除空的 pytexmk 命名空间）同样不得 unlink。
    assert store.clear() is False
    assert path.read_bytes() == before, "版本不兼容时不得删除原文件"

    # 读取侧行为不变：仍按空骨架返回，但原文件保留。
    assert store.load() == {"schema_version": SCHEMA_VERSION}
    assert path.exists()


def test_v3_state_still_writes_and_merges(tmp_path: Path) -> None:
    """v3 文件正常写入仍返回 True，且保留其它命名空间与未知顶层键。"""
    path = tmp_path / PROJECT_STATE_FILENAME
    path.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "pytexmk": {"build": {"round": 2}},
                "other_tool": {"x": 1},
            }
        ),
        encoding="utf-8",
    )

    store = ProjectStateStore(tmp_path, "main")
    assert store.update_refs(keys=["k1"]) is True

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["pytexmk"]["build"]["round"] == 2
    assert data["other_tool"]["x"] == 1
    assert data["pytexlogs"]["refs"]["keys"] == ["k1"]


# -------------------------------------------------- 任务 2：列表 ParsedLog 过滤


def test_to_json_list_parsed_log_filters_and_recomputes() -> None:
    """``to_json([parsed], min_level=ERROR)`` 只含 ERROR，stats 与过滤后一致。"""
    data = json.loads(to_json([_parsed_with_two_levels()], min_level=LogLevel.ERROR, include_hints=False))

    item = data["results"][0]
    assert [e["level"] for e in item["entries"]] == ["error"]

    stats = item["stats"]
    assert stats["entries_count"] == 1
    assert stats["error"] == 1
    assert stats["warning"] == 0
    assert stats["errors_count"] == 1
    assert stats["warnings_count"] == 0
    # 被过滤掉的 Overfull 条目不应再计入盒子统计；整日志键原样保留。
    assert stats["overfull_boxes"] == 0
    assert stats["pages_output"] == 3


def test_to_csv_list_parsed_log_filters_rows() -> None:
    """``to_csv([parsed], min_level=ERROR)`` 只输出表头 + 1 条错误行。"""
    lines = to_csv([_parsed_with_two_levels()], min_level=LogLevel.ERROR, include_hints=False).splitlines()

    assert len(lines) == 2, "列表 ParsedLog 没有被等级过滤"
    assert lines[0].split(",")[:3] == ["file", "line", "level"]
    assert lines[1].split(",")[2] == "error"


# ------------------------------------------------- 任务 3：stats 契约统一


def test_single_file_and_pipeline_stats_keys_match(tmp_path: Path) -> None:
    """同一份 .log：单文件入口与目录 pipeline 的 stats 键集合必须相同。"""
    log_path = tmp_path / "main.log"
    log_path.write_text(_SAMPLE_LOG, encoding="utf-8")

    single = ToolResultReport.from_parsed_log(parse_log_file(log_path))

    report = run_pipeline(jobname="main", auxdir=tmp_path, print_terminal=False)
    assert report.tool_results, "目录模式没有产出任何工具报告"
    pipeline_tr = report.tool_results[0]

    assert set(single.stats) == set(pipeline_tr.stats)
    assert single.stats["pages_output"] == pipeline_tr.stats["pages_output"] == 3
    assert single.stats["entries_count"] == pipeline_tr.stats["entries_count"]


# --------------------------------------------- 任务 4：stats 前缀双兼容


def test_recompute_stats_accepts_english_and_legacy_chinese_prefixes() -> None:
    """英文新文案与旧中文文案都要计入 undefined_refs / undefined_cites。"""
    entries = [
        LogEntry(
            level=LogLevel.WARNING,
            file="main.tex",
            line=1,
            text="Undefined reference `fig:a`",
        ),
        LogEntry(
            level=LogLevel.WARNING,
            file="main.tex",
            line=2,
            text="找不到 reference `fig:b`",
        ),
        LogEntry(
            level=LogLevel.WARNING,
            file="main.tex",
            line=3,
            text="Undefined citation `kim2020`",
        ),
        LogEntry(
            level=LogLevel.WARNING,
            file="main.tex",
            line=4,
            text="找不到 citation `lee2021`",
        ),
    ]
    stats: dict[str, object] = {"undefined_refs": 99, "undefined_cites": 99}

    recompute_stats(entries, stats)

    assert stats["undefined_refs"] == 2
    assert stats["undefined_cites"] == 2
