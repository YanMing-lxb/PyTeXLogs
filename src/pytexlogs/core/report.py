"""报告序列化/反序列化工具：dict_to_report、write_report、load_report。"""

import dataclasses
import json
import logging
import os
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any

from .models import (
    REPORT_SCHEMA_VERSION,
    ConfigIgnoredReport,
    LogLevel,
    ParsedPipelineReport,
    PipelineMeta,
    ReferencesReport,
    ReportEntry,
    ToolResultReport,
)

logger = logging.getLogger(__name__)

#: 合法等级集合直接由 :class:`LogLevel` 派生，避免白名单与枚举漂移
#: （历史问题是白名单漏掉 ``font/graphic/page``，导致报告回读时被降级成 ``info``）。
_VALID_LEVELS: frozenset[str] = frozenset(lv.value for lv in LogLevel)

#: 需要递归还原成 dataclass 的嵌套字段 → 目标类型。
_NESTED_FIELDS: dict[str, type[Any]] = {
    "pipeline": PipelineMeta,
    "references": ReferencesReport,
    "config_ignored": ConfigIgnoredReport,
}

#: 需要递归还原的元素字段 → 元素类型。
_LIST_FIELDS: dict[str, type[Any]] = {
    "entries": ReportEntry,
    "suppressed_entries": ReportEntry,
    "tool_results": ToolResultReport,
}


def _from_dict_simple(cls: type[Any], d: dict[str, Any]) -> Any:
    """从 dict 构造 dataclass 实例；未知字段收进 ``custom_fields`` 以免信息丢失。

    0.6.1 起不再用 ``try: cls(**known) except TypeError`` 兜底：模型里所有字段
    都有默认值，缺字段本该走默认值，``TypeError`` 只说明调用方传了脏数据。旧兜底
    会把这类错误吞掉，换来一个字段全空但"看起来正常"的对象。
    """
    cls_fields = {f.name for f in dataclasses.fields(cls)}
    known: dict[str, Any] = {k: v for k, v in d.items() if k in cls_fields}
    unknown: dict[str, Any] = {k: v for k, v in d.items() if k not in cls_fields}

    for fname, value in known.items():
        nested_cls = _NESTED_FIELDS.get(fname)
        if nested_cls is not None and isinstance(value, dict):
            known[fname] = _from_dict_simple(nested_cls, value)
            continue
        item_cls = _LIST_FIELDS.get(fname)
        if item_cls is not None and isinstance(value, list):
            known[fname] = [_from_dict_simple(item_cls, item) if isinstance(item, dict) else item for item in value]

    if cls is ReportEntry:
        level = known.get("level")
        if level not in _VALID_LEVELS:
            if level:
                logger.warning("报告中出现未知等级 %s，按 info 处理", level)
            known["level"] = "info"

    instance = cls(**known)
    if unknown and "custom_fields" in cls_fields:
        instance.custom_fields.update(unknown)
    return instance


def dict_to_report(d: dict[str, Any]) -> ParsedPipelineReport:
    """从 dict 递归构造 ParsedPipelineReport。"""
    if not isinstance(d, dict):
        raise TypeError(f"报告顶层必须是 JSON object，实际是 {type(d).__name__}")
    result: Any = _from_dict_simple(ParsedPipelineReport, d)
    return result


def _write_report_impl(report: ParsedPipelineReport, path: str | Path) -> tuple[Path | None, str | None]:
    """写报告并同时返回失败原因；公开的 ``write_report`` 只暴露路径。"""
    from ..exporters.json_exporter import report_to_dict

    path = Path(path)
    tmp: Path | None = None
    fd: int | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
        tmp = Path(tmp_name)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            fd = None
            json.dump(
                report_to_dict(report),
                f,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                default=str,
            )
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(path)
    except Exception as e:
        # 任何失败都要清掉半截临时文件；报告本身是可选产物，不能污染项目目录
        logger.warning("报告写入失败: %s", path, exc_info=True)
        if fd is not None:
            with suppress(OSError):
                os.close(fd)
        if tmp is not None:
            with suppress(OSError):
                tmp.unlink(missing_ok=True)
        return None, f"{type(e).__name__}: {e}"
    return path, None


def write_report(report: ParsedPipelineReport, path: str | Path) -> Path | None:
    """原子式写入 JSON 报告到 path，失败返回 None（不留下临时文件）。"""
    return _write_report_impl(report, path)[0]


def load_report(path: str | Path) -> ParsedPipelineReport:
    """从 JSON 文件加载 ParsedPipelineReport，高 schema_version 警告。"""
    try:
        with Path(path).open(encoding="utf-8") as f:
            d: dict[str, Any] = json.load(f)
    except FileNotFoundError:
        logger.error("报告文件不存在: %s", path)
        raise
    except json.JSONDecodeError as e:
        logger.error("报告文件 JSON 格式错误: %s - %s", path, e)
        raise
    except Exception as e:
        logger.error("加载报告文件失败: %s - %s", path, e)
        raise
    if not isinstance(d, dict):
        logger.error("报告顶层不是 JSON object: %s（实际 %s）", path, type(d).__name__)
        raise TypeError(f"报告顶层必须是 JSON object，实际是 {type(d).__name__}")
    sv = d.get("schema_version", REPORT_SCHEMA_VERSION)
    if isinstance(sv, int) and sv > REPORT_SCHEMA_VERSION:
        logger.warning(
            "schema_version %d 高于当前 %d，部分字段可能被忽略",
            sv,
            REPORT_SCHEMA_VERSION,
        )
    return dict_to_report(d)
