"""报告序列化/反序列化工具：dict_to_report、write_report、load_report。"""

import dataclasses
import json
import logging
import os
from pathlib import Path
from typing import Any

from .models import (
    ConfigIgnoredReport,
    ParsedPipelineReport,
    PipelineMeta,
    ReferencesReport,
    ReportEntry,
    ToolResultReport,
)

logger = logging.getLogger(__name__)

_VALID_LEVELS = {"error", "warning", "typesetting", "info", "debug"}


def _from_dict_simple(cls: type[Any], d: dict[str, Any]) -> Any:
    """递归构造 dataclass 实例，未知字段入 custom_fields（若有）。"""
    cls_fields = {f.name for f in dataclasses.fields(cls)}
    known: dict[str, Any] = {}
    unknown: dict[str, Any] = {}

    for k, v in d.items():
        if k in cls_fields:
            known[k] = v
        else:
            unknown[k] = v

    for fname in cls_fields:
        if fname not in known:
            continue
        fval = known[fname]

        if isinstance(fval, dict):
            nested_cls: type[Any] | None = None
            if fname == "pipeline":
                nested_cls = PipelineMeta
            elif fname == "references":
                nested_cls = ReferencesReport
            elif fname == "config_ignored":
                nested_cls = ConfigIgnoredReport
            if nested_cls is not None:
                known[fname] = _from_dict_simple(nested_cls, fval)

        if fname == "entries" and isinstance(fval, list):
            known[fname] = [
                _from_dict_simple(ReportEntry, item) if isinstance(item, dict) else item
                for item in fval
            ]
        if fname == "suppressed_entries" and isinstance(fval, list):
            known[fname] = [
                _from_dict_simple(ReportEntry, item) if isinstance(item, dict) else item
                for item in fval
            ]
        if fname == "tool_results" and isinstance(fval, list):
            known[fname] = [
                _from_dict_simple(ToolResultReport, item) if isinstance(item, dict) else item
                for item in fval
            ]

    if cls is ReportEntry and "level" in known:
        lvl = known["level"]
        if lvl not in _VALID_LEVELS:
            if lvl:
                logger.warning("unknown level %s", lvl)
            known["level"] = "info"

    try:
        instance = cls(**known)
    except TypeError:
        defaults: dict[str, Any] = {}
        for f in dataclasses.fields(cls):
            if f.name not in known:
                if f.default is not dataclasses.MISSING:
                    defaults[f.name] = f.default
                elif f.default_factory is not dataclasses.MISSING:
                    defaults[f.name] = f.default_factory()
        combined = {**defaults, **known}
        instance = cls(**combined)

    if "custom_fields" in cls_fields and unknown:
        key = f"_unknown_keys_{cls.__name__}"
        existing = instance.custom_fields.get(key, [])
        if isinstance(existing, list):
            existing.extend(unknown.keys())
            instance.custom_fields[key] = existing
            for uk, uv in unknown.items():
                if uk not in instance.custom_fields:
                    instance.custom_fields[uk] = uv

    return instance


def dict_to_report(d: dict[str, Any]) -> ParsedPipelineReport:
    """从 dict 递归构造 ParsedPipelineReport。"""
    result: Any = _from_dict_simple(ParsedPipelineReport, d)
    return result


def write_report(report: ParsedPipelineReport, path: str | Path) -> Path | None:
    """原子式写入 JSON 报告到 path，失败返回 None。"""
    from .exporters.json_exporter import report_to_dict

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                report_to_dict(report),
                f,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                default=str,
            )
        os.replace(tmp, path)
    except OSError:
        logger.warning("报告写入失败: %s", exc_info=True)
        return None
    return path


def load_report(path: str | Path) -> ParsedPipelineReport:
    """从 JSON 文件加载 ParsedPipelineReport，高 schema_version 警告。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
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
    sv = d.get("schema_version", 1)
    if sv > 1:
        logger.warning("schema_version %d 高于当前 1，部分字段可能被忽略", sv)
    return dict_to_report(d)